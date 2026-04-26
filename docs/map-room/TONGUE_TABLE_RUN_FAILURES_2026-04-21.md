# Tongue Table Run Failures — 2026-04-21

## What actually failed

### `brick1-v1`
- Not a hard code crash.
- Artifacts show clean checkpoints through step `225`.
- Training loss improved, but structural benchmark pass rate stayed at `0.0%`.
- `validator_pass_rate` moved from `0.41` down to `0.29`, but that metric did **not** trigger trainer stop in the current code.

### `v2-weighted-rerun`
- Not a hard code crash either.
- Checkpoints `25` and `50` exist and contain a valid adapter payload.
- The run never produced `lora_final/`, so downstream consumers treated it as missing.

### `v3-chemistry`, `v3-periodic`, `v3-transport-cloze`
- Zombie dependency failure.
- They were waiting on:
  - `artifacts/tongue-table-lora-v2-weighted/lora_final/adapter_model.safetensors`
- The actual parent directory in this checkout is:
  - `artifacts/tongue-table-lora-v2-weighted-rerun/`
- So the failure was:
  1. exact-name dependency drift
  2. no fallback to latest checkpoint
  3. no recovery path to materialize `lora_final` from an interrupted run

## Root causes

1. `transport_atomic` remains the hardest map and drags the mixed-run objective.
2. Structural benchmark criteria are much stricter than drill loss and table-lock.
3. Parent adapters were treated as binary:
   - `lora_final exists` = usable
   - otherwise = unusable
4. Run naming drift (`v2-weighted` vs `v2-weighted-rerun`) was not tolerated.

## Fixes added

### New support module
- `scripts/train/tongue_table_run_support.py`
- Adds:
  - latest checkpoint discovery
  - best-available adapter resolution
  - alias resolution for renamed run directories
  - checkpoint-to-`lora_final` materialization

### New recovery tool
- `scripts/train/recover_tongue_table_run.py`
- Purpose:
  - recover interrupted runs into a usable `lora_final`
  - populate canonical paths from alias runs

### Continual wrapper hardening
- `scripts/train_brick1_continual.py`
- `verify_and_eval()` now accepts the best available adapter instead of hard-failing only on missing `lora_final`

## Prevention rules

1. Every dependent run must resolve parents through `best available adapter`, not direct `lora_final` string concatenation.
2. If a run has adapter checkpoints, it is considered recoverable.
3. Renamed reruns must either:
   - keep the canonical alias path populated, or
   - be resolved through alias-aware lookup.
4. Structural failure and infrastructure failure must be logged separately.
   - Structural failure: loss improves, benchmark still fails.
   - Infrastructure failure: parent not found, no checkpoint recovery, broken path.
5. New launcher code should fail fast with a clear message if it cannot resolve a parent adapter within one pass.

## Recommended next run policy

1. Freeze `brick2` and `brick3` as known-good anchors.
2. Use recovered checkpoints as parents only for exploratory branches, not as evidence-grade finals.
3. Isolate `transport_atomic` into its own curriculum instead of burying it inside every mixed run.
