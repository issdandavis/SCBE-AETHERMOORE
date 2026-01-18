"""
Cymatic Voxel Storage - HolographicQRCube
==========================================
Encodes data at nodal positions in a standing wave field with
access controlled by 6D vector-derived mode parameters.

Key concepts:
- Voxels stored at positions satisfying Chladni nodal equation
- Access requires agent vector that produces resonance at voxel position
- KD-Tree spatial indexing using harmonic distance metric

Document ID: AETHER-SPEC-2026-001
Section: 6 (Cymatic Voxel Storage)
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
from enum import Enum

from .constants import (
    R_FIFTH, PHI, DEFAULT_L, DEFAULT_TOLERANCE, DEFAULT_R,
    harmonic_distance, harmonic_scale, CONSTANTS
)
from .vacuum_acoustics import (
    check_cymatic_resonance, extract_mode_parameters,
    nodal_surface, is_on_nodal_line,
    VacuumAcousticsConfig
)


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

Vector6D = Tuple[float, float, float, float, float, float]
# (x, y, z, velocity, priority, security)


class StorageMode(Enum):
    """Voxel access control modes."""
    PUBLIC = "public"           # No resonance check
    RESONANCE = "resonance"     # Requires cymatic resonance
    ENCRYPTED = "encrypted"     # Requires resonance + decryption key


@dataclass
class Voxel:
    """
    A data voxel in the cymatic storage system.

    Definition 6.2.1 (Voxel):
        Voxel = {
            position: Vector6D,     // 6D location in harmonic space
            data: bytes,            // Stored payload
            modes: (n, m),          // Access control modes
            checksum: SHA256        // Integrity verification
        }

    Attributes:
        id: Unique voxel identifier
        position: 6D location in harmonic space
        data: Stored payload
        modes: Access control mode parameters (n, m)
        checksum: SHA-256 integrity hash
        created: Unix timestamp
        storage_mode: Access control type
    """
    id: str
    position: Vector6D
    data: bytes
    modes: Tuple[float, float]
    checksum: str
    created: float = field(default_factory=time.time)
    storage_mode: StorageMode = StorageMode.RESONANCE

    def verify_integrity(self) -> bool:
        """Verify data integrity using checksum."""
        computed = hashlib.sha256(self.data).hexdigest()
        return computed == self.checksum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'position': list(self.position),
            'data': self.data.hex(),
            'modes': list(self.modes),
            'checksum': self.checksum,
            'created': self.created,
            'storage_mode': self.storage_mode.value,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Voxel':
        """Create Voxel from dictionary."""
        return cls(
            id=d['id'],
            position=tuple(d['position']),
            data=bytes.fromhex(d['data']),
            modes=tuple(d['modes']),
            checksum=d['checksum'],
            created=d.get('created', time.time()),
            storage_mode=StorageMode(d.get('storage_mode', 'resonance')),
        )


@dataclass
class CubeConfig:
    """
    HolographicQRCube configuration.

    Attributes:
        L: Characteristic length for nodal calculations
        tolerance: Resonance tolerance
        R: Harmonic ratio for distance metric
        v_reference: Reference velocity for mode extraction
        max_voxels: Maximum number of voxels (0 = unlimited)
        auto_verify: Automatically verify checksums on read
    """
    L: float = DEFAULT_L
    tolerance: float = DEFAULT_TOLERANCE
    R: float = R_FIFTH
    v_reference: float = 1.0
    max_voxels: int = 0
    auto_verify: bool = True


@dataclass
class CubeStats:
    """Statistics for a HolographicQRCube."""
    id: str
    voxel_count: int
    total_data_bytes: int
    avg_modes: Tuple[float, float]
    dimension_ranges: Dict[str, Tuple[float, float]]
    created: float
    config: CubeConfig


@dataclass
class KDNode:
    """
    Node in the KD-Tree for spatial indexing.

    Structure from spec:
        Node = {
            point: Vector6D,
            voxel: Voxel,
            left: Node | null,
            right: Node | null,
            split_dim: 0..5  // Cycles through 6 dimensions
        }
    """
    point: Vector6D
    voxel: Voxel
    left: Optional['KDNode'] = None
    right: Optional['KDNode'] = None
    split_dim: int = 0


# =============================================================================
# KD-TREE IMPLEMENTATION
# =============================================================================

class KDTree:
    """
    KD-Tree for O(log n) nearest-neighbor queries in 6D harmonic space.

    Uses harmonic distance metric from AETHERMOORE spec:
        d_H(u, v) = √(Σᵢⱼ g_H[i,j] · (uᵢ - vᵢ)(uⱼ - vⱼ))

    Where g_H = diag(1, 1, 1, R₅, R₅², R₅³)
    """

    def __init__(self, R: float = R_FIFTH):
        """
        Initialize KD-Tree.

        Args:
            R: Harmonic ratio for distance metric
        """
        self.root: Optional[KDNode] = None
        self.R = R
        self.size = 0

    def insert(self, voxel: Voxel) -> None:
        """
        Insert a voxel into the tree.

        Args:
            voxel: Voxel to insert
        """
        node = KDNode(point=voxel.position, voxel=voxel)

        if self.root is None:
            self.root = node
            self.size = 1
            return

        self._insert_recursive(self.root, node, 0)
        self.size += 1

    def _insert_recursive(self, current: KDNode, new_node: KDNode, depth: int) -> None:
        """Recursive insertion helper."""
        dim = depth % 6  # Cycle through 6 dimensions

        if new_node.point[dim] < current.point[dim]:
            if current.left is None:
                current.left = new_node
                new_node.split_dim = (depth + 1) % 6
            else:
                self._insert_recursive(current.left, new_node, depth + 1)
        else:
            if current.right is None:
                current.right = new_node
                new_node.split_dim = (depth + 1) % 6
            else:
                self._insert_recursive(current.right, new_node, depth + 1)

    def nearest(self, point: Vector6D) -> Optional[Voxel]:
        """
        Find nearest voxel to a point using harmonic distance.

        Args:
            point: Query point

        Returns:
            Nearest voxel or None if tree is empty
        """
        if self.root is None:
            return None

        best = [None, float('inf')]  # [node, distance]
        self._nearest_recursive(self.root, point, 0, best)

        return best[0].voxel if best[0] else None

    def _nearest_recursive(
        self,
        node: KDNode,
        target: Vector6D,
        depth: int,
        best: List
    ) -> None:
        """Recursive nearest neighbor search."""
        if node is None:
            return

        # Compute harmonic distance to this node
        dist = harmonic_distance(target, node.point, self.R)

        if dist < best[1]:
            best[0] = node
            best[1] = dist

        dim = depth % 6

        # Determine which subtree to search first
        diff = target[dim] - node.point[dim]

        if diff < 0:
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        # Search closer subtree first
        self._nearest_recursive(first, target, depth + 1, best)

        # Check if we need to search the other subtree
        # (if the splitting plane could contain closer points)
        if abs(diff) < best[1]:
            self._nearest_recursive(second, target, depth + 1, best)

    def range_query(self, center: Vector6D, radius: float) -> List[Voxel]:
        """
        Find all voxels within harmonic distance radius of center.

        Args:
            center: Center of search region
            radius: Maximum harmonic distance

        Returns:
            List of voxels within radius
        """
        results = []
        self._range_recursive(self.root, center, radius, 0, results)
        return results

    def _range_recursive(
        self,
        node: Optional[KDNode],
        center: Vector6D,
        radius: float,
        depth: int,
        results: List[Voxel]
    ) -> None:
        """Recursive range query helper."""
        if node is None:
            return

        # Check if this node is in range
        dist = harmonic_distance(center, node.point, self.R)
        if dist <= radius:
            results.append(node.voxel)

        dim = depth % 6
        diff = center[dim] - node.point[dim]

        # Determine which subtrees to search
        if diff - radius <= 0:
            self._range_recursive(node.left, center, radius, depth + 1, results)
        if diff + radius >= 0:
            self._range_recursive(node.right, center, radius, depth + 1, results)

    def all_voxels(self) -> List[Voxel]:
        """Get all voxels in the tree."""
        results = []
        self._collect_all(self.root, results)
        return results

    def _collect_all(self, node: Optional[KDNode], results: List[Voxel]) -> None:
        """Collect all voxels recursively."""
        if node is None:
            return
        results.append(node.voxel)
        self._collect_all(node.left, results)
        self._collect_all(node.right, results)


# =============================================================================
# HOLOGRAPHIC QR CUBE
# =============================================================================

class HolographicQRCube:
    """
    Holographic QR Cube - Cymatic storage system.

    Stores data voxels at positions satisfying the Chladni nodal equation,
    with access controlled by 6D agent vector resonance.

    Definition 6.2.2 (Storage Grid):
        Grid: V₆ → Voxel ∪ {∅}
        Addressable only at nodal intersections:
        Valid(x) ⟺ ∃(n,m): N(x; n, m) = 0

    Usage:
        cube = HolographicQRCube("my-cube")

        # Store data
        voxel = cube.add_voxel(
            position=(1.0, 2.0, 3.0, 1.5, 0.5, 2.0),
            data=b"secret message"
        )

        # Retrieve with matching agent vector
        agent = (0.0, 0.0, 0.0, 1.5, 0.5, 2.0)  # Same velocity/security
        data = cube.scan(agent)  # Returns b"secret message" if resonance
    """

    def __init__(self, id: str, config: Optional[CubeConfig] = None):
        """
        Initialize HolographicQRCube.

        Args:
            id: Unique cube identifier
            config: Cube configuration
        """
        self.id = id
        self.config = config or CubeConfig()
        self._tree = KDTree(self.config.R)
        self._voxels: Dict[str, Voxel] = {}
        self._created = time.time()

        # Vacuum acoustics config for resonance checks
        self._vac_config = VacuumAcousticsConfig(
            L=self.config.L,
            R=self.config.R,
            v_reference=self.config.v_reference
        )

    @property
    def voxel_count(self) -> int:
        """Number of voxels in the cube."""
        return len(self._voxels)

    def add_voxel(
        self,
        position: Vector6D,
        data: bytes,
        storage_mode: StorageMode = StorageMode.RESONANCE
    ) -> Voxel:
        """
        Store data at a 6D position.

        The position determines the access control mode parameters (n, m)
        derived from the velocity and security components.

        Args:
            position: 6D storage location (x, y, z, velocity, priority, security)
            data: Payload to store
            storage_mode: Access control type

        Returns:
            Created Voxel reference

        Raises:
            ValueError: If max_voxels limit reached
        """
        if self.config.max_voxels > 0 and len(self._voxels) >= self.config.max_voxels:
            raise ValueError(f"Maximum voxel limit ({self.config.max_voxels}) reached")

        # Generate voxel ID
        voxel_id = str(uuid.uuid4())

        # Compute checksum
        checksum = hashlib.sha256(data).hexdigest()

        # Extract mode parameters from position
        modes = extract_mode_parameters(position, self._vac_config)

        # Create voxel
        voxel = Voxel(
            id=voxel_id,
            position=position,
            data=data,
            modes=modes,
            checksum=checksum,
            created=time.time(),
            storage_mode=storage_mode
        )

        # Store in both dict and tree
        self._voxels[voxel_id] = voxel
        self._tree.insert(voxel)

        return voxel

    def scan(
        self,
        agent_vector: Vector6D,
        tolerance: Optional[float] = None
    ) -> Optional[bytes]:
        """
        Retrieve data using agent's vector for access control.

        Algorithm 6.3.1 (Voxel Retrieval):
            1. Extract mode parameters n, m from agent vector
            2. Find nearest voxel
            3. Check resonance at voxel position
            4. Return data if resonance achieved

        Args:
            agent_vector: Agent's current 6D state
            tolerance: Resonance tolerance (uses config default if None)

        Returns:
            Data if resonance achieved, None otherwise
        """
        if tolerance is None:
            tolerance = self.config.tolerance

        # Find nearest voxel to agent
        nearest = self._tree.nearest(agent_vector)
        if nearest is None:
            return None

        # Check access based on storage mode
        if nearest.storage_mode == StorageMode.PUBLIC:
            data = nearest.data
        elif nearest.storage_mode == StorageMode.RESONANCE:
            # Check cymatic resonance
            target_pos = (nearest.position[0], nearest.position[1])  # x, y plane
            if check_cymatic_resonance(agent_vector, target_pos, tolerance, self._vac_config):
                data = nearest.data
            else:
                return None
        else:
            # ENCRYPTED mode - resonance required, data still encrypted
            target_pos = (nearest.position[0], nearest.position[1])
            if check_cymatic_resonance(agent_vector, target_pos, tolerance, self._vac_config):
                data = nearest.data  # Caller must decrypt
            else:
                return None

        # Verify integrity if configured
        if self.config.auto_verify:
            if not nearest.verify_integrity():
                return None

        return data

    def scan_all_resonant(
        self,
        agent_vector: Vector6D,
        tolerance: Optional[float] = None
    ) -> List[Tuple[Voxel, bytes]]:
        """
        Find all voxels that resonate with the agent vector.

        Args:
            agent_vector: Agent's 6D state
            tolerance: Resonance tolerance

        Returns:
            List of (voxel, data) tuples for all resonant voxels
        """
        if tolerance is None:
            tolerance = self.config.tolerance

        results = []

        for voxel in self._voxels.values():
            if voxel.storage_mode == StorageMode.PUBLIC:
                results.append((voxel, voxel.data))
            else:
                target_pos = (voxel.position[0], voxel.position[1])
                if check_cymatic_resonance(agent_vector, target_pos, tolerance, self._vac_config):
                    if not self.config.auto_verify or voxel.verify_integrity():
                        results.append((voxel, voxel.data))

        return results

    def nearest(self, position: Vector6D) -> Optional[Voxel]:
        """
        Find nearest voxel to a position (ignores access control).

        Args:
            position: Query position

        Returns:
            Nearest voxel or None
        """
        return self._tree.nearest(position)

    def range_query(self, center: Vector6D, radius: float) -> List[Voxel]:
        """
        List all voxels within harmonic distance radius.

        Args:
            center: Center position
            radius: Maximum harmonic distance

        Returns:
            Array of voxels within radius
        """
        return self._tree.range_query(center, radius)

    def get_voxel(self, voxel_id: str) -> Optional[Voxel]:
        """Get voxel by ID (ignores access control)."""
        return self._voxels.get(voxel_id)

    def remove_voxel(self, voxel_id: str) -> bool:
        """
        Remove a voxel by ID.

        Note: This doesn't remove from KD-tree (would require rebuild).
        The voxel becomes inaccessible but tree may return stale results
        until rebuild.

        Args:
            voxel_id: Voxel to remove

        Returns:
            True if removed, False if not found
        """
        if voxel_id in self._voxels:
            del self._voxels[voxel_id]
            return True
        return False

    def rebuild_index(self) -> None:
        """Rebuild the KD-tree index from current voxels."""
        self._tree = KDTree(self.config.R)
        for voxel in self._voxels.values():
            self._tree.insert(voxel)

    def get_stats(self) -> CubeStats:
        """Get cube statistics."""
        voxels = list(self._voxels.values())

        if not voxels:
            return CubeStats(
                id=self.id,
                voxel_count=0,
                total_data_bytes=0,
                avg_modes=(0.0, 0.0),
                dimension_ranges={},
                created=self._created,
                config=self.config
            )

        # Compute statistics
        total_bytes = sum(len(v.data) for v in voxels)

        avg_n = sum(v.modes[0] for v in voxels) / len(voxels)
        avg_m = sum(v.modes[1] for v in voxels) / len(voxels)

        dim_names = ['x', 'y', 'z', 'velocity', 'priority', 'security']
        ranges = {}
        for i, name in enumerate(dim_names):
            values = [v.position[i] for v in voxels]
            ranges[name] = (min(values), max(values))

        return CubeStats(
            id=self.id,
            voxel_count=len(voxels),
            total_data_bytes=total_bytes,
            avg_modes=(avg_n, avg_m),
            dimension_ranges=ranges,
            created=self._created,
            config=self.config
        )

    def export(self) -> Dict[str, Any]:
        """
        Export cube to serializable format.

        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            'id': self.id,
            'config': {
                'L': self.config.L,
                'tolerance': self.config.tolerance,
                'R': self.config.R,
                'v_reference': self.config.v_reference,
                'max_voxels': self.config.max_voxels,
                'auto_verify': self.config.auto_verify,
            },
            'created': self._created,
            'voxels': [v.to_dict() for v in self._voxels.values()],
        }

    @classmethod
    def import_cube(cls, data: Dict[str, Any]) -> 'HolographicQRCube':
        """
        Import cube from serialized format.

        Args:
            data: Serialized cube data

        Returns:
            Reconstructed HolographicQRCube
        """
        config = CubeConfig(
            L=data['config']['L'],
            tolerance=data['config']['tolerance'],
            R=data['config']['R'],
            v_reference=data['config']['v_reference'],
            max_voxels=data['config']['max_voxels'],
            auto_verify=data['config']['auto_verify'],
        )

        cube = cls(data['id'], config)
        cube._created = data['created']

        for voxel_data in data['voxels']:
            voxel = Voxel.from_dict(voxel_data)
            cube._voxels[voxel.id] = voxel
            cube._tree.insert(voxel)

        return cube


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_voxel_grid(
    data_chunks: List[bytes],
    base_position: Vector6D = (0, 0, 0, 1.0, 0.5, 1.0),
    spacing: float = 1.0
) -> List[Voxel]:
    """
    Create a grid of voxels from data chunks.

    Args:
        data_chunks: List of data payloads
        base_position: Starting position
        spacing: Distance between voxels

    Returns:
        List of created voxels (not added to cube)
    """
    voxels = []
    n = len(data_chunks)

    # Arrange in 3D grid
    grid_size = int(n ** (1/3)) + 1

    for i, data in enumerate(data_chunks):
        ix = i % grid_size
        iy = (i // grid_size) % grid_size
        iz = i // (grid_size * grid_size)

        position = (
            base_position[0] + ix * spacing,
            base_position[1] + iy * spacing,
            base_position[2] + iz * spacing,
            base_position[3],
            base_position[4],
            base_position[5],
        )

        voxel = Voxel(
            id=str(uuid.uuid4()),
            position=position,
            data=data,
            modes=extract_mode_parameters(position, VacuumAcousticsConfig()),
            checksum=hashlib.sha256(data).hexdigest()
        )
        voxels.append(voxel)

    return voxels


def compute_access_vector(
    target_modes: Tuple[float, float],
    base_position: Vector6D = (0, 0, 0, 1.0, 0.5, 1.0),
    v_reference: float = 1.0
) -> Vector6D:
    """
    Compute an agent vector that will resonate with given modes.

    Args:
        target_modes: Target (n, m) modes
        base_position: Base vector for x, y, z, priority
        v_reference: Reference velocity

    Returns:
        Agent vector that should resonate with target
    """
    n, m = target_modes

    # Reverse the mode extraction
    velocity = n * v_reference
    security = m

    return (
        base_position[0],
        base_position[1],
        base_position[2],
        velocity,
        base_position[4],
        security
    )


def get_cymatic_storage_stats() -> Dict[str, Any]:
    """Get module statistics and constants."""
    return {
        'storage_modes': [mode.value for mode in StorageMode],
        'default_config': {
            'L': DEFAULT_L,
            'tolerance': DEFAULT_TOLERANCE,
            'R': R_FIFTH,
        },
        'harmonic_scales': {
            f'd={d}': harmonic_scale(d, R_FIFTH)
            for d in range(1, 7)
        },
        'vector_dimensions': [
            'x (spatial)',
            'y (spatial)',
            'z (spatial)',
            'velocity (mode n)',
            'priority (scalar)',
            'security (mode m)',
        ],
        'constants': CONSTANTS,
    }
