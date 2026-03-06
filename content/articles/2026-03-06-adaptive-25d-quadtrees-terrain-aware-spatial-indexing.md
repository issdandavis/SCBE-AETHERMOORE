# Adaptive 2.5D Quadtrees: Terrain-Aware Spatial Indexing Meets Hyperbolic Geometry

**SCBE-AETHERMOORE Technical Deep Dive -- March 2026**

What if your spatial index was smart enough to subdivide more finely in areas of high risk and stay coarse where everything is safe? That is exactly what the new `Quadtree25D` in HYDRA does. It borrows terrain-aware subdivision from GIS and game engines, then wires it into the SCBE hyperbolic geometry stack for AI governance decisions.

This article covers the core HYDRA-native `Quadtree25D` class: its variance-based subdivision, LOD system, terrain mesh generation, and DEM rasterization. The code lives in [`hydra/quadtree25d.py`](https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/hydra/quadtree25d.py), with 51 tests passing in PR [#392](https://github.com/issdandavis/SCBE-AETHERMOORE/pull/392).

## The Core Idea: Variance-Driven Subdivision

Classical quadtrees split when a node holds too many points. Our 2.5D variant adds a second trigger: **z-variance**. When the height spread inside a quad exceeds a threshold, the node splits -- even if it has few points. This means the tree automatically refines in areas of high terrain variation (read: high semantic risk) and stays coarse in flat, safe regions.

The decision logic at line 225 of `quadtree25d.py`:

```python
def _should_subdivide(self) -> Tuple[bool, SubdivisionCriterion]:
    if self.depth >= self.max_depth:
        return False, SubdivisionCriterion.NONE
    if len(self.points) > self.max_points:
        return True, SubdivisionCriterion.DENSITY
    if self.z_range > self.variance_threshold and len(self.points) > 1:
        return True, SubdivisionCriterion.VARIANCE
    return False, SubdivisionCriterion.NONE
```

Two criteria, each tracked by its own `SubdivisionCriterion` enum: `VARIANCE` (terrain-style) and `DENSITY` (classical). The stats report tells you exactly how many splits were caused by each. In the demo run, 976 points produced 1417 leaves with **428 variance-triggered splits** -- that is the tree focusing its resolution budget on the rough terrain.

## QuadPoint: 2.5D Points with Semantic Metadata

Every point carries more than coordinates. The `QuadPoint` dataclass (line 63) bundles position, Sacred Tongue assignment, authority level, and an optional intent vector:

```python
@dataclass
class QuadPoint:
    x: float
    y: float
    z: float = 0.0
    tongue: str = "KO"          # Sacred Tongue (KO/AV/RU/CA/UM/DR)
    authority: str = "public"   # governance level
    intent_vector: Optional[List[float]] = None
    payload: Optional[Dict[str, Any]] = None
    point_id: str = ""          # auto-generated BLAKE2s hash
```

The `tongue_weight` property pulls from `TONGUE_WEIGHTS` (golden-ratio scaled: KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09). When the terrain mesh is built, the **dominant tongue per leaf** is determined by weighted vote across all points in that cell. Higher-weight tongues (like DR at 11.09x) carry disproportionate influence -- a single DR-tagged point in a leaf full of KO points will still dominate.

## Level of Detail: Camera-Aware Node Selection

The LOD system (line 456) implements standard screen-space geometric error. Given a camera position and FOV, it traverses the tree and selects the coarsest nodes that satisfy a maximum pixel-error threshold:

```python
def lod_select(root, query, bias=1.0):
    selected = []
    def _traverse(node):
        dist = distance_3d(node.center, query.position)
        k = 2.0 * math.tan(query.fov_rad / 2.0) / query.viewport_height
        screen_error = (node.z_range * bias) / (dist * k)
        if node.is_leaf or screen_error <= query.max_screen_error:
            selected.append(node)
        else:
            for child in node.children.values():
                _traverse(child)
    _traverse(root)
    return selected
```

For AI governance, LOD translates to **attention budgeting**: agents far from a risk zone get coarse summaries, while agents close to the action get full-resolution data. The `LODQuery` object models viewport parameters (resolution, FOV, max screen error) that map directly onto agent attention constraints.

## Terrain Mesh Generation

Each leaf becomes two triangles (diagonal split of the quad). The mesh builder at line 389 walks all leaves, creates shared vertices at quad corners, and assigns Chladni resonance amplitudes that scale by phi^depth:

```python
def _get_or_add_vertex(x, y, z, depth, tongue):
    m, n = root.chladni_base_mode
    scale = PHI ** depth
    amp = chladni_amplitude(x, y, m * scale, n * scale)
    vertices.append(TerrainVertex(
        x=x, y=y, z=z,
        chladni_amplitude=amp,
        depth=depth, tongue=tongue,
    ))
```

The demo generates **2834 terrain triangles** from 1417 leaves. Deeper leaves produce denser mesh exactly where the terrain is roughest -- where z-variance forced subdivision. The Chladni amplitudes provide a secondary resonance signal: nodes at fractal resonance peaks are natural candidates for governance checkpoints.

## DEM Rasterization

The `to_dem_grid()` method (line 591) rasterizes the adaptive quadtree back to a regular grid -- useful for heatmap visualization or export to standard GIS tools:

```python
def to_dem_grid(self, resolution: int = 64) -> np.ndarray:
    grid = np.zeros((resolution, resolution), dtype=np.float64)
    for iy in range(resolution):
        for ix in range(resolution):
            x = b.x_min + (ix + 0.5) * dx
            y = b.y_min + (iy + 0.5) * dy
            results = self.nearest(x, y, k=1, z_weight=0.0)
            if results:
                grid[iy, ix] = results[0][0].z
    return grid
```

This nearest-neighbor interpolation preserves the adaptive structure: grid cells over rough terrain get their values from nearby fine-resolution leaves, while flat areas interpolate from coarser data.

## Synthetic Terrain Generators

Three built-in terrain functions make testing easy (lines 803-825):

- **`sine_hills`**: Overlapping sinusoidal hills with multiple frequencies
- **`ridge_terrain`**: Sharp Gaussian ridge along the diagonal, great for testing variance triggers
- **`flat_with_spikes`**: Mostly flat with three sharp Gaussian spikes -- tests extreme-variance edge cases

## How to Run

```bash
cd C:\Users\issda\SCBE-AETHERMOORE
python -m hydra.quadtree25d          # Full demo
python -m pytest tests/hydra/test_quadtree25d.py -v  # 51 tests
```

Demo output (abbreviated):
```
Inserted 976 terrain points
Quadtree stats: 1417 leaves, 428 variance splits
Terrain mesh: 2834 triangles
DEM grid (16x16): min=-3.58, max=10.00
Octree projection: 976 voxels
Lattice projection: bundles + overlap cells + lace edges
```

## What Comes Next

The octree and lattice bridges -- `project_to_octree()` and `project_to_lattice()` -- are covered in the companion article ["Bridging Game Engines and AI Safety"](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions). The full unified spatial stack (quadtree + octree + lattice + Sacred Tongues) is detailed in ["The Unified Spatial Stack"](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions).

## Links

- **PR #392**: https://github.com/issdandavis/SCBE-AETHERMOORE/pull/392
- **Prior art -- Signed Octrees**: [Discussion #376](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/376)
- **Prior art -- Quadtree-Octree Hybrid**: [Discussion #377](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/377)
- **Prior art -- Polyglot Parity**: [Discussion #378](https://github.com/issdandavis/SCBE-AETHERMOORE/discussions/378)
- **Source**: [`hydra/quadtree25d.py`](https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/hydra/quadtree25d.py)
