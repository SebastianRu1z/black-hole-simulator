"""Placing, selecting and removing particles with the mouse, in the window.

The mouse is driven with QTest on Qt's offscreen platform (see conftest.py). A pixel maps to a
map point only to within a pixel, so the expected values are read back from the pixels used.
"""

import math

import pytest
from helpers import FakeClock, click, fill_particle_form, run_for
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from bhlab.simulation.model import Simulation
from bhlab.simulation.placement import drag_velocity, preview
from bhlab.ui.main_window import MainWindow, describe_preview


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def lab(qapp, clock):
    window = MainWindow(clock=clock)
    window.show()
    qapp.processEvents()
    yield window
    window.close()


def pixel_of(view, x, y):
    return view.plot.mapFromScene(view.view_box.mapViewToScene(QPointF(x, y)))


def map_position_at(view, pixel):
    point = view.view_box.mapSceneToView(view.plot.mapToScene(pixel))
    return point.x(), point.y()


def drag(view, start, end, *, release=True, steps=6):
    """Press at pixel ``start``, move to ``end`` in small steps and (optionally) release."""
    viewport = view.plot.viewport()
    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
    for step in range(1, steps + 1):
        # pyqtgraph ignores mouse moves that come faster than 100 per second, as QTest's do.
        # The last move must get through, so it waits a little first.
        if step == steps:
            QTest.qWait(15)
        QTest.mouseMove(viewport, start + (end - start) * step / steps)
    if release:
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=end)


def click_map(view, pixel):
    QTest.mouseClick(view.plot.viewport(), Qt.MouseButton.LeftButton, pos=pixel)


def expected_placement(view, start, end):
    """The start point and velocity a drag from pixel ``start`` to ``end`` should produce."""
    x, y = map_position_at(view, start)
    tip_x, tip_y = map_position_at(view, end)
    return (x, y, *drag_velocity(x, y, tip_x - x, tip_y - y))


# --- place mode --------------------------------------------------------------------------------


def test_place_button_switches_place_mode(lab):
    view = lab.view
    assert not view.place_mode
    click(view.place_button)
    assert view.place_mode and view.place_button.isChecked()
    click(view.place_button)
    assert not view.place_mode


def test_dragging_in_place_mode_adds_a_particle_with_the_arrow_velocity(lab):
    view = lab.view
    click(view.place_button)
    start, end = pixel_of(view, 8.0, 0.0), pixel_of(view, 8.0, 5.0)
    range_before = view.view_range()

    drag(view, start, end)

    (particle,) = lab.simulation.particles
    x, y, vx, vy = expected_placement(view, start, end)
    assert tuple(particle.initial_state) == pytest.approx((x, y, vx, vy), rel=1e-12, abs=1e-12)
    assert view.view_range() == range_before  # the drag did not pan the map
    assert view.arrow_points() is None  # the arrow disappears on release
    assert lab.particle_form.error_text() == ""
    assert lab.particle_form.message_label.text().startswith("Added particle 1. r = ")
    fields = [float(lab.particle_form.edits[name].text()) for name in lab.particle_form.FIELDS]
    assert fields == pytest.approx([x, y, vx, vy], rel=1e-9)


def test_a_sideways_drag_as_long_as_r_makes_a_nearly_circular_orbit(lab):
    view = lab.view
    click(view.place_button)
    start, end = pixel_of(view, 6.0, 0.0), pixel_of(view, 6.0, 6.0)
    drag(view, start, end)
    x, y, vx, vy = lab.simulation.particles[0].initial_state
    # Exact for an exact arrow; the pixels make it uncertain by about a pixel in 6 r_g.
    elements = preview(Simulation(), x, y, vx, vy).elements
    assert elements.eccentricity < 0.02


def test_while_dragging_the_arrow_and_the_preview_follow_the_mouse(lab):
    view = lab.view
    click(view.place_button)
    start, end = pixel_of(view, 8.0, 0.0), pixel_of(view, 8.0, 4.0)
    drag(view, start, end, release=False)

    (x0, y0), (x1, y1) = view.arrow_points()
    assert (x0, y0) == pytest.approx(map_position_at(view, start), abs=1e-9)
    assert (x1, y1) == pytest.approx(map_position_at(view, end), abs=1e-9)
    assert view.arrow_valid()
    x, y, vx, vy = expected_placement(view, start, end)
    assert lab.particle_form.message_label.text() == describe_preview(
        preview(lab.simulation, x, y, vx, vy), 2.0
    ).replace("GM/c", "GM/⁠c")
    assert len(lab.simulation) == 0  # nothing is added before the release
    QTest.mouseRelease(view.plot.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert len(lab.simulation) == 1


def test_a_drag_that_starts_inside_the_horizon_is_red_and_adds_nothing(lab):
    view = lab.view
    click(view.place_button)
    start, end = pixel_of(view, 1.0, 0.0), pixel_of(view, 1.0, 3.0)
    drag(view, start, end, release=False)
    assert not view.arrow_valid()
    assert "start outside r = 2" in lab.particle_form.error_text()
    QTest.mouseRelease(view.plot.viewport(), Qt.MouseButton.LeftButton, pos=end)
    assert len(lab.simulation) == 0
    assert lab.particle_form.error_text().startswith("Nothing added.")


def test_a_drag_faster_than_light_is_refused(lab):
    view = lab.view
    click(view.place_button)
    # At r = 3 the scale is 3^(-3/2) ≈ 0.19 per r_g, so an arrow of 8 r_g means v ≈ 1.5 c.
    drag(view, pixel_of(view, 3.0, 0.0), pixel_of(view, 3.0, 8.0))
    assert len(lab.simulation) == 0
    assert "slower than light" in lab.particle_form.error_text()


def test_the_preview_warns_when_the_orbit_will_reach_the_horizon(lab):
    view = lab.view
    click(view.place_button)
    drag(view, pixel_of(view, 9.0, 0.0), pixel_of(view, 9.0, 1.0), release=False)
    assert "It will come down to r = 2 and stop there." in lab.particle_form.message_label.text()


def test_a_click_in_place_mode_adds_nothing_and_explains(lab):
    click(lab.view.place_button)
    click_map(lab.view, pixel_of(lab.view, 8.0, 0.0))
    assert len(lab.simulation) == 0
    assert "drag an arrow" in lab.particle_form.message_label.text()


def test_the_mouse_wheel_still_zooms_in_place_mode(lab):
    from test_viewport import turn_wheel

    view = lab.view
    click(view.place_button)
    width = view.view_range()[0][1] - view.view_range()[0][0]
    turn_wheel(view, +1, pixel_of(view, 0.0, 0.0))
    assert view.view_range()[0][1] - view.view_range()[0][0] < width


def test_switching_place_mode_off_brings_panning_back(lab):
    view = lab.view
    click(view.place_button)
    click(view.place_button)
    before = view.view_range()
    drag(view, pixel_of(view, 0.0, 0.0), pixel_of(view, 0.0, 0.0) + QPoint(120, 0))
    assert view.view_range() != before
    assert len(lab.simulation) == 0


# --- selecting and removing ------------------------------------------------------------------


def add_two(lab):
    for values in ((8.0, 0.0, 0.0, 0.35), (-6.0, 0.0, 0.0, -0.4)):
        fill_particle_form(lab.particle_form, *values)
        click(lab.particle_form.add_button)


def test_clicking_a_particle_selects_it(lab):
    add_two(lab)
    view = lab.view
    assert lab.selected_id is None and not lab.particle_form.remove_button.isEnabled()
    click_map(view, pixel_of(view, -6.0, 0.0) + QPoint(5, -4))  # within 12 px
    assert lab.selected_id == 1 and view.selected_index() == 1
    assert lab.particle_form.remove_button.isEnabled()
    assert lab.particle_form.edits["x"].text() == "-6"
    assert "Particle 2 selected" in lab.particle_form.message_label.text()


def test_clicking_empty_map_clears_the_selection(lab):
    add_two(lab)
    view = lab.view
    click_map(view, pixel_of(view, 8.0, 0.0))
    assert lab.selected_id == 0
    click_map(view, pixel_of(view, 8.0, 0.0) + QPoint(20, 0))  # beyond 12 px
    assert lab.selected_id is None and view.selected_index() is None
    assert not lab.particle_form.remove_button.isEnabled()


def test_the_selection_ring_follows_the_particle(lab, clock):
    add_two(lab)
    click_map(lab.view, pixel_of(lab.view, 8.0, 0.0))
    click(lab.run_controls.play_button)
    run_for(lab.runner, clock, 0.2)
    assert lab.view.selected_index() == 0
    ring = lab.view._selection.getData()
    assert (float(ring[0][0]), float(ring[1][0])) == pytest.approx(lab.view.particle_points()[0])


def test_remove_button_removes_the_selected_particle(lab):
    add_two(lab)
    click_map(lab.view, pixel_of(lab.view, 8.0, 0.0))
    click(lab.particle_form.remove_button)
    assert [p.id for p in lab.simulation.particles] == [1]
    assert lab.selected_id is None and len(lab.view.particle_points()) == 1
    assert lab.particle_form.message_label.text() == "Removed particle 1."
    assert lab.particle_form.summary_label.text() == "1 particle, moving."


def test_delete_key_removes_the_selected_particle(lab, qapp):
    add_two(lab)
    click_map(lab.view, pixel_of(lab.view, -6.0, 0.0))
    lab.view.plot.setFocus()
    QTest.keyClick(lab.view.plot, Qt.Key.Key_Delete)
    assert [p.id for p in lab.simulation.particles] == [0]


def test_delete_in_a_text_field_edits_the_text_and_removes_nothing(lab):
    add_two(lab)
    click_map(lab.view, pixel_of(lab.view, -6.0, 0.0))
    edit = lab.particle_form.edits["x"]
    edit.setFocus()
    edit.setCursorPosition(0)
    QTest.keyClick(edit, Qt.Key.Key_Delete)
    assert edit.text() == "6"  # selecting filled in "-6"; Delete removed the minus sign
    assert len(lab.simulation) == 2


def test_colours_and_numbers_stay_with_their_particles_after_a_removal(lab):
    from bhlab.ui.theme import particle_colour

    add_two(lab)
    fill_particle_form(lab.particle_form, 12.0, 0.0, 0.0, 0.28)
    click(lab.particle_form.add_button)
    click_map(lab.view, pixel_of(lab.view, -6.0, 0.0))
    click(lab.particle_form.remove_button)
    ids = [p.id for p in lab.simulation.particles]
    assert ids == [0, 2]
    brushes = [brush.color().name() for brush in lab.view._particles.data["brush"]]
    assert brushes == [particle_colour(0), particle_colour(2)]
    fill_particle_form(lab.particle_form, 15.0, 0.0, 0.0, 0.25)
    click(lab.particle_form.add_button)
    assert "Added particle 4" in lab.particle_form.message_label.text()


def test_reset_keeps_the_remaining_particles_and_the_selection(lab, clock):
    add_two(lab)
    click_map(lab.view, pixel_of(lab.view, -6.0, 0.0))
    click(lab.run_controls.play_button)
    run_for(lab.runner, clock, 0.2)
    click(lab.run_controls.reset_button)
    assert lab.view.particle_points() == ((8.0, 0.0), (-6.0, 0.0))
    assert lab.selected_id == 1 and lab.view.selected_index() == 1


def test_describe_preview_reads_the_orbit_aloud():
    text = describe_preview(preview(Simulation(), 50.0, 0.0, 0.0, math.sqrt(0.03)), 2.0)
    assert text == (
        "r = 50.00, speed 0.1732 c (1.225 × circular). Bound orbit, e = 0.5000, "
        "periapsis 50.00 GM/c², apoapsis 150.0 GM/c²."
    )
    escaping = describe_preview(preview(Simulation(), 10.0, 0.0, 0.6, 0.0), 2.0)
    assert escaping.startswith("r = 10.00, speed 0.6000 c") and "Unbound: it escapes" in escaping


def test_long_numbers_in_the_fields_show_their_leading_digits(lab):
    # Whether the buttons fit is checked by eye in the real window: the offscreen platform the
    # tests use has no fonts, so text widths here are not those on screen.
    form = lab.particle_form
    form.set_fields(7.005884389, 0.03461405331, 0.0, 0.3770589888)
    assert all(form.edits[name].cursorPosition() == 0 for name in form.FIELDS)
