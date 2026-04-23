# Exporting Lattice Notes to Hugging Face Datasets

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-06

## What changed

Lattice route output can now be staged to JSONL and optionally uploaded to a Hugging Face dataset repo from the bridge.

## Parameters

- `hf_output_path`: local JSONL path
- `hf_dataset_repo`: target dataset repo slug
- `hf_push`: toggle upload
- `hf_create_pr`: upload as PR flow
- `hf_commit_message`: commit text

## Why this matters

The same note geometry used for runtime routing can become training-ready artifacts without separate export scripts.

## JSONL shape

Each row includes:

- `note_id`
- `bundle_id`
- `tongue`
- `authority`
- `intent_vector`
- `metric_tags`
- `metrics`
- `position`
- `phase_rad`

## References

- `workflows/n8n/scbe_n8n_bridge.py`
- `scripts/publish/post_all.py`
