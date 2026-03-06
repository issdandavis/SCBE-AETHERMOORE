# Bridging Game Engines and AI Safety: From AABB Quadtrees to Poincare Disk Projections

**SCBE-AETHERMOORE Technical Deep Dive -- March 2026**

Game engines have spent decades perfecting spatial data structures: quadtrees, octrees, BSP trees, BVH. AI safety research has spent the last few years developing hyperbolic geometry for containment and cost scaling. What happens when you wire them together?

The `AdaptiveQuadTree25D` in [`hydra/quadtree25d.py`](https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/hydra/quadtree25d.py) answers that question. It provides a classic game-engine AABB quadtree with `np.var`-based subdivision, then bridges it into HYDRA's signed octree and hyperbolic lattice through three explicit interop methods. 51 tests pass in PR [#392](https://github.com/issdandavis/SCBE-AETHERMOORE/pull/392).

## Two Quadtree Variants, One Module

The module contains two distinct implementations:

| Variant | API Style | Subdivision | Coordinates | Bridge Target |
|---------|-----------|-------------|-------------|---------------|
| `Quadtree25D` | HYDRA-native | z-range heuristic | [-1, 1] normalized | Direct octree/lattice |
| `AdaptiveQuadTree25D` | Game-engine/GIS | `np.var` statistical | AABB origin+size | Via `.to_hydra_quadtree()` |

The Grok-style `AdaptiveQuadTree25D` (line 1034) uses origin+size bounding boxes (`AABB2D`) and named quadrant children (`northwest`, `northeast`, `southwest`, `southeast`) -- the API any Unity or Godot developer would expect. Its variance check uses actual NumPy variance:

```python
def _compute_variance(self) -> float:
    if not self.points:
        return 0.0
    heights = np.array([p.z for p in self.points])
    return float(np.var(heights))
```

Compare this with the HYDRA-native `QuadNode` which uses z-range as a fast heuristic (line 216: `return self.z_max - self.z_min`). The statistical variance is more precise; the range heuristic is faster. Having both lets you pick the right tradeoff.

## Bridge 1: `.to_hydra_quadtree()` -- Coordinate Normalization

The first bridge (line 1253) converts AABB-space coordinates to the [-1, 1] normalized range that the HYDRA stack expects:

```python
def to_hydra_quadtree(self, max_depth=10, max_points=8, variance_threshold=0.5):
    qt = Quadtree25D(bounds=(-1, -1, 1, 1), max_depth=max_depth,
                     max_points=max_points, variance_threshold=variance_threshold)
    for p in self.all_points():
        nx = 2.0 * (p.x - b.x) / b.width - 1.0
        ny = 2.0 * (p.y - b.y) / b.height - 1.0
        nx = max(-0.999, min(0.999, nx))
        ny = max(-0.999, min(0.999, ny))
        qt.insert(QuadPoint(x=nx, y=ny, z=p.z))
    return qt
```

The clamping to +/-0.999 is critical -- the Poincare disk model requires all points to lie strictly inside the unit ball. Points at the boundary would have infinite hyperbolic distance, breaking the cost-scaling math.

## Bridge 2: `.project_to_octree()` -- 2D to 3D Extrusion

The octree bridge (line 618 for HYDRA-native, line 1288 for Grok variant) projects 2.5D points into full 3D signed octants. The z-height becomes the third coordinate, normalized to [-0.99, 0.99]:

```python
def project_to_octree(self, max_depth=6, chladni_mode=(3, 2)):
    octree = SignedOctree(max_depth=max_depth, chladni_mode=chladni_mode)
    z_vals = [p.z for p in all_pts]
    z_lo, z_hi = min(z_vals), max(z_vals)
    z_span = z_hi - z_lo if z_hi > z_lo else 1.0

    for pt in all_pts:
        z_norm = ((pt.z - z_lo) / z_span) * 2.0 - 1.0
        z_clamped = max(-0.99, min(0.99, z_norm * z_scale))
        octree.insert(x=pt.x, y=pt.y, z=z_clamped,
                      tongue=pt.tongue, authority=pt.authority,
                      intent_vector=list(pt.intent_vector or [0, 0, 0]),
                      create_sphere_grid=True)
    return octree
```

The Grok variant also has `to_signed_octree_direct()` (line 1217) which bypasses the HYDRA quadtree conversion and pushes points directly into octree octants. This is faster for bulk ingest but loses the HYDRA-specific metadata enrichment (tongue weighting, Chladni modes, sphere grids).

## Bridge 3: `.integrate_hyperbolic_lattice()` -- Phase Mapping

The most interesting bridge maps z-height to **phase angle** in the hyperbolic lattice's cyclic dimension (line 1172):

```python
def integrate_hyperbolic_lattice(self, lattice):
    if self.divided:
        for child in (self.northwest, self.northeast, self.southwest, self.southeast):
            if child:
                child.integrate_hyperbolic_lattice(lattice)
    elif self.points:
        avg_x = sum(p.x for p in self.points) / len(self.points)
        avg_y = sum(p.y for p in self.points) / len(self.points)
        avg_z = sum(p.z for p in self.points) / len(self.points)

        # Normalize to Poincare disk
        nx = max(-0.99, min(0.99, normalized_x * 0.95))
        ny = max(-0.99, min(0.99, normalized_y * 0.95))
        phase_rad = avg_z % (2 * math.pi)

        lattice.insert_bundle(x=nx, y=ny, phase_rad=phase_rad,
                              tongue="KO", authority="public",
                              payload={"lod_level": self.lod_level,
                                       "variance": self._compute_variance()})
```

This creates a natural mapping: terrain elevation becomes rotational phase in the lattice. High-altitude points cluster near certain phase angles; valley points cluster elsewhere. The lattice's overlap detection then automatically identifies regions where multiple altitude bands share the same (x, y) footprint -- exactly the multi-layer overlap case (buildings on terrain) from GIS literature.

The HYDRA-native `project_to_lattice()` (line 661) does the same thing but normalizes z to [0, 2pi] range rather than using modular arithmetic, giving a full-range phase sweep.

## Why This Matters for AI Safety

The game-engine front end solves three practical problems:

1. **Familiar API**: Any developer who has used a quadtree (in games, GIS, robotics, or simulation) can start working with SCBE spatial structures immediately. Insert points with AABB coordinates; the bridge handles Poincare normalization.

2. **LOD as attention budget**: The `get_lod_mesh()` method (line 1136) returns a nested structure where each cell carries its LOD level. Agents farther from a risk zone get coarser spatial summaries, reducing compute cost for low-risk assessments.

3. **Interop pipeline**: Data flows naturally from external systems (game telemetry, GIS feeds, LiDAR scans) through the AABB quadtree, into the HYDRA quadtree (normalized), then into the octree (3D sign-space) and lattice (hyperbolic distance + overlap). Each stage adds governance metadata without requiring the source system to understand SCBE internals.

## How to Run

```bash
cd C:\Users\issda\SCBE-AETHERMOORE

# Test the Grok-variant bridges
python -m pytest tests/hydra/test_quadtree25d.py -v -k "adaptive"

# Full demo (exercises both variants)
python -m hydra.quadtree25d

# Quick interactive test
python -c "
from hydra.quadtree25d import AdaptiveQuadTree25D, AABB2D, Point2D5
qt = AdaptiveQuadTree25D(AABB2D(0, 0, 100, 100), capacity=4)
for i in range(50):
    qt.insert(Point2D5(i*2, i*1.5, i*0.3))
hydra_qt = qt.to_hydra_quadtree()
octree = hydra_qt.project_to_octree(max_depth=5)
print(f'Leaves: {qt.leaf_count()}, Octree voxels: {octree.stats().get(\"count\", 0)}')
"
```

## Related Articles

- **Core Quadtree25D**: ["Adaptive 2.5D Quadtrees: Terrain-Aware Spatial Indexing"](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions) -- variance subdivision, LOD, terrain mesh, DEM
- **Full Stack**: ["The Unified Spatial Stack"](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions) -- quadtree + octree + lattice + Sacred Tongues interop matrix

## Links

- **PR #392**: https://github.com/issdandavis/SCBE-AETHERMOORE/pull/392
- **Prior art -- Signed Octrees**: [Discussion #376](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/376)
- **Prior art -- Quadtree-Octree Hybrid**: [Discussion #377](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/377)
- **Prior art -- Polyglot Parity**: [Discussion #378](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/378)
- **Source**: [`hydra/quadtree25d.py`](https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/hydra/quadtree25d.py)
