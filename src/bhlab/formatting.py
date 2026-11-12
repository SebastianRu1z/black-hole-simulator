"""Human-readable formatting of physical quantities.

Pure Python with no dependency on the graphical interface, so the same text can be used in the
window, on the command line and in exported reports.
"""

import math

from bhlab.constants import AU, DAY, JULIAN_YEAR, LIGHT_YEAR

_SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")

# (size of the unit in SI, symbol), smallest first.
_Ladder = tuple[tuple[float, str], ...]
_LENGTH_SI: _Ladder = ((1e-3, "mm"), (1.0, "m"), (1e3, "km"))
_TIME_CONVENIENT: _Ladder = (
    (1e-6, "µs"),
    (1e-3, "ms"),
    (1.0, "s"),
    (60.0, "min"),
    (3600.0, "h"),
    (DAY, "d"),
    (JULIAN_YEAR, "yr"),
)


def format_number(value: float, sig: int = 4) -> str:
    """Format ``value`` with ``sig`` significant figures.

    Plain decimals are used for 0.01 ≤ |value| < 100 000 and the form ``a × 10ⁿ`` otherwise.
    """
    if sig < 1:
        raise ValueError(f"sig must be at least 1; got {sig}")
    if math.isnan(value):
        return "not a number"
    if math.isinf(value):
        return "∞" if value > 0 else "-∞"
    if value == 0.0:
        return "0"
    # Let Python do the rounding first, so 99999.6 becomes 1.000 × 10⁵ and not 10.000 × 10⁴.
    mantissa, exponent_text = f"{value:.{sig - 1}e}".split("e")
    exponent = int(exponent_text)
    if -2 <= exponent < 5:
        return f"{value:.{max(sig - 1 - exponent, 0)}f}"
    return f"{mantissa} × 10{str(exponent).translate(_SUPERSCRIPT)}"


def _with_unit(value: float, ladder: _Ladder, sig: int) -> str:
    """Express ``value`` in the largest unit of ``ladder`` that keeps the number at 1 or more."""
    scale, symbol = ladder[0]
    for candidate_scale, candidate_symbol in ladder:
        if abs(value) >= candidate_scale:
            scale, symbol = candidate_scale, candidate_symbol
    return f"{format_number(value / scale, sig)} {symbol}"


def format_length_si(metres: float, sig: int = 4) -> str:
    """A length in mm, m or km, whichever reads best."""
    return _with_unit(metres, _LENGTH_SI, sig)


def format_length_au(metres: float, sig: int = 4) -> str:
    """A length in astronomical units."""
    return f"{format_number(metres / AU, sig)} AU"


def format_length_auto(metres: float, sig: int = 4) -> str:
    """A length in the unit that reads best for any black hole mass.

    Light-years from 0.1 ly, astronomical units from 0.01 AU, otherwise mm, m or km.
    """
    size = abs(metres)
    if size >= 0.1 * LIGHT_YEAR:
        return f"{format_number(metres / LIGHT_YEAR, sig)} ly"
    if size >= 0.01 * AU:
        return f"{format_number(metres / AU, sig)} AU"
    return format_length_si(metres, sig)


def format_time_si(seconds: float, sig: int = 4) -> str:
    """A time in seconds."""
    return f"{format_number(seconds, sig)} s"


def format_time_convenient(seconds: float, sig: int = 4) -> str:
    """A time in the everyday unit that reads best, from microseconds to Julian years."""
    return _with_unit(seconds, _TIME_CONVENIENT, sig)


def format_mass_si(kilograms: float, sig: int = 4) -> str:
    """A mass in kilograms."""
    return f"{format_number(kilograms, sig)} kg"


def format_mass_solar(solar_masses: float, sig: int = 4) -> str:
    """A mass in solar masses."""
    return f"{format_number(solar_masses, sig)} M☉"
