"""
6D Vector Navigation System - Swarm/Fleet Coordination
=======================================================

Maps the Six Sacred Tongues to orthogonal axes in 6-dimensional space:

Physical 3D (Spatial positioning):
    AXIOM (X) - Forward/backward movement (longitudinal)
    FLOW  (Y) - Lateral/sideways movement (transverse)
    GLYPH (Z) - Vertical movement (altitude)

Extended 3D (Operational parameters):
    ORACLE (V) - Velocity magnitude (0-100% thrust)
    CHARM  (H) - Priority/Harmony index (-1 to +1)
    LEDGER (S) - Security/authentication level (0-255)

Features:
- Complete 6D coordinate system for agents
- Hyperbolic distance calculations
- Auto-locking cryptographic docking
- Formation management
- Convergence detection

"Six dimensions, one harmonious swarm."
"""

import numpy as np
import hashlib
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from datetime import datetime
import math


# =============================================================================
# Axis Definitions
# =============================================================================

class Axis(Enum):
    """The six orthogonal axes of the navigation space."""
    # Physical axes (spatial)
    AXIOM = 0   # X: Forward/backward
    FLOW = 1    # Y: Lateral/sideways
    GLYPH = 2   # Z: Vertical/altitude

    # Extended axes (operational)
    ORACLE = 3  # V: Velocity magnitude
    CHARM = 4   # H: Priority/harmony
    LEDGER = 5  # S: Security level


# Axis metadata
AXIS_INFO = {
    Axis.AXIOM: {
        "name": "AXIOM",
        "symbol": "X",
        "unit": "meters",
        "range": (-float('inf'), float('inf')),
        "description": "Forward/backward position"
    },
    Axis.FLOW: {
        "name": "FLOW",
        "symbol": "Y",
        "unit": "meters",
        "range": (-float('inf'), float('inf')),
        "description": "Lateral position"
    },
    Axis.GLYPH: {
        "name": "GLYPH",
        "symbol": "Z",
        "unit": "meters",
        "range": (-float('inf'), float('inf')),
        "description": "Vertical position (altitude)"
    },
    Axis.ORACLE: {
        "name": "ORACLE",
        "symbol": "V",
        "unit": "m/s",
        "range": (0.0, float('inf')),
        "description": "Velocity magnitude"
    },
    Axis.CHARM: {
        "name": "CHARM",
        "symbol": "H",
        "unit": "coefficient",
        "range": (-1.0, 1.0),
        "description": "Priority/harmony index"
    },
    Axis.LEDGER: {
        "name": "LEDGER",
        "symbol": "S",
        "unit": "level",
        "range": (0, 255),
        "description": "Security clearance level"
    },
}


# =============================================================================
# 6D Position
# =============================================================================

@dataclass
class Position6D:
    """
    Complete 6-dimensional position of an agent.

    Combines spatial coordinates with operational parameters.
    """
    # Physical space
    axiom: float = 0.0   # X: meters forward
    flow: float = 0.0    # Y: meters lateral
    glyph: float = 0.0   # Z: meters altitude

    # Operational space
    oracle: float = 0.0  # V: velocity (m/s)
    charm: float = 0.0   # H: harmony coefficient [-1, 1]
    ledger: int = 0      # S: security level [0, 255]

    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    agent_id: str = ""

    def __post_init__(self):
        # Clamp values to valid ranges
        self.charm = max(-1.0, min(1.0, self.charm))
        self.ledger = max(0, min(255, int(self.ledger)))
        self.oracle = max(0.0, self.oracle)

    @property
    def spatial(self) -> np.ndarray:
        """Get spatial coordinates (XYZ)."""
        return np.array([self.axiom, self.flow, self.glyph])

    @property
    def operational(self) -> np.ndarray:
        """Get operational parameters (VHS)."""
        return np.array([self.oracle, self.charm, self.ledger])

    @property
    def full_vector(self) -> np.ndarray:
        """Get complete 6D vector."""
        return np.array([
            self.axiom, self.flow, self.glyph,
            self.oracle, self.charm, self.ledger
        ])

    @classmethod
    def from_array(cls, arr: np.ndarray, agent_id: str = "") -> 'Position6D':
        """Create from numpy array."""
        if len(arr) != 6:
            raise ValueError(f"Expected 6 elements, got {len(arr)}")
        return cls(
            axiom=float(arr[0]),
            flow=float(arr[1]),
            glyph=float(arr[2]),
            oracle=float(arr[3]),
            charm=float(arr[4]),
            ledger=int(arr[5]),
            agent_id=agent_id
        )

    def distance_to(self, other: 'Position6D') -> float:
        """Euclidean distance in 6D space."""
        return float(np.linalg.norm(self.full_vector - other.full_vector))

    def spatial_distance_to(self, other: 'Position6D') -> float:
        """Euclidean distance in spatial (XYZ) space only."""
        return float(np.linalg.norm(self.spatial - other.spatial))

    def to_bytes(self) -> bytes:
        """Serialize to bytes (48 bytes: 6 doubles)."""
        return struct.pack('6d', *self.full_vector)

    @classmethod
    def from_bytes(cls, data: bytes, agent_id: str = "") -> 'Position6D':
        """Deserialize from bytes."""
        values = struct.unpack('6d', data[:48])
        return cls.from_array(np.array(values), agent_id)


# =============================================================================
# Distance Calculations
# =============================================================================

def euclidean_distance_6d(a: Position6D, b: Position6D) -> float:
    """Standard Euclidean distance in 6D."""
    return a.distance_to(b)


def weighted_distance_6d(
    a: Position6D,
    b: Position6D,
    weights: Optional[np.ndarray] = None
) -> float:
    """
    Weighted distance where each axis has different importance.

    Default weights prioritize spatial over operational.
    """
    if weights is None:
        # Default: spatial=1.0, oracle=0.5, charm=0.3, ledger=0.1
        weights = np.array([1.0, 1.0, 1.0, 0.5, 0.3, 0.1])

    diff = a.full_vector - b.full_vector
    weighted_diff = diff * weights
    return float(np.linalg.norm(weighted_diff))


def hyperbolic_distance_6d(a: Position6D, b: Position6D, curvature: float = -1.0) -> float:
    """
    Hyperbolic distance in 6D Poincare ball model.

    Used for security calculations where boundary = infinite cost.
    """
    # Normalize to unit ball
    norm_a = np.linalg.norm(a.full_vector)
    norm_b = np.linalg.norm(b.full_vector)

    if norm_a == 0 and norm_b == 0:
        return 0.0

    # Scale to fit in unit ball
    scale = max(norm_a, norm_b, 1.0) * 1.1
    u = a.full_vector / scale
    v = b.full_vector / scale

    # Poincare distance formula
    nu = np.dot(u, u)
    nv = np.dot(v, v)

    if nu >= 1.0 or nv >= 1.0:
        return float('inf')

    diff_sq = np.dot(u - v, u - v)
    denom = (1 - nu) * (1 - nv)

    if denom <= 0:
        return float('inf')

    arg = 1 + 2 * diff_sq / denom
    if arg < 1.0:
        arg = 1.0

    return float(np.arccosh(arg))


# =============================================================================
# Docking System
# =============================================================================

@dataclass
class DockingLock:
    """
    Cryptographic lock established when two agents dock.

    Generated when ORACLE (velocity) and LEDGER (security) converge.
    """
    agent_a_id: str
    agent_b_id: str
    lock_token: str
    timestamp: datetime
    expiry: datetime
    velocity_delta: float
    security_delta: int

    @property
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expiry

    @property
    def pair_key(self) -> Tuple[str, str]:
        """Canonical pair identifier (sorted)."""
        return tuple(sorted([self.agent_a_id, self.agent_b_id]))


class DockingSystem:
    """
    Auto-locking cryptographic docking via dimensional convergence.

    When ORACLE and LEDGER dimensions converge between two agents,
    a cryptographic lock is automatically established.
    """

    # Convergence thresholds
    VELOCITY_THRESHOLD = 0.5     # m/s relative velocity
    SECURITY_THRESHOLD = 10      # Security level delta
    SPATIAL_THRESHOLD = 2.0      # meters (must be close)

    # Lock parameters
    LOCK_DURATION_SECONDS = 3600  # 1 hour default

    def __init__(self):
        self.active_locks: Dict[Tuple[str, str], DockingLock] = {}

    def check_docking_eligibility(self, a: Position6D, b: Position6D) -> Dict[str, any]:
        """
        Check if two agents meet docking criteria.

        Returns eligibility status and convergence metrics.
        """
        # Calculate deltas
        velocity_delta = abs(a.oracle - b.oracle)
        security_delta = abs(a.ledger - b.ledger)
        spatial_distance = a.spatial_distance_to(b)

        # Check each criterion
        velocity_ok = velocity_delta < self.VELOCITY_THRESHOLD
        security_ok = security_delta < self.SECURITY_THRESHOLD
        spatial_ok = spatial_distance < self.SPATIAL_THRESHOLD

        eligible = velocity_ok and security_ok and spatial_ok

        return {
            "eligible": eligible,
            "velocity_delta": velocity_delta,
            "velocity_ok": velocity_ok,
            "security_delta": security_delta,
            "security_ok": security_ok,
            "spatial_distance": spatial_distance,
            "spatial_ok": spatial_ok,
        }

    def attempt_dock(self, a: Position6D, b: Position6D) -> Optional[DockingLock]:
        """
        Attempt to establish docking lock between two agents.

        Returns DockingLock if successful, None otherwise.
        """
        eligibility = self.check_docking_eligibility(a, b)
        if not eligibility["eligible"]:
            return None

        # Generate lock token from converged dimensions
        now = datetime.utcnow()
        lock_input = (
            f"{a.agent_id}:{b.agent_id}:"
            f"{a.oracle:.3f}:{b.oracle:.3f}:"
            f"{a.ledger}:{b.ledger}:"
            f"{now.isoformat()}"
        )
        lock_token = hashlib.sha256(lock_input.encode()).hexdigest()[:32]

        # Create lock
        lock = DockingLock(
            agent_a_id=a.agent_id,
            agent_b_id=b.agent_id,
            lock_token=lock_token,
            timestamp=now,
            expiry=datetime(now.year, now.month, now.day, now.hour, now.minute, now.second)
                   + __import__('datetime').timedelta(seconds=self.LOCK_DURATION_SECONDS),
            velocity_delta=eligibility["velocity_delta"],
            security_delta=eligibility["security_delta"]
        )

        # Register lock
        self.active_locks[lock.pair_key] = lock

        return lock

    def release_dock(self, agent_a_id: str, agent_b_id: str) -> bool:
        """Release a docking lock."""
        pair_key = tuple(sorted([agent_a_id, agent_b_id]))
        if pair_key in self.active_locks:
            del self.active_locks[pair_key]
            return True
        return False

    def get_lock(self, agent_a_id: str, agent_b_id: str) -> Optional[DockingLock]:
        """Get existing lock between two agents."""
        pair_key = tuple(sorted([agent_a_id, agent_b_id]))
        lock = self.active_locks.get(pair_key)
        if lock and lock.is_valid:
            return lock
        return None

    def cleanup_expired(self) -> int:
        """Remove expired locks. Returns count removed."""
        expired = [k for k, v in self.active_locks.items() if not v.is_valid]
        for k in expired:
            del self.active_locks[k]
        return len(expired)


# =============================================================================
# Swarm/Formation Management
# =============================================================================

@dataclass
class SwarmFormation:
    """
    Collection of agents in formation.
    """
    formation_id: str
    agents: Dict[str, Position6D] = field(default_factory=dict)
    target: Optional[Position6D] = None
    formation_type: str = "distributed"  # distributed, converging, tight_cluster

    @property
    def centroid(self) -> Position6D:
        """Calculate centroid of all agents."""
        if not self.agents:
            return Position6D()
        positions = np.array([a.full_vector for a in self.agents.values()])
        mean = positions.mean(axis=0)
        return Position6D.from_array(mean, agent_id=f"{self.formation_id}_centroid")

    @property
    def avg_distance_from_centroid(self) -> float:
        """Average distance of agents from centroid."""
        if not self.agents:
            return 0.0
        c = self.centroid
        distances = [a.distance_to(c) for a in self.agents.values()]
        return sum(distances) / len(distances)

    @property
    def cohesion_score(self) -> float:
        """
        Cohesion = 1 / (1 + avg_distance_between_agents)

        Range: 0 (dispersed) to 1 (perfectly clustered)
        """
        avg_dist = self.avg_distance_from_centroid
        return 1.0 / (1.0 + avg_dist)

    @property
    def alignment_score(self) -> float:
        """
        Alignment = average dot product of velocity vectors.

        Measures how synchronized agent movements are.
        """
        if len(self.agents) < 2:
            return 1.0

        # Using ORACLE (velocity) and spatial direction
        velocities = []
        for agent in self.agents.values():
            # Velocity vector = spatial direction * magnitude
            spatial = agent.spatial
            norm = np.linalg.norm(spatial)
            if norm > 0:
                direction = spatial / norm
            else:
                direction = np.array([1, 0, 0])  # Default forward
            velocities.append(direction * agent.oracle)

        # Average pairwise dot products
        dot_sum = 0.0
        count = 0
        for i, v1 in enumerate(velocities):
            for v2 in velocities[i+1:]:
                n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
                if n1 > 0 and n2 > 0:
                    dot_sum += np.dot(v1, v2) / (n1 * n2)
                    count += 1

        return dot_sum / count if count > 0 else 1.0

    @property
    def min_separation(self) -> float:
        """Minimum distance between any two agents (collision avoidance)."""
        if len(self.agents) < 2:
            return float('inf')

        positions = list(self.agents.values())
        min_dist = float('inf')

        for i, p1 in enumerate(positions):
            for p2 in positions[i+1:]:
                dist = p1.distance_to(p2)
                min_dist = min(min_dist, dist)

        return min_dist

    def add_agent(self, agent_id: str, position: Position6D):
        """Add agent to formation."""
        position.agent_id = agent_id
        self.agents[agent_id] = position

    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from formation."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def update_agent(self, agent_id: str, position: Position6D):
        """Update agent position."""
        position.agent_id = agent_id
        self.agents[agent_id] = position


# =============================================================================
# Convergence Detection
# =============================================================================

class ConvergenceDetector:
    """
    Detects when agents are converging toward a target or each other.
    """

    def __init__(self, convergence_threshold: float = 0.5):
        self.threshold = convergence_threshold
        self.history: Dict[str, List[Position6D]] = {}

    def record_position(self, agent_id: str, position: Position6D):
        """Record position for tracking."""
        if agent_id not in self.history:
            self.history[agent_id] = []
        self.history[agent_id].append(position)

        # Keep only last 100 positions
        if len(self.history[agent_id]) > 100:
            self.history[agent_id] = self.history[agent_id][-100:]

    def is_converging(self, agent_id: str, target: Position6D) -> bool:
        """Check if agent is converging toward target."""
        history = self.history.get(agent_id, [])
        if len(history) < 2:
            return False

        # Check if recent distances are decreasing
        recent = history[-10:]
        distances = [p.distance_to(target) for p in recent]

        if len(distances) < 2:
            return False

        # Linear regression slope
        x = np.arange(len(distances))
        slope = np.polyfit(x, distances, 1)[0]

        return slope < -self.threshold  # Negative slope = converging

    def convergence_eta(self, agent_id: str, target: Position6D) -> Optional[float]:
        """
        Estimate time to convergence (in seconds).

        Returns None if not converging.
        """
        history = self.history.get(agent_id, [])
        if len(history) < 2:
            return None

        recent = history[-10:]
        distances = [p.distance_to(target) for p in recent]

        if len(distances) < 2:
            return None

        # Calculate average rate of approach
        distance_changes = [distances[i+1] - distances[i] for i in range(len(distances)-1)]
        avg_rate = sum(distance_changes) / len(distance_changes)

        if avg_rate >= 0:  # Not approaching
            return None

        current_distance = distances[-1]
        eta = current_distance / abs(avg_rate)

        return eta


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate 6D vector navigation system."""
    print("=" * 70)
    print("  6D VECTOR NAVIGATION SYSTEM - Swarm Coordination")
    print("=" * 70)
    print()

    # Create some agents
    print("[AGENTS] Creating swarm of 5 agents...")
    agents = {
        "ALPHA": Position6D(10.0, 5.0, 15.0, 5.0, 0.8, 200, agent_id="ALPHA"),
        "BETA": Position6D(12.0, 6.0, 14.0, 4.8, 0.7, 195, agent_id="BETA"),
        "GAMMA": Position6D(-20.0, 10.0, 25.0, 3.0, 0.3, 150, agent_id="GAMMA"),
        "DELTA": Position6D(50.0, -30.0, 5.0, 8.0, -0.2, 100, agent_id="DELTA"),
        "EPSILON": Position6D(11.0, 5.5, 14.5, 4.9, 0.75, 198, agent_id="EPSILON"),
    }

    for name, pos in agents.items():
        print(f"  {name}: X={pos.axiom:.1f}, Y={pos.flow:.1f}, Z={pos.glyph:.1f}, "
              f"V={pos.oracle:.1f}, H={pos.charm:.2f}, S={pos.ledger}")
    print()

    # Distance calculations
    print("[DISTANCE] Pairwise distances:")
    print(f"  ALPHA <-> BETA:    {agents['ALPHA'].distance_to(agents['BETA']):.2f} (close)")
    print(f"  ALPHA <-> GAMMA:   {agents['ALPHA'].distance_to(agents['GAMMA']):.2f} (medium)")
    print(f"  ALPHA <-> DELTA:   {agents['ALPHA'].distance_to(agents['DELTA']):.2f} (far)")
    print()

    # Docking system
    print("[DOCKING] Testing auto-lock docking...")
    docking = DockingSystem()

    # ALPHA and BETA should be docking-eligible (very close)
    eligibility_ab = docking.check_docking_eligibility(agents["ALPHA"], agents["BETA"])
    print(f"  ALPHA <-> BETA eligibility:")
    print(f"    Velocity delta: {eligibility_ab['velocity_delta']:.2f} m/s (ok={eligibility_ab['velocity_ok']})")
    print(f"    Security delta: {eligibility_ab['security_delta']} (ok={eligibility_ab['security_ok']})")
    print(f"    Spatial distance: {eligibility_ab['spatial_distance']:.2f}m (ok={eligibility_ab['spatial_ok']})")
    print(f"    ELIGIBLE: {eligibility_ab['eligible']}")

    # ALPHA and EPSILON are even closer
    eligibility_ae = docking.check_docking_eligibility(agents["ALPHA"], agents["EPSILON"])
    print(f"  ALPHA <-> EPSILON eligibility: {eligibility_ae['eligible']}")

    # Attempt dock
    lock = docking.attempt_dock(agents["ALPHA"], agents["EPSILON"])
    if lock:
        print(f"  DOCKING LOCK ESTABLISHED!")
        print(f"    Token: {lock.lock_token}")
        print(f"    Expiry: {lock.expiry}")
    print()

    # Formation management
    print("[FORMATION] Creating swarm formation...")
    swarm = SwarmFormation(formation_id="SWARM-001")
    for name, pos in agents.items():
        swarm.add_agent(name, pos)

    centroid = swarm.centroid
    print(f"  Centroid: X={centroid.axiom:.1f}, Y={centroid.flow:.1f}, Z={centroid.glyph:.1f}")
    print(f"  Avg distance from centroid: {swarm.avg_distance_from_centroid:.2f}")
    print(f"  Cohesion score: {swarm.cohesion_score:.3f}")
    print(f"  Alignment score: {swarm.alignment_score:.3f}")
    print(f"  Min separation: {swarm.min_separation:.2f}")
    print()

    # Hyperbolic distance
    print("[HYPERBOLIC] Security-aware distances:")
    for name in ["BETA", "GAMMA", "DELTA"]:
        hd = hyperbolic_distance_6d(agents["ALPHA"], agents[name])
        ed = agents["ALPHA"].distance_to(agents[name])
        print(f"  ALPHA <-> {name}: Euclidean={ed:.2f}, Hyperbolic={hd:.2f}")
    print()

    print("=" * 70)
    print("  6D Vector Navigation Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    demo()
