---
tags: [prime-fog, ring, consumed]
updated_at: 2026-06-04
---

# Ring L — 650M to 700M

**Status: CONSUMED — period-2 alternation FALSIFIED; v6 frozen_dominant CONFIRMED (strong)**

## Two hypotheses tested blind

| Hypothesis | Prediction | Result |
| --- | --- | --- |
| **H1: frz_kurt period-2 alternation** | L low (<0.80) → magnitude | **FALSIFIED** — L=1.597 (high) |
| **H2: v6 frozen_dominant** | frz_skew>1.0 → frozen wins | **CONFIRMED** — frozen 13/178, blends 5–6 |

The ring was NOT discriminating (both conditions did not hold) — H1's premise (low kurt) failed outright, so v5 and v6 agreed on "not magnitude." But the *margin* is the story.

## Actual features

| Feature | K | L (actual) | Direction |
| --- | ---: | ---: | --- |
| frz_mean | 0.5062 | 0.5306 | up, but step collapsed (+0.024) |
| frz_std | 0.8036 | 0.7853 | down — concentration deepening |
| frz_skew | 1.0328 | **1.1867** | up hard — super-skew growing |
| frz_kurt | 1.0224 | **1.5965** | up hard — NOT oscillating |
| cen_std | 1.0583 | 1.0310 | stable above threshold |

All four frozen-distribution moments move the same way: **mean↑, skew↑, kurt↑, std↓**. This is one coherent direction — a concentration phase transition, not oscillation.

## Results

| Method | Hits | Delta |
| --- | ---: | ---: |
| **frozen baseline** | **13/178** | — |
| dominant (wf=-1.5, wa=0) | 5/178 | **−8** |
| magnitude (wf=+0.5, wa=2) | 6/178 | **−7** |
| frozen_coherent | 5/178 | −8 |
| v5 committed (dominant) | 5/178 | **−8** |

**Frozen wins by the largest margin yet (+8 over every blend).** At K it was +1; at L it is +8. The frozen-dominant regime is deepening, not stabilizing.

## Cascade v6 was PRE-REGISTERED before L — this is a true blind pass

v6 was frozen in `cascade_v6_spec.json` after Ring K, with `next_test: L, unseen_anchor_boundary`. Ring L is therefore v6's **pre-registered blind validation**, not a post-hoc fit.

v6 order-1 rule: `frz_mean > 0.45 AND frz_skew > 1.0 → frozen_dominant (w_f=1.0, w_a=0, w_c=0)`.
At L: frz_mean=0.5306 ✓, frz_skew=1.1867 ✓ → fires.

**Key identity**: frozen_dominant weights (1.0, 0, 0) reduce `dyn_blend = wf·f + wa·|f| + wc·c` to exactly `f` — the raw frozen z-score. So **frozen_dominant IS the frozen baseline.** The "frozen 13/178" winner is precisely v6 order-1's output.

| Cascade | L prediction | L hits | Correct? |
| --- | --- | ---: | --- |
| v5 (committed earlier) | dominant (kurt≥0.80) | 5/178 | regime-label only; scorer −8 |
| **v6 (frozen pre-L)** | **frozen_dominant** | **13/178** | **YES — blind, +8 winner** |

v6 retrodict was 4/4 (H/I/J/K); L makes it **5/5 (4 retrodict + 1 blind)**.

## Why blends hurt here (mechanism)

As frz_skew exceeds 1.0 and frz_kurt rises past 1.5, the frozen score distribution becomes a sharp spike: a small cluster of rows score very high, the bulk score near zero. The top-20 raw-frozen rows ARE the anchors. Any reweighting:
- **dominant (wf=-1.5)**: the adversarial term subtracts the frozen signal — destroys the spike
- **magnitude (wa=2.0)**: amplifies |frz| symmetrically, pulling in negative-tail noise
- **coop (wf=+1.0, wc=1.5)**: centroid term dilutes the concentrated frozen picks

In the low-skew regime (A–J) the centroid added orthogonal information. Past skew=1.0, the frozen gate alone carries nearly all the signal, and every added term is noise.

## frz_kurt — alternation was coincidence

| Ring | frz_kurt |
| --- | ---: |
| H | 0.559 |
| I | 1.035 |
| J | 0.770 |
| K | 1.022 |
| L | **1.597** |

H/I/J/K looked like low/high/low/high. L breaks it — frz_kurt jumps to 1.597. The real trend across K→L is **monotonic rise** (1.022 → 1.597). It is not a period-2 law.

**Two DIFFERENT claims must not be conflated:**

1. **frz_kurt < 0.80 threshold** (distinguishes magnitude vs dominant *within* the compressed_frozen_late band): H=0.559→mag, I=1.035→dom, J=0.770→mag. **Still 3/3.** This is what v6 keeps as orders 3–4. It is bounded to the compressed_frozen_late band (frz_std < 0.96, frz_mean 0.27–0.45, frz_skew < 1.0).

2. **frz_kurt period-2 oscillation** (my prediction mechanism for *forecasting* L's value): FALSIFIED at L.

Only claim 2 died. The v6 spec correctly scopes claim 1 below frozen_dominant: once frz_skew > 1.0 (K, L), order-1 frozen_dominant fires first and the kurt split never applies. The rising-kurt trajectory has simply left the band where the split operates.

**Lesson: 4 points is not enough to declare a *period*. Blind test on the 5th killed the oscillation forecast — but the bounded threshold it sat on is intact.**

## frz_mean — saturation finally visible

| Ring | frz_mean | Step |
| --- | ---: | ---: |
| G | 0.2152 | — |
| H | 0.3232 | +0.1080 |
| I | 0.3757 | +0.0525 |
| J | 0.4429 | +0.0672 |
| K | 0.5062 | +0.0633 |
| L | 0.5306 | **+0.0244** |

The L step (+0.024) is the first sharp deceleration since H→I. Aitken Δ² on J/K/L gives asymptote ≈ **0.546**. Prior estimates: G/H/I Aitken said 0.425 (too low, overshot), then I over-corrected to 0.60–0.65 (too high). The honest range is now **0.54–0.58**, but step noise makes any single Aitken estimate unstable — it must be recomputed each ring.

**Ring M prediction: frz_mean ≈ 0.55 ± 0.01** (near asymptote).

## Lessons

1. **v6 passed pre-registered blind test**: frozen_dominant fired on L (frz_mean>0.45, frz_skew>1.0) and frozen won +8. v6 is now 5/5 (4 retrodict + 1 blind). It was frozen BEFORE L — clean protocol.
2. **Period-2 oscillation FORECAST falsified** (claim 2): 4-point coincidence, killed at L. The bounded frz_kurt < 0.80 THRESHOLD (claim 1) survives 3/3, correctly scoped below frozen_dominant.
3. **Concentration phase transition is the real structure**: mean↑ skew↑ kurt↑ std↓, all coherent. The trajectory is leaving the blend-helps region monotonically.
4. **frz_mean saturating near 0.55**: step collapsed to +0.024. Asymptote 0.54–0.58.
5. **frozen_dominant == raw frozen gate**: weights (1,0,0) reduce to the frozen z-score. The "new regime" is really "stop blending — the gate alone is optimal once skew > 1.0."

## Next

1. **Ring M (700M–750M)**: cascade v6 committed. frozen_dominant should fire again (frz_skew likely still > 1.0). Watch whether the +8 margin holds, grows, or the regime starts to break.
2. Manifold navigator: the G→L concentration trajectory (mean↑ skew↑ kurt↑ std↓) is the cleanest smooth structure found. Embed and read Ring M direction.
3. Watch for the NEXT phase boundary: does frozen_dominant persist indefinitely, or does the distribution eventually de-concentrate and hand signal back to the blends?

## Related

- [[cascade v5]] — scorer fails here (−8); regime-label-correct only
- [[cascade v6]] — CONFIRMED 2/2 (K, L); commit as code
- [[Ring K]] — first frozen-wins (+1); L deepens it to +8
- [[trajectory gap map]] — concentration phase transition; frz_mean asymptote ≈ 0.55
- [[frz_skew]] — the robust regime trigger; >1.0 = frozen_dominant
- [[frz_kurt]] — alternation FALSIFIED; axis is rising monotonically, not period-2
- [[frozen gate]] — alone optimal in super-skew regime
