# Polly NPC Round Table Quickstart

Build lore-grounded NPCs as training data, then feed them into cross-model training.

## Step 1: Build NPC roundtable dataset

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_npc_roundtable.ps1 -RunAudit
```

Outputs:
- `training-data/npc_roundtable_sessions/npc_cards.jsonl`
- `training-data/npc_roundtable_sessions/npc_roundtable_sft.jsonl`
- `training-data/npc_roundtable_sessions/npc_roundtable_dpo.jsonl`
- `training-data/npc_roundtable_sessions/npc_registry.json`

## Step 2: Run cross-model bootstrap

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer dry-run
```

## Step 3: Train specific heads

Dialogue-heavy NPC quality (UM):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer head -Head UM
```

Canon/safety consistency (DR):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/run_polly_cross_model_bootstrap.ps1 -RunTrainer head -Head DR
```

