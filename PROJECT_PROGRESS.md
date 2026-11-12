# Black Hole Physics Lab — Project Progress

Last updated: 2026-11-12 (Checkpoint 1A built and tested; awaiting Sebastian's approval).

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
8. Each checkpoint is built on its own branch (`checkpoint-1a`, `checkpoint-1b`, …), as Sebastian chose on
   2026-11-12. `main` holds only approved work: merge a checkpoint branch into `main` after its approval.

## Current status

| Item | State |
|---|---|
| Current stage | Stage 1 — working interactive simulation foundation (Newtonian) |
| Last completed checkpoint | **1A — project skeleton, units module, application window** (built 2026-11-12, awaiting approval) |
| Last approved checkpoint | none yet |
| Next proposed checkpoint | 1B — 2D black hole view and camera (not started; needs approval) |
| Automated tests | 113 passed, 0 failed, 0 skipped (pytest 9.2.0, Python 3.14.7, 2026-11-12). `ruff check` and `ruff format --check` clean. |
| Git | 1A is one local commit on branch `checkpoint-1a`, **not pushed**. `main` is Sebastian's commit `71f0514` ("First Stages, 1A": the prototypes and the roadmap, before any 1A code). |
| GitHub | Sebastian published `main` on 2026-11-12 as `SebastianRu1z/black-hole-simulator` (remote `origin`). Visibility not checked. Claude has pushed nothing. |

## What exists today

### The package (Checkpoint 1A)

| Module | What it does |
|---|---|
| `bhlab.constants` | c, G, GM☉, AU, solar mass in kg, day, Julian year, each with its source |
| `bhlab.units` | `BlackHole` (stores GM): geometrized ↔ SI conversion, r_g, t_g, and the Schwarzschild reference radii r_s, r_ph, r_ISCO |
| `bhlab.formatting` | numbers to 4 significant figures (`1.270 × 10⁷`), lengths in mm/m/km or AU, times from µs to years, masses in kg or M☉ |
| `bhlab.ui` | PySide6 window: mass by text field (applied with Enter), logarithmic slider (1 to 10¹¹ M☉) or preset; live table of six characteristic scales with formulas and tooltips; invalid input is reported and never applied |
| `python -m bhlab` | opens the window |

There is no simulation yet: no particles, no dynamics, no viewport.

### Prototypes (`prototypes/`, unchanged since 2026-11-11, not part of the tested package)

| File | What it does | Verification so far |
|---|---|---|
| `bh_physics.py` | Schwarzschild formulas (reference radii, circular-orbit E and L, effective potential, Page–Thorne disc flux, Planck colour) and SI conversion | only exercised through the scripts below |
| `black_hole_orbits.py` | Matplotlib sandbox: Schwarzschild timelike geodesics (fixed-rule RK4 in coordinate time) with a Newtonian twin per object; `--selftest` | built-in self-test passes 6/6 (re-run from `prototypes/` on 2026-11-12) |
| `beta1.py` | Sebastian's copy of `black_hole_orbits.py`, byte-identical | same self-test passes |
| `black_hole_render.py` | Backward ray tracer: Schwarzschild null geodesics, thin disc with Page–Thorne flux and frequency-shift factor g | no automated tests; checked by eye only |
| `black_hole.png`, `orbits_preview.png` | outputs of the two scripts | — |

They overlap parts of Stage 2 (Schwarzschild orbits) and Stage 6 (ray-traced imaging) and will be ported
into the package, with proper tests, when those stages are reached.

## Environment (checked 2026-11-12)

- Windows 11, Python 3.14.7 (the only Python installed), git 2.55.0 with a commit identity configured.
- Sebastian also works on this repository with **GitHub Desktop**. Switching branches there stashes any
  uncommitted work (this happened once during 1A). Check the branch and `git stash list` before working.
- `.venv/` was created by Sebastian in the project folder. Installed: PySide6-Essentials 6.12.0,
  shiboken6 6.12.0, pytest 9.2.0, ruff 0.17.4, numpy 2.5.4, matplotlib 3.11.2, SciPy 1.18.1 (SciPy is
  installed but not yet a declared dependency; it becomes one in 1C).
- GitHub CLI (`gh`) is not installed.
- pyqtgraph 0.14.0 resolves for this Python (pip dry run) but is not installed; it is needed from 1B.

## Architecture

As built (1A):

```
pyproject.toml   README.md   PROJECT_PROGRESS.md   CLAUDE.md   .gitignore
src/bhlab/
    __init__.py        version
    __main__.py        python -m bhlab
    constants.py       SI and astronomical constants
    units.py           BlackHole, geometrized units, reference radii
    formatting.py      text formatting of quantities (no Qt)
    ui/
        app.py             QApplication set-up, run()
        theme.py           colours and style sheet
        main_window.py     window: mass controls (left dock) + scales (centre)
        mass_controls.py   text field, slider, presets, input validation
        scales_panel.py    table of characteristic scales
tests/                 113 tests: constants, units, formatting, architecture, interface
docs/images/           screenshot used by the README
prototypes/            the original scripts, unchanged
```

Planned additions (created only when a checkpoint gives them real content): `physics/` (Newtonian in 1C,
Schwarzschild in Stage 2, Kerr in Stage 4), `solvers/` (1C), `simulation/` (1D), `analysis/` and `export/`
(1E–1F), and `docs/` PHYSICS, NUMERICAL_METHODS, EXPERIMENTS, VALIDATION, ARCHITECTURE (from 1F).

Rules: `ui/` imports the physics, never the reverse (`tests/test_architecture.py` enforces it); the engine
runs headless; internal units are geometrized (G = c = 1, lengths in GM/c², times in GM/c³) with conversion
at the edges.

Stack: Python ≥ 3.12, PySide6 (Essentials wheel), pytest, ruff, hatchling. Still to come: NumPy and SciPy
(`solve_ivp`, DOP853) in 1C, pyqtgraph for real-time 2D views in 1B, Matplotlib for export-quality figures
in 1F, ModernGL or VisPy for 3D in Stage 6.

## Roadmap

Spec sections are numbered as in Sebastian's specification (§1–§51).

| Stage | Scope | Spec | Experiments | Status |
|---|---|---|---|---|
| 1 | Interactive foundation: Newtonian engine, 2D view, particle placement, measurements, tests | §2A, §5, §6, §7, §11–§13 (Newtonian parts) | 1; Newtonian parts of 8, 9 | in progress (1A built) |
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

| # | Checkpoint | Delivers | Status |
|---|---|---|---|
| 1A | Project skeleton, units module, application window | package `bhlab`, tested constants/units/formatting modules, PySide6 window showing live characteristic scales for a chosen mass, pytest and ruff wired up | **built 2026-11-12, awaiting approval** |
| 1B | 2D black hole view and camera | pyqtgraph viewport: horizon disc, photon-sphere and ISCO circles (labelled as GR reference radii the Newtonian engine does not use), scale bar, pan/zoom/reset, cursor readout; the scales table moves to a side panel | not started |
| 1C | Newtonian physics engine (headless) | test-particle equations of motion about a point mass; velocity Verlet, RK4, SciPy DOP853 with event detection; orbital elements; pytest checks against Kepler; command-line run | not started |
| 1D | Particle placement and run controls | click-and-drag placement with a velocity vector, exact numeric inputs, rejection of invalid initial conditions, multiple particles, play/pause/reset/single-step/speed with physics decoupled from frame rate | not started |
| 1E | Trails and live measurements | orbital trails, predicted path, selected-object panel (r, v, E, L, e, a, T, periapsis, apoapsis, status), unit switching, warning where the Newtonian model stops being trustworthy | not started |
| 1F | Validation dashboard, plots, export, Stage 1 docs | conservation-error plots, solver comparison and convergence study, CSV/JSON/PNG export, Newtonian parts of README/PHYSICS/NUMERICAL_METHODS/VALIDATION | not started |

### Checkpoint 1A: what was built, and how it differs from the proposal

Built as proposed: project layout and packaging, the constants and units modules, the dark-themed window
with mass input, three presets and the live scales table, the test suite, ruff, `CLAUDE.md`, the README,
the prototypes moved to `prototypes/`, one local commit, nothing pushed.

Differences from the proposal:
- No new git repository or virtual environment was created: Sebastian had already made both in the project
  folder, so they were reused.
- ħ and k_B were left out of `bhlab.constants`. Nothing uses them before the thermodynamics module
  (Stage 9), and unused constants are dead code.
- Added because the window needed them: `bhlab.formatting`, the logarithmic mass slider, tooltips on every
  row, and a help line that turns into the error message.
- The mass field applies on Enter (or when it loses focus), not on every keystroke. Half-typed numbers
  such as the "4" in "4.3e6" would otherwise be applied, which will matter once the mass drives a simulation.
- `beta1.py` (Sebastian's byte-identical copy of `black_hole_orbits.py`) was moved into `prototypes/`
  with the others, because it imports `bh_physics.py` and must sit next to it.

## Verification matrix

| Physics model | Where | Equations implemented | Automated tests | Analytic benchmarks | Convergence evidence | Limitations documented |
|---|---|---|---|---|---|---|
| Constants, geometrized units, unit conversion | `bhlab.constants`, `bhlab.units` (1A) | yes (r_g = GM/c², t_g = GM/c³) | 45 pytest tests | GM☉/c² = 1.476625 km and GM☉/c³ = 4.925490947 µs (the pulsar-timing constant) reproduced to 1e-6 and 1e-9; c, G, AU, Julian year equal SciPy's CODATA table; exact light-year; linear mass scaling and round trips to 1e-14 | not applicable (closed-form arithmetic) | yes (module docstrings, this file) |
| Schwarzschild reference radii r_s, r_ph, r_ISCO | `bhlab.units` (1A) | stated as 2, 3, 6 × GM/c² | ratios tested | **none yet**: the values are entered as known results, not derived from the geodesic equations. Derivation is a Stage 2 task | — | yes |
| Newtonian point-mass dynamics | planned, 1C | — | — | — | — | — |
| Schwarzschild timelike geodesics | prototype script | yes | script self-test, 6 checks (not pytest) | circular-orbit period (0.01 %), weak-field precession (within 2 %), capture inside ISCO | none | partly, in docstring |
| Schwarzschild null geodesics and thin-disc image | prototype script | yes | none | none (visual check only) | none | partly, in docstring |
| Kerr, RF link, DSP, interferometry, curved-spacetime EM, research extensions | not started | — | — | — | — | — |

No model in this project may be described as validated or research-grade until its row is filled in.

Test suite breakdown (2026-11-12): constants 5, units 40, formatting 29, architecture 1, interface 38.

## Known issues and limitations

Checkpoint 1A:
- The window was checked at one size (1180 × 690) and one display scaling (125 %) only.
- Fonts are Windows fonts (Segoe UI, Cambria). Other systems fall back to their defaults; untested.
- The slider covers 1 to 10¹¹ M☉ and snaps to three significant figures; other masses must be typed.
- The interface tests drive the widgets on Qt's offscreen platform. A real launch of `python -m bhlab` was
  checked once by hand (the process stayed up, no error output), not by an automated test.

Prototypes:
- Renderer: background stars appear as short tangential dashes. Probable cause, reasoned but not yet
  tested: each star is one texel (about 0.18° wide) of a background map, so it behaves as an extended
  source; at the default camera distance of 70 M the Einstein angle is √(4M/D) ≈ 13.7°, inside the field of
  view, and lensing stretches the texels tangentially. True point sources would stay points. Revisit in Stage 6.
- Renderer needs 70–90 s for 960 × 540 (pure NumPy).
- The sandbox window has never been driven interactively by a test.

## Open decisions

- Repository name: the GitHub repository is `black-hole-simulator`; the specification planned
  `black-hole-physics-lab`. Either is fine; a rename on GitHub keeps the history. Decide before Stage 10.
- Whether checkpoint branches should be pushed to GitHub, and when. Until Sebastian says so, they stay local.
- `prototypes/beta1.py` duplicates `black_hole_orbits.py`. Keep both, or remove one?
- Order of Stages 3 and 4: §38 ranks Kerr directly after Schwarzschild, §48 schedules RF communications
  first. Default is the §48 order; confirm at the Stage 2 checkpoint.
- Licence for the repository (decide before Stage 10).

## Feedback log

- 2026-11-12 — Sebastian supplied the full specification (§1–§51) and the working agreement above.
  Emphasis: incremental checkpoints with approval, limited usage credits, electrical-engineering
  integration, Kerr physics and its visualisation as the defining advanced features.
- 2026-11-12 — Sebastian chose the project folder, approved starting Checkpoint 1A, and chose to have the
  work on a new branch `checkpoint-1a` rather than on `main`.
- 2026-11-12 — Sebastian created the git repository and published `main` to GitHub (not done by Claude).

## How to resume in a new session

1. Read this file, then look at the source tree and `git log --oneline --all`.
2. Check `git status`, the current branch and `git stash list` (GitHub Desktop may have switched branches).
3. Find "Last approved checkpoint" above. Do not assume anything later was approved. If the last completed
   checkpoint was approved in the meantime, merge its branch into `main` first, then branch for the next one.
4. If `.venv` is missing: `python -m venv .venv`, then
   `.venv\Scripts\python.exe -m pip install -e ".[dev,prototypes]"`.
5. Run `.venv\Scripts\python.exe -m pytest` and `.venv\Scripts\python.exe -m ruff check .` before changing anything.
6. Propose the next checkpoint and wait for Sebastian's explicit approval before writing code.
7. After the checkpoint: update this file (status table, verification matrix, known issues, feedback log).
