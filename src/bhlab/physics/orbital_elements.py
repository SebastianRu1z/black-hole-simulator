"""The shape of a Newtonian orbit, worked out from a single position and velocity.

Under Newtonian gravity of a point mass every orbit is a conic section: an ellipse (including the
circle), a parabola or a hyperbola, with the mass at one focus. Its size, shape and orientation
follow from one state, because energy, angular momentum and the eccentricity vector are constant
along the orbit. With GM = 1:

    energy               E = v²/2 − 1/r
    angular momentum     L = x v_y − y vₓ
    eccentricity vector  e = (v² − 1/r) r − (r·v) v      points at periapsis; its length is e

From these:

    semi-major axis      a = −1/(2E)        positive for an ellipse, negative for a hyperbola
    periapsis            r_p = L² / (1 + e)  closest approach, valid for every kind of orbit
    apoapsis             r_a = a (1 + e)     farthest point, bound orbits only
    period               T = 2π a^(3/2)      bound orbits only

The orbit is bound (E < 0), parabolic (E = 0) or unbound (E > 0). Quantities that do not exist
for an orbit that escapes, the apoapsis and the period, are infinite.

Like the rest of :mod:`bhlab.physics.newtonian`, this is Newton's theory and is not valid close
to a black hole.
"""

import math
from dataclasses import dataclass

from bhlab.physics.newtonian import State, make_state, specific_angular_momentum, specific_energy

CIRCULAR_ECCENTRICITY = 1e-10
"""Below this eccentricity the direction of periapsis is not defined: the orbit is a circle to
within rounding error, and the direction of the tiny eccentricity vector is noise."""


@dataclass(frozen=True)
class OrbitalElements:
    """Size, shape and orientation of a Newtonian orbit. Lengths in GM/c², times in GM/c³."""

    kind: str
    """"bound", "parabolic" or "unbound"."""
    energy: float
    """E = v²/2 − 1/r, in units of c²."""
    angular_momentum: float
    """L = x v_y − y vₓ, in units of GM/c. Positive for anticlockwise motion."""
    eccentricity: float
    """0 for a circle, between 0 and 1 for an ellipse, 1 for a parabola, above 1 for a hyperbola."""
    semi_major_axis: float
    """a = −1/(2E): positive when bound, negative when unbound, infinite for a parabola."""
    periapsis: float
    """Closest distance to the mass."""
    apoapsis: float
    """Farthest distance from the mass; infinite unless bound."""
    period: float
    """Time for one orbit; infinite unless bound."""
    periapsis_angle: float | None
    """Direction of periapsis, in radians anticlockwise from +x, in the range (−π, π].
    None for a circular orbit, which has no periapsis."""


def orbital_elements(state: State) -> OrbitalElements:
    """The orbit that passes through ``state`` = (x, y, vₓ, v_y)."""
    x, y, vx, vy = (float(component) for component in state)
    make_state(x, y, vx, vy)  # rejects r = 0 and non-finite components
    r = math.hypot(x, y)
    v_squared = vx * vx + vy * vy
    radial = x * vx + y * vy  # r·v
    energy = specific_energy(state)
    angular_momentum = specific_angular_momentum(state)

    # Adding 0.0 turns a negative zero (−0.0) into +0.0, so that atan2 gives +π and not −π
    # for an eccentricity vector along −x.
    ex = (v_squared - 1.0 / r) * x - radial * vx + 0.0
    ey = (v_squared - 1.0 / r) * y - radial * vy + 0.0
    eccentricity = math.hypot(ex, ey)
    periapsis = angular_momentum**2 / (1.0 + eccentricity)
    angle = math.atan2(ey, ex) if eccentricity >= CIRCULAR_ECCENTRICITY else None

    if energy < 0.0:
        kind = "bound"
        semi_major_axis = -1.0 / (2.0 * energy)
        apoapsis = semi_major_axis * (1.0 + eccentricity)
        period = 2.0 * math.pi * semi_major_axis**1.5
    else:
        kind = "parabolic" if energy == 0.0 else "unbound"
        semi_major_axis = math.inf if energy == 0.0 else -1.0 / (2.0 * energy)
        apoapsis = math.inf
        period = math.inf

    return OrbitalElements(
        kind=kind,
        energy=energy,
        angular_momentum=angular_momentum,
        eccentricity=eccentricity,
        semi_major_axis=semi_major_axis,
        periapsis=periapsis,
        apoapsis=apoapsis,
        period=period,
        periapsis_angle=angle,
    )
