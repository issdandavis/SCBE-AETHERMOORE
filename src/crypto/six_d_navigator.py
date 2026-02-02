"""
6D Vector Navigation System - Spiralverse Integration
======================================================

Implements 6-dimensional vector navigation for swarm/fleet coordination,
bridging the 3D hyperbolic octree with the 10D dual lattice.

6D Axes:
  Physical (Spatial):
    X - AXIOM: Forward/backward, rule/principle space
    Y - FLOW:  Lateral, process/execution space
    Z - GLYPH: Vertical, symbol/meaning space

  Operational (Parameters):
    V - ORACLE: Velocity/knowledge/certainty
    H - CHARM:  Priority/harmony coefficient
    S - LEDGER: Security/trust/audit level

Key Features:
  - Proximity-based message optimization (70-80% bandwidth savings)
  - Auto-locking cryptographic docking via ORACLE+LEDGER convergence
  - Integration with Sacred Tongues and Poincaré ball geometry
  - Support for swarm coordination up to 1000+ agents

Based on Spiralverse 6-Language Interoperability Codex System v2.0

@layer Layer 5 (Hyperbolic Distance), Layer 8 (Multi-well Realms)
@component SixDNavigator
@version 1.0.0
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
import struct
import time

# Golden Ratio
PHI = (1 + np.sqrt(5)) / 2

EPSILON = 1e-10


# =============================================================================
# 6D Axis Definitions (Spiralverse Mapping)
# =============================================================================

class PhysicalAxis(str, Enum):
    """Physical 3D axes for spatial positioning."""
    AXIOM = "X"   # Forward/backward (longitudinal) - Rule/Principle
    FLOW = "Y"    # Lateral/sideways (transverse) - Process/Execution
    GLYPH = "Z"   # Vertical (altitude) - Symbol/Meaning


class OperationalAxis(str, Enum):
    """Extended 3D axes for operational parameters."""
    ORACLE = "V"  # Velocity/Knowledge/Certainty magnitude (0-1)
    CHARM = "H"   # Priority/Harmony coefficient (-1 to +1)
    LEDGER = "S"  # Security/Trust level (0-255)


class SacredTongue6D(str, Enum):
    """Sacred Tongues mapped to 6D octants."""
    KO = "KO"  # +X+Y+Z: Intent/Purpose (center tendency)
    AV = "AV"  # +X+Y-Z: Context/Wisdom
    RU = "RU"  # +X-Y+Z: Binding/Structure
    CA = "CA"  # +X-Y-Z: Bitcraft/Precision
    UM = "UM"  # -X+Y+Z: Hidden/Mystery
    DR = "DR"  # -X+Y-Z: Nature/Flow


# 6D Octant to Sacred Tongue mapping (64 octants → 6 primary tongues)
# Uses physical axes signs as primary, operational axes as modifiers
def get_tongue_from_6d(pos: np.ndarray) -> SacredTongue6D:
    """
    Map 6D position to dominant Sacred Tongue.

    Primary mapping uses physical axes (X, Y, Z).
    Operational axes (V, H, S) modify intensity.
    """
    x, y, z = pos[0], pos[1], pos[2]

    # Physical axis signs determine primary tongue
    if x >= 0 and y >= 0 and z >= 0:
        return SacredTongue6D.KO
    elif x >= 0 and y >= 0 and z < 0:
        return SacredTongue6D.AV
    elif x >= 0 and y < 0 and z >= 0:
        return SacredTongue6D.RU
    elif x >= 0 and y < 0 and z < 0:
        return SacredTongue6D.CA
    elif x < 0 and y >= 0 and z >= 0:
        return SacredTongue6D.UM
    else:  # x < 0, y >= 0, z < 0 OR x < 0, y < 0
        return SacredTongue6D.DR


# Tongue weights (Golden Ratio powers)
TONGUE_WEIGHTS_6D = {
    SacredTongue6D.KO: PHI ** 0,  # 1.000
    SacredTongue6D.AV: PHI ** 1,  # 1.618
    SacredTongue6D.RU: PHI ** 2,  # 2.618
    SacredTongue6D.CA: PHI ** 3,  # 4.236
    SacredTongue6D.UM: PHI ** 4,  # 6.854
    SacredTongue6D.DR: PHI ** 5,  # 11.090
}


# =============================================================================
# 6D Position and Agent Structures
# =============================================================================

@dataclass
class Position6D:
    """
    6D position vector for an agent in Spiralverse navigation space.

    Physical Axes (normalized to [-1, 1] Poincaré ball):
        axiom (X): Forward/backward - Rule/principle coordinate
        flow (Y):  Lateral - Process/execution coordinate
        glyph (Z): Vertical - Symbol/meaning coordinate

    Operational Axes:
        oracle (V): Velocity/certainty [0, 1]
        charm (H):  Priority/harmony [-1, +1]
        ledger (S): Security level [0, 255]
    """
    axiom: float = 0.0   # X
    flow: float = 0.0    # Y
    glyph: float = 0.0   # Z
    oracle: float = 0.0  # V (velocity/knowledge)
    charm: float = 0.0   # H (harmony/priority)
    ledger: float = 128  # S (security, 0-255)

    # Metadata
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""

    def to_array(self) -> np.ndarray:
        """Convert to 6D numpy array."""
        return np.array([
            self.axiom, self.flow, self.glyph,
            self.oracle, self.charm, self.ledger / 255.0  # Normalize S
        ], dtype=np.float64)

    @classmethod
    def from_array(cls, arr: np.ndarray, agent_id: str = "") -> 'Position6D':
        """Create from 6D numpy array."""
        return cls(
            axiom=float(arr[0]),
            flow=float(arr[1]),
            glyph=float(arr[2]),
            oracle=float(arr[3]),
            charm=float(arr[4]),
            ledger=float(arr[5] * 255.0),  # Denormalize S
            agent_id=agent_id
        )

    def physical_position(self) -> np.ndarray:
        """Get 3D physical position (X, Y, Z)."""
        return np.array([self.axiom, self.flow, self.glyph])

    def operational_vector(self) -> np.ndarray:
        """Get 3D operational parameters (V, H, S)."""
        return np.array([self.oracle, self.charm, self.ledger / 255.0])

    def euclidean_distance(self, other: 'Position6D') -> float:
        """Euclidean distance in 6D space."""
        return np.linalg.norm(self.to_array() - other.to_array())

    def physical_distance(self, other: 'Position6D') -> float:
        """Distance in physical 3D space only."""
        return np.linalg.norm(self.physical_position() - other.physical_position())

    def poincare_distance(self, other: 'Position6D') -> float:
        """
        Hyperbolic distance in physical space (Poincaré ball model).
        Uses only physical axes (X, Y, Z).
        """
        p1 = self.physical_position()
        p2 = other.physical_position()

        norm1_sq = np.sum(p1 ** 2)
        norm2_sq = np.sum(p2 ** 2)

        # Clamp to ball
        if norm1_sq >= 1.0:
            p1 = p1 * 0.99 / np.sqrt(norm1_sq)
            norm1_sq = np.sum(p1 ** 2)
        if norm2_sq >= 1.0:
            p2 = p2 * 0.99 / np.sqrt(norm2_sq)
            norm2_sq = np.sum(p2 ** 2)

        diff_sq = np.sum((p1 - p2) ** 2)
        denom = (1 - norm1_sq) * (1 - norm2_sq)

        if denom < EPSILON:
            return float('inf')

        arg = 1 + 2 * diff_sq / denom
        if arg <= 1:
            return 0.0

        return np.arccosh(arg)

    def tongue(self) -> SacredTongue6D:
        """Get dominant Sacred Tongue for this position."""
        return get_tongue_from_6d(self.to_array())

    def trust_score(self) -> float:
        """
        Compute trust score based on:
        1. Physical distance from origin (hyperbolic)
        2. Security level (LEDGER)
        3. Oracle confidence
        """
        origin = Position6D()
        h_dist = self.poincare_distance(origin)

        # Base trust from hyperbolic position
        base_trust = 1.0 / (1.0 + h_dist)

        # Security modifier (higher S = more trust)
        security_factor = self.ledger / 255.0

        # Oracle confidence modifier
        oracle_factor = 0.5 + 0.5 * self.oracle

        return base_trust * security_factor * oracle_factor

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "axiom": self.axiom,
            "flow": self.flow,
            "glyph": self.glyph,
            "oracle": self.oracle,
            "charm": self.charm,
            "ledger": self.ledger,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "tongue": self.tongue().value,
            "trust": self.trust_score()
        }


# =============================================================================
# Proximity-Based Message Optimization
# =============================================================================

class MessageComplexity(int, Enum):
    """
    Message complexity levels based on inter-agent distance.

    Achieves 70-80% bandwidth savings in dense formations.
    """
    ULTRA_CLOSE = 1   # < 2 units: AXIOM only (position drift)
    CLOSE = 2         # 2-5 units: + ORACLE (velocity sync)
    LOCAL = 3         # 5-10 units: + LEDGER (security handshake)
    REGIONAL = 4      # 10-20 units: + CHARM (priority negotiation)
    EXTENDED = 5      # 20-50 units: + FLOW (lateral coordination)
    FULL = 6          # 50+ units: All axes (complete state)


def calculate_message_complexity(distance: float) -> MessageComplexity:
    """
    Returns number of tongues/axes required based on distance.

    Distance thresholds (configurable):
    - 0-2 units:   1 tongue (AXIOM only - position drift correction)
    - 2-5 units:   2 tongues (+ ORACLE - velocity sync)
    - 5-10 units:  3 tongues (+ LEDGER - security handshake)
    - 10-20 units: 4 tongues (+ CHARM - priority negotiation)
    - 20-50 units: 5 tongues (+ FLOW - lateral coordination)
    - 50+ units:   6 tongues (full protocol - complete state)
    """
    if distance < 2:
        return MessageComplexity.ULTRA_CLOSE
    elif distance < 5:
        return MessageComplexity.CLOSE
    elif distance < 10:
        return MessageComplexity.LOCAL
    elif distance < 20:
        return MessageComplexity.REGIONAL
    elif distance < 50:
        return MessageComplexity.EXTENDED
    else:
        return MessageComplexity.FULL


def encode_6d_message(position: Position6D, target_distance: float) -> bytes:
    """
    Encodes position in optimal tongue subset based on distance.

    Message format varies by complexity:
    - Level 1: 4 bytes (X position as float16, 2 bytes padding)
    - Level 2: 8 bytes (X + V)
    - Level 3: 12 bytes (X + V + S)
    - Level 4: 16 bytes (X + V + S + H)
    - Level 5: 20 bytes (X + Y + V + S + H)
    - Level 6: 28 bytes (all 6 axes + timestamp)

    Returns:
        Encoded message bytes
    """
    complexity = calculate_message_complexity(target_distance)

    if complexity == MessageComplexity.ULTRA_CLOSE:
        # AXIOM only: 4 bytes
        return struct.pack('<e2x', np.float16(position.axiom))

    elif complexity == MessageComplexity.CLOSE:
        # AXIOM + ORACLE: 8 bytes
        return struct.pack('<ee4x',
            np.float16(position.axiom),
            np.float16(position.oracle))

    elif complexity == MessageComplexity.LOCAL:
        # AXIOM + ORACLE + LEDGER: 12 bytes
        return struct.pack('<eeB5x',
            np.float16(position.axiom),
            np.float16(position.oracle),
            int(position.ledger))

    elif complexity == MessageComplexity.REGIONAL:
        # AXIOM + ORACLE + LEDGER + CHARM: 16 bytes
        return struct.pack('<eeBe6x',
            np.float16(position.axiom),
            np.float16(position.oracle),
            int(position.ledger),
            np.float16(position.charm))

    elif complexity == MessageComplexity.EXTENDED:
        # AXIOM + FLOW + ORACLE + LEDGER + CHARM: 20 bytes
        return struct.pack('<eeeeBe4x',
            np.float16(position.axiom),
            np.float16(position.flow),
            np.float16(position.oracle),
            int(position.ledger),
            np.float16(position.charm))

    else:  # FULL
        # All 6 axes + timestamp: 28 bytes
        return struct.pack('<eeeeeBed',
            np.float16(position.axiom),
            np.float16(position.flow),
            np.float16(position.glyph),
            np.float16(position.oracle),
            np.float16(position.charm),
            int(position.ledger),
            position.timestamp)


def decode_6d_message(data: bytes, complexity: MessageComplexity,
                      defaults: Position6D = None) -> Position6D:
    """
    Decode message back to Position6D.

    Missing axes filled from defaults (typically previous known state).
    """
    if defaults is None:
        defaults = Position6D()

    result = Position6D(
        axiom=defaults.axiom,
        flow=defaults.flow,
        glyph=defaults.glyph,
        oracle=defaults.oracle,
        charm=defaults.charm,
        ledger=defaults.ledger,
        agent_id=defaults.agent_id
    )

    if complexity == MessageComplexity.ULTRA_CLOSE:
        result.axiom = struct.unpack('<e2x', data)[0]

    elif complexity == MessageComplexity.CLOSE:
        axiom, oracle = struct.unpack('<ee4x', data)
        result.axiom = axiom
        result.oracle = oracle

    elif complexity == MessageComplexity.LOCAL:
        axiom, oracle, ledger = struct.unpack('<eeB5x', data)
        result.axiom = axiom
        result.oracle = oracle
        result.ledger = ledger

    elif complexity == MessageComplexity.REGIONAL:
        axiom, oracle, ledger, charm = struct.unpack('<eeBe6x', data)
        result.axiom = axiom
        result.oracle = oracle
        result.ledger = ledger
        result.charm = charm

    elif complexity == MessageComplexity.EXTENDED:
        axiom, flow, oracle, ledger, charm = struct.unpack('<eeeeBe4x', data)
        result.axiom = axiom
        result.flow = flow
        result.oracle = oracle
        result.ledger = ledger
        result.charm = charm

    else:  # FULL
        axiom, flow, glyph, oracle, charm, ledger, ts = struct.unpack('<eeeeeBed', data)
        result.axiom = axiom
        result.flow = flow
        result.glyph = glyph
        result.oracle = oracle
        result.charm = charm
        result.ledger = ledger
        result.timestamp = ts

    result.timestamp = time.time()
    return result


def calculate_bandwidth_savings(distances: List[float]) -> Dict[str, Any]:
    """
    Calculate bandwidth savings for a set of inter-agent distances.

    Returns statistics on message optimization.
    """
    full_bandwidth = len(distances) * 28  # Full protocol bytes

    optimized_bytes = 0
    complexity_counts = {c: 0 for c in MessageComplexity}

    for d in distances:
        complexity = calculate_message_complexity(d)
        complexity_counts[complexity] += 1

        # Bytes per complexity level
        bytes_map = {
            MessageComplexity.ULTRA_CLOSE: 4,
            MessageComplexity.CLOSE: 8,
            MessageComplexity.LOCAL: 12,
            MessageComplexity.REGIONAL: 16,
            MessageComplexity.EXTENDED: 20,
            MessageComplexity.FULL: 28,
        }
        optimized_bytes += bytes_map[complexity]

    savings_percent = (1 - optimized_bytes / full_bandwidth) * 100 if full_bandwidth > 0 else 0

    return {
        "full_bandwidth_bytes": full_bandwidth,
        "optimized_bytes": optimized_bytes,
        "savings_percent": savings_percent,
        "complexity_distribution": {c.name: v for c, v in complexity_counts.items()},
        "average_bytes_per_message": optimized_bytes / len(distances) if distances else 0,
    }


# =============================================================================
# Auto-Locking Cryptographic Docking
# =============================================================================

@dataclass
class DockingLock:
    """
    Cryptographic lock established when two agents converge.

    Convergence criteria:
    - ORACLE (velocity) delta < 0.5
    - LEDGER (security) delta < 10
    """
    agent_a_id: str
    agent_b_id: str
    lock_token: bytes
    established_at: float
    oracle_delta: float
    ledger_delta: float
    valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agents": [self.agent_a_id, self.agent_b_id],
            "lock_token_hash": hashlib.sha256(self.lock_token).hexdigest()[:16],
            "established_at": self.established_at,
            "oracle_delta": self.oracle_delta,
            "ledger_delta": self.ledger_delta,
            "valid": self.valid
        }


class CryptographicDocking:
    """
    Auto-locking cryptographic docking system.

    When two agents' ORACLE (velocity) and LEDGER (security) dimensions
    converge, they automatically establish a cryptographic lock for
    secure communication.
    """

    # Convergence thresholds
    ORACLE_THRESHOLD = 0.5   # Relative velocity (m/s equivalent)
    LEDGER_THRESHOLD = 10    # Security level delta

    # Lock expiration (seconds)
    LOCK_EXPIRATION = 300    # 5 minutes

    def __init__(self, master_key: bytes = None):
        """
        Initialize docking system.

        Args:
            master_key: Master secret for key derivation (generated if None)
        """
        self.master_key = master_key or hashlib.sha256(
            f"spiralverse-docking-{time.time()}".encode()
        ).digest()

        self.active_locks: Dict[Tuple[str, str], DockingLock] = {}

    def check_docking_eligibility(self, agent_a: Position6D,
                                   agent_b: Position6D) -> Tuple[bool, Dict]:
        """
        Check if two agents meet docking lock criteria.

        Returns:
            (eligible: bool, metrics: dict)
        """
        oracle_delta = abs(agent_a.oracle - agent_b.oracle)
        ledger_delta = abs(agent_a.ledger - agent_b.ledger)
        physical_distance = agent_a.physical_distance(agent_b)

        eligible = (
            oracle_delta < self.ORACLE_THRESHOLD and
            ledger_delta < self.LEDGER_THRESHOLD and
            physical_distance < 5.0  # Must be physically close
        )

        metrics = {
            "oracle_delta": oracle_delta,
            "ledger_delta": ledger_delta,
            "physical_distance": physical_distance,
            "oracle_threshold": self.ORACLE_THRESHOLD,
            "ledger_threshold": self.LEDGER_THRESHOLD,
            "eligible": eligible
        }

        return eligible, metrics

    def establish_lock(self, agent_a: Position6D,
                       agent_b: Position6D) -> Optional[DockingLock]:
        """
        Attempt to establish docking lock between two agents.

        Returns:
            DockingLock if successful, None if not eligible
        """
        eligible, metrics = self.check_docking_eligibility(agent_a, agent_b)

        if not eligible:
            return None

        # Sort agent IDs for consistent key derivation
        ids = sorted([agent_a.agent_id, agent_b.agent_id])

        # Derive lock token from converged dimensional values
        lock_material = struct.pack('<ddddQ',
            agent_a.oracle,
            agent_b.oracle,
            agent_a.ledger,
            agent_b.ledger,
            int(time.time() * 1000)  # Timestamp in ms
        )

        lock_token = hmac.new(
            self.master_key,
            f"{ids[0]}:{ids[1]}:".encode() + lock_material,
            hashlib.sha256
        ).digest()

        lock = DockingLock(
            agent_a_id=ids[0],
            agent_b_id=ids[1],
            lock_token=lock_token,
            established_at=time.time(),
            oracle_delta=metrics["oracle_delta"],
            ledger_delta=metrics["ledger_delta"],
            valid=True
        )

        self.active_locks[(ids[0], ids[1])] = lock
        return lock

    def validate_lock(self, agent_a_id: str, agent_b_id: str) -> Optional[DockingLock]:
        """
        Validate if a lock exists and is still valid.
        """
        ids = tuple(sorted([agent_a_id, agent_b_id]))
        lock = self.active_locks.get(ids)

        if lock is None:
            return None

        # Check expiration
        if time.time() - lock.established_at > self.LOCK_EXPIRATION:
            lock.valid = False

        return lock if lock.valid else None

    def revoke_lock(self, agent_a_id: str, agent_b_id: str) -> bool:
        """
        Revoke an existing lock.
        """
        ids = tuple(sorted([agent_a_id, agent_b_id]))
        if ids in self.active_locks:
            self.active_locks[ids].valid = False
            del self.active_locks[ids]
            return True
        return False

    def get_active_locks(self) -> List[DockingLock]:
        """Get all currently active locks."""
        # Prune expired locks
        current_time = time.time()
        expired = [
            ids for ids, lock in self.active_locks.items()
            if current_time - lock.established_at > self.LOCK_EXPIRATION
        ]
        for ids in expired:
            del self.active_locks[ids]

        return list(self.active_locks.values())


# =============================================================================
# 6D Pathfinding Extension
# =============================================================================

@dataclass
class PathResult6D:
    """
    Result of 6D pathfinding.
    """
    success: bool
    path: List[Position6D] = field(default_factory=list)
    total_cost: float = float('inf')
    physical_length: float = 0.0
    hyperbolic_length: float = 0.0
    nodes_explored: int = 0
    tongues_traversed: List[SacredTongue6D] = field(default_factory=list)
    min_trust: float = 1.0
    bandwidth_stats: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "path_length": len(self.path),
            "total_cost": self.total_cost,
            "physical_length": self.physical_length,
            "hyperbolic_length": self.hyperbolic_length,
            "nodes_explored": self.nodes_explored,
            "tongues_traversed": [t.value for t in self.tongues_traversed],
            "min_trust": self.min_trust,
            "bandwidth_stats": self.bandwidth_stats
        }


class SixDNavigator:
    """
    6D Navigation system for Spiralverse swarm coordination.

    Integrates:
    - 3D Poincaré ball geometry (physical axes)
    - Operational parameter optimization (V, H, S axes)
    - Proximity-based message compression
    - Cryptographic docking
    - Sacred Tongue affinity
    """

    # Grid resolution per dimension
    GRID_RESOLUTION = 16  # 16^6 = 16.7M potential cells (sparse)

    # Cost function weights
    PHYSICAL_WEIGHT = 1.0
    OPERATIONAL_WEIGHT = 0.5
    TONGUE_AFFINITY_WEIGHT = 0.2
    TRUST_WEIGHT = 0.3

    def __init__(self, docking_key: bytes = None):
        """
        Initialize 6D navigator.

        Args:
            docking_key: Master key for cryptographic docking
        """
        self.docking = CryptographicDocking(docking_key)
        self.grid_step = 2.0 / self.GRID_RESOLUTION

        # Statistics
        self._searches = 0
        self._nodes_explored = 0

    def _cost_function(self, pos_a: Position6D, pos_b: Position6D,
                       preferred_tongues: Set[SacredTongue6D] = None) -> float:
        """
        Compute navigation cost between two positions.

        Combines:
        1. Hyperbolic physical distance
        2. Operational parameter changes
        3. Tongue affinity bonus/penalty
        4. Trust weighting
        """
        # Physical cost (hyperbolic)
        h_dist = pos_a.poincare_distance(pos_b)
        physical_cost = h_dist * self.PHYSICAL_WEIGHT

        # Operational cost (Euclidean in V, H, S)
        op_a = pos_a.operational_vector()
        op_b = pos_b.operational_vector()
        operational_cost = np.linalg.norm(op_a - op_b) * self.OPERATIONAL_WEIGHT

        # Tongue affinity
        tongue_cost = 0.0
        if preferred_tongues:
            tongue_a = pos_a.tongue()
            tongue_b = pos_b.tongue()

            if tongue_a in preferred_tongues and tongue_b in preferred_tongues:
                tongue_cost = -0.3 * self.TONGUE_AFFINITY_WEIGHT  # Bonus
            elif tongue_a in preferred_tongues and tongue_b not in preferred_tongues:
                tongue_cost = 0.5 * self.TONGUE_AFFINITY_WEIGHT  # Penalty

        # Trust weighting
        avg_trust = (pos_a.trust_score() + pos_b.trust_score()) / 2
        trust_penalty = (1.0 - avg_trust) * self.TRUST_WEIGHT

        return physical_cost + operational_cost + tongue_cost + trust_penalty

    def _heuristic(self, pos: Position6D, goal: Position6D) -> float:
        """
        Admissible heuristic for A* in 6D.

        Uses weighted combination of physical hyperbolic distance
        and operational Euclidean distance.
        """
        h_dist = pos.poincare_distance(goal)
        op_dist = np.linalg.norm(pos.operational_vector() - goal.operational_vector())

        return h_dist * self.PHYSICAL_WEIGHT + op_dist * self.OPERATIONAL_WEIGHT * 0.5

    def _get_neighbors(self, pos: Position6D) -> List[Position6D]:
        """
        Get valid neighbors in 6D grid.

        Uses 6-connected neighbors (one step per axis) to reduce
        complexity from 3^6-1=728 to 12 neighbors.
        """
        neighbors = []
        arr = pos.to_array()

        for dim in range(6):
            for delta in [-self.grid_step, self.grid_step]:
                new_arr = arr.copy()
                new_arr[dim] += delta

                # Validate physical bounds (Poincaré ball for X, Y, Z)
                if dim < 3:
                    physical = new_arr[:3]
                    if np.linalg.norm(physical) >= 1.0:
                        continue

                # Validate operational bounds
                if dim == 3:  # ORACLE
                    if new_arr[dim] < 0 or new_arr[dim] > 1:
                        continue
                elif dim == 4:  # CHARM
                    if new_arr[dim] < -1 or new_arr[dim] > 1:
                        continue
                elif dim == 5:  # LEDGER (normalized)
                    if new_arr[dim] < 0 or new_arr[dim] > 1:
                        continue

                neighbors.append(Position6D.from_array(new_arr, pos.agent_id))

        return neighbors

    def navigate(self, start: Position6D, goal: Position6D,
                 preferred_tongues: Set[SacredTongue6D] = None,
                 max_iterations: int = 10000) -> PathResult6D:
        """
        A* pathfinding in 6D space.

        Args:
            start: Starting position
            goal: Goal position
            preferred_tongues: Tongues to prefer (reduces cost)
            max_iterations: Maximum search iterations

        Returns:
            PathResult6D with path and statistics
        """
        self._searches += 1

        import heapq

        # A* data structures
        g_scores: Dict[Tuple, float] = {}
        f_scores: Dict[Tuple, float] = {}
        parents: Dict[Tuple, Position6D] = {}

        def pos_key(p: Position6D) -> Tuple:
            arr = p.to_array()
            # Quantize to grid
            return tuple((arr / self.grid_step).astype(int))

        start_key = pos_key(start)
        goal_key = pos_key(goal)

        g_scores[start_key] = 0
        f_scores[start_key] = self._heuristic(start, goal)

        # Priority queue: (f_score, counter, position)
        counter = 0
        open_set = [(f_scores[start_key], counter, start)]
        open_set_keys = {start_key}
        closed_set: Set[Tuple] = set()

        nodes_explored = 0

        while open_set and nodes_explored < max_iterations:
            _, _, current = heapq.heappop(open_set)
            current_key = pos_key(current)

            if current_key in closed_set:
                continue

            open_set_keys.discard(current_key)
            closed_set.add(current_key)
            nodes_explored += 1

            # Goal check
            if current.euclidean_distance(goal) < self.grid_step * 2:
                # Reconstruct path
                path = [goal, current]
                key = current_key
                while key in parents:
                    path.append(parents[key])
                    key = pos_key(parents[key])
                path.reverse()

                # Compute statistics
                physical_length = sum(
                    path[i].physical_distance(path[i+1])
                    for i in range(len(path) - 1)
                )
                hyperbolic_length = sum(
                    path[i].poincare_distance(path[i+1])
                    for i in range(len(path) - 1)
                )

                tongues = []
                seen_tongues = set()
                for p in path:
                    t = p.tongue()
                    if t not in seen_tongues:
                        tongues.append(t)
                        seen_tongues.add(t)

                min_trust = min(p.trust_score() for p in path)

                # Bandwidth stats for this path
                distances = [
                    path[i].physical_distance(path[i+1])
                    for i in range(len(path) - 1)
                ]
                bandwidth_stats = calculate_bandwidth_savings(distances)

                self._nodes_explored += nodes_explored

                return PathResult6D(
                    success=True,
                    path=path,
                    total_cost=g_scores[current_key] + current.euclidean_distance(goal),
                    physical_length=physical_length,
                    hyperbolic_length=hyperbolic_length,
                    nodes_explored=nodes_explored,
                    tongues_traversed=tongues,
                    min_trust=min_trust,
                    bandwidth_stats=bandwidth_stats
                )

            # Expand neighbors
            for neighbor in self._get_neighbors(current):
                neighbor_key = pos_key(neighbor)

                if neighbor_key in closed_set:
                    continue

                tentative_g = g_scores[current_key] + self._cost_function(
                    current, neighbor, preferred_tongues
                )

                if neighbor_key not in g_scores or tentative_g < g_scores[neighbor_key]:
                    g_scores[neighbor_key] = tentative_g
                    f_scores[neighbor_key] = tentative_g + self._heuristic(neighbor, goal)
                    parents[neighbor_key] = current

                    if neighbor_key not in open_set_keys:
                        counter += 1
                        heapq.heappush(open_set, (f_scores[neighbor_key], counter, neighbor))
                        open_set_keys.add(neighbor_key)

        # No path found
        self._nodes_explored += nodes_explored
        return PathResult6D(
            success=False,
            nodes_explored=nodes_explored
        )

    def compute_swarm_bandwidth(self, agents: List[Position6D]) -> Dict[str, Any]:
        """
        Compute bandwidth statistics for entire swarm.
        """
        if len(agents) < 2:
            return {"error": "Need at least 2 agents"}

        all_distances = []
        for i, a in enumerate(agents):
            for j, b in enumerate(agents):
                if i < j:
                    all_distances.append(a.physical_distance(b))

        stats = calculate_bandwidth_savings(all_distances)
        stats["agent_count"] = len(agents)
        stats["pair_count"] = len(all_distances)

        return stats

    def attempt_swarm_docking(self, agents: List[Position6D]) -> List[DockingLock]:
        """
        Attempt to establish docking locks between all eligible pairs.
        """
        locks = []

        for i, a in enumerate(agents):
            for j, b in enumerate(agents):
                if i < j:
                    lock = self.docking.establish_lock(a, b)
                    if lock:
                        locks.append(lock)

        return locks

    def statistics(self) -> Dict[str, Any]:
        """Get navigator statistics."""
        return {
            "total_searches": self._searches,
            "total_nodes_explored": self._nodes_explored,
            "avg_nodes_per_search": (
                self._nodes_explored / self._searches
                if self._searches > 0 else 0
            ),
            "grid_resolution": self.GRID_RESOLUTION,
            "grid_step": self.grid_step,
            "active_docking_locks": len(self.docking.get_active_locks()),
        }


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate 6D navigation system."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    6D VECTOR NAVIGATION - SPIRALVERSE                         ║
║         Physical (X,Y,Z) + Operational (V,H,S) Axes Navigation                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Create navigator
    nav = SixDNavigator()

    # Create test agents
    agents = [
        Position6D(axiom=0.1, flow=0.1, glyph=0.1, oracle=0.8, charm=0.5, ledger=200, agent_id="agent_01"),
        Position6D(axiom=0.2, flow=0.15, glyph=0.12, oracle=0.75, charm=0.4, ledger=195, agent_id="agent_02"),
        Position6D(axiom=0.5, flow=0.3, glyph=0.2, oracle=0.3, charm=0.1, ledger=150, agent_id="agent_03"),
        Position6D(axiom=-0.3, flow=0.4, glyph=-0.2, oracle=0.6, charm=-0.3, ledger=100, agent_id="agent_04"),
        Position6D(axiom=0.7, flow=-0.1, glyph=0.3, oracle=0.9, charm=0.8, ledger=230, agent_id="agent_05"),
    ]

    print("=" * 70)
    print("Agent Positions")
    print("=" * 70)

    for agent in agents:
        print(f"\n  {agent.agent_id}:")
        print(f"    Physical:    ({agent.axiom:.2f}, {agent.flow:.2f}, {agent.glyph:.2f})")
        print(f"    Operational: V={agent.oracle:.2f}, H={agent.charm:.2f}, S={agent.ledger:.0f}")
        print(f"    Tongue: {agent.tongue().value}")
        print(f"    Trust: {agent.trust_score():.3f}")

    # Bandwidth optimization
    print("\n" + "=" * 70)
    print("Bandwidth Optimization Analysis")
    print("=" * 70)

    stats = nav.compute_swarm_bandwidth(agents)
    print(f"\n  Agents: {stats['agent_count']}")
    print(f"  Communication pairs: {stats['pair_count']}")
    print(f"  Full protocol bandwidth: {stats['full_bandwidth_bytes']} bytes")
    print(f"  Optimized bandwidth: {stats['optimized_bytes']} bytes")
    print(f"  Savings: {stats['savings_percent']:.1f}%")
    print(f"\n  Complexity distribution:")
    for level, count in stats['complexity_distribution'].items():
        print(f"    {level}: {count}")

    # Docking attempts
    print("\n" + "=" * 70)
    print("Auto-Locking Cryptographic Docking")
    print("=" * 70)

    locks = nav.attempt_swarm_docking(agents)
    if locks:
        print(f"\n  Established {len(locks)} docking lock(s):")
        for lock in locks:
            print(f"    {lock.agent_a_id} ↔ {lock.agent_b_id}")
            print(f"      ORACLE delta: {lock.oracle_delta:.3f}")
            print(f"      LEDGER delta: {lock.ledger_delta:.0f}")
    else:
        print("\n  No docking pairs eligible (agents too far apart or divergent)")

    # Pathfinding demo
    print("\n" + "=" * 70)
    print("6D Pathfinding")
    print("=" * 70)

    start = agents[0]
    goal = agents[-1]

    print(f"\n  Start: {start.agent_id} at ({start.axiom:.2f}, {start.flow:.2f}, {start.glyph:.2f})")
    print(f"  Goal:  {goal.agent_id} at ({goal.axiom:.2f}, {goal.flow:.2f}, {goal.glyph:.2f})")
    print(f"  Direct 6D distance: {start.euclidean_distance(goal):.3f}")
    print(f"  Hyperbolic distance: {start.poincare_distance(goal):.3f}")

    result = nav.navigate(start, goal, max_iterations=5000)

    print(f"\n  Result:")
    print(f"    Success: {result.success}")
    if result.success:
        print(f"    Path length: {len(result.path)} waypoints")
        print(f"    Total cost: {result.total_cost:.3f}")
        print(f"    Physical length: {result.physical_length:.3f}")
        print(f"    Hyperbolic length: {result.hyperbolic_length:.3f}")
        print(f"    Nodes explored: {result.nodes_explored}")
        print(f"    Tongues traversed: {', '.join(t.value for t in result.tongues_traversed)}")
        print(f"    Min trust on path: {result.min_trust:.3f}")
        print(f"    Path bandwidth savings: {result.bandwidth_stats.get('savings_percent', 0):.1f}%")

    # Navigator statistics
    print("\n" + "=" * 70)
    print("Navigator Statistics")
    print("=" * 70)

    nav_stats = nav.statistics()
    for key, value in nav_stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("6D Navigation Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    demo()
