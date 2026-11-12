"""Left-hand panel section: what the map shows."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from bhlab.ui.viewport import REFERENCE_CIRCLES

_NOTE = (
    "The circles are reference radii from general relativity, drawn for orientation. "
    "The view is a map in Schwarzschild coordinates, not what a camera would see."
)


class ViewOptions(QWidget):
    """Check boxes for the reference circles and the grid. They double as the colour legend."""

    reference_toggled = Signal(str, bool)
    """Emitted with the key of a reference circle and whether it should be shown."""

    grid_toggled = Signal(bool)
    """Emitted when the coordinate grid is switched on or off."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        section = QLabel("VIEW")
        section.setObjectName("sectionLabel")

        self.reference_checkboxes: dict[str, QCheckBox] = {}
        for circle in REFERENCE_CIRCLES:
            if not circle.toggleable:
                continue
            checkbox = QCheckBox(f"{circle.name}  ·  {circle.radius:g} GM/c²")
            checkbox.setChecked(True)
            checkbox.setToolTip(circle.tooltip)
            # The filled box takes the colour of the circle it controls.
            checkbox.setStyleSheet(
                "QCheckBox::indicator:checked "
                f"{{ background: {circle.colour}; border: 1px solid {circle.colour}; }}"
            )
            checkbox.toggled.connect(
                lambda checked, key=circle.key: self.reference_toggled.emit(key, checked)
            )
            self.reference_checkboxes[circle.key] = checkbox

        self.grid_checkbox = QCheckBox("Coordinate grid")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.setToolTip("Grid lines at round values of x and y, in units of GM/c².")
        self.grid_checkbox.toggled.connect(self.grid_toggled)

        note = QLabel(_NOTE)
        note.setObjectName("note")
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section)
        layout.addSpacing(2)
        for checkbox in self.reference_checkboxes.values():
            layout.addWidget(checkbox)
        layout.addWidget(self.grid_checkbox)
        layout.addSpacing(6)
        layout.addWidget(note)
