"""Unit systems and the characteristic scales of a black hole.

Geometrized units
-----------------
General relativity has no built-in scale: the Schwarzschild solution for a mass M is the solution
for unit mass with every length and every time multiplied by M. Setting G = c = 1 makes this
explicit. With GM the gravitational parameter of the black hole,

    length unit   r_g = GM / c²     the gravitational radius
    time unit     t_g = GM / c³     the time light needs to travel r_g
    speed unit    c

Equations of motion in this project are solved in these dimensionless units, so one numerical
solution describes a black hole of any mass. :class:`BlackHole` converts to and from SI.

Reference radii
---------------
For a non-rotating, uncharged (Schwarzschild) black hole, in units of r_g:

    event horizon                      r_s    = 2
    photon sphere                      r_ph   = 3
    innermost stable circular orbit    r_ISCO = 6

These are exact results of general relativity. They enter this module as stated values;
recovering them numerically from the geodesic equations is part of Stage 2 of the project.
"""

import math
from dataclasses import dataclass
from typing import Final, Self

from bhlab.constants import GM_SUN, C, G

HORIZON_RADIUS_RG: Final[float] = 2.0
"""Event horizon (Schwarzschild radius) in units of GM/c²."""

PHOTON_SPHERE_RADIUS_RG: Final[float] = 3.0
"""Photon sphere in units of GM/c²."""

ISCO_RADIUS_RG: Final[float] = 6.0
"""Innermost stable circular orbit in units of GM/c²."""


def _require_positive_finite(value: float, what: str) -> None:
    if not (math.isfinite(value) and value > 0.0):
        raise ValueError(f"{what} must be a positive, finite number; got {value!r}")


@dataclass(frozen=True, slots=True)
class BlackHole:
    """A non-rotating, uncharged black hole, specified by its gravitational parameter.

    The mass enters every length and time only through the product GM, so GM is what is
    stored. Use :meth:`from_solar_masses` or :meth:`from_kilograms` to create one.

    Parameters
    ----------
    gm:
        Gravitational parameter GM in m³ s⁻². Must be positive and finite.
    """

    gm: float

    def __post_init__(self) -> None:
        _require_positive_finite(self.gm, "The gravitational parameter GM")

    # --- construction -------------------------------------------------------------------

    @classmethod
    def from_solar_masses(cls, solar_masses: float) -> Self:
        """Create a black hole from its mass in solar masses (independent of G)."""
        _require_positive_finite(solar_masses, "The mass in solar masses")
        return cls(gm=solar_masses * GM_SUN)

    @classmethod
    def from_kilograms(cls, kilograms: float) -> Self:
        """Create a black hole from its mass in kilograms (uses G, uncertain at 2.2e-5)."""
        _require_positive_finite(kilograms, "The mass in kilograms")
        return cls(gm=kilograms * G)

    # --- mass ---------------------------------------------------------------------------

    @property
    def mass_solar(self) -> float:
        """Mass in solar masses."""
        return self.gm / GM_SUN

    @property
    def mass_kg(self) -> float:
        """Mass in kilograms."""
        return self.gm / G

    # --- geometrized units --------------------------------------------------------------

    @property
    def length_unit(self) -> float:
        """Gravitational radius r_g = GM/c², in metres: one unit of length."""
        return self.gm / C**2

    @property
    def time_unit(self) -> float:
        """t_g = GM/c³, in seconds: one unit of time."""
        return self.gm / C**3

    def length_to_si(self, length: float) -> float:
        """Convert a length in units of GM/c² to metres."""
        return length * self.length_unit

    def length_from_si(self, metres: float) -> float:
        """Convert a length in metres to units of GM/c²."""
        return metres / self.length_unit

    def time_to_si(self, time: float) -> float:
        """Convert a time in units of GM/c³ to seconds."""
        return time * self.time_unit

    def time_from_si(self, seconds: float) -> float:
        """Convert a time in seconds to units of GM/c³."""
        return seconds / self.time_unit

    # --- reference radii ----------------------------------------------------------------

    @property
    def schwarzschild_radius(self) -> float:
        """Event horizon r_s = 2GM/c², in metres."""
        return HORIZON_RADIUS_RG * self.length_unit

    @property
    def photon_sphere_radius(self) -> float:
        """Photon sphere r_ph = 3GM/c², in metres."""
        return PHOTON_SPHERE_RADIUS_RG * self.length_unit

    @property
    def isco_radius(self) -> float:
        """Innermost stable circular orbit r_ISCO = 6GM/c², in metres."""
        return ISCO_RADIUS_RG * self.length_unit


def speed_to_si(speed: float) -> float:
    """Convert a speed given as a fraction of c to metres per second."""
    return speed * C


def speed_from_si(metres_per_second: float) -> float:
    """Convert a speed in metres per second to a fraction of c."""
    return metres_per_second / C
