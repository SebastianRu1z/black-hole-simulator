"""Compute a Newtonian orbit from the command line and list what happens along it.

    python -m bhlab.orbit                                  the a = 100, e = 0.5 ellipse, one orbit
    python -m bhlab.orbit --x 50 --vy 0.1732 --orbits 3 --mass 4.3e6
    python -m bhlab.orbit --x 10 --vy 0 --stop-radius 2    fall from rest at r = 10
    python -m bhlab.orbit --help

Positions are in GM/c² and velocities in units of c. The program prints the orbital elements
of the starting state, integrates the motion with DOP853, and lists every periapsis, apoapsis
and (optionally) the moment the particle falls inward through a chosen radius, with times and
lengths also in physical units for the chosen mass. Invalid input is reported, never adjusted.
"""

import argparse
import math
import sys
from collections.abc import Sequence

from bhlab.formatting import format_length_auto, format_number, format_time_convenient
from bhlab.physics.newtonian import acceleration, make_state, specific_energy
from bhlab.physics.orbital_elements import orbital_elements
from bhlab.solvers.adaptive import apoapsis, integrate_adaptive, periapsis, radius_reached
from bhlab.units import BlackHole

DEFAULT_VY = math.sqrt(0.03)
"""With x = 50 this starts the a = 100, e = 0.5 ellipse at periapsis.

From the vis-viva equation: v² = 2/r − 1/a = 2/50 − 1/100 = 0.03."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bhlab.orbit",
        description="Newtonian orbit of a test particle around a point mass (GM = 1 units).",
    )
    start = parser.add_argument_group("starting state (positions in GM/c², velocities in c)")
    start.add_argument("--x", type=float, default=50.0, help="default 50")
    start.add_argument("--y", type=float, default=0.0, help="default 0")
    start.add_argument("--vx", type=float, default=0.0, help="default 0")
    start.add_argument(
        "--vy", type=float, default=DEFAULT_VY, help="default √0.03 ≈ 0.1732 (the a = 100 ellipse)"
    )
    length = parser.add_mutually_exclusive_group()
    length.add_argument(
        "--orbits", type=float, help="how many orbital periods to follow (default 1; bound only)"
    )
    length.add_argument("--duration", type=float, help="how long to follow, in GM/c³")
    parser.add_argument(
        "--stop-radius", type=float, help="stop when the particle falls inward through this r"
    )
    parser.add_argument(
        "--mass", type=float, default=10.0, help="black hole mass in solar masses (default 10)"
    )
    parser.add_argument(
        "--rtol", type=float, default=1e-10, help="relative tolerance of DOP853 (default 1e-10)"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line. Returns 0 on success and 2 for invalid input."""
    args = build_parser().parse_args(argv)
    try:
        _run(args)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


def _run(args: argparse.Namespace) -> None:
    state = make_state(args.x, args.y, args.vx, args.vy)
    black_hole = BlackHole.from_solar_masses(args.mass)
    elements = orbital_elements(state)

    if args.duration is not None:
        duration = args.duration
        length_text = f"{format_number(duration)} GM/c³"
    else:
        orbits = 1.0 if args.orbits is None else args.orbits
        if not (math.isfinite(orbits) and orbits > 0.0):
            raise ValueError(f"--orbits must be a positive, finite number; got {orbits!r}")
        if elements.kind != "bound":
            raise ValueError(
                f"This orbit is {elements.kind} and has no period: give --duration in GM/c³."
            )
        duration = orbits * elements.period
        length_text = (
            f"{orbits:g} orbit{'s' if orbits != 1 else ''} = {format_number(duration)} GM/c³"
        )

    events = [periapsis(), apoapsis()]
    if args.stop_radius is not None:
        events.append(radius_reached(args.stop_radius, direction=-1, stop=True))
    run = integrate_adaptive(acceleration, state, duration, rtol=args.rtol, events=tuple(events))

    def length(value: float) -> str:
        if not math.isfinite(value):
            return "∞"
        return (
            f"{format_number(value)} GM/c²  = {format_length_auto(black_hole.length_to_si(value))}"
        )

    def time(value: float) -> str:
        if not math.isfinite(value):
            return "∞"
        seconds = black_hole.time_to_si(value)
        return f"{format_number(value)} GM/c³  = {format_time_convenient(seconds)}"

    angle = elements.periapsis_angle
    print(
        f"Newtonian orbit, black hole of {format_number(args.mass)} M☉ "
        f"(GM/c² = {format_length_auto(black_hole.length_unit)}, "
        f"GM/c³ = {format_time_convenient(black_hole.time_unit)})"
    )
    print()
    print(
        f"Start              x = {format_number(args.x)}, y = {format_number(args.y)}, "
        f"vx = {format_number(args.vx)}, vy = {format_number(args.vy)}"
    )
    print(
        f"Orbit              {elements.kind}, "
        f"eccentricity e = {format_number(elements.eccentricity)}"
    )
    print(f"  semi-major axis  {length(elements.semi_major_axis)}")
    print(f"  periapsis        {length(elements.periapsis)}")
    print(f"  apoapsis         {length(elements.apoapsis)}")
    print(f"  period           {time(elements.period)}")
    print(
        "  periapsis angle  "
        + ("undefined (circular orbit)" if angle is None else f"{math.degrees(angle):.2f}°")
    )
    print()
    print(
        f"Run                DOP853, rtol = {args.rtol:g}, {length_text}: "
        f"{run.n_steps} steps, {run.n_evaluations} evaluations"
    )
    print()
    print(f"  {'event':<12}{'time (GM/c³)':>14}  {'time':>12}{'r (GM/c²)':>14}")
    print(f"  {'start':<12}{'0':>14}  {'0':>12}{format_number(math.hypot(args.x, args.y)):>14}")
    for event in run.events:
        r = math.hypot(event.state[0], event.state[1])
        print(
            f"  {event.name:<12}{format_number(event.time):>14}  "
            f"{format_time_convenient(black_hole.time_to_si(event.time)):>12}{format_number(r):>14}"
        )
    print()
    drift = (
        abs(specific_energy(run.states[-1]) / elements.energy - 1.0) if elements.energy else None
    )
    end_text = (
        f"stopped at {run.stopped_by}" if run.stopped_by else "reached the end time"
    ) + f", t = {format_number(run.times[-1])} GM/c³"
    print(f"End                {end_text}")
    if drift is not None:
        print(f"Energy error       |ΔE/E| = {format_number(drift, sig=2)}")


if __name__ == "__main__":
    # The output contains symbols such as M☉, GM/c³ and µs. On Windows, output redirected to a
    # file or a pipe would otherwise use an old code page that cannot encode them, and fail.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
