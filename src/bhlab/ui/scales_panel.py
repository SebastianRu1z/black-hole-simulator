"""Central panel: the characteristic scales of the chosen black hole, each with its formula."""

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from bhlab.formatting import (
    format_length_au,
    format_length_si,
    format_mass_si,
    format_mass_solar,
    format_time_convenient,
    format_time_si,
)
from bhlab.ui.theme import MUTED
from bhlab.units import BlackHole


@dataclass(frozen=True)
class ScaleRow:
    """One line of the table: what the quantity is and how to compute and display it."""

    key: str
    name: str
    detail: str
    formula: str  # Qt rich text
    tooltip: str
    si: Callable[[BlackHole], str]
    convenient: Callable[[BlackHole], str]


ROWS: tuple[ScaleRow, ...] = (
    ScaleRow(
        key="mass",
        name="Mass",
        detail="sets every other scale in this table",
        formula="<i>M</i>",
        tooltip=(
            "The value in kilograms uses Newton's constant G, which is only known to about "
            "2 parts in 100 000. Every other row depends on the mass through the product GM, "
            "which is known far more precisely, so those rows do not inherit that uncertainty."
        ),
        si=lambda bh: format_mass_si(bh.mass_kg),
        convenient=lambda bh: format_mass_solar(bh.mass_solar),
    ),
    ScaleRow(
        key="gravitational_radius",
        name="Gravitational radius",
        detail="the unit of length in the simulation",
        formula="<i>r</i><sub>g</sub> = <i>GM</i> / <i>c</i><sup>2</sup>",
        tooltip=(
            "The natural length scale of the black hole. All distances in the simulation are "
            "measured in multiples of this radius."
        ),
        si=lambda bh: format_length_si(bh.length_unit),
        convenient=lambda bh: format_length_au(bh.length_unit),
    ),
    ScaleRow(
        key="event_horizon",
        name="Event horizon",
        detail="Schwarzschild radius",
        formula="<i>r</i><sub>s</sub> = 2<i>GM</i> / <i>c</i><sup>2</sup>",
        tooltip=(
            "The surface of no return: nothing that crosses it, not even light, can come back "
            "out. Exact for a non-rotating black hole."
        ),
        si=lambda bh: format_length_si(bh.schwarzschild_radius),
        convenient=lambda bh: format_length_au(bh.schwarzschild_radius),
    ),
    ScaleRow(
        key="photon_sphere",
        name="Photon sphere",
        detail="where light can circle the black hole",
        formula="<i>r</i><sub>ph</sub> = 3<i>GM</i> / <i>c</i><sup>2</sup>",
        tooltip=(
            "The radius at which light can travel in a circle around the black hole. The orbit "
            "is unstable: the slightest disturbance sends the light inward or outward."
        ),
        si=lambda bh: format_length_si(bh.photon_sphere_radius),
        convenient=lambda bh: format_length_au(bh.photon_sphere_radius),
    ),
    ScaleRow(
        key="isco",
        name="Innermost stable circular orbit",
        detail="ISCO",
        formula="<i>r</i><sub>ISCO</sub> = 6<i>GM</i> / <i>c</i><sup>2</sup>",
        tooltip=(
            "Inside this radius no circular orbit of a massive particle is stable, so matter "
            "spirals in. It sets the inner edge of a thin accretion disc."
        ),
        si=lambda bh: format_length_si(bh.isco_radius),
        convenient=lambda bh: format_length_au(bh.isco_radius),
    ),
    ScaleRow(
        key="time_unit",
        name="Time unit",
        detail="light-travel time across one gravitational radius",
        formula="<i>t</i><sub>g</sub> = <i>GM</i> / <i>c</i><sup>3</sup>",
        tooltip=(
            "The time light needs to travel one gravitational radius. All times in the "
            "simulation are measured in multiples of it."
        ),
        si=lambda bh: format_time_si(bh.time_unit),
        convenient=lambda bh: format_time_convenient(bh.time_unit),
    ),
)

_NOTE = (
    "Every length and time in this table is proportional to the mass. That is why the simulation "
    "works in geometrized units (G = c = 1), with lengths in r<sub>g</sub>, times in "
    "t<sub>g</sub> and speeds as fractions of c: one numerical solution then describes a black "
    "hole of any mass. The three radii are exact results of general relativity for a "
    "non-rotating black hole."
)


class ScalesPanel(QWidget):
    """A table of the black hole's characteristic scales that follows the chosen mass."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("centralPanel")
        # A plain QWidget only paints a style-sheet background if this attribute is set.
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        title = QLabel("Characteristic scales")
        title.setObjectName("pageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(24, 18, 24, 18)
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(11)
        for column, stretch in enumerate((5, 4, 3, 3)):
            grid.setColumnStretch(column, stretch)

        for column, heading in enumerate(("QUANTITY", "FORMULA", "SI UNITS", "CONVENIENT UNITS")):
            header = QLabel(heading)
            header.setObjectName("columnHeader")
            grid.addWidget(header, 0, column)

        self._values: dict[str, tuple[QLabel, QLabel]] = {}
        for index, row in enumerate(ROWS):
            separator = QFrame()
            separator.setObjectName("rowSeparator")
            grid.addWidget(separator, 2 * index + 1, 0, 1, 4)

            name = QLabel(
                f'{row.name}<br><span style="color:{MUTED}; font-size:9pt;">{row.detail}</span>'
            )
            name.setObjectName("quantityName")
            formula = QLabel(row.formula)
            formula.setObjectName("formula")
            si_value = QLabel()
            si_value.setObjectName("valueSi")
            convenient_value = QLabel()
            convenient_value.setObjectName("valueConvenient")

            for column, label in enumerate((name, formula, si_value, convenient_value)):
                label.setTextFormat(
                    Qt.TextFormat.RichText if column < 2 else Qt.TextFormat.PlainText
                )
                label.setToolTip(row.tooltip)
                grid.addWidget(label, 2 * index + 2, column)
            for label in (si_value, convenient_value):
                # Let the numbers be selected and copied.
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._values[row.key] = (si_value, convenient_value)

        note = QLabel(_NOTE)
        note.setObjectName("note")
        note.setTextFormat(Qt.TextFormat.RichText)
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 24)
        layout.setSpacing(4)
        layout.addWidget(title)
        layout.addWidget(self.subtitle)
        layout.addSpacing(16)
        layout.addWidget(card)
        layout.addSpacing(14)
        layout.addWidget(note)
        layout.addStretch(1)

    def set_black_hole(self, black_hole: BlackHole) -> None:
        """Recompute every row for ``black_hole``."""
        self.subtitle.setText(
            f"Non-rotating (Schwarzschild) black hole of {format_mass_solar(black_hole.mass_solar)}"
        )
        for row in ROWS:
            si_label, convenient_label = self._values[row.key]
            si_label.setText(row.si(black_hole))
            convenient_label.setText(row.convenient(black_hole))

    def value_text(self, key: str) -> tuple[str, str]:
        """The displayed (SI, convenient) text of the row called ``key``."""
        si_label, convenient_label = self._values[key]
        return si_label.text(), convenient_label.text()
