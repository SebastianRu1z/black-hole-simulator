"""RK4 and velocity Verlet: exact cases, Kepler orbits, convergence order and conservation."""

import math

import numpy as np
import pytest

from bhlab.physics.newtonian import (
    acceleration,
    circular_orbit,
    kepler_period,
    make_state,
    specific_angular_momentum,
    specific_energy,
)
from bhlab.solvers.fixed_step import (
    first_order_system,
    integrate,
    rk4_step,
    velocity_verlet_step,
)


def ellipse(semi_major_axis, eccentricity):
    """Start at periapsis on the +x axis, with the speed from the vis-viva equation."""
    r_p = semi_major_axis * (1.0 - eccentricity)
    speed = math.sqrt(2.0 / r_p - 1.0 / semi_major_axis)  # v² = GM (2/r − 1/a)
    return make_state(r_p, 0.0, 0.0, speed)


def distance_from_start_after_one_period(state, semi_major_axis, n_steps, method):
    period = kepler_period(semi_major_axis)
    end = integrate(acceleration, state, period / n_steps, n_steps, method).states[-1]
    return float(np.hypot(*(end[:2] - state[:2])))


def relative_energy_errors(trajectory, state):
    e0 = specific_energy(state)
    return np.array([abs(specific_energy(s) - e0) / abs(e0) for s in trajectory.states])


# --- single steps, where the exact answer is known -------------------------------------------


def test_rk4_integrates_a_cubic_exactly():
    # For dy/dt = g(t), RK4 is Simpson's rule, which is exact for cubics: ∫ 4t³ dt = t⁴.
    def f(t, _y):
        return np.array([4.0 * t**3])

    assert rk4_step(f, 0.0, np.array([0.0]), 1.0) == pytest.approx([1.0], rel=1e-15)
    assert rk4_step(f, 1.0, np.array([1.0]), 2.0) == pytest.approx([81.0], rel=1e-15)


def test_rk4_matches_the_taylor_series_of_the_exponential_to_fourth_order():
    # dy/dt = y: one step gives 1 + h + h²/2 + h³/6 + h⁴/24, the series of e^h cut after h⁴.
    h = 0.1
    expected = 1 + h + h**2 / 2 + h**3 / 6 + h**4 / 24
    assert rk4_step(lambda _t, y: y, 0.0, np.array([1.0]), h) == pytest.approx([expected], 1e-15)


def test_verlet_is_exact_for_a_constant_acceleration():
    # Free fall: x = x₀ + v₀h + ah²/2 and v = v₀ + ah, with no error at all.
    g = np.array([0.0, -9.81])

    def constant(_x):
        return g

    x, v, a = velocity_verlet_step(constant, np.array([0.0, 100.0]), np.array([3.0, 4.0]), g, 2.0)
    assert x == pytest.approx([6.0, 100.0 + 8.0 - 19.62], rel=1e-15)
    assert v == pytest.approx([3.0, 4.0 - 19.62], rel=1e-15)
    assert a == pytest.approx(g)


def test_first_order_system_puts_velocities_before_accelerations():
    f = first_order_system(acceleration)
    assert f(0.0, make_state(3.0, 4.0, 0.1, 0.2)) == pytest.approx([0.1, 0.2, -0.024, -0.032])


# --- the trajectory --------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["rk4", "verlet"])
def test_trajectory_holds_every_step_and_cannot_be_changed(method):
    start = circular_orbit(100.0)
    trajectory = integrate(acceleration, start, 2.5, 8, method)
    assert trajectory.times.shape == (9,) and trajectory.states.shape == (9, 4)
    assert trajectory.times == pytest.approx(2.5 * np.arange(9), abs=0.0)
    assert trajectory.states[0] == pytest.approx(start, abs=0.0)
    assert (trajectory.method, trajectory.step) == (method, 2.5)
    with pytest.raises(ValueError):  # read-only: a computed result is never edited afterwards
        trajectory.states[0, 0] = 1.0


@pytest.mark.parametrize(
    "arguments",
    [
        {"method": "euler"},
        {"step": 0.0},
        {"step": -1.0},
        {"step": math.nan},
        {"step": math.inf},
        {"n_steps": 0},
        {"n_steps": -3},
        {"n_steps": 2.5},
        {"n_steps": True},
        {"initial_state": [1.0, 2.0, 3.0]},
        {"initial_state": [[1.0, 0.0], [0.0, 1.0]]},
        {"initial_state": [1.0, 0.0, math.nan, 1.0]},
    ],
)
def test_invalid_arguments_are_refused(arguments):
    valid = {"initial_state": circular_orbit(100.0), "step": 1.0, "n_steps": 10, "method": "rk4"}
    with pytest.raises(ValueError):
        integrate(acceleration, **(valid | arguments))


# --- Kepler orbits ---------------------------------------------------------------------------


@pytest.mark.parametrize(("method", "tolerance"), [("rk4", 1e-7), ("verlet", 0.03)])
def test_circular_orbit_closes_after_one_period(method, tolerance):
    # 1000 steps per orbit. Measured: 2.3e-8 r_g (RK4) and 8.3e-3 r_g (Verlet) at r = 100.
    error = distance_from_start_after_one_period(circular_orbit(100.0), 100.0, 1000, method)
    assert error < tolerance


@pytest.mark.parametrize("method", ["rk4", "verlet"])
def test_ellipse_swings_between_periapsis_and_apoapsis(method):
    # a = 100, e = 0.5: periapsis a(1 − e) = 50, apoapsis a(1 + e) = 150.
    start = ellipse(100.0, 0.5)
    trajectory = integrate(acceleration, start, kepler_period(100.0) / 4000, 4000, method)
    radii = np.hypot(trajectory.states[:, 0], trajectory.states[:, 1])
    assert radii.min() == pytest.approx(50.0, rel=1e-6)
    assert radii.max() == pytest.approx(150.0, rel=1e-4)


@pytest.mark.parametrize("semi_major_axis", [25.0, 100.0, 400.0])
def test_keplers_third_law_holds_for_every_size_of_orbit(semi_major_axis):
    # The orbit closes after T = 2π a^(3/2). The error relative to a is the same for every a,
    # because the problem has no length scale of its own once GM = 1 (measured: 1.9e-9).
    error = distance_from_start_after_one_period(
        ellipse(semi_major_axis, 0.5), semi_major_axis, 2000, "rk4"
    )
    assert error / semi_major_axis < 1e-8


# --- convergence order -----------------------------------------------------------------------


@pytest.mark.parametrize(("method", "order"), [("rk4", 4), ("verlet", 2)])
def test_halving_the_step_reduces_the_error_by_two_to_the_order(method, order):
    start = ellipse(100.0, 0.5)
    coarse = distance_from_start_after_one_period(start, 100.0, 1000, method)
    fine = distance_from_start_after_one_period(start, 100.0, 2000, method)
    # Measured: 16.65 for RK4 (log₂ = 4.06) and 4.00 for Verlet.
    assert math.log2(coarse / fine) == pytest.approx(order, abs=0.2)


# --- long-term behaviour ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def forty_orbits():
    """40 orbits of the e = 0.5 ellipse with 200 steps per orbit, for both methods."""
    start = ellipse(100.0, 0.5)
    step = kepler_period(100.0) / 200
    return start, {m: integrate(acceleration, start, step, 40 * 200, m) for m in ("rk4", "verlet")}


def test_rk4_energy_error_keeps_growing(forty_orbits):
    start, runs = forty_orbits
    errors = relative_energy_errors(runs["rk4"], start)
    first_two, last_two = errors[:401].max(), errors[-401:].max()
    assert last_two > 5.0 * first_two  # measured: 15 times larger after 40 orbits


def test_verlet_energy_error_stays_bounded(forty_orbits):
    start, runs = forty_orbits
    errors = relative_energy_errors(runs["verlet"], start)
    first_two, last_two = errors[:401].max(), errors[-401:].max()
    assert last_two < 1.1 * first_two  # measured: the same, 2.7e-3, after 40 orbits


def test_verlet_conserves_angular_momentum_exactly(forty_orbits):
    # For a central force the Verlet updates never change x × v, so only rounding is left.
    start, runs = forty_orbits
    l0 = specific_angular_momentum(start)
    drift = max(abs(specific_angular_momentum(s) - l0) for s in runs["verlet"].states)
    assert drift / l0 < 1e-12


def test_harmonic_oscillator_rk4_loses_energy_while_verlet_keeps_it():
    """The same mathematics as an ideal LC tank circuit: d²x/dt² = −x, energy (x² + v²)/2."""
    start = np.array([1.0, 0.0])

    def spring(x):
        return -x

    energy = {}
    for method in ("rk4", "verlet"):
        states = integrate(spring, start, 0.2, 20_000, method).states  # about 640 periods
        energy[method] = 0.5 * (states[:, 0] ** 2 + states[:, 1] ** 2)
    # RK4 shrinks the energy a little at every step, like a resistor in the tank.
    assert np.all(np.diff(energy["rk4"]) < 0.0)
    assert energy["rk4"][-1] == pytest.approx(0.4912, abs=1e-4)
    # Verlet's energy wobbles within 1 % of the start and does not decay.
    assert energy["verlet"].min() > 0.495 - 1e-6 and energy["verlet"].max() <= 0.5 + 1e-12


# --- stopping at a radius --------------------------------------------------------------------


@pytest.mark.parametrize("method", ["rk4", "verlet"])
def test_without_a_stop_radius_a_fall_steps_over_r_0_and_gains_energy(method):
    """The failure that stop_radius exists for: the particle is flung out with E > 0."""
    run = integrate(acceleration, make_state(10.0, 0.0, 0.0, 0.0), 0.5, 200, method)
    assert not run.stopped
    assert specific_energy(run.states[-1]) > 0.0 > specific_energy(run.states[0])


@pytest.mark.parametrize("method", ["rk4", "verlet"])
def test_a_fall_stops_at_the_first_step_inside_the_stop_radius(method):
    run = integrate(
        acceleration, make_state(10.0, 0.0, 0.0, 0.0), 0.5, 200, method, stop_radius=2.0
    )
    radii = np.hypot(run.states[:, 0], run.states[:, 1])
    assert run.stopped
    assert radii[-1] <= 2.0 < radii[-2]  # the last state is the first one inside
    assert len(run.times) == len(run.states) < 201
    assert run.times[-1] == pytest.approx(0.5 * (len(run.times) - 1))
    # Analytic time to fall from r = 10 to r = 2 is 33.70; the stop comes within one step after.
    assert 33.70 <= run.times[-1] < 33.70 + 0.5 + 1e-9
    assert specific_energy(run.states[-1]) < 0.0  # no kick: still bound
    assert not run.states.flags.writeable


@pytest.mark.parametrize("method", ["rk4", "verlet"])
def test_an_orbit_that_stays_outside_the_stop_radius_runs_to_the_end(method):
    run = integrate(acceleration, circular_orbit(10.0), 0.5, 100, method, stop_radius=2.0)
    assert not run.stopped
    assert len(run.times) == 101


def test_a_stop_on_the_very_last_step_is_still_reported():
    full = integrate(acceleration, make_state(10.0, 0.0, 0.0, 0.0), 0.5, 200, stop_radius=2.0)
    steps_needed = len(full.times) - 1
    exact = integrate(
        acceleration, make_state(10.0, 0.0, 0.0, 0.0), 0.5, steps_needed, stop_radius=2.0
    )
    assert exact.stopped and len(exact.times) == steps_needed + 1


@pytest.mark.parametrize(
    ("stop_radius", "message"),
    [
        (0.0, "positive"),
        (-2.0, "positive"),
        (math.nan, "positive"),
        (math.inf, "positive"),
        (20.0, "start outside"),
    ],
)
def test_invalid_stop_radius_is_refused(stop_radius, message):
    with pytest.raises(ValueError, match=message):
        integrate(acceleration, circular_orbit(10.0), 0.5, 10, stop_radius=stop_radius)
