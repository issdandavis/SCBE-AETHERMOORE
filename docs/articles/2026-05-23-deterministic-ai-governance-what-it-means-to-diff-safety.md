---
title: "Deterministic AI Governance: What It Means to Diff Safety"
slug: deterministic-ai-governance-what-it-means-to-diff-safety
date: 2026-05-23
author: Issac Daniel Davis
tags: [determinism, ai-governance, auditability, ci-cd, scbe, testing]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# Deterministic AI Governance: What It Means to Diff Safety

Here's a question you can't answer with a model-based safety classifier: "Did anything change between version 1.4.2 and 1.4.3 that affects how borderline inputs are handled?"

With a neural classifier, the answer is always "maybe." Weights shift. Softmax outputs drift between runs. Batch normalization behaves differently in eval mode vs training mode. You retrain on new data and the threshold that was safe last week now catches different things. You can't diff the classifier. You can only run your test suite and hope the coverage is good.

SCBE's pipeline is deterministic. Same input, same score, every time. That means you can diff it.

---

## What diffability gives you

The obvious benefit is reproducibility. A governance receipt from six months ago has the same score if you run it again today against the same pipeline version. You can audit past decisions. You can replay historical inputs through a newer version and see exactly which changed.

The less obvious benefit is CI integration. Because the pipeline is deterministic, you can run it in CI as part of your test suite. Not just "does the pipeline start up" — but "does this specific input still score X, and does that input still score Y, and does the adversarial test set still produce F1 of at least 0.80?"

That's what we do. The test suite in `tests/harmonic/` includes fixed inputs with expected scores. If a code change shifts a score, the test fails. A red CI run on a governance commit is a governance regression.

---

## The three properties you need for this to work

**Determinism.** The same input must produce the same output. This rules out dropout during inference, random seeds without fixing them, and any source of runtime nondeterminism. The Poincaré embedding computation is pure linear algebra — no randomness. The harmonic wall formula is a closed-form expression — no sampling. Layer 5's hyperbolic distance formula:

```
d_H(u, v) = arcosh(1 + 2‖u-v‖² / ((1-‖u‖²)(1-‖v‖²)))
```

…is deterministic by definition.

**Auditability.** Every decision must produce a receipt that's independently verifiable. The receipt includes the input hash, the pipeline version, the score components (d_H and pd separately), the final score, and the tier decision. The receipt is signed with ML-DSA-65. Anyone with the public key can verify it independently.

**Stability.** Scores for a given input should change only when the pipeline deliberately changes. No silent drift. No "the score used to be 0.42, now it's 0.39, we're not sure why." When a pipeline update changes scores, the CI red run makes it visible.

---

## What this doesn't give you

Determinism comes with tradeoffs. The pipeline doesn't generalize the way a fine-tuned neural classifier does. Novel adversarial patterns that don't map to existing tongue-dimension drift might evade the geometry layer. The 74.2% detection rate reflects this — geometry catches geometry-based evasion; novel semantic attacks need the temporal coherence layers.

You also can't "update" the governance layer by retraining on new data. Updating it means changing the code, running the test suite, seeing what moved, deciding whether the movements are acceptable. It's a software release cycle, not a training run. That's slower to adapt. It's also slower to degrade silently.

---

## Running it yourself

```bash
# TypeScript
npm test  # all 14-layer pipeline tests

# Python
PYTHONPATH=. python -m pytest tests/harmonic/ -v

# Specific pipeline test with a fixed input
npx vitest run tests/harmonic/pipeline14.test.ts
```

The test files include fixed expected scores for specific inputs. If you fork the repo and change something in the pipeline, those tests tell you immediately what moved and by how much.

Governance should be software, not magic. When it's software, you can read it. You can test it. You can ship it with a changelog.

[issdandavis/SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) — MIT OR Apache-2.0.
