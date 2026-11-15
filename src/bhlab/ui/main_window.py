"""The main application window."""

import math
import time
from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
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
from bhlab.simulation.placement import Preview, drag_velocity, preview
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


def describe_preview(placement: Preview, stop_radius: float) -> str:
    """What a particle with the previewed starting state would do, in a sentence or two."""
    if placement.error is not None:
        return placement.error
    elements = placement.elements
    assert elements is not None  # a valid preview always has its orbit
    start = (
        f"r = {format_number(math.hypot(placement.x, placement.y))}, speed "
        f"{format_number(placement.speed)} c ({format_number(placement.speed_over_circular)} × "
        "circular). "
    )
    periapsis = f"periapsis {format_number(elements.periapsis)} GM/c²"
    if elements.kind == "bound":
        orbit = (
            f"Bound orbit, e = {format_number(elements.eccentricity)}, {periapsis}, apoapsis "
            f"{format_number(elements.apoapsis)} GM/c²."
        )
    elif elements.kind == "parabolic":
        orbit = f"Parabolic: it only just escapes, {periapsis}."
    else:
        orbit = f"Unbound: it escapes, e = {format_number(elements.eccentricity)}, {periapsis}."
    if placement.reaches_stop_radius:
        orbit += f" It will come down to r = {stop_radius:g} and stop there."
    return start + orbit


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
        self.particle_form.remove_requested.connect(self._remove_selected)
        self.view.placement_moved.connect(self._on_placement_moved)
        self.view.placement_finished.connect(self._on_placement_finished)
        self.view.map_clicked.connect(self._on_map_clicked)
        # A line edit with the focus keeps Delete for its own text; elsewhere it removes.
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.delete_shortcut.activated.connect(self._remove_selected)

        self._selected_id: int | None = None
        self._shown_ids: tuple[int, ...] = ()

        self._show_simulation()

    @property
    def black_hole(self) -> BlackHole:
        """The black hole currently shown."""
        return self._black_hole

    @property
    def selected_id(self) -> int | None:
        """The number of the selected particle, or None."""
        return self._selected_id

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

    def _placement_preview(self, x: float, y: float, dx: float, dy: float) -> Preview:
        try:
            vx, vy = drag_velocity(x, y, dx, dy)
        except ValueError as error:  # pressed exactly on r = 0
            return Preview(x, y, 0.0, 0.0, str(error), None, False)
        return preview(self.simulation, x, y, vx, vy)

    def _on_placement_moved(self, x: float, y: float, dx: float, dy: float) -> None:
        placement = self._placement_preview(x, y, dx, dy)
        self.view.set_placement_valid(placement.is_valid)
        text = describe_preview(placement, self.simulation.stop_radius)
        if placement.is_valid:
            self.particle_form.show_info(text)
        else:
            self.particle_form.show_error(text)

    def _on_placement_finished(self, x: float, y: float, dx: float, dy: float) -> None:
        placement = self._placement_preview(x, y, dx, dy)
        if not placement.is_valid:
            self.particle_form.show_error(
                f"Nothing added. {describe_preview(placement, self.simulation.stop_radius)}"
            )
            return
        particle = self.simulation.add_particle(x, y, placement.vx, placement.vy)
        self.particle_form.set_fields(x, y, placement.vx, placement.vy)
        self.particle_form.show_info(
            f"Added particle {particle.id + 1}. "
            f"{describe_preview(placement, self.simulation.stop_radius)}"
        )
        self._show_simulation()

    def _on_map_clicked(self, x: float, y: float) -> None:
        if self.view.place_mode:
            self.particle_form.show_info(
                "Place mode: press where the particle should start and drag an arrow for its "
                "velocity. A click alone adds nothing."
            )
            return
        index = self.view.particle_index_at(x, y)
        self._select(None if index is None else self._shown_ids[index])

    def _select(self, particle_id: int | None) -> None:
        self._selected_id = particle_id
        self.particle_form.set_remove_enabled(particle_id is not None)
        if particle_id is not None:
            particle = next(p for p in self.simulation.particles if p.id == particle_id)
            x, y, vx, vy = (float(value) for value in particle.state)
            self.particle_form.set_fields(x, y, vx, vy)
            state = "stopped" if particle.is_stopped else "now"
            self.particle_form.show_info(
                f"Particle {particle_id + 1} selected; the fields show its state {state}. "
                "Remove it with Remove or Delete."
            )
        self._show_simulation()

    def _remove_selected(self) -> None:
        if self._selected_id is None:
            return
        removed = self._selected_id
        self.simulation.remove_particle(removed)
        self._selected_id = None
        self.particle_form.set_remove_enabled(False)
        self.particle_form.show_info(f"Removed particle {removed + 1}.")
        self._show_simulation()

    def _show_simulation(self) -> None:
        """Bring the map, the clock and the particle summary up to date with the simulation."""
        particles = self.simulation.particles
        self._shown_ids = tuple(particle.id for particle in particles)
        selected = (
            self._shown_ids.index(self._selected_id)
            if self._selected_id in self._shown_ids
            else None
        )
        self.view.set_particles(
            [(particle.state[0], particle.state[1]) for particle in particles],
            [particle_colour(particle.id) for particle in particles],
            [particle.is_stopped for particle in particles],
            selected,
        )
        self.run_controls.set_time(self.simulation.time)
        self.run_controls.set_behind(self.runner.is_behind)
        self.particle_form.set_summary(describe_particles(particles, self.simulation.stop_radius))
