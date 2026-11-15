"""The tracker panel in the window: the list, selection both ways, live numbers, refresh rate."""

import math

import pytest
from helpers import FakeClock, click, fill_particle_form, run_for, type_mass
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from bhlab.physics.newtonian import circular_velocity, make_state
from bhlab.simulation.tracking import track
from bhlab.ui.main_window import MainWindow
from bhlab.ui.tracker_panel import ROWS, describe_tracking
from bhlab.units import BlackHole

TEN_SOLAR_MASSES = BlackHole.from_solar_masses(10.0)


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


def add(lab, x, y, vx, vy):
    fill_particle_form(lab.particle_form, x, y, vx, vy)
    click(lab.particle_form.add_button)


def click_list_row(lab, row):
    widget = lab.tracker.particle_list
    rect = widget.visualItemRect(widget.item(row))
    QTest.mouseClick(widget.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())


def test_the_list_shows_every_particle_and_its_fate(lab):
    assert lab.tracker.title_label.text() == "No particles yet."
    add(lab, 8.0, 0.0, *circular_velocity(8.0, 0.0))
    add(lab, 10.0, 0.0, 0.0, 0.0)  # at rest: falls in
    add(lab, 10.0, 0.0, 0.0, 0.5)  # above √(2/10): escapes
    texts = [lab.tracker.particle_list.item(row).text() for row in range(3)]
    assert texts == [
        "Particle 1  ·  Bound orbit",
        "Particle 2  ·  Will reach r = 2 and stop",
        "Particle 3  ·  Escapes",
    ]
    assert not lab.tracker.details_visible()
    assert "Click a particle" in lab.tracker.title_label.text()


def test_picking_in_the_list_selects_on_the_map_too(lab):
    add(lab, 8.0, 0.0, *circular_velocity(8.0, 0.0))
    add(lab, -12.0, 0.0, 0.0, -0.25)
    click_list_row(lab, 1)
    assert lab.selected_id == 1 and lab.view.selected_index() == 1
    assert lab.tracker.title_label.text() == "Particle 2" and lab.tracker.details_visible()
    assert lab.particle_form.remove_button.isEnabled()


def test_selecting_on_the_map_selects_in_the_list(lab):
    add(lab, 8.0, 0.0, *circular_velocity(8.0, 0.0))
    view = lab.view
    pixel = view.plot.mapFromScene(view.view_box.mapViewToScene(QPointF(8.0, 0.0)))
    QTest.mouseClick(view.plot.viewport(), Qt.MouseButton.LeftButton, pos=pixel)
    assert lab.tracker.particle_list.item(0).isSelected()
    assert lab.tracker.title_label.text() == "Particle 1"


def test_numbers_for_a_circular_orbit_at_r_8_around_ten_solar_masses(lab):
    add(lab, 8.0, 0.0, *circular_velocity(8.0, 0.0))
    click_list_row(lab, 0)
    v = lab.tracker.value_text
    assert v("fate") == ("Bound orbit", "")
    assert v("r") == ("8.000 GM/c²", "118.1 km")
    assert v("speed") == ("0.3536 c", "1.060 × 10⁵ km/s")  # √(1/8) c = 106 000 km/s
    assert v("circular")[0] == "0.3536 c" and v("escape")[0] == "0.5000 c"
    assert v("ratio") == ("0.7071", "bound")
    assert v("radial") == ("sideways", "neither in nor out")
    assert v("energy")[0] == "-0.06250 c²"  # E = −1/(2r)
    assert v("eccentricity") == ("0", "circular")  # not the rounding noise 2.2e-16
    assert v("period") == ("142.2 GM/c³", "7.003 ms")  # 2π·8^1.5, times 49.25 µs
    assert v("next_periapsis")[0] == "circular orbit"
    assert v("reliability") == ("rough guide only", "corrections ≈ 13 %")


def test_numbers_change_with_the_mass_but_the_orbit_does_not(lab):
    add(lab, 8.0, 0.0, *circular_velocity(8.0, 0.0))
    click_list_row(lab, 0)
    type_mass(lab, "4.3e6")
    assert lab.tracker.value_text("r") == ("8.000 GM/c²", "0.3395 AU")
    assert lab.tracker.value_text("period")[1] == "50.19 min"


def test_an_escaping_particle_has_no_period_or_apoapsis(lab):
    add(lab, 10.0, 0.0, 0.0, 0.5)
    click_list_row(lab, 0)
    v = lab.tracker.value_text
    assert v("fate")[0] == "Escapes"
    assert v("apoapsis") == ("∞", "escapes") and v("period")[0] == "none: it escapes"
    assert v("semi_major")[1] == "negative: hyperbola" and v("ratio")[1] == "escapes"


def test_while_running_the_numbers_refresh_ten_times_a_second(lab, clock):
    add(lab, 30.0, 0.0, 0.0, 0.12)  # an ellipse, so r changes
    click_list_row(lab, 0)
    click(lab.run_controls.play_button)
    clock.advance(0.016)
    lab.runner.tick()
    shown = lab.tracker.value_text("r")
    clock.advance(0.016)
    lab.runner.tick()  # 32 ms after the last redraw: not yet
    assert lab.tracker.value_text("r") == shown
    run_for(lab.runner, clock, 0.1)
    assert lab.tracker.value_text("r") != shown
    # The panel may be up to a tenth of a second behind; after a pause it is exact.
    click(lab.run_controls.play_button)
    lab._show_simulation()
    assert (
        lab.tracker.value_text("r")
        == describe_tracking(track(lab.simulation.particles[0].state, 2.0), TEN_SOLAR_MASSES)["r"]
    )


def test_a_particle_that_falls_in_turns_to_stopped(lab, clock):
    add(lab, 10.0, 0.0, 0.0, 0.0)
    click_list_row(lab, 0)
    assert lab.tracker.value_text("fate")[0] == "Will reach r = 2 and stop"
    click(lab.run_controls.play_button)
    run_for(lab.runner, clock, 0.5)  # 50 GM/c³; the fall takes 33.70
    click(lab.run_controls.play_button)
    assert lab.tracker.value_text("fate")[0] == "Stopped at r = 2"
    assert lab.tracker.particle_list.item(0).text().endswith("Stopped at r = 2")


def test_removing_the_tracked_particle_empties_the_details(lab):
    add(lab, 8.0, 0.0, *circular_velocity(8.0, 0.0))
    add(lab, 12.0, 0.0, *circular_velocity(12.0, 0.0))
    click_list_row(lab, 0)
    click(lab.particle_form.remove_button)
    assert lab.tracker.listed_ids() == (1,)
    assert not lab.tracker.details_visible()


def test_every_row_has_a_tooltip_and_text():
    texts = describe_tracking(
        track(make_state(50.0, 0.0, 0.0, math.sqrt(0.03)), 2.0), TEN_SOLAR_MASSES
    )
    assert set(texts) == {key for key, _name, _tip in ROWS}
    assert all(tip for _key, _name, tip in ROWS)
    assert texts["next_periapsis"][0] == "0 GM/c³"  # it is at periapsis right now
    assert texts["periapsis"][0] == "50.00 GM/c²" and texts["apoapsis"][0] == "150.0 GM/c²"


def test_reliability_is_listed_right_after_the_status():
    assert [key for key, _name, _tip in ROWS][:2] == ["fate", "reliability"]


def test_pausing_clears_the_slow_down_notice(lab, clock):
    add(lab, 8.0, 0.0, *circular_velocity(8.0, 0.0))
    click(lab.run_controls.play_button)
    clock.cost_per_reading = 0.01  # every reading of the clock takes 10 ms: hopelessly slow
    run_for(lab.runner, clock, 0.2)
    assert lab.run_controls.speed_detail_label.property("error") is True
    clock.cost_per_reading = 0.0
    click(lab.run_controls.play_button)  # pause
    assert lab.run_controls.speed_detail_label.property("error") is False
