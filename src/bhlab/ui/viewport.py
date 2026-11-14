"""The 2D view of the black hole's surroundings.

The view is a map of the orbital plane seen from above, drawn in units of the gravitational
radius r_g = GM/c². Every length of the problem is proportional to the mass, so the picture is
the same for every black hole; only the physical size shown by the scale bar changes.

What the map is not: a picture of what a camera would record. It shows Schwarzschild
coordinates, in which a circle of radius r has circumference 2πr. Light bending, which makes
the black hole's shadow look about 2.6 times larger than its horizon, belongs to a later stage.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, QPointF, Qt, Signal
from PySide6.QtGui import QFont, QFontMetricsF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bhlab.ui.scale_bar import ScaleBar
from bhlab.ui.theme import BACKGROUND, BLUE, BORDER, MUTED, ORANGE, PURPLE
from bhlab.units import HORIZON_RADIUS_RG, ISCO_RADIUS_RG, PHOTON_SPHERE_RADIUS_RG, BlackHole

_HORIZON_LABEL_WIDTH = 88.0  # pixels; the label is centred inside the disc

_PARTICLE_SIZE = 10  # pixels across a particle's dot
_STOPPED_SIZE = 12  # pixels across the cross that marks a stopped particle

# The longest label the y axis can show. Within the zoom and pan limits of this view, pyqtgraph
# never prints more than a sign, six digits and a decimal point (tests/test_viewport.py checks).
_WIDEST_TICK_LABEL = "-88888.8"


@dataclass(frozen=True)
class ReferenceCircle:
    """A circle of fixed radius, in units of r_g, drawn for orientation."""

    key: str
    name: str
    radius: float
    colour: str
    toggleable: bool
    min_pixels_per_unit: float  # the label is hidden once the view is zoomed out past this
    tooltip: str


EVENT_HORIZON = ReferenceCircle(
    key="event_horizon",
    name="Event horizon",
    radius=HORIZON_RADIUS_RG,
    colour=ORANGE,
    toggleable=False,
    # The label sits inside the disc, so the disc has to be wide enough to hold it.
    min_pixels_per_unit=(_HORIZON_LABEL_WIDTH + 8.0) / (2.0 * HORIZON_RADIUS_RG),
    tooltip="The surface of no return, at 2 GM/c² for a non-rotating black hole.",
)
PHOTON_SPHERE = ReferenceCircle(
    key="photon_sphere",
    name="Photon sphere",
    radius=PHOTON_SPHERE_RADIUS_RG,
    colour=PURPLE,
    toggleable=True,
    min_pixels_per_unit=16.0,
    tooltip=(
        "The radius at which light can circle the black hole, 3 GM/c². "
        "A result of general relativity, shown for orientation."
    ),
)
ISCO = ReferenceCircle(
    key="isco",
    name="ISCO",
    radius=ISCO_RADIUS_RG,
    colour=BLUE,
    toggleable=True,
    min_pixels_per_unit=4.0,
    tooltip=(
        "Innermost stable circular orbit, 6 GM/c². In general relativity no circular orbit "
        "inside it is stable. Newtonian gravity has no such limit."
    ),
)
REFERENCE_CIRCLES: tuple[ReferenceCircle, ...] = (EVENT_HORIZON, PHOTON_SPHERE, ISCO)


class _PlotWidget(pg.PlotWidget):
    """A plot widget that also reports when the mouse leaves it."""

    mouse_left = Signal()

    def leaveEvent(self, event: QEvent) -> None:
        self.mouse_left.emit()
        super().leaveEvent(event)


class BlackHoleView(QWidget):
    """Top-down map of the black hole with pan, zoom, reference circles and a scale bar.

    Drag with the left mouse button to pan and turn the wheel to zoom about the cursor.
    Positions are in units of r_g; the aspect ratio is locked, so circles stay circles.
    """

    cursor_moved = Signal(float, float)
    """Emitted with the cursor position (x, y) in units of r_g while it is over the map."""

    cursor_left = Signal()
    """Emitted when the cursor leaves the map."""

    DEFAULT_HALF_EXTENT = 10.0  # r_g from the centre to the nearer edge after a reset
    ZOOM_STEP = 1.5  # factor applied by one click on a zoom button
    MIN_SPAN = 0.5  # the view cannot show less than this many r_g across
    MAX_EXTENT = 1.0e6  # the view cannot leave |x|, |y| <= this many r_g

    _GRID_OPACITY = 0.32

    def __init__(self, black_hole: BlackHole, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("viewPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._black_hole = black_hole
        self._visible = {circle.key: True for circle in REFERENCE_CIRCLES}
        self._grid_visible = True

        # --- heading and camera buttons -------------------------------------------------
        title = QLabel("ORBITAL PLANE")
        title.setObjectName("sectionLabel")
        caption = QLabel(
            "seen from above &nbsp;·&nbsp; distances in units of r<sub>g</sub> = GM/c²"
        )
        caption.setObjectName("viewCaption")
        caption.setTextFormat(Qt.TextFormat.RichText)

        self.zoom_out_button = self._camera_button("−", "Zoom out (or turn the mouse wheel)")
        self.zoom_in_button = self._camera_button("+", "Zoom in (or turn the mouse wheel)")
        self.reset_button = self._camera_button(
            "Reset view", f"Show the region within {self.DEFAULT_HALF_EXTENT:g} r_g again"
        )
        self.zoom_out_button.clicked.connect(lambda: self.zoom_by(1.0 / self.ZOOM_STEP))
        self.zoom_in_button.clicked.connect(lambda: self.zoom_by(self.ZOOM_STEP))
        self.reset_button.clicked.connect(self.reset_view)

        header = QHBoxLayout()
        header.setContentsMargins(18, 14, 14, 6)
        header.setSpacing(10)
        header.addWidget(title)
        header.addWidget(caption)
        header.addStretch(1)
        header.addWidget(self.zoom_out_button)
        header.addWidget(self.zoom_in_button)
        header.addWidget(self.reset_button)

        # --- the map --------------------------------------------------------------------
        self.plot = _PlotWidget(background=BACKGROUND)
        self.plot.setAntialiasing(True)
        self.plot_item = self.plot.getPlotItem()
        self.view_box = self.plot_item.getViewBox()
        self.view_box.setAspectLocked(True, ratio=1.0)
        self.view_box.setLimits(
            xMin=-self.MAX_EXTENT,
            xMax=self.MAX_EXTENT,
            yMin=-self.MAX_EXTENT,
            yMax=self.MAX_EXTENT,
            minXRange=self.MIN_SPAN,
            minYRange=self.MIN_SPAN,
        )
        # Room for the tick labels that sit exactly on the top and right edges.
        self.plot_item.setContentsMargins(4, 10, 14, 2)
        self.plot_item.setMenuEnabled(False)
        self.plot_item.hideButtons()
        self.plot_item.showGrid(x=True, y=True, alpha=self._GRID_OPACITY)
        tick_font = QFont("Segoe UI", 8)
        for side, text in (("bottom", "x"), ("left", "y")):
            axis = self.plot_item.getAxis(side)
            axis.enableAutoSIPrefix(False)
            # pyqtgraph draws the grid as part of the axes and, by default, on top of the map.
            # Put the axes underneath, so that grid lines never cross a particle or the horizon.
            axis.setZValue(self.view_box.zValue() - 1.0)
            axis.setPen(pg.mkPen(BORDER))
            axis.setTextPen(pg.mkPen(MUTED))
            axis.setTickFont(tick_font)
            self.plot_item.setLabel(
                side, f"{text} &nbsp;(r<sub>g</sub>)", **{"color": MUTED, "font-size": "9pt"}
            )
        # pyqtgraph makes the left axis as wide as its longest tick label. The map would then
        # change size, and with it the scale, whenever panning or zooming changes the number
        # of digits. Reserve the width of the longest possible label instead, and keep it.
        label_width = QFontMetricsF(tick_font).horizontalAdvance(_WIDEST_TICK_LABEL)
        self.plot_item.getAxis("left").setStyle(
            autoExpandTextSpace=False, tickTextWidth=math.ceil(label_width)
        )

        self._circles: dict[str, QGraphicsEllipseItem] = {}
        self._labels: dict[str, pg.TextItem] = {}
        for circle in REFERENCE_CIRCLES:
            self._add_reference_circle(circle)

        # Particles: dots of a fixed size on screen, drawn above everything else on the map.
        self._particle_points: tuple[tuple[float, float], ...] = ()
        self._particle_stopped: tuple[bool, ...] = ()
        self._particles = pg.ScatterPlotItem(pxMode=True)
        self._particles.setZValue(20)
        self.plot_item.addItem(self._particles, ignoreBounds=True)

        self.scale_bar = ScaleBar(self.plot)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self.plot, 1)

        self.view_box.sigRangeChanged.connect(self._refresh_overlays)
        self.view_box.sigResized.connect(self._refresh_overlays)
        self.plot.scene().sigMouseMoved.connect(self._on_scene_mouse_moved)
        self.plot.mouse_left.connect(self.cursor_left)

        self.reset_view()

    # --- camera -------------------------------------------------------------------------

    def reset_view(self) -> None:
        """Centre on the black hole and show at least ±DEFAULT_HALF_EXTENT in both directions."""
        extent = self.DEFAULT_HALF_EXTENT
        self.view_box.setRange(xRange=(-extent, extent), yRange=(-extent, extent), padding=0.0)

    def zoom_by(self, factor: float) -> None:
        """Zoom about the centre of the view. ``factor`` > 1 zooms in, < 1 zooms out."""
        if not factor > 0.0:
            raise ValueError(f"The zoom factor must be positive; got {factor!r}")
        self.view_box.scaleBy((1.0 / factor, 1.0 / factor))

    def view_range(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """The visible region as ((x_min, x_max), (y_min, y_max)), in units of r_g."""
        (x_min, x_max), (y_min, y_max) = self.view_box.viewRange()
        return (x_min, x_max), (y_min, y_max)

    def pixels_per_unit(self) -> float | None:
        """Screen pixels per r_g, or None while the view has no size yet."""
        if self.view_box.width() <= 0 or self.view_box.height() <= 0:
            return None
        try:
            pixel_width, _pixel_height = self.view_box.viewPixelSize()
        except (TypeError, AttributeError):  # pyqtgraph has no transform before first layout
            return None
        return 1.0 / pixel_width if pixel_width > 0.0 else None

    # --- content ------------------------------------------------------------------------

    def set_black_hole(self, black_hole: BlackHole) -> None:
        """Use ``black_hole`` for physical sizes. The map itself does not depend on the mass."""
        self._black_hole = black_hole
        self._refresh_overlays()

    def set_reference_visible(self, key: str, visible: bool) -> None:
        """Show or hide the reference circle called ``key`` together with its label."""
        self._visible[key] = visible
        self._circles[key].setVisible(visible)
        self._refresh_overlays()

    def reference_visible(self, key: str) -> bool:
        """Whether the reference circle called ``key`` is switched on."""
        return self._visible[key]

    def circle_visible(self, key: str) -> bool:
        """Whether the circle of ``key`` is actually drawn."""
        return self._circles[key].isVisible()

    def label_visible(self, key: str) -> bool:
        """Whether the label of ``key`` is drawn (it hides when zoomed far out)."""
        return self._labels[key].isVisible()

    def circle_radius(self, key: str) -> float:
        """Radius, in r_g, of the circle actually drawn for ``key``."""
        rect = self._circles[key].rect()
        return rect.width() / 2.0

    def set_grid_visible(self, visible: bool) -> None:
        """Show or hide the coordinate grid."""
        self._grid_visible = visible
        self.plot_item.showGrid(x=visible, y=visible, alpha=self._GRID_OPACITY)

    def grid_visible(self) -> bool:
        """Whether the coordinate grid is switched on."""
        return self._grid_visible

    def set_particles(
        self,
        positions: Sequence[tuple[float, float]],
        colours: Sequence[str],
        stopped: Sequence[bool],
    ) -> None:
        """Draw one mark per particle at ``positions``, in units of r_g.

        A moving particle is a dot in its colour; a stopped one is a cross in the same colour,
        so that its state does not depend on colour alone. Each dot has a thin ring in the
        background colour, which keeps overlapping particles apart.
        """
        if not (len(positions) == len(colours) == len(stopped)):
            raise ValueError("positions, colours and stopped must have one entry per particle")
        self._particle_points = tuple((float(x), float(y)) for x, y in positions)
        self._particle_stopped = tuple(bool(flag) for flag in stopped)
        if not self._particle_points:
            self._particles.clear()
            return
        ring = pg.mkPen(BACKGROUND, width=2)
        self._particles.setData(
            pos=np.array(self._particle_points),
            symbol=["x" if flag else "o" for flag in self._particle_stopped],
            size=[_STOPPED_SIZE if flag else _PARTICLE_SIZE for flag in self._particle_stopped],
            brush=[pg.mkBrush(colour) for colour in colours],
            # The ring in the background colour would thin a cross out, so a cross is outlined
            # in its own colour.
            pen=[
                pg.mkPen(colour, width=2) if flag else ring
                for colour, flag in zip(colours, self._particle_stopped, strict=True)
            ],
        )

    def particle_points(self) -> tuple[tuple[float, float], ...]:
        """The map positions of the particles drawn, in units of r_g."""
        return self._particle_points

    def particle_stopped(self) -> tuple[bool, ...]:
        """For each particle drawn, whether it is drawn as stopped."""
        return self._particle_stopped

    # --- internals ----------------------------------------------------------------------

    def _camera_button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("viewButton")
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _add_reference_circle(self, circle: ReferenceCircle) -> None:
        radius = circle.radius
        item = QGraphicsEllipseItem(-radius, -radius, 2.0 * radius, 2.0 * radius)
        label = pg.TextItem()
        label.setFont(QFont("Segoe UI", 8))
        if circle is EVENT_HORIZON:
            item.setPen(pg.mkPen(circle.colour, width=1.6))
            item.setBrush(pg.mkBrush("#000000"))
            item.setZValue(10)
            label.setAnchor((0.5, 0.5))
            label.setHtml(
                f'<div style="text-align:center; color:{circle.colour};">{circle.name}<br>'
                f"{radius:g} r<sub>g</sub></div>"
            )
            label.setTextWidth(_HORIZON_LABEL_WIDTH)
            label.setPos(0.0, 0.0)
            label.setZValue(11)
        else:
            item.setPen(pg.mkPen(circle.colour, width=1.4, style=Qt.PenStyle.DashLine))
            # Sit just above the top of the circle.
            label.setAnchor((0.5, 1.15))
            label.setHtml(
                f'<span style="color:{circle.colour};">{circle.name} &nbsp;·&nbsp; '
                f"{radius:g} r<sub>g</sub></span>"
            )
            label.setPos(0.0, radius)
            label.setZValue(5)
        self.plot_item.addItem(item, ignoreBounds=True)
        self.plot_item.addItem(label, ignoreBounds=True)
        self._circles[circle.key] = item
        self._labels[circle.key] = label

    def _refresh_overlays(self, *_args: object) -> None:
        pixels_per_unit = self.pixels_per_unit()
        if pixels_per_unit is None:
            return
        area = self.view_box.sceneBoundingRect()
        self.scale_bar.update_scale(pixels_per_unit, area.width(), self._black_hole)
        corner = self.plot.mapFromScene(area.bottomLeft())
        self.scale_bar.move(corner.x() + 18, corner.y() - self.scale_bar.height() - 14)
        for circle in REFERENCE_CIRCLES:
            self._labels[circle.key].setVisible(
                self._visible[circle.key] and pixels_per_unit >= circle.min_pixels_per_unit
            )

    def _on_scene_mouse_moved(self, scene_position: QPointF) -> None:
        if self.view_box.sceneBoundingRect().contains(scene_position):
            point = self.view_box.mapSceneToView(scene_position)
            self.cursor_moved.emit(point.x(), point.y())
        else:
            self.cursor_left.emit()
