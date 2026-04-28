# Zero-Cost Own-Model Operating Contract - 2026-04-28

## Goal

Build and operate an SCBE-owned model, using SCBE systems and the SCBE harness, that can complete long-running work with no paid cloud spend.

Allowed cost:

- electricity
- local storage wear
- existing internet connection

Not allowed by default:

- Hugging Face Jobs paid GPU dispatch
- paid Colab tiers
- paid Kaggle compute
- API-token inference loops that bill by usage
- deleting daily-use tools to make temporary training space

## Operating Rule

Train and improve small local adapters first. Do not chase one giant model before the harness can repeatedly evaluate and route smaller models.

The model stack should be:

1. base open-weight model
2. local SCBE LoRA adapters
3. frozen eval gates
4. optional local GGUF/Ollama export
5. agent harness routes for bounded long-running tasks

## First Local Profile

The first zero-cost profile is:

- `config/model_training/scbe-zero-cost-local-0.5b.json`

It uses:

- base model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- backend: `unsloth-qlora`
- local output: `training/runs/scbe-zero-cost-local-0.5b`
- no hub push
- no cloud dispatch
- max local run length: 250 steps for the first smoke lane

Training data comes from the already consolidated local regularized buckets:

- coding model
- aligned foundations
- operator agent bus
- governance security
- research bridge

## Required Harness Loop

The loop is:

```text
bucket index -> regularized SFT -> local adapter train -> focused eval -> harness task -> failure rows -> next adapter
```

Promotion requires:

1. model trains locally or emits a local-only script without cloud fallback
2. eval gates pass
3. adapter output can be routed through GeoSeal / 21D / decision records
4. a bounded repo task is completed by the harness
5. failures become training rows instead of being lost

## Commands

Preflight:

```powershell
python scripts/scbe-system-cli.py model preflight --profile scbe-zero-cost-local-0.5b --json
```

Emit local training script:

```powershell
python scripts/scbe-system-cli.py model train --profile scbe-zero-cost-local-0.5b --emit-script artifacts/model_training/scbe-zero-cost-local-0.5b-train.py --json
```

Run local training only after preflight says local is ready:

```powershell
python artifacts/model_training/scbe-zero-cost-local-0.5b-train.py
```

Consolidate model artifacts without deleting paths:

```powershell
python scripts/system/consolidate_model_artifacts.py --min-mb 1 --apply
```

## Current Constraint

If the machine lacks CUDA, Unsloth, TRL, Transformers, or enough VRAM, the profile must stop at `emit-only`. It must not silently route to HF Jobs or Colab.

That is intentional. The point is zero-dollar local autonomy, not accidentally spending money or burning the user's workflow again.

## Next Useful Work

1. Make the local preflight green by installing only the missing local training dependencies when disk headroom allows.
2. Run the 0.5B smoke adapter.
3. Evaluate against:
   - `tests/interop/test_view_token_envelope.py`
   - `tests/test_geoseal_search_field.py`
   - `tests/test_state21_product_metric.py`
   - coding/operator bucket evals
4. Add harness-generated failure rows back into the bucket index.
5. Export the best small adapter to local GGUF/Ollama only after eval passes.

