---
title: "Why Our AI Safety System Scores 34.5% (And Why That's the Point)"
published: false
description: "We deliberately walled off our test data from training and let our system fail honestly. Here's what we learned about the gap between lab accuracy and real-world detection."
tags: ai, security, machinelearning, testing
canonical_url: https://aethermoorgames.com/research/military-eval-scale.html
---

## The Number Everyone Hides

Our AI governance classifier scores **95.8% accuracy** on its evaluation set. If we stopped there, we'd look great on paper.

But we didn't stop there. We built a separate benchmark with 20 attack categories -- attacks the model has NEVER seen during training -- and tested blind.

**Blind detection rate: 34.5%.**

That's the honest number. Here's why it matters more than the 95.8%.

## The Problem With AI Security Benchmarks

Most AI safety systems test on the same distribution they train on. Train on Kaggle adversarial prompts, test on Kaggle adversarial prompts, report 95%+ accuracy. Ship it.

Then a novel attack hits production and the system folds.

We enforced **strict data isolation**:

```
TRAINING POOL                    BLIND HOLDOUT
(model learns from these)        (model NEVER sees these)
─────────────────────            ────────────────────────
Kaggle MPDD (40K prompts)        SCBE 20-category attacks (400)
Local SFT records (4,846)        - direct_override
Benign doc corpus (500)          - tongue_manipulation
                                 - spin_drift
Hash-checked:                    - rag_injection
0 holdout texts leaked           - function_calling_abuse
into training.                   - ... (20 categories total)
```

Every holdout text was fingerprinted. We verified **zero contamination**. The 34.5% is mathematically clean.

## What the Gap Reveals

The 95.8% → 34.5% drop isn't a failure of our model. It's proof that:

1. **Standard adversarial datasets don't cover structural attacks.** Kaggle data trains you to catch "ignore previous instructions." It doesn't train you to catch spin drift, tongue manipulation, or perpendicular torsion.

2. **Single-model classifiers have distribution shift problems.** Train on one attack family, deploy against another, watch accuracy collapse. This is well-documented in ML literature but rarely admitted in product marketing.

3. **The attacks that matter most are the ones nobody's published yet.** Our 20-category benchmark includes 8 categories mapped to MITRE ATLAS and OWASP LLM Top 10 that don't exist in any public training dataset.

## What We Did About It

Instead of inflating the number, we built a **Hybrid Engine** -- three detection layers that cover each other's blind spots:

| Layer | What It Catches | Blind Detection |
|-------|----------------|-----------------|
| Trained Classifier | Known Kaggle-style attacks | 34.5% (69/200) |
| RuntimeGate (geometric) | Structural anomalies | 49% (98/200) |
| Trichromatic (IR/UV bands) | Hidden-band forgery | 6% (12/200, early) |
| **Hybrid (all three)** | **Combined** | **54.5% (109/200)** |

The hybrid beats every individual system. That proves orthogonal value -- they catch different attacks.

## The Benchmark Categories

All 20 mapped to real standards:

| Standard | What We Test |
|----------|-------------|
| MITRE ATLAS | 5 adversarial tactics |
| OWASP LLM Top 10 | 6 vulnerability categories |
| NIST AI RMF | 4 risk management functions |
| DoD Directive 3000.09 | Autonomous escalation |
| Anthropic RSP | ASL-2/ASL-3 evaluations |

## Per-Category Results (Honest)

| Category | Detection | Why |
|----------|-----------|-----|
| spin_drift | **100%** | Geometric check catches escalation pattern |
| boundary_exploit | **90%** | High cost triggers |
| direct_override | **40%** | Classifier helps but not enough |
| prompt_extraction | **10%** | Polite requests slip through |
| multilingual | **10%** | Training data gap (being addressed) |

## The Point

If your AI safety vendor shows you 99% accuracy, ask one question: **is the test set isolated from the training set?**

If they can't prove zero contamination, their number is meaningless.

We publish the 34.5% because it's real. We publish the gap because it tells us where to improve. We publish the benchmark because nobody else has one with 20 categories mapped to defense standards.

## Links

- **Benchmark data**: [Kaggle](https://kaggle.com/datasets/issacizrealdavis/scbe-governance-research-results)
- **Training pipeline**: [HuggingFace](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data)
- **20-category attack generator**: [GitHub](https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/benchmarks/scbe/attacks/generator.py)
- **Research page**: [Military Eval Scale](https://aethermoorgames.com/research/military-eval-scale.html)

---

*Built by Issac Daniel Davis. SCBE-AETHERMOORE is open source.*
