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
Tang/radial/Morton selectors under the same small evaluation budget. The
asymmetric-well beam can hit the toy-grid optimum, but the large-board test shows
it is sensitive to query-objective mismatch and should be treated as a
third-state diagnostic surface until the objective query is calibrated.

## Dual-State Keyed Search Regimes

`scripts/experiments/mahss_dual_state_keyed_search_sim.py` models paired
search over two spaces `A x B` with a hidden coupling key `M`:

```text
score(a, b) = alpha * ||a|| * ||b|| * cos(M @ a, b)
```

This separates four regimes that should not be collapsed into one headline:

| Regime | Winning method in current harness | Reason |
| --- | --- | --- |
| smooth-real | multigrid / ridge | coarse-to-fine structure preserves the basin |
| confounded-singleton | mirror resonance | norm decoys fail when resonance/contrast is required |
| strong-key-paired | polyhedral edge-walk | keyed sign-facet adjacency exposes paired solutions without full outer product |
| weak-key-paired | low-rank resonance | solution-subspace rank, not full `rank(M)`, controls recovery |

The strong-key default board is intentionally hostile to ordinary multigrid:
`multigrid_cross_c20_k6` and `multigrid_cross_c30_k10` recover `0/4`
diamonds because no one-axis coarse representative predicts the keyed pair.
Before the polyhedral pass, `tang_cross_k20` was the cheapest direct full-recall
method at 400 pair evaluations; full resonance also recovers recall but scores
the complete 6,400-pair outer product.

The new direct selector is `polyhedral_edge_k20_w4`. It rotates `A` by `M`,
normalizes both sides, assigns coordinate-hyperplane sign-facet signatures, and
walks low-Hamming-distance edge neighborhoods from high-energy seeds. It then
scores only the resulting frontier with the true amplitude function. Current
default result:

```text
polyhedral_edge_k20_w4: recall=4/4, regret=0.0, evals=140
tang_cross_k20:         recall=4/4, regret=0.0, evals=400
resonance_cross_a1:     recall=4/4, regret=0.0, evals=6400
multigrid_cross_c20_k6: recall=0/4, regret=30.70867, evals=76
```

The harness also includes literal Platonic-solid compass walks:
`polyhedral_walk_tetrahedron`, `polyhedral_walk_octahedron`,
`polyhedral_walk_cube`, `polyhedral_walk_icosahedron`, and
`polyhedral_walk_dodecahedron`. These are not the same mechanism as
`polyhedral_edge_k20_w4`. They project the joint keyed space to the top-3
singular directions and walk a bounded Platonic graph. On the default full-rank
strong-key board they are intentionally treated as negative-result probes:

```text
polyhedral_walk_tetrahedron:  recall=0/4, evals=4,  diameter=1
polyhedral_walk_octahedron:   recall=0/4, evals=6,  diameter=2
polyhedral_walk_cube:         recall=0/4, evals=8,  diameter=3
polyhedral_walk_icosahedron:  recall=0/4, evals=12, diameter=3
polyhedral_walk_dodecahedron: recall=0/4, evals=20, diameter=5
```

That negative result is useful: a 3D compass cannot recover a full-rank random
orthogonal key by itself. A separate regression constructs an intentionally
rank-3 diagonal landscape where the octahedron compass does recover the planted
pairs, so the Platonic walk remains valid as a low-dimensional diagnostic rather
than a strong-key default winner.

The harness also includes an angular phase selector, `phase_angle_k20_o7`.
This tests the case where the relation is faster to find by cyclic angle than
by linear edge adjacency. On the default full-rank strong-key board it is not
the winner:

```text
phase_angle_k20_o7: recall=1/4, regret=2.464315, evals=514
```

That is expected because the default key is a full-rank random rotation, not a
low-dimensional phase curve. A separate curved-phase regression plants pairs on
matching cyclic angles and recovers all of them with at most 8 exact
evaluations. The regime boundary is:

- full-rank keyed linear relation: use sign-facet polyhedral edge-walk;
- low-dimensional cyclic/curved relation: use phase-angle matching;
- low-rank linear relation: use low-rank resonance or Platonic compass.

The current "tangential parallelism" selector is
`polyhedral_edge_k20_w4_tangent_rescue_r4_b40`. It keeps the cheap
`polyhedral_edge_k20_w4` forward path, then launches four deterministic
tangent-plane sidecars around the keyed direction. Those sidecars run cheap
projection probes in the orthogonal slice and collapse only the best 40 rescue
pairs back into exact amplitude scoring. In cost accounting, the reported
`total_evaluations` is:

```text
total_evaluations = main_evaluations + rescue_evaluations
```

The sidecar projection count is recorded separately as `cheap_probe_count` in
the method metadata. This keeps the result honest: tangent rescue is not free,
but it does not widen the main beam into the expensive `w10` torque setting.

Constructive oscillation adds the missing bridge between those regimes. The
selector `constructive_oscillation_k8_o4_w3` alternates phase matching and
sign-facet compatibility. Its score is an inverse-Lyapunov derivative surrogate:

```text
E(pair, t) = phase_distance(pair, t) / pi + hamming_distance(pair) / d
L(pair, t) = 1 / (epsilon + E(pair, t))
vote(pair) += max(0, L(pair, t) - max_previous_L(pair))
```

This rewards pairs whose mismatch energy collapses as the phase runner advances.
On the default strong-key board it is not the cheapest method, but it is a real
speed improvement over Tang:

```text
constructive_oscillation_k8_o4_w3: recall=4/4, regret=0.0, evals=181
polyhedral_edge_k20_w4:            recall=4/4, regret=0.0, evals=140
tang_cross_k20:                    recall=4/4, regret=0.0, evals=400
```

So the current taxonomy is:

- cheapest strong-key solver: sign-facet polyhedral edge-walk;
- constructive curved/linear bridge: inverse-Lyapunov oscillation;
- pure curved-phase diagnostic: angular phase selector;
- low-rank geometric diagnostic: Platonic compass or low-rank resonance.

### Robustness Sweep Boundary

The single-board result is not enough by itself. The harness therefore includes
a seed/size sweep mode:

```powershell
python scripts/experiments/mahss_dual_state_keyed_search_sim.py --sweep --sweep-sizes 80 --sweep-seeds 50
python scripts/experiments/mahss_dual_state_keyed_search_sim.py --sweep --sweep-sizes 500,1000,2000 --sweep-seeds 3
```

Current sweep artifacts:

- `artifacts/mahss_dual_state/sweep_v1.json`
- `artifacts/mahss_dual_state/seed50_size80_sweep.json`
- `artifacts/mahss_dual_state/seed3_sizes500_1000_2000_sweep.json`
- `artifacts/mahss_dual_state/tangent_rescue_sizes500_1000_2000_seed12.json`
- `artifacts/mahss_dual_state/tangent_rescue_proof_suite_v1.json`

The `sweep_v1.json` run is the current compact authority for the 40..320
regime. It includes seed stability at n=80 over seeds 11..60 and size scaling
over n=40,80,160,320 with seeds 11..15:

```text
n=80, 50 seeds
polyhedral_edge_k20_w4:                     full_recall=50/50, evals_mean=138.68
polyhedral_edge_k20_w4_tangent_rescue_r4_b40 full_recall=50/50, evals_mean=140.68
tang_cross_k20:                             full_recall=50/50, evals_mean=400.00
resonance_cross_a1:                         full_recall=50/50, evals_mean=6400.00
constructive_oscillation                    full_recall=19/50
```

Size scaling in that same artifact:

```text
n=40:  polyhedral_edge_k20_w4 123@100%, tang_cross_k20 400@100%
n=80:  polyhedral_edge_k20_w4 138@100%, tang_cross_k20 400@100%
n=160: polyhedral_edge_k20_w4 144@100%, tang_cross_k20 400@100%
n=320: polyhedral_edge_k20_w4 150@100%, tang_cross_k20 400@100%
```

The tangent-rescue selector stays on the same cost scale in that artifact while
preserving full recall:

```text
n=40:  polyhedral_edge_k20_w4_tangent_rescue_r4_b40 125@100%
n=80:  polyhedral_edge_k20_w4_tangent_rescue_r4_b40 140@100%
n=160: polyhedral_edge_k20_w4_tangent_rescue_r4_b40 146@100%
n=320: polyhedral_edge_k20_w4_tangent_rescue_r4_b40 153@100%
```

That supports the 40..320 result: fixed `k20/w4` is a real fast setting against
the current random-orthogonal strong-key generator. The adaptive gear selector
uses `w4` below the shift threshold and `w10` above it:

```text
polyhedral_edge_gear_k20_w4_w10:
n=40  123@100%
n=80  138@100%
n=160 144@100%
n=320 380@100%
```

The larger 500..2000 smoke artifact is the stricter boundary where tangent
rescue matters. In the current 36-trial run (12 seeds at each n in
500,1000,2000), the fast `k20/w4` setting missed full planted-pair recall in
6/36 trials. The previous conservative torque settings were also not perfect in
that run:

```text
tang_cross_k20:                              full_recall=36/36, median_evals=400
polyhedral_edge_k20_w4:                      full_recall=30/36, median_evals=154
polyhedral_edge_k20_w10:                     full_recall=34/36, median_evals=390
polyhedral_edge_gear_k20_w4_w10:             full_recall=34/36, median_evals=390
polyhedral_edge_k20_w4_tangent_rescue_r4_b40 full_recall=36/36, median_evals=156
```

The defensible claim is therefore:

> Polyhedral edge-walk beats the Tang top-K baseline robustly on the n=80
> strong-key board and in the current 40..320 sweep. At larger tested sizes,
> the fast setting can miss planted-pair recall. Tangent rescue closes the
> tested 500..2000 recall hole at roughly the same cost as `w4`, giving a
> 2.56x median evaluation speedup over `tang_cross_k20` on the current
> random-orthogonal generator.

That is still a synthetic-regime claim. It has not yet been tested against
adversarially chosen keys `M`, real attention matrices, or a stronger
dequantized Tang baseline.

The packaged local proof command is:

```powershell
python scripts/experiments/mahss_tangent_rescue_proof.py --output artifacts/mahss_dual_state/tangent_rescue_proof_suite_v1.json
```

The current `tangent_rescue_proof_suite_v1.json` run covers six profiles:

```text
random_orthogonal_50seed:       250/250 full recall, median_evals=155, speedup_vs_tang=2.580645
random_orthogonal_n5000_20seed:  20/20 full recall, median_evals=160, speedup_vs_tang=2.5
identity_20seed:                 60/60 full recall, median_evals=157, speedup_vs_tang=2.547771
signed_permutation_20seed:       60/60 full recall, median_evals=156, speedup_vs_tang=2.564103
hadamard_20seed:                 60/60 full recall, median_evals=156, speedup_vs_tang=2.555937
block_rotation_20seed:           60/60 full recall, median_evals=156, speedup_vs_tang=2.555937
```

That gives 510/510 full-recall local trials for the target selector across the
current random and structured key profiles. The claim boundary remains the same:
this is a proof over this simulator's planted-pair generator, not over all
possible matrices or physical datasets.

Complex edge metrics are implemented (`phase`, `hybrid`, `weighted_hybrid`) but
are not the default winner. In the refreshed sweep, `polyhedral_edge_k20_w10`
with weighted-hybrid edges reached only 44/50 full recall at n=80 and degraded
again in the size sweep. The current gear system therefore uses Hamming facets
for both speed and torque modes while keeping complex edges as diagnostics.

The disagreement-probe accounting remains intentionally conservative. Probe
rows are re-rankers with `cost_accounting = source_plus_probe`; their
`total_evaluations` are:

```text
total_evaluations = source_evaluations + probe_evaluations
```

On the default strong-key board, the cost audit remains false for probe budget
claims because the direct polyhedral edge-walk is cheaper than the best
source-plus-probe full-recall route. This keeps the earlier misleading
"47-evaluation probe" framing impossible to ship.

## Hindsight Projection

After a search comparison, hindsight mode projects candidate **results** rather
than candidate coordinates:

```powershell
python scripts/experiments/mahss_hindsight_projection.py --objective balanced --sample-budget 24 --variants-per-base 20 --actuation-steps 21 --max-nodes 120
```

This builds a bounded three-axis graph box from:

- candidate inputs such as actuation fraction;
- objective outputs such as score, regret, porosity, force margin, and thermal
  headroom;
- internal MAHSS decisions such as peak margin, cross-manifold strain, selected
  mechanism, and illumination values;
- selector touch flags showing which search methods evaluated each candidate.

The projection uses standardized singular value decomposition over result-space
features. That gives a perpendicular hindsight view: it does not ask "where was
the candidate in the original grid?" but "where did the candidate land after all
inputs, outputs, and internal decisions were observed?" The report then flags
top-region candidates each selector missed. On the 2,100-candidate stress board,
multigrid still reaches zero regret but misses some nearby top-region points,
which makes the next improvement target explicit: keep the exact winner while
improving local top-region coverage.

The report also emits **null-space intersection vertices**. A selector's null
space is the subset of high-value/top-region candidates it did not evaluate. An
intersection vertex is a candidate where multiple selector null spaces converge.
These vertices are the clearest "hindsight 20/20" targets: they show where many
heuristics were blind at once. On the large stress board, the strongest
intersection vertices are near-optimal MAE stress variants with regret below
0.002, missed by every budgeted selector. That means the next safe improvement
is a local ridge-coverage pass around multigrid winners, not a replacement for
multigrid itself.

`multigrid_ridge_top2` implements that pass. It first runs normal multigrid,
then expands around bounded neighbor variants in the best coarse material
families and nearby actuation cells. On the current 2,100-candidate board
(`--variants-per-base 60 --actuation-steps 7`) it keeps zero regret and
improves top-region coverage:

```text
exhaustive:           regret=0.0, evals=2100
multigrid_top2:       regret=0.0, evals=312, missed_top=10
multigrid_ridge_top2: regret=0.0, evals=432, missed_top=0
```

This is the current best exact-mode tradeoff: it costs more than plain
multigrid, but it closes the null-space intersection seam while still using
about 20.6 percent of exhaustive evaluation cost. Earlier local notes cited
248/2100 evaluations; those numbers are stale for the current simulator and
should not be used as publication claims.

## Next Gates

- Replace toy mechanism vectors with actual HAL attention outputs.
- Add a router experiment that compares learned weights, fixed inductive role
  vectors, and Tang-style length-square preselection.
- Feed peak margin and cross-manifold strain into a training evaluation shard,
  not directly into promotion policy.
- Replace toy metamaterial scoring constants with sourced material data before
  using the auxetic rankings for engineering claims.
