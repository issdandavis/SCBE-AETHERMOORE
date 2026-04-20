# MATHBAC Elevator Pitches — 2026-04-21 Proposers Day

## 30-second version (hook + result + ask)

"Two independently-built agentic AI stacks — one bare-metal Rust, one hyperbolic governance pipeline — turned out to share a communication surface we never designed. Under a hash-sealed blind test, the receiver recovered the sender's regime vocabulary at 24-of-24 on sealed labels, permutation p under 10⁻³. For MATHBAC TA1, that says something about the *problem structure* of agentic communication, not about either codebase. I'm Issac Davis — SCBE-AETHERMOORE. We're here looking for the right TA1 team."

## 60-second version (+ the mathematical object)

"Collin Hoag built DAVA — a bare-metal Rust agent kernel that emits a 6-field telemetry beacon it calls `phi_beacon`. I built SCBE-AETHERMOORE — a 14-layer hyperbolic governance pipeline whose Layer-1 input is a 6-slot complex context tuple. When we checked, **five of six fields type-check without translation**. Neither of us designed to the other's spec — we didn't know each other.

We ran a hash-sealed blind commit protocol: Collin sealed 24 traces with an 8-regime closed vocabulary, I committed a segmentation before labels opened, we scored. 100% on sealed labels. Permutation test at N equals 10,000 — zero out of 10,000 shuffles matched. KL channel capacity hit 99.4% of the log₂(8) ceiling under Möbius-equivariant geometry.

For MATHBAC TA1 — that's a geometric upper bound on an agentic communication channel, verified under seal. We're proposing to scale to 100 traces and formalize the curvature-to-capacity bound. We're open to teaming."

## 90-second version (+ caveats + differentiation)

*[Start with the 60-second version, then:]*

"What makes this different from a classifier result — the embedding was fixed, not learned. The 24-of-24 comes from segment-count and first-realm read straight off the Poincaré disk. No training after labels opened, no hyperparameter sweep. The jump from 87.5% to 100% came from keeping segment *order* — which is a statement about what the right observable algebra is, and that's exactly the modeling choice TA1 reviewers will have to make.

Caveats we're honest about: 24 traces is small, 8 regimes is closed vocabulary, and the seal was trace-level not per-tick. We don't have live cross-stack execution yet — the result is on logged output. And we're calling Section 4 of the working paper a 'Working Hypothesis,' not a theorem — because it isn't one yet. That's the deliverable we'd bring to a full proposal: the actual proof, not the sketch.

UEI is J-4-N-X-H-M-6-N-5-F-5-9. Active as of April 13. Here's the one-pager."

---

## Reviewer-anticipated Q&A

### Q: "24 traces is awfully small. What makes this not a lucky draw?"
**A:** Permutation test, N = 10,000 marginal-preserving shuffles. Zero matched or exceeded. One-sided 95% upper bound on p is 3.00 × 10⁻⁴ — that's the exact bound our simulation budget supports. We can budget up to N = 100,000 for a tighter number; 30-second turnaround. But a 2-log drop in p from a 10× budget increase isn't what's going to flip a reviewer — what should is the permutation null's *shape*: mean 10.88, max 16, and we hit 24. The separation is structural, not marginal.

### Q: "Isn't this just overfitting to a closed vocabulary?"
**A:** The vocabulary is closed *by design* for the seal — 8 regimes, declared in advance, hashed with the bundle. The 100% is on a blind commit, not a fit. What we're proposing in scale-up is open-vocabulary regimes, specifically HYPERVIGILANCE and DISSOCIATION, which neither codebase had in-distribution.

### Q: "Your paper had `p < 10⁻³⁰⁰`. That's a float underflow artifact."
**A:** Caught that in review — it was. Replaced with the actual permutation-test upper bound, 3.00 × 10⁻⁴, in the v3 markup. The sharper number is what we defend.

### Q: "The KL capacity number doesn't reconcile with the ceiling you cited."
**A:** Correct — v2 paper cited 1.958 against log₂(4) = 2.000, which doesn't reproduce from the committed bundle at either resolution. Only 3 of 8 cataloged realms are active. We have honest CIs at both resolutions: realm-level 1.5761 bits/tick (99.4% of log₂(3)), regime-level 2.9818 bits/tick (99.4% of log₂(8)). §3.4 gets reconciled before DARPA-facing submission.

### Q: "Have you run DAVA and SCBE live against each other?"
**A:** No — the 24/24 is on logged DAVA output, not a live channel. Deliverable #4 in our proposal is QEMU capture of DAVA `phi_beacon` feeding a running SCBE Layer 1 in real time. Until we've done that, we're careful to say "generator-against-sealed-labels verification," not "external verification of the substrate."

### Q: "What's the 'Theorem (sketch)' in §4?"
**A:** It's a working hypothesis, not a theorem. We renamed it in v3. The channel-capacity bound in terms of Poincaré curvature and realm-layout diameter is the deliverable we'd bring to a full proposal — currently it's conjecture with strong empirical support.

### Q: "Why should DARPA care about two hobbyists' stacks matching?"
**A:** Because neither of us designed to the other's spec. The interface match is a claim about the *problem*, not the *implementations*. If two independent agentic architectures land on the same communication primitive under hash-sealed blind verification, that's the kind of structural observation MATHBAC TA1 is asking for.

### Q: "What's your actual ask?"
**A:** Teaming conversation for a full proposal. We bring two independent codebases, a hash-sealed result, SAM.gov-active business infrastructure (UEI J4NXHM6N5F59), and clear deliverables: scale-up, SDP realm layout, QEMU live capture, formal capacity bound. We don't need to be the prime — we want to be a credible TA1 component.

---

## Quick-reference crib card

- **Hook:** "Communication surface we didn't design."
- **Result:** "24/24 on sealed labels, p < 3 × 10⁻⁴."
- **Math object:** "Geometric upper bound on an agentic channel."
- **Differentiation:** "Fixed embedding, not learned."
- **Ask:** "Teaming for a full proposal."
- **Contact:** `issdandavis7795@gmail.com` · UEI `J4NXHM6N5F59`
