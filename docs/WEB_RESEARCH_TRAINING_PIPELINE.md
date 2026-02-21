# Web Research Training Pipeline

Script: `scripts/web_research_training_pipeline.py`

## Purpose

Automate this chain:

1. Pull up-to-date web research URLs (Google News RSS per topic).
2. Scan URLs with HYDRA headless + Multi-Model Modal Matrix.
3. Gate content via antivirus membrane and decision logic.
4. Emit training-ready JSONL (`allowed` + `quarantine`).
5. Audit allowed records and write `StateVector` + `DecisionRecord`.
6. Optionally upload artifacts to Hugging Face dataset.
7. Optionally notify n8n webhook for downstream automation.

## Linux-first run

```bash
python3 scripts/web_research_training_pipeline.py \
  --topics "space debris cleanup" "autonomous drone navigation" "radiation hardened avionics" \
  --max-per-topic 6 \
  --backend playwright \
  --max-tabs 6
```

## With Hugging Face upload

```bash
export HF_TOKEN=hf_xxx
python3 scripts/web_research_training_pipeline.py \
  --topics "mars robotics" "swarm autonomy" \
  --upload-hf \
  --hf-repo issdandavis/scbe-kernel-datasets
```

## With n8n handoff

```bash
python3 scripts/web_research_training_pipeline.py \
  --topics "space robotics" \
  --n8n-webhook "https://your-n8n-host/webhook/scbe-research-ingest"
```

## Offline replay (no live browser scan)

```bash
python3 scripts/web_research_training_pipeline.py \
  --topics "space robotics" \
  --scan-json artifacts/hydra/mmx_headless_run.json \
  --skip-core-check
```

## Outputs

Run directory:

- `training/runs/web_research/<run_id>/discovered_urls.json`
- `training/runs/web_research/<run_id>/hydra_scan.json`
- `training/runs/web_research/<run_id>/curated_allowed.jsonl`
- `training/runs/web_research/<run_id>/curated_quarantine.jsonl`
- `training/runs/web_research/<run_id>/audit.json`
- `training/runs/web_research/<run_id>/core_health.json`
- `training/runs/web_research/<run_id>/statevector.json`
- `training/runs/web_research/<run_id>/decision_record.json`
- `training/runs/web_research/<run_id>/summary.json`

Intake file:

- `training/intake/web_research/web_research_<run_id>.jsonl`

## Notes

- Core gate uses these tests by default:
  - `tests/test_antivirus_membrane.py`
  - `tests/test_extension_gate.py`
  - `tests/test_hydra_turnstile.py`
  - `tests/test_multi_model_modal_matrix.py`
- Use `--skip-core-check` to bypass the gate for exploratory runs.
