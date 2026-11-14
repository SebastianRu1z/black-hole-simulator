"""Right-hand panel section: adding a particle by typing its starting position and velocity.

The form only reads numbers. Whether they make a valid particle (outside the stop radius,
slower than light) is decided by the simulation, and its answer is shown here.
"""

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bhlab.formatting import format_number
from bhlab.physics.newtonian import circular_velocity
from bhlab.ui.theme import set_style_flag

_HELP_TEXT = (
    "Position in GM/c², velocity as a fraction of c. “Circular speed” fills in the velocity "
    "of the circular orbit through the position."
)


def parse_number(text: str, name: str) -> float:
    """Convert what the user typed for the quantity ``name`` into a number.

    Raises ValueError with a message written for the user. As for the mass, a decimal comma is
    rejected and not guessed at.
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError(f"Enter a number for {name}.")
    if "," in cleaned:
        raise ValueError(f"Use a point for decimals in {name}, for example 0.25.")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"“{cleaned}” is not a number (in {name}).") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    return value


def _unbreakable(text: str) -> str:
    """``text`` with GM/c² and GM/c³ kept in one piece when a label wraps its lines.

    A line may otherwise break after the slash. The word joiner (U+2060) is invisible and
    forbids a break where it stands.
    """
    return text.replace("GM/c", "GM/\u2060c")


def number_to_text(value: float) -> str:
    """Text for a field: ten significant digits, enough to keep a circular orbit circular."""
    return f"{value:.10g}"


class ParticleForm(QWidget):
    """Fields for x, y, vₓ and v_y, a helper for the circular speed, and an Add button."""

    add_requested = Signal(float, float, float, float)
    """Emitted with (x, y, vₓ, v_y) when the user asks for a particle and all four are numbers."""

    FIELDS = ("x", "y", "vx", "vy")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        section = QLabel("PARTICLES")
        section.setObjectName("sectionLabel")

        # A circular orbit at r = 10 as the first suggestion.
        defaults = dict(zip(self.FIELDS, (10.0, 0.0, *circular_velocity(10.0, 0.0)), strict=True))
        captions = {"x": "x", "y": "y", "vx": "v<sub>x</sub>", "vy": "v<sub>y</sub>"}
        self.edits: dict[str, QLineEdit] = {}
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for index, name in enumerate(self.FIELDS):
            row, pair = divmod(index, 2)
            caption = QLabel(captions[name])
            caption.setTextFormat(Qt.TextFormat.RichText)
            edit = QLineEdit(number_to_text(defaults[name]))
            edit.setObjectName("stateField")
            self.edits[name] = edit
            grid.addWidget(caption, row, 3 * pair)
            grid.addWidget(edit, row, 3 * pair + 1)
        grid.setColumnMinimumWidth(2, 10)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(4, 1)
        self.edits["x"].setToolTip("Starting position along x, in GM/c²")
        self.edits["y"].setToolTip("Starting position along y, in GM/c²")
        self.edits["vx"].setToolTip("Starting velocity along x, as a fraction of c")
        self.edits["vy"].setToolTip("Starting velocity along y, as a fraction of c")

        self.circular_button = self._button(
            "Circular speed",
            "Fill in the velocity of the anticlockwise circular orbit through (x, y): v = √(1/r)",
        )
        self.add_button = self._button("Add particle", "Add a particle that starts now")
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.circular_button)
        buttons.addWidget(self.add_button)
        buttons.addStretch(1)

        # One line of help that turns into the error message, as for the mass.
        self._error = ""
        self.message_label = QLabel(_HELP_TEXT)
        self.message_label.setObjectName("helperLabel")
        self.message_label.setWordWrap(True)
        self.message_label.setMinimumHeight(52)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.summary_label = QLabel("No particles yet.")
        self.summary_label.setObjectName("note")
        self.summary_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section)
        layout.addSpacing(2)
        layout.addLayout(grid)
        layout.addLayout(buttons)
        layout.addWidget(self.message_label)
        layout.addWidget(self.summary_label)

        self.circular_button.clicked.connect(self._on_circular_clicked)
        self.add_button.clicked.connect(self._on_add_clicked)

    # --- public interface ---------------------------------------------------------------

    def error_text(self) -> str:
        """The error message on display, or an empty string."""
        return self._error

    def show_error(self, message: str) -> None:
        """Show ``message`` as an error, for example the simulation's reason for a refusal."""
        self._show(message, error=True)

    def show_info(self, message: str) -> None:
        """Show ``message`` as information, replacing any error."""
        self._show(message, error=False)

    def set_summary(self, text: str) -> None:
        """Show ``text`` under the form: how many particles there are and what they are doing."""
        text = _unbreakable(text)
        if text != self.summary_label.text():
            self.summary_label.setText(text)

    # --- internals ----------------------------------------------------------------------

    def _button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("formButton")
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _read(self, names: tuple[str, ...]) -> list[float] | None:
        """The numbers typed into the fields ``names``, or None after showing what is wrong."""
        for edit in self.edits.values():
            set_style_flag(edit, "invalid", False)
        values = []
        for name in names:
            try:
                values.append(parse_number(self.edits[name].text(), name))
            except ValueError as error:
                set_style_flag(self.edits[name], "invalid", True)
                self.show_error(str(error))
                return None
        return values

    def _on_circular_clicked(self) -> None:
        position = self._read(("x", "y"))
        if position is None:
            return
        x, y = position
        if x == 0.0 and y == 0.0:
            self.show_error("There is no circular orbit through the centre, r = 0.")
            return
        vx, vy = circular_velocity(x, y)
        self.edits["vx"].setText(number_to_text(vx))
        self.edits["vy"].setText(number_to_text(vy))
        self.show_info(
            f"Circular speed at r = {format_number(math.hypot(x, y))}: "
            f"{format_number(math.hypot(vx, vy))} c, anticlockwise."
        )

    def _on_add_clicked(self) -> None:
        values = self._read(self.FIELDS)
        if values is not None:
            self.add_requested.emit(*values)

    def _show(self, message: str, *, error: bool) -> None:
        self._error = message if error else ""
        self.message_label.setText(_unbreakable(message or _HELP_TEXT))
        set_style_flag(self.message_label, "error", error)
