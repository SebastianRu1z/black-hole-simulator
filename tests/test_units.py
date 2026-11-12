"""Unit conversions and black-hole scales, checked against published values and exact relations."""

import dataclasses
import math

import pytest

from bhlab.constants import AU, M_SUN_KG, C
from bhlab.units import (
    HORIZON_RADIUS_RG,
    ISCO_RADIUS_RG,
    PHOTON_SPHERE_RADIUS_RG,
    BlackHole,
    speed_from_si,
    speed_to_si,
)

MASSES = [1e-6, 1.0, 10.0, 4.3e6, 6.5e9, 1e11]
BAD_NUMBERS = [0.0, -1.0, math.nan, math.inf, -math.inf]


# --- published values -----------------------------------------------------------------------


def test_solar_gravitational_radius_matches_published_value():
    # GM☉/c² = 1.4766 km, the "mass of the Sun in kilometres" of relativity textbooks.
    assert BlackHole.from_solar_masses(1.0).length_unit == pytest.approx(1476.625, rel=1e-6)


def test_solar_time_unit_matches_pulsar_timing_constant():
    # T☉ = GM☉/c³ = 4.925490947 µs, the constant used in pulsar timing.
    assert BlackHole.from_solar_masses(1.0).time_unit == pytest.approx(4.925490947e-6, rel=1e-9)


def test_solar_schwarzschild_radius_is_about_three_kilometres():
    assert BlackHole.from_solar_masses(1.0).schwarzschild_radius == pytest.approx(2953.25, rel=1e-6)


def test_earth_mass_black_hole_is_about_nine_millimetres():
    earth = BlackHole.from_kilograms(5.9722e24)
    assert earth.schwarzschild_radius == pytest.approx(8.870e-3, rel=1e-3)


def test_known_black_holes_in_astronomical_units():
    sgr_a = BlackHole.from_solar_masses(4.3e6)
    m87 = BlackHole.from_solar_masses(6.5e9)
    assert sgr_a.schwarzschild_radius / AU == pytest.approx(0.0849, rel=1e-3)
    assert m87.schwarzschild_radius / AU == pytest.approx(128.3, rel=1e-3)


# --- exact relations ------------------------------------------------------------------------


def test_reference_radii_in_gravitational_radii():
    assert (HORIZON_RADIUS_RG, PHOTON_SPHERE_RADIUS_RG, ISCO_RADIUS_RG) == (2.0, 3.0, 6.0)


@pytest.mark.parametrize("solar_masses", MASSES)
def test_reference_radii_are_fixed_multiples_of_the_length_unit(solar_masses):
    bh = BlackHole.from_solar_masses(solar_masses)
    assert bh.schwarzschild_radius == pytest.approx(2.0 * bh.length_unit, rel=1e-15)
    assert bh.photon_sphere_radius == pytest.approx(1.5 * bh.schwarzschild_radius, rel=1e-15)
    assert bh.isco_radius == pytest.approx(3.0 * bh.schwarzschild_radius, rel=1e-15)


@pytest.mark.parametrize("solar_masses", MASSES)
def test_every_scale_is_proportional_to_the_mass(solar_masses):
    sun = BlackHole.from_solar_masses(1.0)
    bh = BlackHole.from_solar_masses(solar_masses)
    for scale in ("length_unit", "time_unit", "schwarzschild_radius", "isco_radius", "mass_kg"):
        assert getattr(bh, scale) == pytest.approx(solar_masses * getattr(sun, scale), rel=1e-14)


@pytest.mark.parametrize("solar_masses", MASSES)
def test_light_crosses_one_length_unit_in_one_time_unit(solar_masses):
    bh = BlackHole.from_solar_masses(solar_masses)
    assert bh.length_unit / bh.time_unit == pytest.approx(C, rel=1e-15)


@pytest.mark.parametrize("solar_masses", MASSES)
def test_conversions_round_trip(solar_masses):
    bh = BlackHole.from_solar_masses(solar_masses)
    for value in (1e-9, 0.37, 6.0, 1.234e7):
        assert bh.length_from_si(bh.length_to_si(value)) == pytest.approx(value, rel=1e-14)
        assert bh.time_from_si(bh.time_to_si(value)) == pytest.approx(value, rel=1e-14)
        assert speed_from_si(speed_to_si(value)) == pytest.approx(value, rel=1e-14)
    assert bh.mass_solar == pytest.approx(solar_masses, rel=1e-14)


def test_the_isco_is_six_length_units_in_si():
    bh = BlackHole.from_solar_masses(10.0)
    assert bh.length_to_si(ISCO_RADIUS_RG) == pytest.approx(bh.isco_radius, rel=1e-15)
    assert bh.length_from_si(bh.schwarzschild_radius) == pytest.approx(2.0, rel=1e-15)


def test_speed_unit_is_the_speed_of_light():
    assert speed_to_si(1.0) == C
    assert speed_from_si(C) == 1.0
    assert speed_to_si(0.5) == C / 2


def test_kilograms_and_solar_masses_describe_the_same_black_hole():
    from_kg = BlackHole.from_kilograms(M_SUN_KG)
    from_solar = BlackHole.from_solar_masses(1.0)
    assert from_kg.gm == pytest.approx(from_solar.gm, rel=1e-14)
    assert from_kg.mass_kg == pytest.approx(M_SUN_KG, rel=1e-14)


# --- invalid input --------------------------------------------------------------------------


@pytest.mark.parametrize("bad", BAD_NUMBERS)
def test_non_physical_masses_are_rejected(bad):
    with pytest.raises(ValueError, match="positive, finite"):
        BlackHole(gm=bad)
    with pytest.raises(ValueError, match="positive, finite"):
        BlackHole.from_solar_masses(bad)
    with pytest.raises(ValueError, match="positive, finite"):
        BlackHole.from_kilograms(bad)


def test_a_mass_too_large_to_represent_is_rejected():
    with pytest.raises(ValueError, match="positive, finite"):
        BlackHole.from_solar_masses(1e300)


def test_black_hole_cannot_be_modified_after_creation():
    bh = BlackHole.from_solar_masses(10.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        bh.gm = 1.0  # type: ignore[misc]
