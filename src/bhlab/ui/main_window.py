"""The main application window."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QLabel, QMainWindow, QWidget

from bhlab import __version__
from bhlab.ui.mass_controls import MassControls
from bhlab.ui.scales_panel import ScalesPanel
from bhlab.units import BlackHole


class MainWindow(QMainWindow):
    """Mass controls on the left, the characteristic scales of that mass in the centre."""

    def __init__(self, initial_solar_masses: float = 10.0) -> None:
        super().__init__()
        self.setWindowTitle("Black Hole Physics Lab")
        self.resize(1180, 690)
        self.setMinimumSize(980, 600)

        self.scales = ScalesPanel()
        self.setCentralWidget(self.scales)

        self.controls = MassControls(initial_solar_masses)
        dock = QDockWidget("Black hole", self)
        dock.setObjectName("blackHoleDock")
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget(dock))  # the panel carries its own heading
        dock.setWidget(self.controls)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.addWidget(
            QLabel("Geometrized units: G = c = 1   ·   lengths in GM/c²   ·   times in GM/c³")
        )
        status.addPermanentWidget(QLabel(f"Black Hole Physics Lab {__version__}"))

        self._black_hole = BlackHole.from_solar_masses(self.controls.mass())
        self.scales.set_black_hole(self._black_hole)
        self.controls.mass_changed.connect(self._on_mass_changed)

    @property
    def black_hole(self) -> BlackHole:
        """The black hole currently shown."""
        return self._black_hole

    def _on_mass_changed(self, solar_masses: float) -> None:
        self._black_hole = BlackHole.from_solar_masses(solar_masses)
        self.scales.set_black_hole(self._black_hole)
