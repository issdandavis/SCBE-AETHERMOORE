# Multiview Benchmark And Ablation Plan

Status: execution scaffold  
Date: 2026-04-01  
Purpose: convert the first fixed-compute multiview win into a repeatable benchmark packet

## Objective

Take the measured `~14%` stack-lite loss reduction and test whether it is:
- robust across seeds
- attributable to specific layers
- useful on downstream tasks
- usable for progression and governance gating

## Experiment Matrix

### Core training conditions

Run at matched model family and matched nominal compute:

1. `baseline`
- `L3` only

2. `stack-lite-full`
- `L0 + L1 + L2 + L3`

3. `ablation-l0`
- `L0 + L3`

4. `ablation-l1`
- `L1 + L3`

5. `ablation-l2`
- `L2 + L3`

Optional:
6. `weighted-stack`
- `alpha_0 L0 + alpha_1 L1 + alpha_2 L2 + alpha_3 L3`

## Seed Plan

Minimum:
- `3` seeds per condition

Preferred:
- `5` seeds per condition

Report:
- mean
- standard deviation
- min/max
- delta vs baseline

## Evaluation Surfaces

### 1. Training efficiency

Required:
- final training loss
- validation loss
- loss delta vs baseline
- relative improvement percent

### 2. Route classification

Measure:
- accuracy
- macro F1

Goal:
- verify that lower loss corresponds to stronger routing, not only easier memorization

### 3. Governance posture

Measure:
- precision
- recall
- F1
- false positive rate
- false negative rate

Goal:
- check whether layer-consistent training improves refusal/quarantine quality

### 4. Tongue / orientation fidelity

Measure:
- tongue classification accuracy
- orientation/null prediction accuracy
- route/tongue disagreement rate

Goal:
- confirm that `L1/L2` supervision is actually learned

### 5. Domain drift

Measure:
- drift rate on held-out prompts
- presence of architecture/security leakage on lore tasks
- wrong-register responses

Goal:
- determine whether the stack reduces domain confusion

### 6. Transfer / generalization

Measure on:
- unseen holdout split
- shifted-domain split

Goal:
- test whether the gain survives distribution shift

## Representation Diagnostics

If hidden-state access is available, compute:
- cluster compactness by route/tongue label
- linear separability of route and governance labels
- drift between baseline and stack-lite hidden states

Minimal proxy if hidden-state extraction is too expensive:
- nearest-neighbor retrieval purity on evaluation prompts

## Progression-Gating Hook

Use the benchmark to move progression from `L3-only` to weighted layer consistency.

Candidate progression score:

```text
P = w0 * perf(L0) + w1 * perf(L1) + w2 * perf(L2) + w3 * perf(L3)
```

Minimal gating rule:
- promote only if `P` improves and no critical layer regresses below floor

Candidate floors:
- `L1` route/tongue consistency above baseline
- `L2` governance F1 above baseline
- `L3` expression loss not worse than baseline

## Acceptance Criteria

Treat the multiview claim as stable only if:

1. mean loss win remains positive across seeds
2. at least one downstream task family improves materially
3. no severe governance regression appears
4. at least one ablation identifies where the gain is concentrated

Strong acceptance:
- loss win persists
- governance and route quality also improve
- drift rate falls

Weak acceptance:
- loss win persists
- downstream wins are mixed
- no serious regressions

Reject current hypothesis if:
- the seed variance erases the effect
- the gain is only on training loss and downstream tasks regress
- governance or drift worsens materially

## Execution Notes

Use the existing Kaggle comparison lane as the first harness:
- [train_polly_kaggle_comparison.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/train_polly_kaggle_comparison.py)

The current script compares `baseline` vs `stack_lite` only. Extend it to:
- accept condition list
- accept seed list
- persist per-run metrics
- emit aggregate tables

## Deliverables

After the next run, produce:
- per-run JSON
- aggregate summary table
- ablation chart
- progression-gating recommendation
- one paragraph claim update with exact wording

