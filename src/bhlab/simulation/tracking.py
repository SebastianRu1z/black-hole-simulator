"""Everything worth knowing about one particle right now: the numbers the tracker panel shows.

All quantities are Newtonian, in units of GM/c² (lengths), GM/c³ (times) and c (speeds), like the
rest of the simulation. The panel converts them to SI for the chosen mass.

Speeds at the particle's distance r
-----------------------------------
    circular speed   v_circ = √(1/r)     the speed of a circular orbit through that point
    escape speed     v_esc  = √(2/r)     the least speed that never comes back

E = v²/2 − 1/r < 0 exactly when v < v_esc, so v / v_esc < 1 means bound and ≥ 1 means escaping.

Time to the next periapsis (Kepler's equation)
----------------------------------------------
For a bound orbit (a > 0, 0 < e < 1) the eccentric anomaly E_a locates the particle on its ellipse:

    r = a (1 − e cos E_a)          r·v = e √a sin E_a          (GM = 1)

which give cos E_a and sin E_a directly from the state, so no equation has to be solved
iteratively. Kepler's equation then gives the time since periapsis,

    t_p = a^(3/2) (E_a − e sin E_a)        with E_a taken in [0, 2π),

and the next periapsis comes T − t_p later, T = 2π a^(3/2).

When is Newton good enough?
---------------------------
Relativity changes Newtonian results by relative amounts of order GM/(r c²) = 1/r and v²/c².
Below 1 % (r > 100 and v < 0.1 c) the Newtonian numbers are good; between 1 % and 10 %
approximate; above 10 % (r < 10 or v > 0.32 c) only a rough guide. These are orders of magnitude,
not error bars.
"""

import math
from dataclasses import dataclass
from typing import Literal

from bhlab.physics.newtonian import State
from bhlab.physics.orbital_elements import OrbitalElements, orbital_elements

Fate = Literal["bound", "escapes", "reaches stop radius", "stopped"]
Reliability = Literal["good", "approximate", "rough"]


def comes_down_to(state: State, elements: OrbitalElements, radius: float) -> bool:
    """Whether a particle with ``state`` will come down to ``radius`` (it starts outside it).

    A bound orbit passes its periapsis every lap; an unbound one at most once, and only if it is
    still on its way in (r·v < 0).
    """
    x, y, vx, vy = (float(value) for value in state)
    approaching = x * vx + y * vy < 0.0
    return (elements.kind == "bound" or approaching) and elements.periapsis <= radius


def time_to_next_periapsis(state: State, elements: OrbitalElements) -> float | None:
    """Time until the next periapsis of a bound, non-circular orbit, in GM/c³; otherwise None."""
    e, a = elements.eccentricity, elements.semi_major_axis
    if elements.kind != "bound" or elements.periapsis_angle is None or e >= 1.0:
        return None
    x, y, vx, vy = (float(value) for value in state)
    r = math.hypot(x, y)
    cos_anomaly = (1.0 - r / a) / e
    sin_anomaly = (x * vx + y * vy) / (e * math.sqrt(a))
    anomaly = math.atan2(sin_anomaly, cos_anomaly) % (2.0 * math.pi)
    since = a**1.5 * (anomaly - e * math.sin(anomaly))
    return (elements.period - since) % elements.period


def reliability(r: float, speed: float) -> Reliability:
    """How far Newton's theory can be trusted at distance ``r`` and ``speed`` (see module notes)."""
    correction = max(1.0 / r, speed * speed)
    if correction < 0.01:
        return "good"
    return "approximate" if correction < 0.1 else "rough"


@dataclass(frozen=True)
class Tracking:
    """The state of one particle and what follows from it."""

    x: float
    y: float
    vx: float
    vy: float
    r: float
    angle: float
    """φ in degrees, anticlockwise from +x, in [0, 360)."""
    speed: float
    radial_speed: float
    """dr/dt: positive moving outward, negative moving inward."""
    circular_speed: float
    escape_speed: float
    elements: OrbitalElements
    fate: Fate
    time_to_periapsis: float | None
    reliability: Reliability

    @property
    def speed_over_escape(self) -> float:
        return self.speed / self.escape_speed


def track(state: State, stop_radius: float, *, stopped: bool = False) -> Tracking:
    """The tracker's numbers for ``state``. ``stopped``: it has reached the stop radius."""
    x, y, vx, vy = (float(value) for value in state)
    r = math.hypot(x, y)
    speed = math.hypot(vx, vy)
    elements = orbital_elements(state)
    fate: Fate
    if stopped:
        fate = "stopped"
    elif comes_down_to(state, elements, stop_radius):
        fate = "reaches stop radius"
    elif elements.kind == "bound":
        fate = "bound"
    else:
        fate = "escapes"
    return Tracking(
        x=x,
        y=y,
        vx=vx,
        vy=vy,
        r=r,
        angle=math.degrees(math.atan2(y, x)) % 360.0,
        speed=speed,
        radial_speed=(x * vx + y * vy) / r,
        circular_speed=math.sqrt(1.0 / r),
        escape_speed=math.sqrt(2.0 / r),
        elements=elements,
        fate=fate,
        time_to_periapsis=None
        if fate in ("stopped", "reaches stop radius")
        else time_to_next_periapsis(state, elements),
        reliability=reliability(r, speed),
    )
