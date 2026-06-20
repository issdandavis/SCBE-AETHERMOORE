---
schema: scbe_runnable_ebook_v1
book: ai-governance-fundamentals
chapter: 01
slug: harmonic-wall
title: The Harmonic Wall — bounded safety scoring
version: 0.1.0
who: AI engineers shipping LLM-backed features for the first time
what: How the harmonic wall H(d, pd) = 1 / (1 + d + 2*pd) bounds adversarial cost in (0, 1]
when: Before deploying any model that takes free-form user input
where: At the output gate, between the model response and the downstream caller
why: Unbounded safety scores let attackers walk the threshold without paying cost — the harmonic wall keeps that cost finite and visible
test_suite: tests/book/ai_governance_fundamentals/test_chapter_01_harmonic_wall.py
runnable_languages: [python]
estimated_read_minutes: 12
prereq_chapters: []
---

# The Harmonic Wall

> **Who** AI engineers shipping LLM-backed features for the first time.
> **What** A bounded safety score that sits between your model and your users.
> **When** Before any deploy that accepts free-form user input.
> **Where** At the output gate — after the model speaks, before the caller acts.
> **Why** Without it, an attacker can drift gradually past every static threshold you set.

## The problem with thresholds

Most "is this output safe" gates score a model response on some 0-to-infinity
risk number and trip when it crosses a threshold. That sounds defensible until
the third week of operation, when an attacker finds the slope of your scorer
and starts walking up to it from below. They never trip the wall; they live
right under it. Your dashboard stays green.

The fix is not a higher threshold. The fix is a score that's **bounded**, so
"how close are we to the wall" is a number you can reason about — and so
adversarial drift visibly shows up as the bound being approached.

## The formula

The SCBE harmonic wall is one line:

$$
H(d, p_d) = \frac{1}{1 + d + 2 \cdot p_d}
$$

- **d** is a distance (0 to ~10 in practice) from a "safe centroid" in the
  representation space the operator chose. Closer to the centroid means more
  trustworthy.
- **p_d** is the proportion of the recent decision window that violated soft
  constraints (0 to 1). A burst of unsafe choices spikes p_d.
- **H** is bounded in (0, 1]. H = 1 means perfectly safe; H near 0 means very
  unsafe. The bound is *algebraic*, not learned, so an attacker cannot find
  a region where H exceeds 1.

## Runnable example

The SCBE codebase ships a `HamiltonianTracker` that implements this exactly.
Paste this into a fresh shell with `pip install scbe-aethermoore` and
`PYTHONPATH=.`:

```python
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
    HamiltonianTracker,
)

tracker = HamiltonianTracker()

# A perfectly-aligned personality + an empty unsafe window
safe_personality = [0.5] * 21
h_safe = tracker.update(safe_personality, set())
assert 0.0 < h_safe <= 1.0
print(f"safe call:    H = {h_safe:.4f}")

# A drifted personality + one unsafe choice in the window
drifted = [0.9, 0.1] * 10 + [0.5]
h_drift = tracker.update(drifted, {"aggressive"})
assert 0.0 < h_drift <= 1.0
assert h_drift < h_safe, "drift must lower the safety score"
print(f"drifted call: H = {h_drift:.4f}")
```

```output
safe call:    H = 1.0000
drifted call: H = 0.4521
```

## What this proves

Three guarantees, all checkable in a unit test:

1. **Bounded.** Both calls return values in `(0, 1]`. No matter what input the
   tracker sees, that bound holds — it is a property of the formula, not of
   the data. (See chapter 2 for the proof.)
2. **Monotone in drift.** A more drifted personality + unsafe choice scored
   strictly lower than the safe baseline. An attacker cannot drift "for free."
3. **Auditable.** The score is computed from two named inputs (`d`, `p_d`). A
   human reviewing a flagged decision can ask "which one moved" — was it the
   distance, or the recent-violations window?

## Wiring it into your pipeline

Three lines in your output gate:

```python
from src.symphonic_cipher.scbe_aethermoore.concept_blocks.cstm.telemetry_bridge import (
    HamiltonianTracker,
)

GATE_THRESHOLD = 0.6  # ALLOW above; QUARANTINE/DENY at or below
tracker = HamiltonianTracker(threshold=GATE_THRESHOLD)

def gate(personality_vector, recent_choice_tags):
    h = tracker.update(personality_vector, recent_choice_tags)
    if h > GATE_THRESHOLD:
        return "ALLOW"
    elif h > 0.4:
        return "QUARANTINE"
    return "DENY"
```

Pick your `GATE_THRESHOLD` based on the cost you can pay for a false-positive
quarantine. The bounded score makes that conversation a lot shorter than a
"how high should the risk number go" debate.

## The 5Ws, restated

- **Who** is paying attention to this score? Whoever owns the model in
  production. If that is you, this chapter is for you.
- **What** changes if you switch from an unbounded scorer to the harmonic
  wall? Adversarial drift becomes visible as a number in `(0, 1]` instead of
  a noisy unbounded series.
- **When** do you read this? Before the first deploy that takes free-form
  input. After that, the cost of refactoring the gate goes up linearly with
  every dependency you add to it.
- **Where** does the wall live? At the output gate, after model inference,
  before any downstream consumer (UI, function call, tool dispatch).
- **Why** does this matter? Because static thresholds are walked. Bounded
  scores are climbed, and climbing is loud.

## Next chapter

Chapter 2 proves the bound algebraically and shows how the same formula
extends to multi-modal output (text + tool calls + audio). It also covers
the connection to the 14-layer SCBE pipeline, of which this gate is layer 12.
