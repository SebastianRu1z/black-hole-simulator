"""The main application window."""

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QFrame, QLabel, QMainWindow, QVBoxLayout, QWidget

from bhlab import __version__
from bhlab.formatting import format_length_auto, format_number
from bhlab.ui.mass_controls import MassControls
from bhlab.ui.scales_panel import ScalesPanel
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


def _side_panel(object_name: str, width: int, *sections: QWidget) -> QFrame:
    """A fixed-width panel holding ``sections`` from the top down."""
    panel = QFrame()
    panel.setObjectName(object_name)
    panel.setFixedWidth(width)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(20, 22, 20, 20)
    layout.setSpacing(22)
    for section in sections:
        layout.addWidget(section)
    layout.addStretch(1)
    return panel


class MainWindow(QMainWindow):
    """Controls on the left, the map of the black hole in the centre, its scales on the right."""

    def __init__(self, initial_solar_masses: float = 10.0) -> None:
        super().__init__()
        self.setWindowTitle("Black Hole Physics Lab")
        self.resize(1440, 800)
        self.setMinimumSize(1200, 640)

        self.controls = MassControls(initial_solar_masses)
        self.view_options = ViewOptions()
        self._black_hole = BlackHole.from_solar_masses(self.controls.mass())

        self.view = BlackHoleView(self._black_hole)
        self.setCentralWidget(self.view)

        self.scales = ScalesPanel()
        self.scales.set_black_hole(self._black_hole)

        self._add_dock(
            "controlDock",
            Qt.DockWidgetArea.LeftDockWidgetArea,
            _side_panel("controlPanel", 300, self.controls, self.view_options),
        )
        self._add_dock(
            "scalesDock",
            Qt.DockWidgetArea.RightDockWidgetArea,
            _side_panel("infoPanel", 380, self.scales),
        )

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

    @property
    def black_hole(self) -> BlackHole:
        """The black hole currently shown."""
        return self._black_hole

    def _add_dock(self, object_name: str, area: Qt.DockWidgetArea, panel: QWidget) -> None:
        dock = QDockWidget(self)
        dock.setObjectName(object_name)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget(dock))  # the panels carry their own headings
        dock.setWidget(panel)
        self.addDockWidget(area, dock)

    def _on_mass_changed(self, solar_masses: float) -> None:
        self._black_hole = BlackHole.from_solar_masses(solar_masses)
        self.scales.set_black_hole(self._black_hole)
        self.view.set_black_hole(self._black_hole)

    def _on_cursor_moved(self, x: float, y: float) -> None:
        self.cursor_label.setText(describe_cursor(x, y, self._black_hole))

    def _on_cursor_left(self) -> None:
        self.cursor_label.setText(CURSOR_HINT)
