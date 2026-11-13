"""Adaptive integration with SciPy's DOP853, and detection of events along the way.

Choosing the step automatically
-------------------------------
A fixed step has to be small enough for the hardest part of an orbit, which wastes work
everywhere else: on an eccentric ellipse the particle races through periapsis and crawls
around apoapsis. DOP853 (Dormand and Prince, order 8) adapts the step as it goes. Each step is
computed with an eighth-order formula and with lower-order formulas that reuse the same slope
evaluations. Their difference estimates the error of the step. A step whose error exceeds

    atol + rtol·|y|           (for each component of the state)

is rejected and retried with a smaller h; when the error is well below it, the next step grows.
``rtol`` is a relative tolerance and ``atol`` an absolute one. Circuit simulators such as SPICE
control their time step in the same way, with options called RELTOL and ABSTOL.

The tolerances bound the error made in each step, not the error at the end of a long run, which
can be larger. The tests measure the end error directly.

Events
------
An event is a moment at which a function g(t, y) of the motion crosses zero, for example the
radial velocity r·v at periapsis. SciPy watches the sign of g after every step and, when it
changes, finds the crossing time to full precision. An event can be restricted to one direction
of crossing, and a terminal event stops the run.

Two choices of this module go beyond SciPy:
- Events exactly at the starting time are not reported. SciPy would report a periapsis at t = 0
  for an orbit that starts at periapsis.
- A terminal event whose function is already zero at the start is refused, because the run would
  stop before it began. A tolerance below 1e-13 is refused too: SciPy would quietly raise it to
  about 2.2e-14, and this project never changes an input silently.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from bhlab.solvers.fixed_step import Acceleration, Array, first_order_system, validated_state

MIN_RTOL = 1e-13
"""The smallest relative tolerance accepted (double precision cannot do much better)."""

EventFunction = Callable[[float, Array], float]


@dataclass(frozen=True)
class EventSpec:
    """Something to watch for during a run: the moments when ``function`` crosses zero."""

    name: str
    function: EventFunction
    direction: int = 0
    """+1: only crossings from negative to positive; −1: only the reverse; 0: both."""
    terminal: bool = False
    """Stop the run at the first crossing."""


@dataclass(frozen=True)
class Event:
    """An event that happened: its name, the time, and the state at that time."""

    name: str
    time: float
    state: Array


@dataclass(frozen=True)
class AdaptiveTrajectory:
    """An adaptive run. The time steps are not equal; the arrays are read-only."""

    times: Array
    """The times at the end of each accepted step, shape (n + 1,)."""
    states: Array
    """The state at those times, shape (n + 1, 2d)."""
    events: tuple[Event, ...]
    """Every event found, in order of time."""
    stopped_by: str | None
    """The name of the terminal event that ended the run, or None if it reached its end time."""
    n_evaluations: int
    """How often the right-hand side f(t, y) was evaluated: the cost of the run."""
    rtol: float
    atol: float

    @property
    def n_steps(self) -> int:
        """The number of accepted steps."""
        return len(self.times) - 1

    def events_named(self, name: str) -> tuple[Event, ...]:
        """The events called ``name``, in order of time."""
        return tuple(event for event in self.events if event.name == name)


# --- events of planar motion, for states (x, y, vₓ, v_y) -------------------------------------


def _radial_velocity_times_r(_t: float, y: Array) -> float:
    return float(y[0] * y[2] + y[1] * y[3])  # r·v = r · dr/dt


def periapsis() -> EventSpec:
    """Closest approach: r·v changes from negative (approaching) to positive (receding)."""
    return EventSpec("periapsis", _radial_velocity_times_r, direction=+1)


def apoapsis() -> EventSpec:
    """Farthest point: r·v changes from positive to negative."""
    return EventSpec("apoapsis", _radial_velocity_times_r, direction=-1)


def radius_reached(radius: float, *, direction: int = 0, stop: bool = False) -> EventSpec:
    """The particle crosses the circle r = ``radius``: inward (−1), outward (+1) or either (0)."""
    if not (math.isfinite(radius) and radius > 0.0):
        raise ValueError(f"The radius must be a positive, finite number; got {radius!r}")
    if direction not in (-1, 0, 1):
        raise ValueError(f"The direction must be −1, 0 or +1; got {direction!r}")

    def crossing(_t: float, y: Array) -> float:
        return float(math.hypot(y[0], y[1]) - radius)

    return EventSpec(f"r = {radius:g}", crossing, direction=direction, terminal=stop)


# --- the integrator --------------------------------------------------------------------------


def integrate_adaptive(
    acceleration: Acceleration,
    initial_state: Array,
    duration: float,
    *,
    rtol: float = 1e-10,
    atol: float = 1e-12,
    events: tuple[EventSpec, ...] = (),
) -> AdaptiveTrajectory:
    """Follow d²x/dt² = a(x) from t = 0 to ``duration`` with DOP853, watching for ``events``.

    The run ends early if a terminal event happens. Invalid arguments raise ValueError.
    """
    if not (math.isfinite(duration) and duration > 0.0):
        raise ValueError(f"The duration must be a positive, finite number; got {duration!r}")
    if not (MIN_RTOL <= rtol < 1.0):
        raise ValueError(f"rtol must be at least {MIN_RTOL:g} and less than 1; got {rtol!r}")
    if not (math.isfinite(atol) and atol > 0.0):
        raise ValueError(f"atol must be a positive, finite number; got {atol!r}")
    y0 = validated_state(initial_state)
    names = [spec.name for spec in events]
    if len(set(names)) != len(names):
        raise ValueError(f"Every event needs its own name; got {names}")
    for spec in events:
        if spec.terminal and spec.function(0.0, y0) == 0.0:
            raise ValueError(f"The run would stop at once: the event {spec.name!r} holds at t = 0")

    solution = solve_ivp(
        first_order_system(acceleration),
        (0.0, duration),
        y0,
        method="DOP853",
        rtol=rtol,
        atol=atol,
        events=[_for_scipy(spec) for spec in events] or None,
    )
    if solution.status == -1:
        raise RuntimeError(f"The integration failed: {solution.message}")

    found = []
    if events:
        for spec, times, states in zip(events, solution.t_events, solution.y_events, strict=True):
            found += [
                Event(spec.name, float(t), _read_only(np.array(s)))
                for t, s in zip(times, states, strict=True)
                if t > 0.0
            ]
    found.sort(key=lambda event: event.time)

    stopped_by = None
    if solution.status == 1:  # a terminal event ended the run
        final_time = solution.t[-1]
        stopped_by = next(
            event.name
            for event in found
            if event.time == final_time and next(s for s in events if s.name == event.name).terminal
        )

    return AdaptiveTrajectory(
        times=_read_only(solution.t),
        states=_read_only(solution.y.T.copy()),
        events=tuple(found),
        stopped_by=stopped_by,
        n_evaluations=int(solution.nfev),
        rtol=rtol,
        atol=atol,
    )


def _for_scipy(spec: EventSpec) -> EventFunction:
    """SciPy reads ``terminal`` and ``direction`` as attributes of the event function itself."""

    def event(t: float, y: Array) -> float:
        return spec.function(t, y)

    event.terminal = spec.terminal
    event.direction = spec.direction
    return event


def _read_only(array: Array) -> Array:
    array.flags.writeable = False
    return array
