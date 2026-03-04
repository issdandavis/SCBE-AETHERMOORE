# Cloud Kernel Data Pipeline

This pipeline makes production content cloud-native while still enforcing deterministic local gates before shipping.

## What It Does

1. Pulls source docs and optional Notion sync.
2. Ingests multi-source external content (Airtable, Asana, Proton Mail, Gumroad, Google Business, Zapier exports).
3. Scores every record with:
- `truth_score`
- `useful_score`
- `harmful_score`
4. Splits output into:
- `curated_allowed.jsonl`
- `curated_quarantine.jsonl`
- category files under `categories/`
5. Runs dataset-level anomaly audit.
6. Ships verified artifacts to cloud targets (Hugging Face, GitHub Releases, Dropbox).
7. Rotates older local runs.

## Core Files

- Pipeline script: `scripts/cloud_kernel_data_pipeline.py`
- PowerShell launcher: `scripts/run_cloud_kernel_data_pipeline.ps1`
- Config: `training/cloud_kernel_pipeline.json`
- CI workflow: `.github/workflows/cloud-kernel-data-pipeline.yml`

## External Intake Layout

Drop production exports here:

- `training/intake/airtable/*.jsonl`
- `training/intake/asana/*.jsonl`
- `training/intake/protonmail/*.jsonl`
- `training/intake/gumroad/*.jsonl`
- `training/intake/google_business/*.jsonl`
- `training/intake/zapier/*.jsonl`

`*.json` files are also supported.

## Local Run (Cloud Shipping Enabled)

```powershell
$env:HF_TOKEN="..."
$env:GH_TOKEN="..."
$env:DROPBOX_TOKEN="..."
python scripts/cloud_kernel_data_pipeline.py --config training/cloud_kernel_pipeline.json --ship-targets hf,github
```

PowerShell wrapper:

```powershell
.\scripts\run_cloud_kernel_data_pipeline.ps1 -ShipTargets "hf,github"
```

## Build/Verify Only (No Upload)

```powershell
python scripts/cloud_kernel_data_pipeline.py --config training/cloud_kernel_pipeline.json --no-upload
```

## Optional Notion Refresh

```powershell
$env:NOTION_API_KEY="..."
python scripts/cloud_kernel_data_pipeline.py --sync-notion
```

## Outputs Per Run

- `training/runs/cloud_kernel_sync/<timestamp>/raw_production_ingest.jsonl`
- `training/runs/cloud_kernel_sync/<timestamp>/raw_combined.jsonl`
- `training/runs/cloud_kernel_sync/<timestamp>/curated_allowed.jsonl`
- `training/runs/cloud_kernel_sync/<timestamp>/curated_quarantine.jsonl`
- `training/runs/cloud_kernel_sync/<timestamp>/verification_report.json`
- `training/runs/cloud_kernel_sync/<timestamp>/run_summary.json`
- `training/runs/cloud_kernel_sync/<timestamp>.zip`

Latest pointer:

- `training/ingest/latest_cloud_kernel_sync.txt`

## Verification Policy

Default thresholds in `training/cloud_kernel_pipeline.json`:

- `truth_min: 0.62`
- `useful_min: 0.58`
- `harmful_max: 0.25`
- `dataset_anomaly_threshold: 0.78`
- `dataset_max_flagged_ratio: 0.08`

If dataset audit returns `QUARANTINE`, the pipeline exits non-zero by default and blocks shipping.

