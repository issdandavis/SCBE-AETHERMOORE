# Pyramid Constellation Manifold Map

## Purpose

The flat six-tongue compass is clean and useful, but it is only one map.
This note defines an experimental cartographic layout for comparing against the
canonical 60-degree compass rose.

The user-facing image is explorer navigation: Lewis-and-Clark-style surveying,
star bearings, field notes, fixed landmarks, and map-making discipline. A close
game-facing analogy is a Stellaris-style star map: systems, hyperlanes,
choke points, anomalies, survey status, empire borders, and route-risk overlays.
The system-facing image is a set of deterministic starting points in the
Poincare ball, offset by depth and perception axis, then braced into a pyramid
lattice.

## Core Idea

Each Sacred Tongue remains a star. Each star can be viewed through:

- a depth stratum,
- a perception axis,
- an architectural tier,
- and an optional cryptographic seed.

That creates a constellation map instead of a single flat wheel.

## Coordinates

Implemented in `src/geosealCompass.ts`:

- `pyramidConstellationPosition(...)`
- `generatePyramidConstellation(...)`
- `generatePyramidConstellationStarMap(...)`

The position uses:

- dimensions 0/1 as the circular bearing plane,
- dimension 2 as depth/pyramid height,
- dimension 3 as perception-axis bracing,
- dimension 4 as architectural taper,
- remaining dimensions reserved for future manifold signals.

## Architecture Tiers

Depth becomes architecture:

| Tier | Role |
| --- | --- |
| foundation | wide, low, stable starting layer |
| column | vertical support and repeated measurement |
| arch | narrowed bridge across perception axes |
| spire | high, focused point for precise navigation |

This lets the layout act like a built structure instead of a loose scatter plot.

## Cryptographic Seeding

The optional seed is hashed with SHA-256 over:

```text
seed | tongue | depth | perceptionAxis | tier
```

The digest produces a small deterministic angle/radius/lift perturbation. This
does not replace PQC or claim secrecy by itself. It gives repeatable,
session-bound map variation so different surveys can be compared without
hand-tuning the constellation.

## Map-Making Edges

`generatePyramidConstellationStarMap(...)` adds three trail classes:

- `tongue-bearing`: neighboring tongue stars around a ring
- `depth-line`: same tongue/axis moving through depth
- `axis-ring`: same tongue/depth moving through perception axes

Those edges make the constellation navigable. A benchmark can measure route
quality across the same task under the flat compass, golden-angle layouts, and
this pyramid constellation map.

## Stellaris-Style Reading

The constellation map can be read like a strategy star chart:

| Star-map idea | SCBE meaning |
| --- | --- |
| Star system | A tongue/depth/perception anchor |
| Hyperlane | A map edge between anchors |
| Choke point | A high-cost or low-governance edge |
| Anomaly | A drift spike, null-space event, or failed pose/route check |
| Survey status | Whether an anchor has benchmark evidence |
| Empire border | A trust region around a centroid/session/fleet |
| Wormhole/gate | A validated shortcut through a stronger governance route |
| Fog of war | Undefined space or missing perception/depth evidence |

This matters because the map is not just a visualization. It is an operational
surface. Agents should be able to survey, route, annotate, and avoid unstable
regions the way a player manages a galaxy map.

For video generation, this means:

- each pocket world is a local star system,
- each control sketch is a surveyed body,
- each repair note is an anomaly report,
- each accepted frame becomes a stable route segment,
- and each failed render stays as evidence instead of being erased.

## Next Benchmark

The next harness should compare:

1. canonical flat 60-degree compass,
2. golden-angle compass,
3. learned/corpus layout,
4. seeded pyramid constellation map.

Metrics:

- route viability,
- false allow,
- false block,
- tongue class separation,
- centroid drift stability,
- attack robustness,
- average route length through the star map.
