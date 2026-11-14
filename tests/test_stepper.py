"""DOP853 one step at a time: the same solution as a whole run, readable inside each step."""

import math

import numpy as np
import pytest

from bhlab.physics.newtonian import acceleration, circular_orbit, kepler_period, make_state
from bhlab.solvers.adaptive import AdaptiveStepper, integrate_adaptive

PERIOD = kepler_period(100.0)  # 2000π ≈ 6283


def ellipse():
    """The a = 100, e = 0.5 ellipse, started at periapsis."""
    return make_state(50.0, 0.0, 0.0, math.sqrt(0.03))


def distance(state, other):
    return float(np.hypot(*(np.asarray(state)[:2] - np.asarray(other)[:2])))


def test_before_any_step_only_the_start_is_known():
    stepper = AdaptiveStepper(acceleration, ellipse(), start_time=5.0)
    assert stepper.time == stepper.step_start == 5.0
    assert stepper.n_steps == 0
    assert np.array_equal(stepper.state, ellipse())
    assert np.array_equal(stepper.state_at(5.0), ellipse())
    with pytest.raises(ValueError):
        stepper.state_at(5.1)


def test_each_step_starts_where_the_previous_one_ended_and_the_orbit_closes():
    stepper = AdaptiveStepper(acceleration, ellipse())
    while stepper.time < PERIOD:
        previous = stepper.time
        stepper.step()
        assert stepper.step_start == previous < stepper.time
    # One period later the particle is back at periapsis (measured: 9e-8 GM/c²).
    assert distance(stepper.state_at(PERIOD), ellipse()) < 1e-6
    assert stepper.n_steps < 60  # measured: 42 steps for this orbit
    assert stepper.n_evaluations >= 12 * stepper.n_steps  # DOP853 has 12 stages per step


def test_states_inside_a_step_are_as_accurate_as_its_ends():
    stepper = AdaptiveStepper(acceleration, ellipse())
    worst = 0.0
    while stepper.time < PERIOD:
        stepper.step()
        if stepper.n_steps % 6 == 0:
            middle = 0.5 * (stepper.step_start + stepper.time)
            reference = integrate_adaptive(acceleration, ellipse(), middle, rtol=1e-13, atol=1e-15)
            worst = max(worst, distance(stepper.state_at(middle), reference.states[-1]))
    assert 0.0 < worst < 1e-6  # measured: 1e-7, the same size as the error at the step ends


def test_reading_states_does_not_change_the_steps():
    quiet = AdaptiveStepper(acceleration, ellipse())
    busy = AdaptiveStepper(acceleration, ellipse())
    for _ in range(40):
        quiet.step()
        busy.step()
        for fraction in (0.1, 0.5, 0.9):
            busy.state_at(busy.step_start + fraction * (busy.time - busy.step_start))
        assert busy.time == quiet.time
    assert np.array_equal(busy.state, quiet.state)


def test_the_state_is_known_only_inside_the_latest_step_and_cannot_be_edited():
    stepper = AdaptiveStepper(acceleration, ellipse())
    for _ in range(3):
        stepper.step()
    start, end = stepper.step_start, stepper.time
    assert np.array_equal(stepper.state_at(end), stepper.state)
    assert stepper.state_at(start).shape == (4,)
    for outside in (start - 1e-6, end + 1e-6, math.nan):
        with pytest.raises(ValueError):
            stepper.state_at(outside)
    with pytest.raises(ValueError):  # read-only
        stepper.state_at(0.5 * (start + end))[0] = 0.0
    with pytest.raises(ValueError):
        stepper.state[0] = 0.0


def test_a_later_start_gives_the_same_motion_to_within_the_solvers_accuracy():
    """The physics does not care when a particle starts. The arithmetic does, a little.

    The solver rounds each new time t + h, and near t = 1000 that rounding is coarser than near
    t = 0. A borderline decision about a step can then fall the other way, so the two runs do
    not take identical steps. The motion they describe agrees to the solver's accuracy.
    """
    early = AdaptiveStepper(acceleration, ellipse(), start_time=0.0)
    late = AdaptiveStepper(acceleration, ellipse(), start_time=1000.0)
    elapsed = PERIOD / 2
    while early.time < elapsed:
        early.step()
    while late.time < 1000.0 + elapsed:
        late.step()
    assert distance(late.state_at(1000.0 + elapsed), early.state_at(elapsed)) < 1e-6
    assert early.state_at(elapsed)[:2] == pytest.approx([-150.0, 0.0], abs=1e-5)  # apoapsis


def test_find_crossing_gives_the_moment_a_quantity_passes_zero():
    # On a circle of radius 100 the particle crosses the y axis (x = 0) a quarter period on.
    stepper = AdaptiveStepper(acceleration, circular_orbit(100.0))
    while stepper.time < PERIOD / 4:
        stepper.step()
    crossing = stepper.find_crossing(lambda state: state[0], stepper.step_start, stepper.time)
    assert crossing == pytest.approx(PERIOD / 4, rel=1e-9)
    assert stepper.state_at(crossing)[:2] == pytest.approx([0.0, 100.0], abs=1e-7)


@pytest.mark.parametrize(
    "arguments",
    [
        {"start_time": math.nan},
        {"start_time": math.inf},
        {"rtol": 1e-14},
        {"rtol": 1.0},
        {"atol": 0.0},
        {"initial_state": [1.0, 0.0, 0.0]},
        {"initial_state": [1.0, math.inf, 0.0, 0.0]},
    ],
)
def test_invalid_arguments_are_refused(arguments):
    valid = {"initial_state": ellipse()}
    with pytest.raises(ValueError):
        AdaptiveStepper(acceleration, **(valid | arguments))
