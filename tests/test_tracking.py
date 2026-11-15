"""The tracker's numbers, checked against hand calculations and against the solver itself."""

import math

import numpy as np
import pytest

from bhlab.physics.newtonian import acceleration, circular_orbit, kepler_period, make_state
from bhlab.simulation.tracking import reliability, time_to_next_periapsis, track
from bhlab.solvers.adaptive import integrate_adaptive, periapsis

ELLIPSE_AT_PERIAPSIS = make_state(50.0, 0.0, 0.0, math.sqrt(0.03))  # a = 100, e = 0.5


def test_speeds_of_a_circular_orbit():
    t = track(circular_orbit(8.0), 2.0)
    assert t.speed == pytest.approx(math.sqrt(1 / 8), rel=1e-15)
    assert t.circular_speed == pytest.approx(t.speed, rel=1e-15)
    assert t.escape_speed == pytest.approx(math.sqrt(2 / 8), rel=1e-15)
    assert t.speed_over_escape == pytest.approx(1 / math.sqrt(2), rel=1e-15)
    assert t.radial_speed == 0.0 and t.angle == 0.0
    assert t.fate == "bound" and t.time_to_periapsis is None  # a circle has no periapsis


def test_position_angle_and_radial_speed():
    t = track(make_state(-3.0, -4.0, 0.3, 0.4), 2.0)  # moving straight in, towards the centre
    assert (t.r, t.speed) == pytest.approx((5.0, 0.5))
    assert t.angle == pytest.approx(math.degrees(math.atan2(-4, -3)) + 360.0)  # 233.13°
    assert t.radial_speed == pytest.approx(-0.5)


@pytest.mark.parametrize(
    ("state", "fate"),
    [
        (ELLIPSE_AT_PERIAPSIS, "bound"),
        (make_state(10.0, 0.0, 0.0, 0.0), "reaches stop radius"),  # at rest: falls in
        (make_state(10.0, 0.0, 0.6, 0.0), "escapes"),  # fast and outward
        (make_state(10.0, 0.0, -0.6, 0.0), "reaches stop radius"),  # fast but straight inward
        (make_state(10.0, 0.0, 0.0, 0.5), "escapes"),  # sideways, above √(2/10) = 0.447
    ],
)
def test_fate(state, fate):
    assert track(state, 2.0).fate == fate


def test_a_stopped_particle_is_reported_as_stopped():
    t = track(make_state(2.0, 0.0, -0.9, 0.0), 2.0, stopped=True)
    assert t.fate == "stopped" and t.time_to_periapsis is None


def test_speed_over_escape_speed_separates_bound_from_escaping():
    for vy in (0.40, 0.44, 0.45, 0.50):
        t = track(make_state(10.0, 0.0, 0.0, vy), 2.0)
        assert (t.speed_over_escape < 1.0) == (t.elements.kind == "bound")


def test_time_to_periapsis_from_periapsis_and_apoapsis():
    period = kepler_period(100.0)
    at_periapsis = track(ELLIPSE_AT_PERIAPSIS, 2.0)
    assert at_periapsis.time_to_periapsis == pytest.approx(0.0, abs=1e-9) or (
        at_periapsis.time_to_periapsis == pytest.approx(period, rel=1e-12)
    )
    at_apoapsis = make_state(150.0, 0.0, 0.0, math.sqrt(2 / 150 - 1 / 100))
    assert track(at_apoapsis, 2.0).time_to_periapsis == pytest.approx(period / 2, rel=1e-12)


@pytest.mark.parametrize("fraction", [0.1, 0.37, 0.5, 0.83])
def test_time_to_periapsis_agrees_with_the_solver(fraction):
    """Run the ellipse part of an orbit, then compare the prediction from that state with the
    periapsis the solver finds by integrating onwards."""
    period = kepler_period(100.0)
    run = integrate_adaptive(acceleration, ELLIPSE_AT_PERIAPSIS, fraction * period)
    state = run.states[-1]
    predicted = time_to_next_periapsis(state, track(state, 2.0).elements)
    onward = integrate_adaptive(acceleration, state, period, events=(periapsis(),))
    (event,) = onward.events_named("periapsis")
    assert predicted == pytest.approx(event.time, rel=1e-8)
    assert predicted == pytest.approx((1.0 - fraction) * period, rel=1e-8)


def test_time_to_periapsis_with_a_rotated_orbit():
    angle = 2.0
    rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
    position = rotation @ np.array([150.0, 0.0])
    velocity = rotation @ np.array([0.0, math.sqrt(2 / 150 - 1 / 100)])
    state = make_state(*position, *velocity)
    assert track(state, 2.0).time_to_periapsis == pytest.approx(kepler_period(100) / 2, rel=1e-10)


@pytest.mark.parametrize(
    ("r", "speed", "expected"),
    [
        (500.0, 0.05, "good"),  # 1/r = 0.002, v² = 0.0025
        (100.5, 0.0, "good"),
        (99.0, 0.0, "approximate"),  # 1/r just above 1 %
        (500.0, 0.11, "approximate"),  # v² = 1.2 %
        (11.0, 0.0, "approximate"),
        (9.0, 0.0, "rough"),
        (500.0, 0.33, "rough"),
    ],
)
def test_reliability_follows_the_size_of_the_relativistic_corrections(r, speed, expected):
    assert reliability(r, speed) == expected
