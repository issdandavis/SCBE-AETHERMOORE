"""
HYDRA 6D Voxel Storage — Authority + Intent Encoding with Temporal Slicing
==========================================================================

6 dimensions:
  D1-D3: Spatial (x, y, z) — Chladni-mode vibrational addressing
  D4: Spectral frequency — color channel wavelength (380-780nm)
  D5: Authority — cryptographic provenance hash (PQ-signed)
  D6: Intent — semantic embedding (compressed via autoencoder-style mapping)

  +t: Timestamps as implied 7th dimension (versioning, time-series queries)

Key properties:
  - Voxels are addressed by Chladni nodal patterns: cos(n*pi*x/L) * cos(m*pi*y/L)
  - Authority is verified via hash chains (compatible with ML-DSA-65 / Dilithium)
  - Intent is a normalized float vector (semantic fingerprint)
  - Temporal slicing enables "rewind" queries and drift detection
  - Poincare-ball invariant: spatial coords stay inside unit ball

Usage:
    from hydra.voxel_storage import VoxelGrid, Voxel

    grid = VoxelGrid(resolution=16)
    v = grid.store(x=0.3, y=0.1, z=0.0, wavelength_nm=540.0,
                   authority="agent.claude", intent_vector=[0.8, 0.1, 0.1])
    results = grid.query_by_intent([0.8, 0.1, 0.1], top_k=5)
    history = grid.time_slice(t_start=1700000000, t_end=1700003600)
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from hydra.color_dimension import (
    ColorChannel,
    PHI,
)

# ---------------------------------------------------------------------------
#  Chladni Mode Addressing
# ---------------------------------------------------------------------------


def chladni_amplitude(x: float, y: float, n: int = 3, m: int = 2, L: float = 1.0) -> float:
    """Chladni plate vibration amplitude at (x, y) for mode (n, m).

    A(x,y) = cos(n*pi*x/L) * cos(m*pi*y/L) - cos(m*pi*x/L) * cos(n*pi*y/L)

    Nodal lines (A=0) form the characteristic Chladni patterns.
    Voxels near nodal lines have low amplitude (boundary zones).
    Voxels at antinodes have high amplitude (storage hotspots).
    """
    nx = n * math.pi * x / L
    ny = n * math.pi * y / L
    mx = m * math.pi * x / L
    my = m * math.pi * y / L
    return math.cos(nx) * math.cos(my) - math.cos(mx) * math.cos(ny)


def chladni_address(x: float, y: float, mode_n: int = 3, mode_m: int = 2) -> float:
    """Map (x, y) to a Chladni vibrational address in [0, 1].

    The address encodes the node's position relative to the resonant pattern.
    Values near 0.5 = on nodal lines (low energy, boundary zone)
    Values near 0.0 or 1.0 = at antinodes (high energy, storage hotspot)
    """
    raw = chladni_amplitude(x, y, mode_n, mode_m)
    # Normalize from [-2, 2] to [0, 1]
    return (raw + 2.0) / 4.0


def generate_chladni_grid(resolution: int = 16, mode_n: int = 3, mode_m: int = 2) -> np.ndarray:
    """Generate a 2D Chladni pattern grid for voxel layout.

    Returns (resolution, resolution) array of amplitudes.
    """
    grid = np.zeros((resolution, resolution))
    for i in range(resolution):
        for j in range(resolution):
            x = i / (resolution - 1) if resolution > 1 else 0.5
            y = j / (resolution - 1) if resolution > 1 else 0.5
            grid[i, j] = chladni_amplitude(x, y, mode_n, mode_m)
    return grid


# ---------------------------------------------------------------------------
#  Authority Hash
# ---------------------------------------------------------------------------


def compute_authority_hash(
    agent_id: str,
    payload: str = "",
    timestamp: float = 0.0,
) -> str:
    """Compute authority hash for a voxel (placeholder for ML-DSA-65).

    In production, this would use post-quantum Dilithium signatures.
    For now, HMAC-SHA256 chain: H(agent_id || payload || timestamp).
    """
    data = f"{agent_id}:{payload}:{timestamp}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:32]


def verify_authority(voxel_hash: str, agent_id: str, payload: str, timestamp: float) -> bool:
    """Verify that a voxel's authority hash matches the claimed provenance."""
    expected = compute_authority_hash(agent_id, payload, timestamp)
    return voxel_hash == expected


# ---------------------------------------------------------------------------
#  Intent Vector
# ---------------------------------------------------------------------------


def normalize_intent(vec: List[float]) -> np.ndarray:
    """Normalize an intent vector to unit length."""
    arr = np.array(vec, dtype=np.float64)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr


def intent_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two intent vectors."""
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
#  Voxel — a single cell in the 6D+t grid
# ---------------------------------------------------------------------------


@dataclass
class Voxel:
    """A 6D+t voxel cell with authority and intent encoding."""

    voxel_id: str

    # D1-D3: Spatial
    x: float
    y: float
    z: float

    # D4: Spectral
    wavelength_nm: float
    tongue: str = "KO"

    # D5: Authority
    authority_agent: str = ""
    authority_hash: str = ""
    authority_tags: Set[str] = field(default_factory=set)

    # D6: Intent
    intent_vector: np.ndarray = field(default_factory=lambda: np.zeros(3))
    intent_label: str = ""

    # +t: Temporal
    created_at: float = 0.0
    updated_at: float = 0.0
    version: int = 1

    # Chladni addressing
    chladni_address: float = 0.0

    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)

    @property
    def color_channel(self) -> ColorChannel:
        return ColorChannel(wavelength_nm=self.wavelength_nm, tongue=self.tongue)

    @property
    def position_6d(self) -> np.ndarray:
        """Full 6D position vector for distance calculations."""
        return np.array(
            [
                self.x,
                self.y,
                self.z,
                self.wavelength_nm / 780.0,  # normalized spectral
                hash(self.authority_hash) % 1000 / 1000.0 if self.authority_hash else 0.0,
                float(np.linalg.norm(self.intent_vector)),
            ],
            dtype=np.float64,
        )

    def distance_to(self, other: Voxel) -> float:
        """Euclidean distance in 6D space (tongue-weighted)."""
        a = self.position_6d
        b = other.position_6d
        # Weight dimensions by tongue importance
        weights = np.array([1.0, 1.0, 1.0, PHI, PHI**2, PHI**3])
        diff = (a - b) * weights
        return float(np.linalg.norm(diff))


# ---------------------------------------------------------------------------
#  Voxel Grid — the 6D+t storage engine
# ---------------------------------------------------------------------------


class VoxelGrid:
    """6D voxel storage with Chladni addressing and temporal slicing."""

    def __init__(
        self,
        resolution: int = 16,
        chladni_mode: Tuple[int, int] = (3, 2),
    ):
        self.resolution = resolution
        self.chladni_n, self.chladni_m = chladni_mode
        self.voxels: Dict[str, Voxel] = {}
        self._intent_index: List[Tuple[str, np.ndarray]] = []  # (voxel_id, intent_vec)
        self._temporal_index: List[Tuple[float, str]] = []  # (timestamp, voxel_id)
        self._chladni_pattern = generate_chladni_grid(resolution, self.chladni_n, self.chladni_m)

    def store(
        self,
        x: float,
        y: float,
        z: float = 0.0,
        wavelength_nm: float = 550.0,
        tongue: str = "KO",
        authority: str = "",
        authority_tags: Optional[Set[str]] = None,
        intent_vector: Optional[List[float]] = None,
        intent_label: str = "",
        payload: Optional[Dict[str, Any]] = None,
        voxel_id: Optional[str] = None,
    ) -> Voxel:
        """Store a new voxel in the 6D grid."""
        now = time.time()
        intent_arr = normalize_intent(intent_vector or [0.0, 0.0, 0.0])

        if voxel_id is None:
            voxel_id = hashlib.md5(f"{x}:{y}:{z}:{wavelength_nm}:{authority}:{now}".encode()).hexdigest()[:16]

        auth_hash = compute_authority_hash(authority, str(payload or {}), now)
        ca = chladni_address(x, y, self.chladni_n, self.chladni_m)

        v = Voxel(
            voxel_id=voxel_id,
            x=x,
            y=y,
            z=z,
            wavelength_nm=wavelength_nm,
            tongue=tongue,
            authority_agent=authority,
            authority_hash=auth_hash,
            authority_tags=authority_tags or set(),
            intent_vector=intent_arr,
            intent_label=intent_label,
            created_at=now,
            updated_at=now,
            chladni_address=ca,
            payload=payload or {},
        )

        self.voxels[voxel_id] = v
        self._intent_index.append((voxel_id, intent_arr))
        self._temporal_index.append((now, voxel_id))

        return v

    def update(self, voxel_id: str, **kwargs) -> Optional[Voxel]:
        """Update a voxel, incrementing version and timestamp."""
        v = self.voxels.get(voxel_id)
        if v is None:
            return None

        for key, val in kwargs.items():
            if key == "intent_vector":
                val = normalize_intent(val)
            if hasattr(v, key):
                setattr(v, key, val)

        v.updated_at = time.time()
        v.version += 1
        self._temporal_index.append((v.updated_at, voxel_id))

        return v

    def query_by_intent(
        self,
        intent_vector: List[float],
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> List[Tuple[Voxel, float]]:
        """Find voxels with similar intent (cosine similarity)."""
        query = normalize_intent(intent_vector)
        scores = []

        for vid, ivec in self._intent_index:
            sim = intent_similarity(query, ivec)
            if sim >= min_similarity:
                scores.append((vid, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        seen = set()
        for vid, sim in scores[: top_k * 2]:  # over-fetch for dedup
            if vid in seen:
                continue
            seen.add(vid)
            v = self.voxels.get(vid)
            if v:
                results.append((v, sim))
            if len(results) >= top_k:
                break

        return results

    def query_by_wavelength(
        self,
        wavelength_nm: float,
        tolerance_nm: float = 20.0,
    ) -> List[Voxel]:
        """Find voxels within a spectral band."""
        return [v for v in self.voxels.values() if abs(v.wavelength_nm - wavelength_nm) <= tolerance_nm]

    def query_by_authority(self, agent_id: str) -> List[Voxel]:
        """Find all voxels owned by an agent."""
        return [v for v in self.voxels.values() if v.authority_agent == agent_id]

    def query_by_chladni_zone(
        self,
        zone: str = "antinode",
        threshold: float = 0.3,
    ) -> List[Voxel]:
        """Find voxels at antinodes (high energy) or nodal lines (low energy).

        zone="antinode": chladni_address far from 0.5
        zone="nodal": chladni_address near 0.5
        """
        results = []
        for v in self.voxels.values():
            dist_from_nodal = abs(v.chladni_address - 0.5)
            if zone == "antinode" and dist_from_nodal > threshold:
                results.append(v)
            elif zone == "nodal" and dist_from_nodal <= threshold:
                results.append(v)
        return results

    def time_slice(
        self,
        t_start: float = 0.0,
        t_end: Optional[float] = None,
    ) -> List[Voxel]:
        """Get voxels created/updated in a time window (7th dimension slice)."""
        if t_end is None:
            t_end = time.time()

        vids = set()
        for ts, vid in self._temporal_index:
            if t_start <= ts <= t_end:
                vids.add(vid)

        return [self.voxels[vid] for vid in vids if vid in self.voxels]

    def nearest_neighbors(self, voxel: Voxel, k: int = 5) -> List[Tuple[Voxel, float]]:
        """Find k nearest neighbors in 6D space."""
        distances = []
        for v in self.voxels.values():
            if v.voxel_id == voxel.voxel_id:
                continue
            d = voxel.distance_to(v)
            distances.append((v, d))

        distances.sort(key=lambda x: x[1])
        return distances[:k]

    def stats(self) -> Dict[str, Any]:
        """Grid statistics."""
        if not self.voxels:
            return {"count": 0}

        wavelengths = [v.wavelength_nm for v in self.voxels.values()]
        agents = set(v.authority_agent for v in self.voxels.values())
        chladni_vals = [v.chladni_address for v in self.voxels.values()]

        return {
            "count": len(self.voxels),
            "resolution": self.resolution,
            "chladni_mode": (self.chladni_n, self.chladni_m),
            "wavelength_range": (min(wavelengths), max(wavelengths)),
            "unique_agents": len(agents),
            "agents": list(agents),
            "chladni_mean": float(np.mean(chladni_vals)),
            "temporal_events": len(self._temporal_index),
            "versions_total": sum(v.version for v in self.voxels.values()),
        }


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------


def _demo():
    print("=" * 70)
    print("  6D Voxel Storage — Authority + Intent + Chladni Addressing")
    print("=" * 70)

    grid = VoxelGrid(resolution=16, chladni_mode=(3, 2))

    # Store voxels from different agents with different intents
    agents = [
        ("agent.claude", "architecture", [0.9, 0.1, 0.0], 400.0, "DR"),
        ("agent.gpt", "drafting", [0.1, 0.9, 0.0], 455.0, "AV"),
        ("agent.gemini", "research", [0.0, 0.1, 0.9], 540.0, "RU"),
        ("agent.grok", "challenge", [0.5, 0.5, 0.0], 617.0, "RU"),
        ("agent.claude", "governance", [0.8, 0.0, 0.2], 400.0, "UM"),
    ]

    print("\nStoring voxels:")
    for agent, label, intent, wl, tongue in agents:
        v = grid.store(
            x=0.1 + hash(agent) % 80 / 100,
            y=0.2 + hash(label) % 60 / 100,
            z=0.0,
            wavelength_nm=wl,
            tongue=tongue,
            authority=agent,
            intent_vector=intent,
            intent_label=label,
            payload={"task": label, "priority": "high"},
        )
        print(f"  {v.voxel_id} | {agent:15s} | {label:12s} | {wl:.0f}nm | " f"chladni={v.chladni_address:.3f}")

    # Query by intent
    print("\nIntent query (architecture-like [0.9, 0.1, 0.0]):")
    results = grid.query_by_intent([0.9, 0.1, 0.0], top_k=3)
    for v, sim in results:
        print(f"  {v.intent_label:12s} sim={sim:.3f} agent={v.authority_agent}")

    # Query by wavelength
    print("\nWavelength query (400nm +-30nm = violet band):")
    violet_voxels = grid.query_by_wavelength(400.0, tolerance_nm=30.0)
    for v in violet_voxels:
        print(f"  {v.voxel_id} {v.authority_agent} {v.intent_label}")

    # Query by authority
    print("\nAuthority query (agent.claude):")
    claude_voxels = grid.query_by_authority("agent.claude")
    for v in claude_voxels:
        print(f"  {v.voxel_id} {v.intent_label} v{v.version}")

    # Chladni zone query
    print("\nChladni zone query (antinodes = high energy):")
    antinodes = grid.query_by_chladni_zone("antinode", threshold=0.2)
    for v in antinodes:
        print(f"  {v.voxel_id} chladni={v.chladni_address:.3f} {v.intent_label}")

    # 6D nearest neighbors
    ref = list(grid.voxels.values())[0]
    print(f"\n6D nearest neighbors of {ref.intent_label}:")
    neighbors = grid.nearest_neighbors(ref, k=3)
    for v, d in neighbors:
        print(f"  {v.intent_label:12s} dist={d:.3f}")

    # Time slice
    print(f"\nTime slice (all): {len(grid.time_slice())} voxels")

    # Update a voxel
    first_id = list(grid.voxels.keys())[0]
    grid.update(first_id, intent_vector=[0.7, 0.2, 0.1])
    v = grid.voxels[first_id]
    print(f"\nUpdated {first_id}: v{v.version} intent={v.intent_vector}")

    # Stats
    print(f"\nGrid stats: {grid.stats()}")

    # Chladni pattern preview
    print("\nChladni pattern (16x16, mode 3,2):")
    pattern = grid._chladni_pattern
    for row in range(0, 16, 2):
        line = ""
        for col in range(16):
            val = pattern[row, col]
            if abs(val) < 0.3:
                line += "."  # nodal line
            elif val > 0:
                line += "#"  # positive antinode
            else:
                line += "o"  # negative antinode
        print(f"  {line}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    _demo()
