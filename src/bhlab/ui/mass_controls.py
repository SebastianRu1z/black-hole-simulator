"""Left-hand panel: choosing the black hole's mass.

The mass can be typed (applied with Enter), dragged on a logarithmic slider, or picked from
presets. Text that is not a positive, finite number is reported and never applied.
"""

import math
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from bhlab.constants import GM_SUN
from bhlab.formatting import format_mass_solar


@dataclass(frozen=True)
class MassPreset:
    """A named black hole mass offered as a one-click choice."""

    label: str
    solar_masses: float
    tooltip: str


PRESETS: tuple[MassPreset, ...] = (
    MassPreset(
        "Stellar-mass black hole",
        10.0,
        "A typical black hole left behind by a massive star: about ten solar masses.",
    ),
    MassPreset(
        "Sagittarius A*",
        4.3e6,
        "The black hole at the centre of the Milky Way, about 4.3 million solar masses "
        "(GRAVITY Collaboration 2022).",
    ),
    MassPreset(
        "M87*",
        6.5e9,
        "The black hole imaged by the Event Horizon Telescope, about 6.5 billion solar masses "
        "(Event Horizon Telescope Collaboration 2019).",
    ),
)


_HELP_TEXT = "Type a mass and press Enter, drag the slider, or pick a preset."


def parse_mass_text(text: str) -> float:
    """Convert what the user typed into a mass in solar masses.

    Raises
    ------
    ValueError
        With a message written for the user, if the text is not a positive, finite number.
        A decimal comma is rejected rather than guessed at, because "4,3" and "4.3" would
        otherwise silently mean different masses on different computers.
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Enter a mass, for example 10 or 4.3e6.")
    if "," in cleaned:
        raise ValueError("Use a point for decimals and no thousands separators, for example 4.3e6.")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"“{cleaned}” is not a number. Try 10 or 4.3e6.") from None
    if math.isnan(value) or math.isinf(value) or math.isinf(value * GM_SUN):
        raise ValueError("The mass must be a finite number.")
    if value <= 0.0:
        raise ValueError("The mass must be greater than zero.")
    return value


def mass_to_text(solar_masses: float) -> str:
    """Compact text for the input field: 10, 0.5, 4.3e6."""
    text = f"{solar_masses:.6g}"
    if "e" in text:
        mantissa, exponent = text.split("e")
        text = f"{mantissa}e{int(exponent)}"
    return text


class MassControls(QFrame):
    """Controls for the black hole mass, in solar masses."""

    mass_changed = Signal(float)
    """Emitted with the new mass in solar masses whenever a valid mass is applied."""

    LOG10_MIN = 0.0
    LOG10_MAX = 11.0
    STEPS_PER_DECADE = 100

    def __init__(self, initial_solar_masses: float = 10.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("controlPanel")
        self.setFixedWidth(310)
        self._mass = parse_mass_text(repr(float(initial_solar_masses)))

        section = QLabel("BLACK HOLE")
        section.setObjectName("sectionLabel")

        field_label = QLabel("Mass")
        field_label.setObjectName("fieldLabel")

        self.mass_edit = QLineEdit()
        self.mass_edit.setToolTip(
            "Mass of the black hole in solar masses. Type a positive number and press Enter. "
            "Scientific notation such as 4.3e6 works."
        )
        unit = QLabel("M☉")
        unit.setObjectName("unitLabel")
        unit.setToolTip("M☉ is the mass of the Sun, about 1.988 × 10³⁰ kg.")
        field_row = QHBoxLayout()
        field_row.setSpacing(8)
        field_row.addWidget(self.mass_edit, 1)
        field_row.addWidget(unit)

        # One line of help that turns into the error message when the typed text is invalid.
        self._error = ""
        self.message_label = QLabel(_HELP_TEXT)
        self.message_label.setObjectName("helperLabel")
        self.message_label.setWordWrap(True)
        self.message_label.setMinimumHeight(66)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(
            round(self.LOG10_MIN * self.STEPS_PER_DECADE),
            round(self.LOG10_MAX * self.STEPS_PER_DECADE),
        )
        self.slider.setPageStep(self.STEPS_PER_DECADE)
        self.slider.setToolTip(
            "Logarithmic scale from 1 to 10¹¹ solar masses. "
            "Masses outside this range can still be typed."
        )
        slider_low = QLabel("1 M☉")
        slider_low.setObjectName("sliderEnd")
        slider_high = QLabel("10¹¹ M☉")
        slider_high.setObjectName("sliderEnd")
        slider_ends = QHBoxLayout()
        slider_ends.addWidget(slider_low)
        slider_ends.addStretch(1)
        slider_ends.addWidget(slider_high)

        presets_label = QLabel("PRESETS")
        presets_label.setObjectName("sectionLabel")
        self.preset_buttons: list[QPushButton] = []
        for preset in PRESETS:
            button = QPushButton(
                f"{preset.label}    {format_mass_solar(preset.solar_masses, sig=2)}"
            )
            button.setCheckable(True)
            button.setToolTip(preset.tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, m=preset.solar_masses: self.set_mass(m))
            self.preset_buttons.append(button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(8)
        layout.addWidget(section)
        layout.addSpacing(6)
        layout.addWidget(field_label)
        layout.addLayout(field_row)
        layout.addWidget(self.slider)
        layout.addLayout(slider_ends)
        layout.addSpacing(4)
        layout.addWidget(self.message_label)
        layout.addWidget(presets_label)
        layout.addSpacing(2)
        for button in self.preset_buttons:
            layout.addWidget(button)
        layout.addStretch(1)

        self.mass_edit.editingFinished.connect(self._on_editing_finished)
        self.slider.valueChanged.connect(self._on_slider_changed)

        self._refresh(update_text=True, update_slider=True)

    # --- public interface ---------------------------------------------------------------

    def mass(self) -> float:
        """The current valid mass in solar masses."""
        return self._mass

    def error_text(self) -> str:
        """The error message on display, or an empty string when the input is valid."""
        return self._error

    def set_mass(self, solar_masses: float) -> None:
        """Apply a mass in solar masses; raises ValueError if it is not positive and finite."""
        mass = parse_mass_text(repr(float(solar_masses)))
        self._apply(mass, update_text=True, update_slider=True)

    # --- reactions to the user ----------------------------------------------------------

    def _on_editing_finished(self) -> None:
        try:
            mass = parse_mass_text(self.mass_edit.text())
        except ValueError as error:
            self._show_error(f"{error} The table still shows {mass_to_text(self._mass)} M☉.")
            return
        if mass == self._mass and not self.error_text():
            return
        self._apply(mass, update_text=False, update_slider=True)

    def _on_slider_changed(self, position: int) -> None:
        # Round to three significant figures so the slider lands on readable masses.
        mass = float(f"{10.0 ** (position / self.STEPS_PER_DECADE):.3g}")
        self._apply(mass, update_text=True, update_slider=False)

    # --- internals ----------------------------------------------------------------------

    def _apply(self, mass: float, *, update_text: bool, update_slider: bool) -> None:
        self._mass = mass
        self._refresh(update_text=update_text, update_slider=update_slider)
        self.mass_changed.emit(mass)

    def _refresh(self, *, update_text: bool, update_slider: bool) -> None:
        if update_text:
            self.mass_edit.setText(mass_to_text(self._mass))
        if update_slider:
            log_mass = min(max(math.log10(self._mass), self.LOG10_MIN), self.LOG10_MAX)
            self.slider.blockSignals(True)
            self.slider.setValue(round(log_mass * self.STEPS_PER_DECADE))
            self.slider.blockSignals(False)
        for button, preset in zip(self.preset_buttons, PRESETS, strict=True):
            button.setChecked(math.isclose(self._mass, preset.solar_masses, rel_tol=1e-9))
        self._show_error("")

    def _show_error(self, message: str) -> None:
        self._error = message
        self.message_label.setText(message or _HELP_TEXT)
        for widget, flag in ((self.mass_edit, "invalid"), (self.message_label, "error")):
            widget.setProperty(flag, bool(message))
            # A style sheet rule that depends on a property is only re-evaluated on a re-polish.
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
