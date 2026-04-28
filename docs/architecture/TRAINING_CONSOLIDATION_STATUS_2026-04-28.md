# Training Consolidation Status - 2026-04-28

## Scope

Started consolidation across local repo data, Hugging Face-targeted datasets, Colab notebooks, Kaggle run artifacts, git-tracked training corpora, and Drive-synced mirror storage.

## Completed

- Refreshed aligned foundations data:
  - `training-data/sft/aligned_foundations_train.sft.jsonl`
  - `training-data/sft/aligned_foundations_holdout.sft.jsonl`
  - `training-data/sft/aligned_foundations_manifest.json`
- Refreshed chemistry primary data:
  - `training-data/sft/chemistry_primary_train.sft.jsonl`
  - `training-data/sft/chemistry_primary_holdout.sft.jsonl`
  - `training-data/sft/chemistry_primary_manifest.json`
- Ran all-surface consolidation:
  - `python scripts/system/consolidate_ai_training.py --include-kaggle --include-hf --include-cloud`
- Built platform-split run ledger:
  - `artifacts/training_run_ledger/latest/ledger.md`
  - `artifacts/training_run_ledger/latest/ledger.json`
- Built training surface sync plan:
  - `artifacts/ai_training_consolidation/latest/TRAINING_SURFACE_SYNC_PLAN.md`
  - `artifacts/ai_training_consolidation/latest/training_surface_sync_plan.json`
- Ran training run review:
  - `artifacts/ai_training_consolidation/latest/RUN_REVIEW.md`
  - `artifacts/ai_training_consolidation/latest/run_review.json`
- Started routeable bucket-index consolidation:
  - `python scripts/system/build_training_bucket_index.py`
  - `artifacts/training_buckets/latest/TRAINING_BUCKET_INDEX.md`
  - `artifacts/training_buckets/latest/training_bucket_index.json`
  - 8 useful buckets
  - 260 bucketed files
  - 30 unassigned SFT files left for classification instead of being silently mixed
- Mirrored the constrained consolidation set to Drive:
  - `C:\Users\issda\Drive\SCBE_Training_Consolidation_20260428`
  - 264 files
  - 17,758,216 bytes

## Current Snapshot

Specialist buckets are ready for training:

| Purpose | Specialist | Train | Eval | Status |
| --- | --- | ---: | ---: | --- |
| coding_model | coding_primary_specialist | 2919 | 210 | ready_for_training |
| aligned_foundations | aligned_foundations_specialist | 1359 | 57 | ready_for_training |
| operator_agent_bus | operator_agent_bus_specialist | 48 | 3 | ready_for_training |
| governance_security | governance_security_specialist | 59 | 101 | ready_for_training |
| research_bridge | source_grounded_research_specialist | 84 | 19 | ready_for_training |

Routeable bucket index:

| Bucket | Files | Known JSONL Records | Gate |
| --- | ---: | ---: | --- |
| coding_transport | 42 | 4711 | coding smoke, slot preservation, deterministic round trip |
| aligned_foundations_chemistry | 16 | 2277 | cross-lane concept preservation and packet compliance |
| agent_ops_harness | 28 | 37 | exact command recall and fail-closed route behavior |
| governance_safety | 30 | 175 | invalid-input regression and auditable decision record |
| interop_social_civic | 9 | 0 | dual-frame payload identity, formation route, and social appeal path |
| source_grounded_research | 7 | 138 | source identity, falsifiable claim, and citation verification |
| story_manhwa_social | 91 | 0 | canon/style eval, no coding merge unless explicitly paired |
| commerce_product_sidecar | 37 | 6 | secret sweep, live/test separation, and fulfillment smoke |

Ledger platform counts:

- Kaggle: 14
- Hugging Face: 5
- Colab: 23
- Local: 40
- Dataset: 79

Run review:

- reviewed runs: 108
- promote candidates: 4
- needs eval gate: 1
- sidecar signal not in merge: 1

## Hugging Face Push State

The constrained HF push set contains 264 files and is recorded at:

- `artifacts/cloud-sync/training_consolidation_hf_manifest.json`

The first push attempt reached Hugging Face's repository commit-rate limit because the uploader committed one file at a time. The uploader has been patched to batch selected files into one commit through `HfApi.create_commit`.

Retry after the Hugging Face rate window clears:

```powershell
python scripts/system/cloud_storage_sync.py --target hf --repo issdandavis/scbe-aethermoore-training-data --repo-type dataset --include-only --include-glob "training-data/**/*.jsonl" --include-glob "training-data/**/*.json" --include-glob "artifacts/ai_training_consolidation/latest/**/*.json" --include-glob "artifacts/ai_training_consolidation/latest/**/*.md" --include-glob "artifacts/training_run_ledger/latest/**/*.json" --include-glob "artifacts/training_run_ledger/latest/**/*.md" --manifest-out artifacts/cloud-sync/training_consolidation_hf_manifest.json --push --max-files 500
```

## Blockers / Gaps

- HF upload is temporarily rate-limited; retry with the patched batch uploader.
- `aligned-foundations-qwen-primary` now routes datasets to `issdandavis/scbe-aligned-foundations-sft`.
- `chemistry-qwen-primary` now routes datasets to `issdandavis/scbe-chemistry-primary-sft`.
- `ollama-agentic-handler` and `hf-agentic-handler` profiles are missing both `hub.dataset_repo` and several older `training-data/code_*.jsonl` files.
- Colab notebooks are cataloged and available, but no live Colab session URL was attached in this run.

## Next Safe Actions

1. Retry the patched HF batch upload after the rate limit clears.
2. Run profile preflight for ready HF jobs before dispatch.
3. Run frozen eval gates for the seven priority Kaggle/HF outputs listed in `artifacts/training_run_ledger/latest/ledger.md`.
4. Decide whether the two legacy agentic-handler profiles should be repaired or archived.
5. Classify the 30 unassigned SFT files from `artifacts/training_buckets/latest/training_bucket_index.json`.
6. Add trainable SFT records for `interop_social_civic`; the bucket is structurally useful now but currently doc/code/eval heavy, not record heavy.
