---
tags: [prime-fog, ring, consumed]
updated_at: 2026-06-04
---

# Ring M — 700M to 750M

**Status: CONSUMED — cascade v6 FALSIFIED. frozen_dominant predicted frozen wins; frozen came LAST.**

## The falsification

v6 committed prediction: `frozen_dominant` (frz_mean>0.45 ✓, frz_skew>1.0 ✓) → raw frozen wins.
**Actual: frozen 4/202 — the WORST controller. frozen_coherent won at 9/202.**

| Method | Hits | Delta |
| --- | ---: | ---: |
| frozen baseline (= v6 frozen_dominant) | **4/202** | — |
| dominant (wf=-1.5) | 7/202 | +3 |
| magnitude (wf=+0.5, wa=2) | 6/202 | +2 |
| **frozen_coherent (wf=+1.0, wc=1.5)** | **9/202** | **+5** |

**v6 predicted the single worst controller.** Total regime inversion from L, where frozen
(13) crushed every blend (≤5). At M, every blend beats raw frozen.

## What broke — the frozen_dominant premise

frozen_dominant assumes `frz_skew > 1.0 ⟹ raw frozen top-20 is optimal`. That held for K and L
and failed at M. The trigger fired correctly (frz_skew=1.167 > 1.0) but the conclusion was wrong.

| Ring | frz_mean | frz_skew | corr_frz_cen | frozen result |
| --- | ---: | ---: | ---: | --- |
| K | 0.506 | 1.033 | −0.226 | WON +1 (marginal) |
| L | 0.531 | 1.187 | −0.221 | WON +8 (strong) |
| **M** | **0.606** | 1.167 | **−0.159** | **LOST −5 (worst)** |

## Honest postmortem — frozen_dominant was overfit to noise

frozen_dominant was committed on **2 points**: K (+1, within top-20 counting noise) and L (+8, strong).
It passed L blind because L was genuinely in-regime. But K's +1 is noise-level (anchor counts ~180,
top-20 metric, single-digit hit differences have real variance). So the rule rested largely on **L's
single strong margin** — and M shows that was a favorable fluctuation, not a stable law.

**This is the SAME error as the period-2 alternation**: a pattern believed on too few points. The
"≥5 points before committing cascade logic" discipline from [[Ring L]] applies to NEW regime rules,
not just oscillation claims. frozen_dominant violated it (committed on 2) and got burned on the 3rd.

## Candidate flip discriminator (HYPOTHESIS — 1 point, do NOT commit)

What separates frozen-wins (K/L) from frozen-breaks (M):

- **corr_frz_cen**: K/L ≈ −0.22, M = **−0.159**. The frozen/centroid anti-correlation weakened — the
  centroid realigned with frozen, so the cooperative blend (frozen_coherent) recovers anchors the raw
  spike misses. Candidate threshold ≈ −0.19.
- **frz_mean**: K/L ≤ 0.531, M = **0.606**. Frozen gate may degrade once mean climbs past ~0.57.

**v7 hypothesis (UNCOMMITTED):** inside frz_skew > 1.0, add an exit —
`if corr_frz_cen > −0.19 (or frz_mean > 0.57) → frozen_coherent, NOT frozen_dominant`.
This is a **1-point observation**. Test on Ring N before any commit. Do not repeat the 2-point mistake.

## The concentration phase hit a turning point

5D trajectory speed collapsed: K→L = **0.596** (max of A–L), L→M ≈ **0.085** (7× slower).
The acceleration the navigator saw was a system approaching a **turning point**, not a runaway.

- frz_mean: still climbing (+0.075, broke the ~0.546 saturation estimate — that too was a <5-point illusion)
- frz_skew: turned over (1.187 → 1.167, first drop since F)
- frz_kurt: flattened (1.597 → 1.615, NOT the 2.0+ the navigators projected)
- corr_frz_cen: rose toward zero (centroid re-coupling)

frozen_coherent winning = a **return toward the cooperative regime** (F's controller). The
concentration phase (G→L) appears to be ending/reversing at M.

## Manifold navigator scorecard (honest)

- **Dynamics warning: RIGHT.** It explicitly said "watch for the frozen margin to peak then fall"
  and "near-future breakdown." Margin K +1 → L +8 → M −5. The breakdown arrived.
- **Regime projection: WRONG.** Both navigators (PCA, FD) projected frozen_dominant continues. The
  regime flipped to frozen_coherent.
- **Feature projections: mixed.** frz_skew right sign (>1.0, but overshot). frz_mean WRONG (projected
  ~0.546 saturating; actual 0.606 still climbing). frz_kurt WRONG (projected ~2.0; actual 1.615).

**Lesson on the navigator**: trust its qualitative dynamics flags (a breakdown is coming), not its
quantitative one-step coordinates. Extrapolating an accelerating trajectory assumes no turning point;
there was one.

## Lessons

1. **v6 frozen_dominant FALSIFIED** at M (predicted worst controller). Premise `frz_skew>1.0 ⟹ frozen
   optimal` is false — held K/L (largely L's fluctuation), broke M.
2. **Committed on 2 points → burned on the 3rd.** Same error class as period-2 alternation. Apply the
   ≥5-point rule to new regime rules.
3. **frz_mean did NOT saturate**: 0.546 Aitken estimate falsified; M=0.606. The saturation was a
   transient, like the F/G/H linear slope was.
4. **Turning point at M**: trajectory speed collapsed 0.596 → 0.085; cooperative regime returning.
5. **corr_frz_cen is the candidate flip variable** (−0.22 → −0.159). Hypothesis only; test on N.

## Next

1. **Ring N (750M–800M)**: the disambiguator. Is M a turning point (cooperative regime returns, frz_skew
   keeps dropping) or noise (frozen_dominant resumes)? Route with v6 AS-IS (do not patch on 1 point),
   record whether frozen_coherent wins again and whether corr_frz_cen keeps rising.
2. If N confirms the flip → commit v7 (corr_frz_cen / frz_mean exit from frozen_dominant).
3. Re-examine whether the A-calibrated frozen spec is drifting at 7× scale (alt hypothesis for the
   frozen collapse).

## Related

- [[cascade v6]] — FALSIFIED at M; frozen_dominant was overfit to K/L
- [[cascade v7]] — hypothesis only (corr_frz_cen exit); needs Ring N before commit
- [[Ring L]] — frozen +8 (the fluctuation v6 overfit to); source of the ≥5-point rule v6 ignored
- [[manifold navigator]] — dynamics warning right, regime projection wrong
- [[frozen_dominant]] — premise falsified: skew>1.0 does NOT imply raw frozen optimal
- [[corr_frz_cen]] — candidate flip discriminator; centroid re-coupling at M
- [[frz_mean]] — did not saturate; still climbing at 0.606
