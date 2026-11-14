"""Newtonian point-mass gravity, checked against hand calculations and Kepler's laws."""

import math

import numpy as np
import pytest

from bhlab.constants import GM_SUN, C
from bhlab.physics.newtonian import (
    acceleration,
    circular_orbit,
    circular_velocity,
    kepler_period,
    make_state,
    specific_angular_momentum,
    specific_energy,
)
from bhlab.units import BlackHole

# --- the force law ---------------------------------------------------------------------------


def test_acceleration_points_at_the_mass_and_falls_off_as_the_inverse_square():
    # At (3, 4): r = 5, so |a| = 1/25 = 0.04, directed along −(3, 4)/5.
    assert acceleration(np.array([3.0, 4.0])) == pytest.approx([-0.024, -0.032], rel=1e-15)


@pytest.mark.parametrize("direction", [(1.0, 0.0), (0.0, -1.0), (0.6, 0.8), (-0.28, 0.96)])
def test_doubling_the_distance_quarters_the_acceleration(direction):
    near = acceleration(10.0 * np.array(direction))
    far = acceleration(20.0 * np.array(direction))
    assert far == pytest.approx(near / 4.0, rel=1e-14)
    assert np.hypot(*near) == pytest.approx(1.0 / 100.0, rel=1e-14)


@pytest.mark.parametrize("position", [(0.0, 0.0), (math.nan, 1.0), (1.0, math.inf)])
def test_acceleration_is_refused_where_it_is_undefined(position):
    with pytest.raises(ValueError):
        acceleration(np.array(position))


def test_states_must_be_finite_and_not_at_the_mass():
    assert make_state(1.0, 2.0, 0.1, -0.2) == pytest.approx([1.0, 2.0, 0.1, -0.2])
    for bad in ((0.0, 0.0, 0.1, 0.0), (1.0, 0.0, math.nan, 0.0), (1.0, 0.0, 0.0, -math.inf)):
        with pytest.raises(ValueError):
            make_state(*bad)


# --- conserved quantities --------------------------------------------------------------------


def test_energy_and_angular_momentum_by_hand():
    state = make_state(3.0, 4.0, 0.1, 0.2)
    # E = (0.1² + 0.2²)/2 − 1/5 = 0.025 − 0.2;   L = 3·0.2 − 4·0.1
    assert specific_energy(state) == pytest.approx(-0.175, rel=1e-15)
    assert specific_angular_momentum(state) == pytest.approx(0.2, rel=1e-14)


def test_angular_momentum_is_negative_for_clockwise_motion():
    assert specific_angular_momentum(make_state(10.0, 0.0, 0.0, -0.3)) == pytest.approx(-3.0)


# --- circular orbits and Kepler's third law --------------------------------------------------


@pytest.mark.parametrize("radius", [6.0, 100.0, 1.0e4])
def test_circular_orbit_balances_gravity_and_centripetal_acceleration(radius):
    state = circular_orbit(radius)
    speed = np.hypot(state[2], state[3])
    assert state[:2] == pytest.approx([radius, 0.0])
    # v²/r must equal the gravitational acceleration 1/r².
    assert speed**2 / radius == pytest.approx(np.hypot(*acceleration(state[:2])), rel=1e-14)
    assert specific_energy(state) == pytest.approx(-1.0 / (2.0 * radius), rel=1e-14)
    assert specific_angular_momentum(state) == pytest.approx(math.sqrt(radius), rel=1e-14)


def test_circular_orbit_at_100_rg_by_hand():
    state = circular_orbit(100.0)
    assert state == pytest.approx([100.0, 0.0, 0.0, 0.1], rel=1e-15)  # v = √(1/100) = 0.1 c


@pytest.mark.parametrize(("x", "y"), [(10.0, 0.0), (0.0, 20.0), (-3.0, 4.0), (6.0, -8.0)])
def test_circular_velocity_is_perpendicular_anticlockwise_and_of_circular_speed(x, y):
    vx, vy = circular_velocity(x, y)
    radius = math.hypot(x, y)
    assert math.hypot(vx, vy) == pytest.approx(math.sqrt(1.0 / radius), rel=1e-15)
    assert x * vx + y * vy == pytest.approx(0.0, abs=1e-15)  # perpendicular to the position
    assert x * vy - y * vx > 0.0  # angular momentum is positive: anticlockwise


def test_circular_velocity_by_hand():
    # At (0, 25): speed √(1/25) = 0.2, pointing along −x.
    assert circular_velocity(0.0, 25.0) == pytest.approx((-0.2, 0.0), rel=1e-15, abs=1e-17)
    vx, vy = circular_velocity(100.0, 0.0)
    assert vy == pytest.approx(0.1, rel=1e-15)
    assert vx == 0.0 and math.copysign(1.0, vx) == 1.0  # a plain zero, never −0.0
    with pytest.raises(ValueError):
        circular_velocity(0.0, 0.0)


@pytest.mark.parametrize("radius", [0.0, -1.0, math.nan, math.inf])
def test_circular_orbit_needs_a_positive_finite_radius(radius):
    with pytest.raises(ValueError):
        circular_orbit(radius)


def test_kepler_period():
    assert kepler_period(100.0) == pytest.approx(2000.0 * math.pi, rel=1e-15)
    # T² ∝ a³: four times the size, eight times the period.
    assert kepler_period(400.0) / kepler_period(100.0) == pytest.approx(8.0, rel=1e-15)
    for bad in (0.0, -5.0, math.nan):
        with pytest.raises(ValueError):
            kepler_period(bad)


def test_period_in_seconds_agrees_with_the_si_form_of_keplers_law():
    """Geometrized units and SI must give the same period: T = 2π √(a³ / GM)."""
    black_hole = BlackHole.from_solar_masses(10.0)
    a_metres = 100.0 * GM_SUN * 10.0 / C**2
    t_si = 2.0 * math.pi * math.sqrt(a_metres**3 / (GM_SUN * 10.0))
    assert black_hole.time_to_si(kepler_period(100.0)) == pytest.approx(t_si, rel=1e-14)
    assert t_si == pytest.approx(0.3095, rel=1e-3)  # about a third of a second
