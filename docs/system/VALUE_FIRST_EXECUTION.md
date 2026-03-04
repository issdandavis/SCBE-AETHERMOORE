# Value-First Execution (Budget-Aware)

Goal: keep security gates while maximizing useful outcomes per dollar.

## What this adds

1. Utility and ROI scoring per routed task.
2. Budget-aware mode selection:
- `api_first` (lowest cost)
- `browser_assist` (balanced)
- `full_browser` (highest capability / highest cost)
3. Risk caps that prevent expensive modes on high-risk tasks.

## Files

1. `scripts/system/biomorphic_control_plane.py`
2. `config/governance/value_execution_profiles.json`

## Run

```powershell
python scripts/system/biomorphic_control_plane.py `
  --goal "publish article from approved sources" `
  --domain dev.to `
  --event-type manual `
  --risk medium `
  --budget-cents 10 `
  --dry-run
```

## Readouts in output

1. `state_vector.execution_mode`
2. `state_vector.estimated_cost_cents`
3. `state_vector.utility_score`
4. `state_vector.roi_score`
5. `decision_record.pending_integrations` (missing portal/auth or budget overruns)

## Tuning

Edit `config/governance/value_execution_profiles.json`:

1. `intent_value_weights` to prioritize outcomes (leads, publish, release, research).
2. `execution_modes` to tune cost/quality/speed assumptions.
3. `risk_mode_caps` to allow/deny expensive modes by risk level.
4. `default_budget_cents` to hard-limit default spend per task.

