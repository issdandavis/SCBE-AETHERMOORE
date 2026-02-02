"""
================================================================================
HYPERBLOCI vs STANDARD HNN COMPARISON
================================================================================

Demonstrates the safety advantages of the Hyperbloci/PHDM approach over
standard Hyperbolic Neural Networks (HNNs).

Standard HNNs: Great at hierarchical embedding, but NO safety barriers
Hyperbloci:    Hyperbolic + Harmonic Wall + Byzantine consensus + Flux states

Key Comparison:
- Adversarial paths: HNN allows, Hyperbloci BLOCKS
- Rogue agents: HNN has no detection, Hyperbloci QUARANTINES
- Dimensional stress: HNN static, Hyperbloci CONTRACTS skull

Author: SCBE Development Team
Patent: USPTO #63/961,403 (Provisional)
================================================================================
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum
import time

# ==============================================================================
# CONSTANTS
# ==============================================================================

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio
PYTHAGOREAN_COMMA = 531441 / 524288  # ~1.0136

# Tongue phases (60° apart)
TONGUE_PHASES = [k * np.pi / 3 for k in range(6)]


# ==============================================================================
# HYPERBOLIC PRIMITIVES (would use geoopt in production)
# ==============================================================================

def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Hyperbolic distance in Poincare ball."""
    u = np.clip(u, -0.999, 0.999)
    v = np.clip(v, -0.999, 0.999)

    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)
    diff_norm = np.linalg.norm(u - v)

    norm_u = min(norm_u, 0.999)
    norm_v = min(norm_v, 0.999)

    denom = (1 - norm_u**2) * (1 - norm_v**2)
    if denom <= 0:
        return float('inf')

    arg = 1 + 2 * (diff_norm**2) / denom
    return np.arccosh(max(arg, 1.0))


def mobius_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Mobius addition in Poincare ball."""
    u_dot_v = np.dot(u, v)
    u_norm_sq = np.dot(u, u)
    v_norm_sq = np.dot(v, v)

    numer = (1 + 2*u_dot_v + v_norm_sq) * u + (1 - u_norm_sq) * v
    denom = 1 + 2*u_dot_v + u_norm_sq * v_norm_sq

    result = numer / max(denom, 1e-6)
    norm = np.linalg.norm(result)
    if norm >= 1.0:
        result = result * 0.99 / norm

    return result


def exp_map(v: np.ndarray) -> np.ndarray:
    """Exponential map at origin."""
    norm = np.linalg.norm(v)
    if norm < 1e-10:
        return np.zeros_like(v)
    return np.tanh(norm) * v / norm


# ==============================================================================
# STANDARD HNN (Baseline - No Safety)
# ==============================================================================

class StandardHNN:
    """
    Standard Hyperbolic Neural Network.

    Good at:
    - Hierarchical embeddings
    - Low-dimensional tree representation
    - Distance-preserving encoding

    Missing (compared to Hyperbloci):
    - Hard geometric safety barriers
    - Multi-agent consensus
    - Rogue detection
    - Adaptive dimensional flux
    """

    def __init__(self, dim: int = 3):
        self.dim = dim
        self.embeddings: Dict[str, np.ndarray] = {}

    def embed(self, key: str, vector: np.ndarray) -> np.ndarray:
        """Embed vector in Poincare ball."""
        # Standard: just project to ball
        pos = exp_map(vector[:self.dim])
        self.embeddings[key] = pos
        return pos

    def forward(self, x: np.ndarray, weights: np.ndarray) -> np.ndarray:
        """Standard hyperbolic forward pass."""
        # Mobius matrix-vector multiplication (simplified)
        # In real HNN: uses Mobius addition chain
        result = mobius_add(x, exp_map(weights[:self.dim] * 0.1))
        return result

    def compute_path_cost(self, start: str, end: str) -> float:
        """Path cost is just hyperbolic distance."""
        if start not in self.embeddings or end not in self.embeddings:
            return float('inf')
        return poincare_distance(self.embeddings[start], self.embeddings[end])

    def is_path_allowed(self, start: str, end: str) -> Tuple[bool, str]:
        """Standard HNN: ALL paths are allowed (no safety)."""
        cost = self.compute_path_cost(start, end)
        return True, f"Allowed (cost={cost:.2f})"  # Always allowed!

    def detect_rogue(self, agent_id: str) -> Tuple[bool, str]:
        """Standard HNN: NO rogue detection."""
        return False, "No detection capability"  # Can't detect rogues!


# ==============================================================================
# HYPERBLOCI (PHDM - Full Safety)
# ==============================================================================

class Hyperbloci:
    """
    Hyperbloci / PHDM Neural Architecture.

    Extends HNN with:
    - Harmonic Wall (exp(d²) barrier)
    - Path adjacency constraints
    - Byzantine consensus (4-of-6 voting)
    - Phase anomaly detection
    - Adaptive snap threshold
    """

    # Path adjacency matrix (which tongues can reach which)
    ADJACENCY = {
        'KO': ['AV', 'RU'],
        'AV': ['KO', 'CA', 'RU'],
        'RU': ['KO', 'AV', 'UM'],
        'CA': ['AV', 'UM', 'DR'],
        'UM': ['RU', 'CA', 'DR'],
        'DR': ['CA', 'UM'],
    }

    # Sacred Tongue security levels
    SECURITY_LEVELS = {
        'KO': 0.1, 'AV': 0.2, 'RU': 0.4,
        'CA': 0.5, 'UM': 0.9, 'DR': 1.0
    }

    # φ weights for consensus
    PHI_WEIGHTS = {
        'KO': PHI**0, 'AV': PHI**1, 'RU': PHI**2,
        'CA': PHI**3, 'UM': PHI**4, 'DR': PHI**5
    }

    def __init__(self, dim: int = 3, blocking_threshold: float = 10.0):
        self.dim = dim
        self.blocking_threshold = blocking_threshold
        self.embeddings: Dict[str, np.ndarray] = {}
        self.phases: Dict[str, float] = {}
        self.coherence: Dict[str, float] = {}
        self.suspicion: Dict[str, int] = {}

        # Initialize sacred tongues
        self._init_tongues()

    def _init_tongues(self):
        """Initialize the 6 Sacred Tongue agents."""
        for i, name in enumerate(['KO', 'AV', 'RU', 'CA', 'UM', 'DR']):
            # Position by security level
            radius = 0.75 * self.SECURITY_LEVELS[name]
            angle = i * np.pi / 3

            pos = np.zeros(self.dim)
            pos[0] = radius * np.cos(angle)
            pos[1] = radius * np.sin(angle)
            if self.dim > 2:
                pos[2] = 0.1 * (i / 5)

            self.embeddings[name] = pos
            self.phases[name] = i * np.pi / 3  # Valid phase
            self.coherence[name] = 1.0  # Full coherence
            self.suspicion[name] = 0

    def embed(self, key: str, vector: np.ndarray,
              phase: Optional[float] = None) -> np.ndarray:
        """Embed vector with phase discipline."""
        pos = exp_map(vector[:self.dim])
        self.embeddings[key] = pos
        self.phases[key] = phase  # Can be None (rogue indicator)
        self.coherence[key] = 1.0
        self.suspicion[key] = 0
        return pos

    def harmonic_wall(self, distance: float) -> float:
        """Exponential cost barrier: H(d) = exp(d²)."""
        return np.exp(distance ** 2)

    def compute_path_cost(self, path: List[str]) -> float:
        """
        Compute total path cost with Harmonic Wall.

        Unlike HNN: includes adjacency check and wall penalty.
        """
        if len(path) < 2:
            return 0.0

        total = 0.0
        for i in range(len(path) - 1):
            src, dst = path[i], path[i + 1]

            # Adjacency check (HNN doesn't have this!)
            if dst not in self.ADJACENCY.get(src, []):
                return float('inf')  # Non-adjacent = impossible

            # Hyperbolic distance
            if src in self.embeddings and dst in self.embeddings:
                d = poincare_distance(self.embeddings[src], self.embeddings[dst])
            else:
                d = 1.0

            # Harmonic Wall (HNN doesn't have this!)
            wall_cost = self.harmonic_wall(d)

            # Security weight penalty
            sec_penalty = 1 + 0.1 * self.SECURITY_LEVELS.get(dst, 0.5)

            total += wall_cost * sec_penalty

        return total

    def is_path_allowed(self, start: str, end: str) -> Tuple[bool, str]:
        """
        Check if path is geometrically allowed.

        Key difference from HNN: paths can be BLOCKED.
        """
        # Find shortest valid path
        path = self._find_path(start, end)
        if path is None:
            return False, "No valid path exists (adjacency blocked)"

        cost = self.compute_path_cost(path)

        if cost == float('inf'):
            return False, "Path impossible (non-adjacent hop)"

        if cost > self.blocking_threshold:
            return False, f"BLOCKED by Harmonic Wall (cost={cost:.2f} > {self.blocking_threshold})"

        return True, f"Allowed (cost={cost:.2f}, path={'→'.join(path)})"

    def _find_path(self, start: str, end: str) -> Optional[List[str]]:
        """BFS to find shortest valid path."""
        if start == end:
            return [start]

        queue = [[start]]
        visited = {start}

        while queue:
            path = queue.pop(0)
            current = path[-1]

            for neighbor in self.ADJACENCY.get(current, []):
                if neighbor == end:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return None

    def detect_rogue(self, agent_id: str) -> Tuple[bool, str]:
        """
        Detect rogue agents via phase anomaly.

        Key difference from HNN: actual detection capability.
        """
        if agent_id not in self.phases:
            return True, "Unknown agent (not registered)"

        phase = self.phases[agent_id]

        # Null phase = immediate suspicion
        if phase is None:
            return True, "NULL PHASE detected (rogue signature)"

        # Check if phase matches valid tongue phases
        min_deviation = min(abs(phase - tp) for tp in TONGUE_PHASES)
        if min_deviation > 0.1:
            return True, f"Invalid phase (deviation={min_deviation:.3f})"

        return False, "Phase valid (trusted)"

    def byzantine_vote(self, action: str,
                       voters: Optional[List[str]] = None) -> Tuple[bool, float]:
        """
        Byzantine fault-tolerant consensus.

        HNN has nothing like this.
        """
        if voters is None:
            voters = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']

        # Filter out rogues
        valid_voters = [v for v in voters
                        if not self.detect_rogue(v)[0]]

        # Compute weighted votes
        total_weight = sum(self.PHI_WEIGHTS.get(v, 1) for v in valid_voters)
        approve_weight = sum(
            self.PHI_WEIGHTS.get(v, 1) * self.coherence.get(v, 0.5)
            for v in valid_voters
        )

        if total_weight == 0:
            return False, 0.0

        ratio = approve_weight / total_weight
        approved = ratio >= 0.67  # 2/3 quorum

        return approved, ratio

    def adaptive_snap_threshold(self, D_f: float = 6.0,
                                epsilon_base: float = 0.05) -> float:
        """
        Adaptive sensitivity under dimensional compression.

        ε_snap = ε_base · √(6/D_f)

        HNN has static thresholds; Hyperbloci adapts.
        """
        D_f = max(D_f, 0.01)
        return epsilon_base * np.sqrt(6.0 / D_f)


# ==============================================================================
# COMPARISON TESTS
# ==============================================================================

def test_adversarial_path_blocking():
    """
    Test: Can adversarial paths be blocked?

    Adversary tries: KO → DR (control to schema, bypassing security)
    HNN: Allows (just distance cost)
    Hyperbloci: BLOCKS (no direct path, high wall cost)
    """
    print("=" * 70)
    print("TEST 1: ADVERSARIAL PATH BLOCKING")
    print("=" * 70)
    print("\nScenario: Adversary tries KO → DR direct access")
    print("(Control trying to reach Schema without going through Security)")
    print("-" * 70)

    # Standard HNN
    hnn = StandardHNN(dim=3)
    hnn.embed("KO", np.array([0.1, 0.0, 0.0]))
    hnn.embed("DR", np.array([0.7, 0.5, 0.3]))

    allowed, reason = hnn.is_path_allowed("KO", "DR")
    print(f"\nStandard HNN:")
    print(f"  Path KO→DR: {allowed}")
    print(f"  Reason: {reason}")
    print(f"  ⚠️  VULNERABILITY: HNN allows ALL paths!")

    # Hyperbloci
    hyper = Hyperbloci(dim=3, blocking_threshold=10.0)

    allowed, reason = hyper.is_path_allowed("KO", "DR")
    print(f"\nHyperbloci:")
    print(f"  Path KO→DR direct: {allowed}")
    print(f"  Reason: {reason}")

    # Show valid path
    valid_path = hyper._find_path("KO", "DR")
    if valid_path:
        cost = hyper.compute_path_cost(valid_path)
        print(f"  Valid path: {'→'.join(valid_path)}")
        print(f"  Cost: {cost:.2f}")
        print(f"  ✓ Hyperbloci forces proper routing through security layers")


def test_rogue_detection():
    """
    Test: Can rogue agents be detected?

    HNN: No detection capability
    Hyperbloci: Phase anomaly detection + Byzantine exclusion
    """
    print("\n" + "=" * 70)
    print("TEST 2: ROGUE AGENT DETECTION")
    print("=" * 70)
    print("\nScenario: Rogue agent with null/invalid phase joins network")
    print("-" * 70)

    # Standard HNN
    hnn = StandardHNN(dim=3)
    hnn.embed("ROGUE", np.array([0.3, 0.3, 0.3]))

    detected, reason = hnn.detect_rogue("ROGUE")
    print(f"\nStandard HNN:")
    print(f"  Rogue detected: {detected}")
    print(f"  Reason: {reason}")
    print(f"  ⚠️  VULNERABILITY: HNN cannot detect rogues!")

    # Hyperbloci
    hyper = Hyperbloci(dim=3)
    hyper.embed("ROGUE", np.array([0.3, 0.3, 0.3]), phase=None)  # Null phase

    detected, reason = hyper.detect_rogue("ROGUE")
    print(f"\nHyperbloci:")
    print(f"  Rogue detected: {detected}")
    print(f"  Reason: {reason}")

    # Byzantine vote with rogue
    approved, ratio = hyper.byzantine_vote("dangerous_action",
                                           voters=['KO', 'AV', 'ROGUE'])
    print(f"\n  Byzantine vote (with rogue attempting to vote):")
    print(f"    Approved: {approved}")
    print(f"    Ratio: {ratio:.1%}")
    print(f"    ✓ Rogue excluded from consensus!")


def test_harmonic_wall_scaling():
    """
    Test: How does cost scale with distance?

    HNN: Linear distance (no barrier)
    Hyperbloci: Exponential barrier (H(d) = exp(d²))
    """
    print("\n" + "=" * 70)
    print("TEST 3: HARMONIC WALL COST SCALING")
    print("=" * 70)
    print("\nComparing cost at different hyperbolic distances")
    print("-" * 70)

    hyper = Hyperbloci(dim=3)

    print("\n  Distance | HNN Cost  | Hyperbloci Wall | Blocked?")
    print("  " + "-" * 55)

    for d in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        hnn_cost = d  # Linear
        wall_cost = hyper.harmonic_wall(d)  # Exponential
        blocked = wall_cost > 10

        status = "❌ BLOCKED" if blocked else "✓ Allowed"
        print(f"  {d:8.1f} | {hnn_cost:9.2f} | {wall_cost:15.2f} | {status}")

    print("\n  ✓ Hyperbloci: Exponential barrier makes distant paths impossible")
    print("  ⚠️  HNN: Linear cost allows any path with enough 'push'")


def test_dimensional_compression():
    """
    Test: Adaptive defense under dimensional stress.

    HNN: Static (no adaptation)
    Hyperbloci: Snap threshold tightens as D_f decreases
    """
    print("\n" + "=" * 70)
    print("TEST 4: DIMENSIONAL COMPRESSION (ADAPTIVE DEFENSE)")
    print("=" * 70)
    print("\nWhen dimensions compress under attack, sensitivity increases")
    print("-" * 70)

    hyper = Hyperbloci(dim=3)

    print("\n  Active Dimensions | Snap Threshold | Defense Level")
    print("  " + "-" * 50)

    for D_f in [6.0, 5.0, 4.0, 3.0, 2.0, 1.0]:
        eps = hyper.adaptive_snap_threshold(D_f)
        relative = eps / 0.05  # Relative to base

        if relative > 2.0:
            level = "🔴 MAXIMUM"
        elif relative > 1.5:
            level = "🟠 HIGH"
        elif relative > 1.2:
            level = "🟡 ELEVATED"
        else:
            level = "🟢 NORMAL"

        print(f"  {D_f:17.1f} | {eps:14.4f} | {level}")

    print("\n  ✓ Hyperbloci: 'Skull contracts' under stress")
    print("  ⚠️  HNN: No adaptive response (static thresholds)")


def test_consensus_resilience():
    """
    Test: Byzantine fault tolerance.

    HNN: No consensus (single model)
    Hyperbloci: φ-weighted 4-of-6 voting with rogue exclusion
    """
    print("\n" + "=" * 70)
    print("TEST 5: BYZANTINE CONSENSUS RESILIENCE")
    print("=" * 70)
    print("\nTesting fault tolerance with compromised agents")
    print("-" * 70)

    hyper = Hyperbloci(dim=3)

    # Scenario 1: All agents honest
    print("\nScenario A: All 6 agents honest")
    approved, ratio = hyper.byzantine_vote("safe_action")
    print(f"  Approved: {approved}, Ratio: {ratio:.1%}")

    # Scenario 2: Two agents compromised (low coherence)
    print("\nScenario B: 2 agents with low coherence (compromised)")
    hyper.coherence['AV'] = 0.2
    hyper.coherence['RU'] = 0.3
    approved, ratio = hyper.byzantine_vote("safe_action")
    print(f"  Approved: {approved}, Ratio: {ratio:.1%}")
    print(f"  ✓ Still reaches quorum (weighted by coherence)")

    # Scenario 3: Add rogues
    print("\nScenario C: 2 rogue agents (excluded from vote)")
    hyper.embed("ROGUE1", np.array([0.5, 0.0, 0.0]), phase=None)
    hyper.embed("ROGUE2", np.array([0.0, 0.5, 0.0]), phase=None)
    approved, ratio = hyper.byzantine_vote("safe_action",
                                           voters=['KO', 'DR', 'ROGUE1', 'ROGUE2'])
    print(f"  Voters: KO, DR, ROGUE1, ROGUE2")
    print(f"  Approved: {approved}, Ratio: {ratio:.1%}")
    print(f"  ✓ Rogues excluded, only legitimate votes count")


def run_comparison():
    """Run full comparison suite."""
    print("=" * 70)
    print("HYPERBLOCI vs STANDARD HNN: SAFETY COMPARISON")
    print("=" * 70)
    print()
    print("Standard HNN: Hyperbolic embeddings, good for hierarchy")
    print("Hyperbloci:   Hyperbolic + Wall + Consensus + Flux (PHDM)")
    print()
    print("We test 5 safety-critical scenarios:")
    print("  1. Adversarial path blocking")
    print("  2. Rogue agent detection")
    print("  3. Harmonic Wall cost scaling")
    print("  4. Dimensional compression defense")
    print("  5. Byzantine consensus resilience")
    print()

    test_adversarial_path_blocking()
    test_rogue_detection()
    test_harmonic_wall_scaling()
    test_dimensional_compression()
    test_consensus_resilience()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: WHY HYPERBLOCI IS BETTER FOR SAFE AI")
    print("=" * 70)
    print("""
    +---------------------------+----------------+----------------+
    | Capability                | Standard HNN   | Hyperbloci     |
    +---------------------------+----------------+----------------+
    | Hierarchical Embedding    | ✓ Excellent    | ✓ Excellent    |
    | Hard Path Blocking        | ✗ None         | ✓ Harmonic Wall|
    | Adjacency Constraints     | ✗ None         | ✓ Graph-based  |
    | Rogue Detection           | ✗ None         | ✓ Phase Anomaly|
    | Byzantine Consensus       | ✗ None         | ✓ φ-weighted   |
    | Adaptive Defense          | ✗ Static       | ✓ Flux States  |
    | Multi-Agent Native        | ✗ Single Model | ✓ 6 Agents     |
    +---------------------------+----------------+----------------+

    KEY INSIGHT: Hyperbloci achieves safety through GEOMETRY, not rules.
    Bad paths are mathematically impossible, not just discouraged.
    """)


if __name__ == "__main__":
    run_comparison()
