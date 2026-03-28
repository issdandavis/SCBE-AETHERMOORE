"""Fusion Storage Surfaces — Yu-Gi-Oh-Style Combinations
========================================================

Three fusion surfaces that sacrifice two base surfaces to get one
that's stronger than both:

Fusion 1: CymaticCone (Octree + CymaticVoxelStorage)
  Octree spatial compaction + Chladni access control per voxel.
  Wrong tongue vector → noise. Right vector → data.
  Compacts like octree, protects like cymatic.

Fusion 2: SemiSphereCone (Lattice25D + Octree)
  Hemisphere (safe zone, near origin): wide lattice cells, overlap OK.
  Cone (risky zone, near boundary): tight octree voxels, no overlap.
  Records auto-sort by intent distance into the right zone.
  Adaptive storage density matches the governance cost curve.

Fusion 3: TongueRouter (Sphere + Lattice25D)
  Sphere band_of_focus pre-filters by tongue sector (eliminates 5/6).
  Then lattice handles structured nearest-neighbor in the surviving band.
  Sub-linear query at the cost of sphere routing overhead.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from src.crypto.octree import HyperbolicOctree
from hydra.octree_sphere_grid import HyperbolicLattice25D
from src.kernel.scattered_sphere import ScatteredAttentionSphere

PHI = 1.618033988749895
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")


# =========================================================================== #
#  Shared helpers
# =========================================================================== #


def _chladni_keystream(n: int, m: int, length: int, epoch: int = 0) -> bytes:
    """Generate Chladni-mode XOR keystream (from QC drive pattern)."""
    seed = hashlib.sha256(f"chladni:{n}:{m}:{epoch}".encode()).digest()
    stream = bytearray()
    block = seed
    while len(stream) < length:
        block = hashlib.sha256(block).digest()
        stream.extend(block)
    return bytes(stream[:length])


def _tongue_from_coords(tongue_coords: List[float]) -> str:
    """Pick dominant tongue from 6D coordinates."""
    weights = [PHI**i for i in range(6)]
    weighted = [abs(c) * w for c, w in zip(tongue_coords, weights)]
    idx = weighted.index(max(weighted))
    return TONGUES[idx]


def _intent_distance(coord_3d: np.ndarray) -> float:
    """Poincare ball radius — how far from safe center."""
    return float(np.linalg.norm(coord_3d))


# =========================================================================== #
#  Fusion 1: CymaticCone (Octree + Chladni access control)
# =========================================================================== #


@dataclass
class CymaticLeaf:
    """Octree leaf with Chladni-encoded content."""

    record_id: str
    realm: str
    chladni_n: int
    chladni_m: int
    encoded_content: bytes
    tongue: str


class CymaticCone:
    """Fusion: HyperbolicOctree + CymaticVoxelStorage.

    Insert: record → octree spatial index + Chladni encode content.
    Query: octree spatial lookup → Chladni decode with access vector.
    Wrong vector → noise. Right vector → data.
    """

    def __init__(self, max_depth: int = 3, grid_size: int = 64):
        self.octree = HyperbolicOctree(grid_size=grid_size, max_depth=max_depth)
        self.leaves: Dict[str, CymaticLeaf] = {}
        self._record_count = 0

    def insert(
        self,
        record_id: str,
        coord_3d: np.ndarray,
        tongue_coords: List[float],
        content: bytes,
        realm: str = "path",
    ) -> CymaticLeaf:
        """Insert a record with spatial indexing + Chladni access control."""
        # Octree spatial index
        self.octree.insert(coord_3d, realm)

        # Derive Chladni mode from tongue coords
        vel = math.sqrt(sum(c * c for c in tongue_coords[:3]))
        sec = math.sqrt(sum(c * c for c in tongue_coords[3:]))
        n = max(1, int(vel * 10) % 20 + 1)
        m = max(1, int(sec * 10) % 20 + 1)
        if n == m:
            m += 1

        # Chladni encode
        ks = _chladni_keystream(n, m, len(content))
        encoded = bytes(d ^ k for d, k in zip(content, ks))

        tongue = _tongue_from_coords(tongue_coords)

        leaf = CymaticLeaf(
            record_id=record_id,
            realm=realm,
            chladni_n=n,
            chladni_m=m,
            encoded_content=encoded,
            tongue=tongue,
        )
        self.leaves[record_id] = leaf
        self._record_count += 1
        return leaf

    def retrieve(
        self,
        record_id: str,
        access_tongue_coords: List[float],
    ) -> Optional[bytes]:
        """Retrieve with access vector. Wrong coords → noise."""
        leaf = self.leaves.get(record_id)
        if leaf is None:
            return None

        # Derive access Chladni mode
        vel = math.sqrt(sum(c * c for c in access_tongue_coords[:3]))
        sec = math.sqrt(sum(c * c for c in access_tongue_coords[3:]))
        access_n = max(1, int(vel * 10) % 20 + 1)
        access_m = max(1, int(sec * 10) % 20 + 1)
        if access_n == access_m:
            access_m += 1

        # Decode (XOR with access keystream — matches iff (n,m) same)
        ks = _chladni_keystream(access_n, access_m, len(leaf.encoded_content))
        return bytes(d ^ k for d, k in zip(leaf.encoded_content, ks))

    def query_spatial(self, coord_3d: np.ndarray) -> Optional[str]:
        """Query the octree for realm at a point."""
        return self.octree.query(coord_3d)

    def stats(self) -> Dict[str, Any]:
        oct_stats = self.octree.stats()
        return {
            "type": "CymaticCone",
            "record_count": self._record_count,
            "octree_nodes": oct_stats["node_count"],
            "octree_leaves": oct_stats["leaf_count"],
            "occupied_voxels": oct_stats["occupied_voxels"],
            "node_explosion": round(
                (oct_stats["node_count"] + oct_stats["leaf_count"])
                / max(1, self._record_count),
                4,
            ),
            "compaction_score": round(
                self._record_count
                / max(1, oct_stats["node_count"] + oct_stats["leaf_count"]),
                6,
            ),
            "unique_chladni_modes": len(
                {(leaf.chladni_n, leaf.chladni_m) for leaf in self.leaves.values()}
            ),
        }


# =========================================================================== #
#  Fusion 2: SemiSphereCone (Lattice hemisphere + Octree cone)
# =========================================================================== #


class SemiSphereCone:
    """Fusion: HyperbolicLattice25D (hemisphere) + HyperbolicOctree (cone).

    The Poincare ball is split at a radius threshold (default 0.5):
    - Hemisphere (r < threshold): wide lattice cells, overlap is fine
    - Cone (r >= threshold): tight octree voxels, no collision

    Records auto-sort by their distance from origin. Safe records get
    loose, fast storage. Risky records get precise, tight storage.
    """

    def __init__(
        self,
        radius_threshold: float = 0.5,
        lattice_cell_size: float = 0.5,
        lattice_quadtree_capacity: int = 12,
        octree_max_depth: int = 4,
    ):
        self.radius_threshold = radius_threshold

        # Hemisphere: wide cells, tolerant of overlap
        self.lattice = HyperbolicLattice25D(
            cell_size=lattice_cell_size,
            index_mode="hybrid",
            quadtree_capacity=lattice_quadtree_capacity,
        )

        # Cone: tight octree for boundary records
        self.octree = HyperbolicOctree(max_depth=octree_max_depth)

        self._hemisphere_count = 0
        self._cone_count = 0
        self._records: Dict[str, str] = {}  # id → zone

    def insert(
        self,
        record_id: str,
        coord_3d: np.ndarray,
        x: float,
        y: float,
        phase_rad: float,
        tongue: str = "KO",
        authority: str = "public",
        intent_vector: Optional[List[float]] = None,
    ) -> str:
        """Insert a record. Returns 'hemisphere' or 'cone'."""
        radius = float(np.linalg.norm(coord_3d))

        if radius < self.radius_threshold:
            # Hemisphere: lattice storage
            self.lattice.insert_bundle(
                x=x,
                y=y,
                phase_rad=phase_rad,
                tongue=tongue,
                authority=authority,
                intent_vector=intent_vector or [0.5, 0.5, 0.5],
                intent_label=record_id[:48],
                bundle_id=record_id,
                wavelength_nm=550.0,
            )
            self._hemisphere_count += 1
            self._records[record_id] = "hemisphere"
            return "hemisphere"
        else:
            # Cone: octree storage
            realm = "shadow_realm" if radius > 0.8 else "path"
            self.octree.insert(coord_3d, realm)
            self._cone_count += 1
            self._records[record_id] = "cone"
            return "cone"

    def query_nearest(
        self,
        x: float,
        y: float,
        phase_rad: float,
        intent_vector: Optional[List[float]] = None,
        tongue: str = "KO",
        top_k: int = 5,
    ) -> list:
        """Query nearest in the hemisphere zone (lattice)."""
        return self.lattice.query_nearest(
            x=x,
            y=y,
            phase_rad=phase_rad,
            intent_vector=intent_vector or [0.5, 0.5, 0.5],
            tongue=tongue,
            top_k=top_k,
        )

    def query_spatial(self, coord_3d: np.ndarray) -> Optional[str]:
        """Query the cone zone (octree)."""
        return self.octree.query(coord_3d)

    def stats(self) -> Dict[str, Any]:
        total = self._hemisphere_count + self._cone_count
        oct_stats = self.octree.stats()
        lat_stats = self.lattice.stats()

        hemisphere_nodes = lat_stats["occupied_cells"]
        cone_nodes = oct_stats["node_count"] + oct_stats["leaf_count"]
        total_nodes = hemisphere_nodes + cone_nodes

        return {
            "type": "SemiSphereCone",
            "record_count": total,
            "hemisphere_count": self._hemisphere_count,
            "cone_count": self._cone_count,
            "hemisphere_ratio": round(self._hemisphere_count / max(1, total), 4),
            "cone_ratio": round(self._cone_count / max(1, total), 4),
            "hemisphere_nodes": hemisphere_nodes,
            "cone_nodes": cone_nodes,
            "total_nodes": total_nodes,
            "node_explosion": round(total_nodes / max(1, total), 4),
            "compaction_score": round(total / max(1, total_nodes), 6),
            "lattice_overlap_heat": round(
                len(self.lattice.overlapping_cells()) / max(1, hemisphere_nodes), 4
            ),
        }


# =========================================================================== #
#  Fusion 3: TongueRouter (Sphere pre-filter + Lattice query)
# =========================================================================== #


class TongueRouter:
    """Fusion: ScatteredAttentionSphere + HyperbolicLattice25D.

    Insert: record → lattice storage + accumulate sphere feature row.
    Query: sphere band_of_focus → identify dominant tongue → lattice
    query with tongue filter (eliminates ~5/6 of the search space).
    """

    def __init__(
        self,
        sparsity_threshold: float = 0.01,
        lattice_cell_size: float = 0.5,
        lattice_quadtree_capacity: int = 12,
    ):
        self.sphere = ScatteredAttentionSphere(sparsity_threshold=sparsity_threshold)
        self.lattice = HyperbolicLattice25D(
            cell_size=lattice_cell_size,
            index_mode="hybrid",
            quadtree_capacity=lattice_quadtree_capacity,
        )
        self._feature_rows: List[List[float]] = []
        self._record_count = 0
        self._scattered = False

    def insert(
        self,
        record_id: str,
        x: float,
        y: float,
        phase_rad: float,
        tongue: str,
        tongue_coords: List[float],
        intent_vector: List[float],
        authority: str = "public",
    ) -> None:
        self.lattice.insert_bundle(
            x=x,
            y=y,
            phase_rad=phase_rad,
            tongue=tongue,
            authority=authority,
            intent_vector=intent_vector,
            intent_label=record_id[:48],
            bundle_id=record_id,
            wavelength_nm=550.0,
        )
        # Accumulate feature row for sphere batch scatter
        self._feature_rows.append(tongue_coords + intent_vector)
        self._record_count += 1
        self._scattered = False

    def _ensure_scattered(self) -> None:
        """Flush feature rows into sphere (batch operation)."""
        if self._scattered or not self._feature_rows:
            return
        matrix = np.array(self._feature_rows, dtype=float)
        self.sphere.scatter(matrix, "tongue_router", layer_radius=1.0)
        self._scattered = True

    def route_tongue(self, phi_wall: float, bandwidth: float = 0.3) -> str:
        """Use sphere band_of_focus to find the dominant tongue at a phase angle."""
        self._ensure_scattered()
        band = self.sphere.band_of_focus(phi_wall, bandwidth)
        if not band.tongue_distribution:
            return "KO"
        return max(band.tongue_distribution.items(), key=lambda x: x[1])[0]

    def query_routed(
        self,
        x: float,
        y: float,
        phase_rad: float,
        intent_vector: List[float],
        phi_wall: float = 0.0,
        top_k: int = 5,
    ) -> list:
        """Route through sphere then query lattice with tongue hint."""
        dominant_tongue = self.route_tongue(phi_wall)
        return self.lattice.query_nearest(
            x=x,
            y=y,
            phase_rad=phase_rad,
            intent_vector=intent_vector,
            tongue=dominant_tongue,
            top_k=top_k,
        )

    def stats(self) -> Dict[str, Any]:
        self._ensure_scattered()
        lat_stats = self.lattice.stats()
        sph_stats = self.sphere.stats()

        lat_nodes = lat_stats["occupied_cells"]
        sph_points = sph_stats.get("total_points", 0)

        # Tongue distribution evenness from sweep
        sweep = self.sphere.sweep(steps=6) if sph_points > 0 else []
        tongue_evenness = 0.0
        if sweep:
            for band in sweep:
                dist = band.tongue_distribution
                if dist:
                    vals = list(dist.values())
                    total = sum(vals)
                    if total > 0:
                        probs = [v / total for v in vals]
                        entropy = -sum(p * math.log(p + 1e-12) for p in probs)
                        max_ent = math.log(max(1, len(probs)))
                        tongue_evenness += entropy / max(max_ent, 1e-9)
            tongue_evenness /= max(1, len(sweep))

        return {
            "type": "TongueRouter",
            "record_count": self._record_count,
            "lattice_nodes": lat_nodes,
            "sphere_points": sph_points,
            "total_nodes": lat_nodes + sph_points,
            "node_explosion": round(
                (lat_nodes + sph_points) / max(1, self._record_count), 4
            ),
            "lattice_compaction": round(self._record_count / max(1, lat_nodes), 6),
            "tongue_evenness": round(tongue_evenness, 4),
        }
