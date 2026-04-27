# Kaggle Winning Patterns For SCBE Training

**Status:** operational research note  
**Date:** 2026-04-26  
**Scope:** Kaggle/Hugging Face/Colab LoRA and QLoRA training lanes

## Useful Patterns

1. **Experiment ledger first.** Winning Kaggle work treats every run as a measured experiment: config, data, validation score, output path, and next decision. For SCBE this means every adapter run needs `DONE.json`, `STATUS.json`, `TRAINING_HISTORY.json`, frozen eval output, and a registry row before promotion.

2. **Trust validation over training loss.** Kaggle winners usually tune against a validation/CV signal they trust, not the public leaderboard alone. For SCBE this maps to frozen eval by bucket, executable coding tests, and OOD regression checks.

3. **Small bounded experiments beat giant unclear runs.** The winning loop is baseline, change one thing, measure, repeat. Our equivalent is narrow LoRA lanes with capped records/steps, then router/merge only after measurable improvement.

4. **Feature engineering maps to representation engineering.** In tabular Kaggle, the winner often builds better features. In our coding model, the "features" are binary/hex grounding, bijective code transport, DSL primitives, TypeScript executable receipts, and operator evidence records.

5. **Ensembling maps to routing.** Kaggle solutions often blend diverse models. For LoRA coding agents, routing specialist adapters is safer than merging them early. Merge only after drift and frozen-eval gates pass.

6. **Replay anchors prevent specialist collapse.** The failed `bijective-tongue-coder-v1` run showed the danger: a narrow lane can win in-distribution and lose OOD. Every specialist retrain should include anchor/replay records from governance, aligned foundations, command lattice, and Stage 6 repair.

7. **Checkpoint on validation cadence.** A run can die or overfit after the best point. Kaggle kernels should save at eval cadence, keep trainer history, and expose the best checkpoint/metric in `DONE.json`.

## Repo Changes From This Note

- `scripts/kaggle_auto/kernel_template.py` now writes `TRAINING_HISTORY.json` and includes best checkpoint metadata in `DONE.json`.
- `scripts/eval/score_kaggle_round_patterns.py` scores Kaggle round configs for validation, anchor replay, bounded scope, LoRA overfit controls, remote lineage, T4-safe sizing, and specialist-lane discipline.
- `scripts/eval/analyze_training_curve.py` parses run logs for loss/token-accuracy trends and overfit-watch flags.

## Sources

- NVIDIA Technical Blog, "Winning a Kaggle Competition with Generative AI-Assisted Coding" (2026-04-23): LLM agents, GPU acceleration, many measured experiments, baseline-to-feature-to-ensemble workflow.
- Kaggle Winning Solutions Methods dataset: historical winning-solution method inventory.
- Kaggle notebook best-practice guides: reproducible notebook structure and validation discipline.
- Hugging Face / QLoRA Kaggle fine-tuning references: arrange data for train/validation/test, use QLoRA/PEFT for constrained GPUs.
