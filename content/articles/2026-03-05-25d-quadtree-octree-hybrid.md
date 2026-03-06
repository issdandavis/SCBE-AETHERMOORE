# 2.5D Quadtree-Octree Hybrid: Adaptive Terrain Storage for Semantic Documents

**Issac Daniel Davis** | SCBE-AETHERMOORE Project | 2026-03-05

## Abstract

We describe a 2.5D hybrid data structure that bridges flat semantic document space with a cyclic depth dimension, combining quadtree-like 2D lattice indexing with octree-compatible 3D projection. Documents are positioned on a toroidally-wrapped planar grid and assigned a cyclic phase angle that controls their "elevation" in the third dimension. The phase is projected via `z = sin(phase) * 0.98` into a signed-axis octree, enabling reuse of existing 3D spatial queries, mirror operations, and fractal Chladni addressing. The structure supports overlap-aware cells, hyperbolic 2D distance (Poincare disk metric), cyclic phase distance, and six-tongue semantic weighting via golden ratio phi-scaled metrics. We present the design, implementation, and applications to semantic document retrieval, terrain-like LOD rendering, and adaptive governance workflows.

## 1. Introduction

The term "2.5D" appears across multiple fields:

- **Game development**: Isometric engines (SimCity, Diablo) that render 3D scenes on 2D planes with height.
- **GIS/LiDAR**: Digital Elevation Models store a height value per 2D grid cell.
- **Geophysics**: Seismic surveys use 2D surface grids with depth profiles.
- **Document retrieval**: Semantic embeddings live in high-dimensional space but are often projected to 2D for visualization; adding a third "depth" or "phase" dimension captures temporal or categorical structure.

In SCBE-AETHERMOORE, we use 2.5D to mean: **2D hyperbolic lattice + 0.5D cyclic phase**. The cyclic dimension is periodic (wraps at 2*pi), representing flow lanes, temporal cycles, or governance phases. This is not a full 3D structure -- the phase dimension has fundamentally different topology (circular rather than linear) and different distance semantics.

## 2. Core Data Model

### 2.1 CyclicBundle25D

Each document or semantic record is stored as a `CyclicBundle25D`:

```python
@dataclass
class CyclicBundle25D:
    bundle_id: str
    x: float              # Toroidally wrapped [-1, 1]
    y: float              # Toroidally wrapped [-1, 1]
    phase_rad: float      # Cyclic [0, 2*pi)
    tongue: str = "KO"    # Sacred Tongue semantic weight
    authority: str = "public"
    intent_vector: np.ndarray = field(default_factory=lambda: np.zeros(3))
    intent_label: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
```

The `tongue_weight` property returns the phi-scaled weight for the bundle's Sacred Tongue:

| Tongue | Weight |
|--------|--------|
| KO | 1.00 |
| AV | 1.62 |
| RU | 2.62 |
| CA | 4.24 |
| UM | 6.85 |
| DR | 11.09 |

### 2.2 The HyperbolicLattice25D

The lattice manages a grid of cells, each capable of holding multiple overlapping bundles:

```python
class HyperbolicLattice25D:
    def __init__(
        self,
        cell_size: float = 0.25,
        max_depth: int = 6,
        chladni_mode: Tuple[int, int] = (3, 2),
        phase_weight: float = 0.35,
    ):
        self.cell_size = cell_size
        self.phase_weight = phase_weight
        self.grid_span = max(1, int(math.ceil(2.0 / cell_size)))
        self.octree = SignedOctree(max_depth=max_depth, chladni_mode=chladni_mode)
        self._cells: Dict[Tuple[int, int], List[CyclicBundle25D]] = {}
        self._bundles: Dict[str, CyclicBundle25D] = {}
```

Key design decisions:
- **Overlap is allowed**: Multiple bundles can occupy the same cell. This is intentional -- semantic documents frequently overlap in topic space.
- **Dual indexing**: Every bundle exists in both the 2D lattice (for fast cell-based lookup) and the 3D octree (for spatial queries, mirroring, and Chladni addressing).
- **Toroidal wrapping**: Both x and y wrap at boundaries, and the phase wraps at 2*pi.

## 3. Distance Metrics

### 3.1 Hyperbolic 2D Distance (Poincare Disk)

For points inside the unit disk, the Poincare distance is:

```python
@staticmethod
def hyperbolic_distance_2d(ax: float, ay: float, bx: float, by: float) -> float:
    na2 = ax * ax + ay * ay
    nb2 = bx * bx + by * by
    if na2 >= 1.0 or nb2 >= 1.0:
        return float("inf")
    dx = ax - bx
    dy = ay - by
    diff_sq = dx * dx + dy * dy
    denom = (1.0 - na2) * (1.0 - nb2)
    if denom <= 0:
        return float("inf")
    arg = 1.0 + (2.0 * diff_sq) / denom
    return math.acosh(max(1.0, arg))
```

This is the standard formula: `d(a,b) = acosh(1 + 2||a-b||^2 / ((1-||a||^2)(1-||b||^2)))`. Points near the boundary are exponentially far from the center and from each other -- this is the core SCBE insight that adversarial behavior (pushed toward the boundary) becomes exponentially costly.

### 3.2 Cyclic Phase Distance

The phase lives on a circle, so distance wraps:

```python
@staticmethod
def cyclic_phase_distance(a: float, b: float) -> float:
    two_pi = 2.0 * math.pi
    d = abs((a - b) % two_pi)
    d = min(d, two_pi - d)
    return d / math.pi  # Normalize to [0, 1]
```

### 3.3 Composite 2.5D Distance

The full bundle distance combines hyperbolic, cyclic, and semantic components:

```python
def bundle_distance(self, a: CyclicBundle25D, b: CyclicBundle25D) -> float:
    d_h = self.hyperbolic_distance_2d(a.x, a.y, b.x, b.y)
    d_phase = self.cyclic_phase_distance(a.phase_rad, b.phase_rad)
    sim = float(intent_similarity(a.intent_vector, b.intent_vector))
    avg_weight = (a.tongue_weight + b.tongue_weight) / 2.0
    semantic_penalty = (1.0 - sim) * (1.0 + (1.0 / max(1.0, avg_weight)))
    return d_h + self.phase_weight * d_phase + semantic_penalty
```

The semantic penalty decreases for bundles with higher tongue weights (DR at 11.09 is barely penalized, KO at 1.00 is penalized more), reflecting the governance principle that higher-authority content has stronger semantic coherence.

## 4. Octree Projection

Every bundle inserted into the 2.5D lattice is simultaneously projected into the signed-axis octree:

```python
# 3D projection for octree interoperability
z = max(-0.99, min(0.99, math.sin(phase) * 0.98))
self.octree.insert(x=xw, y=yw, z=z, ...)
```

The `sin(phase)` projection maps the cyclic phase to a z-coordinate in `(-0.99, 0.99)`, keeping all points inside the open unit ball as required by the Poincare model. This means:
- Phase 0 and pi map to z near 0 (equatorial plane)
- Phase pi/2 maps to z near +0.98 (north pole)
- Phase 3*pi/2 maps to z near -0.98 (south pole)

The octree then provides mirror operations, Morton code linearization, cross-branch attachments, and sphere grid progression -- all for free.

## 5. Lattice Operations

### 5.1 Overlap Detection

```python
def overlapping_cells(self, min_bundles: int = 2) -> Dict[...]:
    return {k: list(v) for k, v in self._cells.items() if len(v) >= min_bundles}
```

Overlap cells represent topic convergence -- multiple documents occupying the same semantic region. These are high-value targets for merge operations, cross-referencing, or governance review.

### 5.2 Lace Edges (Lattice Connectivity)

```python
def lace_edges(self) -> Set[Tuple[Tuple[int, int], Tuple[int, int]]]:
    occupied = set(self._cells.keys())
    edges = set()
    for cell in occupied:
        for n in self.lattice_neighbors(cell):
            if n in occupied:
                edge = (cell, n) if cell < n else (n, cell)
                edges.add(edge)
    return edges
```

Lace edges form the connectivity graph over occupied cells, supporting graph-based algorithms (community detection, flow routing, governance propagation).

### 5.3 Cycle Advancement

```python
def advance_cycle(self, delta_rad: float) -> None:
    for b in self._bundles.values():
        b.phase_rad = self.normalize_phase(b.phase_rad + delta_rad)
    self.rebuild_octree_projection()
```

Advancing the cycle rotates all bundles through their phase dimension, changing their z-projection and potentially their octant assignment. This models temporal evolution: governance checkpoints that expire, research priorities that rotate, or seasonal content cycles.

## 6. Application: Semantic Document Ingestion

The `hydra/lattice25d_ops.py` module implements a full document ingestion pipeline on top of the 2.5D lattice:

1. **Text metrics extraction**: Character count, word count, unique ratio, URL detection, digit ratio
2. **Automatic tagging**: Length (tiny/short/medium/long), density (light/normal/dense), lexical diversity
3. **Intent vector derivation**: Three components (governance, research, cohesion) computed from text statistics
4. **Tongue selection**: Deterministic selection from the six Sacred Tongues based on preference and hash
5. **Position assignment**: Deterministic x/y/phase from BLAKE2s hashes of the note ID
6. **Lattice insertion**: Bundle creation with full metadata propagation to octree

```python
def build_lattice25d_payload(
    notes: Sequence[NoteRecord],
    *,
    cell_size: float = 0.4,
    max_depth: int = 6,
    phase_weight: float = 0.35,
    radius: float = 0.72,
    query_intent: Optional[List[float]] = None,
    ...
) -> Dict[str, Any]:
```

The result payload includes ingested counts, lattice statistics, overlap cells, lace edge counts, and nearest-neighbor query results -- a complete governed semantic index built from raw text.

## 7. Real-World 2.5D Analogies

| Domain | 2D Surface | Depth/Height | Our Analog |
|--------|-----------|--------------|------------|
| Terrain rendering | x, y ground plane | Elevation z | x, y semantic plane + phase elevation |
| LiDAR point clouds | GPS coordinates | Return height | Document embedding + authority depth |
| Game LOD | Camera-facing plane | Detail level | Semantic proximity + tongue weight |
| Seismic surveys | Surface grid | Depth profile | Topic grid + temporal phase |
| SCBE governance | Intent space | Authority tier | Hyperbolic position + cyclic governance phase |

## 8. Statistics and Observability

The lattice exposes comprehensive statistics:

```python
def stats(self) -> Dict[str, Any]:
    return {
        "bundle_count": len(self._bundles),
        "occupied_cells": len(self._cells),
        "overlap_cells": len(overlap),
        "max_overlap": max(...),
        "lace_edges": len(self.lace_edges()),
        "semantic_weight_sum": float(sum(weights)),
        "semantic_weight_avg": ...,
        "octree_voxel_count": self.octree.stats().get("count", 0),
    }
```

These metrics feed into the SCBE governance pipeline, where anomalies (unexpected overlap, weight imbalances, empty octants) trigger QUARANTINE or ESCALATE decisions.

## 9. Conclusion

The 2.5D quadtree-octree hybrid demonstrates that flat semantic spaces and 3D spatial structures need not be separate systems. By treating the cyclic phase as a "half dimension" that projects into a full octree, we get the best of both worlds: fast 2D grid operations for document retrieval, and full 3D spatial queries (mirroring, Morton ranges, Chladni addressing) for governance analysis. The toroidal wrapping and cyclic advancement operations make the structure inherently suitable for temporal workflows where content rotates through phases of creation, review, and publication.

## References

- `hydra/octree_sphere_grid.py` -- HyperbolicLattice25D and CyclicBundle25D implementation
- `hydra/lattice25d_ops.py` -- Document ingestion pipeline with text metrics
- `hydra/voxel_storage.py` -- Base 6D voxel and Chladni addressing
- `src/harmonic/pipeline14.ts` -- 14-layer pipeline with Poincare embedding (Layer 4)
- `src/harmonic/hyperbolic.ts` -- Hyperbolic distance and Mobius transforms
- Cannon, J.W. et al. (1997). "Hyperbolic Geometry." Flavors of Geometry, MSRI Publications.
- Samet, H. (2006). "Foundations of Multidimensional and Metric Data Structures." Morgan Kaufmann.

---

*Part of the SCBE-AETHERMOORE open governance framework. Patent pending: USPTO #63/961,403.*
*Repository: github.com/issdandavis/SCBE-AETHERMOORE*
