# UPG LLM Training Map

Status: draft v0.1  
Date: 2026-04-01  
Scope: concrete experiment matrix for applying the Universal Propagation Grammar to SCBE LLM training

---

## Purpose

The Universal Propagation Grammar becomes useful only when it constrains training design and evaluation. This document turns the LLM section of the grammar into a concrete experiment matrix that can run on the current SCBE Qwen lane.

This is not a new training stack. It is a disciplined framing layer over the existing small-model workflow:

- base family: `Qwen/Qwen2.5-0.5B-Instruct`
- first notebook lane: [finetune_qwen_governance.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/finetune_qwen_governance.ipynb)
- fallback notebook lane: [scbe_finetune_colab.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/scbe_finetune_colab.ipynb)

---

## UPG Mapping For LLMs

| UPG term | LLM training object | Typical measurement |
| --- | --- | --- |
| Carrier | token stream, latent manifold, parameter state | token count, activation statistics, checkpoint delta |
| Excitation | prompt, batch, optimizer step, reward signal | batch size, lr, schedule, reward type |
| Pattern | desired behavior or task structure | target label, answer format, chain shape |
| Propagation | forward pass, backpropagation, optimizer trajectory | train loss curve, eval loss curve |
| Distortion | bias, reward misspecification, overfit, domain mismatch | calibration drift, hallucination rate, eval regressions |
| Coupling | one view or stage changing another | transfer delta, DPO headroom, multi-view lift |
| Resonance | aligned gradients and mutually useful views | win rate, agreement, stable improvements across evals |
| Damping | weak signal, forgetting, retry fatigue, curriculum washout | diminishing gain per epoch or stage |
| Reconstruction | recovery of latent task from examples | generalization on held-out variants |
| Adaptation | fine-tuning, DPO, curriculum shift, self-play | post-feedback improvement on the same class of task |

---

## Existing Repo Anchors

- [UNIVERSAL_PROPAGATION_GRAMMAR.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/UNIVERSAL_PROPAGATION_GRAMMAR.md)
- [HF_TRAINING_CURRICULUM_MAP_2026-03-24.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/HF_TRAINING_CURRICULUM_MAP_2026-03-24.md)
- [2026-04-01-harmonic-training-complete-synthesis.md](C:/Users/issda/SCBE-AETHERMOORE/notes/theory/2026-04-01-harmonic-training-complete-synthesis.md)
- [fiber_optics_qwen_adapter_runbook.md](C:/Users/issda/SCBE-AETHERMOORE/training-data/fiber_optics/fiber_optics_qwen_adapter_runbook.md)

The grammar should integrate with those files, not compete with them.

---

## Core Hypothesis

For equal or matched token budgets, improvements should come primarily from structured carrier diversity and aligned propagation, not from raw corpus volume.

In repo terms:

1. Multi-view packets should outperform prose-only examples when both describe the same pattern.
2. A later-stage preference or governance signal should work better when the prior SFT stage created usable structure.
3. Structured rejection-feedback loops should outperform blind retries because they increase adaptation and reduce damping.

---

## Carrier Classes

The first useful abstraction is to treat each training example as a packet carried through one or more representations.

### Carrier A: prose-only

The default baseline.

- one natural-language prompt
- one natural-language answer
- no explicit structural side channels

### Carrier B: tagged multiview

The same pattern appears in multiple aligned sections.

- `L0` raw substrate or low-level shape
- `L1` transformed representation
- `L2` diagnosis / policy / intermediate decision
- `L3` final human explanation or output

### Carrier C: governed feedback

The model sees not only the target but also rejection structure.

- proposed output
- deterministic rejection reason
- corrected output

### Carrier D: staged curriculum packet

The same task family is represented across training stages.

- SFT pass teaches the pattern
- DPO or preference stage teaches ranking
- governed retry stage teaches adaptation under failure

---

## Distortion Classes

Each experiment should track which distortion class it is trying to reduce.

| Distortion class | Description | Primary symptom |
| --- | --- | --- |
| carrier collapse | too much information forced into prose-only packets | weak transfer, shallow explanation |
| spectral bias lock | model learns only easy low-frequency structure | fragile on long-chain or diagnostic tasks |
| reward misspecification | later-stage optimization pushes the wrong behavior | confident but wrong answers |
| view disagreement | different views do not describe the same latent pattern | noisy gains, unstable evals |
| curriculum washout | later training erases earlier useful structure | forgetting, low adaptation |
| retry damping | extra loop turns add little or no new information | many retries, small deltas |

---

## Experiment Matrix

### Matrix A: carrier comparison

Purpose:

- isolate the value of multi-view propagation over prose-only training

Arms:

1. `A0` prose-only baseline
2. `A1` tagged multiview with matched token budget

Shared controls:

- same base model
- same notebook lane
- same task families
- same train / validation / test split

Primary metrics:

- exact or rubric accuracy
- transfer accuracy on structurally similar held-out tasks
- explanation quality
- calibration or abstention quality

Success criterion:

- `A1` beats `A0` on transfer and explanation quality, not only in-domain memorization

### Matrix B: stage coupling

Purpose:

- test whether structured SFT improves later preference or governance learning

Arms:

1. `B0` prose-only SFT -> DPO
2. `B1` multiview SFT -> DPO

Primary metrics:

- preference win rate
- refusal / safety quality where applicable
- downstream robustness under prompt reformulation

Success criterion:

- `B1` shows higher DPO headroom and more stable downstream gains

### Matrix C: governed adaptation

Purpose:

- test whether structured rejection feedback creates useful adaptation

Arms:

1. `C0` generic denial text
2. `C1` structured denial with specific failure reasons and corrected exemplar

Primary metrics:

- retries to approval
- improvement between retry `n` and retry `n+1`
- final approval rate
- post-approval test pass rate

Success criterion:

- `C1` requires fewer retries and produces better final approvals

### Matrix D: curriculum progression

Purpose:

- test whether easy-to-hard propagation improves generalization

Arms:

1. `D0` shuffled curriculum
2. `D1` staged curriculum
3. `D2` staged curriculum with self-paced selection where feasible

Primary metrics:

- validation gain by stage
- forgetting on earlier stages
- final held-out performance

Success criterion:

- staged or self-paced routes improve held-out performance without raising regression on prior stages

---

## Recommended First Implementation

Start small. The first executable version should use one base model and one notebook lane.

### Lane

- notebook: [finetune_qwen_governance.ipynb](C:/Users/issda/SCBE-AETHERMOORE/notebooks/finetune_qwen_governance.ipynb)
- base model: `Qwen/Qwen2.5-0.5B-Instruct`
- method: 4-bit LoRA SFT

### Datasets

1. existing SCBE governance-style corpus
2. one structured multiview subset
3. one governed retry subset where available
4. one specialist second domain such as fiber optics

### First matrix to run

Run `Matrix A` first.

Why:

- it is the cleanest falsification of the grammar
- it does not require a new reward model
- it can be implemented with existing infrastructure

---

## Packet Formatting Rule

Every multiview record should preserve the same latent pattern across all views. That means the views are not decorative. They are aligned carriers for the same thing.

Recommended formatting:

```text
[category]
L0: raw substrate or trace
L1: transformed features
L2: diagnosis or intermediate decision
Question: final task request
```

The assistant output stays at `L3`.

If the views do not align, the packet should be rejected at dataset-build time.

---

## Evaluation Table

Each run should report at least the following:

| Metric | Why it matters |
| --- | --- |
| train loss | basic optimization health |
| validation loss | generalization check |
| held-out task accuracy | task performance |
| transfer accuracy | whether structure moved across related tasks |
| calibration / abstention score | whether confidence tracks reality |
| post-hoc explanation quality | whether reconstruction improved |
| token budget | keeps comparisons honest |

Optional but useful:

- gradient norm stability
- cross-view agreement score
- per-category delta

---

## Falsifiable Predictions

1. Tagged multiview packets should beat prose-only packets at matched token count.
2. The gain should be strongest on diagnostic or reconstruction-heavy tasks, not simple lookup tasks.
3. Structured SFT should increase the value of later DPO or governed-feedback stages.
4. Governed retry data should primarily improve adaptation, not just static instruction following.

If those predictions fail, the grammar is too abstract or the packet design is wrong.

---

## Failure Modes

This spec should be revised if:

1. multiview formatting adds cost without measurable gains
2. gains come only from more tokens rather than better structure
3. preference or governance stages do not benefit from structured earlier stages
4. the packet views cannot be kept semantically aligned during dataset construction

---

## Next Practical Moves

1. Build a small matched-token baseline pair: prose-only vs multiview.
2. Reuse the new fiber optics schema as the first non-governance multiview packet family.
3. Add governed retry triples once the loop metrics spec is in place.
4. Promote only the winning packet shapes into larger Colab or HF job runs.

The grammar becomes real only when one of these matrices produces a repeatable lift.
