"""Right-hand panel section: following one particle and everything that follows from its state.

The numbers come from :func:`bhlab.simulation.tracking.track`; this module only lays them out,
in the simulation's units (GM/c², GM/c³, c) with the SI value for the chosen mass underneath.
While the simulation runs, the numbers change on every frame. They are redrawn at most ten times
a second, which is as fast as anyone can read them.
"""

import math
import time
from collections.abc import Callable, Sequence

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bhlab.constants import C
from bhlab.formatting import format_length_auto, format_number, format_time_convenient
from bhlab.simulation.model import Particle
from bhlab.simulation.tracking import Tracking, track
from bhlab.ui.theme import particle_colour, set_style_flag
from bhlab.units import BlackHole

FATE_TEXT = {
    "bound": "Bound orbit",
    "escapes": "Escapes",
    "reaches stop radius": "Will reach r = 2 and stop",
    "stopped": "Stopped at r = 2",
}

RELIABILITY_TEXT = {
    "good": "good",
    "approximate": "approximate",
    "rough": "rough guide only",
}

# (key, name, tooltip): one row of the details grid each.
ROWS: tuple[tuple[str, str, str], ...] = (
    ("fate", "Status", "What the particle will do, from its energy and closest approach."),
    (
        "reliability",
        "Newton's theory here",
        "Relativity changes Newton's numbers by about GM/(rc²) and v²/c². Good below 1 %, "
        "approximate below 10 %, beyond that only a rough guide. Stage 2 replaces Newton.",
    ),
    ("r", "Distance r", "Distance from the centre of the black hole."),
    ("angle", "Direction φ", "Angle anticlockwise from the +x axis."),
    ("speed", "Speed", "How fast it moves."),
    ("radial", "Moving", "The part of the velocity towards or away from the black hole."),
    ("circular", "Circular speed here", "v = √(GM/r): the speed of a circular orbit at this r."),
    ("escape", "Escape speed here", "v = √(2GM/r): the least speed that never comes back."),
    ("ratio", "Speed ÷ escape speed", "Below 1 the particle is bound; 1 or more, it escapes."),
    (
        "energy",
        "Energy E",
        "E = v²/2 − GM/r per unit mass. Negative: bound. Zero or more: escapes.",
    ),
    ("angular", "Angular momentum L", "L = x v_y − y vₓ per unit mass. Constant along the orbit."),
    ("eccentricity", "Eccentricity e", "0 circle, below 1 ellipse, 1 parabola, above 1 hyperbola."),
    ("semi_major", "Semi-major axis a", "Half the longest diameter of the ellipse."),
    ("periapsis", "Closest approach", "Periapsis: the smallest distance on this orbit."),
    ("apoapsis", "Farthest point", "Apoapsis: the largest distance; infinite if it escapes."),
    ("period", "Period", "Time for one orbit: T = 2π √(a³/GM)."),
    ("next_periapsis", "Next closest approach in", "Time until the next periapsis (Kepler)."),
)

_EMPTY_HINT = "Click a particle on the map or in this list to follow it."


def _dot_icon(colour: str) -> QIcon:
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(colour))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, 10, 10)
    painter.end()
    return QIcon(pixmap)


def describe_tracking(t: Tracking, black_hole: BlackHole) -> dict[str, tuple[str, str]]:
    """The text of every row: (value in the simulation's units, value in SI or a remark)."""

    def length(value: float) -> tuple[str, str]:
        if math.isinf(value):
            return "∞", ""
        return f"{format_number(value)} GM/c²", format_length_auto(black_hole.length_to_si(value))

    def duration(value: float | None, missing: str) -> tuple[str, str]:
        if value is None or math.isinf(value):
            return missing, ""
        return f"{format_number(value)} GM/c³", format_time_convenient(black_hole.time_to_si(value))

    def speed(value: float) -> tuple[str, str]:
        return f"{format_number(value)} c", f"{format_number(value * C / 1000.0)} km/s"

    elements = t.elements
    if abs(t.radial_speed) < 1e-12 * max(t.speed, 1e-300):
        radial = ("sideways", "neither in nor out")
    else:
        direction = "outward" if t.radial_speed > 0 else "inward"
        radial = (f"{direction} {format_number(abs(t.radial_speed))} c", "")
    correction = max(1.0 / t.r, t.speed * t.speed)
    semi_major: tuple[str, str]
    if elements.kind == "bound":
        semi_major = length(elements.semi_major_axis)
    elif elements.kind == "parabolic":
        semi_major = ("∞", "parabola")
    else:
        semi_major = (f"{format_number(elements.semi_major_axis)} GM/c²", "negative: hyperbola")
    return {
        "fate": (FATE_TEXT[t.fate], ""),
        "r": length(t.r),
        "angle": (f"{t.angle:.1f}°", ""),
        "speed": speed(t.speed),
        "radial": radial,
        "circular": speed(t.circular_speed),
        "escape": speed(t.escape_speed),
        "ratio": (
            format_number(t.speed_over_escape),
            "bound" if t.speed_over_escape < 1 else "escapes",
        ),
        "energy": (
            f"{format_number(elements.energy)} c²",
            f"{format_number(elements.energy * C * C)} J/kg",
        ),
        "angular": (
            f"{format_number(elements.angular_momentum)} GM/c",
            f"{format_number(elements.angular_momentum * black_hole.gm / C)} m²/s",
        ),
        # Below CIRCULAR_ECCENTRICITY the orbit is a circle to within rounding (e ≈ 2e-16).
        "eccentricity": ("0", "circular")
        if elements.periapsis_angle is None
        else (format_number(elements.eccentricity), ""),
        "semi_major": semi_major,
        "periapsis": length(elements.periapsis),
        "apoapsis": length(elements.apoapsis) if elements.kind == "bound" else ("∞", "escapes"),
        "period": duration(elements.period, "none: it escapes"),
        "next_periapsis": duration(
            t.time_to_periapsis,
            "circular orbit" if elements.periapsis_angle is None and t.fate == "bound" else "—",
        ),
        "reliability": (
            RELIABILITY_TEXT[t.reliability],
            f"corrections ≈ {format_number(100.0 * correction, sig=2)} %",
        ),
    }


class TrackerPanel(QWidget):
    """A list of the particles, and live numbers for the one selected."""

    particle_chosen = Signal(int)
    """Emitted with a particle's number when the user picks it in the list."""

    REFRESH_SECONDS = 0.1

    def __init__(
        self, *, clock: Callable[[], float] = time.perf_counter, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._clock = clock
        self._last_refresh = -math.inf
        self._ids: tuple[int, ...] = ()
        self._selected: int | None = None

        section = QLabel("TRACKER")
        section.setObjectName("sectionLabel")

        self.particle_list = QListWidget()
        self.particle_list.setObjectName("particleList")
        self.particle_list.setIconSize(QSize(12, 12))
        self.particle_list.setMaximumHeight(118)
        self.particle_list.itemClicked.connect(self._on_item_clicked)

        self.title_label = QLabel(_EMPTY_HINT)
        self.title_label.setObjectName("pageSubtitle")
        self.title_label.setWordWrap(True)

        self._details = QFrame()
        grid = QGridLayout(self._details)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(3)
        grid.setColumnStretch(0, 1)
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        self._values: dict[str, tuple[QLabel, QLabel]] = {}
        for row, (key, name, tooltip) in enumerate(ROWS):
            name_label = QLabel(name)
            name_label.setObjectName("trackerName")
            value = QLabel()
            value.setObjectName("trackerValue")
            remark = QLabel()
            remark.setObjectName("trackerRemark")
            for label in (name_label, value, remark):
                label.setToolTip(tooltip)
            for label in (value, remark):
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(name_label, 2 * row, 0)
            grid.addWidget(value, 2 * row, 1, right)
            grid.addWidget(remark, 2 * row + 1, 1, right)
            self._values[key] = (value, remark)
        self._details.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(section)
        layout.addWidget(self.particle_list)
        layout.addWidget(self.title_label)
        layout.addWidget(self._details)

    # --- public interface ---------------------------------------------------------------

    def show_particles(
        self,
        particles: Sequence[Particle],
        selected: int | None,
        black_hole: BlackHole,
        stop_radius: float,
        *,
        force: bool = False,
    ) -> None:
        """Bring the list and the numbers up to date.

        While the simulation runs the numbers are redrawn at most every REFRESH_SECONDS; ``force``
        redraws them at once, as does any change to the list or the selection.
        """
        ids = tuple(particle.id for particle in particles)
        changed = ids != self._ids or selected != self._selected
        now = self._clock()
        if not (force or changed or now - self._last_refresh >= self.REFRESH_SECONDS):
            return
        self._last_refresh = now
        if ids != self._ids:
            self._rebuild_list(particles)
        self._selected = selected

        self.particle_list.blockSignals(True)
        trackings = {p.id: track(p.state, stop_radius, stopped=p.is_stopped) for p in particles}
        for row, particle_id in enumerate(ids):
            item = self.particle_list.item(row)
            item.setText(f"Particle {particle_id + 1}  ·  {FATE_TEXT[trackings[particle_id].fate]}")
            item.setSelected(particle_id == selected)
        self.particle_list.blockSignals(False)

        if selected is None or selected not in trackings:
            self.title_label.setText(_EMPTY_HINT if particles else "No particles yet.")
            self._details.hide()
            return
        self.title_label.setText(f"Particle {selected + 1}")
        texts = describe_tracking(trackings[selected], black_hole)
        for key, (value, remark) in texts.items():
            value_label, remark_label = self._values[key]
            value_label.setText(value)
            remark_label.setText(remark)
            remark_label.setVisible(bool(remark))
        reliability = trackings[selected].reliability
        set_style_flag(self._values["reliability"][0], "error", reliability == "rough")
        self._details.show()

    def value_text(self, key: str) -> tuple[str, str]:
        """The (value, remark) shown in the row ``key``."""
        value, remark = self._values[key]
        return value.text(), remark.text()

    def details_visible(self) -> bool:
        return not self._details.isHidden()

    def listed_ids(self) -> tuple[int, ...]:
        return self._ids

    # --- internals ----------------------------------------------------------------------

    def _rebuild_list(self, particles: Sequence[Particle]) -> None:
        self.particle_list.blockSignals(True)
        self.particle_list.clear()
        for particle in particles:
            item = QListWidgetItem(_dot_icon(particle_colour(particle.id)), "")
            item.setData(Qt.ItemDataRole.UserRole, particle.id)
            self.particle_list.addItem(item)
        self.particle_list.blockSignals(False)
        self._ids = tuple(particle.id for particle in particles)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.particle_chosen.emit(int(item.data(Qt.ItemDataRole.UserRole)))
