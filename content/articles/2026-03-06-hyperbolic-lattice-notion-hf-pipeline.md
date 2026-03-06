# Hyperbolic Lattice Pipeline: Notion Notes to Hugging Face Dataset

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-06

## Overview

SCBE now supports a direct note pipeline: Notion pages can be pulled into the Lattice25D workflow, normalized into governance-ready records, and exported to JSONL for Hugging Face datasets.

## Flow

1. Search Notion pages with bounded pagination.
2. Convert title + block content into canonical note records.
3. Embed records into HyperbolicLattice25D.
4. Export rows with intent vectors, metric tags, and position metadata.
5. Optionally push to Hugging Face dataset repo.

## Why this is useful

- Research memory becomes machine-trainable without manual copy steps.
- Runtime retrieval and training data share one schema surface.
- Governance labels (authority, tongue, intent) stay attached from source to export.

## Implementation pointers

- `workflows/n8n/scbe_n8n_bridge.py`
- `/v1/workflow/lattice25d`
- `hf upload <repo> <file> --repo-type dataset`
