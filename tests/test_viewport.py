"""The 2D map: what is drawn, how the camera behaves, the scale bar and the cursor readout.

These tests run on Qt's offscreen platform (see conftest.py), so no window appears.
"""

import math

import pytest
from helpers import click, type_mass
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDockWidget

from bhlab.formatting import format_length_auto
from bhlab.ui.main_window import CURSOR_HINT, describe_cursor
from bhlab.ui.scale_bar import ScaleBar, nice_length
from bhlab.ui.viewport import REFERENCE_CIRCLES, BlackHoleView
from bhlab.units import HORIZON_RADIUS_RG, ISCO_RADIUS_RG, PHOTON_SPHERE_RADIUS_RG, BlackHole


def spans(view):
    """Width and height of the visible region, in r_g."""
    (x_min, x_max), (y_min, y_max) = view.view_range()
    return x_max - x_min, y_max - y_min


def centre(view):
    (x_min, x_max), (y_min, y_max) = view.view_range()
    return (x_min + x_max) / 2.0, (y_min + y_max) / 2.0


def hover(view, x, y):
    """Report the mouse at the map position (x, y), the way pyqtgraph does."""
    view.plot.scene().sigMouseMoved.emit(view.view_box.mapViewToScene(QPointF(x, y)))


def pixel_of(view, x, y):
    """The whole pixel of the plot widget that shows the map position (x, y)."""
    return view.plot.mapFromScene(view.view_box.mapViewToScene(QPointF(x, y)))


def map_position_at(view, pixel):
    point = view.view_box.mapSceneToView(view.plot.mapToScene(pixel))
    return point.x(), point.y()


def turn_wheel(view, notches, pixel):
    """Turn the mouse wheel by ``notches`` clicks (positive = away from the user) over ``pixel``."""
    viewport = view.plot.viewport()
    event = QWheelEvent(
        QPointF(pixel),
        QPointF(viewport.mapToGlobal(pixel)),
        QPoint(0, 0),
        QPoint(0, 120 * notches),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(viewport, event)


def map_area(view):
    """Width and height of the map on screen, in pixels. The axes are not part of it."""
    return view.view_box.width(), view.view_box.height()


def let_the_layout_settle(qapp):
    """Paint the view, then give the layout the further passes in which it reacts."""
    for _ in range(5):
        qapp.processEvents()


# --- what is drawn ---------------------------------------------------------------------------


def test_circles_are_drawn_at_the_schwarzschild_radii(window):
    view = window.view
    assert view.circle_radius("event_horizon") == pytest.approx(HORIZON_RADIUS_RG)
    assert view.circle_radius("photon_sphere") == pytest.approx(PHOTON_SPHERE_RADIUS_RG)
    assert view.circle_radius("isco") == pytest.approx(ISCO_RADIUS_RG)
    assert (HORIZON_RADIUS_RG, PHOTON_SPHERE_RADIUS_RG, ISCO_RADIUS_RG) == (2.0, 3.0, 6.0)


def test_window_has_the_map_in_the_centre_and_a_panel_on_each_side(window):
    assert window.centralWidget() is window.view
    left = window.findChild(QDockWidget, "controlDock")
    right = window.findChild(QDockWidget, "scalesDock")
    assert window.dockWidgetArea(left) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(right) == Qt.DockWidgetArea.RightDockWidgetArea
    # Left: what the user sets up. Right: reference information and what the map shows.
    assert left.isAncestorOf(window.controls) and left.isAncestorOf(window.particle_form)
    assert right.isAncestorOf(window.scales) and right.isAncestorOf(window.view_options)
    assert window.scales.isVisible() and window.view.isVisible()


def test_run_controls_sit_under_the_map_and_nowhere_else(window):
    bar = window.findChild(QDockWidget, "runDock")
    assert window.dockWidgetArea(bar) == Qt.DockWidgetArea.BottomDockWidgetArea
    assert bar.isAncestorOf(window.run_controls) and window.run_controls.isVisible()
    # As wide as the map: the side panels keep the full height of the window.
    assert bar.width() == window.view.width()
    assert bar.geometry().top() >= window.view.geometry().bottom()


@pytest.mark.parametrize("size", [(1250, 640), (1440, 800)])
def test_side_panels_scroll_when_the_window_is_short_and_never_squash_their_text(
    window, qapp, size
):
    window.resize(*size)
    qapp.processEvents()
    for name in ("controlDock", "scalesDock"):
        scroll = window.findChild(QDockWidget, name).widget()
        panel = scroll.widget()
        needed = panel.layout().totalHeightForWidth(panel.width())
        assert panel.height() >= needed  # every section has the height its text needs
        assert scroll.verticalScrollBar().maximum() == max(0, needed - scroll.viewport().height())


def test_default_view_is_centred_on_the_black_hole_and_shows_every_reference_radius(window):
    view = window.view
    width, height = spans(view)
    assert centre(view) == pytest.approx((0.0, 0.0), abs=1e-9)
    assert min(width, height) / 2.0 == pytest.approx(view.DEFAULT_HALF_EXTENT, rel=1e-6)
    assert min(width, height) / 2.0 > ISCO_RADIUS_RG


def test_circles_stay_circular_whatever_the_window_shape(window, qapp):
    view = window.view
    for size in ((1440, 800), (1250, 700), (1700, 660)):
        window.resize(*size)
        qapp.processEvents()
        pixel_width, pixel_height = view.view_box.viewPixelSize()
        assert pixel_width == pytest.approx(pixel_height, rel=1e-9)
        assert view.pixels_per_unit() == pytest.approx(1.0 / pixel_width)


# --- camera ----------------------------------------------------------------------------------


def test_zoom_buttons_scale_the_view_by_the_zoom_step(window):
    view = window.view
    width, height = spans(view)
    click(view.zoom_in_button)
    assert spans(view) == pytest.approx((width / view.ZOOM_STEP, height / view.ZOOM_STEP))
    assert centre(view) == pytest.approx((0.0, 0.0), abs=1e-9)
    click(view.zoom_out_button)
    assert spans(view) == pytest.approx((width, height))
    click(view.zoom_out_button)
    assert spans(view) == pytest.approx((width * view.ZOOM_STEP, height * view.ZOOM_STEP))


def test_reset_restores_the_default_view(window):
    view = window.view
    initial = view.view_range()
    view.zoom_by(7.3)
    view.view_box.translateBy(x=4.0, y=-2.5)
    assert centre(view) == pytest.approx((4.0, -2.5))
    click(view.reset_button)
    assert view.view_range()[0] == pytest.approx(initial[0])
    assert view.view_range()[1] == pytest.approx(initial[1])


def test_zoom_stops_at_the_limits(window):
    view = window.view
    for _ in range(80):
        view.zoom_by(view.ZOOM_STEP)
    assert min(spans(view)) == pytest.approx(view.MIN_SPAN, rel=1e-6)
    for _ in range(120):
        view.zoom_by(1.0 / view.ZOOM_STEP)
    (x_min, x_max), (y_min, y_max) = view.view_range()
    assert max(-x_min, x_max, -y_min, y_max) == pytest.approx(view.MAX_EXTENT, rel=1e-6)
    pixel_width, pixel_height = view.view_box.viewPixelSize()
    assert pixel_width == pytest.approx(pixel_height, rel=1e-9)


@pytest.mark.parametrize("factor", [0.0, -1.0, math.nan])
def test_zoom_factor_must_be_positive(window, factor):
    with pytest.raises(ValueError):
        window.view.zoom_by(factor)


def test_mouse_wheel_zooms_about_the_cursor(window):
    view = window.view
    pixel = pixel_of(view, 5.0, 4.0)
    anchor = map_position_at(view, pixel)
    width, height = spans(view)

    turn_wheel(view, +1, pixel)
    zoomed_width, zoomed_height = spans(view)
    assert zoomed_width < width and zoomed_height < height
    assert zoomed_width / width == pytest.approx(zoomed_height / height)
    # The map point under the cursor has not moved.
    assert map_position_at(view, pixel) == pytest.approx(anchor, abs=1e-6)

    turn_wheel(view, -1, pixel)
    assert spans(view) == pytest.approx((width, height))
    assert map_position_at(view, pixel) == pytest.approx(anchor, abs=1e-6)


def test_dragging_with_the_left_button_pans_the_map(window, qapp):
    view = window.view
    viewport = view.plot.viewport()
    start = pixel_of(view, 0.0, 0.0)
    shift = QPoint(120, -45)
    width, height = spans(view)
    pixels_per_unit = view.pixels_per_unit()

    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
    for step in range(1, 7):  # several small moves, as a real drag produces
        QTest.mouseMove(viewport, start + shift * step / 6)
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=start + shift)
    qapp.processEvents()

    # Dragging the map 120 px right and 45 px up moves the view centre the opposite way.
    expected = (-shift.x() / pixels_per_unit, shift.y() / pixels_per_unit)
    assert centre(view) == pytest.approx(expected, abs=1.5 / pixels_per_unit)
    # Panning moves the map and does nothing else: the visible region keeps its size.
    assert spans(view) == pytest.approx((width, height))
    assert view.pixels_per_unit() == pytest.approx(pixels_per_unit)


@pytest.mark.parametrize(
    ("x", "y"),
    [(-4.0, 1.5), (30.0, -200.0), (500.0, 5000.0), (-3.0e4, -8.0e4), (9.0e5, -9.0e5)],
)
def test_panning_changes_neither_the_scale_nor_the_size_of_the_map(window, qapp, x, y):
    """Far from the centre the tick labels have more digits. The map must not give way to them."""
    view = window.view
    area, scale, visible = map_area(view), view.pixels_per_unit(), spans(view)

    view.view_box.translateBy(x=x, y=y)
    let_the_layout_settle(qapp)

    assert centre(view) == pytest.approx((x, y))
    assert map_area(view) == area
    assert spans(view) == pytest.approx(visible, rel=1e-9)
    # The scale is read back through the view transform, which loses digits far from the
    # origin (two numbers near 10⁶ are subtracted), hence the looser tolerance.
    assert view.pixels_per_unit() == pytest.approx(scale)


def test_zooming_does_not_change_the_size_of_the_map(window, qapp):
    view = window.view
    area = map_area(view)
    for factor in (900.0, 1.0 / 40.0, 1.0e-4):  # tick labels from 0.05 to 100000
        view.reset_view()
        view.zoom_by(factor)
        let_the_layout_settle(qapp)
        assert map_area(view) == area


def test_the_longest_tick_labels_fit_in_the_space_reserved_for_them(window, qapp):
    """The price of a fixed axis width: it has to be wide enough for the longest label."""
    view = window.view
    axis = view.plot_item.getAxis("left")
    reserved = axis.style["tickTextWidth"]
    # (y at the centre of the view, visible height): where the labels have the most characters.
    places = ((0.0, 20.0), (-9999.9, 0.5), (-99999.9, 0.5), (-88888.0, 20.0), (-999990.0, 20.0))
    for y, height in places:
        view.view_box.setRange(
            xRange=(-height / 2, height / 2), yRange=(y - height / 2, y + height / 2), padding=0.0
        )
        let_the_layout_settle(qapp)
        view.plot.grab()  # paint now, so that pyqtgraph measures the labels it draws
        assert axis.textWidth <= reserved, f"the labels near y = {y:g} need {axis.textWidth} px"


# --- the scale bar and scale invariance ------------------------------------------------------


@pytest.mark.parametrize(
    ("maximum", "expected"),
    [
        (1.0, 1.0),
        (1.9, 1.0),
        (2.0, 2.0),
        (4.99, 2.0),
        (5.0, 5.0),
        (9.99, 5.0),
        (10.0, 10.0),
        (0.2, 0.2),
        (0.03, 0.02),
        (1234.0, 1000.0),
        (2.5e6, 2.0e6),
        (7e-4, 5e-4),
    ],
)
def test_nice_length_is_the_largest_1_2_5_number_not_above_the_maximum(maximum, expected):
    assert nice_length(maximum) == pytest.approx(expected, rel=1e-12)
    assert nice_length(maximum) <= maximum * (1 + 1e-12)


@pytest.mark.parametrize("bad", [0.0, -3.0, math.inf, math.nan])
def test_nice_length_rejects_non_physical_lengths(bad):
    with pytest.raises(ValueError):
        nice_length(bad)


def test_scale_bar_is_a_round_length_that_fits_the_view(window):
    view = window.view
    bar = view.scale_bar
    for zoom in (1.0, 1.0 / 3.7, 1.0 / 40.0, 900.0, 11.0):
        view.reset_view()
        view.zoom_by(zoom)
        pixels_per_unit = view.pixels_per_unit()
        view_width = spans(view)[0] * pixels_per_unit
        mantissa = bar.length / 10.0 ** math.floor(math.log10(bar.length) + 1e-9)
        assert (
            mantissa == pytest.approx(1.0)
            or mantissa == pytest.approx(2.0)
            or (mantissa == pytest.approx(5.0))
        )
        assert bar.pixel_length == round(bar.length * pixels_per_unit)
        assert 0.1 * view_width - 1 <= bar.pixel_length <= bar.MAX_FRACTION * view_width + 1


def test_changing_the_mass_changes_the_scale_bar_but_not_the_map(window):
    view = window.view
    bar = view.scale_bar
    range_before = view.view_range()
    length, pixels = bar.length, bar.pixel_length
    small = BlackHole.from_solar_masses(10.0)
    assert (
        bar.text() == f"{length:g} r<sub>g</sub> = {format_length_auto(small.length_to_si(length))}"
    )

    type_mass(window, "4.3e6")

    large = BlackHole.from_solar_masses(4.3e6)
    assert view.view_range() == range_before
    assert (bar.length, bar.pixel_length) == (length, pixels)
    assert (
        bar.text() == f"{length:g} r<sub>g</sub> = {format_length_auto(large.length_to_si(length))}"
    )
    assert "AU" in bar.text() and "km" not in bar.text()


def test_scale_bar_text_at_extreme_zoom(qapp):
    bar = ScaleBar()
    ten_solar_masses = BlackHole.from_solar_masses(10.0)
    bar.update_scale(pixels_per_unit=1e-4, view_width=1000.0, black_hole=ten_solar_masses)
    assert bar.length == pytest.approx(2e6)
    assert bar.text() == "2 × 10⁶ r<sub>g</sub> = 0.1974 AU"
    bar.update_scale(pixels_per_unit=4000.0, view_width=1000.0, black_hole=ten_solar_masses)
    assert bar.length == pytest.approx(0.05)
    assert bar.text() == "0.05 r<sub>g</sub> = 738.3 m"


# --- the cursor readout ----------------------------------------------------------------------


def test_cursor_position_is_reported_in_cartesian_and_polar_form(window):
    hover(window.view, 3.0, 4.0)
    text = window.cursor_label.text()
    assert "x = 3.000 r<sub>g</sub>" in text
    assert "y = 4.000 r<sub>g</sub>" in text
    assert "r = 5.000 r<sub>g</sub> = 73.83 km" in text
    assert "φ = 53.1°" in text
    assert "inside the event horizon" not in text


def test_cursor_readout_uses_the_current_mass(window):
    type_mass(window, "4.3e6")
    hover(window.view, -6.0, 0.0)
    text = window.cursor_label.text()
    assert "r = 6.000 r<sub>g</sub> = 0.2547 AU" in text
    assert "φ = 180.0°" in text


def test_cursor_inside_the_event_horizon_is_flagged(window):
    hover(window.view, 1.0, 0.5)
    assert "inside the event horizon" in window.cursor_label.text()
    hover(window.view, 2.5, 0.0)
    assert "inside the event horizon" not in window.cursor_label.text()


def test_readout_returns_to_the_hint_when_the_mouse_leaves(window):
    hover(window.view, 3.0, 4.0)
    assert window.cursor_label.text() != CURSOR_HINT
    QApplication.sendEvent(window.view.plot, QEvent(QEvent.Type.Leave))
    assert window.cursor_label.text() == CURSOR_HINT


def test_mouse_over_the_axes_is_not_reported_as_a_map_position(window):
    hover(window.view, 3.0, 4.0)
    window.view.plot.scene().sigMouseMoved.emit(QPointF(2.0, 2.0))  # top-left corner: an axis
    assert window.cursor_label.text() == CURSOR_HINT


@pytest.mark.parametrize(
    ("x", "y", "angle"),
    [
        (1.0, 0.0, "φ = 0.0°"),
        (0.0, 1.0, "φ = 90.0°"),
        (-1.0, 0.0, "φ = 180.0°"),
        (0.0, -1.0, "φ = 270.0°"),
        (3.0, -3.0, "φ = 315.0°"),
        (1.0, -1e-9, "φ = 0.0°"),  # just below the +x axis: never printed as 360.0°
    ],
)
def test_describe_cursor_measures_the_angle_anticlockwise_from_the_x_axis(x, y, angle):
    assert angle in describe_cursor(x, y, BlackHole.from_solar_masses(10.0))


def test_describe_cursor_gives_the_radius_as_a_physical_length():
    m87 = BlackHole.from_solar_masses(6.5e9)
    assert "r = 10.00 r<sub>g</sub> = 641.6 AU" in describe_cursor(0.0, 10.0, m87)
    assert "r = 100.0 r<sub>g</sub> = 0.1015 ly" in describe_cursor(0.0, 100.0, m87)


# --- reference circles, labels and grid ------------------------------------------------------


def test_reference_circles_can_be_switched_off_and_on(window):
    view, boxes = window.view, window.view_options.reference_checkboxes
    assert view.reference_visible("photon_sphere") and view.label_visible("photon_sphere")

    boxes["photon_sphere"].click()
    assert not view.reference_visible("photon_sphere")
    assert not view.circle_visible("photon_sphere")
    assert not view.label_visible("photon_sphere")
    assert view.reference_visible("isco") and view.circle_visible("isco")

    boxes["photon_sphere"].click()
    assert view.reference_visible("photon_sphere") and view.label_visible("photon_sphere")

    boxes["isco"].click()
    assert not view.reference_visible("isco") and not view.label_visible("isco")


def test_the_event_horizon_cannot_be_switched_off(window):
    assert set(window.view_options.reference_checkboxes) == {"photon_sphere", "isco"}
    assert window.view.circle_visible("event_horizon")


def test_grid_can_be_switched_off_and_on(window):
    assert window.view.grid_visible()
    window.view_options.grid_checkbox.click()
    assert not window.view.grid_visible()
    window.view_options.grid_checkbox.click()
    assert window.view.grid_visible()


def test_labels_disappear_as_the_view_is_zoomed_out(window):
    view = window.view
    assert view.pixels_per_unit() > 24.0  # precondition: the default window is large enough
    assert all(view.label_visible(circle.key) for circle in REFERENCE_CIRCLES)
    seen_all_hidden = False
    for _ in range(8):
        view.zoom_by(1.0 / view.ZOOM_STEP)
        pixels_per_unit = view.pixels_per_unit()
        for circle in REFERENCE_CIRCLES:
            assert view.label_visible(circle.key) == (pixels_per_unit >= circle.min_pixels_per_unit)
        seen_all_hidden = not any(view.label_visible(circle.key) for circle in REFERENCE_CIRCLES)
    assert seen_all_hidden
    view.reset_view()
    assert all(view.label_visible(circle.key) for circle in REFERENCE_CIRCLES)


# --- particles on the map --------------------------------------------------------------------


def colour_at(view, x, y):
    """The colour of the screen pixel that shows the map position (x, y), as #rrggbb."""
    image = view.plot.grab().toImage()
    ratio = image.devicePixelRatio()
    pixel = pixel_of(view, x, y)
    return image.pixelColor(round(pixel.x() * ratio), round(pixel.y() * ratio)).name()


def test_particles_are_drawn_where_they_are_in_their_colours(window, qapp):
    view = window.view
    view.set_particles([(4.0, 3.0), (-5.0, -4.0)], ["#199e70", "#d95926"], [False, True])
    qapp.processEvents()
    assert view.particle_points() == ((4.0, 3.0), (-5.0, -4.0))
    assert view.particle_stopped() == (False, True)
    assert colour_at(view, 4.0, 3.0) == "#199e70"  # the centre of the dot
    assert colour_at(view, -5.0, -4.0) == "#d95926"  # the centre of the cross
    assert colour_at(view, 8.0, 8.0) not in ("#199e70", "#d95926")  # empty map


def test_particles_keep_their_size_on_screen_when_the_view_is_zoomed(window, qapp):
    view = window.view
    view.set_particles([(4.0, 3.0)], ["#199e70"], [False])
    view.zoom_by(1.0 / 20.0)  # 4 r_g is now a twentieth of the distance on screen
    qapp.processEvents()
    assert colour_at(view, 4.0, 3.0) == "#199e70"
    # The dot is 10 pixels across whatever the zoom: two pixels from its centre it is still
    # there, nine pixels away it is not.
    centre = pixel_of(view, 4.0, 3.0)
    image = view.plot.grab().toImage()
    ratio = image.devicePixelRatio()

    def colour_beside(pixels):
        return image.pixelColor(
            round((centre.x() + pixels) * ratio), round(centre.y() * ratio)
        ).name()

    assert colour_beside(2) == "#199e70"
    assert colour_beside(9) != "#199e70"


def test_no_particles_means_nothing_is_drawn(window, qapp):
    view = window.view
    view.set_particles([(4.0, 3.0)], ["#199e70"], [False])
    view.set_particles([], [], [])
    qapp.processEvents()
    assert view.particle_points() == () and view.particle_stopped() == ()
    assert colour_at(view, 4.0, 3.0) != "#199e70"


def test_particle_lists_must_match(window):
    with pytest.raises(ValueError):
        window.view.set_particles([(1.0, 2.0)], ["#199e70", "#d95926"], [False])


def test_view_can_be_used_on_its_own(qapp):
    """The map does not need the main window: it only needs a black hole."""
    view = BlackHoleView(BlackHole.from_solar_masses(1.0))
    view.resize(700, 600)
    view.show()
    qapp.processEvents()
    assert view.scale_bar.text().endswith("km")
    assert view.circle_radius("isco") == pytest.approx(ISCO_RADIUS_RG)
    view.close()
