---
tags: [prime-fog, geoseed, atlas, manifold, projection, view]
updated_at: 2026-06-05
---

# Prime Manifold / Graph Projection

Status: a VIEW on the [[prime spacetime atlas]], truthful by construction.

Code: `src/geoseed/prime_manifold.py` · Tests: `tests/test_geoseed_prime_manifold.py` (7).

Embeds the multi-coordinate prime addresses into a low-dimensional space so you can
SEE which regions cluster — while keeping the atlas discipline:

- **Refuses falsified coordinates by default.** `project_manifold` only takes
  FACT / KNOWN_STRUCTURE scalars; a `FALSIFIED_PROJECTION` coordinate (curvature,
  graph_signature) raises unless `include_falsified=True`, and then the projection
  is flagged. The picture cannot be quietly built from hallucinated geometry.
- **Every axis is named.** Returns explained-variance ratio + loadings, so you
  always know what each component *is*.
- **A cluster is a hypothesis, not a path.** `alignment_vs_null` (re-exported) is
  the gate: a projected axis only counts if it clears its own circular-shift null.

## What the projection shows (it shows the closure)

| view | result | reading |
| --- | --- | --- |
| WIDE range (idx 1k–5k) | PC1 = scale (loads `log_log_value`; PC1↔`log_value` **0.93** vs null 0.73, beats) | the one real manifold axis is SCALE (PNT density) |
| NARROW window (300 primes) | PC1↔`log_value` **0.049** ≈ noise floor 0.043; explained var flat 0.33/0.29/0.25 | zoom in → featureless cloud = **the wall, made visible** |
| graph `shared_wheel_lane` | max degree 1, 3463/4000 isolated | lanes nearly unique → no spurious clustering |
| graph `shared_ap_difference` | max degree 405, 35 components | clusters on KNOWN small even differences (Green–Tao constraint), not a new lane |

So the manifold view does not reopen anything: across scales the only strong axis is
the known density gradient; locally it is the incompressible wall; the graph clusters
are known wheel/AP structure. The projection is a truthful map of the survived
structure, and it makes the wall *visible* rather than papering over it.

## Where it goes next

Remaining atlas view: the Green–Tao **AP-lattice layer** — grow the AP coordinate
into traversable progression chains as explicit straight-line paths (each chain still
gated by `alignment_vs_null` before it earns the word "path"). The seed-window region
bridge ([[prime spacetime atlas]]) and this projection are done.
