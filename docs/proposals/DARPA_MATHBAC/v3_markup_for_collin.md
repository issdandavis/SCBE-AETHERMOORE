# v3 markup for Collin — push-back list on "Joint Observer" v2

**From:** Issac D. Davis
**To:** Collin Hoag
**Re:** Joint Observer: DAVA ⊕ SCBE-AETHERMOORE v2 → v3
**Date:** 2026-04-20

Collin — I ran the v2 draft against what I can actually defend under DARPA-style review. Five items I'd like you to land before we ship. Headline result (24/24 sealed-commit, the phi_beacon ↔ L1 match, the channel-capacity story) stays exactly as you have it. The pushback is entirely on language that overclaims what the artifacts prove.

## 1. Abstract — "first independent external verification of phi-telemetry substrate"

**Current:** "...the first independent external verification of the phi-telemetry substrate..."

**Proposed:** "...a generator-against-sealed-labels verification of the regime vocabulary encoded in the phi-telemetry substrate..."

**Why:** We verified SCBE can recover your regime labels under a hash-sealed blind protocol. We did not verify a *live* phi-telemetry channel between DAVA (running) and SCBE (running). "External verification of the substrate" implies the latter. Until we have live QEMU capture feeding SCBE L1 in real time, the softer phrasing is what we can defend.

## 2. §3.2 — `p < 10⁻³⁰⁰`

**Current:** "Permutation test yields p < 10⁻³⁰⁰."

**Proposed:** "Permutation test (N = 10,000, marginal-preserving label shuffle, seed = 20260419): 0 / 10,000 permutations matched or exceeded the observed 24/24. Null distribution: mean 10.88 correct, max 16. One-sided 95% upper bound on p is 1 − 0.05^(1/N) = 3.00 × 10⁻⁴. Bootstrap CI on accuracy (N = 10,000, resample-with-replacement over the 24 traces) is [1.00, 1.00] (median 1.00)."

**Why:** `10⁻³⁰⁰` is below float64 representable range. It's a float-underflow artifact, not a p-value. A reviewer who knows numerics will call this out. Running the actual permutation test is strictly stronger and the `3.00 × 10⁻⁴` number is defensible — it's the exact upper bound our simulation budget supports. Ran 2026-04-19; report at `artifacts/collab/dava_blind_v1/permutation_test_report.json` (sha256 `0830e7dd95678b680e1d53d7f90a89c77beb7960a4318ea0d0dfbf5c271bc2fd`). Budget-up to N = 100,000 is a 30-second turnaround if you want a tighter bound for the paper.

## 3. §3.4 — KL channel capacity 1.958 bits/tick

**Current:** Reports a point estimate of 1.958 bits/tick (97.9% of the 2.000-bit log₂(4) ceiling).

**Proposed:** Add a bootstrap CI (resample segments with replacement, ≥ 1,000 bootstrap samples) and report as "1.958 bits/tick [CI_low, CI_high]." If the CI is tight, that's a stronger claim; if it's wide, we learn something about the estimator.

**Status 2026-04-19 — bootstrap CI ran, K_active mismatch surfaced.** Bootstrap CI on the committed segmentation bundle (`segmentation_committed.json`, sha256 `dab56a6832548f22821d737f7f4f7434f6d9f0c9165ed375baf57963673e64d8`), N = 10,000 trace-level resamples with replacement, Laplace α = 1.0 smoothing, seed 20260419:

| resolution | K_active | ceiling log₂(K) | point estimate | bootstrap median | 95% CI | % of ceiling |
|---|---|---|---|---|---|---|
| realm  | 3 | 1.585 | 1.5761 | 1.5762 | [1.5718, 1.5799] | 99.4% |
| regime | 8 | 3.000 | 2.9818 | 2.9815 | [2.5709, 2.9835] | 99.4% |

Report: `artifacts/collab/dava_blind_v1/kl_capacity_ci_report.json` (sha256 `138d3cf9d00b16153fe4e9e50ec5ec152d4ac5ede47959cad8f5d381f4f2d4d5`).

**Reconciliation needed before §3.4 can cite a CI.** The v2 paper's 1.958 bits/tick against a log₂(4) = 2.000 ceiling does not match either resolution in the committed bundle. Only 3 of 8 cataloged realms (R_CORE_QUIET, R_CORE_ACTIVE, R_CONN_LOW) are active in the segmentation — the other 5 realms have zero ticks — and all 8 regimes (SCBE_R00–R07) are active. Two reads:

1. The v2 number was computed on a different segmentation resolution (e.g., a 4-bin coarse-graining of the 8 realms that we don't have source for). Share the v2 computation code and I'll re-run the bootstrap at that resolution.
2. The v2 number pooled realm + something else (e.g., tier or breath phase) to reach 4 effective states. Same ask — share the binning and we re-run.

**Proposed v3 text:** "Under the phi-quantile Poincaré embedding, the regime-transition Markov chain has channel capacity [point estimate] bits/tick, bootstrap 95% CI [low, high] over N = 10,000 trace-level resamples of the blind protocol, which is [%]% of the log₂([K_active]) = [ceiling] bit/tick maximum-entropy ceiling under [resolution]-level segmentation (K_active = [K])." Fill in from the table once the K_active question is resolved.

**Why:** A point estimate this close to the theoretical ceiling begs the question "how close is it actually?" A reviewer will not trust the 97.9% without a CI. Also: specify the binning / quantile-center procedure used to estimate the transition probabilities; it matters for reproducibility — the K_active discrepancy above is a live example of that reproducibility cost.

## 4. §4 — "Theorem (sketch)"

**Current:** "**Theorem (sketch).** Under the phi-quantile Poincaré embedding, the channel capacity of the regime-transition process is upper-bounded by [...]."

**Proposed:** Rename to "**Working Hypothesis**" or "**Claim**." Keep the intuition-building derivation verbatim.

**Why:** "Theorem" is a load-bearing word. "Theorem (sketch)" is not a theorem — it is a hypothesis, phrased aspirationally. DARPA MATHBAC TA1 is specifically asking for *mathematical* objects, so being sharp about the difference between "we conjecture" and "we prove" is exactly the kind of rigor they're selecting for. Write it as a hypothesis now, deliver the actual theorem as a follow-on.

## 5. §4 — "provably higher combinatorial cost"

**Current:** "...a provably higher combinatorial cost than [...]"

**Proposed:** "...a higher combinatorial cost, with supporting empirical evidence at [cited scale]..." or "...a combinatorial cost we conjecture to be asymptotically dominant; see open problem O-1."

**Why:** Same reason as #4. "Provably" is a promise we haven't delivered on. Drop it; promote the proof to an explicit open problem in the open-problems section. Reviewers will respect the open-problem framing; they will not respect an unbacked "provably."

## What I want to keep unchanged

- The phi_beacon ↔ L1 interface table (Proposition 1). Five-of-six is the finding, state it exactly.
- Both SHA-256 hashes in §3.5. They're verified locally on my end against the artifacts — reproducible from `dava_v1_for_collin.tar.gz`.
- The v1 → v2 → v3 scoring ladder. The jump from 87.5% to 100% via segment ordering is the most interesting single finding in the paper.
- The min-form `causal_phi = max(0, min(H_k, H_m) − |H_k − H_m|/2)`. That correction belongs in v3, with the v2 ratio-form flagged as superseded.
- The honest caveats in §3.6 (trace-level seal, closed vocabulary, N=24). Don't soften these — they're what make the sealed result credible.

## Mechanics

Happy to take a pass in Google Docs tracked changes if you want, or send back a unified diff against the v2 text once you've dropped it into a repo. Let me know which is easier. I'm holding the Proposers Day joint memo (separate file, `docs/proposals/DARPA_MATHBAC/joint_memo_v1.md`) for your review before either of us ships anything externally.

— Issac
