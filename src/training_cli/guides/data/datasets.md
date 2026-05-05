# Datasets

How SCBE prepares training data and what the canonical shapes are.

## Where datasets live

| Directory | Purpose |
|---|---|
| `training-data/` | SFT/DPO ready JSONL the dispatch scripts read. |
| `training-data/sft/` | SFT pairs. |
| `training-data/dpo/` | DPO preference triples. |
| `training-data/proofs/` | Tiny proof bundles (e.g. spine_overlay_proof_v1). |
| `training-data/curriculum/` | Lane-balanced curriculum schedules (golden-helix, etc.). |
| `training/intake/` | Raw upstream sources before normalization. |
| `training/runs/` | Per-run artifacts: configs, logs, eval verdicts. |

## Canonical builders (pick one)

| Builder | Output |
|---|---|
| `scripts/training_data/build_coding_approval_metrics_v3.py` | Coding approval SFT |
| `scripts/training_data/build_chemistry_adapter_sft.py` | Chemistry adapter SFT |
| `scripts/training_data/build_geoseal_industry_commands_sft.py` | GeoSeal industry commands SFT |
| `scripts/training_data/build_sacred_tongue_syntax_alignment_sft.py` | Sacred tongue syntax alignment |
| `scripts/training_data/build_agentic_preference_math_dpo.py` | Agentic preference math DPO |
| `scripts/training_data/build_geoshell_pair_agent_preference_dpo.py` | GeoShell pair-agent preference DPO |
| `scripts/training_data/build_golden_helix_curriculum.py` | Lane-balanced curriculum across all rows |
| `scripts/training_data/build_go_game_go_lang_strategy_sft.py` | Go (game + lang) cross-tongue strategy SFT |

## Quality bar

Before dispatching a run, datasets should clear:

1. **Schema valid** -- every row parses; every required field present.
2. **No leakage from holdout** -- use `scripts/dsl/audit_v5_holdout.py` for the v5 holdout, or write a similar dedup against the eval set.
3. **Lane balance** -- if you target one lane (coding/chemistry/governance/research/motion/tokenizer), use the golden-helix builder to interleave so the model doesn't catastrophically forget.
4. **Canonical vocabulary present** -- run a pre-check that the must-pass markers (e.g. `transmit_burst`, `hex`, `semantic`, `steady-state fallback` for stage6) actually appear with sufficient frequency in the chosen rows.

## Pushing to HuggingFace

Datasets used by HF Jobs need to be on the Hub OR the job script needs to upload them at start. SCBE's pattern is:

```
python scripts/system/push_dataset_to_hf.py \
  --src training-data/sft/my_data.jsonl \
  --repo issdandavis/my-dataset \
  --visibility private
```

Public datasets need a README/data card. Use `docs/dataset_cards/` as templates.
