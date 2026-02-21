# Multi-AI Offline/Online Setup

This runbook sets up a local-first content pipeline so multiple AI agents can coordinate with the same source of truth offline, then mirror that content online when network services are available.

## Goal

- Keep coordination-critical content available locally at all times.
- Produce deterministic offline bundles for handoff/replay.
- Optionally mirror bundle artifacts online to Hugging Face datasets.

## Components Already in This Repo

- Offline governance baseline: `docs/OFFLINE_MODE_SPEC.md`
- Session continuity store: `docs/map-room/session_handoff_latest.md`
- Notion sync source map: `scripts/sync-config.json`
- Doc ingest pipeline: `scripts/ingest_docs_to_training_jsonl.py`
- Manifest verifier: `training/doc_verifier.py`
- HF uploader: `scripts/push_to_hf.py`
- New one-command orchestrator: `scripts/run_multi_ai_content_sync.py`
- Cloud verification+shipping pipeline: `scripts/cloud_kernel_data_pipeline.py`

## Prerequisites

- Python 3.10+
- Node.js (for optional Notion sync)
- Optional env for online mirror: `HF_TOKEN`
- Optional env for Notion sync: `NOTION_API_KEY`

## Offline-Only Setup

Run from repo root:

```powershell
python scripts/run_multi_ai_content_sync.py
```

PowerShell wrapper:

```powershell
.\scripts\run_multi_ai_content_sync.ps1
```

## Offline + Notion Refresh

```powershell
$env:NOTION_API_KEY = "your_notion_key"
python scripts/run_multi_ai_content_sync.py --sync-notion
```

Sync only specific mapped pages:

```powershell
python scripts/run_multi_ai_content_sync.py --sync-notion --notion-config-key multiAiDevelopmentCoordination --notion-config-key hydraMultiAgentCoordinationSystem
```

## Offline + Online Mirror (Hugging Face)

```powershell
$env:HF_TOKEN = "your_hf_token"
python scripts/run_multi_ai_content_sync.py --sync-notion --hf-dataset-repo issdandavis/scbe-multi-ai-corpus
```

## Outputs

Each run creates a timestamped bundle:

- `training/runs/multi_ai_sync/<timestamp>/offline_docs.jsonl`
- `training/runs/multi_ai_sync/<timestamp>/doc_manifest.json`
- `training/runs/multi_ai_sync/<timestamp>/run_summary.json`
- `training/runs/multi_ai_sync/<timestamp>.zip`
- Pointer to latest run: `training/ingest/latest_multi_ai_sync.txt`

## How Agents Use It

- Offline lane uses `filesystem` MCP to read bundle files.
- Offline lane uses `scbe_map_room_read_latest` and `scbe_map_room_write_latest` for continuity.
- Offline lane uses `scbe_decide_offline` for deterministic policy gating.
- Online lane mirrors JSON/manifest artifacts to a HF dataset.
- Online lane keeps GitHub as canonical versioned source.

## Recommended Cadence

- During active development: run every major session end.
- For shared teams: run on a scheduler (for example every 4-6 hours) with `--sync-notion` and optional HF mirror.

## Cloud-First Variant

If you want cloud storage as the primary dataset source for model training, use:

- Runbook: `docs/CLOUD_KERNEL_DATA_PIPELINE.md`
- Script: `scripts/cloud_kernel_data_pipeline.py`
- Workflow: `.github/workflows/cloud-kernel-data-pipeline.yml`
