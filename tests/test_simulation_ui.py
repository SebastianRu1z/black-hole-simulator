"""The simulation in the window: run controls, the real-time runner, the particle form.

Real time comes from a fake clock that the tests move by hand, so nothing here waits. The tests
run on Qt's offscreen platform (see conftest.py).
"""

import math

import numpy as np
import pytest
from helpers import FakeClock, click, fill_particle_form, run_for, type_mass
from PySide6.QtTest import QSignalSpy

from bhlab.physics.newtonian import circular_velocity, kepler_period
from bhlab.simulation.model import Particle, Simulation
from bhlab.ui.main_window import MainWindow, describe_particles
from bhlab.ui.particle_form import ParticleForm, parse_number
from bhlab.ui.run_controls import RunControls, format_clock
from bhlab.ui.simulation_runner import SimulationRunner
from bhlab.ui.theme import PARTICLE_COLOURS, PARTICLE_NEUTRAL, particle_colour
from bhlab.units import BlackHole

T10 = kepler_period(10.0)  # 198.69 GM/c³: one lap of the circular orbit at r = 10
TEN_SOLAR_MASSES = BlackHole.from_solar_masses(10.0)
SAGITTARIUS_A = BlackHole.from_solar_masses(4.3e6)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def lab(qapp, clock):
    """A main window whose real-time clock is under the test's control."""
    window = MainWindow(clock=clock)
    window.show()
    qapp.processEvents()
    yield window
    window.close()


@pytest.fixture
def runner(qapp, clock):
    """A runner at 100 GM/c³ per second with one particle on the circular orbit at r = 10."""
    simulation = Simulation()
    simulation.add_particle(10.0, 0.0, *circular_velocity(10.0, 0.0))
    runner = SimulationRunner(simulation, speed=100.0, clock=clock)
    yield runner
    runner.set_running(False)


# --- run controls ----------------------------------------------------------------------------


def test_speed_slider_offers_1_2_5_steps_from_1_to_100000(qapp):
    controls = RunControls(TEN_SOLAR_MASSES)
    assert controls.SPEEDS[:7] == (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0)
    assert controls.SPEEDS[-1] == 100_000.0 and len(controls.SPEEDS) == 16
    assert controls.speed() == 100.0  # the default

    changes = QSignalSpy(controls.speed_changed)
    controls.speed_slider.setValue(controls.speed_slider.maximum())
    controls.speed_slider.setValue(0)
    assert [changes.at(i)[0] for i in range(changes.count())] == [100_000.0, 1.0]
    assert controls.speed() == 1.0


def test_speed_readout_says_what_a_second_on_screen_means_for_the_mass(qapp):
    controls = RunControls(TEN_SOLAR_MASSES)
    assert controls.speed_label.text() == "100 GM/c³ per second"
    # 100 GM/c³ is 100 × 49.25 µs for ten solar masses, and 100 × 21.18 s for Sagittarius A*.
    assert controls.speed_detail_label.text() == "1 s on screen = 4.925 ms"
    controls.set_black_hole(SAGITTARIUS_A)
    assert controls.speed_detail_label.text() == "1 s on screen = 35.30 min"
    controls.speed_slider.setValue(controls.SPEEDS.index(20_000.0))
    assert controls.speed_label.text() == "20,000 GM/c³ per second"
    assert controls.speed_detail_label.text() == "1 s on screen = 4.903 d"


def test_clock_shows_simulated_time_and_physical_time(qapp):
    controls = RunControls(TEN_SOLAR_MASSES)
    assert controls.clock_label.text() == "t = 0.0 GM/c³  =  0 µs"
    controls.set_time(1234.56)  # × 49.2549 µs = 60.81 ms
    assert controls.clock_label.text() == "t = 1234.6 GM/c³  =  60.81 ms"
    controls.set_black_hole(SAGITTARIUS_A)  # × 21.18 s = 26 147 s
    assert controls.clock_label.text() == "t = 1234.6 GM/c³  =  7.263 h"
    assert format_clock(2.5e7) == "2.50000 × 10⁷"


def test_play_turns_into_pause_and_switches_step_off(qapp):
    controls = RunControls(TEN_SOLAR_MASSES)
    toggles = QSignalSpy(controls.play_toggled)
    assert controls.play_button.text() == "Play" and controls.step_button.isEnabled()

    click(controls.play_button)
    assert controls.play_button.text() == "Pause" and not controls.step_button.isEnabled()
    click(controls.play_button)
    assert controls.play_button.text() == "Play" and controls.step_button.isEnabled()
    assert [toggles.at(i)[0] for i in range(toggles.count())] == [True, False]

    controls.set_running(True)  # told by the program, not by the user: no signal
    assert controls.play_button.text() == "Pause" and toggles.count() == 2


def test_step_and_reset_buttons_report_the_request(qapp):
    controls = RunControls(TEN_SOLAR_MASSES)
    steps, resets = QSignalSpy(controls.step_requested), QSignalSpy(controls.reset_requested)
    click(controls.step_button)
    click(controls.reset_button)
    click(controls.reset_button)
    assert (steps.count(), resets.count()) == (1, 2)


def test_a_notice_replaces_the_physical_time_when_the_computer_cannot_keep_up(qapp):
    controls = RunControls(TEN_SOLAR_MASSES)
    controls.set_behind(True)
    assert controls.speed_detail_label.text() == "running slower than this: too much to compute"
    assert controls.speed_detail_label.property("error") is True
    controls.set_behind(False)
    assert controls.speed_detail_label.text() == "1 s on screen = 4.925 ms"
    assert controls.speed_detail_label.property("error") is False


# --- the runner: real time in, simulated time out --------------------------------------------


def test_each_frame_advances_simulated_time_by_speed_times_real_time(runner, clock):
    changes = QSignalSpy(runner.changed)
    runner.set_running(True)
    clock.advance(0.02)
    runner.tick()
    assert runner.simulation.time == pytest.approx(2.0, rel=1e-12)  # 100 GM/c³ per s × 0.02 s
    clock.advance(0.05)
    runner.tick()
    assert runner.simulation.time == pytest.approx(7.0, rel=1e-12)
    assert changes.count() == 2 and not runner.is_behind


def test_the_timer_runs_only_while_playing(runner):
    states = QSignalSpy(runner.running_changed)
    assert not runner.is_running
    runner.set_running(True)
    runner.set_running(True)  # asking twice changes nothing
    assert runner.is_running
    runner.set_running(False)
    assert not runner.is_running
    assert [states.at(i)[0] for i in range(states.count())] == [True, False]


def test_time_spent_paused_does_not_count(runner, clock):
    runner.set_running(True)
    clock.advance(0.01)
    runner.tick()
    runner.set_running(False)
    clock.advance(60.0)  # a minute passes while paused
    runner.set_running(True)
    clock.advance(0.01)
    runner.tick()
    assert runner.simulation.time == pytest.approx(2.0, rel=1e-12)


def test_a_long_gap_between_frames_counts_as_a_tenth_of_a_second(runner, clock):
    runner.set_running(True)
    clock.advance(5.0)  # the window was frozen for five seconds
    runner.tick()
    assert runner.simulation.time == pytest.approx(100.0 * runner.MAX_FRAME_SECONDS, rel=1e-12)


def test_step_advances_by_a_tenth_of_a_second_of_playback(runner):
    changes = QSignalSpy(runner.changed)
    runner.set_speed(200.0)
    runner.step()
    assert runner.simulation.time == pytest.approx(20.0, rel=1e-12)
    assert changes.count() == 1 and not runner.is_running


def test_reset_pauses_and_goes_back_to_time_zero(runner, clock):
    runner.set_running(True)
    run_for(runner, clock, 0.5)
    assert runner.simulation.time == pytest.approx(50.0, rel=1e-9)
    runner.reset()
    assert runner.simulation.time == 0.0 and not runner.is_running
    assert np.array_equal(
        runner.simulation.particles[0].state, runner.simulation.particles[0].initial_state
    )


@pytest.mark.parametrize("speed", [0.0, -5.0, math.nan, math.inf])
def test_the_speed_must_be_positive_and_finite(runner, speed):
    with pytest.raises(ValueError):
        runner.set_speed(speed)
    assert runner.speed == 100.0


def test_the_frame_rate_does_not_change_where_the_particle_is(qapp):
    """After the same real time at the same speed, a slow and a fast display agree."""
    positions = []
    for frames_per_second in (30.0, 144.0):
        clock = FakeClock()
        simulation = Simulation()
        simulation.add_particle(10.0, 0.0, *circular_velocity(10.0, 0.0))
        runner = SimulationRunner(simulation, speed=100.0, clock=clock)
        runner.set_running(True)
        run_for(runner, clock, 3.0, frames_per_second)
        runner.set_running(False)
        assert simulation.time == pytest.approx(300.0, rel=1e-12)
        positions.append(simulation.particles[0].state[:2])
    # The two simulated times differ only by rounding in the sum of the frame times.
    assert positions[0] == pytest.approx(positions[1], abs=1e-9)


def test_too_much_to_compute_slows_the_pace_and_says_so_but_keeps_the_motion_right(qapp, clock):
    simulation = Simulation()
    simulation.add_particle(6.0, 0.0, *circular_velocity(6.0, 0.0))  # a lap takes 92 GM/c³
    runner = SimulationRunner(simulation, speed=100_000.0, clock=clock)
    runner.set_running(True)
    clock.cost_per_reading = 0.003  # the budget of 8 ms allows three solver steps per frame
    for _ in range(10):
        clock.advance(1.0 / 60.0)
        runner.tick()
    runner.set_running(False)

    asked_for = 100_000.0 * 10 * (1.0 / 60.0)  # more than 16 000 GM/c³
    assert 0.0 < simulation.time < 0.01 * asked_for
    assert runner.is_behind is False  # pausing clears the notice …

    runner.set_running(True)
    clock.advance(1.0 / 60.0)
    runner.tick()
    assert runner.is_behind is True  # … and it is back on the next slow frame

    # Only the pace suffered: the state is exactly that of an unhurried run to the same time.
    unhurried = Simulation()
    unhurried.add_particle(6.0, 0.0, *circular_velocity(6.0, 0.0))
    unhurried.advance(simulation.time)
    assert np.array_equal(simulation.particles[0].state, unhurried.particles[0].state)

    # Once the frames are on time again the notice goes away, after half a second.
    clock.cost_per_reading = 0.0
    runner.set_speed(1.0)
    run_for(runner, clock, 0.4)
    assert runner.is_behind is True
    run_for(runner, clock, 0.2)
    assert runner.is_behind is False
    runner.set_running(False)


# --- the particle form -----------------------------------------------------------------------


def test_form_suggests_the_circular_orbit_at_r_10(qapp):
    form = ParticleForm()
    texts = [form.edits[name].text() for name in form.FIELDS]
    assert texts == ["10", "0", "0", "0.316227766"]  # v = √(1/10)
    assert form.error_text() == ""


def test_add_reports_the_four_numbers(qapp):
    form = ParticleForm()
    requests = QSignalSpy(form.add_requested)
    fill_particle_form(form, " 50 ", "-2.5", "1e-2", "0.1732")
    click(form.add_button)
    assert requests.count() == 1
    assert list(requests.at(0)) == [50.0, -2.5, 0.01, 0.1732]


@pytest.mark.parametrize(
    ("field", "text", "message"),
    [
        ("x", "", "Enter a number for x."),
        ("vy", "fast", "“fast” is not a number (in vy)."),
        ("y", "1,5", "Use a point for decimals in y, for example 0.25."),
        ("vx", "inf", "vx must be a finite number."),
        ("x", "nan", "x must be a finite number."),
    ],
)
def test_text_that_is_not_a_number_is_reported_and_nothing_is_added(qapp, field, text, message):
    form = ParticleForm()
    requests = QSignalSpy(form.add_requested)
    form.edits[field].setText(text)
    click(form.add_button)
    assert requests.count() == 0
    assert form.error_text() == message and form.message_label.text() == message
    assert form.edits[field].property("invalid") is True

    form.edits[field].setText("3")  # corrected: the mark goes away and the particle is asked for
    click(form.add_button)
    assert requests.count() == 1 and form.edits[field].property("invalid") is False


def test_parse_number_accepts_the_usual_ways_of_writing_a_number():
    assert parse_number(" -2.5 ", "x") == -2.5
    assert parse_number("1e3", "x") == 1000.0
    assert parse_number("0", "vx") == 0.0


def test_circular_speed_fills_in_the_velocity_of_the_circular_orbit(qapp):
    form = ParticleForm()
    fill_particle_form(form, 0, 20, 0.5, 0.5)
    click(form.circular_button)
    # At (0, 20): speed √(1/20) = 0.2236, pointing along −x for anticlockwise motion.
    assert form.edits["vx"].text() == "-0.2236067977" and form.edits["vy"].text() == "0"
    assert form.message_label.text() == "Circular speed at r = 20.00: 0.2236 c, anticlockwise."
    assert form.error_text() == ""

    fill_particle_form(form, 0, 0, 0.5, 0.5)
    click(form.circular_button)
    assert "no circular orbit through the centre" in form.error_text()
    assert form.edits["vx"].text() == "0.5"  # left as it was


def test_units_are_not_broken_across_lines_in_the_form(qapp):
    form = ParticleForm()
    form.show_error("It starts at r = 1.5 GM/c², inside.")
    assert form.error_text() == "It starts at r = 1.5 GM/c², inside."
    assert form.message_label.text() == "It starts at r = 1.5 GM/⁠c², inside."
    form.set_summary("1 stopped at r = 2 GM/c².")
    assert form.summary_label.text() == "1 stopped at r = 2 GM/⁠c²."
    form.show_info("Fine.")
    assert form.error_text() == "" and form.message_label.property("error") is False


# --- particle colours and the summary --------------------------------------------------------


def test_the_first_three_particles_have_their_own_colours_and_the_rest_share_one():
    assert [particle_colour(index) for index in range(3)] == list(PARTICLE_COLOURS)
    assert particle_colour(3) == particle_colour(40) == PARTICLE_NEUTRAL
    assert len({*PARTICLE_COLOURS, PARTICLE_NEUTRAL}) == 4


def test_describe_particles():
    def particle(stopped):
        state = np.array([10.0, 0.0, 0.0, 0.3])
        return Particle(0, state, state, 0.0, 33.7 if stopped else None)

    assert describe_particles([], 2.0) == "No particles yet."
    assert describe_particles([particle(False)], 2.0) == "1 particle, moving."
    assert describe_particles([particle(False)] * 3, 2.0) == "3 particles, all moving."
    assert describe_particles([particle(False), particle(True), particle(False)], 2.0) == (
        "3 particles: 2 moving, 1 stopped at r = 2 GM/c². Newtonian gravity has no horizon: "
        "the stop only marks where this model ends."
    )


# --- the whole window ------------------------------------------------------------------------


def test_adding_a_particle_draws_it_and_says_so(lab):
    assert lab.view.particle_points() == () and lab.particle_form.summary_label.text() == (
        "No particles yet."
    )
    click(lab.particle_form.add_button)  # the suggested circular orbit at r = 10
    assert lab.view.particle_points() == ((10.0, 0.0),)
    assert lab.view.particle_stopped() == (False,)
    assert lab.particle_form.error_text() == ""
    assert lab.particle_form.message_label.text() == (
        "Added particle 1 at r = 10.00 GM/⁠c², speed 0.3162 c."
    )
    assert lab.particle_form.summary_label.text() == "1 particle, moving."
    assert len(lab.simulation) == 1


@pytest.mark.parametrize(
    ("state", "message"),
    [
        ((1.0, 1.0, 0.0, 0.1), "outside r = 2"),  # r = 1.41, inside the horizon radius
        ((10.0, 0.0, 0.9, 0.9), "slower than light"),
    ],
)
def test_an_invalid_particle_is_explained_and_not_added(lab, state, message):
    fill_particle_form(lab.particle_form, *state)
    click(lab.particle_form.add_button)
    assert message in lab.particle_form.error_text()
    assert lab.view.particle_points() == () and len(lab.simulation) == 0


def test_playing_carries_the_particle_round_its_orbit(lab, clock):
    click(lab.particle_form.add_button)
    click(lab.run_controls.play_button)
    assert lab.runner.is_running and lab.run_controls.play_button.text() == "Pause"

    run_for(lab.runner, clock, (T10 / 4) / 100.0)  # a quarter of a lap at 100 GM/c³ per second
    (x, y), *_ = lab.view.particle_points()
    assert (x, y) == pytest.approx((0.0, 10.0), abs=1e-6)
    assert lab.run_controls.clock_label.text().startswith("t = 49.7 GM/c³")


def test_pause_step_and_reset(lab, clock):
    click(lab.particle_form.add_button)
    click(lab.run_controls.play_button)
    run_for(lab.runner, clock, 0.25)
    click(lab.run_controls.play_button)  # pause
    assert not lab.runner.is_running and lab.run_controls.step_button.isEnabled()
    assert lab.simulation.time == pytest.approx(25.0, rel=1e-9)

    click(lab.run_controls.step_button)  # a tenth of a second of playback: 10 GM/c³
    assert lab.simulation.time == pytest.approx(35.0, rel=1e-9)
    assert lab.run_controls.clock_label.text().startswith("t = 35.0 GM/c³")

    click(lab.run_controls.play_button)
    click(lab.run_controls.reset_button)  # reset also pauses
    assert lab.simulation.time == 0.0 and not lab.runner.is_running
    assert lab.run_controls.play_button.text() == "Play"
    assert lab.view.particle_points() == ((10.0, 0.0),)
    assert lab.run_controls.clock_label.text().startswith("t = 0.0 GM/c³")


def test_a_particle_that_falls_in_is_drawn_as_stopped_and_counted(lab, clock):
    fill_particle_form(lab.particle_form, 10, 0, 0, 0)  # at rest: it falls straight in
    click(lab.particle_form.add_button)
    click(lab.particle_form.circular_button)
    click(lab.particle_form.add_button)  # and one on the circular orbit, which keeps going
    click(lab.run_controls.play_button)
    run_for(lab.runner, clock, 0.5)  # 50 GM/c³; the fall to r = 2 takes 33.70

    assert lab.view.particle_stopped() == (True, False)
    assert lab.view.particle_points()[0] == pytest.approx((2.0, 0.0), abs=1e-9)
    assert lab.particle_form.summary_label.text().startswith(
        "2 particles: 1 moving, 1 stopped at r = 2 GM/⁠c²."
    )


def test_changing_the_mass_changes_the_clock_but_not_the_motion(lab, clock):
    click(lab.particle_form.add_button)
    click(lab.run_controls.play_button)
    run_for(lab.runner, clock, 0.3)
    click(lab.run_controls.play_button)
    points, time = lab.view.particle_points(), lab.simulation.time
    assert lab.run_controls.clock_label.text() == "t = 30.0 GM/c³  =  1.478 ms"

    type_mass(lab, "4.3e6")
    assert lab.view.particle_points() == points and lab.simulation.time == time
    assert lab.run_controls.clock_label.text() == "t = 30.0 GM/c³  =  10.59 min"
    assert lab.run_controls.speed_detail_label.text() == "1 s on screen = 35.30 min"


def test_the_speed_slider_sets_the_pace(lab, clock):
    click(lab.particle_form.add_button)
    lab.run_controls.speed_slider.setValue(lab.run_controls.SPEEDS.index(1000.0))
    assert lab.runner.speed == 1000.0
    click(lab.run_controls.play_button)
    clock.advance(0.01)
    lab.runner.tick()
    assert lab.simulation.time == pytest.approx(10.0, rel=1e-12)


def test_closing_the_window_stops_the_timer(qapp, clock):
    window = MainWindow(clock=clock)
    window.show()
    click(window.run_controls.play_button)
    assert window.runner.is_running
    window.close()
    assert not window.runner.is_running
