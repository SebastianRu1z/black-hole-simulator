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

One step at a time
------------------
:func:`integrate_adaptive` computes a whole run and returns it. A simulation that is shown while
it runs needs the opposite: compute a little further whenever the display asks.
:class:`AdaptiveStepper` drives the same DOP853 method one step at a time. Each step is as long
as the solver chooses from the motion alone, and the state at any time inside the latest step
comes from the method's own interpolating polynomial (its "dense output"), which is about as
accurate as the steps themselves. Nothing about when or how often the state is asked for can
change the steps, so a display may sample the motion at any rate without affecting it.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import DOP853, solve_ivp
from scipy.optimize import brentq

from bhlab.solvers.fixed_step import Acceleration, Array, first_order_system, validated_state

MIN_RTOL = 1e-13
"""The smallest relative tolerance accepted (double precision cannot do much better)."""

EventFunction = Callable[[float, Array], float]


def check_tolerances(rtol: float, atol: float) -> None:
    """Raise ValueError unless ``rtol`` and ``atol`` are tolerances DOP853 can honour."""
    if not (MIN_RTOL <= rtol < 1.0):
        raise ValueError(f"rtol must be at least {MIN_RTOL:g} and less than 1; got {rtol!r}")
    if not (math.isfinite(atol) and atol > 0.0):
        raise ValueError(f"atol must be a positive, finite number; got {atol!r}")


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
    check_tolerances(rtol, atol)
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


# --- one step at a time ----------------------------------------------------------------------


class AdaptiveStepper:
    """DOP853 driven one step at a time, with interpolation inside the latest step.

    ``time`` is how far the solution has been computed. :meth:`step` moves it forward by one
    step, whose length the solver chooses. :meth:`state_at` gives the state at any time from
    ``step_start`` to ``time``. The steps depend only on the motion and the tolerances, never
    on when or how often the state is read.
    """

    def __init__(
        self,
        acceleration: Acceleration,
        initial_state: Array,
        start_time: float = 0.0,
        *,
        rtol: float = 1e-10,
        atol: float = 1e-12,
    ) -> None:
        if not math.isfinite(start_time):
            raise ValueError(f"The start time must be finite; got {start_time!r}")
        check_tolerances(rtol, atol)
        y0 = validated_state(initial_state)
        self._start_time = float(start_time)
        # No end time is given: the solver is never made to shorten a step to stop somewhere.
        self._solver = DOP853(
            first_order_system(acceleration), self._start_time, y0, math.inf, rtol=rtol, atol=atol
        )
        self._interpolant: Callable[[float], Array] | None = None
        self._n_steps = 0

    @property
    def time(self) -> float:
        """The time up to which the solution has been computed."""
        return float(self._solver.t)

    @property
    def step_start(self) -> float:
        """The time at which the latest step began (the start time, before any step)."""
        previous = self._solver.t_old
        return self._start_time if previous is None else float(previous)

    @property
    def state(self) -> Array:
        """The state at ``time``."""
        return _read_only(self._solver.y.copy())

    @property
    def n_steps(self) -> int:
        """The number of steps taken so far."""
        return self._n_steps

    @property
    def n_evaluations(self) -> int:
        """How often the right-hand side has been evaluated so far."""
        return int(self._solver.nfev)

    def step(self) -> None:
        """Advance by one step of the solver's own choosing."""
        message = self._solver.step()
        if self._solver.status == "failed":
            raise RuntimeError(f"The integration failed at t = {self.time:g}: {message}")
        self._interpolant = None
        self._n_steps += 1

    def state_at(self, time: float) -> Array:
        """The state at ``time``, which must lie inside the latest step."""
        if not (self.step_start <= time <= self.time):
            raise ValueError(
                f"The state is known only inside the latest step, from t = {self.step_start!r} "
                f"to t = {self.time!r}; asked for t = {time!r}"
            )
        if time == self.time:
            return self.state
        if self._interpolant is None:
            # Computed only when a state inside the step is wanted: it costs three more
            # evaluations of the right-hand side.
            self._interpolant = self._solver.dense_output()
        return _read_only(self._interpolant(time))

    def find_crossing(
        self, function: Callable[[Array], float], earliest: float, latest: float
    ) -> float:
        """The time between ``earliest`` and ``latest`` at which ``function(state)`` is zero.

        Both times must lie inside the latest step, and the function must have opposite signs,
        or be zero, at the two of them. The time is found by Brent's method to the precision
        of a float.
        """
        precision = 4.0 * np.finfo(float).eps
        return float(
            brentq(
                lambda time: function(self.state_at(time)),
                earliest,
                latest,
                xtol=precision,
                rtol=precision,
            )
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
