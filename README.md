# Black Hole Physics Lab

An interactive numerical laboratory for black hole physics, built one validated step at a time:
from Newtonian gravity, through Schwarzschild and Kerr spacetimes, to electrical-engineering
laboratories on top of them (RF links, signal processing, radio interferometry).

**Status: early development — Stage 1, Checkpoint 1A.**
The roadmap, and the verification status of every physics model, are in
[PROJECT_PROGRESS.md](PROJECT_PROGRESS.md).

![The application window at Checkpoint 1A](docs/images/checkpoint-1a.png)

## What works today

- **Units and scales** (`bhlab.constants`, `bhlab.units`): SI constants with their sources,
  conversion between geometrized units (G = c = 1) and SI, and the characteristic radii and times
  of a non-rotating black hole of any mass.
- **Desktop window** (`python -m bhlab`): choose a mass by typing, by slider or by preset, and see
  every characteristic scale update live, each with its formula.
- **Automated tests** for the unit conversions, the number formatting, the separation between
  physics and interface, and the window itself.

Not there yet: the simulation. There are no particles, no orbits and no relativity in the package so
far. Those arrive in later checkpoints, each one tested before the next begins.

## Quick start (Windows)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,prototypes]"
.venv\Scripts\python.exe -m bhlab
.venv\Scripts\python.exe -m pytest
```

Python 3.12 or newer is required.

## Using the physics without the window

```python
from bhlab.units import BlackHole

sgr_a = BlackHole.from_solar_masses(4.3e6)
sgr_a.schwarzschild_radius  # 1.27e10 m
sgr_a.time_unit  # 21.2 s, the time light needs to cross GM/c^2
sgr_a.length_to_si(6.0)  # the ISCO radius, 6 GM/c^2, in metres
```

## Prototypes

`prototypes/` holds the standalone scripts the project started from: a Schwarzschild orbit sandbox
and a ray-traced image of a black hole with an accretion disc. They run, but they are not part of
the tested package. See [prototypes/README.md](prototypes/README.md).
