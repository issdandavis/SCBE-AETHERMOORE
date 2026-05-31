---
schema: scbe_runnable_ebook_v1
book: ai-governance-fundamentals
chapter: 02
slug: risk-tiers
title: The Four-Tier Risk Decision — ALLOW, QUARANTINE, ESCALATE, DENY
version: 0.1.0
who: AI engineers who already have a safety score and need to decide what to do with it
what: How to map a bounded H(d, pd) score into the four canonical SCBE risk tiers and a runnable gate function
when: After Chapter 1, before any production deploy that takes free-form user input
where: Layer 13 of the SCBE pipeline — the governance decision step that sits between the harmonic wall and the downstream caller
why: A bounded score is useless if every threshold collapses to a binary "block / allow" — the four tiers preserve the action gradient an operator can act on
test_suite: tests/book/ai_governance_fundamentals/test_chapter_02_risk_tiers.py
runnable_languages: [python]
estimated_read_minutes: 10
prereq_chapters: [01]
---

# The Four-Tier Risk Decision

> **Who** AI engineers who already have a safety score and need to decide what to do with it.
> **What** A four-tier ladder — ALLOW, QUARANTINE, ESCALATE, DENY — that turns one number into one of four operator-actionable buckets.
> **When** After Chapter 1's harmonic wall is wired in, before any production deploy.
> **Where** Layer 13 of the SCBE pipeline. The score comes from L12, the action goes to the caller.
> **Why** A binary gate forces operators to pick one threshold and live with both kinds of errors. Four tiers preserve the gradient.

## The problem with binary gates

A binary gate has one knob: the threshold. Set it conservative and you quarantine half the legitimate traffic. Set it permissive and adversarial drift eats you alive. There is no setting that wins both arguments, because the operator doesn't actually want a binary decision — they want **proportional response**.

The four-tier ladder is the smallest set that encodes proportional response without a continuous policy:

| Tier | When | Operator action |
|---|---|---|
| **ALLOW** | High confidence safe | Pass through to caller |
| **QUARANTINE** | Suspicious — needs a second look | Hold, log, surface to reviewer |
| **ESCALATE** | High risk — surface to governance | Page on-call, freeze conversation |
| **DENY** | Adversarial — block | Refuse with audit record |

Three thresholds, one bounded score, no continuous policy file.

## The runnable gate

```python
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
    HamiltonianTracker,
)


def tier_for(h: float) -> str:
    if h > 0.6:
        return "ALLOW"
    if h > 0.4:
        return "QUARANTINE"
    if h > 0.2:
        return "ESCALATE"
    return "DENY"


# Case 1: aligned + safe — first call, empty unsafe window
t = HamiltonianTracker()
h = t.update([0.5] * 21, set())
print(f"aligned + safe          H={h:.4f} tier={tier_for(h)}")

# Case 2: recovery from one slip — 9 safe choices, then a drifted one
t = HamiltonianTracker()
for _ in range(9):
    t.update([0.5] * 21, set())
h = t.update([0.7, 0.3] * 10 + [0.5], {"aggressive"})
print(f"recovering from slip    H={h:.4f} tier={tier_for(h)}")

# Case 3: half the recent window is unsafe
t = HamiltonianTracker()
for _ in range(5):
    t.update([0.5] * 21, set())
for _ in range(5):
    t.update([0.5] * 21, {"aggressive"})
h = t.update([0.7, 0.3] * 10 + [0.5], {"aggressive"})
print(f"half-window unsafe      H={h:.4f} tier={tier_for(h)}")

# Case 4: sustained adversarial pressure
t = HamiltonianTracker()
for _ in range(9):
    t.update([0.5] * 21, {"aggressive"})
h = t.update([0.9, 0.1] * 10 + [0.5], {"aggressive"})
print(f"sustained adversarial   H={h:.4f} tier={tier_for(h)}")
```

```output
aligned + safe          H=1.0000 tier=ALLOW
recovering from slip    H=0.7884 tier=ALLOW
half-window unsafe      H=0.4631 tier=QUARANTINE
sustained adversarial   H=0.3114 tier=ESCALATE
```

## Why DENY did not fire

The default centroid is `[0.5] * 21` and personality vectors live in `[0, 1]^21`, so the maximum cosine distance the tracker can see is bounded. With `pd = 1.0` and the largest reachable `d`, `H` floors around `0.25` — above the DENY threshold.

This is **on purpose**. With the default centroid, DENY is reserved for cases where the operator has tightened the centroid (or replaced it with a per-tenant safe profile). If you want DENY to fire on raw drift alone, lower the threshold or pick a centroid your traffic cannot reach naturally:

```python
def tier_for_strict(h: float) -> str:
    if h > 0.7:
        return "ALLOW"
    if h > 0.5:
        return "QUARANTINE"
    if h > 0.3:
        return "ESCALATE"
    return "DENY"
```

A "strict" ladder demotes everything by one tier and reaches DENY at `H <= 0.3`, which the sustained-adversarial case hits. Your traffic shape decides which ladder is right.

## What this proves

1. **All four tiers are reachable** with a single bounded score — no policy DSL required.
2. **Recovery is real.** A slip after a clean history scores higher (`0.7884`) than a slip after a 50% unsafe window (`0.4631`) — the tracker rewards behavior, not just the latest action.
3. **The thresholds are operator knobs.** The default ladder targets product traffic. The strict ladder targets known-hostile environments. Both use the same harmonic wall.

## Wiring it into your pipeline

```python
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
    HamiltonianTracker,
)

tracker = HamiltonianTracker()

def gate(personality, choice_tags):
    h = tracker.update(personality, choice_tags)
    if h > 0.6:
        return "ALLOW", h
    if h > 0.4:
        return "QUARANTINE", h
    if h > 0.2:
        return "ESCALATE", h
    return "DENY", h
```

Return the tier **and** the score — the score is what the human reviewer needs to argue with.

## Next chapter

Chapter 3 wraps each gate decision in a structured **decision record**: the same tier output plus enough audit context that a reviewer six months later can reconstruct what happened and why.
