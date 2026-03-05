# Polly Cross-Model Training Quickstart

Goal: run a low-touch, governance-gated training flow from game/story/commercial data.

## One command (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer dry-run -TriggerColab
```

## What this does

1. Builds funnel data from:
- `training-data/game_sessions/**`
- `training-data/game_design_sessions/**`
- `training-data/space_commerce_sessions/**`
- `training-data/graphics_feedback/**`
- plus lore/sidekick/gacha sources
2. Runs `scripts/training_auditor.py` governance audit.
3. Stops if data is quarantined (unless `-AllowQuarantine` is set).
4. Runs HYDRA trainer mode you selected (`dry-run`, `head`, or `all`).

## Common runs

Dry-run only:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer dry-run
```

Train one head:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer head -Head AV
```

Train all heads + push adapters:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer all -PushModel
```

Push funnel dataset to HF + trigger Colab:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer dry-run -PushHF -TriggerColab
```

## Artifacts

- `training-data/funnel_cross_model/build_summary.json`
- `training-data/funnel_cross_model/merged_all.audit.json`
- `training-data/funnel_cross_model/cross_model_bootstrap_report.json`

