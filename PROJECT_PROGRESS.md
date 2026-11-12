# Black Hole Physics Lab — Project Progress

Last updated: 2026-11-12 (planning session; no code written in this session).

This file is the single source of truth for where the project stands.
**Read it first in every new session, then inspect the code. Do not rebuild or overwrite existing work.**

## Working agreement (set by Sebastian; applies to every session)

1. One small checkpoint at a time: PLAN → BUILD → TEST → DEMONSTRATE → EXPLAIN → CHECKPOINT REPORT → STOP.
2. Ask for approval before writing code. Never begin the next checkpoint without an explicit yes.
   Silence is not approval. Approving one checkpoint does not approve the rest of the stage.
3. Keep everything that already works working; run the regression tests before each report.
4. Scientific accuracy before complexity. Nothing is called validated without a test that shows it.
5. Usage credits are limited: no unrequested features, no unnecessary rewrites.
6. Nothing goes to GitHub without explicit approval of the account, repository name, visibility and push.
7. Every checkpoint report has the sections Completed / What I should test / Scientific explanation /
   Next checkpoint, and ends with: "CHECKPOINT COMPLETE — Awaiting your approval. Do you approve moving to
   the next checkpoint, or would you like to change or improve anything first?"

## Current status

| Item | State |
|---|---|
| Current stage | Stage 1 — working interactive simulation foundation (Newtonian) |
| Last completed checkpoint | none |
| Last approved checkpoint | none |
| Next proposed checkpoint | **1A — project skeleton, units module, application window** (proposed 2026-11-12, awaiting approval) |
| Automated tests | none yet (no pytest suite exists) |
| Git | no repository yet; nothing published anywhere |

## What exists today (inspected 2026-11-12)

Three standalone prototype scripts written on 2026-11-11, before the project specification existed.
They are **not** a completed checkpoint: no package structure, no pytest suite, no version control.

| File | What it does | Verification so far |
|---|---|---|
| `bh_physics.py` | Schwarzschild formulas (reference radii, circular-orbit E and L, effective potential, Page–Thorne disc flux, Planck colour) and SI conversion | only exercised through the two scripts below |
| `black_hole_orbits.py` | Matplotlib sandbox: Schwarzschild timelike geodesics (fixed-rule RK4 in coordinate time) with a Newtonian twin per object; `--selftest` | built-in self-test passed 6/6 on 2026-11-11; the window was only run headlessly, never clicked |
| `black_hole_render.py` | Backward ray tracer: Schwarzschild null geodesics, thin disc with Page–Thorne flux and frequency-shift factor g | no automated tests; checked by eye only |
| `black_hole.png`, `orbits_preview.png` | outputs of the two scripts | — |
| `.venv/` | Python 3.14 environment with numpy 2.5.4 and matplotlib 3.11.2 | local only; never commit |

They overlap parts of Stage 2 (Schwarzschild orbits) and Stage 6 (ray-traced imaging). Plan: keep them
unchanged under `prototypes/` as reference implementations and port their physics into the package, with
proper tests, when those stages are reached.

## Environment (checked 2026-11-12)

- Windows 11, Python 3.14.7 (the only Python installed), git 2.55.0 with a commit identity configured.
- GitHub CLI (`gh`) is not installed. Only needed for Stage 10.
- A pip dry run confirmed these resolve for Python 3.14: PySide6-Essentials 6.12.0, pyqtgraph 0.14.0,
  SciPy 1.18.1, pytest 9.2.0, ruff 0.17.4. None of them is installed yet.

## Architecture

Today: three flat scripts (see above).

Planned (directories are created only when a checkpoint gives them real content):

```
pyproject.toml  README.md  PROJECT_PROGRESS.md  CLAUDE.md  .gitignore
src/bhlab/
    constants.py, units.py   physical constants, unit systems, black-hole scales      (1A)
    physics/                 newtonian.py (1C); schwarzschild.py (Stage 2); kerr.py (Stage 4)
    solvers/                 integrators, event detection, solver diagnostics          (1C)
    simulation/              world state, particles, fixed-step clock                  (1D)
    analysis/, export/       measurements, plots, CSV/JSON/PNG                         (1E–1F)
    ui/                      PySide6 application                                       (1A onward)
tests/                       pytest suite, grows with every checkpoint
docs/                        PHYSICS, NUMERICAL_METHODS, EXPERIMENTS, VALIDATION, ARCHITECTURE
prototypes/                  the three scripts above, unchanged
```

Rules: `ui/` imports the physics, never the reverse; the engine runs headless; internal units are
geometrized (G = c = 1, lengths in GM/c², times in GM/c³) with conversion at the edges.

Stack: Python ≥ 3.12, NumPy, SciPy (`solve_ivp`, DOP853), PySide6 (Essentials wheel), pyqtgraph for
real-time 2D views and live plots, Matplotlib for export-quality figures, pytest, ruff.
3D rendering (ModernGL or VisPy) is deferred to Stage 6.

## Roadmap

Spec sections are numbered as in Sebastian's specification (§1–§51).

| Stage | Scope | Spec | Experiments | Status |
|---|---|---|---|---|
| 1 | Interactive foundation: Newtonian engine, 2D view, particle placement, measurements, tests | §2A, §5, §6, §7, §11–§13 (Newtonian parts) | 1; Newtonian parts of 8, 9 | planning |
| 2 | Schwarzschild relativity: timelike and null geodesics, ISCO, photon sphere, time dilation, radial infall, Newton vs GR, validation | §2B, §8, §9, §13 | 2–7, 10 | not started (prototypes exist) |
| 3 | RF communication physics: emitters/receivers, null-geodesic signal paths, gravitational and Doppler shift via g = (k·u)_obs/(k·u)_em, Shapiro delay, received-signal analysis | §43, §26 | EE 1, EE 2 | not started |
| 4 | Kerr black holes: geodesics with E, L_z, Carter constant; horizons, ergosphere, frame dragging, prograde/retrograde ISCO, orbital frequencies; Penrose process as analytic demonstration | §23, §24, §31, §36 | 11, 12, 20 | not started |
| 5 | Digital signal processing: FFT, PSD, spectrograms, filters, noise, correlation, matched filter | §44 | EE 3 | not started |
| 6 | Advanced visualisation and relativistic imaging: 3D view, backward ray tracing from a local orthonormal frame, shadows and critical curves, thin-disc imaging | §4, §25, §26, §27 | 13, 14, 15 | not started (prototype exists) |
| 7 | Radio astronomy and interferometry: stations, baselines, visibilities, (u,v) sampling, image reconstruction | §45 | EE 4, EE 5 | not started |
| 8 | Electromagnetics in curved spacetime: field tensor, local-observer E and B, simple magnetosphere models, Blandford–Znajek scaling | §42, §46 | EE 6, EE 7 | not started |
| 9 | Optional research extensions, each only if it can be validated: geodesic deviation and tides, thermodynamics, ringdown/quasinormal modes, parameter estimation, advanced numerics | §28–§30, §32, §33 | 16–19 | not started |
| 10 | Presentation and publication: docs, worked case study, publication-quality figures, numerical-relativity outlook (document only), GitHub Actions, publish after approval | §15, §18, §34, §39 | — | not started |

Cross-cutting from Stage 1 onward: headless scriptable engine with reproducible JSON configurations (§33),
the verification matrix below (§36), and references that are checked before they are cited (§37).

### Stage 1 checkpoints

| # | Checkpoint | Delivers | Sebastian can test |
|---|---|---|---|
| 1A | Project skeleton, units module, application window | local git repo, `pyproject.toml`, package `bhlab`, tested constants/units module, PySide6 window showing live characteristic scales for a chosen mass, pytest and ruff wired up | launch the app, change the mass, run the tests |
| 1B | 2D black hole view and camera | pyqtgraph viewport: horizon disc, photon-sphere and ISCO circles (labelled as GR reference radii the Newtonian engine does not use), scale bar, pan/zoom/reset, cursor readout | drag, zoom, toggle the reference circles |
| 1C | Newtonian physics engine (headless) | test-particle equations of motion about a point mass; velocity Verlet, RK4, SciPy DOP853 with event detection; orbital elements; pytest checks against Kepler; command-line run | run an orbit from the command line, run the tests |
| 1D | Particle placement and run controls | click-and-drag placement with a velocity vector, exact numeric inputs, rejection of invalid initial conditions, multiple particles, play/pause/reset/single-step/speed with physics decoupled from frame rate | place particles, start and stop time |
| 1E | Trails and live measurements | orbital trails, predicted path, selected-object panel (r, v, E, L, e, a, T, periapsis, apoapsis, status), unit switching, warning where the Newtonian model stops being trustworthy | compare readouts with hand calculations |
| 1F | Validation dashboard, plots, export, Stage 1 docs | conservation-error plots, solver comparison and convergence study, CSV/JSON/PNG export, Newtonian parts of README/PHYSICS/NUMERICAL_METHODS/VALIDATION | reproduce a convergence plot, open exported files |

### Checkpoint 1A as proposed (not started)

Build:
- Project layout: `pyproject.toml` (distribution `black-hole-physics-lab`, import name `bhlab`,
  Python ≥ 3.12), `src/bhlab/`, `tests/`, `.gitignore`, a short honest `README.md`, and a `CLAUDE.md`
  that makes every new Claude Code session read this file and follow the working agreement.
- Move the three prototype scripts and their two images into `prototypes/`, unchanged.
- `bhlab.constants` and `bhlab.units`: c, G, ħ, k_B (CODATA), the IAU nominal solar mass parameter
  GM☉ = 1.3271244×10²⁰ m³ s⁻² (so a mass given in solar masses never depends on the poorly known G),
  the astronomical unit; conversion between geometrized, SI and astronomical units; a `BlackHole` object
  giving r_g = GM/c², t_g = GM/c³, r_s = 2 r_g, r_ph = 3 r_g, r_ISCO = 6 r_g.
- `python -m bhlab`: dark-themed PySide6 window (orange, blue, purple, white accents) with a mass input in
  solar masses, presets (10 M☉; Sgr A*, 4.3×10⁶ M☉; M87*, 6.5×10⁹ M☉) and a live table of the
  characteristic scales in SI and astronomical units, each row showing its formula.
- Tests: unit conversions (solar r_s ≈ 2.953 km, round trips, linear scaling with mass, radius ratios) and
  an offscreen smoke test that the window builds and updates when the mass changes.
- Fresh virtual environment; installs PySide6-Essentials (roughly 80 MB), pytest, ruff, and numpy +
  matplotlib so the prototypes still run. Local git commit. Nothing pushed.

Not in 1A: no viewport, no particles, no dynamics.

## Verification matrix

| Physics model | Where | Equations implemented | Automated tests | Analytic benchmarks | Convergence evidence | Limitations documented |
|---|---|---|---|---|---|---|
| Units and reference radii | planned, 1A | — | — | — | — | — |
| Newtonian point-mass dynamics | planned, 1C | — | — | — | — | — |
| Schwarzschild timelike geodesics | prototype script | yes | script self-test, 6 checks (not pytest) | circular-orbit period (0.01 %), weak-field precession (within 2 %), capture inside ISCO | none | partly, in docstring |
| Schwarzschild null geodesics and thin-disc image | prototype script | yes | none | none (visual check only) | none | partly, in docstring |
| Kerr, RF link, DSP, interferometry, curved-spacetime EM, research extensions | not started | — | — | — | — | — |

No model in this project may be described as validated or research-grade until its row is filled in.

## Known issues

- Prototype renderer: background stars appear as short tangential dashes. Probable cause, reasoned but not
  yet tested: each star is one texel (about 0.18° wide) of a background map, so it behaves as an extended
  source; at the default camera distance of 70 M the Einstein angle is √(4M/D) ≈ 13.7°, inside the field of
  view, and lensing stretches the texels tangentially. True point sources would stay points. Revisit in Stage 6.
- Prototype renderer needs 70–90 s for 960×540 (pure NumPy).
- Prototype sandbox window has never been used interactively.

## Open decisions

- Order of Stages 3 and 4: §38 ranks Kerr directly after Schwarzschild, §48 schedules RF communications
  first. Default is the §48 order; confirm at the Stage 2 checkpoint.
- Licence for the public repository (decide before Stage 10).

## Feedback log

- 2026-11-12 — Sebastian supplied the full specification (§1–§51) and the working agreement above.
  Emphasis: incremental checkpoints with approval, limited usage credits, electrical-engineering
  integration, Kerr physics and its visualisation as the defining advanced features, no GitHub publishing yet.

## How to resume in a new session

1. Read this file, then look at the source tree and `git log`.
2. Find "Last approved checkpoint" above. Do not assume anything later was approved.
3. If a virtual environment is missing: `python -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -e ".[dev]"`
   (available once Checkpoint 1A has created `pyproject.toml`).
4. Run the test suite before changing anything.
5. Propose the next checkpoint and wait for Sebastian's explicit approval before writing code.
6. After the checkpoint: update this file (status table, verification matrix, known issues, feedback log).
