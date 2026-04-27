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

8. **Chris Deotte stacking maps to route-first adapter selection.** Deotte's 2025 RAPIDS/cuML writeup describes exploring many diverse Level 1 models, then using validation predictions as Level 2 stack features. For SCBE we should not blindly merge LoRAs; the equivalent is per-holdout routing: each adapter earns only the frozen-eval slices where it beats BASE without causing broad regressions.

9. **Predict the target several ways.** Deotte's stacking example trains models on target, ratio, residual, missing-feature, and pseudo-label views. For SCBE that means teaching the same coding operation through English, Python, TypeScript, binary, hex, and tongue-token forms, then evaluating whether each view improves a different holdout slice.

10. **Use constrained outputs for scored tasks.** The Amazon KDD Cup 2024 winning LLM solution used LoRA ensembles plus output constraints for task-relevant tokens. Our multiple-choice / approval-metric lanes should use constrained decoding or exact-choice validators during eval, not free-form grading alone.

## Repo Changes From This Note

- `scripts/kaggle_auto/kernel_template.py` now writes `TRAINING_HISTORY.json`, includes best checkpoint metadata in `DONE.json`, and arms eval-loss early stopping when an eval split exists.
- `scripts/eval/score_kaggle_round_patterns.py` scores Kaggle round configs for validation, anchor replay, bounded scope, LoRA overfit controls, remote lineage, T4-safe sizing, and specialist-lane discipline.
- `scripts/eval/analyze_training_curve.py` parses run logs for loss/token-accuracy trends and overfit-watch flags.
- `scripts/eval/plan_adapter_stack.py` builds a Deotte-style route/stack plan from frozen-eval reports by selecting adapters per holdout slice instead of merge-first.

## Sources

- NVIDIA Technical Blog, "Winning a Kaggle Competition with Generative AI-Assisted Coding" (2026-04-23): LLM agents, GPU acceleration, many measured experiments, baseline-to-feature-to-ensemble workflow.
- NVIDIA Technical Blog, Chris Deotte, "Grandmaster Pro Tip: Winning First Place in a Kaggle Competition with Stacking Using cuML" (2025-05-22): many diverse Level 1 models, Level 2 stackers, Level 3 weighted average, and fast GPU experimentation.
- NVIDIA Technical Blog, Chris Deotte and Carol McDonald, "Leveraging Machine Learning to Detect Fraud: Tips to Developing a Winning Kaggle Solution" (2021-01-26): feature engineering, validation, GPU experimentation loop, and XGBoost/CatBoost/LGBM ensemble.
- arXiv:2408.04658, "Winning Amazon KDD Cup'24" by Chris Deotte et al.: Qwen fine-tuning, synthetic data augmentation, wise-ft for distribution shift, multiple LoRA adapters, and constrained output tokens.
- Kaggle Winning Solutions Methods dataset: historical winning-solution method inventory.
- Kaggle notebook best-practice guides: reproducible notebook structure and validation discipline.
- Hugging Face / QLoRA Kaggle fine-tuning references: arrange data for train/validation/test, use QLoRA/PEFT for constrained GPUs.
