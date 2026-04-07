# Code A/B Matched-Budget Runbook

Purpose: replace the broken Kaggle CPU `baseline vs triangulated` notebook lane with a fair, fast benchmark that matches token budget before training.

## Problem

The old Kaggle lane compared:
- `code_baseline_l3.jsonl` — `5,000` rows
- `code_triangulated_sft.jsonl` — `47,240` rows

That is not a valid fixed-budget comparison. On the local manifest produced by [train_code_ab_fast.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/research/train_code_ab_fast.py), the full corpora differ by:
- row ratio: `9.448x`
- estimated token ratio: `6.2874x`

This is why the CPU notebook burned the 12-hour Kaggle limit.

## Fix

Use the preparation script first:

```powershell
python scripts/research/train_code_ab_fast.py --prepare-only
```

This emits matched corpora:
- [baseline_matched.jsonl](C:/Users/issda/SCBE-AETHERMOORE/artifacts/research/code_ab_fast/baseline_matched.jsonl)
- [triangulated_matched.jsonl](C:/Users/issda/SCBE-AETHERMOORE/artifacts/research/code_ab_fast/triangulated_matched.jsonl)
- [manifest.json](C:/Users/issda/SCBE-AETHERMOORE/artifacts/research/code_ab_fast/manifest.json)

Current matched snapshot:
- baseline: `5,000` rows, `1,060,324` estimated tokens
- triangulated matched: `7,460` rows, `1,060,295` estimated tokens

## Recommended run lane

Preferred:
- [code_ab_matched_budget_colab.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/code_ab_matched_budget_colab.ipynb)
- free Colab T4 GPU

Fallback:
- [kaggle_code_ab_matched_budget.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/kaggle_code_ab_matched_budget.ipynb)
- [train_code_ab_kaggle_safe.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/research/train_code_ab_kaggle_safe.py)
- Kaggle GPU on `T4` or `P100`

Avoid:
- Kaggle CPU for this benchmark

The Kaggle-safe runner now enforces this policy directly:
- GPU present: run the real matched-budget A/B
- CPU only: stop immediately unless `--allow-cpu-smoke` is set
- summary packet: `/kaggle/working/code_ab_matched_budget_summary.json`

## Training defaults

Use these defaults unless there is a reason to widen the run:
- model: `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- one epoch
- `75` max steps per condition
- LoRA `r=8`
- max sequence length `512`

These settings are intended to produce a meaningful answer quickly, not to maximize absolute model quality.

## Acceptance rule

Treat the run as valid only if:
1. both conditions use the matched corpora from the manifest
2. both conditions use the same model and trainer settings
3. the result summary is written to a single JSON file

Do not compare a full triangulated corpus against the baseline corpus and call that fixed-compute.
