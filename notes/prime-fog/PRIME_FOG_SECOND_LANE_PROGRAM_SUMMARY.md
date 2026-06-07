---
tags: [prime-fog, summary, closure, falsification, methodology, capstone]
updated_at: 2026-06-05
---

# Prime-Fog Second-Lane Program — Consolidated Summary

**One-line verdict:** The search for a *second* independent prediction signal beyond
`frozen` is **CLOSED**. Across every attack surface and every coordinate frame tested,
nothing beats a proper null. **Frozen + density is both the floor and the ceiling.** This
is a clean, exhaustively-falsified negative result with honest baselines — not an
unfinished search.

This doc consolidates the whole program. Detail lives in the linked notes; this is the
"read one thing" capstone.

---

## 1. The problem and the discipline

**Object:** the `P(P(n))` superprime anchor field — known-solution trajectory problem.
50M-wide rings A (100–150M) … N (750–800M) are consumed in sequence; Ring O (800–850M) is
the unseen next board. **Discipline:** reverse old rings into a rule frozen *before* the
next board; a rule is only real when it clears the next unseen ring. In-sample ceiling is
not a score.

**The central question of this program:** is there a *second* lane — any axis, feature, or
transform that locates anchors better than chance, independent of `frozen`?

---

## 2. The two-metric crisis (why most "wins" were fake)

The single most important methodological finding. The original evaluation metric —
**top-20-unique-anchor union** — is **null-saturated**: ~52–57% of rows are anchor-bearing
and each anchor spans ~18–21 rows, so a *random* pick of 20 rows catches ~10 distinct
anchors. The metric **rewards scatter and penalizes correct clustering**. Every "lane"
measured on it (IP=9, RR union, the per-ring cascade winners) was noise. See
[[null floor metric audit]].

**What survives:** the **NMS count-proxy** (de-duplicate predictions by scan-gap radius,
then precision). It does not reward scatter. Under it, `frozen` beats the null p95 on every
ring K–N — real signal — and everything else dies.

**Rule:** compare lanes only under count-matched nulls, never top-20-unique.

---

## 3. Attack surface 1 — row-cache lane gating (ALL dead but frozen)

Every candidate axis was run through the gate: `precision > null_p95 AND |count_err| ≤
30%·actual` on **every** ring, one frozen config, proper null.

| candidate / family | how it died |
| --- | --- |
| `inverse prime field` (IP=9/union 17) | density artifact, 0.9× null |
| `RR extraction lane` (rr_sqrt1) | 1.0× null at top-20; at/below null under count-proxy |
| `log_power_bridge`, `golden_spiral_phase` | anti-aligned — below their own shuffle |
| `gap_acceleration` | edge is count-inflation (over-predicts); detrend makes it worse |
| `ratio_curvature` | fails precision 3/4, count all |
| `ratio_graph_resonance` | "9/14 beats null" was a value-shuffle confound; **circular-shift null → 0/14** |
| `residue_wheel` (mod 210) | below null, count-dishonest |
| `numerical_emulsion` (factor-pressure collar) | below null, count-dishonest |
| `prime_circuit_geometry` (circle-of-fifths) | fails L/M, over-predicts every ring |
| CMPSSZ/cassette (6 channels) | best 5/14@S60 vs 4/14@S40 on **different rings** = seed-unstable noise |
| hyperbolic/topology (4 channels) | `topo_*` 0/14 (stone dead); `gravity` 1/14 |
| lambda / graph_map / ratio-depth (13 channels) | best 2/6 on regime-spanning rings = chance floor |

**`frozen` is the only null-clearing axis.** `future_*` columns are leakage (forward-looking)
and permanently disqualified. Detail: [[null floor metric audit]],
[[prime ratio transition graph]], [[geometric alignment axes]], [[residue wheel axis]],
[[numerical emulsion axis]], [[prime circuit geometry]].

---

## 4. Attack surface 2 — exact-sequence targeting reframe

Reframe (the right way to ask): stop classifying anchors vs a shuffle null; instead **hide a
known prime `p_n → ? → p_{n+k}` and ask whether geometry narrows the search cone below an
honest baseline.** Uses only the exact prime sequence (`prime_truth_oracle`) — sidesteps the
row cache entirely. Honest baseline = **wheel (mod 210, 22.9%) + PNT/Cramér window + LO–S
residue anti-correlation**; beating "all integers" just re-derives known number theory.

Results on raw primes AND the actual `P(P(n))` sequence:

- **Gap-magnitude trajectory: null.** Local last-3 gap mean predicts the next gap *worse*
  than the global mean, out-of-sample, every scale, both sequences.
- **Joint multi-feature, density-controlled: null.** Ridge with gaps+ratio+curvature+mod30+
  mod210, time-ordered held-out, adds **+0.1–0.24%** over the `log p` (PNT) baseline.
  **Flat-baseline trap caught:** vs a flat mean it looked like signal, but the edge was
  100% PNT density drift (`log p` dominant). Control for the trend, not a flat mean.
- **Residue-lane ranking: null.** Mod 6/30/210 wheel lanes are **uniform** (within 0.002
  bits) *and* **serially independent** (held-out conditional entropy ≥ marginal). The
  raw-prime LO–S anti-correlation does **not** transfer to superprimes.
- **Long-range / periodogram: flat.** No periodicity (max peak p=0.66 vs shuffle). One real
  effect — **gap repulsion** (lag-1 ACF ≈ −0.08, survives a pipeline-faithful surrogate) —
  but it is a **known, general** prime-gap property (present in raw primes, decays with
  scale), R²<1%, and does not narrow the cone.

**Conclusion:** for `P(P(n))` the search cone **is** the density envelope. Detail:
[[calibration targeting reframe]].

---

## 5. Attack surface 3 — rotated frames (the "why flat?" resolution)

"We know the primes, so why can't geometry find them?" → **flat = locally pseudorandom,
NOT unfindable.** The sieve finds every prime (global arithmetic); there is simply no
*local* compression that beats it (cf. knowing every digit of π while digit n+1 stays
locally unpredictable — the Cramér model).

The structure IS there, but in the **log frame, as the Riemann zeros**:

| sequence | windowed log-spectrum localization (power at γ / off γ) | null p95 | verdict |
| --- | ---: | ---: | --- |
| raw primes (control) | **15.63×** | 1.62 | real ζ-zero comb (detector validated) |
| superprimes `π(π(x))` | **1.21×** | 1.51 | **no comb** — within null |

Two hard limits make this **not** a reopened lane: (1) it's *known* explicit-formula
structure, and (2) it **doesn't target** — reconstructing primes needs all infinitely many
zeros; the zeros count primes globally, never cheaply predict the next local gap. The
superprime sequence carries no detectable comb of its own. Detail:
[[calibration targeting reframe]] §rotated frame.

### 5b. The wall, located — the address tower (2026-06-05)

The "why is it not a lookup?" question, resolved concretely. **Known ≠ compressible:**
primes have a short *generator* (the sieve) but no short *address* (random-access
coordinate formula). The index→value smooth address `p_n ≈ n(ln n + ln ln n − 1 + …)` is
99.98% accurate but bottoms out at an incompressible residual window.

The **decimal-place tower** (Cipolla asymptotic series, each term a finer "decimal place
of the address") separates the compressible from the wall — band p∈[1e6,1e7]:

| place | bias (mean residual) | fluctuation (std) = WALL |
| --- | ---: | ---: |
| 0 `n·ln n` | +594,949 | 281,890 |
| 1 `+ln ln n−1` | +15,522 | 7,184 |
| 2 `+(··)/ln n` | −531 | 710 |
| 3 `+(··)/ln²n` | +1,916 | 617 |
| 4 `+(··)/ln³n` | +1,535 | **536** |

Each place crushes the **bias** (predictable part: 595k → 1.5k); the **std plateaus** at
~536 = the wall. The wall sits at the `√x/ln x` Riemann-fluctuation scale and its residual
has lag-1 corr −0.045 (pattern-free — nothing left to peel). Double meaning realized: it's
an *asymptotic* series, so place 3's bias turns back up — the series' own optimal-truncation
wall lands at the same ±500–600. **The honest lookup is therefore: O(1) address tower →
~√x/ln x window → one sieve pass.** Compressible part is addressable; the wall is the zeros'
fluctuation, only closable by infinitely many places or a local sieve.

**The wall is a horizon, not a floor — the zeros are the decimals.** Pushed the tower deeper
with the actual Riemann zeros via the explicit formula `ψ(x) = x − Σ_ρ xρ/ρ − …` (each zero
pair = `2√x·cos(γ ln x − atan 2γ)/√(¼+γ²)`). Adding zeros shrinks the exact ψ-fluctuation wall
(std): 0 zeros 36.4 → 10 zeros 24.7 (68%) → 50 zeros 15.9 (**44%**). It recedes slowly
(amplitude ~`√x/γ`, so diminishing returns per zero) and closes to exact only with *all*
zeros. Two honest walls behind the receding one: (1) the decimals **never terminate**
(infinite-depth); (2) the decimals are **dual to the primes** (explicit formula runs both
ways, primes↔zeros — computing deep digits costs as much as knowing the primes). Final shape:
`prime address = smooth tower (integer part) + Riemann zeros (non-terminating, self-referential
decimals)`. "Known ≠ short lookup" because the lookup's decimal expansion *is* the primes in a
rotated coordinate.

### 5c. Two coordinate systems for the address — **log layers** and **mod layers**

The address can be peeled in two dual coordinate frames; both bottom out at the same wall.

**Log (decimal) layers** — analytic frame, precision measured in decimal digits `log10(x/wall)`,
on the exact ψ(x) fluctuation (band x∈[12k,45k], first 50 ζ zeros):

| layer | zeros | wall (resid. std) | precision (digits) |
| --- | ---: | ---: | ---: |
| smooth only | 0 | 36.36 | 2.867 |
| +zeros | 5 | 28.42 | 2.974 |
| +zeros | 13 | 23.85 | 3.050 |
| +zeros | 50 | 15.87 | 3.227 |

Residual ~ `√x/√K`, so **each additional decimal digit costs ~100× more zeros** — the layers are
logarithmically spaced in zero-count and never terminate (digits ↔ primes duality).

**Mod (residue) layers** — arithmetic frame, the primorial-wheel twin, measured in bits of
candidate mass pinned `−log₂(φ(M)/M)`:

| layer | wheel M | survive φ(M)/M | cum. bits | marginal |
| --- | --- | ---: | ---: | ---: |
| L1 | mod 2 | 0.500 | 1.000 | +1.000 |
| L2 | mod 6 | 0.333 | 1.585 | +0.585 |
| L4 | mod 210 | **0.2286** | 2.129 | +0.222 |
| L6 | mod 30030 | 0.192 | 2.382 | +0.115 |
| L9 | mod 223092870 | 0.164 | 2.612 | +0.064 |

(L4 = the 22.9% wheel baseline already used in [[calibration targeting reframe]].) Marginal bits
shrink each layer and the cumulative ceiling diverges only like `log log M` (Mertens) — the same
**receding-horizon, never-closes** shape as the log layers. And the kill-check: **within every
wheel the prime residues are exactly uniform** (mod 210 entropy 5.5849 vs max 5.5850; gap 0.0000)
— the mod layer pins the *lane*, never the prime inside it.

**Unified picture:** log layers (Riemann zeros, continuous/analytic) and mod layers (primorial
wheel, discrete/arithmetic) are two decompositions of the *same* address. Each peels a measured,
**known** fraction with diminishing returns, and both stop at the identical incompressible core —
the locally-pseudorandom wall. Neither is a free lookup; the "row × column × decimal" coordinate
exists but its deepest layer is the primes themselves.

### 5d. The scaled prime seed — the constructor face of the density floor

Rotate the same result from *"can't predict"* to *"can generate."* The two layers compose into a
compact, scale-covariant **seed** — state `(tower coefficients, primorial M, zero-count K)` — that
**regenerates the prime candidate field at any scale** from O(1) data:

- **scale** ← log layer: the smooth tower centers the address; relative placement error → 0 (this
  is just **PNT**, not a signal — labeled as such so it is never mistaken for one).
- **lanes** ← mod layer: the primorial wheel restricts to `φ(M)/M` of residues (0.2286 at mod 210).
- **window** ← the wall: a `~√x/ln x` band that one sieve pass resolves.

This is **not a new object** — it is exactly the honest lookup of §5b (`O(1) tower → √x/ln x window →
one sieve pass`), with the mod-table lane density and the zero-refined window already tabulated
above. It is a **constructor, not a predictor**: it emits the candidate *set* (the density
envelope), never the pick inside a lane (within-wheel residues are uniform, §5c). No new compute is
warranted — a measurement run would only re-derive §5b and the mod table. The value of the "seed"
framing is purely **constructive/engineering**: a deterministic, phi/primorial-scaled anchor
generator suitable as an init for a prime-anchored field — i.e. the density floor packaged as a
generator, consistent end-to-end with the second-lane closure.

### 5e. The scaling trichotomy — every divisor classified (shadow-lattice closure)

"Divide the prime path by `c`" (the rational shadow lattice / ÷7 idea) was pushed across the
whole space of `c`. Dividing by a constant is a **homothety** = a translation of the log-axis, so
it preserves the entire ratio skeleton *for any `c`* and carries **zero new information**; only the
fractional field `{p_n/c}` changes. That field partitions exhaustively three ways — verified on
primes ≤ 1e6 (`p_n/c mod 1`, KS vs U(0,1)):

| `c` | examples | `{p_n/c}` | status |
| --- | --- | --- | --- |
| shares wheel factors | 2, 6, 2/3 | spike(s) on parity/wheel classes (c=2 → all 0.5) | **known** (wheel resonance) |
| rational `a/b` (prime, non-prime, prime-ratio) | 7, 7/5, 11/7, 10/3 | finite uniform lanes = wheel mod reduced numerator (KS=(L−1)/L) | **known** (the wheel) |
| irrational (φ, √2, π, e) | φ KS 0.0023 | continuous, equidistributed | **no comb** (Vinogradov) |

There is no fourth cell (every real is rational or irrational). Integer-lattice overlap
`p_n/c ∈ ℤ` happens at ≤1 isolated point (prime `c`: only `p_n=c`; irrational `c`: never). The
single non-constant escape — the **running ratio** `p_{n+1}/p_n` — is the already-falsified
ratio-transition lane (`ratio_graph_resonance` circular-shift 0/14). **The scaling/ratio frame is
therefore exhaustively closed: the space is fully partitioned and every cell is known or null** —
not an unfinished search. Resonance only ever recovers known small-prime/wheel structure; it never
manufactures a new lane.

### 5f. Circle inscription — Fermat mod-4 boundary + Gauss-circle wall

The geometric rotation

```text
prime p -> circle x^2 + y^2 = p^2
```

also closes into known structure.

**Boundary inscription:** for odd primes, the number of integer lattice points on the circle is
exactly a mod-4 detector:

| prime class | boundary lattice points | theorem face |
| --- | ---: | --- |
| `p ≡ 1 (mod 4)` | 12 | Fermat two-squares: `p = a^2 + b^2`, so 8 non-axis points + 4 axis points |
| `p ≡ 3 (mod 4)` | 4 | only the axis points |

That is not a new lane; it is the `mod 4` wheel lane read off a circle.

**Interior inscription:** the count

```text
N(p) = #{(x,y) in Z^2 : x^2 + y^2 <= p^2}
E(p) = N(p) - pi*p^2
```

lands on the Gauss circle problem. In the measured range the discrepancy sits at the
square-root-scale wall (e.g. tens at `p≈100`, hundreds by `p≈20000`). It is bounded enough
to name the surface, but it does not provide local prime selection.

So the circle frame gives the same closure seen everywhere else:

```text
known arithmetic face + square-root fluctuation wall
```

Boundary = Fermat/mod-4 wheel. Interior = Gauss-circle discrepancy. Neither manufactures a
sub-density targeter.

---

## 6. The convergent conclusion

Two independent attacks reach the same floor:

- **Ring side:** `frozen` is genuinely real (beats null every ring); nothing beats `frozen`.
- **Sequence side:** no local feature, residue lane, spectrum, or rotated frame beats density.

**Frozen + density is floor-and-ceiling.** Therefore **Ring O is confirmation, not
discrimination** — there is no live falsifiable prediction that O could break, so the
OOM-risk 850M build is *not* justified until one is stated. The discovery question "is there
a second independent signal" is answered: **no**, with evidence that holds up.

---

## 7. Reusable methodology (the null toolkit)

The durable transferable output — how to not fool yourself:

1. **Count-matched metric.** NMS count-proxy, never top-20-unique (density-saturated).
2. **Circular-shift null** for smooth/autocorrelated scores — a value-shuffle scatters and
   over-predicts cluster count, inflating the smoother axis (killed `ratio_graph_resonance`).
3. **Density-trend baseline** (PNT / `log p`) for time-ordered splits — never a flat mean,
   or the model "discovers" the trend and you call it signal (the flat-baseline trap).
4. **Localization-ratio vs gap-shuffle null** for spectral combs — not per-frequency p95
   (too noisy; raw primes "failed" 0/10 per-point despite a 15.6× comb).
5. **Window/taper** finite log-sums — a sharp cutoff fabricates a dense fake comb (Δt=2π/logX).
6. **Proper permutation null:** `random.Random(seed).shuffle`, never `(i*M)%n` (collides
   unless gcd=1). Report null mean AND p95; clear p95 on every ring.
7. **Frame rotation as an unsticking tool:** when flat in natural coords, try a rotated frame
   (linear→log, value→residue, seq→spectrum, time→circular-shift, raw→detrended) — but still
   null-check *in* the new frame, and separate revealing / known / exploitable.
8. **The gate, restated:** known truth → relationship → candidate axis → null gate → lane
   status. Alignment in-sample is a hypothesis; the gate decides if it has mass.

---

## 8. What remains open

Nothing for *targeting*. The only residual is a pure-math curiosity, now **resolved
negative**: `π(π(x))` shows no spectral comb of its own (§5). If revisited it is a
structural write-up note, never evidence that the second lane reopened.

To reopen the search, a candidate must *first* state which honest baseline it beats and
which null falsifies it — before any compute is spent.

---

## Related
- [[second lane closure]] — the decision record
- [[null floor metric audit]] — the metric crisis + most falsifications
- [[calibration targeting reframe]] — the exact-sequence + rotated-frame work
- [[prime ratio transition graph]] — circular-shift null worked example
- [[anchor count proxy]] — the surviving metric
- [[frozen gate]] — the one real axis
- [[Ring O pre-registration]] — confirmation-only; needs a falsifiable prediction first
