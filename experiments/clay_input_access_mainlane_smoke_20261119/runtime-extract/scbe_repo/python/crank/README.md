# Crank

**Turn long AI work into a visible workflow machine: intent in → controlled, checkpointed steps → a cataloged result with receipts.**

Standalone (no project deps). The discipline is borrowed from a mechanical calculator: a result is only real once every step has settled into a constrained, **receipted** state — no half-turned gears, no in-between — and the catalog (the receipt chain) is the proof.

## Why

Two ideas converge here:
- **Topology** (a hard problem becomes easy once lifted into a structure where the answer is *forced*) → lift a messy AI task into a phase graph where drift / collision / missing-output become *visible*.
- **The mechanical calculator** (arithmetic gets reliable when mental steps become constrained discrete states) → force each AI phase into a settled, gated, hashed state before the next turn.

| messy input | lifted structure | reliability | proof | failure mode |
|---|---|---|---|---|
| vague AI task | phase sequence | forced checkpoints | catalog + receipt chain | drift / blocked / collision |

## Use

```python
from python.crank import Phase, turn, render

phases = [
    Phase("research", lambda intent, ctx: f"notes about: {intent}"),
    Phase("build",    lambda intent, ctx: f"impl for: {intent}"),
    Phase("review",   lambda intent, ctx: f"reviewed: {ctx['outputs']['build']}"),
    Phase("deliver",  lambda intent, ctx: {"artifact": ctx["outputs"]["build"], "status": "shipped"}),
]
cat = turn("add a numfind tool", phases)
cat.ok            # True
cat.result        # {"artifact": "impl for: add a numfind tool", "status": "shipped"}
cat.chain_digest  # tamper-evident proof of the whole run
print(render(cat))
```

## The three failure modes (surfaced, not hidden)

- **drift** — a phase produced nothing (empty output, or it raised). The machine does not crash; it records the drift.
- **blocked** — the gate refused a (non-empty) output. Plug in a real policy (e.g. a governance score) as the `gate`.
- **collision** — a phase produced output identical to an earlier phase: no progress.

Each receipt folds the previous chain digest, so changing *any* phase's output or status changes the final `chain_digest`. The run is **deterministic** — same intent + same phases → same catalog → same proof.

## Composition

Executors are injected, so the machine is deterministic and testable while the real work plugs in:
- a **research/build/review** phase can call an AI or a tool;
- a **build** phase can emit + verify code with `python/loom` (cross-language, with a loop/halting check);
- the **gate** can be a real governance policy;
- parallel phases can be kept coherent with the tangent (keel) coordinator.
