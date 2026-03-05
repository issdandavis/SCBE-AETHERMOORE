# Cross-Talk Reliability Runbook

## Why
Cross-talk reliability breaks when packet mirrors drift between:
1. packet JSON files (`artifacts/agent_comm/<day>/`)
2. lane bus (`artifacts/agent_comm/github_lanes/cross_talk.jsonl`)
3. markdown mirrors (`notes/_inbox.md`, `notes/_context.md`, `agents/codex.md`)

## Tool
`scripts/system/crosstalk_reliability_manager.py`

## Commands
Run from `C:\Users\issda\SCBE-AETHERMOORE`.

### Audit today
```powershell
python scripts/system/crosstalk_reliability_manager.py
```

### Audit specific day
```powershell
python scripts/system/crosstalk_reliability_manager.py --day 20260304
```

### Auto-repair missing mirrors
```powershell
python scripts/system/crosstalk_reliability_manager.py --day 20260304 --repair
```

## Output
Report file:
- `artifacts/agent_comm/<day>/crosstalk-reliability-report-<timestamp>.json`

Contains:
1. packet totals
2. missing-surface counts
3. per-packet missing map
4. repair counts (if enabled)

## Operational policy
1. Run audit every 4 hours during active multi-agent sessions.
2. Run `--repair` immediately if missing mirrors > 0.
3. Require at least one `ack` packet per active lane (`lane_assignment`/`handoff`) before lane close.
