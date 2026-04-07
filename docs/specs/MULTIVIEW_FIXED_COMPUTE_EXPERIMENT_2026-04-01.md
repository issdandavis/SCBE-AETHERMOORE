# Multiview Fixed-Compute Experiment

Status: measured result  
Date: 2026-04-01  
Scope: baseline `L3-only` vs `stack-lite L0+L1+L2+L3` under fixed model family and fixed training budget

## Claim

Multi-view supervision across substrate, coordination, and orientation layers reduced training loss by about `14%` at fixed compute compared to expression-only training.

This is the precise claim that is currently supported. It is narrower and more defensible than "multi-layer is better."

## Setup

Controlled comparison:
- same model family
- same optimizer class
- same nominal compute budget
- same training lane
- only the supervision structure changed

Compared conditions:
- `baseline`: `L3` expression-only training
- `stack-lite`: `L0 + L1 + L2 + L3` multi-view supervision

Conceptually:

```text
L_baseline = L_L3
L_stack = alpha_0 L_L0 + alpha_1 L_L1 + alpha_2 L_L2 + alpha_3 L_L3
```

The run should be interpreted as a multi-view supervision result, not a scaling-law result.

## Measured Result

Observed losses:
- baseline loss: `2.2226`
- stack-lite loss: `1.9121`
- absolute delta: `-0.3105`
- relative improvement: `0.3105 / 2.2226 = 0.1397`

Rounded result:
- `13.97%` loss reduction

## Interpretation

The observed gain is structurally meaningful because the experiment did **not** change:
- parameter count
- optimizer family
- wall-clock budget target
- the core model lane

It changed:
- the structure of supervision

That means the gain is best interpreted as:
- better gradient quality per update
- shared representation regularization
- reduced reliance on surface-token memorization
- better internal factorization across layers

## Why This Matters

The `stack-lite` condition forces the model to jointly account for:
- `L0`: substrate
- `L1`: coordination
- `L2`: orientation / intent coherence
- `L3`: expression

That changes the training burden from:

```text
memorize surface sequences
```

to:

```text
learn an internal state that explains multiple projections of the same sample
```

This aligns with:
- multi-task learning
- representation learning through shared constraints
- information bottleneck style pressure toward more meaningful latent structure

## What This Does Not Yet Prove

This result does **not** yet prove:
- stronger cross-domain generalization
- better inference-time governance behavior
- lower drift on unseen distributions
- optimal layer weighting
- robustness across seeds

It proves something narrower:

```text
At fixed compute, multiview supervision improved training efficiency relative to expression-only supervision.
```

## Progression Consequence

The result supports moving progression and governance away from `L3-only` scoring.

Old view:

```text
Progression ∝ performance(L3)
```

Better view:

```text
Progression ∝ sum_k w_k * performance(L_k),  for k in {0,1,2,3}
```

Implication:
- good `L3` with weak `L1/L2` is not enough
- promotion can require layer-consistent advancement
- governance can reject high-surface-quality, low-structure outputs

## Immediate Follow-On Work

Use this result as the anchor for the next experiment packet:

1. Robustness
- rerun with `3-5` seeds
- report mean, std, and confidence interval

2. Ablation
- `L0 + L3`
- `L1 + L3`
- `L2 + L3`
- full `L0 + L1 + L2 + L3`

3. Generalization
- holdout distribution
- shifted domain
- route/governance/tongue/drift tasks

4. Weight tuning
- test explicit `alpha_0..alpha_3` schedules
- check whether one layer dominates or whether balance matters

5. Representation diagnostics
- compare latent clustering or separability between baseline and stack-lite
- track whether stack-lite reduces drift and increases route separation

## Reporting Line

Use this wording in notes, talks, or papers:

> Multi-view supervision across substrate, coordination, and orientation layers reduced training loss by ~14% at fixed compute compared to expression-only training.

Avoid looser variants like:
- "multi-layer is better"
- "the stack proves deeper intelligence"
- "binary-first solves alignment"

## Related Files

- [BINARY_FIRST_TRAINING_STACK.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/BINARY_FIRST_TRAINING_STACK.md)
- [2026-04-01-conversationality-training-plan.md](C:/Users/issda/SCBE-AETHERMOORE/notes/theory/2026-04-01-conversationality-training-plan.md)
- [train_polly_kaggle_comparison.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/train_polly_kaggle_comparison.py)

