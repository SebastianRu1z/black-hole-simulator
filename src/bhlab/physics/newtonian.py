"""Newtonian gravity of a point mass: a test particle moving in the orbital plane.

Equation of motion
------------------
A test particle at position r feels the acceleration

    d²r/dt² = −GM r / |r|³

It points at the mass, and its size falls off as 1/|r|². In geometrized units lengths are
measured in GM/c² and times in GM/c³, which makes GM = 1:

    d²r/dt² = −r / |r|³

The motion stays in the plane that contains the starting position and velocity, so two
coordinates (x, y) are enough. A state is the array (x, y, vₓ, v_y).

Conserved quantities
--------------------
Gravity of a fixed point mass conserves, per unit mass of the particle,

    energy             E = v²/2 − 1/r
    angular momentum   L = x v_y − y vₓ

A numerical solution conserves them only approximately. How far they drift measures the
numerical error, which is how the tests judge the integrators in :mod:`bhlab.solvers`.

Limits of the model
-------------------
This is Newton's theory. Close to a black hole it is wrong: it has no horizon, no photon sphere
and no innermost stable circular orbit, and it gets orbital speeds and periods wrong by an
amount that grows towards the black hole. A circular orbit at r has speed √(1/r), so at
r = 100 the particle already moves at 0.1 c. General relativity replaces this model in Stage 2.
"""

import math

import numpy as np
from numpy.typing import NDArray

State = NDArray[np.float64]
"""(x, y, vₓ, v_y): position in units of GM/c², velocity as a fraction of c."""

Vector = NDArray[np.float64]
"""A position or an acceleration in the orbital plane, (x, y)."""


def _require_positive_finite(value: float, what: str) -> None:
    if not (math.isfinite(value) and value > 0.0):
        raise ValueError(f"{what} must be a positive, finite number; got {value!r}")


def _radius(x: float, y: float) -> float:
    """Distance from the mass. Rejects the singular point r = 0 and non-finite positions."""
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"The position must be finite; got ({x!r}, {y!r})")
    r = math.hypot(x, y)
    if r == 0.0:
        raise ValueError("The acceleration is infinite at r = 0, the position of the mass.")
    return r


def make_state(x: float, y: float, vx: float, vy: float) -> State:
    """A state array (x, y, vₓ, v_y). Every component must be finite and the position not r = 0."""
    _radius(x, y)
    if not (math.isfinite(vx) and math.isfinite(vy)):
        raise ValueError(f"The velocity must be finite; got ({vx!r}, {vy!r})")
    return np.array([x, y, vx, vy], dtype=float)


def acceleration(position: Vector) -> Vector:
    """The acceleration −r/|r|³ at ``position`` = (x, y), in units of c⁴/(GM)."""
    x, y = float(position[0]), float(position[1])
    r = _radius(x, y)
    factor = -1.0 / r**3
    return np.array([factor * x, factor * y])


def specific_energy(state: State) -> float:
    """Energy per unit mass, E = v²/2 − 1/r, in units of c². Negative for a bound orbit."""
    x, y, vx, vy = (float(component) for component in state)
    return 0.5 * (vx * vx + vy * vy) - 1.0 / _radius(x, y)


def specific_angular_momentum(state: State) -> float:
    """Angular momentum per unit mass, L = x v_y − y vₓ, in units of GM/c.

    Positive for anticlockwise motion.
    """
    x, y, vx, vy = (float(component) for component in state)
    return x * vy - y * vx


def circular_velocity(x: float, y: float) -> tuple[float, float]:
    """The velocity (vₓ, v_y) of the anticlockwise circular orbit through the point (x, y).

    Gravity supplies the centripetal acceleration: v²/r = 1/r², so v = √(1/r). The velocity is
    perpendicular to the position, a quarter turn anticlockwise from it.
    """
    r = _radius(x, y)
    speed = math.sqrt(1.0 / r)
    # Adding 0.0 turns a negative zero (−0.0, as for a point on the +x axis) into +0.0.
    return -speed * (y / r) + 0.0, speed * (x / r) + 0.0


def circular_orbit(radius: float) -> State:
    """The state that starts an anticlockwise circular orbit of ``radius`` on the +x axis."""
    _require_positive_finite(radius, "The orbital radius")
    return make_state(radius, 0.0, *circular_velocity(radius, 0.0))


def kepler_period(semi_major_axis: float) -> float:
    """Period of a bound orbit, T = 2π a^(3/2), in units of GM/c³.

    This is Kepler's third law, T² = 4π² a³ / GM, with GM = 1.
    """
    _require_positive_finite(semi_major_axis, "The semi-major axis")
    return 2.0 * math.pi * semi_major_axis**1.5
