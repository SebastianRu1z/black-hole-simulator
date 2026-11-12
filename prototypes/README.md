# Prototypes

Standalone scripts written before the project had a structure. They are kept unchanged as
reference implementations and will be ported into the tested `bhlab` package when their stages
are reached. Nothing here is covered by the automated test suite.

| File | What it does | Where it is headed |
|---|---|---|
| `black_hole_orbits.py` | Interactive sandbox: planets on Schwarzschild geodesics, each with a Newtonian twin for comparison. `--selftest` runs six physics checks. | Stage 2 |
| `beta1.py` | A copy of `black_hole_orbits.py`, byte for byte, saved under another name. | — |
| `black_hole_render.py` | Ray-traced image of a Schwarzschild black hole with a thin accretion disc. Writes `black_hole.png`. | Stage 6 |
| `bh_physics.py` | Formulas shared by the scripts above. They must stay in the same folder as it. | Stages 2 and 6 |

Run them from the project folder (they need numpy and matplotlib):

```powershell
.venv\Scripts\python.exe prototypes\black_hole_orbits.py
.venv\Scripts\python.exe prototypes\black_hole_orbits.py --selftest
.venv\Scripts\python.exe prototypes\black_hole_render.py
```

Known limitations are listed in `PROJECT_PROGRESS.md` under "Known issues".
