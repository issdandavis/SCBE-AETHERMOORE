---
tags: [prime-fog, geoseed, atlas, constructor, green-tao, truth-map]
updated_at: 2026-06-05
---

# Prime Spacetime Atlas

Status: constructor-side truth map. The map you build BEFORE the pathfinder flies.

Mission restated (the real goal all along): not a magic prime solver — a **truthful
coordinate system over known primes**, where each prime has an address from value,
index, gap, residue, ratio, log scale, wheel lane, and AP (straight-line) position.
Then use that atlas to see which paths through number-space are real and which are
hallucinated geometry.

Code: `src/geoseed/prime_atlas.py` · Tests: `tests/test_geoseed_prime_atlas.py` (7).
Companion (ring-anchor side): `scripts/research/prime_alignment_ledger.py`.
Constructor (window): [[geoseed prime seed init]].

## Truthful by construction

Every coordinate the atlas records carries its epistemic **verdict** in
`COORDINATE_STATUS`, enforced by a test (no coordinate may be unclassified):

| status | coordinates | meaning |
| --- | --- | --- |
| `FACT` | value, index, gap_prev/next, ratio_prev/next, residues | exact integer property; recording never overfits |
| `KNOWN_STRUCTURE` | log_value, log_log_value, wheel_lane, **ap_length, ap_difference** | alignment that SURVIVED a proper null |
| `FALSIFIED_PROJECTION` | curvature, graph_signature | computable but proven NON-predictive by the gates |

The falsified coordinates are kept on purpose: the map must *show* you the
hallucinated geometry (ratio curvature, the gap-transition graph — both died under
the count-honest nulls) rather than silently omit it. A path that navigates by a
`FALSIFIED_PROJECTION` is flying through hallucinated territory by definition.

## CLI lookup aggregates are facts, not lanes

The GeoSeal CLI `prime-atlas` command also reports helper aggregates:

- `global_prime_composite_balance` (`pi(x)`, composite count, `pi/C`)
- `prime_composite_phase` (finite-window `P/NP`, phase balance, PNT residual)
- `small_factor_pressure` (small residue-prime divisibility inside the phase window)

These are **FACT_AGGREGATE** fields, not new `PrimeAddress` coordinates and not
`KNOWN_STRUCTURE` claims. Recording them does not need a null because they are exact
counts/ratios over known integers. The null gate attaches only when someone claims
one of these fields separates, predicts, ranks, or routes better than a baseline.

This keeps the [[numerical emulsion axis]] result intact: the old factor-pressure
collar failed as a standalone search lane, while the new CLI fields are simply a
truth-map readout of the local prime/composite environment.

## Green–Tao as the straight-line coordinate

Green–Tao: the primes contain arbitrarily long arithmetic progressions even though
their density → 0. That is the "spacetime" payoff — **sparse space, guaranteed
straight lines under the AP coordinate rule.** `prime_ap_through(value, is_prime)`
records the longest prime AP through each prime (even common difference required;
divisible by primorials for longer APs). It is a real KNOWN_STRUCTURE view, unlike
the falsified gap/ratio graph.

## The real-vs-hallucinated test, as a first-class operation

`alignment_vs_null(signal, target, null="circular_shift")` is baked in: a projection
is only a "real path" if it clears its own null on this object. The default is the
**circular-shift** null (count-matched for smooth scores — the one that killed
`ratio_graph_resonance`), not a value-shuffle. The atlas cannot report an alignment
without the correct null available.

## Seed-window region query

`build_prime_seed_region(index)` now wires the [[geoseed prime seed init]] window
into the atlas.

Flow:

```text
prime index -> proven seed bracket -> exact known primes inside window -> atlas addresses -> nearby survived structures
```

This is still constructor-side. It does not choose the target prime. It answers:

```text
inside this guaranteed candidate field, what known structures are nearby?
```

Example at `n=10000`:

| Field | Value |
| --- | ---: |
| seed window | `[104306, 114307]` |
| exact known primes in window | 856 |
| target value | 104729 |
| target inside window | yes |
| twin-neighbor structures | 194 |
| cousin-neighbor structures | 212 |
| sexy-neighbor structures | 276 |

The function has an explicit `max_sieve_limit` guard so a region view cannot
accidentally trigger a giant sieve. Raise it knowingly for larger local atlases.

## Where it goes next

The address record is the substrate. Open views to build ON it (each must clear the
baked-in null before it becomes a "path"): graph/manifold projection of the address
space and AP-lattice (Green–Tao) layer expansion. The seed-window region query is
now wired. None of these reopen the second-lane search — they are constructor views
over the survived structure only.
