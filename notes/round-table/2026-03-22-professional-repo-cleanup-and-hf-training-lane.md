# 2026-03-22 Professional Repo Cleanup And HF Training Lane

## GitHub Snapshot

- Recent merged PRs are dominated by dependency churn, with key product merges at `#551`, `#552`, `#549`, and `#548`.
- The latest closed issues surfaced by GitHub API were:
  - `#521` Daily Review Failure - 2026-03-16
  - `#520` Workflow Audit: 23 high-risk CI masking issue(s) found
  - `#517` fix(security): Resolve all 29 CodeQL security alerts

## Professional Repo Surface

Keep active in the monorepo:
- `src`
- `tests`
- `docs`
- `scripts`
- `content`
- `notes`
- `workflows`

Curate before promotion:
- `training-data` -> Hugging Face dataset lane
- `notebooks` -> GitHub source + Colab runtime lane
- `kindle-app` -> manual review; large but still product-facing

Export/archive out of the active engineering surface:
- `artifacts` -> cloud/archive only
- `training` -> cloud/archive plus generated-run evidence
- `.n8n_local_iso` -> local runtime only
- `external` -> archive/vendor lane, not active source of truth
- `SCBE-AETHERMOORE-v3.0.0` -> archive snapshot, not live code

## Current Size Pressure

Top roots from `repo_ordering.py`:
- `artifacts`: `1364.92 MB`
- `kindle-app`: `389.98 MB`
- `training-data`: `248.11 MB`
- `external`: `196.53 MB`
- `training`: `74.94 MB`
- `.n8n_local_iso`: `53.53 MB`
- `src`: `29.92 MB`
- `tests`: `19.67 MB`
- `docs`: `12.29 MB`
- `scripts`: `7.44 MB`

Main dirty hotspots:
- `kindle-app`
- `artifacts`
- `SCBE-AETHERMOORE-v3.0.0`
- `training-data`
- `tests`
- `notes`
- `src`

## HF Training Lane

New governed ingestion builder:
- `scripts/build_training_ingestion_pool.py`

Timed workflow:
- `.github/workflows/programmatic-hf-training.yml`

Current dry-run outcome:
- `4,970` refreshed codebase SFT rows from `training-data/sft_codebase.jsonl`
- `7,743` docs/notes/notebook-derived ingestion-pool rows in `training/sft_records/sft_ingestion_pool.jsonl`
- `13,211` clean ledgered rows in `training/ledgered/sft_ledgered_clean.jsonl`
- audit status: `ALLOW`
- split counts:
  - train: `11,889`
  - validation: `660`
  - test: `662`

## Immediate Cleanup Rule

Treat the repo as:
- GitHub monorepo for canonical source and curated notes/docs
- Hugging Face for promoted datasets and model outputs
- Cloud/archive for artifacts, training runs, vendored externals, and snapshot trees

Do not let generated/runtime lanes compete with the live code surface.
