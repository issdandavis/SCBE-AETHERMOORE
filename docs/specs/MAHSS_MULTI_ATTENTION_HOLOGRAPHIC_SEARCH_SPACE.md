# Multi-Attention Holographic Search Space

Status: deterministic proof harness, not a trained model component.

## Purpose

Multi-Attention Holographic Search Space folds several attention mechanisms into
one queryable vector while preserving a route back to the contributing
mechanism. The proof harness lives in `python/scbe/mahss.py`.

The design target is:

- run multiple attention mechanisms in parallel,
- bind each output to a stable role vector,
- superpose the bound vectors into one holographic surface,
- apply a bounded Layer 7 style phase fold,
- unbind with the role vectors and score illumination peaks,
- emit telemetry for selected mechanism, peak margin, router entropy, and
  cross-manifold strain.

## Math Contract

For attention outputs `v_k` and role vectors `r_k`:

```text
b_k = r_k (*) v_k
s   = sum_k w_k b_k
f   = MobiusPhaseFold(s)
u_k = correlate(r_k, f)
p_k = similarity(normalize(u_k), normalize(query))
```

`(*)` is circular convolution. `correlate` is circular correlation. The router
weights `w_k` may be supplied explicitly or derived by projecting the query
onto the role vectors and applying softmax.

## Tang-Style Dequantized Sampling

MAHSS also exposes the classical bridge from Ewin Tang's dequantized
recommendation-system result: sample or route by squared vector length instead
of requiring quantum amplitude measurement. For a mechanism or candidate vector
`x_i`:

```text
P(i) = ||x_i||^2 / sum_j ||x_j||^2
```

This is implemented as `length_square_probabilities` and
`length_square_router` in `python/scbe/mahss.py`. It is not a claim of quantum
hardware behavior. It is the useful classical analogue: weighted sampling by
representation energy before the more expensive fold/unbind pass.

The exponent is configurable:

```text
P(i) = ||x_i||^alpha / sum_j ||x_j||^alpha
```

`alpha = 2` is the Tang baseline. Values such as `2.125` are pure classical
search heuristics: they sharpen exploitation without claiming quantum
equivalence.

## Adaptive Radial Power

The radial variant replaces the fixed exponent with a deterministic dial tied
to the query direction and previously explored path keys:

```text
alpha_i = clamp(
  alpha_0
  + g_r * alignment(x_i, q)
  + g_n * (novelty(x_i, history) - 0.5)
  + g_phi * (phase_phi(i, |history|) - 0.5)
  - revisit_penalty(i, history),
  alpha_min,
  alpha_max
)

P(i) = ||x_i||^alpha_i / sum_j ||x_j||^alpha_j
```

This is still pure mathematics. The phi/quasicrystal phase is a deterministic
tie-breaker, not random magic. The emitted `radial_hints` expose alignment,
redundancy, novelty, phase, exponent, and probability so a caller can stop
early after a hint and triangulate a later full run.

## Bijective Origin, Path State, and Goal

The reversible part is the vector path state, not the probability projection.
For signed/polar routing:

```text
x_pos = max(x, 0)
x_neg = max(-x, 0)
x     = x_pos - x_neg
```

This split is bijective as long as both channels are retained. It does not need
to be symmetric. It only needs to be computable in both directions between
origin, in-between path state, and goal. Once the channels are collapsed to
norms or probabilities, the result becomes telemetry/search guidance, not a
bijective representation.

## Space-Filling 1D Search Path

The repo also includes bounded Morton/Z-order primitives in
`python/scbe/space_filling.py`:

```text
index = interleave_bits(x_0, x_1, ..., x_d)
coords = deinterleave_bits(index, dims=d, bits=b)
```

This is a bijection only under a fixed dimension count and fixed bit width. It
is useful because nearby 1D indices often remain near each other in the
multi-dimensional grid, so a hierarchical search can test coarse blocks before
refining. It does not by itself prove quasilogarithmic search. The speed claim
must come from the hierarchy, cache, or pruning rule used on top of the 1D
ordering.

## Combined Algebraic Selector

The single combined selector is `algebraic_hybrid`. It keeps all pieces in one
pure algebraic scoring rule:

```text
A_i = 0.90 * R_i + 0.08 * normalize(C_i) + 0.01 * G_i + 0.01 * M_i
```

where:

- `R_i` is radial/Tang probability with adaptive exponent;
- `C_i` is constructive dissonance: mechanism spread that still aligns with the
  query;
- `G_i` is coarse group coverage so one branch does not consume the whole
  budget too early;
- `M_i` is Morton locality on the reversible bounded 1D path.

Candidate probabilities are normalized from `A_i`; the selected board is the
top budgeted set under the same score. Constructive dissonance is therefore a
pruning signal, not a replacement for radial/Tang energy. This is still a
finite-grid algorithmic heuristic, not a proof of quasilogarithmic complexity.

## SCBE Layer Mapping

| Layer | Role |
| --- | --- |
| L1-L2 | attention outputs enter as real vectors |
| L7 | bounded phase fold over the superposition |
| L9-L10 | illumination peaks and strain become telemetry |
| L13 | downstream policy may use peak margin and strain, but MAHSS itself does not decide ALLOW or DENY |

## Current Proof

The current test board uses three toy mechanisms:

- `dense_global`
- `sparse_local`
- `state_space`

The focused test asserts that a sparse-local query, with a sparse-local router
bias, selects `sparse_local` and produces a positive illumination margin.

Run:

```powershell
python -m pytest -q tests/test_mahss.py
```

## Metamaterial Simulation Hook

`scripts/experiments/mahss_metamaterial_sim.py` applies the same proof harness
to a toy auxetic metamaterial optimization problem. It compares material
variants by converting five physics-flavored views into MAHSS mechanism
vectors:

- `flow_pressure`
- `magnetic_actuation`
- `auxetic_porosity`
- `thermal_inertia`
- `abrasion_sheath`

The candidate materials are intentionally explicit: Nitinol braid, magneto-
active elastomer lattice, sacrificial Kevlar reentrant layer, TPU reentrant
lattice, and carbon PEEK high-temperature lattice. The simulator ranks
variant-plus-actuation candidates for `balanced`, `filter`, `release`, or
`high_heat` objectives and writes a JSON receipt under
`artifacts/mahss_metamaterial/`.

This is not a CFD, FEM, or materials certification model. It is a deterministic
search-space receipt that keeps the ending idea measurable: several physics
views enter as role-bound vectors, the folded space chooses an illuminated
mechanism, and the outer score ranks material variants with visible penalties
for cross-manifold strain, cost, and operating limits.

Run:

```powershell
python scripts/experiments/mahss_metamaterial_sim.py --objective balanced
python scripts/experiments/mahss_metamaterial_sim.py --objective balanced --search-mode tang_sampled --sample-budget 6
python scripts/experiments/mahss_metamaterial_sim.py --objective balanced --search-mode tang_beam --sample-budget 6
python scripts/experiments/mahss_metamaterial_sim.py --objective balanced --search-mode radial_beam --sampling-power 2.125 --sample-budget 6
python scripts/experiments/mahss_metamaterial_sim.py --objective balanced --compare --sample-budget 6 --json
python -m pytest -q tests/experiments/test_mahss_metamaterial_sim.py
```

`--search-mode tang_sampled` uses the squared-length distribution above as a
candidate preselector. The top-energy sketch is always retained, then the rest
of the budget is sampled deterministically by seed. This gives the simulator a
real speed knob for larger grids while keeping exhaustive mode available for
audits.

`--search-mode tang_beam` is the deterministic high-throughput variant: it
keeps only the top squared-energy sketches and skips random exploration.

`--search-mode radial_beam` uses the adaptive exponent above. The side-by-side
comparison harness tests it against:

- `exhaustive` — old full-grid proof mode;
- `uniform_sampled` — standard random-search baseline;
- `tang_beam_2` — fixed Tang squared-length beam;
- `tang_beam_2_125` — fixed sharpened beam;
- `radial_beam_2_125` — path-aware adaptive radial beam.
- `polar_beam_2_125` — signed positive/negative surface beam; current tests
  keep it as telemetry because it does not beat Tang on the toy grid.
- `asymmetric_well_2_125` — target-centered third-state beam where positive
  residuals pass normally and negative residuals are compressed by an
  exponential potential well.
- `morton_stride` — bounded Morton/Z-order locality traversal baseline.
- `dissonance_pruned` — constructive dissonance pruning baseline.
- `algebraic_hybrid` — one combined algebraic selector using radial, dissonance,
  coverage, and Morton locality.
- `mirror_beam_c1` — hyperbolic Poincare-ball distance beam over the same
  candidate sketches.

The comparison harness can also scale the proof board without adding random
materials:

```powershell
python scripts/experiments/mahss_metamaterial_sim.py --objective balanced --compare --sample-budget 24 --variants-per-base 20 --actuation-steps 21
```

That expands the board to 2,100 candidates with deterministic phi-phase
perturbations around the five base material families. On that larger board,
bounded Morton/Z-order traversal becomes competitive, but the confirmed
zero-regret speed improvement is still multigrid: it recovers the exhaustive
winner with fewer evaluations by scoring a coarse actuation slice first, then
refining only the top material neighborhoods. Constructive dissonance remains a
useful telemetry and pruning feature, but current tests do not show it beating
Tang/radial/Morton selectors under the same small evaluation budget.

## Next Gates

- Replace toy mechanism vectors with actual HAL attention outputs.
- Add a router experiment that compares learned weights, fixed inductive role
  vectors, and Tang-style length-square preselection.
- Feed peak margin and cross-manifold strain into a training evaluation shard,
  not directly into promotion policy.
- Replace toy metamaterial scoring constants with sourced material data before
  using the auxetic rankings for engineering claims.
