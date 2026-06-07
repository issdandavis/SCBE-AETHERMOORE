---
tags: [prime-fog, calibration, targeting, cone-reduction, methodology]
updated_at: 2026-06-05
---

# Calibration / Targeting Reframe — narrow the cone, don't "know" primes

Status: adopted as the cleaner objective (2026-06-05). Foundational measurement done;
raw-gap magnitude geometry is empirically null, LO–S residue signal is real-but-known.
Superprime-anchor hide-and-recover is now tested: same local-gap failure, different
density scale.

## The reframe

Stop hunting a row-cache axis that classifies anchors vs a shuffle null (every such
axis died — see [[null floor metric audit]]). Instead make it a **targeting/calibration**
problem:

```text
hide a known prime:  p_n -> ? -> p_{n+k}
judge the geometry by whether it reconstructs the withheld prime from nearby known
primes, narrowing the SEARCH CONE below brute force — across scale (7, 107, 1e8+).
```

Signals named: p_n, gap g_n=p_{n+1}-p_n, ratio r=p_{n+1}/p_n, curvature c=r_{n+1}/r_n,
p_n mod 30, p_n mod 210. The win is **cone reduction**, not magic knowledge.

Why cleaner: regression/interval task with a PRINCIPLED baseline (not a density-confounded
shuffle null), and it needs only the exact prime sequence (`prime_truth_oracle`) — it
sidesteps the entire row-cache graveyard.

## The honest baseline (the trap)

"Better than brute force" has a free floor that is KNOWN number theory, not our discovery.
Reducing the cone vs "all integers" re-derives the wheel and LO–S and fools us — the same
disease that killed IP/RR/the channels. The only result that counts is beating:

1. **Wheel (mod 210):** primes > 7 occupy φ(210)=48/210 = **22.9%** of integers (free).
2. **PNT/Cramér envelope:** next prime within ~ln²(p) above p_n; mean gap ~ln(p). Honest
   cone = wheel candidates inside the expected-gap window.
3. **Lemke Oliver–Soundararajan (2016):** consecutive primes ANTI-correlate in residue
   mod q. A real signal in the mod-30/210+gap space — must be subtracted to claim novelty.

**Target metric:** does our geometry narrow the corridor below `wheel + PNT + LO–S`?

## Foundational measurement (raw primes, 3 scales)

| scale | N | mean gap (ln p) | honest cone @ mid | next-gap RMSE global vs local(last3) | LO–S P(next==curr mod6) |
| --- | ---: | --- | --- | --- | --- |
| ~1e2 | 40 | 5.4 (5.3) | 2 / window 14 | 3.81 vs **4.86** (no edge) | 0.308 |
| ~1e5 | 3000 | 11.7 (11.7) | 16 / window 68 | 9.23 vs **10.95** (no edge) | 0.409 |
| ~1e8 | 4000 | 18.4 (18.4) | 38 / window 168 | 16.53 vs **19.36** (no edge) | 0.439 |

Findings:
- **Honest cone is already tiny** (~38 wheel candidates at 1e8). Wheel+PNT do almost all
  the cone reduction for free; mean gap = ln(p) to the decimal (PNT exact).
- **Gap-magnitude trajectory is empirically null.** Local mean of last-3 gaps predicts the
  next gap WORSE than the global mean, out-of-sample, at every scale. Consecutive gap
  magnitudes are ~uncorrelated beyond PNT — the "curvature bridge points to the next prime"
  idea, in raw-magnitude form, isn't there to ride.
- **LO–S anti-correlation is real but known.** P(next==curr class mod 6) < 0.5 at all scales,
  decaying toward 0.5 with scale, exactly as the literature gives. The only live conditioning
  signal in this space is known number theory.

## Superprime-anchor measurement (P(P(n)) for prime n)

Durable probe:

`scripts/research/run_prime_calibration_targeting_probe.py`

Run:

```powershell
python scripts\research\run_prime_calibration_targeting_probe.py --mode superprime --limit 100000000 --scales 100,100000,100000000 --counts 40,3000,4000 --out-dir artifacts\prime_calibration_targeting_probe
```

Artifact:

`artifacts/prime_calibration_targeting_probe/superprime_latest.md`

Generated sequence count: 33,666 exact `p_{p_n}` values for prime `n`, no row cache.

| scale | N | mean gap | PNT cone hit rate | empirical cone @ mid | next-gap RMSE global vs local(last3) | same mod6 |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| ~1e2 | 40 | 239.3 | 0.000 | 127 | 168.05 vs **169.09** (no edge) | 0.513 |
| ~1e5 | 3000 | 1603.9 | 0.006 | 953 | 1282.16 vs **1466.14** (no edge) | 0.491 |
| ~1e8 | 4000 | 3659.4 | 0.006 | 2231 | 3050.22 vs **3553.19** (no edge) | 0.499 |

Findings:
- **Different density scale:** raw-prime PNT windows are far too narrow for the
  `P(P(n))` anchor sequence. At ~1e8, the raw PNT half-log² cone has only 39 wheel
  candidates and captures ~0.6% of next anchors.
- **Gap-magnitude trajectory is still empirically null:** local last-3 gap means are
  worse than a rolling global mean at all scales. Lag-1 gap correlation is near zero
  or slightly negative.
- **Residue transition is not the raw-prime LO–S lever:** same-mod6 sits near 0.5
  for the superprime-anchor sequence. The raw-prime anti-correlation does not carry
  over as an obvious targeting edge here.

Conclusion: the reframe survives as the right objective, but the specific "follow
local gap curvature" idea is dead on both raw primes and the actual `P(P(n))`
anchor sequence. The baseline for `P(P(n))` must be an empirical sequence-density
cone, not raw-prime PNT.

### Joint multi-feature steelman (2026-06-05) — confirms null, with a trap caught

The single-feature probe above used only last-3 gap magnitude. The reframe named
OVERLAPPING signals (gap, ratio, curvature, mod30, mod210), so the fair close is a
JOINT held-out predictor. Durable reproduction:

```powershell
python scripts\research\run_prime_calibration_targeting_probe.py --density-control-steelman --index-limit 1500000 --out-dir artifacts\prime_calibration_targeting_probe
```

Artifact:

`artifacts/prime_calibration_targeting_probe/superprime_density_control_latest.md`

Ridge least-squares, time-ordered 70/30 split (no shuffle, no leakage), inner
index cutoff `P(n) <= 1.5M`: 10,801 sequence values, 10,797 usable next-gap rows,
test n=3,240. Target = next gap in the `P(P(n))` sequence. Value range: 5 to
23,874,601.

| model (out-of-sample RMSE) | RMSE | delta vs density |
| --- | ---: | ---: |
| flat global mean (WRONG baseline) | 2315.64 | — |
| **density only `[1, log p]` (honest baseline)** | **2210.81** | 0.00 |
| density + ALL local feats (gaps+curv+mod30+mod210) | 2208.33 | -2.48 |
| density + local gaps only | 2207.55 | -3.26 |
| density + residue phase only | 2211.34 | +0.52 |
| local geometry without density | 2305.01 | +94.19 |

**TRAP CAUGHT:** the full model looks like it "beats baselines" if compared to the
flat mean (2208.33 vs 2315.64), but that edge is PNT/density drift. With a
time-ordered split the test set is the larger-`p` tail, so a flat mean
under-predicts and any `log p` term "wins". Against the HONEST density baseline
(2210.81), all local geometry together adds **0.11%** (→2208.33); local gaps add
**0.15%** (→2207.55); residue is worse. That is not enough to credit the
named local geometry as a new targeting law.

**Reusable lesson:** when the train/test split is time-ordered over a sequence with a
density trend, the baseline MUST be the trend (PNT / `log p`), never a flat mean —
otherwise the model "discovers" PNT and you call it signal. Same flat-baseline disease
as the value-shuffle null in [[null floor metric audit]]; control for the known
structure before crediting the new feature. **The joint local-geometry hypothesis is
now closed on P(P(n)).**

## Forks closed (2026-06-05)

### Residue-lane ranking — NULL on every modulus

Tested whether conditioning on the current mod-M wheel lane narrows the next-lane
corridor (lower held-out conditional entropy) vs the empirical wheel-marginal baseline.
Superprime anchors ≤ 3M (19,349 anchors), time-ordered 70/30, Laplace-smoothed
transition matrix, test n=5804:

| modulus | wheel lanes | uniform | empirical marginal | conditional-on-lane |
| ---: | ---: | ---: | ---: | ---: |
| 6 | 2 | 1.000 | 1.000 | 1.000 (no narrowing) |
| 30 | 8 | 3.000 | 3.001 | 3.002 (worse = overfit) |
| 210 | 48 | 5.585 | 5.587 | 5.627 (worse: 49.4 eff lanes) |

Two honest facts: (a) the wheel lanes are **uniformly occupied** (marginal within 0.002
bits of uniform — all 48 mod-210 lanes equiprobable), and (b) they are **serially
independent** (conditioning adds nothing held-out; slightly negative = noise). The raw-prime
LO–S residue anti-correlation **does not appear at all** in the P(P(n)) sequence.

### Landing

Both forks the reframe had are now dead: local gap-trajectory geometry (even joint
multi-feature, density-controlled: +0.24%) AND residue-lane ranking (uniform + independent).
**For P(P(n)), the search cone IS the density envelope; neither gap geometry nor residue
lanes narrow it below the empirical density window.** The targeting/calibration reframe was
the right way to ASK, and it returns a clean, multi-pronged negative: no sub-density aiming
signal exists at the local-conditioning level. This converges with the ring-gating side
([[null floor metric audit]]): frozen-plus-density is the floor from BOTH directions.

### Long-range / spectral fork — also closed (2026-06-05)

The one structurally different attack (non-local, not conditioning): does the detrended
gap sequence have periodicity or long-range correlation? Detrended by centered MA(201)
divide; superprime anchors ≤ 3M (N=19,148 residuals).

- **Periodogram max-statistic test (vs 200 shuffle surrogates): NULL.** Real max power
  111k vs shuffle p95 150k, p=0.655. No periodicity; spectrally flat.
- **Autocorrelation: one REAL effect — gap repulsion.** Lag-1 ACF = −0.078, beyond the
  MA-artifact band (a faithful surrogate — same density trend, i.i.d. fluctuations, identical
  detrend pipeline — induces only −0.005). Lags 2,3,5 also real-negative. Gaps repel: a large
  gap tends to be followed by a smaller one.
- **But it's KNOWN, general, and negligible.** Raw primes show the same repulsion under the
  identical pipeline (lag-1 −0.059 @1e6, −0.040 @1e8) — it's a general prime-gap property,
  not special to superprimes, and it **decays with scale**. Lag-1 R² ≈ 0.6% (superprime),
  0.16–0.35% (raw) — explains <1% of gap variance, matching the ridge's +0.15% local-gap
  edge. It does NOT narrow the targeting cone.

So the long-range fork adds no exploitable structure: no periodicity, and the only real
serial correlation is the known, scale-decaying, sub-1%-variance gap repulsion.

Still untested (very low prior): higher-order lane history (last-k lanes), joint lane×gap
interactions. Given first-order lane is dead-uniform, gaps are density-only, and the spectrum
is flat, the prior that these survive is negligible.

### Why "flat" — and the rotated (log) frame (2026-06-05)

Recurring question: "we KNOW the primes, so why can't the geometry find them?" Answer:
**flat = locally pseudorandom, NOT unfindable.** We find every prime exactly with the
sieve (global arithmetic over all smaller primes). What's absent is a *local-geometry
compression* that beats the sieve. Knowing a value ≠ that value being predictable from a
few recent values — cf. knowing every digit of π while digit n+1 stays locally
unpredictable (Cramér: primes are deterministic, globally density-structured, locally
pseudorandom).

**The structure IS there — in the log frame, as the Riemann zeros.** The linear gap
spectrum is flat because the structure isn't one period in linear n; it's a dense comb of
incommensurate frequencies (the zeros' γ) in log x. Demonstrated: `S(t) = -Σ_{p≤1e5}
(log p) p^{-1/2} cos(t log p)` has peaks at the first zeros — **5/6 of γ =
{14.13, 21.02, 25.01, 30.43, 32.94, 37.59} recovered within 0.5** from our own prime list.
Same primes, linear axis: no dominant period.

Two hard limits on this (why it does NOT reopen the second-lane search):
1. It's KNOWN structure (the explicit formula / "music of the primes") — rediscovering it
   is not a new lane, same discipline as wheel/PNT/LO–S.
2. It does NOT shortcut targeting: the explicit formula needs ALL (infinitely many) zeros
   to reconstruct primes. Zeros let you smoothly COUNT primes; they never cheaply predict
   the NEXT gap locally.

**Does `π(π(x))` have its own comb? — RESOLVED: no (2026-06-05).** Ran the proper
Gaussian-windowed log-spectrum (taper kills the Δt=2π/logX≈0.43 cutoff ringing that
contaminated the naive probe), X=1.5e7, 76k superprimes, with the RIGHT statistic +
a real null:

| sequence | localization = power(at γ)/power(off γ) | gap-shuffle null p95 | verdict |
| --- | ---: | ---: | --- |
| raw primes (positive control) | **15.63×** | 1.62 | COMB — beats null (detector validated) |
| superprimes `π(π(x))` | **1.21×** | 1.51 | NO comb — within null |

Raw primes localize 15.6× of spectral power exactly at the first ten ζ zeros (textbook
comb, validated). Superprimes localize 1.21×, inside the null — no inherited ζ comb, no
novel comb, nothing above a gap-shuffled surrogate at this scale. (Cannot prove a weak
inherited comb is absent below the sparse-sequence floor; none is detectable.)

**Method note (reusable):** to test for a spectral comb, the honest statistic is the
**localization ratio (power at targets / power off targets) vs a gap-shuffle null**, NOT
a per-frequency p95 (which is too noisy — the gap-shuffle null retains density and
fluctuates at the targets, so raw primes "failed" 0/10 per-point despite a 15.6× comb).
And ALWAYS window/taper a finite log-sum or the 2π/logX cutoff ringing fabricates a dense
peak comb that "matches" anything.

### Frame rotation as an unsticking tool (reference)

When a signal looks dead/flat in its natural coordinates, **try a rotated frame before
concluding "nothing there."** Demonstrated here: the prime gap sequence is flat in the
LINEAR axis but its structure (the ζ zeros) appears under the LOG-frame transform. The
rotation revealed real structure that the linear view hid.

But the discipline still applies in the rotated frame — rotation reveals, it does not
license:
1. **Still null-check.** The rotated view produced a fake "10/10 zeros" comb until a
   gap-shuffle null + localization ratio killed it for superprimes. A peak in a new frame
   is not signal until it beats a structure-matched null IN that frame.
2. **Known ≠ novel.** The log frame recovered the *known* ζ zeros — real, but not a new
   lane. Ask whether the rotated structure is already-known number theory.
3. **Revealing ≠ exploitable.** Even real rotated-frame structure (the zeros) need not
   give what you want (local targeting). Separate "is there structure" from "does it do
   the job."

Candidate rotations to keep on the shelf for stuck problems: linear→log (scale/PNT),
value→residue (mod-q wheel), sequence→spectrum (FFT/periodogram), time-order→circular-shift
(autocorrelation-preserving null), raw→density-detrended (remove the known trend first).

## Related
- [[null floor metric audit]] — why the old anchor-vs-shuffle metric was the wrong objective
- [[inverse bridge map]] / [[manifold navigator]] — trajectory tools that now get a real metric
- [[prime truth oracle]] — exact prime sequence generator this harness rides on
