# The Corridor Test — does coordinated legible structure beat the sum of its parts?

**Status:** experiment design (pre-registered). The point is to make the thesis
*falsifiable*: define the win, the null, and the loss before running, so the result can
actually disprove the idea instead of flattering it.

## The thesis, in your words

> "Keep making each system ~4× better, then let them help each other in a coordination of
> ons and offs, fallings and risings between them."

Formally: you have *k* legible subsystems, each with its own honest gain factor `fᵢ`
(measured, ~2–6×, not assumed). Two questions:

1. **Do the levers actually pull?** (ablation — does each `fᵢ > 1`, measured, with a card?)
2. **Does coordination buy synergy?** Define the **compounding factor**:

   ```
   g  =  (coordinated result)  /  (best static combination of the same levers)
   ```

   - `g > 1`  → coordination buys something the parts don't. **Thesis supported.**
   - `g ≈ 1`  → coordination is just stacking. Fine, honest, but no magic.
   - `g < 1`  → coordination *overhead* hurts. **Thesis refuted** (and worth knowing).

`g` is the whole experiment. One number, pre-registered, three possible verdicts.

## The levers (each an on/off knob, each measured alone)

Each subsystem is a switch. With it OFF you fall back to the opaque/static equivalent.
This is where "each system ~4× better" gets *measured*, not claimed:

| Lever | OFF (baseline) | ON (legible) | What it should buy |
|---|---|---|---|
| **L1 encode** | opaque re-encode every step | reversible board address | skip redundant work; exact position ⇄ token |
| **L2 verify** | trust the bytes | DNA self-verify per token | detect corruption locally, no full recompute |
| **L3 route** | round-robin / random | Poincaré cost + torus locality | send work the cheap way; quarantine drift |
| **L4 recover** | fail / full redo on fault | reversible address + RRNS lane | reconstruct from a surviving face |

Run the full 2⁴ ablation (16 cells) or a focused subset. Each cell gets a score card
(`score-template.json`). Output: a measured `fᵢ` per lever — the honest "4× each."

## The coordination layer (ons / offs, fallings / risings)

Static combination = all levers on, fixed, independent. **Coordination** = the geometric
scheduler driving them as a dynamic: under load and faults, route each unit of work to the
subsystem that is *rising* (has capacity / low current cost) and rest the one that is
*falling* (saturated / drifting), with each subsystem's output feeding the next.

This is the existing `geometric_scheduler` + `poly_mountain` machinery pointed at the
levers. The "fallings and risings" are literal: a per-subsystem load/cost signal that
oscillates, and the scheduler surfs it instead of fighting it. Hypothesis: phased hand-off
recovers idle time and dodges the worst-case of any single lever — which is exactly the
super-additive `g > 1` we're testing for.

## The task + fault model (concrete, runnable)

- **Workload:** a stream of *N* programs (token sequences from the real corpus), each pushed
  through encode → route → verify → (recover) under **injected faults** (bit flips, dropped
  lane, drifted token) at a tunable rate `p`, and **varying load** (bursts, so subsystems
  actually rise and fall).
- **Baseline arm (opaque/static):** programs as opaque vectors, round-robin routing, no
  self-verify, full redo on fault. The honest "what everyone else does."
- **Measured per arm:**
  - correctness under fault (recovery rate)
  - cost (steps / tokens / simulated \$ — defined exactly, marked modeled)
  - throughput under load (units/sec)
  - tail latency (p95) — coordination should crush the tail, not just the mean

## Pre-registered verdicts (no moving the goalposts after)

- **Supported:** coordinated arm beats best-static by `g > 1` on cost *and* tail latency,
  with CV < 5%, on two independent machines (laptop + Kaggle). Recovery rate strictly higher
  than opaque when `p > 0`.
- **Null:** `g ≈ 1` — coordination matches stacking. The structure is *legible and correct*
  but not yet an *edge*. Honest, publishable, and the signal to go find a task where it does.
- **Refuted:** `g < 1` or recovery ≤ opaque — coordination overhead isn't worth it here.
  Report it plainly; that's a real finding, not a failure.

## What a win would actually prove

Not "fastest." It would prove the thing nobody else can say: **a system of legible,
self-verifying parts that coordinate degrades gracefully and routes cheaply under fault and
load, and does so measurably better than an opaque monolith** — and that the advantage
*compounds* as you add honest 4× levers rather than needing one heroic 100×. That is a moat
a 4.5× encoder never could be, because it's an architecture claim, not a micro-optimization.

## Build plan

1. `scripts/benchmarks/corridor_bench.py` — the arms, fault injector, load generator,
   emitting one `score-template.json` per ablation cell + a top-line `g`.
2. Wire the 4 levers to their real modules (board, bijective_dna, geometric_router/torus,
   RRNS) with clean OFF fallbacks.
3. Drive the coordinated arm with `geometric_scheduler`; the static arm with fixed parallel.
4. Run locally (pinned) and on Kaggle (you push); compare `g` across both.
5. Loop-until-dry: keep adding honest levers; re-measure `g` each time. The thesis is alive
   exactly as long as `g` stays > 1 while `k` grows.

> One line: *measure each lever's honest gain, then measure whether coordinating their
> rises and falls beats stacking them — `g` is the verdict, and it's allowed to say no.*
