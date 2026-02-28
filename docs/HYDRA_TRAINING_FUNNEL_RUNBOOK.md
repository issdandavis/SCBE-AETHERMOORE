# HYDRA Training Funnel Runbook

## Purpose
Build one normalized funnel from spiral search + mesh/intake + training JSONL files, then optionally publish to Hugging Face and trigger Colab.

## Primary Command
```powershell
python scripts/build_hydra_training_funnel.py `
  --repo-root C:\Users\issda\SCBE-AETHERMOORE `
  --output-dir training-data/funnel `
  --no-dedupe
```

## Optional: Publish to Hugging Face
Make sure `HF_TOKEN` is set in your shell first.

```powershell
python scripts/build_hydra_training_funnel.py `
  --repo-root C:\Users\issda\SCBE-AETHERMOORE `
  --output-dir training-data/funnel `
  --no-dedupe `
  --push-hf `
  --hf-repo issdandavis/scbe-aethermoore-training-data
```

## Optional: Trigger Colab
If `COLAB_API_URL` is not set, the script returns the manual notebook URL.

```powershell
python scripts/build_hydra_training_funnel.py `
  --repo-root C:\Users\issda\SCBE-AETHERMOORE `
  --output-dir training-data/funnel `
  --no-dedupe `
  --trigger-colab `
  --tongue KO
```

## Output Artifacts
- `training-data/funnel/sft_pairs.jsonl`
- `training-data/funnel/chat_format.jsonl`
- `training-data/funnel/merged_all.jsonl`
- `training-data/funnel/funnel_stats.json`
- `training-data/funnel/build_summary.json`

## Current Known Shell Constraint
In this Codex shell, direct outbound HF upload can fail with `WinError 10013`.  
If that happens, run the same command in your Claude shell lane where HF upload is already working.
