# Where Prime Structure Is Load-Bearing — A Map of Four Tools

> Companion to `instrument_family_for_geometric_claims.md`. Same rule: **every
> instrument ships with its own null.** This note is the synthesis of four tools
> that each asked the same question of a different "prime geometry" idea —
> *does the prime-rationing do real work, or is it decoration?* — and answered it
> by measurement, not assertion.

The recurring shape of the answer (it held all four times):

> **The vision is real every time; the prime-rationing is narrow.**
> Generic prime-rationing — prime *lengths*, *radices*, *couplings* — keeps
> testing **decorative** (it reduces to coprimality, or the work is done by
> something else). Primes earn their keep in exactly **two** narrow places:
> **(1) Fermat ANGLES → constructibility** (geometry, via Galois/cyclotomy) and
> **(2) COPRIME RESIDUES → exact carry-free computation** (CRT / RNS / NTT).

---

## The four tools

| Tool | Vision under test | Null run | Verdict |
|---|---|---|---|
| `prime_rationed_lattice.py` | sides move but lengths stay locked to prime ratios | coprime-composite set; Fermat-vs-non-Fermat; polygon inequality | lengths **decorative** (=coprimality); **Fermat angles load-bearing**; straight→curved boundary real |
| `tensor_foam_reservoir.py` | "the foam becomes the computer" | prime vs random/uniform/shuffled coupling, matched gain | foam **computes** (NMSE 0.65 vs raw 1.01); prime coupling **decorative** (≈ random) |
| `fermat_ntt_readout.py` | Fermat/NTT structure helps the readout | linear absorption; DFT-vs-random compression; exact round-trip | NTT **decorative for accuracy** (absorbed); **exactness** is the only Fermat win (cost) |
| `fermat_rns.py` | exact integer computation in the material | info-only vs guarded reconstruction; non-coprime moduli | coprime/Fermat moduli **load-bearing**; exact carry-free parallel arithmetic + detectable overflow |

---

## 1. Prime-rationed lattice — primes as moving side-lengths
- **NULL A (lengths):** "primes resist simplification" is just **coprimality**. The
  composite set `8:9:25` is equally irreducible; `6:8:10` collapses. → prime
  *lengths* are **decorative**; any pairwise-coprime set behaves identically.
- **NULL B (angles):** a regular *p*-gon is straightedge-compass constructible **iff
  p is a Fermat prime** (Gauss–Wantzel; predicate `p>2 ∧ prime ∧ (p−1) a power of
  two` → exactly `{3,5,17,257,65537}`). → Fermat *angles* are **load-bearing** and
  prime-specific. `θ = 2π·p/65537` is the right home.
- **NULL C (feasibility):** `3:5:7` closes as a triangle, `3:5:17` cannot (`17 ≥ 8`).
  → the straight→curved boundary is real; spread primes belong on arcs, not edges.

## 2. Tensor foam reservoir — does the medium compute?
- **NULL 1:** a linear readout on the foam state solves `y=u(t−2)²` (NMSE ≈ 0.65)
  where a linear readout on raw input cannot (≈ 1.01). → the **foam genuinely
  computes** (reservoir computing: fading memory + nonlinear separation).
- **NULL 2:** with connectivity, input, and spectral radius matched, prime coupling
  (0.646) ≈ random (0.677) ≈ uniform (0.673) ≈ shuffled-prime (0.681). → the prime
  coupling **pattern is decorative**; the computation comes from nonlinear dynamics
  + dimensionality + bias.
- **Design fact kept:** `tanh` is odd → cannot synthesize `u²` without a **bias**
  (nonzero operating point). A real constraint for any sense-decide-respond medium.

## 3. Fermat/NTT in the readout — accuracy vs exactness
- **Absorption (hard fact):** a linear readout absorbs any invertible linear map;
  NTT/DFT are linear, so raw-state OLS == rotated-state OLS to the digit
  (`0.663669`). → NTT-in-linear-readout buys **zero accuracy**.
- **Compression:** DFT-lowK ≈ random projection ≈ raw truncation (PCA is the
  ceiling). → spectral basis is **decorative** here (foam state has no low-freq
  structure to concentrate under random drive — untested under localized drive).
- **Exactness (the one win):** NTT mod 65537 round-trips with **0 error** vs float
  DFT `1.5e−11`, because `65536 = 2¹⁶` gives a primitive `2¹⁶`-th root of unity. →
  a **cost / hardware** property (exact integer compute), not an accuracy lever.

## 4. Fermat RNS — the exactness lever doing real work
- Integers as residues over coprime Fermat moduli `(3,5,17,257)`; add/sub/mul run
  **independently per channel** (carry-free, parallel), reconstructed via CRT.
- **Overflow is undetectable without redundancy** (x and x+M share residues). The
  big Fermat prime **65537 is the guard**: extends the recoverable range to
  `65535·65537 = (2¹⁶−1)(2¹⁶+1) = 2³²−1`, so overflow is **flagged AND the true
  result recovered exactly**. Info-only would silently mis-reconstruct (`60000 →
  −5535`).
- **Non-coprime moduli cannot reconstruct** → coprimality is genuinely load-bearing.
- Honest bound: detection holds only while `|result| ≤ M_total/2`; flagged, not
  silently trusted.

---

## The meta-lesson (for future "primes are special" claims)

A prime-specialness claim is empty until it names **which prime property** and
**which operation**. Tested across these four tools:

- **magnitude / ratio / length / radix / coupling** → reduces to **coprimality**
  (or the work is done by nonlinear dynamics); primes are **decorative** there.
- **constructible angle** → **Galois/cyclotomy**: Fermat primes only. Load-bearing.
- **exact coprime-channel arithmetic** → **CRT / RNS / NTT**: coprimality required,
  Fermat primes give clean power-of-two structure. Load-bearing (for *cost/
  exactness*, not accuracy).

Files (all `scripts/research/`, self-checking, local): `prime_rationed_lattice.py`,
`tensor_foam_reservoir.py`, `fermat_ntt_readout.py`, `fermat_rns.py`,
`nested_integer_ruler.py` (mixed-radix measurement + RNS bridge). Run each with
`PYTHONPATH=. python scripts/research/<file>`.
