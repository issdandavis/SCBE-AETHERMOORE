---
schema: scbe_runnable_ebook_v1
book: ai-governance-fundamentals
chapter: 04
slug: sacred-tongues
title: Sacred Tongues — choosing which governance dimensions matter for your product
version: 0.1.0
who: Operators tuning a governance gate for a specific product, not a generic SaaS template
what: How the six Sacred Tongues (KO, AV, RU, CA, UM, DR) act as φ-weighted dimensional knobs you can switch on, off, or scale
when: After Chapter 3, when you have a working gate but the wrong things are being weighted
where: The Langues Metric, layer 3 of the SCBE pipeline — upstream of the harmonic wall
why: A governance score that weights every dimension equally is a score that pleases nobody — different products care about different drift modes
test_suite: tests/book/ai_governance_fundamentals/test_chapter_04_sacred_tongues.py
runnable_languages: [python]
estimated_read_minutes: 12
prereq_chapters: [01, 02, 03]
---

# Sacred Tongues

> **Who** Operators who already have a working gate but want to weight it for their product, not a generic template.
> **What** Six φ-weighted dimensions you can switch on, off, or scale per request — KO, AV, RU, CA, UM, DR — covering time, intent, policy, trust, risk, and entropy.
> **When** After Chapter 3, when the gate is shipping but the wrong drift mode is dominating its score.
> **Where** The Langues Metric, upstream of the harmonic wall in the SCBE pipeline.
> **Why** Equal-weight scoring penalizes harmless drift the same as adversarial drift. φ-weighting lets the operator choose which dimensions deserve exponential attention.

## The φ progression

The six tongues are weighted by powers of the golden ratio. The progression is not arbitrary — it makes the higher tongues exponentially more expensive to drift in than the lower ones, which mirrors the cost gradient operators actually want.

```python
from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
    TONGUES,
    TONGUE_WEIGHTS,
)

print("Tongue weights (phi^k progression):")
for tongue, weight in zip(TONGUES, TONGUE_WEIGHTS):
    print(f"  {tongue}: w = {weight:.4f}")
```

```output
Tongue weights (phi^k progression):
  KO: w = 1.0000
  AV: w = 1.6180
  RU: w = 2.6180
  CA: w = 4.2361
  UM: w = 6.8541
  DR: w = 11.0902
```

DR (the entropy tongue) costs **11x** as much as KO (the time tongue). That is the operator's choice baked into the math: chaotic, unpredictable behavior is far more expensive than slow, time-correlated drift.

## Aligned vs drifted: a single number

The Langues Metric collapses a 6-dimensional point into a single cost number. Operators read the cost; reviewers read the per-tongue breakdown.

```python
from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
    LanguesMetric,
    HyperspacePoint,
)

metric = LanguesMetric()

aligned = HyperspacePoint(
    time=0.0, intent=0.05, policy=0.5, trust=0.85, risk=0.15, entropy=0.25
)
drifted = HyperspacePoint(
    time=0.0, intent=0.7, policy=0.5, trust=0.3, risk=0.8, entropy=0.7
)

L_a = metric.compute(aligned)
L_d = metric.compute(drifted)

print(f"aligned cost L = {L_a:.4f}")
print(f"drifted cost L = {L_d:.4f}")
print(f"cost ratio drifted/aligned = {L_d / L_a:.2f}x")
```

```output
aligned cost L = 27.4331
drifted cost L = 44.2003
cost ratio drifted/aligned = 1.61x
```

A 1.6x cost ratio is what an operator sees on the dashboard. It is enough to flag attention but not enough to throttle a customer over a single request.

## Per-tongue projection — finding what actually drifted

When the cost spikes, the operator wants to know **which tongue is responsible**. Pass `active_tongues=[...]` to project the cost onto a single dimension:

```python
from src.symphonic_cipher.scbe_aethermoore.axiom_grouped.langues_metric import (
    LanguesMetric,
    HyperspacePoint,
    TONGUES,
)

metric = LanguesMetric()
drifted = HyperspacePoint(
    time=0.0, intent=0.7, policy=0.5, trust=0.3, risk=0.8, entropy=0.7
)

print("Drifted cost by single-tongue projection:")
for tongue in TONGUES:
    L_only = metric.compute(drifted, active_tongues=[tongue])
    print(f"  {tongue} only: L = {L_only:.4f}")
```

```output
Drifted cost by single-tongue projection:
  KO only: L = 1.0000
  AV only: L = 3.6956
  RU only: L = 2.8425
  CA only: L = 7.2691
  UM only: L = 12.2751
  DR only: L = 17.1179
```

DR (entropy) carries 39% of the total drifted cost — the request looks chaotic, not just biased. UM (risk) carries another 28%. Together they tell the reviewer: "this drift is unpredictability + risk-taking, not slow misalignment." That is a different category of incident than a high CA (trust) projection would be.

## What this proves

1. **Single-number scoring is recoverable to per-tongue causes.** The same metric serves dashboard summary and incident-room forensics.
2. **The φ progression is the operator's lever.** Want entropy to dominate? It already does. Want time to dominate? Override `TONGUE_WEIGHTS` for your subclass. The math respects whatever progression you pick.
3. **Tongue projection is cheap.** Each call is O(1) and uses the same metric instance. There is no separate "explain" pipeline to maintain.

## Wiring it into your decision record

Drop the per-tongue projection straight into the Chapter 3 decision record:

```text
record = DecisionRecord(
    request_id=request_id,
    tier=tier_for(h),
    h_score=h,
    centroid_distance=d,
    recent_unsafe_ratio=pd,
    reviewer_action=reviewer_action_for(tier),
    audit_note=f"top tongue: {dominant_tongue} ({L_dominant:.2f})",
)
```

A reviewer who reads `top tongue: DR (17.12)` knows immediately what kind of drift this was.

## Next chapter

Chapter 5 ties the four chapters together with a **complete worked example** — one request flowing through the harmonic wall, the four-tier ladder, the decision record, and the Sacred Tongues projection — and the corresponding test suite that proves the wiring stays correct.
