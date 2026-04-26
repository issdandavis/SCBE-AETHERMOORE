# Training Dataset Inventory - 2026-04-25

This is the current working map for consolidating SCBE training data across local files, local notebooks, Kaggle kernels, Hugging Face datasets, and cloud-synced training surfaces.

## Current Counts

- Local dataset/config/notebook files: 357
- Local JSONL files: 153
- Known local JSONL records: 10,737
- Local repo notebooks: 22
- Kaggle kernels under the account: 43
- Hugging Face datasets under `issdandavis`: 35
- Cloud-synced SCBE/training surfaces sampled: 300

Generated artifacts:

- `artifacts/training_inventory/latest/inventory.json`
- `artifacts/training_inventory/latest/regularized_index.jsonl`
- `artifacts/training_inventory/latest/merge_plan.json`
- `artifacts/training_inventory/latest/report.md`
- `artifacts/training_regularized/latest/coding_model/coding_model_train.regularized.jsonl`
- `artifacts/training_regularized/latest/coding_model/coding_model_eval.regularized.jsonl`
- `artifacts/training_regularized/latest/aligned_foundations/aligned_foundations_train.regularized.jsonl`
- `artifacts/training_regularized/latest/aligned_foundations/aligned_foundations_eval.regularized.jsonl`

Repeatable command:

```powershell
python scripts/training_dataset_inventory.py --include-kaggle --include-hf --include-cloud --max-cloud-files 300
python scripts/regularize_training_bucket.py --purpose coding_model
python scripts/regularize_training_bucket.py --purpose aligned_foundations
```

## Purpose Buckets

- `aligned_foundations`: 19 files, 7,271 known records.
- `coding_model`: 45 files, 2,867 known records.
- `commerce_product`: 15 files, 452 known records.
- `governance_security`: 19 files, 59 known records.
- `operator_agent_bus`: 31 files, 88 known records.
- `research_bridge`: 17 files, 0 known records currently available locally.
- `story_lore`: 62 files, 0 known records currently available locally.
- `uncategorized`: 149 files, 206 known records.

## Regularization Status

- `ready_messages`: 30 files are immediately trainable in message format.
- `needs_schema_adapter`: 3 files need adapters before training.
- `lfs_pointer_needs_pull`: 116 files are Git LFS pointers and need `git lfs pull` or remote recovery before they count as usable local data.
- `manifest_or_metadata`: 168 files are manifests, configs, audits, or metadata.
- `notebook_surface`: 22 local notebooks need consolidation by purpose, not direct merge into SFT.
- `tabular_needs_adapter`: 2 CSV files need a tabular adapter.
- `inspect`: 12 raw text transcript files need conversion.
- `quarantine_tiny`: 4 tiny files should not enter training without inspection.

## Merge Rule

Do not flat-merge all corpora. Keep purpose buckets separate, dedupe inside each bucket, and promote only through that bucket's eval gate.

The priority model set is `coding_model`. It should pull from code primaries, binary/token transport, GeoSeal command recall, command harmony, atomic workflow repair, EML operator records, and full coding-system records. Lore, story, and product data stay out of the coder unless they are explicit code-primary paired records.

The tracked policy file is:

```text
config/model_training/scbe_dataset_regularization_v1.json
```

## Regularized Outputs Built Today

- `coding_model`: 18 ready source files produced 1,775 train records and 34 eval records after removing 1,058 exact duplicates.
- `aligned_foundations`: 9 ready source files produced 1,143 train records and 57 eval records after removing 6,071 exact duplicates.
- `governance_security`: 1 ready source file produced 59 train records.
- `commerce_product`: 2 ready source files produced 339 train records.
- `operator_agent_bus`: 0 immediately ready files because the available workflow audit JSONL currently needs a schema adapter.

## Frontier Model Lessons Applied

DeepSeek-V3 reports a 671B-total / 37B-active MoE model trained on 14.8T diverse high-quality tokens, followed by SFT and RL. The useful lesson for us is not model size; it is staged high-quality data, stable training instrumentation, and no uncontrolled corpus mixing.

DeepSeek-R1 shows reasoning gains from reinforcement learning on verifiable math, coding, and STEM tasks. The useful lesson for us is to turn GeoSeal checks, coding benchmarks, tokenizer roundtrips, and Stage 6 gates into verifier-style rewards instead of relying only on static SFT.

Kimi K2 reports a 1T-total / 32B-active MoE model with post-training driven by agentic data synthesis and RL in real/synthetic environments. The useful lesson for us is that the agent bus, CLI, Colab/Kaggle runs, and coding workflow traces should generate executable task records with mechanical pass/fail checks.

Sources:

- DeepSeek-V3 Technical Report, arXiv:2412.19437.
- DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning, arXiv:2501.12948.
- Kimi k1.5: Scaling Reinforcement Learning with LLMs, arXiv:2501.12599.
- Kimi K2: Open Agentic Intelligence, arXiv:2507.20534.

## Next Merge Path

1. Pull or recover LFS-backed datasets before treating old local JSONL pointer files as usable data.
2. Build adapters for `needs_schema_adapter`, raw transcript text, and tabular datasets.
3. Generate bucket-level merged candidates under `training-data/regularized/<purpose>/`, but keep those generated outputs ignored unless intentionally published.
4. Run secret/anomaly audit on every publish candidate.
5. Train the coding model first with the `coding_model` bucket and the existing `coding-agent-qwen-full-coding-system-v8` profile.
6. Add verifier/RL-style task generation after SFT: byte-identical code roundtrip, executable Python output, CLI command correctness, Stage 6 fallback/re-advance compliance, and benchmark pass/fail.
