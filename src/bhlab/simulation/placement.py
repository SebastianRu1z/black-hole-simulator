"""Placing a particle by dragging an arrow on the map, and what that particle will do.

From an arrow to a velocity
---------------------------
The user presses at the starting point (x, y) and drags an arrow d = (dₓ, d_y), both in units of
GM/c². The velocity is

    v = d / r^(3/2)          r = √(x² + y²)

Two properties make this rule convenient:

- r^(3/2) is the time a circular orbit at r needs to turn through one radian, T/(2π). The tip of
  the arrow is where the particle would be after that time if it moved in a straight line.
- The circular speed is √(1/r), and r · r^(−3/2) = √(1/r). So an arrow as long as the distance to
  the black hole, drawn at right angles to the line towards it, gives exactly a circular orbit;
  half as long gives half the circular speed, and √2 times as long the escape speed √(2/r).

The arrow therefore stays a comfortable size at every distance, since one zooms out to place a
particle far away.

What the particle will do
-------------------------
:func:`preview` works out the orbit from the starting state before the particle is added, with
the same check the simulation applies when adding it (:meth:`Simulation.check_start`).
"""

import math
from dataclasses import dataclass

from bhlab.physics.orbital_elements import OrbitalElements, orbital_elements
from bhlab.simulation.model import Simulation
from bhlab.simulation.tracking import comes_down_to


def drag_velocity(x: float, y: float, dx: float, dy: float) -> tuple[float, float]:
    """The velocity (vₓ, v_y) given by an arrow (dₓ, d_y) dragged from the point (x, y)."""
    r = math.hypot(x, y)
    if not (math.isfinite(r) and r > 0.0):
        raise ValueError(f"The starting point must be finite and not at r = 0; got ({x!r}, {y!r})")
    if not (math.isfinite(dx) and math.isfinite(dy)):
        raise ValueError(f"The arrow must be finite; got ({dx!r}, {dy!r})")
    scale = r**-1.5
    return dx * scale, dy * scale


@dataclass(frozen=True)
class Preview:
    """What adding a particle with a given starting state would do."""

    x: float
    y: float
    vx: float
    vy: float
    error: str | None
    """Why the particle cannot be added, or None if it can."""
    elements: OrbitalElements | None
    """Its orbit, if it can be added."""
    reaches_stop_radius: bool
    """Whether it will come down to the stop radius and be stopped there."""

    @property
    def is_valid(self) -> bool:
        return self.error is None

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    @property
    def speed_over_circular(self) -> float:
        """The speed as a multiple of the circular speed √(1/r) at the starting point."""
        return self.speed / math.sqrt(1.0 / math.hypot(self.x, self.y))


def preview(simulation: Simulation, x: float, y: float, vx: float, vy: float) -> Preview:
    """What adding (x, y, vₓ, v_y) to ``simulation`` would do, without adding it."""
    try:
        state = simulation.check_start(x, y, vx, vy)
    except ValueError as error:
        return Preview(x, y, vx, vy, str(error), None, False)
    elements = orbital_elements(state)
    reaches = comes_down_to(state, elements, simulation.stop_radius)
    return Preview(x, y, vx, vy, None, elements, reaches)
