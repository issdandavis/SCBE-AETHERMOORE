# Polly Pad Auditable Runtime

This runtime is headless by design: no GUI requirement.

Core requirement met:
- Auditable by owner
- Usable by agent AI
- Safe test spots
- Decommission + cousin takeover on shutdown/failure

## Model

Polly Pad behaves like a small personal tablet for each agent:

- `books/docs`: task lane for reading and synthesis
- `web`: browser lane via HYDRA browser worker
- `lab`: sandbox lane for experiments
- `memory`: stable notes + compact snapshots

## Lifecycle

1. Active pad executes tasks.
2. Failure/shutdown captured as `exit_log`.
3. Pad is decommissioned (not silently reused).
4. Last compact state is absorbed.
5. Cousin pad is spawned with inherited compact.
6. Takeover task is enqueued with handoff bundle.

## Components

- Store: `hydra/polly_pad.py`
  - pad records
  - event log
  - compact snapshots
  - recovery ledger
- Watchdog: `scripts/polly_pad_watchdog.py`
  - scans failed tasks from Switchboard
  - decommissions source pad
  - spawns cousin
  - enqueues takeover task

## Run

```powershell
./scripts/run_polly_pad_watchdog.ps1
```

Optional:

```powershell
python scripts/polly_pad_watchdog.py --switchboard-db artifacts/hydra/headless_ide/switchboard.db --pad-db artifacts/hydra/polly_pad/pads.db --scan-limit 100
```

## Audit surface

Pad lifecycle DB:

- `artifacts/hydra/polly_pad/pads.db`

Switchboard DB:

- `artifacts/hydra/headless_ide/switchboard.db`

Key audit entities:

- `pads`
- `pad_events`
- `recoveries`
- `tasks` (switchboard)

## Notes

- This is intentionally deterministic and machine-readable.
- For vehicle/fleet real-time systems, use turnstile policy to pivot/isolate rather than stall.
