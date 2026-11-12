"""The scale bar drawn over the view: a round length in r_g together with its physical size."""

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QLabel, QWidget

from bhlab.formatting import format_length_auto, format_number
from bhlab.ui.theme import TEXT
from bhlab.units import BlackHole


def nice_length(maximum: float) -> float:
    """The largest length of the form 1, 2 or 5 × 10ⁿ that does not exceed ``maximum``."""
    if not (math.isfinite(maximum) and maximum > 0.0):
        raise ValueError(f"maximum must be a positive, finite number; got {maximum!r}")
    exponent = math.floor(math.log10(maximum))
    fraction = maximum / 10.0**exponent
    # log10 can land a hair on the wrong side of a power of ten; bring the fraction into [1, 10).
    if fraction < 1.0:
        exponent -= 1
        fraction *= 10.0
    elif fraction >= 10.0:
        exponent += 1
        fraction /= 10.0
    tolerance = 1.0 - 1e-12
    step = 5.0 if fraction >= 5.0 * tolerance else 2.0 if fraction >= 2.0 * tolerance else 1.0
    return step * 10.0**exponent


def _round_number_text(value: float) -> str:
    """Text for a 1-2-5 number: 0.05, 2, 500, and 2 × 10⁵ once plain digits get long."""
    if 1e-3 <= value < 1e5:
        return f"{value:g}"
    return format_number(value, sig=1)


class ScaleBar(QWidget):
    """A bar of round length in r_g, labelled with that length and its physical size.

    The picture of a black hole in units of r_g is the same for every mass. This bar is where
    the mass shows: its length in r_g follows the zoom, its physical size follows the mass.

    The widget is an overlay: it sits on top of the view and lets mouse events through.
    """

    MAX_FRACTION = 0.25  # the bar is never longer than this fraction of the view's width

    _BAR_SPACE = 12  # pixels reserved under the label for the bar itself

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._label = QLabel(self)
        self._label.setObjectName("scaleBarLabel")
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._length = 1.0
        self._pixels = 1

    @property
    def length(self) -> float:
        """Length of the bar in units of r_g."""
        return self._length

    @property
    def pixel_length(self) -> int:
        """Length of the bar on screen, in pixels."""
        return self._pixels

    def text(self) -> str:
        """The label, as Qt rich text."""
        return self._label.text()

    def update_scale(
        self, pixels_per_unit: float, view_width: float, black_hole: BlackHole
    ) -> None:
        """Choose the bar for a view ``view_width`` pixels wide at ``pixels_per_unit``."""
        self._length = nice_length(self.MAX_FRACTION * view_width / pixels_per_unit)
        self._pixels = max(round(self._length * pixels_per_unit), 1)
        physical = format_length_auto(black_hole.length_to_si(self._length))
        self._label.setText(f"{_round_number_text(self._length)} r<sub>g</sub> = {physical}")
        self._label.adjustSize()
        self.setFixedSize(
            max(self._pixels + 2, self._label.width()), self._label.height() + self._BAR_SPACE
        )
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setPen(QPen(QColor(TEXT), 2))
        baseline = self.height() - 3
        painter.drawLine(1, baseline, self._pixels, baseline)
        painter.drawLine(1, baseline - 6, 1, baseline)
        painter.drawLine(self._pixels, baseline - 6, self._pixels, baseline)
        painter.end()
