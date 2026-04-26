# Coding Model Training System Report - 2026-04-25

## Current Live State

- Hugging Face repair run: `coding-agent-qwen-stage6-repair-v7`
- Hugging Face job: `69ec70b9d70108f37acde12d`
- Hugging Face adapter target: `issdandavis/scbe-coding-agent-qwen-stage6-repair-v7`
- Hugging Face status at last check: `RUNNING`, step `155/360`
- Hugging Face loss trace: `3.945 -> 3.209 -> 2.319 -> 1.628 -> 1.013 -> 0.8778 -> 0.7056 -> 0.6728 -> 0.5319 -> 0.4628 -> 0.509 -> 0.4887 -> 0.34 -> 0.3083 -> 0.3423`
- Kaggle repair run: `issacizrealdavis/polly-auto-geoseal-stage6-repair-v7`
- Kaggle status at last check: `RUNNING`
- Kaggle dataset: `issacizrealdavis/scbe-coding-agent-stage6-repair-v7`
- Kaggle adapter target: `issdandavis/scbe-coding-agent-qwen-stage6-repair-v7-kaggle`
- Prepared next lane: `coding-agent-qwen-full-coding-system-v8`
- New v8 dataset: `coding_system_full_v1`, with `48` train rows and `8` holdout rows
- New v8 adapter target: `issdandavis/scbe-coding-agent-qwen-full-coding-system-v8`
- Current v8 Hugging Face job: `69ec82d9d2c8bd8662bcd602`

The first Kaggle attempt failed during data load because the kernel still pointed at the older generic Polly dataset. Version 2 is running with the dedicated Stage 6 repair dataset attached.

An earlier v8 job, `69ec7bc4d70108f37acde319`, was cancelled after the `test_assert` samples were made self-contained for executable benchmark checks. The current v8 job above uses the corrected dataset.

## Training Assets

Current local `training-data/sft` inventory:

- Files: `46`
- Rows: `9,982`
- Approximate text tokens by chars/4: `2,348,471`
- Dominant datasets:
- `drill_langues_full_all.sft.jsonl`: `2,630` rows, about `2.07M` chars
- `drill_langues_full_train.sft.jsonl`: `2,373` rows, about `1.87M` chars
- `bijective_codeflow_v1_all.sft.jsonl`: `1,040` rows, about `1.31M` chars
- `chemistry_primary_train.sft.jsonl`: `1,551` rows, about `1.22M` chars
- `bijective_codeflow_v1_train.sft.jsonl`: `936` rows, about `1.17M` chars
- `binary_interpretation_matrix_v1.sft.jsonl`: `326` rows, about `453K` chars
- `atomic_workflow_stage6_train.sft.jsonl`: `76` rows, about `286K` chars
- `atomic_workflow_stage6_repair_train.sft.jsonl`: `36` rows, about `45K` chars
- `coding_system_full_v1_train.sft.jsonl`: `48` rows, about `359K` chars

The new `coding_system_full_v1` lane is deliberately small and dense. Each record preserves separate code-primary, music-theory, atomic-tokenizer, binary/hex transport, lane-contract, and workflow-composition fields instead of flattening them into generic prose. It is a v8 training lane, not a mutation of the running v7 repair job.

## Industry-Style Benchmark Gate

Local benchmark harness:

- `scripts/benchmark/coding_system_industry_benchmark.py`
- Latest artifact: `artifacts/benchmarks/coding_system_full_v1/coding-system-industry-benchmark-20260425T090217Z.json`
- Decision: `PASS`
- Records checked: `56`
- Single-primary records: `48`
- Cross-primary roundabout records: `8`
- HumanEval/MBPP-style executable Python checks: `8/8`
- Full lane pass: `true`

This is a dataset/system readiness gate. It validates executable Python behavior, byte/hex/hash integrity, music-mode coverage, all six code primaries, atomic-tokenizer row presence, boundary language, and roundabout lane coverage. It is not a public HumanEval, MBPP, or SWE-bench leaderboard result for the trained adapter.

The pool is real but still small. It is strong enough for adapter training and behavior steering. It is not yet large enough to justify claiming general code intelligence from training alone.

## Parameter Scale Guidance

| Target model size | Current data fit | Recommended use |
|---:|---|---|
| `0.5B` | Strong fit | Best current lane. Enough data for repeated adapter passes, repair loops, frozen eval gates, and merge experiments. |
| `1.5B` | Good fit | Reasonable next scale if 0.5B passes frozen eval. Use LoRA/QLoRA, not full fine-tune. |
| `3B` | Plausible | Good ceiling for current data if deduped and curriculum-weighted. Needs stricter holdout and eval. |
| `7B` | Marginal | Can train a LoRA adapter, but likely overfits current corpus unless more real code tasks are generated. Use only after dataset grows past roughly `10M-30M` useful tokens. |
| `14B+` | Not justified yet | Current data is too small. Adapter may memorize style but not generalize. |
| Full model from scratch | Not viable | Needs billions of tokens and much larger compute. Current system should fine-tune open base models. |

Practical answer: with today’s corpus, the defensible ceiling is `3B` for a coding model adapter. `7B` is an experiment, not a production claim. The immediate best path is `0.5B -> 1.5B -> 3B`, with the same frozen eval contract at each step.

## What The Loss Curve Says

The repair run loss curve is healthy in the narrow training sense:

- It dropped quickly from `3.945` to around `0.34`.
- The small bounce from `0.3083` to `0.3423` is not alarming by itself.
- The slope is flattening, which means the model is learning the training distribution.

But lower training loss is not the final goal. The previous Stage 6 adapter failed frozen smoke eval `0/5`, so promotion depends on held-out behavior, not loss. The frozen eval must be run after this adapter finishes.

## Main Weaknesses

1. The corpus has duplicate families: `_all`, `_train`, and related variants can overlap. This can lower loss while inflating confidence.
2. Several files are tiny placeholder records, around `130` chars each, and should not be mixed into serious training unless regenerated.
3. Stage 6 repair data is high value but small: `36` train rows and `10` holdout rows.
4. Training currently optimizes next-token loss, while the desired behavior is rule compliance: preserve byte/hex lane, separate semantic/material chemistry, predict budget overrun, fallback, re-advance.
5. The merge profile exists, but full merge should stay blocked until a repair adapter passes frozen eval.

## Loss-Curve Improvements

These improve real behavior, not just cosmetic loss:

1. Deduplicate before training.
   - Remove overlap between `_all`, `_train`, and holdout variants.
   - Hash normalized message text and report duplicates before upload.

2. Add curriculum weights.
   - Start with bijective codeflow and binary interpretation.
   - Then add command recall/harmony.
   - Then Stage 6 fallback/re-advance.
   - Do not let the small Stage 6 repair set get drowned by large general files.

3. Oversample hard repair rows, but cap them.
   - Stage 6 repair rows should appear more often than their raw count implies.
   - Cap oversampling to avoid memorizing the exact answer shape.

4. Add negative/contrastive examples.
   - Good: “hex lane separate from semantic lane.”
   - Bad: “literal atoms / real chemistry claim.”
   - Good: “hold, dampen, re-advance.”
   - Bad: “launch anyway.”

5. Use the full coding-system lane as structure, not volume.
   - It should teach the model to keep KO/Python, AV/TypeScript, RU/Rust, CA/C, UM/Julia, and DR/Haskell aligned through music harmony, atomic rows, and binary transport.
   - It should not replace real code-task growth; it gives the next training pass a stronger map for how to read the code corpora.

5. Use eval-driven early stop.
   - Do not run fixed steps blindly.
   - Stop when held-out Stage 6 marker score stops improving.

6. Reduce learning rate after first repair pass.
   - Current `8e-5` is acceptable for repair.
   - Next pass should test `4e-5` or `5e-5` with more examples and stronger eval.

7. Increase logging quality.
   - Log train loss, eval loss, marker recall, forbidden-marker violations, and must-pass task score.
   - Loss alone is too weak for this system.

8. Build RLVR-style reward records from frozen eval output.
   - Reward exact required marker coverage.
   - Penalize forbidden marker use.
   - Penalize lane conflation.
   - This matches the model behavior target better than plain SFT.

## Recommended Next Build Order

1. Let HF and Kaggle repair runs finish.
2. Run frozen Stage 6 smoke eval on both adapters.
3. Pick the better adapter by frozen eval score, not loss.
4. If pass rate is below `0.8`, generate Stage 6 repair v8 with:
   - `200-500` analog repair rows
   - dedupe report
   - balanced lane labels
   - hard negatives
5. If pass rate is at least `0.8`, update the merge profile to use the passing v7 adapter.
6. Merge adapters into `issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1`.
7. Run the same frozen eval on the merged model.
8. Only then consider scaling to `1.5B` or `3B`.

## Bottom Line

The system is now a real staged coding-model training pipeline:

- It has profile manifests.
- It has HF and Kaggle execution lanes.
- It has frozen eval gates.
- It has adapter merge tooling.
- It has a repair loop after failed eval.

The current corpus supports serious adapter training up to `3B`. To go beyond that, the highest-value improvement is not bigger models first. It is more verified coding tasks, dedupe, curriculum weighting, hard negatives, and eval-driven promotion.
