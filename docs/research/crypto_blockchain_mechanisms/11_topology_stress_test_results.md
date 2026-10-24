# 11 — Topology Stress Test Results

Condensed from `SCBE_Topology_Stress_Test.md` (513 lines, 30 sections). This was an
adversarial review of spec v1. Each row is an attack, its verdict, and the v2 fix.

| # | Attack on v1 | Verdict | v2 fix |
|---|---|---|---|
| 1 | IDW interpolation is accurate enough | **Broken**: bull's-eyes, no extrapolation, outlier-sensitive | RBF surface + Kriging variance (10b) |
| 2 | Venues cluster "genetically" by lineage | **Weak**: the clonal-fish result shows identical starts diverge through experience | Experiential signatures, recency-weighted (10c) |
| 3 | The projection field can fill empty regions | **Dishonest**: no geostatistics justifies it | Cross-validated radius, unknown beyond it (10d) |
| 4 | The Poincaré ball naturally encodes confidence | **Unproven**: radial order is a training outcome | Falsification test before adoption (10) |
| 5 | Route first, check health after | **Unsafe** | Baseline gate before routing (10e) |
| 6 | TDA early-warning is plug-and-play | **Partially supported**: real literature, but thresholds are data-specific | Keep it as a slow-instance signal (14), not a trigger |
| 7 | Every past break votes equally | **Dilution risk** | ExperientialSignature weighting (14) |
| 8 | Missing data = no position | **Dangerous** | NO_DATA state, fail closed (09) |

**Result:** the core idea survived (map venue state plus confidence, then route
through it). Every layer whose *estimation method* claimed more certainty than it had
was replaced. v1 is archived in `CHANGELOG.md` form; the separate
`SCBE_Topology_Archive_v1.md` was lost.
