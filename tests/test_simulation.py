"""The simulation model: particles, simulated time, the stop radius, and frame-rate independence.

No window is involved: the model is advanced directly.
"""

import math

import numpy as np
import pytest

from bhlab.physics.newtonian import (
    circular_velocity,
    kepler_period,
    specific_angular_momentum,
    specific_energy,
)
from bhlab.simulation.model import Simulation

T10 = kepler_period(10.0)  # 2π·10^1.5 ≈ 198.69
FREE_FALL = (10.0, 0.0, 0.0, 0.0)  # at rest at r = 10: falls straight in


def circle(simulation, radius):
    """Add a particle on the anticlockwise circular orbit of ``radius``, starting on the +x axis."""
    return simulation.add_particle(radius, 0.0, *circular_velocity(radius, 0.0))


def identical(simulation, other):
    """Whether two simulations hold exactly the same particle states and stop times."""
    pairs = list(zip(simulation.particles, other.particles, strict=True))
    return all(np.array_equal(a.state, b.state) and a.stopped_at == b.stopped_at for a, b in pairs)


def free_fall_time(start_radius, radius):
    """Time to fall from rest at ``start_radius`` (r₀) to ``radius``.

    The exact solution is r = r₀ cos²η with t = √(r₀³/2) (η + sin η cos η).
    """
    eta = math.acos(math.sqrt(radius / start_radius))
    return math.sqrt(start_radius**3 / 2.0) * (eta + math.sin(eta) * math.cos(eta))


def grazing_pass(periapsis, apoapsis=60.0, **settings):
    """A particle released at ``apoapsis`` on the orbit whose closest approach is ``periapsis``.

    Returns the particle after 1.2 orbital periods, and the period.
    """
    semi_major_axis = (periapsis + apoapsis) / 2.0
    speed = math.sqrt(2.0 / apoapsis - 1.0 / semi_major_axis)  # vis-viva
    simulation = Simulation(**settings)
    simulation.add_particle(apoapsis, 0.0, 0.0, speed)
    period = kepler_period(semi_major_axis)
    simulation.advance(1.2 * period)
    return simulation.particles[0], period


# --- particles and time ----------------------------------------------------------------------


def test_a_new_simulation_is_empty_and_its_clock_runs():
    simulation = Simulation()
    assert len(simulation) == 0 and simulation.particles == () and simulation.time == 0.0
    assert simulation.stop_radius == 2.0
    assert simulation.advance(5.0) is True
    assert simulation.time == 5.0


def test_adding_particles_numbers_them_in_order():
    simulation = Simulation()
    first = simulation.add_particle(10.0, 0.0, 0.0, 0.3)
    second = simulation.add_particle(0.0, -20.0, 0.1, 0.0)
    assert (first.id, second.id) == (0, 1) and len(simulation) == 2
    assert np.array_equal(first.state, [10.0, 0.0, 0.0, 0.3])
    assert np.array_equal(first.initial_state, first.state)
    assert first.added_at == 0.0 and first.stopped_at is None and not first.is_stopped
    assert [particle.id for particle in simulation.particles] == [0, 1]


def test_particle_states_cannot_be_edited():
    particle = Simulation().add_particle(10.0, 0.0, 0.0, 0.3)
    for array in (particle.state, particle.initial_state):
        with pytest.raises(ValueError):
            array[0] = 3.0


@pytest.mark.parametrize(
    ("state", "message"),
    [
        ((1.5, 0.0, 0.0, 0.1), "outside r = 2"),  # inside the stop radius
        ((0.0, -2.0, 0.1, 0.0), "outside r = 2"),  # exactly on it
        ((10.0, 0.0, 1.0, 0.0), "slower than light"),  # exactly the speed of light
        ((10.0, 0.0, 0.8, 0.7), "speed 1.063"),  # faster than light; the message says how fast
        ((0.0, 0.0, 0.0, 0.1), "r = 0"),
        ((math.nan, 0.0, 0.0, 0.1), "finite"),
        ((10.0, 0.0, math.inf, 0.0), "finite"),
    ],
)
def test_invalid_particles_are_refused_and_nothing_is_added(state, message):
    simulation = Simulation()
    with pytest.raises(ValueError, match=message):
        simulation.add_particle(*state)
    assert len(simulation) == 0


@pytest.mark.parametrize("duration", [-1.0, math.nan, math.inf])
def test_time_only_runs_forward(duration):
    simulation = Simulation()
    with pytest.raises(ValueError, match="forward"):
        simulation.advance(duration)
    assert simulation.time == 0.0


@pytest.mark.parametrize(
    "settings", [{"stop_radius": 0.0}, {"stop_radius": math.nan}, {"rtol": 1e-14}, {"atol": 0.0}]
)
def test_invalid_settings_are_refused(settings):
    with pytest.raises(ValueError):
        Simulation(**settings)


# --- orbits against Kepler's laws ------------------------------------------------------------


def test_circular_orbit_goes_round_in_one_kepler_period():
    simulation = Simulation()
    circle(simulation, 10.0)
    simulation.advance(T10 / 4)
    assert simulation.particles[0].state[:2] == pytest.approx([0.0, 10.0], abs=1e-7)
    simulation.advance(3 * T10 / 4)
    assert simulation.time == pytest.approx(T10, rel=1e-15)
    assert simulation.particles[0].state[:2] == pytest.approx(
        [10.0, 0.0], abs=1e-7
    )  # measured 2e-9


def test_ellipse_is_at_apoapsis_half_a_period_after_periapsis():
    # a = 100, e = 0.5, started at periapsis (50, 0): half a period later it is at (−150, 0).
    simulation = Simulation()
    simulation.add_particle(50.0, 0.0, 0.0, math.sqrt(0.03))
    simulation.advance(kepler_period(100.0) / 2)
    x, y, vx, vy = simulation.particles[0].state
    assert (x, y) == pytest.approx((-150.0, 0.0), abs=1e-5)
    assert (vx, vy) == pytest.approx((0.0, -math.sqrt(0.03) / 3.0), abs=1e-9)  # r_p v_p = r_a v_a


def test_energy_and_angular_momentum_hold_over_two_hundred_orbits():
    simulation = Simulation()
    start = circle(simulation, 10.0).state
    simulation.advance(200 * T10)
    end = simulation.particles[0].state
    # Measured: 7.5e-10 in energy after 200 orbits.
    assert specific_energy(end) == pytest.approx(specific_energy(start), rel=1e-8)
    assert specific_angular_momentum(end) == pytest.approx(
        specific_angular_momentum(start), rel=1e-8
    )


def test_particles_do_not_influence_each_other():
    """Test particles: each one moves exactly as it would alone."""
    together = Simulation()
    circle(together, 10.0)
    together.add_particle(50.0, 0.0, 0.0, math.sqrt(0.03))
    together.add_particle(*FREE_FALL)
    for duration in (1.0, 250.0, 0.5, 400.0):
        together.advance(duration)

    for index, state in enumerate(
        (
            [10.0, 0.0, *circular_velocity(10.0, 0.0)],
            [50.0, 0.0, 0.0, math.sqrt(0.03)],
            list(FREE_FALL),
        )
    ):
        alone = Simulation()
        alone.add_particle(*state)
        alone.advance(together.time)
        assert np.array_equal(alone.particles[0].state, together.particles[index].state)


def test_a_particle_added_later_starts_at_that_time():
    simulation = Simulation()
    circle(simulation, 10.0)
    simulation.advance(77.7)
    late = circle(simulation, 20.0)
    assert late.added_at == 77.7 and late.id == 1
    assert np.array_equal(late.state, [20.0, 0.0, *circular_velocity(20.0, 0.0)])
    simulation.advance(kepler_period(20.0) / 4)
    assert simulation.particles[1].state[:2] == pytest.approx([0.0, 20.0], abs=1e-7)


# --- independence of how time is advanced ----------------------------------------------------


def busy_simulation():
    """A circle, an ellipse, a wide orbit and a particle that falls in and stops on the way."""
    simulation = Simulation()
    circle(simulation, 10.0)
    simulation.add_particle(50.0, 0.0, 0.0, math.sqrt(0.03))
    simulation.add_particle(6.0, 3.0, -0.2, 0.25)
    simulation.add_particle(*FREE_FALL)
    return simulation


@pytest.fixture(scope="module")
def one_jump():
    simulation = busy_simulation()
    simulation.advance(1234.5)
    return simulation


@pytest.mark.parametrize("frames_per_second", [30.0, 144.0, 7.3])
def test_states_do_not_depend_on_the_frame_rate(one_jump, frames_per_second):
    """The same simulated time gives the same states, bit for bit, whatever the frame rate."""
    simulation = busy_simulation()
    per_frame = 100.0 / frames_per_second  # a display running at 100 GM/c³ per second
    while simulation.time + per_frame < one_jump.time:
        simulation.advance(per_frame)
    simulation.advance(one_jump.time - simulation.time)
    assert simulation.time == one_jump.time
    assert identical(simulation, one_jump)
    assert simulation.particles[3].is_stopped  # the falling particle stopped on the way


def test_a_budget_changes_the_pace_but_not_the_states(one_jump):
    simulation = busy_simulation()
    answers = iter([True] * 19 + [False])  # enough for twenty solver steps, shared by 4 particles
    covered = simulation.advance(one_jump.time, keep_going=lambda: next(answers))
    assert covered is False
    assert 0.0 < simulation.time < one_jump.time  # it got somewhere, but not to the end

    unhurried = busy_simulation()
    unhurried.advance(simulation.time)
    assert identical(simulation, unhurried)

    assert simulation.advance(one_jump.time - simulation.time) is True
    assert simulation.time == one_jump.time and identical(simulation, one_jump)


def test_time_moves_on_even_when_the_budget_is_already_spent():
    """Every call takes at least one solver step, so the clock cannot stall for good.

    The clock moves only once every particle has been computed past it. With three particles
    and one step per call, that takes up to three calls.
    """
    simulation = Simulation()
    for radius in (10.0, 20.0, 30.0):
        circle(simulation, radius)
    times = []
    for _ in range(12):
        simulation.advance(1000.0, keep_going=lambda: False)
        times.append(simulation.time)
    assert times == sorted(times)  # never backwards
    assert times[2] > 0.0 and len(set(times)) >= 4  # and forward at least every third call


# --- the stop radius -------------------------------------------------------------------------


def test_free_fall_stops_at_r_2_at_the_analytic_time():
    simulation = Simulation()
    simulation.add_particle(*FREE_FALL)
    expected = free_fall_time(10.0, 2.0)  # 33.70 GM/c³

    simulation.advance(33.0)  # not there yet, although its solver may already be ahead
    moving = simulation.particles[0]
    assert not moving.is_stopped and 2.0 < moving.state[0] < 10.0

    simulation.advance(1.0)
    stopped = simulation.particles[0]
    assert stopped.stopped_at == pytest.approx(expected, rel=1e-9)
    assert stopped.state[:2] == pytest.approx([2.0, 0.0], abs=1e-9)
    # It arrives with v² = 2(1/2 − 1/10) = 0.8, from conservation of energy.
    assert stopped.state[2:] == pytest.approx([-math.sqrt(0.8), 0.0], rel=1e-8, abs=1e-12)

    simulation.advance(5000.0)
    assert np.array_equal(simulation.particles[0].state, stopped.state)  # it stays there


def test_a_stopped_particle_does_not_hold_the_others_back():
    simulation = Simulation()
    simulation.add_particle(*FREE_FALL)
    circle(simulation, 10.0)
    assert simulation.advance(1000.0) is True and simulation.time == 1000.0
    alone = Simulation()
    circle(alone, 10.0)
    alone.advance(1000.0)
    assert simulation.particles[0].is_stopped
    assert np.array_equal(simulation.particles[1].state, alone.particles[0].state)


def test_the_stop_radius_can_be_chosen():
    simulation = Simulation(stop_radius=5.0)
    simulation.add_particle(*FREE_FALL)
    simulation.advance(100.0)
    particle = simulation.particles[0]
    assert particle.stopped_at == pytest.approx(free_fall_time(10.0, 5.0), rel=1e-9)  # 28.74
    assert particle.state[0] == pytest.approx(5.0, abs=1e-9)
    with pytest.raises(ValueError, match="outside r = 5"):
        simulation.add_particle(4.0, 0.0, 0.0, 0.1)


GRAZING = [
    (1.9, 60.0),
    (1.99, 60.0),
    (1.9999, 60.0),
    (1.99999, 60.0),
    (1.9999, 20.0),
    (1.999, 200.0),
]


@pytest.mark.parametrize(("periapsis", "apoapsis"), GRAZING)
def test_a_pass_that_dips_inside_r_2_is_stopped_however_briefly(periapsis, apoapsis):
    particle, period = grazing_pass(periapsis, apoapsis)
    assert particle.is_stopped
    assert particle.stopped_at < period / 2  # on the way in, before the closest approach
    assert math.hypot(*particle.state[:2]) == pytest.approx(2.0, abs=1e-9)


@pytest.mark.parametrize("periapsis", [2.00001, 2.001, 2.5])
def test_a_pass_that_stays_outside_r_2_is_not_stopped(periapsis):
    particle, _period = grazing_pass(periapsis)
    assert not particle.is_stopped


def test_the_check_for_a_dip_inside_a_step_is_what_catches_the_briefest_passes(monkeypatch):
    """Without it, a step that starts and ends outside r = 2 hides a dip inside it."""
    monkeypatch.setattr(Simulation, "_could_have_dipped_inside", lambda *_arguments: False)
    missed = [pair for pair in GRAZING if not grazing_pass(*pair)[0].is_stopped]
    assert (1.99999, 60.0) in missed


# --- reset -----------------------------------------------------------------------------------


def test_reset_returns_to_the_start_and_replays_identically():
    simulation = Simulation()
    circle(simulation, 10.0)
    simulation.advance(77.7)
    recorded = simulation.particles[0].state
    simulation.add_particle(20.0, 0.0, 0.0, 0.2)  # added at t = 77.7
    simulation.advance(300.0)

    simulation.reset()
    assert simulation.time == 0.0 and len(simulation) == 2
    for particle in simulation.particles:
        assert np.array_equal(particle.state, particle.initial_state)
        assert particle.added_at == 0.0 and not particle.is_stopped

    simulation.advance(77.7)
    assert np.array_equal(simulation.particles[0].state, recorded)


def test_reset_sets_a_stopped_particle_moving_again():
    simulation = Simulation()
    simulation.add_particle(*FREE_FALL)
    simulation.advance(100.0)
    assert simulation.particles[0].is_stopped
    simulation.reset()
    assert not simulation.particles[0].is_stopped
    simulation.advance(100.0)
    assert simulation.particles[0].stopped_at == pytest.approx(free_fall_time(10.0, 2.0), rel=1e-9)
