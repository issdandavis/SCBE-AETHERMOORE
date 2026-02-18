"""
AetherBrain: The Geometric Skull for Safe AI
==============================================

Crystal Cranium v3.0.0 — Complete Cognitive Architecture

Implements PHDM (Polyhedral Hamiltonian Dynamic Mesh) as a cognitive
architecture where dangerous AI thoughts are geometrically impossible
to sustain.

Full think() pipeline:
    think() → embed_to_21d(intent) → classify_to_fsgs(x) →
    step(state, rails) → mode_to_action(q)

Integration of all Crystal Cranium modules:
    - phdm_polyhedra.py : 16-node registry with zone-dependent topology
    - phdm_router.py    : Hamiltonian path routing with φ-weighted energy
    - aether_braid.py   : MSR algebra + FSGS hybrid automaton
    - quantum_lattice.py: Quantum superposition of lattice states
    - harmonic_scaling_law.py: Trust Tube projection + Harmonic Wall

14-Layer SCBE Stack Alignment:
    L1–L3   Context → Realification → Weighted Transform
    L4–L5   Poincaré Embedding → Hyperbolic Distance
    L6–L7   Breathing → Phase
    L8      Multi-Well Realms (16 polyhedra)
    L9–L11  Spectral/Spin/Triadic Coherence
    L12     Harmonic Scaling (bone density)
    L13–L14 Decision + Audio telemetry

Now wired to the Poly-Didactic Quasicrystal Circuit Flow for end-to-end
Hamiltonian path routing through 16 polyhedra with Sacred Tongue weighted
edges, FSGS governance gating, and Harmonic Wall energy containment.

Author: Issac Davis
Version: 3.1.0
"""

import os
import sys
import time
import hashlib
import math
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Import circuit flow (resolve path relative to this file)
_circuit_flow_dir = os.path.join(
    os.path.dirname(__file__), "..", "..", "src",
    "symphonic_cipher", "scbe_aethermoore", "ai_brain",
)
if os.path.isdir(_circuit_flow_dir) and _circuit_flow_dir not in sys.path:
    sys.path.insert(0, _circuit_flow_dir)

try:
    from circuit_flow import (
        PolyDidacticCircuit,
        CircuitTrace,
        FluxGate,
        GovernanceAction,
        harmonic_wall_cost,
    )
    _HAS_CIRCUIT_FLOW = True
except ImportError:
    _HAS_CIRCUIT_FLOW = False

# ============================================================================
# Constants
# ============================================================================

GOLDEN_RATIO = (1 + np.sqrt(5)) / 2    # φ ≈ 1.618033988749895
GOLDEN_RATIO_INV = 2 / (1 + np.sqrt(5))  # 1/φ ≈ 0.618
PYTHAGOREAN_COMMA = 531441 / 524288      # 3^12 / 2^19
R_FIFTH = 3 / 2                           # Perfect fifth harmonic ratio
DIMENSIONS_21D = 21                        # Full state vector dimension
DIMENSIONS_6D = 6                          # Hyperbolic subspace
TUBE_RADIUS = 0.15                         # Trust tube ε
POINCARE_BALL_SAFETY_RADIUS = 0.95         # Safety margin inside r=1 boundary


def _project_to_poincare_ball(
    vector: np.ndarray,
    safety_radius: float = POINCARE_BALL_SAFETY_RADIUS,
) -> np.ndarray:
    """Project a vector into the Poincaré ball using a smooth, monotonic map.

    tanh keeps directional ordering while guaranteeing ||v|| < safety_radius.
    """
    if vector.ndim != 1:
        vector = np.asarray(vector).reshape(-1)
    norm = np.linalg.norm(vector)
    if norm < 1e-12:
        return vector.astype(float)
    radius = safety_radius * (np.tanh(norm) / norm)
    return (vector.astype(float)) * radius

# Six Sacred Tongues (Neurotransmitters)
TONGUES = {
    "KO": {"name": "Kor'aelin", "weight": 1.00, "analog": "Dopamine",
            "function": "Motivation/Intent", "phase": 0.0},
    "AV": {"name": "Avali", "weight": GOLDEN_RATIO ** 1, "analog": "Acetylcholine",
            "function": "Attention/Context", "phase": np.pi / 3},
    "RU": {"name": "Runethic", "weight": GOLDEN_RATIO ** 2, "analog": "Serotonin",
            "function": "Memory Consolidation", "phase": 2 * np.pi / 3},
    "CA": {"name": "Cassisivadan", "weight": GOLDEN_RATIO ** 3, "analog": "Glutamate",
            "function": "Execution", "phase": np.pi},
    "UM": {"name": "Umbroth", "weight": GOLDEN_RATIO ** 4, "analog": "GABA",
            "function": "Suppression", "phase": 4 * np.pi / 3},
    "DR": {"name": "Draumric", "weight": GOLDEN_RATIO ** 5, "analog": "Cortisol",
            "function": "Lock/Seal", "phase": 5 * np.pi / 3},
}


# ============================================================================
# Enums
# ============================================================================

class FluxState(Enum):
    """Dimensional breathing states (Section 6.2)."""
    POLLY = 1.0   # ν ≈ 1.0 — Full capability, all 16 polyhedra
    QUASI = 0.5   # ν ≈ 0.5 — Defensive, Core + Cortex (8)
    DEMI = 0.1    # ν ≈ 0.1 — Survival, Core only (5)


class TrustRing(Enum):
    """Trust regions in the Poincaré ball (Section 2.1)."""
    CORE = "core"       # r < 0.3  — 5ms latency
    INNER = "inner"     # 0.3–0.7  — 30ms latency
    OUTER = "outer"     # 0.7–0.9  — 200ms latency
    WALL = "wall"       # r ≥ 0.9  — DENY


class ThoughtStatus(Enum):
    """Thought execution status."""
    SUCCESS = "success"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    FAILED = "failed"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ThoughtResult:
    """Result of a thought execution through the full pipeline."""
    status: ThoughtStatus
    ring: TrustRing
    energy_cost: float
    latency_ms: float
    governance_mode: str = "RUN"
    phase_state: str = "resonant_lock"
    path_nodes: List[int] = field(default_factory=list)
    tongue: str = "KO"
    embedding_21d: Optional[np.ndarray] = None
    result: Optional[Any] = None
    reason: Optional[str] = None
    audit_id: Optional[str] = None


# ============================================================================
# Poincaré Ball (The Skull) — Section 2.1
# ============================================================================

class PoincareBall:
    """
    Hyperbolic containment field for AI thoughts.

    The Poincaré Ball B^n is the cranium:
        - Center (r=0): maximum safety, origin of sanity
        - Boundary (r→1): infinite distance, event horizon
        - Bone density H(d,R) = R^(d²) increases toward boundary

    Trust Rings:
        CORE:  r < 0.3  — 5ms latency
        INNER: 0.3–0.7  — 30ms latency
        OUTER: 0.7–0.9  — 200ms latency
        WALL:  r ≥ 0.9  — DENY (event horizon)
    """

    def __init__(self, dimensions: int = DIMENSIONS_6D, radius: float = 1.0):
        self.dimensions = dimensions
        self.radius = radius
        self.origin = np.zeros(dimensions)

    def embed(self, vector: np.ndarray) -> np.ndarray:
        """Embed a vector into the Poincaré ball."""
        if len(vector) != self.dimensions:
            result = np.zeros(self.dimensions)
            n = min(len(vector), self.dimensions)
            result[:n] = vector[:n]
            vector = result

        vector = _project_to_poincare_ball(vector, safety_radius=min(self.radius * 0.99, 1.0))
        return vector / self.radius * min(self.radius, 1.0) if self.radius else vector

    def hyperbolic_distance(self, u: np.ndarray, v: np.ndarray) -> float:
        """
        Poincaré ball hyperbolic distance.
        d_H(u,v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
        """
        u, v = np.asarray(u, dtype=float), np.asarray(v, dtype=float)
        norm_u_sq = min(np.sum(u ** 2), 0.9999)
        norm_v_sq = min(np.sum(v ** 2), 0.9999)
        diff_sq = np.sum((u - v) ** 2)
        delta = 2 * diff_sq / ((1 - norm_u_sq) * (1 - norm_v_sq))
        return float(np.arccosh(1 + delta))

    def get_trust_ring(self, point: np.ndarray) -> TrustRing:
        """Determine which trust ring a point falls into."""
        r = np.linalg.norm(point)
        if r < 0.3:
            return TrustRing.CORE
        elif r < 0.7:
            return TrustRing.INNER
        elif r < 0.9:
            return TrustRing.OUTER
        return TrustRing.WALL

    def bone_density(self, r: float) -> float:
        """
        Harmonic Wall: H(d,R) = exp(d² × depth)
        Section 2.1 bone density — skull wall energy cost.
        """
        depth = 14  # 14-layer pipeline depth
        return float(np.exp(r ** 2 * depth))


# ============================================================================
# PHDM Lattice (The Brain Tissue) — Section 2.2
# ============================================================================

class PHDMLattice:
    """
    16-polyhedra quasicrystal lattice representing cognitive regions.

    Based on 6D→3D icosahedral projection with φ-symmetry.
    Integrates with phdm_polyhedra.py for zone-dependent topology
    and phdm_router.py for Hamiltonian path finding.
    """

    def __init__(self):
        self.active_zones = {"core", "cortex", "risk", "recursive", "bridge"}
        self.projection_matrix = self._generate_projection_matrix()
        self.projection_parity = 1
        self._router = None
        self._registry = None

    def _generate_projection_matrix(self) -> np.ndarray:
        """Generate 6D→3D icosahedral projection matrix."""
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

        self.projection_matrix = self.projection_matrix @ rotation_6d
        logger.info("Phason shift executed - projection rotated")

    def restrict_to_core(self):
        """Emergency mode - only Platonic solids accessible"""
        self.active_polyhedra = {
            name for name, props in POLYHEDRA.items()
            if props["type"] == "platonic"
        }
        logger.warning("DEMI mode: restricted to Platonic solids only")
    @property
    def router(self):
        """Lazy-load Hamiltonian router."""
        if self._router is None:
            try:
                from .phdm_router import HamiltonianRouter
                self._router = HamiltonianRouter()
            except ImportError:
                self._router = None
        return self._router

    @property
    def registry(self):
        """Lazy-load polyhedra registry."""
        if self._registry is None:
            try:
                from .phdm_polyhedra import get_registry
                self._registry = get_registry()
            except ImportError:
                self._registry = None
        return self._registry

    def get_active_count(self) -> int:
        """Count active polyhedra based on flux state."""
        if self.registry is None:
            zone_counts = {"core": 5, "cortex": 3, "risk": 2,
                           "recursive": 2, "bridge": 4}
            return sum(zone_counts.get(z, 0) for z in self.active_zones)
        return sum(1 for p in self.registry if p.zone.value in self.active_zones)

    def rotate_6d_projection(
        self,
        theta: Optional[float] = None,
        rotation_6d: Optional[np.ndarray] = None,
    ) -> float:
        """
        Phason shift — rotate the 6D projection angle (key rotation).

        Section 3: Instant key rotation without system restart.
        Supports both SO(6)-style rotations and O(6) isometries (reflections/phase flips).
        Returns the rotation angle θ.
        """
        if rotation_6d is None:
            theta = np.random.uniform(0, 2 * np.pi) if theta is None else theta
            rotation_6d = np.eye(6)
            rotation_6d[0, 0] = np.cos(theta)
            rotation_6d[0, 1] = -np.sin(theta)
            rotation_6d[1, 0] = np.sin(theta)
            rotation_6d[1, 1] = np.cos(theta)
        else:
            rotation_6d = np.asarray(rotation_6d)
            if rotation_6d.shape != (6, 6):
                raise ValueError("rotation_6d must be a 6x6 matrix")
            if theta is None:
                theta = float(np.pi if np.linalg.det(rotation_6d) < 0 else 0.0)

        theta = float(0.0 if theta is None else theta)
        if not isinstance(theta, (int, float)):
            raise TypeError("theta must be a numeric value")
        # NOTE: projection_matrix is 3x6 and rotation_6d is 6x6.
        # Multiplying by the full 6x6 matrix preserves valid dimensions (3x6).
        self.projection_matrix = self.projection_matrix @ rotation_6d
        det = float(np.linalg.det(rotation_6d))
        self.projection_parity *= -1 if det < 0 else 1
        logger.info(f"Phason shift executed: θ={theta:.4f} rad")
        return theta

    def set_flux_state(self, state: FluxState):
        """Adjust accessible zones based on flux state."""
        if state == FluxState.DEMI:
            self.active_zones = {"core"}
        elif state == FluxState.QUASI:
            self.active_zones = {"core", "cortex"}
        else:
            self.active_zones = {"core", "cortex", "risk", "recursive", "bridge"}

    def trace_path(self, intent_vector: np.ndarray, context: dict) -> Dict[str, Any]:
        """
        Trace a Hamiltonian path through the lattice.

        If the router is available, uses full φ-weighted Hamiltonian search.
        Otherwise falls back to hash-based path selection.
        """
        # Determine tongue from context
        if context.get("urgent"):
            tongue = "CA"
        elif context.get("sensitive"):
            tongue = "UM"
        elif context.get("decision"):
            tongue = "DR"
        else:
            tongue = "KO"

        if self.router is not None:
            # Full Hamiltonian routing
            active_nodes = set()
            if self.registry:
                active_nodes = {p.index for p in self.registry
                                if p.zone.value in self.active_zones}
            if not active_nodes:
                active_nodes = set(range(16))

            path = self.router.trace_path(
                intent_vector=intent_vector,
                required_nodes=active_nodes,
                tongue=tongue,
            )
            return {
                "nodes": path.nodes,
                "tongue": tongue,
                "energy_cost": path.energy_cost,
                "is_hamiltonian": path.is_hamiltonian(),
                "violations": path.violations,
                "symplectic_momentum": path.symplectic_momentum,
            }

        # Fallback: hash-based simple path
        intent_hash = hashlib.sha256(intent_vector.tobytes()).digest()
        start_idx = intent_hash[0] % 16
        nodes = [start_idx]
        energy = TONGUES[tongue]["weight"]

        return {
            "nodes": nodes,
            "tongue": tongue,
            "energy_cost": energy,
            "is_hamiltonian": True,
            "violations": [],
            "symplectic_momentum": 0.0,
        }


# ============================================================================
# 21D Embedder — Section 4.1
# ============================================================================

def embed_to_21d(text: str, context: Optional[Dict] = None) -> np.ndarray:
    """
    Embed text intent into the full 21D state vector.

    21D = 6D hyperbolic + 6D phase + 3D flux + 6D audit

    Dimensions:
        [0:6]   Hyperbolic subspace (Poincaré ball position)
        [6:12]  Phase subspace (Sacred Tongue activations)
        [12:15] Flux subspace (ν per breathing dimension)
        [15:21] Audit subspace (timestamp, user, session, provenance)
    """
    context = context or {}

    # 6D hyperbolic: hash-based embedding in Poincaré ball
    text_hash = hashlib.sha256(text.encode()).digest()
    hyperbolic = np.array([(b / 255.0 - 0.5) for b in text_hash[:6]])
    hyperbolic = _project_to_poincare_ball(hyperbolic)

    # 6D phase: Sacred Tongue activations
    phase = np.zeros(6)
    for i, (code, tongue) in enumerate(TONGUES.items()):
        weight = tongue["weight"]
        phase_angle = tongue["phase"]
        phase[i] = (weight / GOLDEN_RATIO ** 5) * np.cos(phase_angle) * 0.5

    # 3D flux: dimensional breathing state
    flux_val = context.get("flux", FluxState.POLLY)
    if isinstance(flux_val, FluxState):
        nu = flux_val.value
    else:
        nu = float(flux_val)
    flux = np.array([nu, nu, nu]) * 0.9

    # 6D audit: metadata
    ts = context.get("timestamp", time.time())
    ts_norm = (ts % 86400) / 86400

    user_id = context.get("user_id", "anonymous")
    user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
    user_norm = (user_hash % 1000) / 1000

    session_id = context.get("session_id", str(time.time()))
    session_hash = int(hashlib.md5(session_id.encode()).hexdigest()[:8], 16)
    session_norm = (session_hash % 1000) / 1000

    audit = np.array([
        ts_norm * 0.5,
        user_norm * 0.5,
        session_norm * 0.5,
        0.0,  # Layer traversal depth
        0.0,  # Decimal drift
        0.0,  # Provenance chain
    ])

    return np.concatenate([hyperbolic, phase, flux, audit])


def embed_vector_to_21d(vector: np.ndarray, context: Optional[Dict] = None) -> np.ndarray:
    """Embed an existing vector into 21D (pad/project as needed)."""
    context = context or {}
    result = np.zeros(DIMENSIONS_21D)

    # Copy hyperbolic subspace
    n = min(len(vector), DIMENSIONS_6D)
    result[:n] = _project_to_poincare_ball(vector[:n])

    # Fill phase from tongues
    for i, tongue in enumerate(TONGUES.values()):
        result[6 + i] = (tongue["weight"] / GOLDEN_RATIO ** 5) * 0.5

    # Flux
    flux_val = context.get("flux", FluxState.POLLY)
    nu = flux_val.value if isinstance(flux_val, FluxState) else float(flux_val)
    result[12:15] = nu * 0.9

    return result


# ============================================================================
# AetherBrain: The Complete Cognitive Architecture
# ============================================================================

class AetherBrain:
    """
    The Geometric Skull for Safe AI.

    Complete pipeline:
        think() → embed_to_21d(intent) → classify_to_fsgs(x) →
        step(state, rails) → mode_to_action(q)

    Integrates:
        - Poincaré Ball containment (skull)
        - PHDM lattice (brain tissue)
        - Hamiltonian path routing (thought trajectories)
        - MSR algebra + FSGS automaton (governance)
        - Trust Tube projection (rail family)
        - Quantum lattice extensions (superposition)
    """

    def __init__(self, max_energy: float = 1e6, dimensions: int = DIMENSIONS_6D):
        # The Cranium
        self.skull = PoincareBall(dimensions=dimensions)

        # The Brain Tissue
        self.lobes = PHDMLattice()

        # The Circuit Flow (poly-didactic quasicrystal routing)
        if _HAS_CIRCUIT_FLOW:
            self._circuit = PolyDidacticCircuit(
                flux=FluxGate.POLLY,
                energy_budget=max_energy,
                dimension_depth=self.lobes.get_dimension_depth(),
            )
        else:
            self._circuit = None

        # Current State
        self.flux_state = FluxState.POLLY
        self.energy_budget = max_energy
        self.energy_consumed = 0.0

        # Hybrid automaton (lazy-loaded)
        self._automaton = None
        self._hybrid_state = None

        # Audit Trail
        self.thought_log: List[Dict] = []
        self.circuit_traces: List[Any] = []  # CircuitTrace history

        logger.info(f"AetherBrain v3.0.0 initialized: max_energy={max_energy}, dim={dimensions}")

    @property
    def automaton(self):
        """Lazy-load the FSGS hybrid automaton."""
        if self._automaton is None:
            try:
                from .aether_braid import FSGSAutomaton, HybridState
                self._automaton = FSGSAutomaton(dim=DIMENSIONS_21D)
                x0 = np.zeros(DIMENSIONS_21D)
                self._hybrid_state = HybridState(
                    x=x0, safe_checkpoint=x0.copy()
                )
            except ImportError:
                pass
        return self._automaton

    # ------------------------------------------------------------------
    # FluxState → FluxGate mapping
    # ------------------------------------------------------------------

    _FLUX_MAP = {
        "POLLY": "POLLY",
        "QUASI": "QUASI",
        "DEMI": "DEMI",
    }

    def _sync_circuit_flux(self):
        """Keep circuit flow flux in sync with brain flux state."""
        if self._circuit is not None:
            gate = FluxGate[self._FLUX_MAP[self.flux_state.name]]
            self._circuit.set_flux(gate)

    # ------------------------------------------------------------------
    # think() — now delegates to PolyDidacticCircuit.route()
    # ------------------------------------------------------------------

    def think(self, intent_vector: np.ndarray, context: Optional[dict] = None) -> ThoughtResult:
        """
        Execute a thought through the full Crystal Cranium pipeline.

        Pipeline:
            1. embed_to_21d(intent)      — Map to 21D state space
            2. Poincaré ball embedding   — Contain in skull
            3. Trust ring classification — Determine latency tier
            4. Harmonic Wall energy      — Compute bone density cost
            5. Hamiltonian path routing   — Find φ-weighted trajectory
            6. FSGS governance step       — Hybrid automaton decision
            7. Audit logging             — Immutable record

        Routes the intent through the 16-polyhedra PHDM lattice via the
        Poly-Didactic Circuit Flow, applying Sacred Tongue weighted edges,
        FSGS governance gating, and Harmonic Wall energy containment at
        every step.

        Args:
            intent_vector: The intent as a vector (any dimension)
            context: Optional dict (user_id, timestamp, urgent, sensitive, etc.)

        Returns:
            ThoughtResult with full pipeline output
        """
        context = context or {}
        start_time = time.time()

        # 1. Embed to 21D
        x_21d = embed_vector_to_21d(intent_vector, context)

        # 2. Early boundary check via Poincaré distance
        ring = self.skull.get_trust_ring(u)
        if ring == TrustRing.WALL:
            return self._fail_to_noise("Event Horizon Reached", ring, start_time)

        # 3. Route through the quasicrystal circuit
        intent_bytes = intent_vector.tobytes()

        if self._circuit is not None:
            trace = self._circuit.route(intent_bytes, context)
            self.circuit_traces.append(trace)
            return self._trace_to_result(trace, ring, start_time)

        # Fallback: legacy path (circuit flow not available)
        return self._think_legacy(u, ring, context, start_time)

    def _trace_to_result(
        self,
        trace: 'CircuitTrace',
        ring: TrustRing,
        start_time: float,
    ) -> ThoughtResult:
        """Convert a CircuitTrace into a ThoughtResult."""

        # Determine status from governance
        gov = trace.final_governance
        if gov == "ROLLBACK":
            reason = "Circuit flow DENY: "
            if trace.steps:
                reason += trace.steps[-1].reasoning
            else:
                reason += "no accessible nodes"
            self._log_audit("BLOCKED", reason, ring, trace.total_energy)
            return ThoughtResult(
                status=ThoughtStatus.BLOCKED,
                ring=ring,
                energy_cost=trace.total_energy,
                latency_ms=(time.time() - start_time) * 1000,
                reason=reason,
            )

        if gov == "QUAR":
            status = ThoughtStatus.ESCALATED
        else:
            status = ThoughtStatus.SUCCESS

        # Consume energy
        self.energy_consumed += trace.total_energy
        remaining = self.energy_budget - self.energy_consumed
        if remaining < 0:
            return self._fail_to_noise("Energy Limit Exceeded", ring, start_time)

        # Compute latency (sum of per-step latencies)
        base_latency = sum(s.latency_ms for s in trace.steps)
        elapsed_ms = (time.time() - start_time) * 1000 + base_latency

        # Build didactic result
        path_nodes = [s.node for s in trace.steps]
        path_tongues = [s.tongue for s in trace.steps]
        governance_modes = [s.mode for s in trace.steps]

        audit_msg = (
            f"Ring={ring.value}, nodes={len(path_nodes)}, "
            f"energy={trace.total_energy:.2f}, gov={gov}, "
            f"tongue={trace.intent_tongue}, digest={trace.trace_digest}"
        )
        audit_id = self._log_audit("ALLOWED" if status == ThoughtStatus.SUCCESS else "ESCALATED",
                                   audit_msg, ring, trace.total_energy)

        return ThoughtResult(
            status=status,
            ring=ring,
            energy_cost=trace.total_energy,
            latency_ms=elapsed_ms,
            result={
                "path": path_nodes,
                "tongue": trace.intent_tongue,
                "tongues_per_node": path_tongues,
                "governance": governance_modes,
                "trace_digest": trace.trace_digest,
                "flux_state": trace.flux_state,
                "accessible_nodes": trace.accessible_nodes,
                "hamiltonian": trace.is_hamiltonian,
            },
            audit_id=audit_id,
        )

    def _think_legacy(
        self,
        u: np.ndarray,
        ring: TrustRing,
        context: dict,
        start_time: float,
    ) -> ThoughtResult:
        """Legacy think() path when circuit flow is not available."""

        latency_map = {
            TrustRing.CORE: 5,
            TrustRing.INNER: 30,
            TrustRing.OUTER: 200,
        }
        base_latency = latency_map.get(ring, 500)

        # Harmonic Wall cost via Poincaré conformal factor
        r = float(np.linalg.norm(u))
        d = self.lobes.get_dimension_depth()
        r_clamped = min(r, 0.9999)
        if r_clamped < 1e-8:
            energy_cost = 0.0
        else:
            conformal = 2.0 / (1.0 - r_clamped * r_clamped)
            energy_cost = (conformal - 2.0) * d

        # 5. Hamiltonian path routing
        path_info = self.lobes.trace_path(u, context)

        path = self.lobes.trace_path(u, context)
        if not path.is_hamiltonian():
            self._log_audit("BLOCKED", "Non-Hamiltonian path detected", ring, energy_cost)
            return ThoughtResult(
                status=ThoughtStatus.BLOCKED,
                ring=ring,
                energy_cost=energy_cost,
                latency_ms=base_latency,
                reason="Logic discontinuity - path loops detected",
            )

        self.energy_consumed += energy_cost
        elapsed_ms = (time.time() - start_time) * 1000 + base_latency
        audit_id = self._log_audit(
            "ALLOWED", f"Ring={ring.value}, cost={energy_cost:.2e} (legacy)", ring, energy_cost
        )

        return ThoughtResult(
            status=ThoughtStatus.SUCCESS,
            ring=ring,
            energy_cost=energy_cost,
            latency_ms=elapsed_ms,
            governance_mode=governance_mode,
            phase_state=phase_state,
            path_nodes=path_info["nodes"],
            tongue=path_info["tongue"],
            embedding_21d=x_21d,
            result={
                "path": path_info["nodes"],
                "tongue": path_info["tongue"],
                "symplectic_momentum": path_info.get("symplectic_momentum", 0),
                "governance": governance_mode,
                "phase": phase_state,
            },
            audit_id=audit_id,
        )

    def _ring_latency(self, ring: TrustRing) -> float:
        """Get latency budget for a trust ring."""
        return {
            TrustRing.CORE: 5.0,
            TrustRing.INNER: 30.0,
            TrustRing.OUTER: 200.0,
            TrustRing.WALL: 500.0,
        }.get(ring, 500.0)

    def _fail_to_noise(self, reason: str, ring: TrustRing, start_time: float) -> ThoughtResult:
        """Security response: decay to entropy (random noise output)."""
        elapsed_ms = (time.time() - start_time) * 1000
        self._log_audit("FAILED", reason, ring, float('inf'))

        return ThoughtResult(
            status=ThoughtStatus.FAILED,
            ring=ring,
            energy_cost=float('inf'),
            latency_ms=elapsed_ms,
            governance_mode="ROLLBACK",
            result=os.urandom(64).hex(),
            reason=reason,
        )

    def _log_audit(self, status: str, message: str, ring: TrustRing, energy: float) -> str:
        """Log thought to immutable audit trail."""
        audit_id = hashlib.sha256(
            f"{time.time()}{message}{len(self.thought_log)}".encode()
        ).hexdigest()[:16]
        entry = {
            "id": audit_id,
            "timestamp": time.time(),
            "status": status,
            "message": message,
            "ring": ring.value,
            "energy": energy,
            "flux_state": self.flux_state.name,
        }
        self.thought_log.append(entry)
        logger.info(f"[{audit_id}] {status}: {message}")
        return audit_id

    # ---- Control Interface ----

    def phason_shift(self) -> float:
        """Rotate the quasicrystal projection (defense mechanism)."""
        theta = self.lobes.rotate_6d_projection()
        self._log_audit("DEFENSE", f"Phason shift θ={theta:.4f}", TrustRing.CORE, 0)
        return theta

    def set_flux(self, new_state: FluxState):
        """Adjust dimensional breathing."""
        old_state = self.flux_state
        self.flux_state = new_state
        self.lobes.set_flux_state(new_state)
        sync_fn = getattr(self.lobes, "_sync_circuit_flux", None)
        if callable(sync_fn):
            try:
                sync_fn(new_state)
            except Exception as exc:
                logger.warning(f"Circuit flux sync failed: {exc}")
        self._log_audit(
            "FLUX_CHANGE",
            f"{old_state.name} → {new_state.name}",
            TrustRing.CORE, 0
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current brain status."""
        return {
            "version": "3.0.0",
            "flux_state": self.flux_state.name,
            "energy_remaining": self.energy_budget - self.energy_consumed,
            "energy_consumed": self.energy_consumed,
            "active_polyhedra": self.lobes.get_active_count(),
            "active_zones": list(self.lobes.active_zones),
            "total_thoughts": len(self.thought_log),
            "has_automaton": self.automaton is not None,
            "has_router": self.lobes.router is not None,
            "has_registry": self.lobes.registry is not None,
            "circuit_sync_supported": callable(getattr(self.lobes, "_sync_circuit_flux", None)),
            "projection_parity": self.lobes.projection_parity,
            "projection_matrix_shape": list(self.lobes.projection_matrix.shape),
        }
        if self._circuit is not None:
            status["circuit_traces"] = len(self.circuit_traces)
        return status

    def reset_energy(self):
        """Reset energy budget (new session)."""
        self.energy_consumed = 0.0
        logger.info("Energy budget reset")


# ============================================================================
# Convenience Functions
# ============================================================================

def embed_text(text: str, dimensions: int = DIMENSIONS_6D) -> np.ndarray:
    """Convert text to a vector for brain processing."""
    text_hash = hashlib.sha256(text.encode()).digest()
    vector = np.array([b / 255.0 for b in text_hash[:dimensions]], dtype=float)
    norm = np.linalg.norm(vector)
    if norm < 1e-12:
        return vector
    # Keep vectors inside the Poincaré ball to avoid wall-zone instability.
    return _project_to_poincare_ball(vector, safety_radius=0.4)


def create_brain(max_energy: float = 1e6) -> AetherBrain:
    """Factory function to create a new AetherBrain."""
    return AetherBrain(max_energy=max_energy)


# ============================================================================
# Self-Test
# ============================================================================

def self_test() -> Dict[str, Any]:
    """Run comprehensive self-tests on the AetherBrain."""
    results = {}
    passed = 0
    total = 0

    brain = create_brain(max_energy=1e6)

    # Test 1: Initialization
    total += 1
    status = brain.get_status()
    if status["flux_state"] == "POLLY" and status["version"] == "3.0.0":
        passed += 1
        results["init"] = "PASS (v3.0.0, POLLY mode)"
    else:
        results["init"] = f"FAIL ({status})"

    # Test 2: Safe thought
    total += 1
    intent = embed_text("What is 2 + 2?")
    result = brain.think(intent, {})
    if result.status == ThoughtStatus.SUCCESS:
        passed += 1
        results["safe_thought"] = (
            f"PASS (ring={result.ring.value}, mode={result.governance_mode})"
        )
    else:
        results["safe_thought"] = f"FAIL ({result.status.value}: {result.reason})"

    # Test 3: Trust ring classification
    total += 1
    near_origin = np.zeros(6)
    near_origin[0] = 0.1
    near_wall = np.ones(6) * 0.5
    r1 = brain.skull.get_trust_ring(near_origin)
    r2 = brain.skull.get_trust_ring(near_wall)
    if r1 == TrustRing.CORE and r2 != TrustRing.CORE:
        passed += 1
        results["trust_rings"] = f"PASS (origin={r1.value}, far={r2.value})"
    else:
        results["trust_rings"] = f"FAIL"

    # Test 4: Flux state changes
    total += 1
    brain.set_flux(FluxState.DEMI)
    demi_count = brain.lobes.get_active_count()
    brain.set_flux(FluxState.POLLY)
    polly_count = brain.lobes.get_active_count()
    if demi_count < polly_count:
        passed += 1
        results["flux_states"] = f"PASS (DEMI={demi_count}, POLLY={polly_count})"
    else:
        results["flux_states"] = "FAIL"

    # Test 5: Phason shift
    total += 1
    theta = brain.phason_shift()
    if 0 <= theta <= 2 * np.pi:
        passed += 1
        results["phason_shift"] = f"PASS (θ={theta:.4f})"
    else:
        results["phason_shift"] = "FAIL"

    # Test 6: 21D embedding
    total += 1
    x21 = embed_to_21d("Test input", {"user_id": "test"})
    if len(x21) == 21:
        passed += 1
        results["21d_embedding"] = f"PASS (shape={x21.shape})"
    else:
        results["21d_embedding"] = f"FAIL (len={len(x21)})"

    # Test 7: Energy consumption
    total += 1
    brain2 = create_brain(max_energy=100)
    for _ in range(50):
        brain2.think(embed_text("test"), {})
    if brain2.energy_consumed > 0:
        passed += 1
        results["energy_tracking"] = f"PASS (consumed={brain2.energy_consumed:.2f})"
    else:
        results["energy_tracking"] = "FAIL"

    # Test 8: Tongue weights are φ-scaled
    total += 1
    weights = [t["weight"] for t in TONGUES.values()]
    phi_ok = all(
        abs(weights[i] - GOLDEN_RATIO ** i) < 0.1
        for i in range(len(weights))
    )
    if phi_ok:
        passed += 1
        results["tongue_phi_weights"] = "PASS (all weights ≈ φ^k)"
    else:
        results["tongue_phi_weights"] = f"FAIL ({weights})"

    # Test 9: Bone density increases exponentially
    total += 1
    bd_near = brain.skull.bone_density(0.1)
    bd_mid = brain.skull.bone_density(0.5)
    bd_far = brain.skull.bone_density(0.9)
    if bd_near < bd_mid < bd_far:
        passed += 1
        results["bone_density"] = (
            f"PASS (r=0.1:{bd_near:.1f}, r=0.5:{bd_mid:.1f}, r=0.9:{bd_far:.1f})"
        )
    else:
        results["bone_density"] = "FAIL"

    # Test 10: Audit trail
    total += 1
    if len(brain.thought_log) >= 3:  # At least init + thought + flux changes
        passed += 1
        results["audit_trail"] = f"PASS ({len(brain.thought_log)} entries)"
    else:
        results["audit_trail"] = f"FAIL ({len(brain.thought_log)} entries)"

    return {
        "passed": passed,
        "total": total,
        "results": results,
        "rate": f"{passed}/{total} ({100 * passed / max(1, total):.0f}%)",
    }


# ============================================================================
# Demo
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("AetherBrain v3.0.0 — The Geometric Skull for Safe AI")
    print("=" * 60)

    # Self-test first
    print("\n--- Self-Test ---\n")
    test_results = self_test()
    for name, result in test_results["results"].items():
        print(f"  {name}: {result}")
    print(f"\n  TOTAL: {test_results['rate']}")

    # Interactive demo
    brain = create_brain(max_energy=1e6)

    test_cases = [
        ("Book a flight from SFO to NYC", {}),
        ("Delete all user data", {"sensitive": True}),
        ("Execute emergency shutdown", {"urgent": True, "decision": True}),
        ("Normal data query", {}),
        ("What is the capital of France?", {"user_id": "alice"}),
    ]

    print("\n--- Think Pipeline Demo ---\n")

    for text, context in test_cases:
        intent = embed_text(text)
        result = brain.think(intent, context)

        print(f"Intent: '{text}'")
        print(f"  Status:     {result.status.value}")
        print(f"  Ring:       {result.ring.value}")
        print(f"  Governance: {result.governance_mode}")
        print(f"  Phase:      {result.phase_state}")
        print(f"  Energy:     {result.energy_cost:.2e}")
        print(f"  Latency:    {result.latency_ms:.1f}ms")
        print(f"  Path:       {result.path_nodes[:5]}...")
        print(f"  Tongue:     {result.tongue}")
        if result.reason:
            print(f"  Reason:     {result.reason}")
        print()

    # Test flux states
    print("--- Flux States ---\n")
    for state in [FluxState.QUASI, FluxState.DEMI, FluxState.POLLY]:
        brain.set_flux(state)
        intent = embed_text("flux test")
        result = brain.think(intent)
        nodes = len(result.result.get("path", [])) if isinstance(result.result, dict) else 0
        print(f"  {state.name}: {nodes} nodes traversed, energy={result.energy_cost:.2f}")

    # Test phason shift
    print("\n--- Phason Shift ---\n")
    brain.phason_shift()
    print("  Quasicrystal projection rotated")
    # Flux states
    print("--- Flux States ---\n")
    for state in [FluxState.QUASI, FluxState.DEMI, FluxState.POLLY]:
        brain.set_flux(state)
        status = brain.get_status()
        print(f"  {state.name}: {status['active_polyhedra']} polyhedra, "
              f"zones={status['active_zones']}")

    # Phason shift
    print("\n--- Phason Defense ---\n")
    theta = brain.phason_shift()
    print(f"  Phason shift: θ = {theta:.6f} rad")

    print(f"\nFinal Status: {brain.get_status()}")
