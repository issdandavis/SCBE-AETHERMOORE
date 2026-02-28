"""
BraidedVoxelStore — Voxel Comb
===============================

Fused spatial storage: CymaticVoxelStorage (Chladni patterns) +
HyperbolicOctree (sparse Poincare ball indexing).

The "honeycomb" — fast spatial storage for clean, indexed data.

@layer Layer 5 (Poincare), Layer 10 (Cymatic Voxel)
@component BraidedStorage.VoxelComb
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.braided_storage.types import BraidedPayload
from src.crypto.octree import HyperbolicOctree, SpectralVoxel
from src.symphonic_cipher.core.cymatic_voxel_storage import (
    CymaticVoxelStorage,
    VoxelAccessVector,
)

# Sacred Tongue to frequency mapping for spectral metadata
TONGUE_FREQ: Dict[str, float] = {
    "KO": 440.0,
    "AV": 528.0,
    "RU": 396.0,
    "CA": 639.0,
    "UM": 741.0,
    "DR": 852.0,
}

# Tongue to realm mapping for octree insertion
TONGUE_REALM: Dict[str, str] = {
    "KO": "light_realm",
    "AV": "light_realm",
    "RU": "path",
    "CA": "path",
    "UM": "shadow_realm",
    "DR": "shadow_realm",
}


class VoxelComb:
    """Fused honeycomb storage: Chladni voxels + hyperbolic octree.

    deposit() stores data in both:
    - CymaticVoxelStorage for Chladni-pattern encoded voxels
    - HyperbolicOctree for sparse spatial indexing with spectral metadata

    retrieve() decodes from cymatic storage and returns spectral metadata.
    cluster() and find_neighbors() use the octree's spectral capabilities.
    """

    def __init__(
        self,
        *,
        resolution: int = 32,
        octree_grid_size: int = 64,
        octree_max_depth: int = 6,
    ):
        self._cymatic = CymaticVoxelStorage(resolution=resolution)
        self._octree = HyperbolicOctree(
            grid_size=octree_grid_size,
            max_depth=octree_max_depth,
        )
        self._resolution = resolution
        # Map cube_id -> (encoded_data, access_vector, braided_payload)
        self._store: Dict[str, Tuple[np.ndarray, VoxelAccessVector, BraidedPayload]] = {}

    # ------------------------------------------------------------------
    #  deposit
    # ------------------------------------------------------------------

    def deposit(self, braided: BraidedPayload) -> str:
        """Deposit a braided payload into the honeycomb.

        Returns:
            cube_id: Unique identifier for this voxel entry.
        """
        cube_id = f"vx_{uuid.uuid4().hex[:12]}"

        # Build 6D access vector from braid phase state + tongue trits
        access_vec = self._access_vector_from_braid(braided)

        # Encode data into cymatic voxel (resize to resolution grid)
        data_grid = self._bytes_to_grid(braided.raw_bytes)
        encoded = self._cymatic.encode(data_grid, access_vec)

        # Store encoded data
        self._store[cube_id] = (encoded, access_vec, braided)

        # Insert into octree with spectral metadata
        coord_3d = self._tongue_to_poincare(braided.semantic_bits.dominant_tongue)
        tongue = braided.semantic_bits.dominant_tongue
        realm = TONGUE_REALM.get(tongue, "path")
        fp_hash = hashlib.md5(
            braided.semantic_bits.sha256_hash.encode()
        ).hexdigest()[:16]

        self._octree.insert_with_fingerprint(
            coord_3d=coord_3d,
            realm=realm,
            fingerprint_hash=fp_hash,
            spectral_centroid=TONGUE_FREQ.get(tongue, 440.0),
            dominant_freq=TONGUE_FREQ.get(tongue, 440.0),
            polarity="light" if braided.strand_intent > 0.5 else "balanced",
        )

        return cube_id

    # ------------------------------------------------------------------
    #  retrieve
    # ------------------------------------------------------------------

    def retrieve(self, cube_id: str) -> Optional[Tuple[np.ndarray, BraidedPayload]]:
        """Retrieve and decode a voxel by cube_id.

        Returns:
            (decoded_grid, braided_payload) or None if not found.
        """
        entry = self._store.get(cube_id)
        if entry is None:
            return None

        encoded, access_vec, braided = entry
        decoded = self._cymatic.decode(encoded, access_vec)
        return decoded, braided

    # ------------------------------------------------------------------
    #  cluster / search
    # ------------------------------------------------------------------

    def cluster(self, tongue: Optional[str] = None) -> Dict[str, int]:
        """Cluster stored voxels by polarity (or frequency band if tongue given).

        If tongue is specified, returns frequency band clusters.
        Otherwise returns polarity clusters.
        """
        if tongue is not None:
            freq = TONGUE_FREQ.get(tongue, 440.0)
            # Cluster by frequency band centered on tongue frequency
            bands = [
                (freq - 100, freq + 100),
                (0, freq - 100),
                (freq + 100, float("inf")),
            ]
            clusters = self._octree.cluster_by_frequency_band(bands)
            return {name: len(voxels) for name, voxels in clusters.items()}

        polarity_clusters = self._octree.cluster_by_polarity()
        return {name: len(voxels) for name, voxels in polarity_clusters.items()}

    def find_neighbors(
        self,
        fingerprint_hash: str,
        max_distance: float = 0.5,
        max_results: int = 10,
    ) -> List[Tuple[np.ndarray, SpectralVoxel, float]]:
        """Find spectrally similar voxels by fingerprint."""
        target = SpectralVoxel(
            color="cyan",
            fingerprint_hash=fingerprint_hash,
            spectral_centroid=440.0,
            dominant_freq=440.0,
            polarity="balanced",
        )
        return self._octree.find_spectral_neighbors(
            target, max_distance=max_distance, max_results=max_results
        )

    # ------------------------------------------------------------------
    #  Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _access_vector_from_braid(braided: BraidedPayload) -> VoxelAccessVector:
        """Map braid phase state + tongue trits to 6D VoxelAccessVector.

        velocity dims <- first 3 tongue trits (KO, AV, RU)
        security dims <- last 3 tongue trits (CA, UM, DR)

        Scaled to ensure non-zero n,m pair.
        """
        trits = braided.semantic_bits.tongue_trits
        # Pad to 6 if needed
        while len(trits) < 6:
            trits.append(0)

        # Scale: trit {-1,0,+1} -> {1, 2, 3} to ensure positive non-zero
        def _trit_to_vel(t: int) -> float:
            return float(t + 2)  # -1->1, 0->2, +1->3

        return VoxelAccessVector(
            velocity_x=_trit_to_vel(trits[0]),
            velocity_y=_trit_to_vel(trits[1]),
            velocity_z=_trit_to_vel(trits[2]),
            security_x=_trit_to_vel(trits[3]),
            security_y=_trit_to_vel(trits[4]),
            security_z=_trit_to_vel(trits[5]),
        )

    @staticmethod
    def _tongue_to_poincare(tongue: str) -> np.ndarray:
        """Map a Sacred Tongue to a 3D position in the Poincare ball.

        Each tongue gets a deterministic position based on its frequency:
        - Angle derived from tongue index
        - Radius derived from frequency (higher freq = closer to boundary)
        """
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        idx = tongues.index(tongue) if tongue in tongues else 0
        angle = (idx / 6.0) * 2 * np.pi

        freq = TONGUE_FREQ.get(tongue, 440.0)
        radius = min(0.85, freq / 1000.0)  # Keep inside Poincare ball

        return np.array([
            radius * np.cos(angle),
            radius * np.sin(angle),
            0.1 * (idx - 2.5),  # Small z spread
        ])

    def _bytes_to_grid(self, data: bytes) -> np.ndarray:
        """Convert raw bytes to a resolution x resolution grid for cymatic encoding.

        Pads or truncates to fill the grid, then normalizes to [0, 1].
        """
        n = self._resolution * self._resolution
        # Pad data to fill grid
        if len(data) < n:
            padded = data + b"\x00" * (n - len(data))
        else:
            padded = data[:n]

        arr = np.frombuffer(padded, dtype=np.uint8).astype(float)
        arr = arr.reshape(self._resolution, self._resolution)
        # Normalize to [0, 1]
        return arr / 255.0

    # ------------------------------------------------------------------
    #  Diagnostics
    # ------------------------------------------------------------------

    @property
    def voxel_count(self) -> int:
        return len(self._store)

    @property
    def octree_point_count(self) -> int:
        return self._octree.point_count

    def occupancy(self) -> float:
        return self._octree.occupancy_ratio()
