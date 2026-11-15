"""The simulation the window shows: test particles moving around the black hole as time passes.

What is modelled
----------------
Each particle is a test particle in Newtonian gravity (:mod:`bhlab.physics.newtonian`). Test
particles do not attract each other, so each follows its own orbit, computed by its own solver
(:class:`bhlab.solvers.adaptive.AdaptiveStepper`).

Two rules come from the map and not from Newton's theory, which has neither a horizon nor a
speed limit:

- A particle has to start outside the stop radius, r = 2 GM/c² (the event horizon drawn on the
  map), and slower than light.
- A particle that reaches the stop radius is stopped there and stays there. This is a geometric
  stop that marks where the model ends. It is not the physics of a horizon.

Simulated time and whoever advances it
--------------------------------------
The simulation has one clock, ``time``, in units of GM/c³, and :meth:`Simulation.advance` moves
it forward. How far and how often is up to the caller: the window advances it a little on every
frame, a test may advance it in one jump. The states at a given simulated time are the same
either way, because every solver chooses its steps from the motion alone and the state between
two steps comes from interpolation.

A solver is usually ahead of the clock by part of a step, and the state of a particle can be
read only inside its solver's latest step. The simulation therefore always steps the particle
whose solution is least advanced. Every particle's latest step then contains the clock time.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

from bhlab.physics.newtonian import State, acceleration, make_state
from bhlab.solvers.adaptive import AdaptiveStepper, check_tolerances
from bhlab.units import HORIZON_RADIUS_RG


@dataclass(frozen=True)
class Particle:
    """One particle as it is at the simulation's current time. Lengths in GM/c², speeds in c."""

    id: int
    """Its number: 0 for the first particle added, then 1, 2, … A removed particle's number is
    never given to another one."""
    state: State
    """(x, y, vₓ, v_y) now. For a stopped particle: the state in which it arrived."""
    initial_state: State
    """The state it was added with, and returns to on a reset."""
    added_at: float
    """The simulated time at which it started moving (0 after a reset)."""
    stopped_at: float | None
    """The simulated time at which it reached the stop radius, or None while it is moving."""

    @property
    def is_stopped(self) -> bool:
        """Whether it has reached the stop radius."""
        return self.stopped_at is not None


@dataclass
class _Body:
    """The simulation's own record of a particle: its solver, and where it stopped if it did."""

    id: int
    initial_state: State
    added_at: float
    stepper: AdaptiveStepper
    stopped_at: float | None = None
    stopped_state: State | None = None


def _radius(state: State) -> float:
    return math.hypot(state[0], state[1])


def _radial_velocity_times_r(state: State) -> float:
    return float(state[0] * state[2] + state[1] * state[3])  # r·v: negative while approaching


class Simulation:
    """Particles around the black hole, and the simulated time, in units of GM/c² and GM/c³."""

    def __init__(
        self,
        *,
        stop_radius: float = HORIZON_RADIUS_RG,
        rtol: float = 1e-10,
        atol: float = 1e-12,
    ) -> None:
        if not (math.isfinite(stop_radius) and stop_radius > 0.0):
            raise ValueError(
                f"The stop radius must be a positive, finite number; got {stop_radius!r}"
            )
        check_tolerances(rtol, atol)
        self._stop_radius = float(stop_radius)
        self._rtol = rtol
        self._atol = atol
        self._time = 0.0
        self._bodies: list[_Body] = []
        self._next_id = 0

    # --- what the simulation holds ------------------------------------------------------

    @property
    def time(self) -> float:
        """The simulated time, in GM/c³."""
        return self._time

    @property
    def stop_radius(self) -> float:
        """Particles that reach this radius are stopped, in GM/c²."""
        return self._stop_radius

    def __len__(self) -> int:
        return len(self._bodies)

    @property
    def particles(self) -> tuple[Particle, ...]:
        """Every particle as it is now, in the order in which they were added."""
        return tuple(self._snapshot(body) for body in self._bodies)

    # --- changing it --------------------------------------------------------------------

    def check_start(self, x: float, y: float, vx: float, vy: float) -> State:
        """The state (x, y, vₓ, v_y) if a particle may start with it; otherwise ValueError.

        A value must be finite, the particle must start outside the stop radius and slower than
        light. :meth:`add_particle` applies exactly this check, so a preview that calls it agrees
        with what adding will do.
        """
        state = make_state(x, y, vx, vy)
        radius, speed = _radius(state), math.hypot(vx, vy)
        if radius <= self._stop_radius:
            raise ValueError(
                f"A particle has to start outside r = {self._stop_radius:g} GM/c², the horizon "
                f"radius drawn on the map. This one would start at r = {radius:.4g}."
            )
        if speed >= 1.0:
            raise ValueError(
                "A particle has to start slower than light, which is speed 1 in these units. "
                f"This one would start at speed {speed:.4g}."
            )
        return state

    def add_particle(self, x: float, y: float, vx: float, vy: float) -> Particle:
        """Add a particle that starts now at (x, y) with velocity (vₓ, v_y).

        Raises ValueError, and adds nothing, if :meth:`check_start` refuses the values.
        """
        state = self.check_start(x, y, vx, vy)
        state.flags.writeable = False
        body = _Body(self._next_id, state, self._time, self._new_stepper(state))
        self._next_id += 1
        self._bodies.append(body)
        return self._snapshot(body)

    def remove_particle(self, particle_id: int) -> None:
        """Remove the particle numbered ``particle_id``. Raises KeyError if there is none."""
        for index, body in enumerate(self._bodies):
            if body.id == particle_id:
                del self._bodies[index]
                return
        raise KeyError(f"There is no particle number {particle_id}")

    def advance(self, duration: float, keep_going: Callable[[], bool] | None = None) -> bool:
        """Move the clock forward by ``duration``, and every particle with it.

        ``keep_going`` is asked after every solver step. When it answers False the call ends
        early, with the clock as far forward as every particle has been computed; the window
        uses this to stay responsive when there is more to compute than a frame allows.
        Returns True if the clock covered the whole ``duration``.
        """
        if not (math.isfinite(duration) and duration >= 0.0):
            raise ValueError(
                f"Time only runs forward: the duration must be finite and not negative; "
                f"got {duration!r}"
            )
        target = self._time + duration
        moving = [body for body in self._bodies if body.stopped_at is None]
        while True:
            behind = [body for body in moving if body.stepper.time < target]
            if not behind:
                break
            # Least advanced first: see the module docstring.
            body = min(behind, key=lambda candidate: candidate.stepper.time)
            self._step(body)
            if body.stopped_at is not None:
                moving.remove(body)
            if keep_going is not None and not keep_going():
                break
        computed = min((body.stepper.time for body in moving), default=math.inf)
        self._time = min(target, computed)
        return self._time == target

    def reset(self) -> None:
        """Back to time zero: every particle returns to its starting state and moves again."""
        self._time = 0.0
        for body in self._bodies:
            body.added_at = 0.0
            body.stepper = self._new_stepper(body.initial_state)
            body.stopped_at = None
            body.stopped_state = None

    # --- internals ----------------------------------------------------------------------

    def _new_stepper(self, state: State) -> AdaptiveStepper:
        return AdaptiveStepper(acceleration, state, self._time, rtol=self._rtol, atol=self._atol)

    def _step(self, body: _Body) -> None:
        """One solver step for ``body``, then see whether it reached the stop radius in it."""
        stepper = body.stepper
        before = stepper.state
        stepper.step()
        start, end, after = stepper.step_start, stepper.time, stepper.state

        inside_at = None  # a time in this step at which it is on or inside the stop radius
        if _radius(after) <= self._stop_radius:
            inside_at = end
        elif _radial_velocity_times_r(before) < 0.0 <= _radial_velocity_times_r(
            after
        ) and self._could_have_dipped_inside(before, after, end - start):
            # It passed its closest approach inside this step, near the stop radius. A dip
            # between two points that are both outside would otherwise go unnoticed.
            closest = stepper.find_crossing(_radial_velocity_times_r, start, end)
            if _radius(stepper.state_at(closest)) <= self._stop_radius:
                inside_at = closest

        if inside_at is not None:
            body.stopped_at = stepper.find_crossing(
                lambda state: _radius(state) - self._stop_radius, start, inside_at
            )
            body.stopped_state = stepper.state_at(body.stopped_at)

    def _could_have_dipped_inside(self, before: State, after: State, duration: float) -> bool:
        """Whether a step that starts and ends outside the stop radius R could have gone inside.

        While the particle is outside R, conservation of energy limits its speed:
        v² = 2E + 2/r ≤ 2E + 2/R. To go inside and come back out it would have to cover the
        distance from one end of the step to R in at most half of the step's duration. If even
        the fastest allowed speed cannot do that, the search for a dip is skipped.
        """
        x, y, vx, vy = before
        radius_before = math.hypot(x, y)
        fastest = math.sqrt(vx * vx + vy * vy + 2.0 / self._stop_radius - 2.0 / radius_before)
        nearer_end = min(radius_before, _radius(after))
        return nearer_end - 0.5 * fastest * duration <= self._stop_radius

    def _snapshot(self, body: _Body) -> Particle:
        # A solver may already have found a stop that the clock has not reached yet.
        stopped = body.stopped_at is not None and body.stopped_at <= self._time
        state = body.stopped_state if stopped else body.stepper.state_at(self._time)
        return Particle(
            id=body.id,
            state=state,
            initial_state=body.initial_state,
            added_at=body.added_at,
            stopped_at=body.stopped_at if stopped else None,
        )
