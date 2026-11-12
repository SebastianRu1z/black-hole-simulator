"""Number and quantity formatting."""

import math

import pytest

from bhlab.formatting import (
    format_length_au,
    format_length_si,
    format_mass_si,
    format_mass_solar,
    format_number,
    format_time_convenient,
    format_time_si,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (29.5325, "29.53"),
        (1.0, "1.000"),
        (0.0848874, "0.08489"),
        (12345.678, "12346"),
        (-29.5325, "-29.53"),
        (1.26989753e7, "1.270 × 10⁷"),
        (1.97413e-7, "1.974 × 10⁻⁷"),
        (1.98840987e31, "1.988 × 10³¹"),
        (0.0, "0"),
    ],
)
def test_format_number_uses_four_significant_figures(value, expected):
    assert format_number(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (99999.6, "1.000 × 10⁵"),  # rounds up across the fixed/scientific boundary
        (0.0099996, "0.01000"),  # rounds up into the fixed range
        (99.996, "100.0"),  # rounding adds a digit before the point
    ],
)
def test_format_number_rounds_before_choosing_the_notation(value, expected):
    assert format_number(value) == expected


def test_format_number_with_other_precision():
    assert format_number(4.3e6, sig=2) == "4.3 × 10⁶"
    assert format_number(10.0, sig=2) == "10"
    with pytest.raises(ValueError):
        format_number(1.0, sig=0)


def test_format_number_names_values_that_are_not_finite():
    assert format_number(math.nan) == "not a number"
    assert format_number(math.inf) == "∞"
    assert format_number(-math.inf) == "-∞"


@pytest.mark.parametrize(
    ("metres", "expected"),
    [
        (8.87e-3, "8.870 mm"),
        (500.0, "500.0 m"),
        (1476.625, "1.477 km"),
        (29532.5, "29.53 km"),
        (1.26989753e10, "1.270 × 10⁷ km"),
    ],
)
def test_lengths_pick_a_readable_si_unit(metres, expected):
    assert format_length_si(metres) == expected


def test_lengths_in_astronomical_units():
    assert format_length_au(1.26989753e10) == "0.08489 AU"
    assert format_length_au(29532.5) == "1.974 × 10⁻⁷ AU"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (4.925490947e-5, "49.25 µs"),
        (2.5e-3, "2.500 ms"),
        (21.18, "21.18 s"),
        (90.0, "1.500 min"),
        (32015.69, "8.893 h"),
        (2.0e5, "2.315 d"),
        (3.2e7, "1.014 yr"),
    ],
)
def test_times_pick_a_readable_unit(seconds, expected):
    assert format_time_convenient(seconds) == expected


def test_times_in_seconds():
    assert format_time_si(4.925490947e-5) == "4.925 × 10⁻⁵ s"


def test_masses():
    assert format_mass_solar(10.0) == "10.00 M☉"
    assert format_mass_si(1.98840987e31) == "1.988 × 10³¹ kg"
