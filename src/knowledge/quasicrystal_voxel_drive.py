"""
Quasi-Crystal Voxel Storage Drive — 6D Tensor Arrays

Fuses:
  - QuasicrystalLattice (6D -> 3D+3D icosahedral projection, phason rekeying)
  - CymaticVoxelStorage (Chladni pattern access control, nodal line encoding)
  - Sacred Tongues (6D coordinate system with phi weights)
  - FibonacciSphereGrid (even coverage placement)

Architecture:
  Knowledge chunks are stored in a 6D tensor array indexed by Sacred Tongue
  coordinates. Each cell in the tensor is a quasicrystal lattice point with
  cymatic access control — data is only readable with the correct tongue vector.

  The grid grows as new data arrives. Each surface node leads to a depth tree
  of related content. Phase separation (from the Octagonal Octree research)
  keeps categories in distinct "fluid phases" that don't mix without emulsifier
  tongues (UM/DR).

Usage:
    drive = QuasiCrystalVoxelDrive(resolution=64)
    drive.store(chunk_id, content_bytes, tongue_coords)
    data = drive.retrieve(chunk_id, access_vector)
    drive.export("knowledge_drive.qcv")
"""

import math
import json
import hashlib
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Golden Ratio — fundamental to icosahedral symmetry
PHI = (1 + np.sqrt(5)) / 2
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_WEIGHTS = [PHI ** i for i in range(6)]

# Viscosity per tongue (from Octagonal Octree research note 114)
TONGUE_VISCOSITY = {
    "KO": 1 / (1 + 1.0 * PHI),    # Very low — high fluidity
    "AV": 1 / (1 + 0.8 * PHI),    # Low — flows easily
    "RU": 1 / (1 + 0.3 * PHI),    # High — slows waves
    "CA": 1 / (1 + 0.4 * PHI),    # Medium-high — shapes under pressure
    "UM": 0.5,                      # Variable — emulsifier
    "DR": 0.5,                      # Variable — emulsifier
}


@dataclass
class VoxelCell:
    """A single cell in the 6D tensor array."""
    cell_id: str
    tongue_index: list  # 6D integer index in the tensor
    tongue_coords: list  # 6D float coordinates (Sacred Tongue)
    physical_projection: list  # 3D physical space (from QC lattice)
    perpendicular_projection: list  # 3D validation space
    chladni_mode: tuple  # (n, m) for cymatic encoding
    content_hash: str
    content_size: int
    category: str
    depth: int = 0
    parent_id: str = ""
    children: list = field(default_factory=list)
    phase: str = "laminar"  # laminar | turbulent | emulsion
    viscosity: float = 0.5
    is_valid: bool = True


@dataclass
class TensorSlab:
    """A slice of the 6D tensor along one tongue dimension."""
    tongue: str
    tongue_index: int
    cells: dict  # cell_id -> VoxelCell
    total_content_bytes: int = 0
    phase_state: str = "laminar"


class QuasiCrystalVoxelDrive:
    """
    6D Tensor Storage Drive using Quasicrystal Lattice + Cymatic Voxels.

    The drive is a 6D tensor array where:
    - Axes = Sacred Tongues (KO, AV, RU, CA, UM, DR)
    - Each cell = a quasicrystal lattice point with cymatic access control
    - Data is only readable with the correct tongue vector
    - Phase separation keeps categories in distinct fluid phases
    - The grid grows as data arrives (no fixed size)
    """

    def __init__(self, resolution: int = 64, lattice_constant: float = 1.0):
        self.resolution = resolution
        self.lattice_constant = lattice_constant

        # 6D -> 3D projection matrices (icosahedral symmetry)
        self.M_par, self.M_perp = self._build_projection_matrices()

        # Phason state (secret key component)
        self._phason_strain = np.zeros(3)
        self._phason_epoch = 0
        self.acceptance_radius = 1.5 * lattice_constant

        # Storage
        self.cells: dict[str, VoxelCell] = {}
        self.tensor_slabs: dict[str, TensorSlab] = {
            name: TensorSlab(tongue=name, tongue_index=i, cells={})
            for i, name in enumerate(TONGUE_NAMES)
        }
        self.depth_trees: dict[str, list] = {}
        self.content_store: dict[str, bytes] = {}  # cell_id -> encoded bytes

        # Category -> phase mapping (from fluid dynamics model)
        self.phase_map: dict[str, str] = {}

    def _build_projection_matrices(self):
        """Build 6D -> 3D icosahedral projection matrices."""
        norm = 1 / np.sqrt(1 + PHI ** 2)

        # Physical space basis (E_parallel)
        e_par = np.array([
            [1, PHI, 0], [-1, PHI, 0],
            [0, 1, PHI], [0, -1, PHI],
            [PHI, 0, 1], [PHI, 0, -1],
        ]).T * norm

        # Perpendicular/validation space (E_perp) — Galois conjugation
        e_perp = np.array([
            [1, -1/PHI, 0], [-1, -1/PHI, 0],
            [0, 1, -1/PHI], [0, -1, -1/PHI],
            [-1/PHI, 0, 1], [-1/PHI, 0, -1],
        ]).T * norm

        return e_par, e_perp

    def _project_6d(self, coords: list) -> tuple:
        """Project 6D tongue coordinates to 3D physical + 3D perpendicular."""
        n = np.array(coords, dtype=float)
        r_phys = (self.M_par @ n).tolist()
        r_perp = (self.M_perp @ n).tolist()
        return r_phys, r_perp

    def _coords_to_chladni(self, coords: list) -> tuple:
        """Convert 6D tongue coordinates to Chladni (n, m) mode pair."""
        # Split coords into velocity (KO, AV, RU) and security (CA, UM, DR)
        vel = np.linalg.norm(coords[:3])
        sec = np.linalg.norm(coords[3:])
        n = max(1, int(vel * 10) % 20 + 1)
        m = max(1, int(sec * 10) % 20 + 1)
        if n == m:
            m += 1
        return (n, m)

    def _chladni_encode(self, data: bytes, n: int, m: int) -> bytes:
        """Cymatic encode: XOR data with Chladni-derived key stream."""
        # Generate key stream from Chladni pattern
        key_seed = hashlib.sha256(f"chladni:{n}:{m}:{self._phason_epoch}".encode()).digest()
        key_stream = bytearray()
        block = key_seed
        while len(key_stream) < len(data):
            block = hashlib.sha256(block).digest()
            key_stream.extend(block)

        # XOR encode
        encoded = bytes(d ^ k for d, k in zip(data, key_stream[:len(data)]))
        return encoded

    def _dominant_tongue(self, coords: list) -> tuple:
        """Find dominant tongue dimension and compute viscosity."""
        weighted = [abs(c) * w for c, w in zip(coords, TONGUE_WEIGHTS)]
        dom_idx = weighted.index(max(weighted))
        dom_name = TONGUE_NAMES[dom_idx]
        viscosity = TONGUE_VISCOSITY[dom_name]
        return dom_name, dom_idx, viscosity

    def _tensor_index(self, coords: list) -> list:
        """Convert float coords to integer tensor indices."""
        return [
            max(0, min(self.resolution - 1, int((c + 1) / 2 * self.resolution)))
            for c in coords
        ]

    def store(self, chunk_id: str, content: bytes, tongue_coords: list,
              category: str = "general", parent_id: str = "") -> VoxelCell:
        """
        Store a knowledge chunk in the 6D tensor drive.

        Args:
            chunk_id: Unique identifier
            content: Raw content bytes
            tongue_coords: 6D Sacred Tongue coordinates
            category: Knowledge category
            parent_id: Parent cell for depth tree

        Returns:
            VoxelCell with storage metadata
        """
        # Project to 3D + 3D
        phys, perp = self._project_6d(tongue_coords)

        # Compute Chladni mode
        n, m = self._coords_to_chladni(tongue_coords)

        # Cymatic encode the content
        encoded = self._chladni_encode(content, n, m)

        # Compute tensor index
        t_index = self._tensor_index(tongue_coords)

        # Determine dominant tongue and viscosity
        dom_tongue, dom_idx, viscosity = self._dominant_tongue(tongue_coords)

        # Validate against quasicrystal acceptance window
        r_perp = np.array(perp)
        distance = np.linalg.norm(r_perp - self._phason_strain)
        is_valid = distance < self.acceptance_radius

        # Determine phase state
        phase = self._determine_phase(category, viscosity)

        cell = VoxelCell(
            cell_id=chunk_id,
            tongue_index=t_index,
            tongue_coords=tongue_coords,
            physical_projection=phys,
            perpendicular_projection=perp,
            chladni_mode=(n, m),
            content_hash=hashlib.sha256(content).hexdigest()[:16],
            content_size=len(content),
            category=category,
            depth=0 if not parent_id else self._get_depth(parent_id) + 1,
            parent_id=parent_id,
            phase=phase,
            viscosity=viscosity,
            is_valid=is_valid,
        )

        # Store
        self.cells[chunk_id] = cell
        self.content_store[chunk_id] = encoded
        self.tensor_slabs[dom_tongue].cells[chunk_id] = cell
        self.tensor_slabs[dom_tongue].total_content_bytes += len(content)

        # Depth tree
        if parent_id and parent_id in self.cells:
            self.cells[parent_id].children.append(chunk_id)
            self.depth_trees.setdefault(parent_id, []).append(chunk_id)

        return cell

    def retrieve(self, chunk_id: str, access_coords: list) -> Optional[bytes]:
        """
        Retrieve content from the drive using tongue coordinates as access key.

        Only returns data if the access vector matches the stored Chladni mode.
        Wrong vector = noise (cymatic access control).
        """
        cell = self.cells.get(chunk_id)
        if not cell:
            return None

        encoded = self.content_store.get(chunk_id)
        if not encoded:
            return None

        # Compute Chladni mode from access coordinates
        access_n, access_m = self._coords_to_chladni(access_coords)

        # Decode with access Chladni mode
        decoded = self._chladni_encode(encoded, access_n, access_m)

        # If access mode matches stored mode, XOR cancels out = original data
        # If wrong mode, result is noise
        return decoded

    def _determine_phase(self, category: str, viscosity: float) -> str:
        """Determine phase state based on category and viscosity (fluid dynamics)."""
        # Categories with high viscosity stay laminar
        if viscosity > 0.6:
            return "laminar"
        # Low viscosity categories can become turbulent
        if viscosity < 0.3:
            return "turbulent" if len(self.cells) > 100 else "laminar"
        return "laminar"

    def _get_depth(self, cell_id: str) -> int:
        cell = self.cells.get(cell_id)
        return cell.depth if cell else 0

    def phason_rekey(self, entropy: bytes):
        """Apply phason shift — atomically invalidates previous access window."""
        h = hashlib.sha256(entropy).digest()
        self._phason_strain = np.array([
            int.from_bytes(h[0:4], "big") / (2**32) * 2 - 1,
            int.from_bytes(h[4:8], "big") / (2**32) * 2 - 1,
            int.from_bytes(h[8:12], "big") / (2**32) * 2 - 1,
        ]) * self.acceptance_radius * 2.0
        self._phason_epoch += 1

    def get_slab(self, tongue: str) -> dict:
        """Get all cells in a tongue slab."""
        slab = self.tensor_slabs.get(tongue)
        if not slab:
            return {}
        return {
            "tongue": slab.tongue,
            "total_cells": len(slab.cells),
            "total_bytes": slab.total_content_bytes,
            "phase_state": slab.phase_state,
            "cells": list(slab.cells.keys()),
        }

    def query_nearby(self, coords: list, radius: float = 0.3) -> list[str]:
        """Find cells near a point in 6D tongue space."""
        results = []
        for cell_id, cell in self.cells.items():
            dist = math.sqrt(sum(
                (a - b) ** 2 * w
                for a, b, w in zip(coords, cell.tongue_coords, TONGUE_WEIGHTS)
            )) / sum(TONGUE_WEIGHTS)
            if dist < radius:
                results.append((cell_id, dist))
        results.sort(key=lambda x: x[1])
        return [r[0] for r in results]

    def stats(self) -> dict:
        """Drive statistics."""
        return {
            "total_cells": len(self.cells),
            "total_content_bytes": sum(c.content_size for c in self.cells.values()),
            "phason_epoch": self._phason_epoch,
            "resolution": self.resolution,
            "slabs": {
                name: {
                    "cells": len(slab.cells),
                    "bytes": slab.total_content_bytes,
                }
                for name, slab in self.tensor_slabs.items()
            },
            "categories": {},
            "max_depth": max((c.depth for c in self.cells.values()), default=0),
            "phase_distribution": {},
        }

    def export(self, path: str) -> str:
        """Export drive metadata (not content) for visualization/upload."""
        data = {
            "drive_type": "QuasiCrystalVoxelDrive",
            "dimensions": 6,
            "tongue_names": TONGUE_NAMES,
            "tongue_weights": [float(w) for w in TONGUE_WEIGHTS],
            "tongue_viscosity": TONGUE_VISCOSITY,
            "phason_epoch": self._phason_epoch,
            "resolution": self.resolution,
            "total_cells": len(self.cells),
            "cells": {
                cid: {
                    "tongue_index": c.tongue_index,
                    "tongue_coords": c.tongue_coords,
                    "physical_3d": c.physical_projection,
                    "perpendicular_3d": c.perpendicular_projection,
                    "chladni_mode": list(c.chladni_mode),
                    "content_hash": c.content_hash,
                    "content_size": c.content_size,
                    "category": c.category,
                    "depth": c.depth,
                    "parent_id": c.parent_id,
                    "children": c.children,
                    "phase": c.phase,
                    "viscosity": c.viscosity,
                    "is_valid": c.is_valid,
                }
                for cid, c in self.cells.items()
            },
            "slabs": {
                name: {
                    "cells": len(slab.cells),
                    "bytes": slab.total_content_bytes,
                }
                for name, slab in self.tensor_slabs.items()
            },
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(data, indent=2))
        return path


def demo():
    """Demo: store and retrieve knowledge chunks in the QC voxel drive."""
    print("=" * 60)
    print("Quasi-Crystal Voxel Drive — 6D Tensor Storage")
    print("=" * 60)

    drive = QuasiCrystalVoxelDrive(resolution=64)

    # Store some test chunks
    test_data = [
        ("chunk-001", b"Hyperbolic geometry provides exponential cost scaling for adversarial behavior",
         [0.3, 0.1, 0.2, 0.7, 0.1, 0.1], "math"),
        ("chunk-002", b"Post-quantum lattice-based cryptography resists Shor's algorithm",
         [0.2, 0.1, 0.2, 0.8, 0.2, 0.3], "security"),
        ("chunk-003", b"Multi-agent governance consensus using Byzantine fault tolerance",
         [0.8, 0.1, 0.3, 0.1, 0.1, 0.2], "governance"),
        ("chunk-004", b"Sacred Tongue tokenizer maps 6 languages to phi-weighted dimensions",
         [0.2, 0.2, 0.2, 0.2, 0.2, 0.8], "tongues"),
    ]

    for cid, content, coords, cat in test_data:
        cell = drive.store(cid, content, coords, category=cat)
        print(f"  Stored {cid}: Chladni({cell.chladni_mode[0]},{cell.chladni_mode[1]}) "
              f"phase={cell.phase} viscosity={cell.viscosity:.3f}")

    # Retrieve with correct coords
    print(f"\nRetrieve with correct vector:")
    data = drive.retrieve("chunk-001", [0.3, 0.1, 0.2, 0.7, 0.1, 0.1])
    print(f"  chunk-001: {data[:50]}..." if data else "  FAILED")

    # Retrieve with wrong coords (should be noise)
    print(f"\nRetrieve with wrong vector:")
    noise = drive.retrieve("chunk-001", [0.9, 0.9, 0.9, 0.1, 0.1, 0.1])
    print(f"  chunk-001: {noise[:50]}..." if noise else "  FAILED")

    # Query nearby
    print(f"\nQuery near math region [0.2, 0.1, 0.2, 0.7, 0.1, 0.1]:")
    nearby = drive.query_nearby([0.2, 0.1, 0.2, 0.7, 0.1, 0.1], radius=0.5)
    for nid in nearby:
        print(f"  {nid}: {drive.cells[nid].category}")

    # Export
    path = drive.export("training/intake/qc_voxel_drive.json")
    print(f"\nExported: {path}")

    stats = drive.stats()
    print(f"\nDrive Stats:")
    print(f"  Total cells: {stats['total_cells']}")
    print(f"  Total bytes: {stats['total_content_bytes']}")
    print(f"  Max depth: {stats['max_depth']}")
    for name, slab in stats["slabs"].items():
        if slab["cells"] > 0:
            print(f"  Slab {name}: {slab['cells']} cells, {slab['bytes']} bytes")


if __name__ == "__main__":
    demo()
