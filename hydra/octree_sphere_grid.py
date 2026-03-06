"""
HYDRA Octree Sphere Grid — Signed-Axis Octree + FF10 Sphere Slots + Fractal Chladni
====================================================================================

Connects existing infrastructure:
  - src/crypto/octree.py         (HyperbolicOctree, 3-bit octant indexing)
  - hydra/voxel_storage.py       (6D Voxel, VoxelGrid, Chladni addressing)
  - hydra/color_dimension.py     (ColorChannel, spectral flow isolation)
  - src/ai_brain/cymatic-voxel-net.ts  (6D Chladni equation reference)
  - training/intake/fibonacci_sphere_grid.json  (217-node sphere seed data)

New concepts added:
  1. Signed-axis octants: 8 octants via (+/-x, +/-y, +/-z) sign triplets
  2. Mirror/non-mirror operations between octant pairs
  3. Toroidal wrap for circular storage across sign boundaries
  4. FF10-style SphereSlot grid embedded per voxel node (10 slots)
  5. Fractal Chladni subdivision (modes scale by phi at each depth)
  6. Morton/Z-order curve for linearized octree traversal
  7. Cross-branch attachments connecting octants via face planes

Usage:
    from hydra.octree_sphere_grid import SignedOctree, SphereGrid, SphereSlot

    tree = SignedOctree(max_depth=6)
    tree.insert(0.3, -0.5, 0.1, intent="govern", authority="sealed")
    mirror = tree.mirror_octant((True, True, True), (True, True, False))  # +z -> -z
    neighbors = tree.query_octant((False, True, True), intent="govern")
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

import numpy as np

from hydra.color_dimension import ColorChannel, PHI, TONGUE_WEIGHTS
from hydra.voxel_storage import (
    Voxel,
    chladni_amplitude,
    chladni_address,
    compute_authority_hash,
    normalize_intent,
    intent_similarity,
)


# ---------------------------------------------------------------------------
#  Morton / Z-Order Curve (space-filling linearization)
# ---------------------------------------------------------------------------

def morton_encode_3d(x: int, y: int, z: int) -> int:
    """Interleave 3 integers into a single Morton code (Z-order curve).

    Maps 3D grid coordinates to 1D index preserving spatial locality.
    """
    def spread(v: int) -> int:
        v = v & 0x1FFFFF  # 21 bits max
        v = (v | (v << 32)) & 0x1F00000000FFFF
        v = (v | (v << 16)) & 0x1F0000FF0000FF
        v = (v | (v << 8)) & 0x100F00F00F00F00F
        v = (v | (v << 4)) & 0x10C30C30C30C30C3
        v = (v | (v << 2)) & 0x1249249249249249
        return v

    return spread(x) | (spread(y) << 1) | (spread(z) << 2)


def morton_decode_3d(code: int) -> Tuple[int, int, int]:
    """Decode a Morton code back to 3D coordinates."""
    def compact(v: int) -> int:
        v = v & 0x1249249249249249
        v = (v | (v >> 2)) & 0x10C30C30C30C30C3
        v = (v | (v >> 4)) & 0x100F00F00F00F00F
        v = (v | (v >> 8)) & 0x1F0000FF0000FF
        v = (v | (v >> 16)) & 0x1F00000000FFFF
        v = (v | (v >> 32)) & 0x1FFFFF
        return v

    return compact(code), compact(code >> 1), compact(code >> 2)


# ---------------------------------------------------------------------------
#  Sign Triplet — identifies which octant a point lives in
# ---------------------------------------------------------------------------

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

# 6 face planes where cross-branch attachments connect octants
FACE_PLANES = [
    ("xy+", (None, None, True)),   # z > 0 face
    ("xy-", (None, None, False)),  # z < 0 face
    ("xz+", (None, True, None)),   # y > 0 face
    ("xz-", (None, False, None)),  # y < 0 face
    ("yz+", (True, None, None)),   # x > 0 face
    ("yz-", (False, None, None)),  # x < 0 face
]


def sign_triplet(x: float, y: float, z: float) -> SignTriplet:
    """Determine which octant a point belongs to."""
    return (x >= 0, y >= 0, z >= 0)


def mirror_point(
    x: float, y: float, z: float,
    flip_x: bool = False, flip_y: bool = False, flip_z: bool = False,
) -> Tuple[float, float, float]:
    """Mirror a point across specified axes."""
    return (
        -x if flip_x else x,
        -y if flip_y else y,
        -z if flip_z else z,
    )


def toroidal_wrap(val: float, bound: float = 1.0) -> float:
    """Wrap a coordinate toroidally: exits +bound, enters -bound."""
    if abs(val) <= bound:
        return val
    return ((val + bound) % (2 * bound)) - bound


# ---------------------------------------------------------------------------
#  Sphere Slot — FF10-style character slot inside a voxel node
# ---------------------------------------------------------------------------

class SlotType(str, Enum):
    """Types of sphere grid slots (inspired by FF10)."""
    INTENT = "intent"           # Semantic intent upgrade
    AUTHORITY = "authority"     # Authority tier gate
    SPECTRAL = "spectral"      # Wavelength/frequency shift
    GOVERNANCE = "governance"   # Governance check node
    MERGE = "merge"             # Convergence/prism node
    EMPTY = "empty"             # Unactivated slot


@dataclass
class SphereSlot:
    """A single slot in the per-voxel sphere grid.

    Like FF10's sphere grid: each slot holds an attribute that can be
    "activated" (unlocked) by spending resources (authority, intent, time).
    """
    slot_id: int
    slot_type: SlotType = SlotType.EMPTY
    value: float = 0.0
    label: str = ""
    activated: bool = False
    tongue: str = "KO"
    connections: List[int] = field(default_factory=list)  # connected slot IDs

    @property
    def weight(self) -> float:
        """Phi-scaled weight based on tongue."""
        return TONGUE_WEIGHTS.get(self.tongue, 1.0)


@dataclass
class SphereGrid:
    """FF10-style sphere grid embedded in a single voxel node.

    10 slots arranged in a ring topology with cross-connections.
    Each slot can hold intent upgrades, authority gates, spectral shifts, etc.

    Layout (default 10 slots):
        0 -- 1 -- 2 -- 3 -- 4
        |              |
        5 -- 6 -- 7 -- 8 -- 9
              \\       /
               center

    Progression: "move" through slots by activating them in sequence.
    """
    slots: List[SphereSlot] = field(default_factory=list)
    active_slot: int = 0

    @staticmethod
    def create_default(tongue: str = "KO") -> SphereGrid:
        """Create a default 10-slot sphere grid for a voxel."""
        tongues = list(TONGUE_WEIGHTS.keys())
        slot_types = [
            SlotType.INTENT, SlotType.SPECTRAL, SlotType.AUTHORITY,
            SlotType.GOVERNANCE, SlotType.MERGE,
            SlotType.INTENT, SlotType.SPECTRAL, SlotType.AUTHORITY,
            SlotType.GOVERNANCE, SlotType.MERGE,
        ]

        slots = []
        for i in range(10):
            # Ring connections: each slot connects to neighbors
            connections = []
            if i > 0:
                connections.append(i - 1)
            if i < 9:
                connections.append(i + 1)
            # Cross-connections (top row to bottom row)
            if i < 5:
                connections.append(i + 5)
            else:
                connections.append(i - 5)

            slots.append(SphereSlot(
                slot_id=i,
                slot_type=slot_types[i],
                tongue=tongues[i % len(tongues)],
                label=f"{slot_types[i].value}_{tongues[i % len(tongues)]}",
                connections=connections,
            ))

        return SphereGrid(slots=slots)

    def activate_slot(self, slot_id: int) -> bool:
        """Activate a slot if it's connected to the current active slot."""
        if slot_id < 0 or slot_id >= len(self.slots):
            return False
        slot = self.slots[slot_id]
        current = self.slots[self.active_slot]
        if slot_id not in current.connections and slot_id != self.active_slot:
            return False
        slot.activated = True
        self.active_slot = slot_id
        return True

    def activated_count(self) -> int:
        return sum(1 for s in self.slots if s.activated)

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
        return []  # unreachable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_slot": self.active_slot,
            "activated_count": self.activated_count(),
            "slots": [
                {
                    "id": s.slot_id,
                    "type": s.slot_type.value,
                    "tongue": s.tongue,
                    "activated": s.activated,
                    "label": s.label,
                    "connections": s.connections,
                }
                for s in self.slots
            ],
        }


# ---------------------------------------------------------------------------
#  Octree Node with Signed Axes + Sphere Grid + Fractal Chladni
# ---------------------------------------------------------------------------

@dataclass
class OctreeVoxel:
    """A voxel stored in the signed octree, with sphere grid attached."""
    x: float
    y: float
    z: float
    octant: SignTriplet
    morton_code: int

    # 6D extensions
    wavelength_nm: float = 550.0
    tongue: str = "KO"
    authority: str = "public"
    intent_vector: np.ndarray = field(default_factory=lambda: np.zeros(3))
    intent_label: str = ""

    # Chladni addressing
    chladni_value: float = 0.0
    chladni_mode: Tuple[int, int] = (3, 2)

    # Sphere grid (10 FF10-style slots per voxel)
    sphere_grid: SphereGrid = field(default_factory=lambda: SphereGrid.create_default())

    # Metadata
    created_at: float = 0.0
    authority_hash: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)


class OctreeNode:
    """Recursive octree node with signed-axis awareness.

    3-bit octant indexing (same as src/crypto/octree.py):
      bit 0 = x >= center  (1 = positive x)
      bit 1 = y >= center  (2 = positive y)
      bit 2 = z >= center  (4 = positive z)
    """

    def __init__(
        self,
        center: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        half_size: float = 1.0,
        depth: int = 0,
        max_depth: int = 6,
        chladni_base_mode: Tuple[int, int] = (3, 2),
    ):
        self.center = center
        self.half_size = half_size
        self.depth = depth
        self.max_depth = max_depth
        self.chladni_base_mode = chladni_base_mode
        self.children: Dict[int, OctreeNode] = {}  # 0-7
        self.voxels: List[OctreeVoxel] = []
        self.is_leaf = True

    @property
    def chladni_mode(self) -> Tuple[int, int]:
        """Fractal Chladni: modes scale by phi at each depth level."""
        n = max(2, int(self.chladni_base_mode[0] * (PHI ** self.depth)))
        m = max(2, int(self.chladni_base_mode[1] * (PHI ** self.depth)))
        if n == m:
            m += 1  # avoid degenerate symmetric mode
        return (n, m)

    def _octant_index(self, x: float, y: float, z: float) -> int:
        """3-bit octant index from point position."""
        idx = 0
        if x >= self.center[0]:
            idx |= 1
        if y >= self.center[1]:
            idx |= 2
        if z >= self.center[2]:
            idx |= 4
        return idx

    def _child_center(self, octant: int) -> Tuple[float, float, float]:
        """Compute center of child octant."""
        hs = self.half_size / 2
        cx = self.center[0] + (hs if octant & 1 else -hs)
        cy = self.center[1] + (hs if octant & 2 else -hs)
        cz = self.center[2] + (hs if octant & 4 else -hs)
        return (cx, cy, cz)

    def insert(self, voxel: OctreeVoxel) -> None:
        """Insert a voxel into the octree."""
        if self.depth >= self.max_depth:
            self.voxels.append(voxel)
            return

        octant = self._octant_index(voxel.x, voxel.y, voxel.z)

        if octant not in self.children:
            self.children[octant] = OctreeNode(
                center=self._child_center(octant),
                half_size=self.half_size / 2,
                depth=self.depth + 1,
                max_depth=self.max_depth,
                chladni_base_mode=self.chladni_base_mode,
            )
            self.is_leaf = False

        self.children[octant].insert(voxel)

    def query_octant(self, octant: int) -> List[OctreeVoxel]:
        """Get all voxels in a specific octant subtree."""
        if octant in self.children:
            return self.children[octant].collect_all()
        return []

    def collect_all(self) -> List[OctreeVoxel]:
        """Collect all voxels in this subtree."""
        result = list(self.voxels)
        for child in self.children.values():
            result.extend(child.collect_all())
        return result

    def count(self) -> int:
        """Count total voxels in subtree."""
        n = len(self.voxels)
        for child in self.children.values():
            n += child.count()
        return n

    def depth_stats(self) -> Dict[int, int]:
        """Count voxels at each depth level."""
        stats: Dict[int, int] = {}
        self._depth_stats(stats)
        return stats

    def _depth_stats(self, stats: Dict[int, int]):
        if self.voxels:
            stats[self.depth] = stats.get(self.depth, 0) + len(self.voxels)
        for child in self.children.values():
            child._depth_stats(stats)


# ---------------------------------------------------------------------------
#  Signed Octree — the main structure tying everything together
# ---------------------------------------------------------------------------

class SignedOctree:
    """Signed-axis octree with mirroring, toroidal wrap, sphere grids, and fractal Chladni.

    Extends:
      - src/crypto/octree.py HyperbolicOctree (3-bit octant indexing)
      - hydra/voxel_storage.py VoxelGrid (6D voxels, Chladni addressing)
      - New: signed axes, mirror ops, sphere grid slots, Morton linearization

    Key insight (from user): positive (x,y,z) and negative (-x,-y,-z) give
    8 octants. Combined with 6 face-plane attachment points = 14 connection
    surfaces. Mirroring across any axis creates symmetric storage; toroidal
    wrap enables circular flow.
    """

    def __init__(
        self,
        max_depth: int = 6,
        chladni_mode: Tuple[int, int] = (3, 2),
    ):
        self.max_depth = max_depth
        self.chladni_mode = chladni_mode
        self.root = OctreeNode(
            center=(0.0, 0.0, 0.0),
            half_size=1.0,
            depth=0,
            max_depth=max_depth,
            chladni_base_mode=chladni_mode,
        )
        self._cross_branches: List[Tuple[str, str, str]] = []  # (from_octant, to_octant, plane)

    def insert(
        self,
        x: float, y: float, z: float,
        wavelength_nm: float = 550.0,
        tongue: str = "KO",
        authority: str = "public",
        intent_vector: Optional[List[float]] = None,
        intent_label: str = "",
        payload: Optional[Dict[str, Any]] = None,
        create_sphere_grid: bool = True,
    ) -> OctreeVoxel:
        """Insert a voxel with full 6D metadata and sphere grid."""
        # Toroidal wrap if outside bounds
        x = toroidal_wrap(x)
        y = toroidal_wrap(y)
        z = toroidal_wrap(z)

        # Compute derived fields
        octant = sign_triplet(x, y, z)
        intent_arr = normalize_intent(intent_vector or [0, 0, 0])

        # Fractal Chladni: mode scales with depth estimate
        depth_est = min(self.max_depth, int(-math.log2(max(abs(x), abs(y), abs(z), 0.01))))
        n = max(2, int(self.chladni_mode[0] * (PHI ** min(depth_est, 4))))
        m = max(2, int(self.chladni_mode[1] * (PHI ** min(depth_est, 4))))
        if n == m:
            m += 1
        cv = chladni_amplitude(abs(x), abs(y), n, m)

        # Morton code for linearized addressing
        # Map [-1,1] to [0, 2^10] grid for Morton encoding
        res = 1024
        mx = int((x + 1) / 2 * (res - 1))
        my = int((y + 1) / 2 * (res - 1))
        mz = int((z + 1) / 2 * (res - 1))
        morton = morton_encode_3d(mx, my, mz)

        import time
        now = time.time()

        voxel = OctreeVoxel(
            x=x, y=y, z=z,
            octant=octant,
            morton_code=morton,
            wavelength_nm=wavelength_nm,
            tongue=tongue,
            authority=authority,
            intent_vector=intent_arr,
            intent_label=intent_label,
            chladni_value=cv,
            chladni_mode=(n, m),
            sphere_grid=SphereGrid.create_default(tongue) if create_sphere_grid else SphereGrid(),
            created_at=now,
            authority_hash=compute_authority_hash(authority, str(payload or {}), now),
            payload=payload or {},
        )

        self.root.insert(voxel)
        return voxel

    # -- Octant queries --

    def query_by_octant(self, signs: SignTriplet) -> List[OctreeVoxel]:
        """Get all voxels in a specific signed octant."""
        # Map sign triplet to 3-bit index
        idx = (1 if signs[0] else 0) | (2 if signs[1] else 0) | (4 if signs[2] else 0)
        return self.root.query_octant(idx)

    def query_by_intent(
        self,
        intent_vector: List[float],
        octant: Optional[SignTriplet] = None,
        min_similarity: float = 0.5,
        top_k: int = 10,
    ) -> List[Tuple[OctreeVoxel, float]]:
        """Semantic intent query, optionally restricted to one octant."""
        query = normalize_intent(intent_vector)
        if octant:
            voxels = self.query_by_octant(octant)
        else:
            voxels = self.root.collect_all()

        scored = []
        for v in voxels:
            sim = intent_similarity(query, v.intent_vector)
            if sim >= min_similarity:
                scored.append((v, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def query_by_authority(self, authority: str) -> List[OctreeVoxel]:
        """Find all voxels with a specific authority level."""
        return [v for v in self.root.collect_all() if v.authority == authority]

    def query_by_morton_range(self, start: int, end: int) -> List[OctreeVoxel]:
        """Query voxels within a Morton code range (spatial locality query)."""
        return [v for v in self.root.collect_all() if start <= v.morton_code <= end]

    # -- Mirror operations --

    def mirror_octant(
        self,
        source: SignTriplet,
        target: SignTriplet,
        transform_intent: bool = False,
    ) -> List[OctreeVoxel]:
        """Mirror all voxels from source octant to target octant.

        Flips coordinates for each axis where source and target signs differ.
        Returns the newly inserted mirrored voxels.
        """
        source_voxels = self.query_by_octant(source)
        flip_x = source[0] != target[0]
        flip_y = source[1] != target[1]
        flip_z = source[2] != target[2]

        mirrored = []
        for v in source_voxels:
            mx, my, mz = mirror_point(v.x, v.y, v.z, flip_x, flip_y, flip_z)

            # Optionally negate intent vector for semantic mirror
            intent = list(-v.intent_vector if transform_intent else v.intent_vector)

            new_v = self.insert(
                x=mx, y=my, z=mz,
                wavelength_nm=v.wavelength_nm,
                tongue=v.tongue,
                authority=v.authority,
                intent_vector=intent,
                intent_label=f"mirror_{v.intent_label}",
                payload={**v.payload, "_mirrored_from": OCTANT_NAMES[source]},
            )
            mirrored.append(new_v)

        return mirrored

    # -- Cross-branch attachments --

    def add_cross_branch(self, from_octant: str, to_octant: str, plane: str) -> None:
        """Register a cross-branch attachment between octants via a face plane."""
        self._cross_branches.append((from_octant, to_octant, plane))

    def auto_cross_branches(self) -> int:
        """Automatically create cross-branches between all adjacent octant pairs.

        Adjacent octants share a face plane (differ in exactly one sign).
        """
        count = 0
        signs = list(OCTANT_NAMES.keys())
        for i, a in enumerate(signs):
            for b in signs[i + 1:]:
                # Adjacent = differ in exactly one axis
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

    # -- Statistics --

    def stats(self) -> Dict[str, Any]:
        """Comprehensive statistics about the octree."""
        all_voxels = self.root.collect_all()
        if not all_voxels:
            return {"count": 0, "octants_used": 0}

        octant_counts = {}
        authority_counts = {}
        tongue_counts = {}
        total_sphere_activated = 0

        for v in all_voxels:
            name = OCTANT_NAMES[v.octant]
            octant_counts[name] = octant_counts.get(name, 0) + 1
            authority_counts[v.authority] = authority_counts.get(v.authority, 0) + 1
            tongue_counts[v.tongue] = tongue_counts.get(v.tongue, 0) + 1
            total_sphere_activated += v.sphere_grid.activated_count()

        chladni_values = [v.chladni_value for v in all_voxels]

        return {
            "count": len(all_voxels),
            "max_depth": self.max_depth,
            "chladni_base_mode": self.chladni_mode,
            "octants_used": len(octant_counts),
            "octant_distribution": octant_counts,
            "authority_distribution": authority_counts,
            "tongue_distribution": tongue_counts,
            "cross_branches": len(self._cross_branches),
            "depth_stats": self.root.depth_stats(),
            "chladni_range": (min(chladni_values), max(chladni_values)),
            "total_sphere_slots": len(all_voxels) * 10,
            "total_sphere_activated": total_sphere_activated,
            "morton_range": (
                min(v.morton_code for v in all_voxels),
                max(v.morton_code for v in all_voxels),
            ),
        }


# ---------------------------------------------------------------------------
#  Interoperability Matrix — Rosetta Stone for porting
# ---------------------------------------------------------------------------

INTEROP_MATRIX = {
    "concepts": {
        "SignedOctree": {
            "python": "hydra.octree_sphere_grid.SignedOctree",
            "typescript": "src/crypto/octree.py -> port to TS class",
            "rust": "struct SignedOctree<V> { root: OctreeNode<V>, max_depth: u8 }",
            "go": "type SignedOctree struct { Root *OctreeNode; MaxDepth int }",
            "wasm": "Export via wasm-bindgen (Rust) or AssemblyScript",
            "sql": "CREATE TABLE octree_nodes (id, parent_id, octant INT, depth INT, ...)",
            "html_css": "CSS Grid with 8 quadrant divs, transform: scaleX(-1) for mirror",
            "solidity": "mapping(bytes32 => Voxel) public voxels; // octant as high bits",
            "glsl": "uniform vec3 u_center; int octant = (x>=c.x?1:0)|(y>=c.y?2:0)|(z>=c.z?4:0);",
        },
        "MortonCode": {
            "python": "morton_encode_3d(x, y, z) -> int",
            "typescript": "function mortonEncode3D(x: number, y: number, z: number): number",
            "rust": "fn morton_encode(x: u32, y: u32, z: u32) -> u64 { bit interleave }",
            "go": "func MortonEncode(x, y, z uint32) uint64",
            "sql": "INDEX ON morton_code for range scans (WHERE morton BETWEEN a AND b)",
            "glsl": "int mortonCode = interleave(uvec3(gl_FragCoord.xyz));",
        },
        "ChladniAmplitude": {
            "python": "cos(n*pi*x/L)*cos(m*pi*y/L) - cos(m*pi*x/L)*cos(n*pi*y/L)",
            "typescript": "Math.cos(n*PI*x)*Math.cos(m*PI*y) - Math.cos(m*PI*x)*Math.cos(n*PI*y)",
            "rust": "(n*PI*x).cos()*(m*PI*y).cos() - (m*PI*x).cos()*(n*PI*y).cos()",
            "glsl": "cos(n*PI*uv.x)*cos(m*PI*uv.y) - cos(m*PI*uv.x)*cos(n*PI*uv.y)",
            "html_css": "CSS Houdini paint worklet with cos() in canvas",
            "solidity": "Fixed-point cos via Chebyshev polynomials (gas-expensive)",
        },
        "SphereGrid": {
            "python": "SphereGrid with 10 SphereSlot (ring topology + BFS pathfinding)",
            "typescript": "class SphereGrid { slots: SphereSlot[]; activateSlot(id) }",
            "rust": "struct SphereGrid { slots: [SphereSlot; 10], active: usize }",
            "html_css": "SVG <circle> nodes + <line> edges, CSS animation for activation",
            "sql": "TABLE sphere_slots (voxel_id FK, slot_id, type, activated BOOL, ...)",
        },
        "PoincareDistance": {
            "formula": "d(a,b) = acosh(1 + 2||a-b||^2 / ((1-||a||^2)(1-||b||^2)))",
            "python": "math.acosh(1 + 2*norm_sq / ((1-na2)*(1-nb2)))",
            "typescript": "Math.acosh(1 + 2*euclidSq / ((1-na2)*(1-nb2)))",
            "rust": "((1.0 + 2.0*esq / ((1.0-na2)*(1.0-nb2)))).acosh()",
            "glsl": "acosh(1.0 + 2.0*dot(d,d) / ((1.0-dot(a,a))*(1.0-dot(b,b))))",
        },
        "ToroidalWrap": {
            "formula": "((val + bound) % (2*bound)) - bound",
            "python": "((val + 1.0) % 2.0) - 1.0",
            "typescript": "((val + 1) % 2) - 1",
            "rust": "((val + 1.0).rem_euclid(2.0)) - 1.0",
            "glsl": "mod(val + 1.0, 2.0) - 1.0",
            "sql": "MOD(val + 1.0, 2.0) - 1.0",
        },
        "IntentSimilarity": {
            "formula": "dot(a,b) / (||a|| * ||b||)  (cosine similarity)",
            "python": "np.dot(a,b) / (np.linalg.norm(a) * np.linalg.norm(b))",
            "typescript": "dotProduct(a,b) / (norm(a) * norm(b))",
            "rust": "a.dot(&b) / (a.norm() * b.norm())",
            "sql": "SUM(a_i * b_i) / (SQRT(SUM(a_i^2)) * SQRT(SUM(b_i^2)))",
            "glsl": "dot(a,b) / (length(a) * length(b))",
        },
        "AuthorityHash": {
            "python": "hashlib.sha256(f'{agent}:{payload}:{ts}'.encode()).hexdigest()[:32]",
            "typescript": "createHash('sha256').update(`${agent}:${payload}:${ts}`).digest('hex').slice(0,32)",
            "rust": "Sha256::digest(format!('{}:{}:{}', agent, payload, ts))[..16].to_hex()",
            "solidity": "keccak256(abi.encodePacked(agent, payload, ts))",
            "go": "sha256.Sum256([]byte(fmt.Sprintf('%s:%s:%f', agent, payload, ts)))",
        },
    },
    "type_mappings": {
        "np.ndarray": {"rust": "ndarray::Array1<f64>", "go": "[]float64", "ts": "Float64Array"},
        "dataclass": {"rust": "struct", "go": "struct", "ts": "interface/class", "sql": "TABLE"},
        "Dict[str, Any]": {"rust": "HashMap<String, Value>", "go": "map[string]interface{}", "ts": "Record<string, unknown>"},
        "List[float]": {"rust": "Vec<f64>", "go": "[]float64", "ts": "number[]", "sql": "ARRAY or JSON"},
        "Enum": {"rust": "enum", "go": "const iota", "ts": "enum or union type", "sql": "CHECK constraint"},
        "Optional[T]": {"rust": "Option<T>", "go": "*T or nil", "ts": "T | null", "sql": "NULLABLE"},
        "Tuple[float,float,float]": {"rust": "(f64,f64,f64)", "go": "[3]float64", "ts": "[number,number,number]"},
    },
}


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def _demo():
    print("=" * 70)
    print("  Signed-Axis Octree + FF10 Sphere Grid + Fractal Chladni")
    print("=" * 70)

    tree = SignedOctree(max_depth=5, chladni_mode=(3, 2))

    # Insert voxels across all 8 octants
    agents = [
        ("agent.claude", "govern", [0.9, 0.0, 0.1], "sealed", "DR", 0.3, 0.5, 0.1),
        ("agent.gpt", "draft", [0.1, 0.9, 0.0], "public", "AV", -0.4, 0.2, 0.6),
        ("agent.gemini", "research", [0.0, 0.1, 0.9], "internal", "RU", 0.5, -0.3, -0.7),
        ("agent.grok", "challenge", [0.5, 0.5, 0.0], "restricted", "CA", -0.6, -0.4, 0.3),
        ("agent.claude", "architect", [0.8, 0.1, 0.1], "sealed", "UM", 0.7, 0.6, -0.2),
    ]

    print("\nInserting voxels across signed octants:")
    for agent, label, intent, auth, tongue, x, y, z in agents:
        v = tree.insert(x, y, z,
                        wavelength_nm=400 + hash(tongue) % 300,
                        tongue=tongue, authority=auth,
                        intent_vector=intent, intent_label=label,
                        payload={"agent": agent})
        print(f"  {OCTANT_NAMES[v.octant]:8s} | {label:10s} | chladni={v.chladni_value:+.3f} "
              f"| morton={v.morton_code:>10d} | mode={v.chladni_mode}")

    # Mirror +x+y+z octant to -x-y-z
    print("\nMirroring (+x+y+z) -> (-x-y-z):")
    mirrored = tree.mirror_octant((True, True, True), (False, False, False))
    for v in mirrored:
        print(f"  {OCTANT_NAMES[v.octant]:8s} | {v.intent_label:20s} | ({v.x:.2f}, {v.y:.2f}, {v.z:.2f})")

    # Auto cross-branches
    branches = tree.auto_cross_branches()
    print(f"\nCross-branches created: {branches}")

    # Intent query
    print("\nIntent query (governance-like [0.9, 0.0, 0.1]):")
    results = tree.query_by_intent([0.9, 0.0, 0.1], min_similarity=0.3, top_k=3)
    for v, sim in results:
        print(f"  {v.intent_label:15s} sim={sim:.3f} octant={OCTANT_NAMES[v.octant]}")

    # Sphere grid demo
    print("\nSphere grid (first voxel):")
    first = tree.root.collect_all()[0]
    grid = first.sphere_grid
    grid.activate_slot(0)
    grid.activate_slot(1)
    grid.activate_slot(5)  # cross-connection jump
    print(f"  Active slot: {grid.active_slot}")
    print(f"  Activated: {grid.activated_count()}/10")
    path = grid.path_to(9)
    print(f"  Path from slot {grid.active_slot} to slot 9: {path}")

    # Stats
    print(f"\nOctree stats:")
    stats = tree.stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    _demo()
