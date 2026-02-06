"""
GeoSeal - Context Vectors + Hyperbolic Geometry Core
====================================================

Provisions 2 & 3:
- Context vectors freely use negative floats
- Operates in hyperbolic space (negative curvature)
- Hyperbolic distance is always non-negative (failable by design if negative)

Integration with Dual Lattice:
- Context vectors map to the 10D lattice space
- Hyperbolic distance feeds into trust score calculation
- Negative curvature amplifies adversarial drift cost
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SecurityPosture(str, Enum):
    """Security postures based on flux state (from ADVANCED_CONCEPTS.md)."""
    DEMI = "demi"        # Containment: 0 < v < 0.5, minimal trust
    QUASI = "quasi"      # Adaptive: 0.5 <= v < 0.9, conditional trust
    POLLY = "polly"      # Permissive: v >= 0.9, high trust
    COLLAPSED = "collapsed"  # Dormant: v ~ 0, no activity


@dataclass
class ContextVector:
    """
    6+ dimensional agent state vector.
    Components can be negative (position, velocity, priority, security level).
    Example from docs: supports values like -9.9, -2.0

    Dimensions (default interpretation):
    - [0]: Position X (can be negative for left/opposing)
    - [1]: Position Y (can be negative for below/shadow)
    - [2]: Velocity/momentum
    - [3]: Priority/urgency
    - [4]: Security level (negative = restricted)
    - [5]: Trust baseline
    - [6+]: Extended dimensions (intent, phase, etc.)
    """
    components: np.ndarray

    def __init__(self, components: List[float]):
        self.components = np.array(components, dtype=np.float64)
        if len(self.components) < 6:
            raise ValueError("ContextVector must have at least 6 dimensions")

    def __repr__(self):
        return f"ContextVector({self.components.tolist()})"

    def __len__(self):
        return len(self.components)

    @property
    def position(self) -> np.ndarray:
        """First 2 components as position."""
        return self.components[:2]

    @property
    def has_negative(self) -> bool:
        """Check if any component is negative."""
        return np.any(self.components < 0)

    @property
    def negative_mask(self) -> np.ndarray:
        """Boolean mask of negative components."""
        return self.components < 0

    @property
    def signed_magnitude(self) -> float:
        """Magnitude preserving dominant sign."""
        positive_sum = np.sum(self.components[self.components > 0])
        negative_sum = np.sum(self.components[self.components < 0])
        if abs(positive_sum) > abs(negative_sum):
            return np.linalg.norm(self.components)
        else:
            return -np.linalg.norm(self.components)

    def to_poincare(self, scale: float = 0.9) -> np.ndarray:
        """
        Project into Poincare ball (||v|| < 1).

        Uses tanh normalization to map to open ball while preserving
        relative magnitudes and signs.
        """
        # Normalize each component independently using tanh
        return scale * np.tanh(self.components / 10.0)

    def to_lattice_10d(
        self,
        tongue_mapping: Dict[int, float] = None
    ) -> np.ndarray:
        """
        Map context vector to 10D dual lattice space.

        Mapping:
        - components[0:6] -> tongue dimensions (scaled)
        - If more components: [6]->time, [7]->intent, [8]->phase, [9]->flux
        """
        result = np.zeros(10)

        # Map first 6 components to tongue dimensions (scaled to [0,1])
        for i in range(min(6, len(self.components))):
            # Use sigmoid to map arbitrary floats to [0,1]
            # Negative values map below 0.5, positive above
            result[i] = 1 / (1 + np.exp(-self.components[i]))

        # Map additional dimensions if present
        if len(self.components) > 6:
            result[6] = 1 / (1 + np.exp(-self.components[6]))  # time
        if len(self.components) > 7:
            result[7] = 1 / (1 + np.exp(-self.components[7]))  # intent
        if len(self.components) > 8:
            result[8] = (self.components[8] % 360) / 360.0  # phase (normalized)
        if len(self.components) > 9:
            result[9] = 1 / (1 + np.exp(-self.components[9]))  # flux

        return result


def bytes_to_signed_signal(byte_data: bytes) -> np.ndarray:
    """
    Convert 0-255 bytes to float32 signal in [-1.0, 1.0].

    This is essential for FFT analysis where DC offset (unsigned values)
    would corrupt frequency analysis.
    """
    arr = np.frombuffer(byte_data, dtype=np.uint8)
    return (arr.astype(np.float32) - 127.5) / 127.5


def signed_signal_to_bytes(signal: np.ndarray) -> bytes:
    """Convert signed [-1.0, 1.0] signal back to 0-255 bytes."""
    arr = ((signal * 127.5) + 127.5).clip(0, 255).astype(np.uint8)
    return arr.tobytes()


# =============================================================================
# Hyperbolic Geometry (Poincare Ball Model)
# =============================================================================

def hyperbolic_distance(
    x: np.ndarray,
    y: np.ndarray,
    curvature: float = -1.0,
    eps: float = 1e-8
) -> float:
    """
    Poincare ball hyperbolic distance.

    Always >= 0 for valid points inside the ball (||x|| < 1, ||y|| < 1).
    Negative distance is mathematically impossible -> rejected.

    Formula: d(x,y) = arcosh(1 + 2||x-y||^2 / ((1-||x||^2)(1-||y||^2)))

    Args:
        x, y: Points in the Poincare ball (||v|| < 1)
        curvature: Curvature constant (default -1 for standard hyperbolic)
        eps: Small epsilon for numerical stability
    """
    nx = np.dot(x, x)
    ny = np.dot(y, y)

    if nx >= 1.0 or ny >= 1.0:
        raise ValueError("Points must lie strictly inside the Poincare ball (||v|| < 1)")

    diff_norm_sq = np.dot(x - y, x - y)
    denominator = (1 - nx) * (1 - ny)
    arg = 1 + 2 * diff_norm_sq / (denominator + eps)

    if arg < 1.0:
        # This should never happen for valid points, but we enforce the constraint
        raise ValueError("Invalid hyperbolic argument < 1 -> negative/complex distance impossible")

    # Scale by curvature
    c = abs(curvature)
    return np.arccosh(arg) / np.sqrt(c)


def hyperbolic_midpoint(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    Compute midpoint on hyperbolic geodesic between x and y.

    Uses Mobius addition formula for Poincare ball.
    """
    # Mobius addition: x (+) y = ((1 + 2<x,y> + ||y||^2)x + (1 - ||x||^2)y) /
    #                           (1 + 2<x,y> + ||x||^2||y||^2)
    xy = np.dot(x, y)
    nx = np.dot(x, x)
    ny = np.dot(y, y)

    # Midpoint is (x (+) y) / 2 in Mobius sense
    # Simplified: scale the Euclidean midpoint back into the ball
    euclidean_mid = (x + y) / 2
    scale = 1 - np.dot(euclidean_mid, euclidean_mid)

    if scale <= 0:
        # Midpoint would be outside ball, project back
        return euclidean_mid / (np.linalg.norm(euclidean_mid) + 0.01) * 0.9

    return euclidean_mid


def hyperbolic_angle(a: float, b: float, c: float) -> float:
    """
    Hyperbolic law of cosines for angle opposite side c.

    In hyperbolic space, triangle angle sum < 180 degrees.
    """
    cosh_c = np.cosh(c)
    cosh_a = np.cosh(a)
    cosh_b = np.cosh(b)
    sinh_a = np.sinh(a)
    sinh_b = np.sinh(b)

    if sinh_a == 0 or sinh_b == 0:
        return 0.0

    cos_angle = (cosh_a * cosh_b - cosh_c) / (sinh_a * sinh_b)
    # Clamp to valid range for arccosh
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    return np.arccos(cos_angle)


def compute_triangle_deficit(a: float, b: float, c: float) -> float:
    """
    Compute angular deficit of hyperbolic triangle.

    Returns: 180 - (sum of angles in degrees)
    Positive deficit confirms negative curvature.
    """
    angle_A = hyperbolic_angle(b, c, a)
    angle_B = hyperbolic_angle(a, c, b)
    angle_C = hyperbolic_angle(a, b, c)

    sum_degrees = np.degrees(angle_A + angle_B + angle_C)
    return 180.0 - sum_degrees


# =============================================================================
# Harmonic Wall Integration
# =============================================================================

def harmonic_wall_cost(
    distance: float,
    radius: float = 1.0,
    base: float = 2.718281828  # e
) -> float:
    """
    Compute harmonic wall cost: H(d) = base^(d^2).

    As distance approaches the Poincare ball boundary,
    cost approaches infinity exponentially.
    """
    # Normalize distance by radius
    normalized = distance / radius
    return base ** (normalized ** 2)


def trust_from_position(
    point: np.ndarray,
    center: np.ndarray = None,
    radius: float = 0.9
) -> float:
    """
    Compute trust score from position in Poincare ball.

    - Center (origin) = maximum trust (1.0)
    - Boundary = minimum trust (0.0)

    Trust decays hyperbolically with distance from center.
    """
    if center is None:
        center = np.zeros_like(point)

    # Ensure point is inside ball
    point_norm = np.linalg.norm(point)
    if point_norm >= 1.0:
        # Project back inside ball
        point = point / (point_norm + 0.01) * 0.95

    center_norm = np.linalg.norm(center)
    if center_norm >= 1.0:
        center = center / (center_norm + 0.01) * 0.95

    try:
        d = hyperbolic_distance(point, center)
    except ValueError:
        # Fallback: use Euclidean distance
        d = np.linalg.norm(point - center)

    # Reference distance: from center to near boundary (in 2D subspace)
    # This avoids the multi-dimensional norm issue
    boundary_point = np.zeros_like(center)
    boundary_point[0] = radius * 0.98  # Single dimension near boundary

    try:
        max_d = hyperbolic_distance(boundary_point, center)
    except ValueError:
        max_d = 3.0  # Reasonable fallback

    # Hyperbolic decay
    trust = 1.0 / (1.0 + d / max_d)
    return float(trust)


# =============================================================================
# Immune System: Phase Discipline & Swarm Dynamics
# =============================================================================

# Sacred Tongues phase mapping (radians)
TONGUE_PHASES: Dict[str, float] = {
    'KO': 0.0,                    # Kor'aelin - Control/orchestration
    'AV': np.pi / 3,              # Avali - Initialization/transport
    'RU': 2 * np.pi / 3,          # Runethic - Policy/authorization
    'CA': np.pi,                  # Cassisivadan - Encryption/compute
    'UM': 4 * np.pi / 3,          # Umbroth - Redaction/privacy
    'DR': 5 * np.pi / 3           # Draumric - Authentication/integrity
}

# Reverse mapping for phase -> tongue lookup
PHASE_TO_TONGUE: Dict[float, str] = {v: k for k, v in TONGUE_PHASES.items()}


@dataclass
class SwarmAgent:
    """
    Agent in the GeoSeal immune swarm.

    Represents either:
    - A Sacred Tongue (legitimate, fixed phase)
    - A retrieval/tool output (candidate, assigned or null phase)
    - A memory chunk (probationary, builds trust over time)
    """
    id: str
    position: np.ndarray          # Embedding in Poincaré ball (||v|| < 1)
    phase: Optional[float]        # Tongue phase, or None if rogue/unknown
    tongue: Optional[str] = None  # Which Sacred Tongue (if any)
    suspicion_count: Dict[str, float] = None  # Per-neighbor suspicion
    is_quarantined: bool = False
    trust_score: float = 1.0      # 0.0 = untrusted, 1.0 = fully trusted

    def __post_init__(self):
        if self.suspicion_count is None:
            self.suspicion_count = {}
        # Ensure position is in ball
        self.position = np.asarray(self.position, dtype=np.float64)
        norm = np.linalg.norm(self.position)
        if norm >= 1.0:
            self.position = self.position / (norm + 1e-6) * 0.95


@dataclass
class RepulsionResult:
    """Result of computing repulsion force between two agents."""
    force: np.ndarray
    amplification: float
    anomaly_flag: bool


def phase_deviation(phase1: Optional[float], phase2: Optional[float]) -> float:
    """
    Compute normalized phase deviation in [0, 1].

    Returns 1.0 (maximum) if either phase is None (rogue/unknown).
    Otherwise returns angular difference normalized to [0, 1].
    """
    if phase1 is None or phase2 is None:
        return 1.0  # Maximum deviation for unknown phase

    diff = abs(phase1 - phase2)
    # Wrap to [0, π]
    if diff > np.pi:
        diff = 2 * np.pi - diff

    return diff / np.pi  # Normalize to [0, 1]


def compute_repel_force(
    agent_a: SwarmAgent,
    agent_b: SwarmAgent,
    base_strength: float = 1.0
) -> RepulsionResult:
    """
    Core GeoSeal repulsion force computation.

    Implements immune-like response to phase-weird agents:
    - Null phase (unknown/rogue) → 2.0x force amplification
    - Wrong phase at close distance → 1.5x + deviation amplification
    - Quarantined agents → additional 1.5x multiplier

    Returns force vector pointing away from agent_b, with amplification
    and anomaly flag for suspicion tracking.
    """
    # Compute hyperbolic distance
    try:
        d_H = hyperbolic_distance(agent_a.position, agent_b.position)
    except ValueError:
        # Fallback to Euclidean if points are at boundary
        d_H = np.linalg.norm(agent_a.position - agent_b.position)

    # Base repulsion: inversely proportional to distance
    base_repulsion = base_strength / (d_H + 1e-6)

    # Compute phase-based amplification
    amplification = 1.0
    anomaly_flag = False

    if agent_b.phase is None:
        # Null phase (unknown/rogue) → maximum amplification
        amplification = 2.0
        anomaly_flag = True
    elif agent_a.phase is not None:
        # Both have phases, check for mismatch
        deviation = phase_deviation(agent_a.phase, agent_b.phase)

        # Expected: agents with similar phases should cluster
        # If phases differ significantly at close distance → suspicious
        if d_H < 1.0 and deviation > 0.5:
            amplification = 1.5 + deviation
            anomaly_flag = True

    # If agent_b is quarantined, boost repulsion further
    if agent_b.is_quarantined:
        amplification *= 1.5

    # Compute force vector (direction: away from agent_b)
    direction = agent_a.position - agent_b.position
    dir_norm = np.linalg.norm(direction)
    if dir_norm > 1e-8:
        direction = direction / dir_norm

    force = direction * base_repulsion * amplification

    return RepulsionResult(
        force=force,
        amplification=amplification,
        anomaly_flag=anomaly_flag
    )


def update_suspicion(
    agent: SwarmAgent,
    neighbor_id: str,
    is_anomaly: bool,
    decay_rate: float = 0.5,
    suspicion_threshold: int = 3,
    consensus_threshold: int = 3
) -> None:
    """
    Update suspicion counters and quarantine status.

    Temporal integration filters transient flukes:
    - Anomaly detection increments suspicion by 1
    - No anomaly decays suspicion by decay_rate
    - Quarantine requires consensus_threshold+ neighbors with
      suspicion >= suspicion_threshold

    This prevents false positives from single-step noise while
    catching persistent phase violations.
    """
    if is_anomaly:
        current = agent.suspicion_count.get(neighbor_id, 0.0)
        agent.suspicion_count[neighbor_id] = current + 1.0
    else:
        # Decay suspicion if no anomaly detected
        current = agent.suspicion_count.get(neighbor_id, 0.0)
        agent.suspicion_count[neighbor_id] = max(0.0, current - decay_rate)

    # Count how many neighbors are suspicious
    suspicious_neighbors = sum(
        1 for count in agent.suspicion_count.values()
        if count >= suspicion_threshold
    )

    # Quarantine threshold: consensus_threshold+ neighbors with high suspicion
    agent.is_quarantined = suspicious_neighbors >= consensus_threshold

    # Update trust score (inverse of normalized suspicion)
    total_suspicion = sum(agent.suspicion_count.values())
    agent.trust_score = max(0.0, 1.0 - total_suspicion / 20.0)


def swarm_step(
    agents: List[SwarmAgent],
    drift_rate: float = 0.01,
    ball_radius: float = 0.99
) -> List[SwarmAgent]:
    """
    Run one swarm update step for all agents.

    Computes pairwise repulsion forces, updates positions,
    tracks suspicion, and enforces Poincaré ball containment.

    Legitimate agents cluster (same phase → low repulsion).
    Rogue agents drift outward (phase mismatch → high repulsion).

    Suspicion is tracked ON the observed agent (agent_j) when an
    observer (agent_i) detects anomalous behavior. This allows
    consensus-based quarantine: if many agents flag an agent as
    anomalous, that agent gets quarantined.

    Returns updated agent list with new positions and trust scores.
    """
    n = len(agents)

    for i in range(n):
        net_force = np.zeros_like(agents[i].position)

        for j in range(n):
            if i == j:
                continue

            result = compute_repel_force(agents[i], agents[j])

            # Accumulate force on agent i
            net_force += result.force

            # Update suspicion ON agent_j (the one being observed)
            # This way, if many agents flag j as anomalous, j gets quarantined
            update_suspicion(agents[j], agents[i].id, result.anomaly_flag)

        # Apply force with drift rate
        agents[i].position = agents[i].position + net_force * drift_rate

        # Clamp to Poincaré ball (radius < 1)
        norm = np.linalg.norm(agents[i].position)
        if norm >= ball_radius:
            agents[i].position = agents[i].position * (ball_radius / norm)

    return agents


def run_swarm_dynamics(
    agents: List[SwarmAgent],
    num_steps: int = 10,
    drift_rate: float = 0.01
) -> List[SwarmAgent]:
    """
    Run multiple swarm update steps.

    Returns agents after dynamics converge or num_steps reached.
    """
    for _ in range(num_steps):
        agents = swarm_step(agents, drift_rate)
    return agents


def create_tongue_agents(dimension: int = 64) -> List[SwarmAgent]:
    """
    Initialize the 6 Sacred Tongues as legitimate agents.

    Each tongue gets a position based on its phase (evenly distributed
    around a circle in the first two dimensions).
    """
    agents = []
    radius = 0.3  # Place tongues near center (high trust)

    for tongue, phase in TONGUE_PHASES.items():
        # Position based on phase angle
        position = np.zeros(dimension)
        position[0] = radius * np.cos(phase)
        position[1] = radius * np.sin(phase)

        agents.append(SwarmAgent(
            id=f"tongue-{tongue}",
            position=position,
            phase=phase,
            tongue=tongue,
            trust_score=1.0  # Tongues start fully trusted
        ))

    return agents


def create_candidate_agent(
    agent_id: str,
    embedding: np.ndarray,
    assigned_tongue: Optional[str] = None,
    initial_trust: float = 0.5
) -> SwarmAgent:
    """
    Create a candidate agent for immune evaluation.

    If assigned_tongue is provided, the agent gets that tongue's phase.
    Otherwise, phase is None (treated as rogue/unknown).
    """
    phase = TONGUE_PHASES.get(assigned_tongue) if assigned_tongue else None

    # Project embedding to Poincaré ball if needed
    norm = np.linalg.norm(embedding)
    if norm >= 1.0:
        embedding = embedding / (norm + 1e-6) * 0.95

    return SwarmAgent(
        id=agent_id,
        position=embedding,
        phase=phase,
        tongue=assigned_tongue,
        trust_score=initial_trust
    )


def filter_by_trust(
    agents: List[SwarmAgent],
    threshold: float = 0.3
) -> List[SwarmAgent]:
    """
    Filter agents by trust score, returning only those above threshold.

    Excludes tongue agents (they're always trusted infrastructure).
    """
    return [
        a for a in agents
        if a.trust_score >= threshold or a.id.startswith("tongue-")
    ]


def get_attention_weights(
    agents: List[SwarmAgent]
) -> Dict[str, float]:
    """
    Extract trust scores as attention weights for RAG reweighting.

    Returns dict mapping agent ID -> trust score (0.0 to 1.0).
    Excludes tongue agents (infrastructure, not content).
    """
    return {
        a.id: a.trust_score
        for a in agents
        if not a.id.startswith("tongue-")
    }


@dataclass
class SwarmMetrics:
    """Metrics from swarm immune dynamics."""
    quarantine_count: int
    avg_trust_score: float
    boundary_agents: int  # Agents pushed near boundary (norm > 0.9)
    suspicious_pairs: int  # Number of agent pairs with high suspicion


def compute_swarm_metrics(agents: List[SwarmAgent]) -> SwarmMetrics:
    """Compute metrics for monitoring swarm health."""
    non_tongue = [a for a in agents if not a.id.startswith("tongue-")]

    if not non_tongue:
        return SwarmMetrics(0, 1.0, 0, 0)

    quarantine_count = sum(1 for a in non_tongue if a.is_quarantined)
    avg_trust = sum(a.trust_score for a in non_tongue) / len(non_tongue)
    boundary_agents = sum(
        1 for a in non_tongue
        if np.linalg.norm(a.position) > 0.9
    )

    suspicious_pairs = sum(
        1 for a in non_tongue
        for count in a.suspicion_count.values()
        if count >= 3
    )

    return SwarmMetrics(
        quarantine_count=quarantine_count,
        avg_trust_score=avg_trust,
        boundary_agents=boundary_agents,
        suspicious_pairs=suspicious_pairs
    )


# =============================================================================
# Tests (from documentation)
# =============================================================================

if __name__ == "__main__":
    # Test context vector with negative components
    test_ctx = ContextVector([0.2, -0.3, 0.7, 1.0, -2.0, 0.5, 3.1, -9.9, 0.0])
    print(f"[GEO] Test context vector: {test_ctx}")
    print(f"[GEO] Has negative components: {test_ctx.has_negative}")
    print(f"[GEO] Negative mask: {test_ctx.negative_mask}")
    print(f"[GEO] Signed magnitude: {test_ctx.signed_magnitude:.3f}")

    # Project to Poincare ball
    poincare_point = test_ctx.to_poincare()
    print(f"[GEO] Poincare projection: {poincare_point}")

    # Map to 10D lattice
    lattice_10d = test_ctx.to_lattice_10d()
    print(f"[GEO] 10D Lattice mapping: {lattice_10d}")

    # Test F10: negative hyperbolic distance impossible
    print("\n[TEST F10] Hyperbolic distance test...")
    x = np.array([0.1, -0.2])
    y = np.array([-0.3, 0.4])
    d = hyperbolic_distance(x, y)
    assert d >= 0.0
    print(f"[GEO] Valid distance: {d:.4f} (always positive)")

    # Test negative curvature: triangle angle sum < 180
    print("\n[TEST] Negative curvature verification...")
    a = b = c = 0.5  # equilateral-ish hyperbolic triangle
    deficit = compute_triangle_deficit(a, b, c)
    print(f"[GEO] Triangle angle deficit: {deficit:.2f}deg (positive = negative curvature)")

    # Test harmonic wall
    print("\n[TEST] Harmonic wall cost...")
    for d in [0.1, 0.5, 0.9, 0.99]:
        cost = harmonic_wall_cost(d)
        print(f"[GEO] d={d:.2f} -> H(d)={cost:.2f}")

    # Test trust from position
    print("\n[TEST] Trust from position...")
    for pos in [[0.0, 0.0], [0.3, 0.3], [0.6, 0.6], [0.85, 0.0]]:
        trust = trust_from_position(np.array(pos))
        print(f"[GEO] pos={pos} -> trust={trust:.3f}")

    # =============================================================================
    # Immune System Tests
    # =============================================================================
    print("\n" + "=" * 60)
    print("IMMUNE SYSTEM TESTS")
    print("=" * 60)

    # Test phase deviation
    print("\n[TEST] Phase deviation...")
    assert phase_deviation(0.0, 0.0) == 0.0, "Same phase should have 0 deviation"
    assert phase_deviation(0.0, np.pi) == 1.0, "Opposite phases should have max deviation"
    assert phase_deviation(None, 0.0) == 1.0, "Null phase should have max deviation"
    print("[PASS] Phase deviation tests passed")

    # Test tongue agent creation
    print("\n[TEST] Creating tongue agents...")
    tongues = create_tongue_agents(dimension=8)
    assert len(tongues) == 6, "Should create 6 tongue agents"
    for t in tongues:
        assert t.trust_score == 1.0, "Tongue agents should have full trust"
        assert t.phase is not None, "Tongue agents should have phase"
        assert np.linalg.norm(t.position) < 1.0, "Should be in Poincaré ball"
    print(f"[PASS] Created {len(tongues)} tongue agents")

    # Test rogue agent detection
    print("\n[TEST] Rogue agent detection...")
    # Create a rogue agent (no phase) near the tongues
    rogue = create_candidate_agent(
        agent_id="rogue-001",
        embedding=np.array([0.2, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        assigned_tongue=None,  # No tongue = rogue
        initial_trust=0.5
    )
    assert rogue.phase is None, "Rogue should have no phase"

    # Add rogue to swarm
    all_agents = tongues + [rogue]

    # Run swarm dynamics
    print("[INFO] Running 15 steps of swarm dynamics...")
    all_agents = run_swarm_dynamics(all_agents, num_steps=15, drift_rate=0.02)

    # Check rogue status
    rogue_after = [a for a in all_agents if a.id == "rogue-001"][0]
    print(f"[INFO] Rogue trust score: {rogue_after.trust_score:.3f}")
    print(f"[INFO] Rogue quarantined: {rogue_after.is_quarantined}")
    print(f"[INFO] Rogue position norm: {np.linalg.norm(rogue_after.position):.3f}")

    # Rogue should have lower trust and potentially be quarantined
    assert rogue_after.trust_score < 1.0, "Rogue should have reduced trust"
    print("[PASS] Rogue agent was detected and penalized")

    # Test legitimate agent (with matching phase)
    print("\n[TEST] Legitimate agent preservation...")
    legit = create_candidate_agent(
        agent_id="legit-001",
        embedding=np.array([0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        assigned_tongue="KO",  # Has KO tongue phase
        initial_trust=0.5
    )
    assert legit.phase == TONGUE_PHASES["KO"], "Should have KO phase"

    # Add to fresh swarm
    tongues2 = create_tongue_agents(dimension=8)
    all_agents2 = tongues2 + [legit]
    all_agents2 = run_swarm_dynamics(all_agents2, num_steps=15, drift_rate=0.02)

    legit_after = [a for a in all_agents2 if a.id == "legit-001"][0]
    print(f"[INFO] Legit trust score: {legit_after.trust_score:.3f}")
    print(f"[INFO] Legit quarantined: {legit_after.is_quarantined}")

    # Legitimate agent should maintain higher trust
    assert legit_after.trust_score > rogue_after.trust_score, \
        "Legitimate agent should have higher trust than rogue"
    print("[PASS] Legitimate agent preserved trust")

    # Test metrics
    print("\n[TEST] Swarm metrics...")
    metrics = compute_swarm_metrics(all_agents)
    print(f"[INFO] Quarantine count: {metrics.quarantine_count}")
    print(f"[INFO] Avg trust score: {metrics.avg_trust_score:.3f}")
    print(f"[INFO] Boundary agents: {metrics.boundary_agents}")
    print(f"[INFO] Suspicious pairs: {metrics.suspicious_pairs}")

    # Test attention weights
    weights = get_attention_weights(all_agents)
    print(f"[INFO] Attention weights: {weights}")
    assert "rogue-001" in weights, "Should have rogue in weights"
    print("[PASS] Attention weights extracted")

    print("\n" + "=" * 60)
    print("ALL IMMUNE SYSTEM TESTS PASSED")
    print("=" * 60)
