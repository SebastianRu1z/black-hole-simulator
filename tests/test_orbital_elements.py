"""Orbital elements from a single state, checked against conics worked out by hand."""

import math

import numpy as np
import pytest

from bhlab.physics.newtonian import circular_orbit, make_state
from bhlab.physics.orbital_elements import orbital_elements


def periapsis_state(semi_major_axis, eccentricity):
    """Start at periapsis on the +x axis, speed from the vis-viva equation v² = 2/r − 1/a."""
    r_p = semi_major_axis * (1.0 - eccentricity)
    return make_state(r_p, 0.0, 0.0, math.sqrt(2.0 / r_p - 1.0 / semi_major_axis))


def rotated(state, angle):
    """The same orbit turned anticlockwise by ``angle`` about the mass."""
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.array([[c, -s], [s, c]])
    x, v = rotation @ state[:2], rotation @ state[2:]
    return make_state(x[0], x[1], v[0], v[1])


def test_circle():
    elements = orbital_elements(circular_orbit(100.0))
    assert elements.kind == "bound"
    assert elements.eccentricity < 1e-14
    assert elements.semi_major_axis == pytest.approx(100.0, rel=1e-14)
    assert elements.periapsis == pytest.approx(100.0, rel=1e-14)
    assert elements.apoapsis == pytest.approx(100.0, rel=1e-14)
    assert elements.period == pytest.approx(2000.0 * math.pi, rel=1e-14)
    assert elements.periapsis_angle is None  # a circle has no periapsis


def test_ellipse_started_at_periapsis():
    elements = orbital_elements(periapsis_state(100.0, 0.5))
    assert elements.kind == "bound"
    assert elements.eccentricity == pytest.approx(0.5, rel=1e-14)
    assert elements.semi_major_axis == pytest.approx(100.0, rel=1e-14)
    assert elements.periapsis == pytest.approx(50.0, rel=1e-14)
    assert elements.apoapsis == pytest.approx(150.0, rel=1e-14)
    assert elements.energy == pytest.approx(-0.005, rel=1e-14)  # E = −1/(2a)
    assert elements.angular_momentum == pytest.approx(math.sqrt(100.0 * 0.75), rel=1e-14)
    assert elements.periapsis_angle == pytest.approx(0.0, abs=1e-15)


def test_ellipse_seen_from_a_point_between_periapsis_and_apoapsis():
    # The a = 100, e = 0.5 ellipse at eccentric anomaly E = π/2, where r = a(1 − e cos E) = 100:
    #   position  x = a(cos E − e) = −50,  y = a√(1 − e²) sin E = 86.60
    #   velocity  (−a sin E, a√(1 − e²) cos E)·dE/dt with dE/dt = n/(1 − e cos E) = 1/a^(3/2)
    #             = (−0.1, 0)
    # Here r·v ≠ 0, so every term of the eccentricity vector matters.
    state = make_state(-50.0, 100.0 * math.sqrt(0.75), -0.1, 0.0)
    elements = orbital_elements(state)
    assert elements.semi_major_axis == pytest.approx(100.0, rel=1e-13)
    assert elements.eccentricity == pytest.approx(0.5, rel=1e-13)
    assert elements.periapsis_angle == pytest.approx(0.0, abs=1e-13)


@pytest.mark.parametrize("degrees", [30.0, 135.0, -60.0])
def test_turning_the_orbit_turns_only_the_periapsis_direction(degrees):
    reference = orbital_elements(periapsis_state(100.0, 0.5))
    elements = orbital_elements(rotated(periapsis_state(100.0, 0.5), math.radians(degrees)))
    assert math.degrees(elements.periapsis_angle) == pytest.approx(degrees, rel=1e-12)
    assert elements.eccentricity == pytest.approx(reference.eccentricity, rel=1e-12)
    assert elements.semi_major_axis == pytest.approx(reference.semi_major_axis, rel=1e-12)


def test_ellipse_started_at_apoapsis_points_periapsis_the_other_way():
    # At apoapsis r = 150 on the +x axis, moving at the vis-viva speed: periapsis lies along −x.
    state = make_state(150.0, 0.0, 0.0, math.sqrt(2.0 / 150.0 - 1.0 / 100.0))
    elements = orbital_elements(state)
    assert elements.periapsis == pytest.approx(50.0, rel=1e-13)
    assert abs(elements.periapsis_angle) == pytest.approx(math.pi, rel=1e-13)


def test_clockwise_motion_has_negative_angular_momentum_and_the_same_shape():
    state = periapsis_state(100.0, 0.5) * np.array([1.0, 1.0, 1.0, -1.0])
    elements = orbital_elements(state)
    assert elements.angular_momentum < 0.0
    assert elements.eccentricity == pytest.approx(0.5, rel=1e-14)
    assert elements.periapsis_angle == pytest.approx(0.0, abs=1e-15)


def test_hyperbola():
    # At r = 50 with v² = 2/50 + 0.01 the energy is E = +0.005, so a = −1/(2E) = −100 and
    # r_p = a(1 − e) gives e = 1.5.
    elements = orbital_elements(make_state(50.0, 0.0, 0.0, math.sqrt(0.05)))
    assert elements.kind == "unbound"
    assert elements.semi_major_axis == pytest.approx(-100.0, rel=1e-13)
    assert elements.eccentricity == pytest.approx(1.5, rel=1e-13)
    assert elements.periapsis == pytest.approx(50.0, rel=1e-13)
    assert math.isinf(elements.apoapsis) and math.isinf(elements.period)


def test_parabola():
    # At r = 2 with v = 1: v²/2 = 1/r exactly, so E = 0, e = 1 and r_p = L²/2 = 2.
    elements = orbital_elements(make_state(2.0, 0.0, 0.0, 1.0))
    assert elements.kind == "parabolic"
    assert elements.energy == 0.0
    assert elements.eccentricity == pytest.approx(1.0, rel=1e-15)
    assert elements.periapsis == pytest.approx(2.0, rel=1e-15)
    assert math.isinf(elements.semi_major_axis) and math.isinf(elements.period)


def test_fall_from_rest_is_a_flattened_ellipse():
    # From rest at r = 10: L = 0, e = 1, a = 5, so the "orbit" runs from 10 into the mass.
    elements = orbital_elements(make_state(10.0, 0.0, 0.0, 0.0))
    assert elements.angular_momentum == 0.0
    assert elements.eccentricity == pytest.approx(1.0, rel=1e-15)
    assert elements.semi_major_axis == pytest.approx(5.0, rel=1e-15)
    assert elements.periapsis == 0.0
    assert elements.apoapsis == pytest.approx(10.0, rel=1e-15)
    assert elements.periapsis_angle == pytest.approx(math.pi, rel=1e-15)  # never −π


@pytest.mark.parametrize(
    "state", [(0.0, 0.0, 0.1, 0.0), (math.nan, 1.0, 0.0, 0.0), (1.0, 0.0, math.inf, 0.0)]
)
def test_states_without_an_orbit_are_refused(state):
    with pytest.raises(ValueError):
        orbital_elements(np.array(state))
