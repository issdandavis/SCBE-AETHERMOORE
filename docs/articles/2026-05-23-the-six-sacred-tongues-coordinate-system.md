---
title: "The Six Sacred Tongues: How Fictional Languages Became a Semantic Coordinate System"
slug: the-six-sacred-tongues-coordinate-system
date: 2026-05-23
author: Issac Daniel Davis
tags: [six-sacred-tongues, tokenizer, semantic-embedding, ai-governance, scbe]
platforms: [dev.to, aethermoore.com/articles]
status: ready
---

# The Six Sacred Tongues: How Fictional Languages Became a Semantic Coordinate System

Let me start by correcting something I've seen described wrong on Hugging Face and in some summaries of this project: the six Sacred Tongues are not:

- KO = Foundation/Structure
- UM = Coordination/Consensus
- DR = Authority/Governance

Those descriptions are from a bad summary that got propagated. The correct roles — matching both the lore they came from and the actual implementation — are:

| Tongue | Code | Role | Weight |
|--------|------|------|--------|
| Kor'aelin | KO | Control/Intent | 1.000 |
| Avali | AV | Transport/Messaging | 1.618 |
| Runethic | RU | Policy/Binding | 2.618 |
| Cassisivadan | CA | Compute/Transforms | 4.236 |
| Umbroth | UM | Redaction/Privacy | 6.854 |
| Draumric | DR | Authentication/Integrity | 11.090 |

UM is about what's contained, redacted, kept private — not a general security bucket. DR is about record, proof, authentication — not schema. The distinction matters for how the geometry works.

---

## What these actually are

Each tongue is a dimension in a six-dimensional semantic coordinate space. Every token input to the SCBE pipeline gets projected into this space. The projection is not probabilistic — it's a lookup and weight computation based on a 16×16 token grid per tongue (256 tokens per tongue × 6 tongues = 1,536 total tokens in the tokenizer vocabulary).

The weights follow the golden ratio:

```
KO: φ^0 = 1.000
AV: φ^1 = 1.618
RU: φ^2 = 2.618
CA: φ^3 = 4.236
UM: φ^4 = 6.854
DR: φ^5 = 11.090
```

Why golden ratio spacing? Because φ gives you a consistent multiplicative gap between adjacent dimensions without collapsing them into each other. The ratio between any adjacent pair is always φ. This means governance-layer drift (toward high-weight DR) costs disproportionately more than transport-layer drift (toward low-weight AV). That's intentional — governance and authentication signals should be harder to fake.

---

## How the phases work

Each tongue also carries a phase angle — its position on the unit circle. The six tongues are evenly spaced:

```
KO: 0°    (0 radians)
AV: 60°   (π/3)
RU: 120°  (2π/3)
CA: 180°  (π)
UM: 240°  (4π/3)
DR: 300°  (5π/3)
```

The 21D PHDM embedding model maps inputs into a manifold `M = B_c^6 × T^6 × R^9` where:
- `B_c^6` is the six-dimensional hyperbolic Poincaré ball (one ball per tongue)
- `T^6` is the six-dimensional torus of phase angles
- `R^9` is the nine-dimensional governance telemetry space

When an input's phase deviates from the expected tongue phase, the `pd` term in the harmonic wall formula grows:

```
H(d, pd) = 1 / (1 + d_H + 2·pd)
```

Phase deviation feeds into the harmonic score at twice the weight of hyperbolic distance. So if you're semantically near the center but your phase alignment is wrong — if the pattern of your input looks like one tongue but signals like another — the harmonic score drops harder than pure distance would predict.

---

## Why Umbroth is "Redaction/Privacy" specifically

Umbroth's role comes from the lore: the shadow tongue, the containment tongue. In the Everweave game logs where these six traditions emerged, Umbroth magic was about what gets withheld. Secrets held under shadow. Information that doesn't propagate.

In the technical system, that maps directly to the governance function of redaction and privacy. When an input tries to extract hidden context — system prompts, injected instructions, context it shouldn't have access to — it tends to drift toward the UM semantic region while also generating phase deviation because the access pattern doesn't match the expected routing.

The weight is high (6.854) because privacy violations are expensive to tolerate. The geometry enforces that cost automatically.

---

## Why Draumric is "Authentication/Integrity" specifically

Draumric in the lore is the record tongue — the tradition concerned with proof, lineage, what has been witnessed and cannot be undone. Draumric magic leaves marks. It cares about the chain of custody.

In the technical system: authentication, integrity verification, audit trail. Draumric-tongue tokens are things like signature checks, session validation, receipt verification. DR has the highest weight (11.090) because successful authentication impersonation is the highest-value adversarial target. If you can fake the governance receipt, you can fake everything downstream.

The geometry reflects that: any input that generates Draumric-region signals without legitimate authentication context will produce hyperbolic distance and phase deviation that drive the harmonic score toward DENY.

---

## The thing these six dimensions are not

They're not ML-trained feature dimensions. They're not cluster centroids extracted from fine-tuning data. They're hand-specified dimensions whose token grids were built from the lore and then validated against adversarial inputs.

That design choice is deliberate. Learned dimensions drift when the model drifts. Hand-specified dimensions tied to geometric weights don't drift — they're constants. The tradeoff is that they require manual curation when new token patterns emerge. The benefit is that a change in the underlying model doesn't invalidate the governance geometry.

The full tokenizer source is in [src/tokenizer/](https://github.com/issdandavis/SCBE-AETHERMOORE/tree/main/src/tokenizer). The token grids, weight computation, and phase mappings are all in there.

---

*Related: [What the harmonic wall is actually measuring](2026-05-23-why-our-safety-system-scores-low.md)*
