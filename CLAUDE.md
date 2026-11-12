# Black Hole Physics Lab — instructions for Claude Code sessions

## First, every session

1. Read `PROJECT_PROGRESS.md`. It records the current stage, the last checkpoint Sebastian
   **approved**, the verification status of every physics model, and the exact next step.
2. Then look at the code and `git log`. Never rebuild or overwrite existing work.

## How this project is developed

- One small checkpoint at a time: plan → build → test → demonstrate → explain → report → **stop**.
- Ask for approval before writing code. Never begin the next checkpoint without an explicit yes.
  Silence is not approval, and approving one checkpoint does not approve the rest of the stage.
- Usage credits are limited: no unrequested features, no unnecessary rewrites.
- Each checkpoint is built on its own branch (`checkpoint-1a`, `checkpoint-1b`, …). `main` holds
  only work Sebastian has approved; merge a checkpoint branch into `main` only after approval.
- Never push, publish or change anything on GitHub without Sebastian's explicit approval.
  Sebastian also uses GitHub Desktop on this repository, so check `git status`, the current
  branch and `git stash list` before starting work.
- End every checkpoint report with: "CHECKPOINT COMPLETE — Awaiting your approval. Do you approve
  moving to the next checkpoint, or would you like to change or improve anything first?"

## Commands (Windows)

```powershell
python -m venv .venv                                             # only if .venv is missing
.venv\Scripts\python.exe -m pip install -e ".[dev,prototypes]"   # install / refresh
.venv\Scripts\python.exe -m pytest                               # tests
.venv\Scripts\python.exe -m ruff check .                         # lint
.venv\Scripts\python.exe -m ruff format --check .                # formatting
.venv\Scripts\python.exe -m bhlab                                # run the application
```

## Rules for the code

- `bhlab.ui` may import the physics modules; the physics modules never import the interface.
  `tests/test_architecture.py` enforces this.
- Internal units are geometrized (G = c = 1; lengths in GM/c², times in GM/c³). Convert to SI or
  astronomical units only at the edges, through `bhlab.units`.
- Every physics model needs tests against analytic results, and a row in the verification matrix
  in `PROJECT_PROGRESS.md`. Do not call anything validated before that row is filled in.
- Invalid input is rejected with a clear message. It is never silently "corrected".
- Cite only sources that have been checked. Do not invent references or results.
- `prototypes/` is reference material: leave it unchanged, port from it.
