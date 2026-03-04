# SCBE Headless IDE Quickstart (ClayBot Example)

This is a local-first example of a headless IDE workflow built on HYDRA Switchboard.

## What it does

- Queues role-separated tasks: `planner -> coder -> reviewer -> memory`
- Runs headless coding workers
- Applies turnstile safety decisions per task
- Produces visuals without Figma:
  - `artifacts/hydra/headless_ide/headless_ide_dashboard.html`
  - `artifacts/hydra/headless_ide/headless_ide_flow.mmd`

## One command (PowerShell)

```powershell
./scripts/run_headless_ide_demo.ps1
```

## Python command (direct)

```powershell
python scripts/scbe_headless_ide_demo.py --db artifacts/hydra/headless_ide/switchboard.db --out-dir artifacts/hydra/headless_ide --workspace .
```

## Remote/virtual worker mode

Run workers on another machine against the same Switchboard DB location:

```powershell
python -m hydra.remote_coding_worker --db artifacts/hydra/headless_ide/switchboard.db --roles planner,coder,reviewer,memory --workspace . --domain fleet
```

## Notes

- `run_cmd` tasks are command-prefix restricted by default (`python,pytest`).
- Workspace path safety prevents writing outside the selected workspace root.
- Worker outputs include `StateVector` and `DecisionRecord` in role messages.
