"""Compare RK4 and velocity Verlet on one Kepler ellipse, at several step sizes.

Run from the project folder:

    .venv\\Scripts\\python.exe examples\\integrator_comparison.py

The orbit has semi-major axis a = 100 GM/c² and eccentricity e = 0.5, so it swings between
r = 50 and r = 150 and should close after T = 2π a^(3/2) ≈ 6283 GM/c³. For each run the table
shows how far the particle ends up from its starting point after one period, the largest
relative energy error along the way, and how much the end-point error shrank when the step was
halved. Theory predicts 16 for RK4 (fourth order) and 4 for Verlet (second order).

Try: change SEMI_MAJOR_AXIS (the error relative to a does not change; why?), ECCENTRICITY
(more eccentric orbits are harder; why?) or STEPS_PER_ORBIT.
"""

import math

import numpy as np

from bhlab.physics.newtonian import acceleration, kepler_period, make_state, specific_energy
from bhlab.solvers.fixed_step import integrate
from bhlab.units import BlackHole

SEMI_MAJOR_AXIS = 100.0
ECCENTRICITY = 0.5
STEPS_PER_ORBIT = (250, 500, 1000, 2000, 4000)


def main() -> None:
    periapsis = SEMI_MAJOR_AXIS * (1.0 - ECCENTRICITY)
    speed = math.sqrt(2.0 / periapsis - 1.0 / SEMI_MAJOR_AXIS)  # vis-viva equation
    start = make_state(periapsis, 0.0, 0.0, speed)
    period = kepler_period(SEMI_MAJOR_AXIS)
    energy = specific_energy(start)
    seconds = BlackHole.from_solar_masses(10.0).time_to_si(period)

    print(f"Ellipse a = {SEMI_MAJOR_AXIS:g}, e = {ECCENTRICITY:g}: period {period:.1f} GM/c³")
    print(f"(for a 10 solar-mass black hole that is {seconds:.4f} s)\n")
    print(f"{'method':8}{'steps':>7}{'step h':>9}{'end error':>13}{'max |ΔE/E|':>13}{'ratio':>8}")
    for method in ("rk4", "verlet"):
        previous = None
        for n in STEPS_PER_ORBIT:
            trajectory = integrate(acceleration, start, period / n, n, method)
            end_error = float(np.hypot(*(trajectory.states[-1, :2] - start[:2])))
            energy_error = max(abs(specific_energy(s) / energy - 1.0) for s in trajectory.states)
            ratio = "" if previous is None else f"{previous / end_error:8.2f}"
            print(f"{method:8}{n:7d}{period / n:9.3f}{end_error:13.3e}{energy_error:13.3e}{ratio}")
            previous = end_error
        print()


if __name__ == "__main__":
    main()
