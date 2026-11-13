"""DOP853 with events: Kepler times, free fall, tolerances, and what adaptivity buys."""

import math

import numpy as np
import pytest

from bhlab.physics.newtonian import acceleration, circular_orbit, kepler_period, make_state
from bhlab.physics.orbital_elements import orbital_elements
from bhlab.solvers.adaptive import (
    EventSpec,
    apoapsis,
    integrate_adaptive,
    periapsis,
    radius_reached,
)
from bhlab.solvers.fixed_step import integrate

PERIOD = kepler_period(100.0)  # 2000π ≈ 6283


def ellipse(semi_major_axis, eccentricity):
    r_p = semi_major_axis * (1.0 - eccentricity)
    return make_state(r_p, 0.0, 0.0, math.sqrt(2.0 / r_p - 1.0 / semi_major_axis))


def end_error(run, start):
    return float(np.hypot(*(run.states[-1, :2] - start[:2])))


@pytest.fixture(scope="module")
def three_orbits():
    """Three orbits of the a = 100, e = 0.5 ellipse, watching for every kind of event."""
    start = ellipse(100.0, 0.5)
    events = (periapsis(), apoapsis(), radius_reached(100.0, direction=+1))
    return start, integrate_adaptive(acceleration, start, 3 * PERIOD, events=events)


# --- the run as a whole ----------------------------------------------------------------------


def test_run_reaches_its_end_time_and_cannot_be_changed(three_orbits):
    _start, run = three_orbits
    assert run.stopped_by is None
    assert run.times[0] == 0.0 and run.times[-1] == pytest.approx(3 * PERIOD, rel=1e-15)
    assert run.states.shape == (run.n_steps + 1, 4)
    assert np.all(np.diff(run.times) > 0.0)
    assert [event.time for event in run.events] == sorted(event.time for event in run.events)
    with pytest.raises(ValueError):
        run.states[0, 0] = 1.0


def test_orbital_elements_stay_constant_along_the_run(three_orbits):
    _start, run = three_orbits
    elements = [orbital_elements(state) for state in run.states]
    axes = [e.semi_major_axis for e in elements]
    eccentricities = [e.eccentricity for e in elements]
    angles = [e.periapsis_angle for e in elements]
    # Measured over three orbits: 7.7e-8 in a (relative 7.7e-10), 3.6e-10 in e, 2.4e-10 rad.
    assert (max(axes) - min(axes)) / 100.0 < 1e-8
    assert max(eccentricities) - min(eccentricities) < 1e-8
    assert max(abs(angle) for angle in angles) < 1e-8


def test_tighter_tolerances_give_smaller_errors():
    start = ellipse(100.0, 0.5)
    errors = [
        end_error(
            integrate_adaptive(acceleration, start, PERIOD, rtol=rtol, atol=rtol / 100), start
        )
        for rtol in (1e-6, 1e-8, 1e-10, 1e-12)
    ]
    # Measured: 1.5e-4, 4.2e-6, 8.8e-8, 1.7e-9.
    assert errors == sorted(errors, reverse=True)
    assert errors[-1] < 1e-8


def test_adaptive_steps_beat_fixed_steps_on_an_eccentric_orbit():
    """At e = 0.9 the particle passes periapsis at r = 10 and turns around at r = 190."""
    start = ellipse(100.0, 0.9)
    adaptive = integrate_adaptive(acceleration, start, PERIOD)
    fixed = integrate(acceleration, start, PERIOD / 2500, 2500, "rk4")  # 10 000 evaluations
    # Measured: DOP853 1.1e-6 with 1334 evaluations; RK4 with 7.5 times the work, about 0.03.
    assert end_error(adaptive, start) < 1e-5
    assert adaptive.n_evaluations < 2000
    assert end_error(fixed, start) > 1000 * end_error(adaptive, start)
    # The steps are small near periapsis and large near apoapsis.
    steps = np.diff(adaptive.times)
    radii = np.hypot(adaptive.states[:-1, 0], adaptive.states[:-1, 1])
    assert steps[radii.argmax()] > 10 * steps[radii.argmin()]


# --- events against Kepler's laws ------------------------------------------------------------


def test_periapsis_and_apoapsis_come_once_per_period(three_orbits):
    _start, run = three_orbits
    apoapses = [event.time / PERIOD for event in run.events_named("apoapsis")]
    periapses = [event.time / PERIOD for event in run.events_named("periapsis")]
    assert apoapses == pytest.approx([0.5, 1.5, 2.5], rel=1e-8)
    # The start at periapsis is not reported. The return after three orbits may fall a hair
    # after the end time, within the tolerance, so only the first two returns are required.
    assert periapses[:2] == pytest.approx([1.0, 2.0], rel=1e-8)
    for event in run.events_named("apoapsis"):
        assert math.hypot(event.state[0], event.state[1]) == pytest.approx(150.0, rel=1e-8)


def test_crossing_time_agrees_with_keplers_equation(three_orbits):
    # r = a(1 − e cos E) = 100 needs cos E = 0, so E = π/2, and the time since periapsis is
    # t = √(a³) (E − e sin E) = 1000 (π/2 − 0.5) ≈ 1070.80.
    _start, run = three_orbits
    expected = 1000.0 * (math.pi / 2 - 0.5)
    crossings = [event.time for event in run.events_named("r = 100")]
    assert crossings == pytest.approx([expected + k * PERIOD for k in range(3)], rel=1e-9)


def test_free_fall_stops_at_the_chosen_radius_at_the_analytic_time():
    # Falling from rest at r₀: r = r₀ cos²η, t = √(r₀³/2) (η + sin η cos η).
    r0, r_stop = 10.0, 2.0
    eta = math.acos(math.sqrt(r_stop / r0))
    expected = math.sqrt(r0**3 / 2.0) * (eta + math.sin(eta) * math.cos(eta))  # 33.70
    run = integrate_adaptive(
        acceleration,
        make_state(r0, 0.0, 0.0, 0.0),
        1000.0,
        events=(radius_reached(r_stop, direction=-1, stop=True),),
    )
    assert run.stopped_by == "r = 2"
    assert run.times[-1] == pytest.approx(expected, rel=1e-9)
    assert math.hypot(*run.states[-1, :2]) == pytest.approx(r_stop, abs=1e-9)
    assert len(run.events) == 1 and run.events[0].time == run.times[-1]


def test_an_outward_crossing_is_not_mistaken_for_an_inward_one():
    run = integrate_adaptive(
        acceleration,
        ellipse(100.0, 0.5),
        PERIOD / 4,  # periapsis to beyond r = 100, moving outward the whole time
        events=(radius_reached(100.0, direction=-1, stop=True),),
    )
    assert run.stopped_by is None and run.events == ()


# --- invalid input ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "arguments",
    [
        {"duration": 0.0},
        {"duration": -1.0},
        {"duration": math.inf},
        {"duration": math.nan},
        {"rtol": 0.0},
        {"rtol": 1e-14},  # SciPy would quietly raise this to 2.2e-14
        {"rtol": 1.0},
        {"rtol": math.nan},
        {"atol": 0.0},
        {"atol": math.nan},
        {"initial_state": [1.0, 0.0, 0.0]},
        {"initial_state": [1.0, math.nan, 0.0, 0.0]},
        {"events": (periapsis(), periapsis())},  # two events with one name
    ],
)
def test_invalid_arguments_are_refused(arguments):
    valid = {"initial_state": circular_orbit(100.0), "duration": 10.0}
    with pytest.raises(ValueError):
        integrate_adaptive(acceleration, **(valid | arguments))


def test_a_run_that_would_stop_before_it_starts_is_refused():
    with pytest.raises(ValueError, match="stop at once"):
        integrate_adaptive(
            acceleration,
            make_state(2.0, 0.0, 0.0, 0.0),
            10.0,
            events=(radius_reached(2.0, stop=True),),
        )


@pytest.mark.parametrize(("radius", "direction"), [(0.0, 0), (-1.0, 0), (math.inf, 0), (5.0, 2)])
def test_radius_events_need_a_positive_radius_and_a_valid_direction(radius, direction):
    with pytest.raises(ValueError):
        radius_reached(radius, direction=direction)


def test_custom_events_can_be_watched():
    # Crossing the y axis (x = 0) going left happens a quarter of the way round a circle.
    crossing = EventSpec("x = 0", lambda _t, y: float(y[0]), direction=-1)
    run = integrate_adaptive(acceleration, circular_orbit(100.0), PERIOD, events=(crossing,))
    assert [event.time for event in run.events] == pytest.approx([PERIOD / 4], rel=1e-9)
