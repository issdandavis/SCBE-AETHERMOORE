# AetherBrowse Transparency + Budget Guardrails

## What Is Now Wired

- Deterministic step execution in runtime (`PLAN -> step wait -> result -> retry`).
- Live run telemetry API:
  - `GET /api/runs/latest?limit=8`
  - `GET /api/runs/{run_id}`
- Visual transparency lane on `http://127.0.0.1:8400/home` (glass panel showing status, confidence, step progress).
- Worker now supports:
  - `extract_article`
  - `extract_video`
- OctoArmor daily cost caps (provider/global) enforced in throttle:
  - `SCBE_<PROVIDER>_DAILY_BUDGET_USD`
  - `SCBE_DAILY_BUDGET_USD`
  - `SCBE_EST_COST_PER_1K_<PROVIDER>`

## Your Current Budget Policy

- `SCBE_CEREBRAS_DAILY_BUDGET_USD=1`
- `SCBE_EST_COST_PER_1K_CEREBRAS=0.005`

When estimated 24h spend reaches `$1.00`, Cerebras is blocked for additional requests until the rolling 24h window clears.

## Run It (Headless + Visually Transparent)

1. Runtime:

```powershell
python aetherbrowse/runtime/server.py
```

2. Worker (headless):

```powershell
$env:AETHERSCREEN_HEADLESS='1'
python aetherbrowse/worker/browser_worker.py
```

3. Open transparency dashboard:

```text
http://127.0.0.1:8400/home
```

## Check Tentacle Spend State

```python
from src.fleet.octo_armor import OctoArmor
armor = OctoArmor()
for row in armor.tentacle_status():
    if row["tentacle"] == "cerebras":
        print(row)
```
