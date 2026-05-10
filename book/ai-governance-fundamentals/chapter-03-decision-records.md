---
schema: scbe_runnable_ebook_v1
book: ai-governance-fundamentals
chapter: 03
slug: decision-records
title: Decision Records — making one gate call auditable six months later
version: 0.1.0
who: AI engineers and team leads who need to defend a gate decision after the fact
what: A 7-field decision record schema that wraps each gate call with enough context to reconstruct it without rerunning the model
when: Whenever a gate decision could be challenged later — incident review, compliance audit, customer complaint
where: Immediately downstream of the L13 risk decision (Chapter 2), inside the same request handler
why: A bare ALLOW/QUARANTINE/ESCALATE/DENY tier is a verdict without a defense — the decision record is the defense
test_suite: tests/book/ai_governance_fundamentals/test_chapter_03_decision_records.py
runnable_languages: [python]
estimated_read_minutes: 11
prereq_chapters: [01, 02]
---

# Decision Records

> **Who** Anyone who will be asked, six months after a deploy, "why did the gate quarantine that conversation?"
> **What** A 7-field record schema you can serialize to JSON, ship to a log sink, and replay during review.
> **When** Every gate call in production. The cost of synthesis is one dataclass instantiation; the cost of *not* having it is reconstructing the run from memory under audit pressure.
> **Where** Inline in the request handler, right after the gate emits a tier.
> **Why** "We blocked it" is not an answer. "We blocked it because H = 0.31, the personality drifted to cosine distance 0.21, and 100% of the recent window was tagged unsafe" is.

## The toolkit pillar this replaces

The classic "AI Governance Toolkit" sells you a Word template with blank fields and a few example fills. It works once and rots immediately, because nobody updates static templates after a deploy ships.

A decision record is the same idea, except it is **emitted by the running system on every gate call**, with values pulled from the actual gate inputs. There is no template to keep in sync — the record IS the running gate.

## The 7-field schema

```python
from dataclasses import dataclass, asdict
import json

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


def reviewer_action_for(tier: str) -> str:
    return {
        "ALLOW": "pass-through",
        "QUARANTINE": "hold-for-reviewer",
        "ESCALATE": "page-on-call",
        "DENY": "block-and-log",
    }[tier]


@dataclass(frozen=True)
class DecisionRecord:
    request_id: str
    tier: str
    h_score: float
    centroid_distance: float
    recent_unsafe_ratio: float
    reviewer_action: str
    audit_note: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def make_record(
    request_id: str,
    tracker: HamiltonianTracker,
    personality: list,
    tags: set,
) -> DecisionRecord:
    h = tracker.update(personality, tags)
    tier = tier_for(h)
    # Recompute the same intermediates the tracker used so the record is
    # auditable without having to rerun the model.
    d = tracker._cosine_distance(personality, tracker._centroid)
    pd = sum(1 for u in tracker._recent_choices if u) / max(
        len(tracker._recent_choices), 1
    )
    note = f"tier={tier} fired because H={h:.4f} (d={d:.4f}, pd={pd:.4f})"
    return DecisionRecord(
        request_id=request_id,
        tier=tier,
        h_score=round(h, 4),
        centroid_distance=round(d, 4),
        recent_unsafe_ratio=round(pd, 4),
        reviewer_action=reviewer_action_for(tier),
        audit_note=note,
    )


# A clean ALLOW
tracker = HamiltonianTracker()
record = make_record("req-001", tracker, [0.5] * 21, set())
print(record.to_json())
```

```output
{
  "audit_note": "tier=ALLOW fired because H=1.0000 (d=0.0000, pd=0.0000)",
  "centroid_distance": 0.0,
  "h_score": 1.0,
  "recent_unsafe_ratio": 0.0,
  "request_id": "req-001",
  "reviewer_action": "pass-through",
  "tier": "ALLOW"
}
```

## What changes when the gate fires hot

Same record, drift-and-unsafe input:

```python
from dataclasses import dataclass, asdict
import json

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


def reviewer_action_for(tier: str) -> str:
    return {
        "ALLOW": "pass-through",
        "QUARANTINE": "hold-for-reviewer",
        "ESCALATE": "page-on-call",
        "DENY": "block-and-log",
    }[tier]


@dataclass(frozen=True)
class DecisionRecord:
    request_id: str
    tier: str
    h_score: float
    centroid_distance: float
    recent_unsafe_ratio: float
    reviewer_action: str
    audit_note: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


tracker = HamiltonianTracker()
h = tracker.update([0.9, 0.1] * 10 + [0.5], {"aggressive"})
record = DecisionRecord(
    request_id="req-002",
    tier=tier_for(h),
    h_score=round(h, 4),
    centroid_distance=round(
        tracker._cosine_distance([0.9, 0.1] * 10 + [0.5], tracker._centroid),
        4,
    ),
    recent_unsafe_ratio=1.0,
    reviewer_action=reviewer_action_for(tier_for(h)),
    audit_note=f"tier={tier_for(h)} fired because H={h:.4f}",
)
print(record.to_json())
```

```output
{
  "audit_note": "tier=ESCALATE fired because H=0.3114",
  "centroid_distance": 0.2118,
  "h_score": 0.3114,
  "recent_unsafe_ratio": 1.0,
  "request_id": "req-002",
  "reviewer_action": "page-on-call",
  "tier": "ESCALATE"
}
```

## What this proves

1. **A gate decision is auditable in seven fields.** No external system, no annotation pass, no second model call. The fields come from the same arithmetic the gate already did.
2. **The record is replayable.** A reviewer can take `centroid_distance` and `recent_unsafe_ratio` and recompute `H` exactly — no need to rerun the model.
3. **The record is shippable.** `to_json()` produces a stable, sorted-keys output safe for log sinks, change detection, and diff-based incident triage.

## Wiring it into your pipeline

Two lines in your handler (pseudocode — `make_record` is the helper from
the first runnable example above):

```text
record = make_record(request_id, tracker, personality, tags)
log_sink.write(record.to_json())
```

If `tier` is `QUARANTINE` or stricter, also push the record into your reviewer queue. The reviewer queue's input is now stable JSON, not free-form chat transcripts — which means triage tooling, search, and metrics all become trivial.

## Next chapter

Chapter 4 introduces the **Sacred Tongues weighting** — the φ-progression that lets the operator choose *which* governance dimensions matter for *this* product, not a one-size-fits-all set.
