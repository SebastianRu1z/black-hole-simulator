"""Physical and astronomical constants, in SI units.

Sources
-------
Speed of light ``C``
    Exact, by the definition of the metre.
Newtonian constant of gravitation ``G``
    CODATA 2022 recommended value, 6.674 30(15) × 10⁻¹¹ m³ kg⁻¹ s⁻² (unchanged from CODATA 2018),
    relative standard uncertainty 2.2 × 10⁻⁵. https://physics.nist.gov/cuu/Constants/
Astronomical unit ``AU``
    Exact, by IAU 2012 Resolution B2.
Nominal solar mass parameter ``GM_SUN``
    (GM)☉ = 1.327 124 4 × 10²⁰ m³ s⁻², an exact conversion constant defined by IAU 2015
    Resolution B3 (Prša et al. 2016, The Astronomical Journal 152, 41).

Why masses are converted with ``GM_SUN`` rather than ``G``
-----------------------------------------------------------
Tracking of planets and spacecraft measures the product GM of the Sun to better than one part
in a billion, while G on its own is known to only about two parts in 100 000. Every length and
time in this project depends on a mass only through GM. A mass given in solar masses is
therefore converted with ``GM_SUN`` and never touches G; G is needed only to express a mass in
kilograms.
"""

from typing import Final

C: Final[float] = 299_792_458.0
"""Speed of light in vacuum, m/s (exact)."""

G: Final[float] = 6.67430e-11
"""Newtonian constant of gravitation, m³ kg⁻¹ s⁻² (CODATA 2022, relative uncertainty 2.2e-5)."""

GM_SUN: Final[float] = 1.327_124_4e20
"""Nominal solar mass parameter (GM)☉, m³ s⁻² (IAU 2015 Resolution B3, exact by definition)."""

AU: Final[float] = 149_597_870_700.0
"""Astronomical unit, m (IAU 2012 Resolution B2, exact)."""

M_SUN_KG: Final[float] = GM_SUN / G
"""Solar mass in kilograms, about 1.9884e30 kg. Carries the uncertainty of G."""

DAY: Final[float] = 86_400.0
"""Day, s."""

JULIAN_YEAR: Final[float] = 365.25 * DAY
"""Julian year, s. The year astronomy uses, for example in the definition of the light-year."""
