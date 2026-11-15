# Black Hole Physics Lab — Project Progress

Last updated: 2026-11-15. Checkpoints 1A, 1B, 1C and 1D-1 are approved and merged into `main` (only 1A is
pushed). 1D-2 is approved and merged too. Checkpoint 1E-1 (particle tracker panel) is built on
`checkpoint-1e1` and awaits approval.

This file is the single source of truth for where the project stands.
**Read it first in every new session, then inspect the code. Do not rebuild or overwrite existing work.**

## Working agreement (set by Sebastian; applies to every session)

1. One small checkpoint at a time: PLAN → EXPLAIN → BUILD → TEST → TEACH → REVIEW → STOP. Sebastian changed
   the process on 2026-11-12; `CLAUDE.md` describes each step and is the authority on these rules.
2. Ask for approval before writing code. Never begin the next checkpoint without an explicit yes.
   Silence is not approval. Approving one checkpoint does not approve the rest of the stage.
3. Keep everything that already works working; run the regression tests before each report.
4. Scientific accuracy before complexity. Nothing is called validated without a test that shows it.
5. Usage credits are limited: no unrequested features, no unnecessary rewrites.
6. Nothing goes to GitHub without explicit approval of the account, repository name, visibility and push.
7. Every checkpoint report has the sections Completed / What I should test / Learning summary (parts A–F of
   `CLAUDE.md`) / Understanding check /
   Next checkpoint, and ends with: "CHECKPOINT COMPLETE — Awaiting your approval. Do you approve moving to
   the next checkpoint, or would you like to change or improve anything first?"
8. Each checkpoint is built on its own branch (`checkpoint-1a`, `checkpoint-1b`, …), as Sebastian chose on
   2026-11-12. `main` holds only approved work: merge a checkpoint branch into `main` after its approval.
9. Teach the code: explain before building, give a learning summary afterwards, and keep
   `LEARNING_NOTES.md` current (set by Sebastian on 2026-11-12).
10. A review reports findings and changes nothing without approval. External skills are inspected,
    explained and approved before they are installed or run.

## Current status

| Item | State |
|---|---|
| Current stage | Stage 1 — working interactive simulation foundation (Newtonian) |
| Last completed checkpoint | **1E-1 — particle tracker panel** (built 2026-11-15, awaiting approval) |
| Last approved checkpoint | **1D-2** (approved by Sebastian on 2026-11-15). 1D-1 approved 2026-11-15. 1C-2 approved on 2026-11-13; 1A, 1B and 1C-1 on 2026-11-12 |
| Checkpoint in progress | None. 1E-1 is complete on `checkpoint-1e1` and reported; not merged into `main`. |
| Next step | Sebastian approves 1E-1 (then merge `checkpoint-1e1` into `main`) and decides on 1E-2 (trails and predicted path) or 1E-3 (gravitational field view). No code before an explicit yes. |
| Automated tests | 482 passed, 0 failed on `checkpoint-1e1` (pytest 9.2.0, Python 3.14.7, 2026-11-15); 448 on `main`. `ruff check` and `ruff format --check` clean. |
| Git | 1A (commit `ccea74b`) is merged into `main`. Each later checkpoint is built on its own branch and merged after approval. 1B (`7e9526b`, `e51d367` by Sebastian, and the completing commit) was merged into `main` locally on 2026-11-12 after Sebastian's approval. Branch `checkpoint-1c` was created from `main` (at `50b8baa`) after Sebastian approved starting 1C-1. 1C-1 and 1C-2 were committed there and, after Sebastian approved 1C-2 on 2026-11-13, merged into `main` locally. |
| GitHub | Remote `origin` is `SebastianRu1z/black-hole-simulator`, created by Sebastian. On 2026-11-12 Sebastian asked for the approved 1A work to be pushed to it; `main` was pushed at commit `d903597`. Push `main` only when Sebastian asks; never push an unapproved checkpoint. Visibility not checked. On 2026-11-12 Sebastian also published `checkpoint-1b` himself, at `e51d367`. The approved 1B work on `main` and the completing commit on `checkpoint-1b` are not pushed: push only when Sebastian asks. |

## What exists today

### The package (Checkpoints 1A and 1B)

| Module | What it does |
|---|---|
| `bhlab.constants` | c, G, GM☉, AU, solar mass in kg, day, Julian year, light-year, each with its source |
| `bhlab.units` | `BlackHole` (stores GM): geometrized ↔ SI conversion, r_g, t_g, and the Schwarzschild reference radii r_s, r_ph, r_ISCO |
| `bhlab.formatting` | numbers to 4 significant figures (`1.270 × 10⁷`), lengths in mm/m/km or AU, or in whichever unit from mm to light-years suits the size (`format_length_auto`), times from µs to years, masses in kg or M☉ |
| `bhlab.ui` | PySide6 window: mass by text field (applied with Enter), logarithmic slider (1 to 10¹¹ M☉) or preset; live table of six characteristic scales with formulas and tooltips; invalid input is reported and never applied |
| `bhlab.ui.viewport`, `bhlab.ui.scale_bar`, `bhlab.ui.view_options` (1B) | pyqtgraph map of the orbital plane in units of r_g: horizon disc, photon-sphere and ISCO circles with labels that hide when zoomed out, grid, drag to pan, wheel zoom about the cursor, zoom buttons, reset, zoom and pan limits, scale bar in r_g and in km, AU or light-years, cursor readout (x, y, r, φ) in the status bar, check boxes for the circles and the grid. The scales table sits in a right-hand panel |
| `python -m bhlab` | opens the window |

### Checkpoint 1E-1 (on `checkpoint-1e1`, awaiting approval)

| Module | What it does |
|---|---|
| `bhlab.simulation.tracking` | `track`: r, φ, speed, radial speed, circular and escape speed, v/v_esc, orbital elements, fate (bound / escapes / reaches stop radius / stopped), time to next periapsis by Kepler's equation, reliability of Newton (1/r and v²); `comes_down_to` now shared with the placement preview |
| `bhlab.ui.tracker_panel` | right-hand TRACKER section: coloured list of particles with their fate; 17 rows of live numbers for the selected one, each in GM units with SI underneath; redrawn at most 10 times a second while running |
| `bhlab.ui.main_window` (extended) | selection in the list and on the map kept in step; tracker refreshed on mass change and on pause. Fixed a 1D-1 bug: the "running slower" notice stayed on after pausing |

### Checkpoint 1D-2 (approved 2026-11-15)

| Module | What it does |
|---|---|
| `bhlab.simulation.placement` | `drag_velocity`: v = d / r^(3/2) (a sideways arrow of length r gives the circular orbit); `preview`: the orbit a start would give, or why it is refused, and whether it comes down to r = 2 |
| `bhlab.simulation.model` (extended) | `check_start` shared by `add_particle` and the preview; `remove_particle`; particle numbers are never reused |
| `bhlab.ui.viewport` (extended) | Place button; `_MapViewBox` hands the left drag and click to the view in place mode, wheel zoom unchanged; blue or red arrow with head; selection ring; `particle_index_at` (12 px); `_Marks` stops dots from swallowing clicks |
| `bhlab.ui.main_window`, `bhlab.ui.particle_form` (extended) | live preview text while dragging, add on release, select by click, Remove button and Delete key (a text field keeps Delete for itself), fields filled with the placed or selected state |

### Checkpoint 1D-1 (approved 2026-11-15)

| Module | What it does |
|---|---|
| `bhlab.solvers.adaptive.AdaptiveStepper` | DOP853 one step at a time, with the state anywhere inside the latest step from its dense output |
| `bhlab.simulation.model` | `Simulation`: one simulated clock, one solver per particle (least advanced stepped first), particles refused at r ≤ 2 or speed ≥ c, stopped exactly where they reach r = 2 (including a dip inside between two steps), reset |
| `bhlab.ui.simulation_runner` | real time → simulated time (speed × Δt), 16 ms timer, 0.1 s cap on a gap, 8 ms compute budget per frame and a "cannot keep up" notice |
| `bhlab.ui.run_controls`, `bhlab.ui.particle_form` | Play/Pause, Step, Reset, speed slider (1 to 100 000 GM/c³ per second, 1-2-5 steps) with the physical meaning for the mass; form for x, y, vₓ, v_y with a "Circular speed" button and a summary of moving and stopped particles |
| `bhlab.ui.viewport` (extended) | draws particles: dots while moving, a cross when stopped |

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
  shiboken6 6.12.0, pytest 9.2.0, ruff 0.17.4, numpy 2.5.4, matplotlib 3.11.2, SciPy 1.18.1. NumPy has been
  a declared dependency since 1C-1 and SciPy since 1C-2.
- GitHub CLI (`gh`) is installed (seen on 2026-11-12 in `C:\Program Files\GitHub CLI`; not used, and its
  login state was not checked). Node.js is not installed.
- pyqtgraph 0.14.0 is installed and has been a declared dependency since 1B.
- Screenshots: `QWidget.grab()` on a window shown with `WA_DontShowOnScreen` renders the real window (real
  fonts, 125 % scaling, hence 1800 × 1000 px) without putting it on screen. On Qt's offscreen platform,
  which the tests use, every character is a box unless `QT_QPA_FONTDIR=C:\Windows\Fonts` is set.

## Architecture

As built (1A and 1B):

```
pyproject.toml   README.md   PROJECT_PROGRESS.md   LEARNING_NOTES.md   CLAUDE.md   .gitignore
src/bhlab/
    __init__.py        version
    __main__.py        python -m bhlab
    constants.py       SI and astronomical constants
    units.py           BlackHole, geometrized units, reference radii
    formatting.py      text formatting of quantities (no Qt)
    physics/
        newtonian.py       point-mass gravity: acceleration, E, L, circular orbits, Kepler period (1C-1)
        orbital_elements.py  a, e, periapsis, apoapsis, period, orientation from one state (1C-2)
    solvers/
        fixed_step.py      RK4, velocity Verlet, integrate() -> Trajectory (1C-1)
        adaptive.py        DOP853 via SciPy with events, integrate_adaptive() -> AdaptiveTrajectory (1C-2)
    orbit.py           python -m bhlab.orbit: orbital elements and events from the command line (1C-2)
    ui/
        app.py             QApplication set-up, run()
        theme.py           colours and style sheet
        main_window.py     window: controls (left dock), map (centre), scales (right dock), cursor readout
        mass_controls.py   text field, slider, presets, input validation
        view_options.py    check boxes for the reference circles and the grid
        viewport.py        the 2D map: reference circles, camera, overlays
        scale_bar.py       scale bar and its 1-2-5 rounding
        scales_panel.py    table of characteristic scales
    simulation/
        model.py           Simulation: clock, particles, stop at r = 2 (1D-1)
    ui/ (1D-1 additions)   simulation_runner.py, run_controls.py, particle_form.py
tests/                 411 tests: constants, units, formatting, architecture, interface, map, physics, solvers, CLI, simulation
examples/              integrator_comparison.py: RK4, Verlet and DOP853 compared (1C-1, 1C-2)
docs/images/           screenshots of each checkpoint; the README shows the latest
prototypes/            the original scripts, unchanged
```

Planned additions (created only when a checkpoint gives them real content): more of `physics/`
(Schwarzschild in Stage 2, Kerr in Stage 4), `simulation/` (1D), `analysis/` and `export/`
(1E–1F), and `docs/` PHYSICS, NUMERICAL_METHODS, EXPERIMENTS, VALIDATION, ARCHITECTURE (from 1F).

Rules: `ui/` imports the physics, never the reverse (`tests/test_architecture.py` enforces it); the engine
runs headless; internal units are geometrized (G = c = 1, lengths in GM/c², times in GM/c³) with conversion
at the edges.

Stack: Python ≥ 3.12, NumPy, SciPy, PySide6 (Essentials wheel), pyqtgraph, pytest, ruff, hatchling. Still to
come: Matplotlib for export-quality figures
in 1F, ModernGL or VisPy for 3D in Stage 6.

## Roadmap

Spec sections are numbered as in Sebastian's specification (§1–§51).

| Stage | Scope | Spec | Experiments | Status |
|---|---|---|---|---|
| 1 | Interactive foundation: Newtonian engine, 2D view, particle placement, measurements, tests | §2A, §5, §6, §7, §11–§13 (Newtonian parts) | 1; Newtonian parts of 8, 9 | in progress (1A, 1B and 1C approved) |
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
| 1A | Project skeleton, units module, application window | package `bhlab`, tested constants/units/formatting modules, PySide6 window showing live characteristic scales for a chosen mass, pytest and ruff wired up | **approved 2026-11-12** |
| 1B | 2D black hole view and camera | pyqtgraph viewport: horizon disc, photon-sphere and ISCO circles (labelled as GR reference radii the Newtonian engine does not use), scale bar, pan/zoom/reset, cursor readout; the scales table moves to a side panel | **approved 2026-11-12** |
| 1C | Newtonian physics engine (headless) | test-particle equations of motion about a point mass; velocity Verlet, RK4, SciPy DOP853 with event detection; orbital elements; pytest checks against Kepler; command-line run | split on 2026-11-12. **1C-1** (equations of motion, RK4, velocity Verlet, Kepler and convergence tests): **approved 2026-11-12**. **1C-2** (DOP853 with events, orbital elements, command-line run): **approved 2026-11-13** |
| 1D | Particle placement and run controls | click-and-drag placement with a velocity vector, exact numeric inputs, rejection of invalid initial conditions, multiple particles, play/pause/reset/single-step/speed with physics decoupled from frame rate | split: **1D-1** (simulation loop, run controls, numeric input): **approved 2026-11-15**. **1D-2** (mouse placement, selection, removal): **approved 2026-11-15** |
| 1E | Trails and live measurements | split on 2026-11-15 after Sebastian's feedback. **1E-1** (built 2026-11-15, awaiting approval) particle tracker panel: list of particles; for the selected one live r, φ, speed, circular and escape speed, v/v_esc, E, L, orbit kind, e, a, periapsis, apoapsis, period, time to next periapsis, fate (bound / escapes / reaches r = 2), values in GM units and SI for the mass, warning where Newton stops being trustworthy. **1E-2** trails and predicted path. **1E-3** gravitational field view (spec §5): Newtonian acceleration arrows, potential and field-strength map in physical units, tidal stretching, with a note on why relativity cannot be drawn as arrows | proposed, not started |
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

### Checkpoint 1B: what was built, and how it differs from the plan

Built as planned in the table above: the pyqtgraph map in units of r_g with the horizon disc and the
photon-sphere and ISCO circles, the scale bar, pan, zoom and reset, the cursor readout, and the scales
table in a side panel.

Added because the map needed them:
- Labels on the circles that hide when the view is zoomed out too far to hold them, and check boxes that
  switch the two reference circles and the grid on and off and double as the colour legend.
- Limits on the camera: the view cannot show less than 0.5 r_g across or leave |x|, |y| ≤ 10⁶ r_g.
- `LIGHT_YEAR` and `format_length_auto`, so that the scale bar and the readout use km, AU or light-years
  as the mass requires.
- A larger window (1440 × 800, minimum 1200 × 640) to hold three columns.

Finished in a second session on 2026-11-12, after the first stopped at the usage limit:
- Direct tests for `format_length_auto` and `LIGHT_YEAR`.
- A fixed width for the left axis. pyqtgraph sized that axis to its longest tick label, so the map area
  changed width while panning or zooming (by 18 px between the centre and y ≈ −80 000 r_g). Where the map
  was limited by its width the scale changed with it, by up to 4.5 % in the test environment. The axis now
  reserves the width of the longest label the view can show. Eight tests were written first and failed on
  the old code. The drag test, which had been loosened to 1 %, is back at the default tolerance of 10⁻⁶.
- README, screenshot and `LEARNING_NOTES.md`.

### Checkpoint 1C-1: what was built, and how it differs from the plan

Built as planned: `physics/newtonian.py` (acceleration, E, L, circular orbits, Kepler period, rejection
of r = 0 and non-finite input), `solvers/fixed_step.py` (RK4, velocity Verlet, `integrate` returning a
read-only `Trajectory`), 52 tests, NumPy declared as a dependency, the architecture test extended to
the new modules, and the comparison script `examples/integrator_comparison.py`.

Differences from the plan:
- The first-order form f(t, y) lives in the solver (`first_order_system`), not in the physics module.
  The physics then only supplies the force law, and both integrators take the same argument.
- Added `make_state`, which validates a state in one place.
- The tests were checked by breaking each integrator on purpose in a temporary copy: 7 tests failed for
  wrong RK4 weights, 5 for a wrong Verlet velocity update.

### Checkpoint 1C-2: what was built, and how it differs from the plan

Built as planned: `physics/orbital_elements.py`; `solvers/adaptive.py` (DOP853 through SciPy, events for
periapsis, apoapsis and crossing a radius, terminal events); `python -m bhlab.orbit`; SciPy declared as a
dependency; DOP853 added to `examples/integrator_comparison.py`; 53 tests.

Decisions the plan did not spell out:
- The wrapper does not report events at exactly t = 0. SciPy reported a periapsis at t = 0 for an orbit
  that starts there.
- It refuses rtol < 1e-13, because SciPy would quietly raise it to about 2.2e-14, and it refuses a stopping
  event that already holds at t = 0.
- Infinite apoapsis, period and (for a parabola) semi-major axis are `math.inf`; only the periapsis
  direction of a circle is `None`.
- The input check of the fixed-step `integrate` moved into a shared `validated_state`, used by both
  integrators. Its behaviour is unchanged and its tests still pass.
- `python -m bhlab.orbit` writes UTF-8, so that symbols such as M☉ survive output redirected to a file on
  Windows.
- The event table starts with a "start" row. In a one-orbit run the return to periapsis lands within the
  tolerance just after the end time, so it is often not listed.
- Checked by breaking the code on purpose in a temporary copy. A sign error in the eccentricity vector at
  first failed only one test, because every hand-worked state sat at periapsis or apoapsis, where r·v = 0.
  A test from a state in the middle of the orbit was added.

### Checkpoint 1D-1: how it was built

The code was written on 2026-11-13 in a session that left it uncommitted and unrecorded. On 2026-11-14
Sebastian confirmed he had approved 1D-1; it was committed unchanged (`d34cd86`), reviewed (see "Review of
2026-11-14"), and finished: the capture fixes, the screenshot `docs/images/checkpoint-1d1.png`, the README
and `LEARNING_NOTES.md`. Seen working in the real window off screen: four particles, the plunging one
stopped on the horizon.

### Review of 2026-11-14 (thermos and improve, on Checkpoint 1C; report only)

Run on the committed 1C code (`50b8baa..085276f`). Findings and decisions:

| # | Finding | Decision |
|---|---|---|
| I1 | A plunge without `--stop-radius` crashed the command line with a traceback; `integrate_adaptive` raised an unexplained `RuntimeError` at r → 0 | **fixed** (`b18933a`): `IntegrationError`, horizon default, start inside refused, exit code 1 |
| I2 | Fixed-step integrators step over r = 0 and fling the particle out (E from −0.1 to +4.96) without warning | **fixed** (`b18933a`): optional `stop_radius`, `Trajectory.stopped` |
| I3 | No test covered a plunge without a stop | **fixed**: 21 tests; the 16 for new behaviour fail on the old code |
| T1 | Planar orbit events (`periapsis`, `apoapsis`, `radius_reached`) live in the generic solver module | **planned**: small cleanup checkpoint before Stage 2, moving them to `physics/` |
| T3 | `adaptive.py` imports shared plumbing (`first_order_system`, `validated_state`, types) from `fixed_step.py` | **planned**: same cleanup, into a shared solver module |
| T2 | `orbit._run` computes and prints in one function | when 1E/1F need the same numbers |
| T4, T5, I4 | duplicated `_require_positive_finite` and inline checks; string-typed `kind`/`method`; `integrate` refuses NumPy integers | in passing, when those files are edited |

No security findings. Not audited: interface code, performance, dependencies, docs.

## Verification matrix

| Physics model | Where | Equations implemented | Automated tests | Analytic benchmarks | Convergence evidence | Limitations documented |
|---|---|---|---|---|---|---|
| Constants, geometrized units, unit conversion | `bhlab.constants`, `bhlab.units` (1A) | yes (r_g = GM/c², t_g = GM/c³) | 46 pytest tests | GM☉/c² = 1.476625 km and GM☉/c³ = 4.925490947 µs (the pulsar-timing constant) reproduced to 1e-6 and 1e-9; c, G, AU, Julian year and light-year equal SciPy's CODATA table; the light-year constant is exact (checked with whole-number arithmetic); linear mass scaling and round trips to 1e-14 | not applicable (closed-form arithmetic) | yes (module docstrings, this file) |
| Schwarzschild reference radii r_s, r_ph, r_ISCO | `bhlab.units` (1A) | stated as 2, 3, 6 × GM/c² | ratios tested | **none yet**: the values are entered as known results, not derived from the geodesic equations. Derivation is a Stage 2 task | — | yes |
| 2D map (display geometry, not a physics model): map ↔ pixel coordinates, scale bar, cursor readout, choice of length unit | `bhlab.ui.viewport`, `bhlab.ui.scale_bar`, `bhlab.ui.main_window`, `bhlab.formatting` (1B) | r = √(x² + y²), φ = atan2(y, x); 1-2-5 rounding of the scale bar; physical length = length in r_g × GM/c² | 55 map tests, 12 for `format_length_auto` | circles drawn at 2, 3 and 6 r_g; the point (3, 4) reads r = 5 and φ = 53.1°, and 5 r_g = 73.83 km for 10 M☉; bar length in pixels equals its length × the scale; the map point under the cursor stays put during wheel zoom (1e-6 r_g); panning and zooming leave the size of the map area unchanged, panning also the scale | not applicable | yes (module docstrings, known issues below) |
| Newtonian point-mass dynamics: equations of motion and the RK4 and velocity Verlet integrators | `bhlab.physics.newtonian`, `bhlab.solvers.fixed_step` (1C-1) | yes (d²r/dt² = −r/r³; E = v²/2 − 1/r; L = x v_y − y vₓ; RK4; velocity Verlet) | 52 pytest tests (21 physics, 31 solvers) | by hand: a, E, L at sample points; circular speed √(1/r), E = −1/(2r), L = √r; T = 2π a^(3/2) agrees with the SI form of Kepler's law; RK4 exact on a cubic and equal to the Taylor series of e^h; Verlet exact for constant acceleration; orbits close after one Kepler period (RK4 to 1e-8 a for a = 25, 100, 400); periapsis 50 and apoapsis 150 for a = 100, e = 0.5 | measured orders 4.06 (RK4) and 2.00 (Verlet) from halving the step; over 40 orbits the RK4 energy error grows 15-fold while Verlet's stays bounded; Verlet conserves L to 1e-12; harmonic oscillator: RK4 energy decays monotonically, Verlet's stays within 1 % | yes (module docstrings; Newtonian model not valid near the black hole). Fixed steps only: adaptive steps and events come in 1C-2 |
| Newtonian orbital elements | `bhlab.physics.orbital_elements` (1C-2) | yes (eccentricity vector, a = −1/(2E), r_p = L²/(1 + e), r_a = a(1 + e), T = 2π a^(3/2)) | 14 pytest tests | by hand: circle; ellipse from periapsis, from apoapsis and from a mid-orbit state (E = π/2); rotated orbits; clockwise motion; hyperbola (a = −100, e = 1.5); exact parabola (E = 0); fall from rest (e = 1, a = r₀/2) | elements constant along a DOP853 run to 1e-8 over three orbits | yes (module docstring) |
| Adaptive integration (DOP853) and events | `bhlab.solvers.adaptive` (1C-2) | SciPy `solve_ivp` with DOP853; events as zero crossings of r·v and r − R | 27 pytest tests, plus 12 for the command line | periapsis and apoapsis at k·T and (k + ½)·T to 1e-8; crossing of r = 100 at 1070.80 from Kepler's equation to 1e-9; free fall from r = 10 stops at r = 2 at the analytic 33.70 to 1e-9; custom event at T/4 on a circle | end error falls monotonically as rtol tightens (1.5e-4 to 1.7e-9 for rtol 1e-6 to 1e-12); at e = 0.9 an end error of 1.1e-6 with 1334 evaluations, against about 0.03 for RK4 with 10 000 | yes (module docstring; not symplectic; tolerance is per step) |
| Plunge handling: stop at a radius, failure at r = 0 | `solvers.adaptive`, `solvers.fixed_step`, `orbit` (review fix) | stop radius r = 2; `IntegrationError` | 21 pytest tests | fall from rest at r = 10 stops at the analytic 33.70 (adaptive, to 1e-9; fixed step, within one step); failure at the analytic time to the centre, (π/2)√(r₀³/2) = 35.12, to 1e-3 | not applicable | yes (module docstrings, learning notes 2.15) |
| Simulation clock and real-time playback | `simulation.model`, `ui.simulation_runner` (1D-1) | one clock, least-advanced stepping, dense output, speed × Δt | 42 simulation, 14 stepper, 39 interface tests | positions after the same simulated time agree at any frame rate; free fall stops at r = 2 at 33.70; a circular orbit returns after one Kepler period | not applicable | yes (module docstrings) |
| Placement rule and orbit preview | `simulation.placement` (1D-2) | v = d / r^(3/2); reaches r = 2 if periapsis ≤ 2 and (bound or r·v < 0) | 17 pytest tests, plus 20 window tests driven with the mouse | sideways arrow of length r gives v = √(1/r) and e = 0 to 1e-12 (r = 3, 10, 250); √2 r gives E = 0 to 1e-15; v at (3, 4) equals d·5^(−3/2); periapsis/apoapsis 50/150 for the a = 100 ellipse; preview refusals match `add_particle` | not applicable | yes (module docstring, learning notes 2.16) |
| Particle tracking: speeds, fate, Kepler timing, reliability | `simulation.tracking` (1E-1) | v_circ = √(1/r), v_esc = √(2/r), E, L, elements, eccentric anomaly from the state, t_p = a^(3/2)(E_a − e sin E_a) | 22 pytest tests, plus 12 window tests | circular orbit at r = 8 (all speeds, E, T); fates of five hand-worked states; time to periapsis T/2 from apoapsis, also on a rotated orbit (1e-10); after 0.1, 0.37, 0.5, 0.83 of an orbit the prediction matches the solver's periapsis event to 1e-8; reliability thresholds at 1 % and 10 % | not applicable | yes (module docstring, learning notes 2.17–2.19) |
| Schwarzschild timelike geodesics | prototype script | yes | script self-test, 6 checks (not pytest) | circular-orbit period (0.01 %), weak-field precession (within 2 %), capture inside ISCO | none | partly, in docstring |
| Schwarzschild null geodesics and thin-disc image | prototype script | yes | none | none (visual check only) | none | partly, in docstring |
| Kerr, RF link, DSP, interferometry, curved-spacetime EM, research extensions | not started | — | — | — | — | — |

No model in this project may be described as validated or research-grade until its row is filled in.

Test suite breakdown (2026-11-14, `checkpoint-1d`): constants 6, units 40, formatting 41, architecture 1, interface 38,
map 62, Newtonian physics 26, fixed-step solvers 43, orbital elements 14, adaptive solver 29, stepper 14, command
line 16, simulation 42, simulation interface 39, placement 17 (1D-2), placement interface 20 (1D-2), tracking 22 (1E-1), tracker interface 12 (1E-1).
Total 482.
(The breakdown above the 1D-2 entries is for 2026-11-14.)

## Known issues and limitations

Checkpoint 1A:
- The window was checked at one size (1180 × 690) and one display scaling (125 %) only.
- Fonts are Windows fonts (Segoe UI, Cambria). Other systems fall back to their defaults; untested.
- The slider covers 1 to 10¹¹ M☉ and snaps to three significant figures; other masses must be typed.
- The interface tests drive the widgets on Qt's offscreen platform. A real launch of `python -m bhlab` was
  checked once by hand (the process stayed up, no error output), not by an automated test.

Checkpoint 1B:
- The map was looked at in one window size (1440 × 800) at one display scaling (125 %), in a rendering of
  the real window made off screen. Sebastian has not yet judged it on his own screen; the grid is subtle.
- After "Reset view" the outermost tick labels, −10 and 10, are not printed. They sit exactly on the edge
  of the map, and pyqtgraph drops a label that would stick out while the grid is on. Before the left axis
  got its fixed width the x axis happened to show them, because the map was then a little wider than tall.
  Showing slightly more than ±10 r_g after a reset would bring them back on both axes.
- The left axis reserves room for eight characters, so near the centre there is empty space between the
  axis title and the numbers.
- Far from the centre and zoomed in, neighbouring tick labels can show the same text, because pyqtgraph
  prints at most six significant digits (99 999.85 and 99 999.95 both print as 99999.9). The cursor readout
  shows four significant figures, so it cannot resolve small distances there either. The map itself is
  not affected.
- The interface tests run without fonts (Qt's offscreen platform finds none on this machine and draws
  boxes), so they check geometry and text content, not appearance. The suite also passes with fonts
  enabled through `QT_QPA_FONTDIR`.

Checkpoint 1C-1:
- The integrators loop in pure Python: about 10 µs per RK4 step and 3 µs per Verlet step for one
  particle. Enough for tests and a few particles; to be measured again when 1D animates many.
- Fixed steps waste work on eccentric orbits (at e = 0.9 and 1000 steps per orbit Verlet misses its start
  point by 138 r_g). Use the adaptive solver from 1C-2 there.
- The fixed-step integrators cannot stop at a radius: a particle that falls onto r = 0 between two steps
  receives a huge but finite kick. The adaptive solver's terminal radius event handles this.
- The engine is not connected to the window yet (1D).

Checkpoint 1C-2:
- The tolerances bound the error of each step, not the error at the end. Over three orbits at rtol = 1e-10
  the energy drifts by 6.7e-10; long runs need a check of the conservation laws, as the command line prints.
- Event times are accurate to about 1e-9 of a period at the default tolerance. An event that falls within
  that margin of the end time may or may not be reported.
- DOP853 is not symplectic: over very many orbits its energy error grows slowly, unlike Verlet's.
- A periapsis direction is reported only for e ≥ 1e-10; below that the orbit is treated as circular.
- Still Newtonian: no horizon, and the radius event at r = 2 is a geometric stop, not the physics of a
  horizon.

Checkpoint 1D-1:
- Particles leave no trail yet (1E), so one that leaves the view is simply gone from sight.

Checkpoint 1E-1:
- The right-hand panel is long: the scales and view options are below the tracker and need scrolling.
- In the off-screen checks the pace of simulated time varied between about 75 % and 100 % of the speed
  set, with and without the tracker, from run to run: load on the machine, not the panel (measured
  three times; the tracker's own redraw takes about 0.2 ms). Worth watching on Sebastian's screen.
- The SI values of energy (J/kg) and angular momentum (m²/s) are per kilogram of the particle.

Checkpoint 1D-2:
- A placed particle starts where the mouse was pressed, so its coordinates carry pixel noise
  (7.005884389 rather than 7). Type the numbers in the form when exact values matter.
- Whether the buttons fit their panel can only be checked by eye: the tests' offscreen platform has no
  fonts. Checked in the real window, off screen, at 1440 × 800 and 125 % scaling.
- pyqtgraph ignores mouse moves that arrive faster than 100 per second. The release always carries the
  final position, so placement is exact; only the arrow drawn during very fast drags may lag a frame.
- There is no Escape to cancel a drag: release over an invalid spot, or switch Place off.
- Only seen off screen at one size and scaling; Sebastian has not yet judged it on his own screen.

Prototypes:
- Renderer: background stars appear as short tangential dashes. Probable cause, reasoned but not yet
  tested: each star is one texel (about 0.18° wide) of a background map, so it behaves as an extended
  source; at the default camera distance of 70 M the Einstein angle is √(4M/D) ≈ 13.7°, inside the field of
  view, and lensing stretches the texels tangentially. True point sources would stay points. Revisit in Stage 6.
- Renderer needs 70–90 s for 960 × 540 (pure NumPy).
- The sandbox window has never been driven interactively by a test.

## Review skills (inspected 2026-11-12; none installed; used once on 2026-11-14 by reading their files)

Both are plain Markdown instructions: no scripts, no hooks, no packages to install.

| Skill | Source read | What it does | Fit and conditions |
|---|---|---|---|
| `improve` | `shadcn/improve` at commit `cac56e1` (2026-09-12): `SKILL.md` and three reference files, MIT | Read-only audit in nine categories (bugs, security, performance, tests, tech debt, dependencies, tooling, docs, direction). Returns a ranked findings table, then writes a plan file into `plans/` for each finding chosen | Suits Python. Has no physics or numerics category: give it those as focus hints. Use its `quick` level, because the repository is small. `execute` (another model edits code in a git worktree) and `--issues` (publishes plans on GitHub) need explicit approval each time. Its documented installer, `npx skills add`, needs Node.js and runs third-party code: copy the four files instead |
| `thermo-nuclear-code-quality-review` | `cursor/plugins`, folder `thermos`, last changed in commit `dc41543` (2026-05-28): one `SKILL.md`, MIT | A strict maintainability rubric for a branch's diff: needless abstraction, tangled branching, files over 1 000 lines, logic in the wrong layer | Written for Cursor, mostly with TypeScript in mind. Its file format is the one Claude Code skills use, so it should load once copied by hand (not yet tried). Little to find while the largest file has 325 lines. Its prompt tells the reviewer to restructure code: here it only reports |

On 2026-11-14 Sebastian asked for both to be run with `npx skills use`. Node.js is not installed, so the two
repositories were cloned into a temporary folder and their `SKILL.md` files followed by hand, report only.

Claude Code's own `/code-review`, `/security-review` and `/simplify` are available without installing anything.

## Open decisions

- Repository name: the GitHub repository is `black-hole-simulator`; the specification planned
  `black-hole-physics-lab`. Either is fine; a rename on GitHub keeps the history. Decide before Stage 10.
- Checkpoint branches on GitHub: Sebastian published `checkpoint-1b` himself on 2026-11-12. Claude still
  pushes nothing unless asked.
- Install the two review skills, as copies of the inspected files in Sebastian's personal Claude skills
  folder? Asked on 2026-11-12, not answered yet.
- Map polish: Sebastian approved 1B as it looks on his screen. Showing slightly more than ±10 r_g after a
  reset, so that the outermost tick labels appear, stays optional; change it only if he asks.
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
- 2026-11-12 — Sebastian approved Checkpoint 1A, approved starting Checkpoint 1B, and asked for the work to
  be committed to GitHub.
- 2026-11-12 — After the first conversation grew to about 500K tokens, Sebastian set new permanent rules:
  recover context from the files instead of the conversation; teach the code (explanation before building,
  learning summary and understanding check after, `LEARNING_NOTES.md`); use the `improve` and
  `thermo-nuclear-code-quality-review` skills only after inspection and approval; and the process
  PLAN → EXPLAIN → BUILD → TEST → TEACH → REVIEW → STOP. All of it is recorded in `CLAUDE.md`.
- 2026-11-12 — Sebastian approved finishing Checkpoint 1B, including the fix for the map changing size
  while panning. He committed the document edits himself (`e51d367`) and published `checkpoint-1b` on
  GitHub. The questions about installing the review skills were left unanswered.
- 2026-11-12 — Sebastian set a model-selection rule: Opus High by default, and Opus Max only after an
  explicit, justified recommendation that he accepts. Recorded in `CLAUDE.md`.
- 2026-11-12 — Sebastian ran the program, looked at the window and approved Checkpoint 1B. The work was
  committed and merged into `main` locally, not pushed. The understanding-check questions and the
  review-skill installation were not answered yet.
- 2026-11-12 — Sebastian approved starting Checkpoint 1C-1, accepting the split of 1C into 1C-1 and 1C-2.
  1C-1 was built on branch `checkpoint-1c` with Opus High.
- 2026-11-12 — Sebastian approved Checkpoint 1C-1. It was committed on `checkpoint-1c`, not merged or pushed.
  The understanding-check questions were not answered.
- 2026-11-12 — Sebastian approved starting Checkpoint 1C-2. Built on `checkpoint-1c` with Opus High.
- 2026-11-13 — Sebastian approved Checkpoint 1C-2. 1C-2 was committed and `checkpoint-1c` merged into `main`
  locally, not pushed. The understanding-check questions were not answered.
- 2026-11-14 — Sebastian asked for the thermos and improve reviews, then said "do recommended": fix I1–I3
  within 1D and plan the T1/T3 cleanup before Stage 2. He confirmed he had approved 1D-1, whose code a
  2026-11-13 session had left uncommitted and unrecorded. Session model: Opus 5.5.
- 2026-11-15 — Sebastian approved Checkpoint 1D-1. `checkpoint-1d` was merged into `main` locally, not
  pushed. The understanding-check questions were not answered.
- 2026-11-15 — Sebastian approved starting Checkpoint 1D-2 as proposed (Place mode, v = d / r^(3/2),
  selection and removal). Built on `checkpoint-1d2` with Opus 5.5.
- 2026-11-15 — Sebastian liked placing particles with their own speed. He asked for a panel to track
  individual particles (speed, escape information, other relevant quantities) and to "see the gravitational
  effects of the black hole", wondering whether that waits for 3D. Answer given: a 2D field view fits
  Stage 1 (spec §5); relativistic views follow in Stage 2 and 3D in Stage 6. Planned as 1E-1 (tracker)
  and 1E-3 (field view). 1D-2 not yet explicitly approved.
- 2026-11-15 — Sebastian approved 1D-2 ("Yes, go ahead") and starting 1E-1, the particle tracker panel.
  `checkpoint-1d2` merged into `main` locally, not pushed.
- 2026-11-15 — 1E-1 built: tracker panel as Sebastian asked (individual particles, speed, escape
  information). Awaiting his approval.

## How to resume in a new session

1. Read this file, then look at the source tree and `git log --oneline --all`.
2. Check `git status`, the current branch and `git stash list` (GitHub Desktop may have switched branches).
3. Find "Last approved checkpoint" above. Do not assume anything later was approved. If the last completed
   checkpoint was approved in the meantime, merge its branch into `main` first, then branch for the next one.
4. If `.venv` is missing: `python -m venv .venv`, then
   `.venv\Scripts\python.exe -m pip install -e ".[dev,prototypes]"`.
5. Run `.venv\Scripts\python.exe -m pytest` and `.venv\Scripts\python.exe -m ruff check .` before changing anything.
6. Propose the next checkpoint and wait for Sebastian's explicit approval before writing code.
7. After the checkpoint: update this file (status table, verification matrix, known issues, feedback log)
   and `LEARNING_NOTES.md`.
