# MATHBAC Proposers Day — Cheat Sheet

**2026-04-21 · 11 AM – 2 PM ET (8 AM – 11 AM PT) · Virtual**
**PM:** Yannis Kevrekidis · **Your ID:** Issac D Davis · **UEI:** J4NXHM6N5F59 · **CAGE:** 1EXD5 (ACTIVE 2026-04-13)

---

## The one sentence

> "Geometric upper bound on an agentic communication channel, verified under seal — 24/24 on sealed labels, p ≤ 3.00 × 10⁻⁴."

## The 15-second hook

Two independently-built agentic stacks — bare-metal Rust (DAVA) and hyperbolic governance (SCBE) — turned out to share a 5-of-6 communication surface we never designed. Hash-sealed blind verification landed 24/24.

---

## Numbers to defend

| Claim | Number | Guard |
|---|---|---|
| Sealed-label accuracy | **24/24 = 100%** | Blind commit protocol, segmentation hashed before labels opened |
| Permutation upper bound | **p ≤ 3.00 × 10⁻⁴** | Not `p < 10⁻³⁰⁰` (that was float underflow, corrected in v3) |
| KL capacity (realm-level) | **1.5761 bits/tick = 99.4% of log₂(3)** | Only 3 of 8 cataloged realms active — this is honest CI |
| KL capacity (regime-level) | **2.9818 bits/tick = 99.4% of log₂(8)** | Reconciled in v3 markup |
| Trace count (v1) | **24** | Small, closed vocabulary (8 regimes), hand-picked — evidence of separability, not proof |
| Mobius equivariance | **Bit-identical k-means++** | PSU(1,1) isometries preserve clustering |

## Anti-numbers (things to NOT say)

- ❌ "p < 10⁻³⁰⁰" (float underflow, v2 paper only)
- ❌ "Theorem 4" (it's a Working Hypothesis in v3)
- ❌ "Externally verified substrate" (it's generator-against-sealed-labels)
- ❌ "log₂(4) = 2 bits ceiling" (v2 number, unreproducible from bundle)
- ❌ "Provably higher combinatorial cost" (not proven, dropped in v3)

---

## Top-3 teaming targets (hit in this order)

| # | Person | Handle | Opener |
|---|---|---|---|
| 1 | **Oliver Chiriac** (Aalyria) | oliver@aalyria.com · 609-613-0220 | "Your Oxford work on persistent homology of graph embeddings in product manifolds — we're running a hyperbolic product-manifold embedding with hash-sealed 24/24 on a live agentic channel. 60 seconds?" |
| 2 | **Somesh Jha** (UW-Madison) | jha@cs.wisc.edu · 608-215-6702 | "Your π-calculus approach for agent communication — we have the geometric substrate that generates the messages. TA1+TA2 joint?" |
| 3 | **Chandan Reddy** (VA Tech) | reddy@cs.vt.edu · 571-858-3307 | "Your ask for information/category-theoretic inter-agent knowledge transfer — LWS is a phi-weighted categorical transform with a channel-capacity bound. Want to compare?" |

If prime needed: **Salman Avestimehr** (USC, 3× DARPA PI) — `avestime@usc.edu`. SCBE = hyperbolic substrate under his Coded Computing.

---

## Q&A pivots (reviewer likely questions)

| They ask | You say |
|---|---|
| "N=24 is small" | "Permutation null: mean 10.88, max 16, we hit 24. Structural separation, not marginal." |
| "Overfitting closed vocabulary" | "Vocabulary sealed in hashed bundle. 100% is on blind commit. v2 is open-vocab — HYPERVIGILANCE + DISSOCIATION." |
| "Paper has p<10⁻³⁰⁰" | "Caught it in review. Float underflow. Replaced with permutation-test upper bound 3.00 × 10⁻⁴ in v3." |
| "Live cross-stack?" | "Not yet. v2 deliverable is QEMU capture of DAVA phi_beacon → SCBE L1 in real time. Currently generator-against-sealed-labels." |
| "Theorem 4?" | "Working Hypothesis in v3. Channel capacity in terms of Poincaré curvature + realm diameter is the proposal deliverable." |
| "Why should DARPA care?" | "Two independent architectures land on the same communication primitive under hash-sealed blind test. That's a claim about the problem, not the implementations." |
| "Your ask?" | "Teaming conversation for a full proposal. Two independent codebases, sealed result, SAM.gov-active. Don't need to be prime — want to be credible TA1 component." |

---

## Things to say orally every conversation

- "Working Hypothesis, not Theorem"
- "Permutation upper bound 3 × 10⁻⁴, not the paper's 10⁻³⁰⁰"
- "CAGE is 1EXD5, active April 13 — consolidated profiles show Pending"
- "Joint result with Collin Hoag / DAVA (page 11 in your book)"

## What to write down in the PM talk (first 10 min are the whole game)

- [ ] Scoring criteria verbatim
- [ ] Out-of-scope list
- [ ] Deliverable cadence (phase gates)
- [ ] Contracting vehicle (OT vs FAR)
- [ ] Every specific phrase about what TA1 is / isn't
- [ ] Every example he gives of target applications

## One written Q&A to submit (pick one)

1. "Is a communication channel between agents of independent architectures in scope, or does TA1 presume a single architecture?"
2. "Does 'mathematics of agentic AI communication' include verification geometry, or is that assumed TA2?"
3. "Is empirical evidence at N=24 closed-vocabulary adequate phase-1 evidence, or is open-vocab a phase-1 requirement?"

---

## Contact line (business card equivalent)

```
Issac D Davis · SCBE-AETHERMOORE
issdandavis@proton.me · (360) 808-0876
UEI J4NXHM6N5F59 · CAGE 1EXD5 (ACTIVE)
Port Angeles, WA · sole prop · minority-owned
github.com/issdandavis/SCBE-AETHERMOORE
```

## If you can't answer something DAVA-internal

> "Collin owns DAVA internals; happy to loop him in after today. I can speak to the observational interface and the SCBE side."

---

**Before the call:** test webcast audio/video. Print or load this file on a second screen. Have one-pager PDF ready to drop in chat. Be early — first 10 minutes is the scoring rubric.
