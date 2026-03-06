# Signed-Axis Octrees with Fractal Chladni Addressing for 6D Voxel Storage

**Issac Daniel Davis** | SCBE-AETHERMOORE Project | 2026-03-05

## Abstract

We present a signed-axis octree data structure that extends classical 3-bit octant indexing with fractal Chladni addressing, Morton Z-order linearization, and an embedded per-voxel sphere grid inspired by Final Fantasy X's progression system. The structure stores 6D voxels (x, y, z, wavelength, tongue, authority) within the Poincare ball, supporting mirror operations between octant pairs, toroidal coordinate wrapping across sign boundaries, and cross-branch attachments via face planes. Chladni mode parameters scale by the golden ratio at each depth level, producing self-similar nodal patterns that serve as content-addressable keys for semantic document storage. The implementation bridges hyperbolic geometry, game design patterns, and information retrieval within the SCBE-AETHERMOORE governance framework.

## 1. Introduction

Octree structures are well-established for spatial partitioning in computer graphics and physics simulation. In the SCBE-AETHERMOORE system, we extend the octree concept in three directions:

1. **Signed-axis awareness**: Explicit tracking of which of the 8 sign-based octants a point inhabits, enabling mirror and symmetry operations.
2. **Fractal Chladni addressing**: Vibrational mode patterns (Chladni figures) whose parameters scale by phi at each depth level, producing content-addressable nodal fingerprints.
3. **FF10 Sphere Grid slots**: Each voxel node embeds a 10-slot progression grid inspired by Final Fantasy X, supporting intent upgrades, authority gates, and governance checkpoints.

This article describes the design, shows working code from `hydra/octree_sphere_grid.py`, and maps the concepts to a multi-language interoperability matrix.

## 2. Signed-Axis Octants

A classical octree partitions space by comparing each coordinate to the node center. The 3-bit octant index is:

```
bit 0 = x >= center.x  (1 = positive x)
bit 1 = y >= center.y  (2 = positive y)
bit 2 = z >= center.z  (4 = positive z)
```

We make this sign structure explicit with a `SignTriplet`:

```python
SignTriplet = Tuple[bool, bool, bool]  # (x_positive, y_positive, z_positive)

OCTANT_NAMES: Dict[SignTriplet, str] = {
    (True, True, True): "+x+y+z",
    (True, True, False): "+x+y-z",
    (True, False, True): "+x-y+z",
    (True, False, False): "+x-y-z",
    (False, True, True): "-x+y+z",
    (False, True, False): "-x+y-z",
    (False, False, True): "-x-y+z",
    (False, False, False): "-x-y-z",
}
```

The 8 octants, combined with 6 face-plane attachment points (where adjacent octants share a boundary), yield 14 connection surfaces -- a number that aligns with the 14-layer security pipeline used throughout SCBE.

### 2.1 Mirror Operations

Mirroring copies all voxels from a source octant to a target octant by flipping the coordinates where signs differ:

```python
def mirror_point(
    x: float, y: float, z: float,
    flip_x: bool = False, flip_y: bool = False, flip_z: bool = False,
) -> Tuple[float, float, float]:
    return (
        -x if flip_x else x,
        -y if flip_y else y,
        -z if flip_z else z,
    )
```

In the `SignedOctree.mirror_octant()` method, intent vectors can optionally be negated alongside spatial coordinates, creating a "semantic mirror" where governance-approved content in one octant generates its adversarial counterpart in the opposite octant for testing.

### 2.2 Toroidal Wrap

Coordinates that exit the `[-1, 1]` bounds re-enter from the opposite side:

```python
def toroidal_wrap(val: float, bound: float = 1.0) -> float:
    if abs(val) <= bound:
        return val
    return ((val + bound) % (2 * bound)) - bound
```

This creates circular flow across sign boundaries, which is essential for cyclic processes like the 2.5D phase lattice (Section 7).

## 3. Morton Z-Order Curves

For linearized traversal and range queries, each voxel receives a Morton code computed by interleaving the 3D grid coordinates:

```python
def morton_encode_3d(x: int, y: int, z: int) -> int:
    def spread(v: int) -> int:
        v = v & 0x1FFFFF  # 21 bits max
        v = (v | (v << 32)) & 0x1F00000000FFFF
        v = (v | (v << 16)) & 0x1F0000FF0000FF
        v = (v | (v << 8))  & 0x100F00F00F00F00F
        v = (v | (v << 4))  & 0x10C30C30C30C30C3
        v = (v | (v << 2))  & 0x1249249249249249
        return v
    return spread(x) | (spread(y) << 1) | (spread(z) << 2)
```

The implementation maps the `[-1, 1]` continuous range to a 1024-step integer grid before interleaving, yielding up to 63-bit Morton codes. Range queries `query_by_morton_range(start, end)` exploit spatial locality -- nearby Morton codes correspond to nearby 3D positions.

## 4. FF10 Sphere Grid (10 Slots Per Voxel)

Each `OctreeVoxel` embeds a `SphereGrid` with 10 typed slots arranged in a dual-row ring topology:

```
0 -- 1 -- 2 -- 3 -- 4
|              |
5 -- 6 -- 7 -- 8 -- 9
      \       /
       center
```

Slot types include:

| Type | Purpose |
|------|---------|
| INTENT | Semantic intent upgrade |
| AUTHORITY | Authority tier gate |
| SPECTRAL | Wavelength/frequency shift |
| GOVERNANCE | Governance check node |
| MERGE | Convergence/prism node |

Each slot carries a Sacred Tongue label (KO, AV, RU, CA, UM, DR) with phi-scaled weights. Progression through the grid uses BFS pathfinding:

```python
def path_to(self, target_id: int) -> List[int]:
    """BFS shortest path from active_slot to target_id."""
    if target_id == self.active_slot:
        return [self.active_slot]
    visited = {self.active_slot}
    queue = [[self.active_slot]]
    while queue:
        path = queue.pop(0)
        current = path[-1]
        for neighbor in self.slots[current].connections:
            if neighbor == target_id:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return []
```

This gamified progression means a document or agent must "unlock" governance checkpoints before reaching high-authority merge nodes -- a mechanical enforcement of the SCBE principle that adversarial behavior costs exponentially more.

## 5. Fractal Chladni Addressing

Chladni figures are the nodal patterns of vibrating plates. The 2D amplitude function is:

```
A(x, y) = cos(n * pi * x) * cos(m * pi * y) - cos(m * pi * x) * cos(n * pi * y)
```

In the signed octree, the mode parameters `(n, m)` scale with depth by the golden ratio:

```python
@property
def chladni_mode(self) -> Tuple[int, int]:
    n = max(2, int(self.chladni_base_mode[0] * (PHI ** self.depth)))
    m = max(2, int(self.chladni_base_mode[1] * (PHI ** self.depth)))
    if n == m:
        m += 1  # avoid degenerate symmetric mode
    return (n, m)
```

Starting from base mode `(3, 2)`, the modes at each depth are:

| Depth | n | m | Pattern Character |
|-------|---|---|-------------------|
| 0 | 3 | 2 | Coarse, 6 nodal lines |
| 1 | 4 | 3 | Moderate subdivision |
| 2 | 7 | 5 | Fine structure emerging |
| 3 | 12 | 8 | High-frequency detail |
| 4 | 20 | 13 | Near-fractal density |

The Chladni value assigned to each voxel serves as a content-addressable fingerprint: voxels near nodal lines (amplitude close to zero) are "stable" storage locations; voxels at antinodes (high amplitude) are "active" zones suitable for merge operations.

## 6. Cross-Branch Attachments

Adjacent octants (differing in exactly one sign) share a face plane. The `auto_cross_branches()` method automatically registers these connections:

```python
def auto_cross_branches(self) -> int:
    count = 0
    signs = list(OCTANT_NAMES.keys())
    for i, a in enumerate(signs):
        for b in signs[i + 1:]:
            diffs = sum(1 for x, y in zip(a, b) if x != y)
            if diffs == 1:
                # Find which axis differs
                for ax_idx, (sa, sb) in enumerate(zip(a, b)):
                    if sa != sb:
                        plane = ["yz", "xz", "xy"][ax_idx]
                        self._cross_branches.append(
                            (OCTANT_NAMES[a], OCTANT_NAMES[b], plane)
                        )
                        count += 1
                        break
    return count
```

This produces 12 cross-branch edges (each of 3 axes has 4 pairs of octants differing on that axis), forming a connected graph where semantic queries can flow between octants along face planes.

## 7. Relationship to the Existing Octree (src/crypto/octree.py)

The existing `HyperbolicOctree` in `src/crypto/octree.py` provides:
- Sparse hierarchical storage for points in the Poincare ball
- Realm coloring (light/shadow/path)
- Spectral clustering via harmonic fingerprints
- Dense export for visualization

The new `SignedOctree` in `hydra/octree_sphere_grid.py` extends this foundation with:
- Explicit signed-axis tracking and mirror operations
- Morton linearization for range queries
- Sphere grid progression per voxel
- Fractal Chladni content addressing
- 6D metadata (wavelength, tongue, authority, intent)

Both share the same 3-bit octant indexing convention, ensuring compatibility.

## 8. The INTEROP_MATRIX: A Rosetta Stone

The module includes a comprehensive `INTEROP_MATRIX` dictionary that maps every concept to its equivalent in Python, TypeScript, Rust, Go, WASM, SQL, GLSL, Solidity, and HTML/CSS:

```python
"PoincareDistance": {
    "formula": "d(a,b) = acosh(1 + 2||a-b||^2 / ((1-||a||^2)(1-||b||^2)))",
    "python": "math.acosh(1 + 2*norm_sq / ((1-na2)*(1-nb2)))",
    "typescript": "Math.acosh(1 + 2*euclidSq / ((1-na2)*(1-nb2)))",
    "rust": "((1.0 + 2.0*esq / ((1.0-na2)*(1.0-nb2)))).acosh()",
    "glsl": "acosh(1.0 + 2.0*dot(d,d) / ((1.0-dot(a,a))*(1.0-dot(b,b))))",
},
```

This serves as the contract for cross-language parity: any port must produce identical results for the same inputs. The matrix covers `SignedOctree`, `MortonCode`, `ChladniAmplitude`, `SphereGrid`, `ToroidalWrap`, `IntentSimilarity`, and `AuthorityHash`, plus type mappings for `np.ndarray`, `dataclass`, `Dict`, `List`, `Enum`, `Optional`, and tuples.

## 9. Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Insert | O(depth) | Recursive octant descent |
| Point query | O(depth) | Same descent path |
| Morton range query | O(N) | Linear scan (could be B-tree indexed) |
| Mirror octant | O(K * depth) | K = source voxel count |
| Intent query | O(N) | Cosine similarity over all or octant subset |
| Sphere grid BFS | O(10) | Constant (10 slots max) |
| Auto cross-branches | O(1) | Fixed 12 edges from 8 octants |

## 10. Conclusion

The signed-axis octree with fractal Chladni addressing unifies spatial partitioning, vibrational physics, and game-inspired progression into a single data structure for governed 6D voxel storage. By making octant signs, mirror operations, and cross-branch connections first-class concepts, the structure supports governance workflows where symmetric analysis, adversarial testing, and authority progression are mechanical requirements rather than afterthoughts.

## References

- `hydra/octree_sphere_grid.py` -- Full implementation (1089 lines)
- `src/crypto/octree.py` -- Original HyperbolicOctree with spectral clustering
- `hydra/voxel_storage.py` -- 6D Voxel base classes and Chladni addressing
- `hydra/color_dimension.py` -- Sacred Tongue weights and wavelength mappings
- `src/ai_brain/cymatic-voxel-net.ts` -- TypeScript 6D Chladni reference
- `training/intake/fibonacci_sphere_grid.json` -- 217-node sphere seed data
- Morton, G.M. (1966). "A Computer Oriented Geodetic Data Base and a New Technique in File Sequencing." IBM Ottawa.
- Chladni, E.F.F. (1787). "Entdeckungen uber die Theorie des Klanges." Leipzig.

---

*Part of the SCBE-AETHERMOORE open governance framework. Patent pending: USPTO #63/961,403.*
*Repository: github.com/issdandavis/SCBE-AETHERMOORE*
