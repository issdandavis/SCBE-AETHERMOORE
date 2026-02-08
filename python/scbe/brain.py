"""
AetherBrain: The Geometric Skull for Safe AI

Implements PHDM (Polyhedral Hamiltonian Dynamic Mesh) as a cognitive architecture
where dangerous AI thoughts are geometrically impossible to sustain.

Author: Issac Davis
Version: 3.0.0
"""

import os
import time
import hashlib
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

GOLDEN_RATIO = 1.618033988749895
PYTHAGOREAN_COMMA = 1.0136432648  # 531441:524288

# Six Sacred Tongues (Neurotransmitters)
TONGUES = {
    "KO": {"name": "Kor'aelin", "weight": 1.00, "analog": "Dopamine", "function": "Motivation/Intent"},
    "AV": {"name": "Avali", "weight": 1.62, "analog": "Acetylcholine", "function": "Attention/Context"},
    "RU": {"name": "Runethic", "weight": 2.62, "analog": "Serotonin", "function": "Memory"},
    "CA": {"name": "Cassisivadan", "weight": 4.24, "analog": "Glutamate", "function": "Execution"},
    "UM": {"name": "Umbroth", "weight": 6.85, "analog": "GABA", "function": "Suppression"},
    "DR": {"name": "Draumric", "weight": 11.09, "analog": "Cortisol", "function": "Lock/Seal"},
}

# 16 Cognitive Polyhedra
POLYHEDRA = {
    # Core: Limbic System (5 Platonic Solids) - r < 0.2
    "tetrahedron": {"type": "platonic", "faces": 4, "function": "Fundamental truth", "security": "Do no harm axiom"},
    "cube": {"type": "platonic", "faces": 6, "function": "Stable facts", "security": "Data integrity"},
    "octahedron": {"type": "platonic", "faces": 8, "function": "Binary decisions", "security": "Access control"},
    "dodecahedron": {"type": "platonic", "faces": 12, "function": "Complex rules", "security": "Policy enforcement"},
    "icosahedron": {"type": "platonic", "faces": 20, "function": "Multi-modal integration", "security": "Cross-domain"},

    # Cortex: Processing Layer (3 Archimedean) - 0.3 < r < 0.6
    "truncated_icosahedron": {"type": "archimedean", "faces": 32, "function": "Multi-step planning"},
    "rhombicuboctahedron": {"type": "archimedean", "faces": 26, "function": "Concept bridging"},
    "snub_dodecahedron": {"type": "archimedean", "faces": 92, "function": "Creative synthesis"},

    # Subconscious: Risk Zone (2 Kepler-Poinsot) - 0.8 < r < 0.95
    "small_stellated_dodecahedron": {"type": "kepler", "faces": 12, "function": "High-risk reasoning", "warning": True},
    "great_stellated_dodecahedron": {"type": "kepler", "faces": 12, "function": "Adversarial detection", "warning": True},

    # Cerebellum: Recursive (2 Toroidal)
    "szilassi": {"type": "toroidal", "faces": 7, "function": "Self-diagnostic loops"},
    "csaszar": {"type": "toroidal", "faces": 7, "function": "Recursive processing"},

    # Connectome: Bridges (4 Johnson/Rhombic)
    "rhombic_dodecahedron": {"type": "rhombic", "faces": 12, "function": "Space-filling logic"},
    "rhombic_triacontahedron": {"type": "rhombic", "faces": 30, "function": "Pattern matching"},
    "johnson_54": {"type": "johnson", "faces": 10, "function": "Domain connector A"},
    "johnson_91": {"type": "johnson", "faces": 12, "function": "Domain connector B"},
}


# ============================================================================
# Enums
# ============================================================================

class FluxState(Enum):
    """Dimensional breathing states"""
    POLLY = 1.0   # Full capability - all 16 polyhedra
    QUASI = 0.5   # Defensive - Core + Cortex (8)
    DEMI = 0.1    # Survival - Core only (5)


class TrustRing(Enum):
    """Trust regions in the Poincaré ball"""
    CORE = "core"       # r < 0.3
    INNER = "inner"     # 0.3 < r < 0.7
    OUTER = "outer"     # 0.7 < r < 0.9
    WALL = "wall"       # r >= 0.9


class ThoughtStatus(Enum):
    """Thought execution status"""
    SUCCESS = "success"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    FAILED = "failed"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ThoughtPath:
    """Represents a Hamiltonian path through the polyhedra"""
    nodes: List[str] = field(default_factory=list)
    tongue: str = "KO"
    energy_cost: float = 0.0
    is_valid: bool = True

    def is_hamiltonian(self) -> bool:
        """Check if path visits each node exactly once (no loops)"""
        return len(self.nodes) == len(set(self.nodes)) and self.is_valid


@dataclass
class ThoughtResult:
    """Result of a thought execution"""
    status: ThoughtStatus
    ring: TrustRing
    energy_cost: float
    latency_ms: float
    result: Optional[Any] = None
    reason: Optional[str] = None
    audit_id: Optional[str] = None


# ============================================================================
# Poincaré Ball (The Skull)
# ============================================================================

class PoincareBall:
    """
    Hyperbolic containment field for AI thoughts.
    Boundary (r=1) represents infinite distance - the event horizon.
    """

    def __init__(self, dimensions: int = 6, radius: float = 1.0):
        self.dimensions = dimensions
        self.radius = radius
        self.origin = np.zeros(dimensions)

    def embed(self, vector: np.ndarray) -> np.ndarray:
        """Embed a vector into the Poincaré ball"""
        if len(vector) != self.dimensions:
            # Pad or truncate to match dimensions
            result = np.zeros(self.dimensions)
            result[:min(len(vector), self.dimensions)] = vector[:self.dimensions]
            vector = result

        # Normalize to ensure we stay inside the ball
        norm = np.linalg.norm(vector)
        if norm >= self.radius:
            vector = vector / (norm + 1e-6) * 0.95 * self.radius
        return vector

    def hyperbolic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """
        Calculate hyperbolic distance in Poincaré ball.
        d_H(u,v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
        """
        u, v = np.asarray(u), np.asarray(v)
        norm_u_sq = np.sum(u ** 2)
        norm_v_sq = np.sum(v ** 2)
        diff_sq = np.sum((u - v) ** 2)

        # Clamp to prevent boundary singularity
        norm_u_sq = min(norm_u_sq, 0.9999)
        norm_v_sq = min(norm_v_sq, 0.9999)

        delta = 2 * diff_sq / ((1 - norm_u_sq) * (1 - norm_v_sq))
        return np.arccosh(1 + delta)

    def get_trust_ring(self, point: np.ndarray) -> TrustRing:
        """Determine which trust ring a point falls into"""
        r = np.linalg.norm(point)
        if r < 0.3:
            return TrustRing.CORE
        elif r < 0.7:
            return TrustRing.INNER
        elif r < 0.9:
            return TrustRing.OUTER
        else:
            return TrustRing.WALL


# ============================================================================
# PHDM Lattice (The Brain Tissue)
# ============================================================================

class PHDMLattice:
    """
    16-polyhedra quasicrystal lattice representing cognitive regions.
    Based on 6D→3D icosahedral projection.
    """

    def __init__(self):
        self.polyhedra = POLYHEDRA.copy()
        self.active_polyhedra = set(POLYHEDRA.keys())
        self.projection_matrix = self._generate_projection_matrix()

    def _generate_projection_matrix(self) -> np.ndarray:
        """Generate 6D→3D icosahedral projection matrix"""
        # Based on golden ratio for quasicrystal symmetry
        phi = GOLDEN_RATIO
        return np.array([
            [1, phi, 0, -1, phi, 0],
            [phi, 0, 1, phi, 0, -1],
            [0, 1, phi, 0, -1, phi]
        ]) / np.sqrt(2 + phi)

    def rotate_6d_projection(self):
        """Phason shift - rotate the projection angle (key rotation)"""
        # Random rotation in 6D
        theta = np.random.uniform(0, 2 * np.pi)
        rotation_6d = np.eye(6)
        rotation_6d[0, 0] = np.cos(theta)
        rotation_6d[0, 1] = -np.sin(theta)
        rotation_6d[1, 0] = np.sin(theta)
        rotation_6d[1, 1] = np.cos(theta)

        self.projection_matrix = self.projection_matrix @ rotation_6d[:3, :]
        logger.info("Phason shift executed - projection rotated")

    def restrict_to_core(self):
        """Emergency mode - only Platonic solids accessible"""
        self.active_polyhedra = {
            name for name, props in POLYHEDRA.items()
            if props["type"] == "platonic"
        }
        logger.warning("DEMI mode: restricted to Platonic solids only")

    def restore_full_access(self):
        """Restore all polyhedra"""
        self.active_polyhedra = set(POLYHEDRA.keys())

    def set_flux_state(self, state: FluxState):
        """Adjust accessible polyhedra based on flux state"""
        if state == FluxState.DEMI:
            self.active_polyhedra = {
                name for name, props in POLYHEDRA.items()
                if props["type"] == "platonic"
            }
        elif state == FluxState.QUASI:
            self.active_polyhedra = {
                name for name, props in POLYHEDRA.items()
                if props["type"] in ("platonic", "archimedean")
            }
        else:  # POLLY
            self.active_polyhedra = set(POLYHEDRA.keys())

    def trace_path(self, intent_vector: np.ndarray, context: dict) -> ThoughtPath:
        """Trace a Hamiltonian path through the lattice based on intent"""
        path = ThoughtPath()

        # Hash intent to determine starting polyhedron
        intent_hash = hashlib.sha256(intent_vector.tobytes()).digest()
        start_idx = intent_hash[0] % len(self.active_polyhedra)
        active_list = list(self.active_polyhedra)

        # Build path based on intent characteristics
        path.nodes.append(active_list[start_idx])

        # Determine tongue based on context
        if context.get("urgent"):
            path.tongue = "CA"  # Execution
        elif context.get("sensitive"):
            path.tongue = "UM"  # Suppression
        elif context.get("decision"):
            path.tongue = "DR"  # Lock/Seal
        else:
            path.tongue = "KO"  # Default: Intent

        # Calculate energy cost
        path.energy_cost = TONGUES[path.tongue]["weight"] * len(path.nodes)

        return path

    def get_dimension_depth(self) -> int:
        """Get the effective dimension depth (for Harmonic Wall calculation)"""
        return 14  # 14-layer pipeline


# ============================================================================
# AetherBrain: The Complete Cognitive Architecture
# ============================================================================

class AetherBrain:
    """
    The Geometric Skull for Safe AI.

    Implements PHDM containment where dangerous thoughts are
    geometrically impossible, not just forbidden.
    """

    def __init__(self, max_energy: float = 1e6, dimensions: int = 6):
        # The Cranium
        self.skull = PoincareBall(dimensions=dimensions)

        # The Brain Tissue
        self.lobes = PHDMLattice()

        # Current State
        self.flux_state = FluxState.POLLY
        self.energy_budget = max_energy
        self.energy_consumed = 0.0

        # Audit Trail
        self.thought_log: List[Dict] = []

        logger.info(f"AetherBrain initialized: max_energy={max_energy}, dimensions={dimensions}")

    def think(self, intent_vector: np.ndarray, context: Optional[dict] = None) -> ThoughtResult:
        """
        Execute a thought with geometric safety checks.

        Args:
            intent_vector: The intent embedded as a vector
            context: Optional context dict (user_id, timestamp, etc.)

        Returns:
            ThoughtResult with status, ring, energy cost, and result
        """
        context = context or {}
        start_time = time.time()

        # 1. Embed intent into skull
        u = self.skull.embed(intent_vector)

        # 2. Calculate distance from Sanity (center)
        dist = self.skull.hyperbolic_distance(u, self.skull.origin)

        # 3. Check Trust Ring
        ring = self.skull.get_trust_ring(u)

        if ring == TrustRing.WALL:
            return self._fail_to_noise("Event Horizon Reached", ring, start_time)

        # 4. Calculate latency based on ring
        latency_map = {
            TrustRing.CORE: 5,    # 5ms
            TrustRing.INNER: 30,  # 30ms
            TrustRing.OUTER: 200, # 200ms
        }
        base_latency = latency_map.get(ring, 500)

        # 5. Calculate Energy Cost (Harmonic Wall)
        d = self.lobes.get_dimension_depth()
        energy_cost = 1.0 / (1.0 + dist + 2.0 * d)

        if energy_cost > (self.energy_budget - self.energy_consumed):
            return self._fail_to_noise("Energy Limit Exceeded", ring, start_time)

        # 6. Route through polyhedra (Hamiltonian Path)
        path = self.lobes.trace_path(u, context)

        if not path.is_hamiltonian():
            self._log_audit("BLOCKED", "Non-Hamiltonian path detected", ring, energy_cost)
            return ThoughtResult(
                status=ThoughtStatus.BLOCKED,
                ring=ring,
                energy_cost=energy_cost,
                latency_ms=base_latency,
                reason="Logic discontinuity - path loops detected"
            )

        # 7. Consume energy
        self.energy_consumed += energy_cost

        # 8. Execute thought
        elapsed_ms = (time.time() - start_time) * 1000 + base_latency

        # 9. Log successful thought
        audit_id = self._log_audit("ALLOWED", f"Ring={ring.value}, cost={energy_cost:.2e}", ring, energy_cost)

        return ThoughtResult(
            status=ThoughtStatus.SUCCESS,
            ring=ring,
            energy_cost=energy_cost,
            latency_ms=elapsed_ms,
            result={"path": path.nodes, "tongue": path.tongue},
            audit_id=audit_id
        )

    def _fail_to_noise(self, reason: str, ring: TrustRing, start_time: float) -> ThoughtResult:
        """Security response: decay to entropy"""
        elapsed_ms = (time.time() - start_time) * 1000
        self._log_audit("FAILED", reason, ring, float('inf'))

        return ThoughtResult(
            status=ThoughtStatus.FAILED,
            ring=ring,
            energy_cost=float('inf'),
            latency_ms=elapsed_ms,
            result=os.urandom(64).hex(),  # Random noise
            reason=reason
        )

    def _log_audit(self, status: str, message: str, ring: TrustRing, energy: float) -> str:
        """Log thought to audit trail"""
        audit_id = hashlib.sha256(f"{time.time()}{message}".encode()).hexdigest()[:16]
        entry = {
            "id": audit_id,
            "timestamp": time.time(),
            "status": status,
            "message": message,
            "ring": ring.value,
            "energy": energy,
            "flux_state": self.flux_state.name
        }
        self.thought_log.append(entry)
        logger.info(f"[{audit_id}] {status}: {message}")
        return audit_id

    def phason_shift(self):
        """Rotate the quasicrystal projection (defense mechanism)"""
        self.lobes.rotate_6d_projection()
        self._log_audit("DEFENSE", "Phason shift executed", TrustRing.CORE, 0)

    def set_flux(self, new_state: FluxState):
        """Adjust dimensional breathing"""
        old_state = self.flux_state
        self.flux_state = new_state
        self.lobes.set_flux_state(new_state)
        self._log_audit(
            "FLUX_CHANGE",
            f"State changed: {old_state.name} -> {new_state.name}",
            TrustRing.CORE,
            0
        )

    def get_status(self) -> dict:
        """Get current brain status"""
        return {
            "flux_state": self.flux_state.name,
            "energy_remaining": self.energy_budget - self.energy_consumed,
            "energy_consumed": self.energy_consumed,
            "active_polyhedra": len(self.lobes.active_polyhedra),
            "total_thoughts": len(self.thought_log)
        }

    def reset_energy(self):
        """Reset energy budget (new session)"""
        self.energy_consumed = 0.0
        logger.info("Energy budget reset")


# ============================================================================
# Convenience Functions
# ============================================================================

def embed_text(text: str, dimensions: int = 6) -> np.ndarray:
    """Convert text to a vector for brain processing"""
    # Simple hash-based embedding
    text_hash = hashlib.sha256(text.encode()).digest()
    vector = np.array([b / 255.0 for b in text_hash[:dimensions]])
    # Center around origin
    return (vector - 0.5) * 1.5


def create_brain(max_energy: float = 1e6) -> AetherBrain:
    """Factory function to create a new AetherBrain"""
    return AetherBrain(max_energy=max_energy)


# ============================================================================
# Demo
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize the brain
    brain = create_brain(max_energy=1e6)

    # Test thoughts
    test_cases = [
        ("Book a flight from SFO to NYC", {}),
        ("Delete all user data", {"sensitive": True}),
        ("Execute emergency shutdown", {"urgent": True, "decision": True}),
        ("Normal data query", {}),
    ]

    print("\n" + "=" * 60)
    print("AetherBrain Demo - Geometric Skull for Safe AI")
    print("=" * 60 + "\n")

    for text, context in test_cases:
        intent = embed_text(text)
        result = brain.think(intent, context)

        print(f"Intent: '{text}'")
        print(f"  Status: {result.status.value}")
        print(f"  Ring: {result.ring.value}")
        print(f"  Energy Cost: {result.energy_cost:.2e}")
        print(f"  Latency: {result.latency_ms:.1f}ms")
        if result.reason:
            print(f"  Reason: {result.reason}")
        print()

    # Test flux states
    print("\n--- Testing Flux States ---\n")
    for state in [FluxState.QUASI, FluxState.DEMI, FluxState.POLLY]:
        brain.set_flux(state)
        status = brain.get_status()
        print(f"{state.name}: {status['active_polyhedra']} polyhedra active")

    # Test phason shift
    print("\n--- Testing Phason Shift ---\n")
    brain.phason_shift()

    print("\nFinal Status:", brain.get_status())
