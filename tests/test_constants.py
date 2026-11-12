"""The constants, checked against their defining values and an independent table."""

import pytest

from bhlab import constants


def test_speed_of_light_is_the_exact_si_value():
    assert constants.C == 299_792_458.0


def test_astronomical_unit_is_the_exact_iau_value():
    assert constants.AU == 149_597_870_700.0


def test_light_year_follows_from_c_and_the_julian_year():
    # The IAU light-year is exactly 9 460 730 472 580 800 m.
    assert constants.C * constants.JULIAN_YEAR == 9_460_730_472_580_800.0


def test_solar_mass_in_kilograms():
    # Commonly quoted value: 1.9884e30 kg.
    assert pytest.approx(1.9884e30, rel=1e-4) == constants.M_SUN_KG
    assert pytest.approx(constants.GM_SUN, rel=1e-15) == constants.M_SUN_KG * constants.G


def test_values_agree_with_scipy_codata_table():
    """Independent check: SciPy ships the CODATA constants in its own table."""
    scipy_constants = pytest.importorskip("scipy.constants")
    assert scipy_constants.c == constants.C
    assert scipy_constants.G == constants.G
    assert scipy_constants.au == constants.AU
    assert scipy_constants.Julian_year == constants.JULIAN_YEAR
