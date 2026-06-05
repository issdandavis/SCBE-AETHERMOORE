---
tags: [prime-fog, solution, trajectory, gap-map]
updated_at: 2026-06-04
---

# Trajectory Gap Map

A tool for measuring how far off-course the regime classifier is from the "line of solutions" — the known-optimal weight trajectory traced across rings A–H.

## What it does

For each ring:
1. **Feature vector**: [[frz_skew]], [[frz_mean]], [[frz_std]], [[cen_std]]
2. **Prescribed weight vector**: what the current cascade gives (wf, wa, wc)
3. **Actual best weight vector**: empirically proven winner
4. **Gap vector**: actual − prescribed in (wf, wa, wc) space

The "line of solutions" is a linear regression trained on all 8 known (feature → weight) pairs. The fitted solution line has lower residual than the discrete cascade (avg fit|gap|=0.688 vs cascade pred|gap| blowing up at H=3.0).

## Key findings (A–I)

| Ring | pred\|gap\| | Direction of error |
| --- | ---: | --- |
| A | 0.500 | +wc only |
| B | 1.118 | +wf, +wc |
| C | 0.000 | on-course |
| D | 0.000 | on-course |
| E | 0.000 | on-course |
| F | 0.000 | on-course |
| G | 0.000 | on-course |
| **H** | **3.000** | **+wf=+2, +wa=+2, +wc=+1** |
| **I** | — | v4 fired correctly, dominant won (frz_kurt=1.035) |

H's gap was entirely in the wa direction. The cascade set wa=0; the winner needed wa=2. For I, cascade v4 correctly fired (frz_mean > 0.27) but chose wrong winner — dominant took it at 11/204 vs magnitude 8/204. frz_kurt emerged as the new discriminator.

## Feature trajectory — SATURATION MODEL

The linear model worked for A–H but overshoots at I. The trajectory is **saturating** — approaching an asymptote, not moving at constant velocity.

### frz_mean (the core drift axis)

Actual values: F=0.090, G=0.215, H=0.323, I=0.376, **J=0.4429**

Step increments: F→G +0.125, G→H +0.108, H→I +0.053, **I→J +0.067** (steps NOT monotonically decelerating)

| Model | Ring J prediction | Ring J actual | Error | Asymptote |
| --- | ---: | ---: | ---: | ---: |
| Linear (r²=0.998, old) | ≈0.558 | 0.4429 | −21% | none |
| Geometric decay (r=0.486) | ≈0.401 | 0.4429 | −10% | — |
| Aitken / logistic | ≈0.410 | 0.4429 | −8% | **0.425** (underestimated) |
| Conservative (last step) | ≈0.428 | 0.4429 | −0.3% | — |

**All models undershoot Ring J.** The Aitken asymptote estimate of L≈0.4254 is already exceeded at J=0.4429. The asymptote needs upward revision.

**Ring L actual: frz_mean = 0.5306** (step +0.0244 — sharp deceleration)

Steps: +0.125, +0.108, +0.053, +0.067, +0.063, **+0.024**. The L step collapsed — first clear
saturation signal since H→I. Aitken Δ² on J/K/L gives asymptote ≈ **0.546**.

History of the estimate (a lesson in not over-correcting):
- G/H/I Aitken → 0.425 (too low; overshot at I/J/K)
- after K → over-corrected to 0.60–0.65 (too high)
- J/K/L Aitken → **0.546** (step deceleration finally visible)

Honest range: **0.54–0.58**. Step noise makes any single Aitken estimate unstable — recompute each ring.

**Ring M prediction**: frz_mean ≈ 0.55 ± 0.01 (near asymptote).

### frz_skew

Already at 0.965 in Ring I, asymptote = 1.0. Nearly saturated.

### frz_std

Declining. F=1.000, G=0.924, H=0.877, I=0.846. Step: −0.031. Asymptote unknown.

### frz_kurt (H/I/J/K/L — alternation FALSIFIED, axis is rising)

H=0.559, I=1.035, J=0.770, K=1.022, **L=1.597**.

The period-2 oscillation hypothesis (low/high/low/high) was FALSIFIED at L: predicted low (<0.80),
actual 1.597 (high). The real K→L trend is a **monotonic rise** (1.022 → 1.597). 4 points were not
enough to declare a period; the blind 5th killed it.

Two separate claims, do not conflate:
- **frz_kurt < 0.80 THRESHOLD** (magnitude vs dominant *within* compressed_frozen_late): 3/3 (H/I/J). Alive.
- **frz_kurt period-2 oscillation** (forecast mechanism): dead.

The threshold is bounded to the compressed_frozen_late band. Once frz_skew > 1.0 (K, L), the
frozen_dominant regime (v6 order-1) fires first and the kurt split never applies.

### frz_skew (the robust regime boundary — VALIDATED)

K=1.0328 (first break past 1.0), L=1.1867 (rising). When frz_skew > 1.0, the frozen distribution is
super-skewed: most rows score near zero, a small cluster scores very high. The frozen gate's top-N
IS the answer — every blend term is noise.

**Cascade v6 frozen_dominant — PRE-REGISTERED, blind PASS at L:**
Condition: frz_mean > 0.45 AND frz_skew > 1.0 → pure frozen (wf=1.0, wa=0, wc=0).
Note (1,0,0) reduces dyn_blend to the raw frozen z-score, so frozen_dominant == frozen baseline.
Validated 4/4 retrodict (H/I/J/K) + blind L (+8 margin) = 5/5.

## Ring I result — retrospect

The linear extrapolation predicted frz_mean≈0.442; actual was 0.376. The overshoot comes from using the F/G/H window average (+0.116/step) without accounting for the deceleration already visible in G→H (+0.108) vs H→I (+0.053).

The slingshot principle: a trajectory in a field has curvature. The linear model aimed past the target because it didn't model the gravitational well of the asymptote. At Ring I, the correction lands on 0.376, closer to the asymptote than the linear prediction.

## Ring J result — retrospect

The saturation model predicted 0.40–0.41; actual was 0.4429 (above). The conservative step model (+0.053) was closest. Steps are noisy — the geometric decay model's r≈0.486 doesn't hold past 2 steps. The best working assumption: steps oscillate in the range +0.05–+0.12, with frz_mean continuing upward past 0.45 toward an asymptote likely near 0.47–0.50.

Going forward: use the conservative "last step ± noise" estimate, not the Aitken formula.

## Cascade v5 (VALIDATED on H/I/J)

frz_kurt is the split axis inside compressed_frozen_late:
- frz_kurt < 0.80 → magnitude weights (H and J behavior)
- frz_kurt ≥ 0.80 → dominant (I behavior, high-kurtosis frozen distribution)

Joint condition: `compressed_frozen AND frz_mean > 0.27 AND frz_kurt < 0.80 → magnitude`

**Validated 3/3 (H, I, J). Ready to write as code.**

## Artifact

`artifacts/trajectory_gap_map/gap_map.json`  
`artifacts/trajectory_gap_map/REPORT.md`  
Script: `scripts/research/trajectory_gap_map.py`

## Related

- [[frz_mean]] — core drift axis, saturating to ~0.425
- [[frz_kurt]] — new discriminator axis (H=0.559 vs I=1.035)
- [[wa]] — the systematically missing component at H
- [[Ring H]] — the ring that exposed the cliff
- [[Ring I]] — frz_kurt revealed, dominant wins
- [[cascade v4]] — fires correctly but misclassifies I
- [[cascade v5]] — next: frz_kurt joint condition
