"""Two fixed-step integrators for d²x/dt² = a(x): fourth-order Runge–Kutta and velocity Verlet.

Both advance the motion in steps of a fixed length h. They differ in how they spend the work.

Runge–Kutta (RK4)
-----------------
RK4 solves any first-order system dy/dt = f(t, y). It samples the slope four times per step and
combines the samples with weights 1, 2, 2, 1:

    k₁ = f(t, y)
    k₂ = f(t + h/2, y + h k₁/2)
    k₃ = f(t + h/2, y + h k₂/2)
    k₄ = f(t + h,   y + h k₃)
    y(t + h) ≈ y + h (k₁ + 2k₂ + 2k₃ + k₄) / 6

The error after a fixed time falls as h⁴: halving h makes it 16 times smaller. RK4 does not
respect the structure of a mechanical system, though, so the energy of an orbit drifts steadily
and the error keeps growing over many orbits.

A second-order equation is first written as a first-order system. With the state y = (x, v),
d²x/dt² = a(x) becomes dx/dt = v and dv/dt = a(x) (see :func:`first_order_system`).

Velocity Verlet
---------------
Verlet works on position and velocity directly:

    v_half = v + (h/2) a(x)
    x_new  = x + h v_half
    v_new  = v_half + (h/2) a(x_new)

It is only second order (halving h makes the error 4 times smaller) and needs one new force
evaluation per step against four for RK4. Its strength is that it is *symplectic*: it preserves
the geometric structure of Hamiltonian mechanics. In practice the energy error oscillates within
a bound instead of drifting, and for a central force the angular momentum is conserved exactly,
up to rounding.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]
Acceleration = Callable[[Array], Array]
"""A force law: the acceleration (as an array) at a position (as an array)."""
RightHandSide = Callable[[float, Array], Array]
"""The right-hand side f(t, y) of a first-order system dy/dt = f(t, y)."""

METHODS: tuple[str, ...] = ("rk4", "verlet")


@dataclass(frozen=True)
class Trajectory:
    """A computed motion: the state at each step. The arrays are read-only."""

    times: Array
    """Times t₀, t₀ + h, t₀ + 2h, …, shape (n + 1,)."""
    states: Array
    """States (position, velocity) at those times, one row per time, shape (n + 1, 2d)."""
    method: str
    step: float


def rk4_step(f: RightHandSide, t: float, y: Array, h: float) -> Array:
    """One Runge–Kutta step of length ``h`` for dy/dt = f(t, y); returns y(t + h)."""
    k1 = f(t, y)
    k2 = f(t + h / 2, y + (h / 2) * k1)
    k3 = f(t + h / 2, y + (h / 2) * k2)
    k4 = f(t + h, y + h * k3)
    return y + (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)


def velocity_verlet_step(
    acceleration: Acceleration, x: Array, v: Array, a: Array, h: float
) -> tuple[Array, Array, Array]:
    """One velocity Verlet step of length ``h``.

    ``a`` is the acceleration at ``x``, carried over from the previous step so that each step
    evaluates the force only once. Returns the new position, velocity and acceleration.
    """
    v_half = v + (h / 2) * a
    x_new = x + h * v_half
    a_new = acceleration(x_new)
    v_new = v_half + (h / 2) * a_new
    return x_new, v_new, a_new


def first_order_system(acceleration: Acceleration) -> RightHandSide:
    """Turn d²x/dt² = a(x) into dy/dt = f(t, y) with y = (x, v), for :func:`rk4_step`."""

    def f(_t: float, y: Array) -> Array:
        half = len(y) // 2
        return np.concatenate((y[half:], acceleration(y[:half])))

    return f


def integrate(
    acceleration: Acceleration,
    initial_state: Array,
    step: float,
    n_steps: int,
    method: str = "rk4",
) -> Trajectory:
    """Follow d²x/dt² = a(x) for ``n_steps`` steps of length ``step``, starting at t = 0.

    ``initial_state`` holds the positions followed by the velocities, for example
    (x, y, vₓ, v_y). ``method`` is ``"rk4"`` or ``"verlet"``. Invalid arguments are rejected
    with a ValueError; nothing is adjusted silently.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}; choose one of {', '.join(METHODS)}")
    if not (math.isfinite(step) and step > 0.0):
        raise ValueError(f"The step must be a positive, finite number; got {step!r}")
    if isinstance(n_steps, bool) or not isinstance(n_steps, int) or n_steps < 1:
        raise ValueError(
            f"The number of steps must be a whole number of at least 1; got {n_steps!r}"
        )
    y0 = np.asarray(initial_state, dtype=float)
    if y0.ndim != 1 or len(y0) == 0 or len(y0) % 2 != 0:
        raise ValueError(
            "The initial state must be a flat list of positions followed by as many velocities; "
            f"got shape {y0.shape}"
        )
    if not np.all(np.isfinite(y0)):
        raise ValueError(f"The initial state must be finite; got {y0}")

    states = np.empty((n_steps + 1, len(y0)))
    states[0] = y0
    if method == "rk4":
        f = first_order_system(acceleration)
        for i in range(n_steps):
            states[i + 1] = rk4_step(f, i * step, states[i], step)
    else:
        half = len(y0) // 2
        x, v = y0[:half], y0[half:]
        a = acceleration(x)
        for i in range(n_steps):
            x, v, a = velocity_verlet_step(acceleration, x, v, a, step)
            states[i + 1, :half] = x
            states[i + 1, half:] = v

    times = np.arange(n_steps + 1) * step
    times.flags.writeable = False
    states.flags.writeable = False
    return Trajectory(times=times, states=states, method=method, step=step)
