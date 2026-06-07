---
tags: [prime-fog, pre-registration, ring-O, discriminator]
updated_at: 2026-06-04
---

# Ring O Pre-Registration (document BEFORE unblinding)

The frozen → frozen_coherent flip across K/L/M/N. Goal: make Ring O a true
out-of-sample discriminator, not a fit target. Hypotheses and their falsifiers
are frozen here before O is built.

## The four transition points

| Ring | frz_mean | frz_std | frz_skew | frz_kurt | corr_frz_cen | winner |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| K | 0.5062 | 0.8036 | 1.0328 | 1.0224 | −0.226 | frozen (+1, marginal) |
| L | 0.5306 | 0.7853 | 1.1867 | 1.5965 | −0.221 | frozen (+8, strong) |
| M | 0.6060 | 0.7701 | 1.1673 | 1.6152 | −0.159 | coherent (frozen LAST) |
| N | 0.6238 | 0.7283 | 1.0775 | 1.2753 | −0.202 | coherent |

## Separation analysis (frozen {K,L} vs coherent {M,N})

| variable | frozen range | coherent range | clean split? | margin |
| --- | --- | --- | --- | ---: |
| frz_mean | [0.506, 0.531] | [0.606, 0.624] | YES | 0.075 |
| frz_std | [0.785, 0.804] | [0.728, 0.770] | YES (inverse) | 0.015 |
| corr_frz_cen | [−0.226, −0.221] | [−0.202, −0.159] | YES | 0.019 |
| frz_skew | [1.033, 1.187] | [1.077, 1.167] | **NO (overlap)** | 0.000 |
| frz_kurt | [1.022, 1.597] | [1.275, 1.615] | **NO (overlap)** | 0.000 |

## THE CONFOUND (the headline finding)

frz_mean and frz_std are **monotonic** across K→N:
- frz_mean steps: +0.024, +0.075, +0.018 (always up)
- frz_std steps: −0.018, −0.015, −0.042 (always down)

**Any monotonic variable separates an early-vs-late split trivially.** That frz_mean
"cleanly separates" with margin 0.075 is NOT causal evidence — it is confounded with
"deeper into the sequence." H1 (fixed pocket) and H2 (density saturation) both rest on
frz_mean as the driver, and neither can be established with monotonic data.

The non-monotonic (non-confounded, informative) variables are skew, kurt, corr:
- frz_skew steps: +0.154, −0.019, −0.090 — **peaked at L, falling since**
- frz_kurt steps: +0.574, +0.019, −0.340 — **peaked at M, falling at N**

## Hypothesis verdicts (from existing data, before Ring O)

- **H3 (kurtosis/variance level): FALSIFIED.** frz_kurt and frz_skew LEVELS do not
  separate the winners (margin 0.000). L (frozen) kurt=1.597 ≈ M (coherent) kurt=1.615;
  N (coherent) kurt=1.275 is BELOW L (frozen). No threshold works. (Note: the period-2
  kurt model was already falsified at Ring L — it was never a frozen/coherent driver.)
- **H1 ≡ H2: same model, confounded.** Both are mean-band/pocket models. They make
  IDENTICAL predictions on all four points and differ only on reversibility — untested,
  because frz_mean only ever climbs. Treat as one "mean-pocket" hypothesis, confounded.
- **H4 (derivative / turning-point): the only non-confounded hypothesis.** The flip
  (L→M) coincides exactly with the skew/kurt PEAK rolling over and with the manifold
  navigator's trajectory-speed collapse (K→L 0.596 → L→M ~0.085). Mechanism: frozen wins
  while the concentration spike is still GROWING; coherent wins once it rolls over, even
  though frz_skew is still > 1.0. Uses the non-confounded (non-monotonic) information.

## Ring O is a discriminator ONLY if it breaks monotonicity

If O continues the trend (frz_mean up ~0.64, frz_skew down ~1.0), then mean-pocket
(H1/H2) AND H4 BOTH predict coherent — non-discriminating, we learn nothing.

Pre-registered falsifiers (frozen before unblinding O):

1. **O frz_mean reverts < 0.55 AND coherent wins** → mean-pocket FALSIFIED; the flip is
   a permanent structural shift, not a reversible band.
2. **O frz_mean reverts < 0.55 AND frozen wins** → consistent with mean-pocket (back in band).
3. **O frz_mean stays high (>0.57) BUT frz_skew RE-RISES AND frozen wins** → H4 (derivative)
   CONFIRMED over mean-pocket; it is the spike direction, not the mean level, that flips it.
4. **O frz_mean stays high AND frz_skew keeps falling AND coherent wins** → consistent with
   BOTH mean-pocket and H4 (non-discriminating; the common case).

The ring we WANT (to break the confound) is one where frz_mean and frz_skew-direction
DISAGREE. We can't choose it, but we can recognize and exploit it if it appears.

## Decision rule for v7 (still UNCOMMITTED)

Do not commit any v7 exit on K/L/M/N alone (4 points, 1 transition, confounded). v7 earns
a commit only after a ring that breaks monotonicity confirms mean-level vs spike-derivative.

## Related

- [[Ring M]] — first frozen collapse; the turning point
- [[Ring N]] — confirmed the flip (coherent 13/180)
- [[manifold navigator]] — the speed collapse that coincides with the spike rollover
- [[cascade v7]] — uncommitted; this note is its pre-registration discipline
- [[frozen_dominant overfit]] — why we do not fit thresholds to 4 confounded points
