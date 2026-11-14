"""The main application window."""

import math
import time
from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QLabel,
    QMainWindow,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bhlab import __version__
from bhlab.formatting import format_length_auto, format_number
from bhlab.simulation.model import Particle, Simulation
from bhlab.ui.mass_controls import MassControls
from bhlab.ui.particle_form import ParticleForm
from bhlab.ui.run_controls import RunControls
from bhlab.ui.scales_panel import ScalesPanel
from bhlab.ui.simulation_runner import SimulationRunner
from bhlab.ui.theme import particle_colour
from bhlab.ui.view_options import ViewOptions
from bhlab.ui.viewport import BlackHoleView
from bhlab.units import HORIZON_RADIUS_RG, BlackHole

CURSOR_HINT = "Move the mouse over the map to read coordinates."


def describe_cursor(x: float, y: float, black_hole: BlackHole) -> str:
    """Qt rich text giving a map position in Cartesian and polar form.

    ``x`` and ``y`` are in units of r_g. The radius is also given as a physical length for
    ``black_hole``; the angle φ is measured anticlockwise from the +x axis, from 0° to 360°.
    """
    radius = math.hypot(x, y)
    angle = round(math.degrees(math.atan2(y, x)) % 360.0, 1) % 360.0
    unit = "r<sub>g</sub>"
    parts = [
        f"x = {format_number(x)} {unit}",
        f"y = {format_number(y)} {unit}",
        f"r = {format_number(radius)} {unit} = "
        f"{format_length_auto(black_hole.length_to_si(radius))}",
        f"φ = {angle:.1f}°",
    ]
    if radius < HORIZON_RADIUS_RG:
        parts.append("inside the event horizon")
    return " &nbsp;·&nbsp; ".join(parts)


def describe_particles(particles: Sequence[Particle], stop_radius: float) -> str:
    """A sentence or two on how many particles there are and what they are doing."""
    count = len(particles)
    if count == 0:
        return "No particles yet."
    stopped = sum(particle.is_stopped for particle in particles)
    noun = "particle" if count == 1 else "particles"
    if stopped == 0:
        return f"{count} {noun}, {'moving' if count == 1 else 'all moving'}."
    return (
        f"{count} {noun}: {count - stopped} moving, {stopped} stopped at "
        f"r = {stop_radius:g} GM/c². Newtonian gravity has no horizon: the stop only marks "
        "where this model ends."
    )


def _side_panel(object_name: str, width: int, *sections: QWidget) -> QScrollArea:
    """A fixed-width panel holding ``sections`` from the top down.

    When the window is too short to show all of it the panel scrolls. Without the scroll area
    Qt would squash the sections into the space there is, and clip their text.
    """
    panel = QFrame()
    panel.setObjectName(object_name)
    panel.setFixedWidth(width)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 22, 20, 20)
    layout.setSpacing(22)
    for section in sections:
        layout.addWidget(section)
    layout.addStretch(1)

    scroll = QScrollArea()
    scroll.setObjectName("sideScroll")
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidgetResizable(True)  # the panel fills the height when there is room to spare
    scroll.setFixedWidth(width)
    scroll.setWidget(panel)
    return scroll


class MainWindow(QMainWindow):
    """What you set up on the left (the black hole, the particles), the map with its run
    controls in the centre, reference information on the right (the scales, what the map shows).

    The window owns a :class:`Simulation` (the model) and a :class:`SimulationRunner`, which
    advances it in real time. The widgets only display the model and pass on what the user
    asks for. ``clock`` supplies real time in seconds; tests pass their own.
    """

    def __init__(
        self,
        initial_solar_masses: float = 10.0,
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Black Hole Physics Lab")
        self.resize(1440, 800)
        self.setMinimumSize(1250, 640)  # narrower than this, the map's heading is clipped

        self.controls = MassControls(initial_solar_masses)
        self.view_options = ViewOptions()
        self._black_hole = BlackHole.from_solar_masses(self.controls.mass())

        self.view = BlackHoleView(self._black_hole)
        self.setCentralWidget(self.view)

        self.scales = ScalesPanel()
        self.scales.set_black_hole(self._black_hole)

        self.simulation = Simulation()
        self.run_controls = RunControls(self._black_hole)
        self.runner = SimulationRunner(
            self.simulation, speed=self.run_controls.speed(), clock=clock, parent=self
        )
        self.particle_form = ParticleForm()

        self._add_dock(
            "controlDock",
            Qt.DockWidgetArea.LeftDockWidgetArea,
            _side_panel("controlPanel", 300, self.controls, self.particle_form),
        )
        self._add_dock(
            "scalesDock",
            Qt.DockWidgetArea.RightDockWidgetArea,
            _side_panel("infoPanel", 380, self.scales, self.view_options),
        )
        # The run controls sit under the map only: the side panels keep the full height.
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self._add_dock("runDock", Qt.DockWidgetArea.BottomDockWidgetArea, self.run_controls)

        self.cursor_label = QLabel(CURSOR_HINT)
        self.cursor_label.setTextFormat(Qt.TextFormat.RichText)
        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.addWidget(self.cursor_label, 1)
        status.addPermanentWidget(QLabel("G = c = 1   ·   lengths in GM/c²   ·   times in GM/c³"))
        status.addPermanentWidget(QLabel(f"Black Hole Physics Lab {__version__}"))

        self.controls.mass_changed.connect(self._on_mass_changed)
        self.view_options.reference_toggled.connect(self.view.set_reference_visible)
        self.view_options.grid_toggled.connect(self.view.set_grid_visible)
        self.view.cursor_moved.connect(self._on_cursor_moved)
        self.view.cursor_left.connect(self._on_cursor_left)

        self.run_controls.play_toggled.connect(self.runner.set_running)
        self.run_controls.step_requested.connect(self.runner.step)
        self.run_controls.reset_requested.connect(self.runner.reset)
        self.run_controls.speed_changed.connect(self.runner.set_speed)
        self.runner.running_changed.connect(self.run_controls.set_running)
        self.runner.changed.connect(self._show_simulation)
        self.particle_form.add_requested.connect(self._on_add_requested)

        self._show_simulation()

    @property
    def black_hole(self) -> BlackHole:
        """The black hole currently shown."""
        return self._black_hole

    def closeEvent(self, event: QCloseEvent) -> None:
        self.runner.set_running(False)  # no timer may outlive the window
        super().closeEvent(event)

    def _add_dock(self, object_name: str, area: Qt.DockWidgetArea, panel: QWidget) -> None:
        dock = QDockWidget(self)
        dock.setObjectName(object_name)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget(dock))  # the panels carry their own headings
        dock.setWidget(panel)
        self.addDockWidget(area, dock)

    def _on_mass_changed(self, solar_masses: float) -> None:
        # The simulation runs in units of GM/c² and GM/c³, so the motion does not change with
        # the mass. Only the physical sizes and times on display do.
        self._black_hole = BlackHole.from_solar_masses(solar_masses)
        self.scales.set_black_hole(self._black_hole)
        self.view.set_black_hole(self._black_hole)
        self.run_controls.set_black_hole(self._black_hole)

    def _on_cursor_moved(self, x: float, y: float) -> None:
        self.cursor_label.setText(describe_cursor(x, y, self._black_hole))

    def _on_cursor_left(self) -> None:
        self.cursor_label.setText(CURSOR_HINT)

    def _on_add_requested(self, x: float, y: float, vx: float, vy: float) -> None:
        try:
            particle = self.simulation.add_particle(x, y, vx, vy)
        except ValueError as error:
            self.particle_form.show_error(str(error))
            return
        self.particle_form.show_info(
            f"Added particle {particle.id + 1} at r = {format_number(math.hypot(x, y))} GM/c², "
            f"speed {format_number(math.hypot(vx, vy))} c."
        )
        self._show_simulation()

    def _show_simulation(self) -> None:
        """Bring the map, the clock and the particle summary up to date with the simulation."""
        particles = self.simulation.particles
        self.view.set_particles(
            [(particle.state[0], particle.state[1]) for particle in particles],
            [particle_colour(particle.id) for particle in particles],
            [particle.is_stopped for particle in particles],
        )
        self.run_controls.set_time(self.simulation.time)
        self.run_controls.set_behind(self.runner.is_behind)
        self.particle_form.set_summary(describe_particles(particles, self.simulation.stop_radius))
