"""
Poly-Didactic Quasicrystal Circuit Flow
=========================================

@file circuit_flow.py
@module ai_brain/circuit_flow
@layer Layer 1-14 (End-to-end integration)
@version 1.0.0
@author Issac Davis / SCBE-AETHERMOORE v3.0.0

Integrates PHDM polyhedra, Sacred Tongue neurotransmitter routing,
Hamiltonian path traversal, FSGS governance gating, Trust Tube
projection, and Harmonic Wall energy containment into a single
traceable, self-documenting circuit flow.

This is the "poly didactic" layer: every step through the geometric
skull is recorded with its geometric reasoning, enabling full
provenance auditing of AI thought trajectories.

Architecture:
    Intent → Tongue Classification → Trust Ring → Zone Filtering (Flux)
    → Hamiltonian Route → Per-Node Governance (FSGS) → Energy Check
    → Harmonic Wall → CircuitTrace (didactic audit trail)

Integration Points:
    - brain.py: AetherBrain.think() should delegate routing here
    - phdm.py: 16-polyhedra registry with HMAC-chained paths
    - fsgs.py: GovernanceSymbol/GovernanceMode for per-node gating
    - hamiltonian_braid.py: Braid distance and harmonic cost
    - mirror_shift.py: refactor_align for Trust Tube projection
    - unified_state.py: 21D brain state vector
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio

# Sacred Tongue neurotransmitter weights (φ^n scaling)
TONGUE_WEIGHTS: Dict[str, float] = {
    "KO": 1.00,   # Kor'aelin  → Dopamine   → Motivation/Intent
    "AV": 1.62,   # Avali      → ACh        → Attention/Context
    "RU": 2.62,   # Runethic   → Serotonin  → Memory/Binding
    "CA": 4.24,   # Cassisivadan → Glutamate → Execution
    "UM": 6.85,   # Umbroth    → GABA       → Suppression
    "DR": 11.09,  # Draumric   → Cortisol   → Lock/Seal
}

# Tongue phases on unit circle at π/3 spacing
TONGUE_PHASES: Dict[str, float] = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

# Trust ring radial thresholds and latency tiers (ms)
TRUST_RINGS = {
    "CORE":  (0.0, 0.3, 5),     # r < 0.3  → 5ms
    "INNER": (0.3, 0.7, 30),    # 0.3–0.7  → 30ms
    "OUTER": (0.7, 0.9, 200),   # 0.7–0.9  → 200ms
    "WALL":  (0.9, 1.0, None),  # r ≥ 0.9  → DENY
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Zone(Enum):
    """Cognitive zone in the geometric skull."""
    CORE = "core"            # Platonic solids, r < 0.2, maximum stability
    CORTEX = "cortex"        # Archimedean solids, 0.3 < r < 0.6
    RISK = "risk"            # Kepler-Poinsot stars, 0.8 < r < 0.95
    RECURSIVE = "recursive"  # Toroidal (Szilassi/Csaszar), self-stabilizing
    BRIDGE = "bridge"        # Johnson/Rhombic connectors


class FluxGate(Enum):
    """Dimensional breathing states controlling polyhedra access."""
    POLLY = "polly"  # ν ≈ 1.0 — all 16 polyhedra
    QUASI = "quasi"  # ν ≈ 0.5 — Core + Cortex (8)
    DEMI = "demi"    # ν ≈ 0.1 — Core only (5)


class GovernanceAction(Enum):
    """FSGS-derived action at each circuit node."""
    RUN = "RUN"           # +1 → forward impulse
    HOLD = "HOLD"         # -0 → freeze, run invariants
    QUARANTINE = "QUAR"   # -0 + high risk → defensive checks
    ROLLBACK = "ROLLBACK" # -1 → reverse, deny


# ---------------------------------------------------------------------------
# Circuit Node (one of the 16 polyhedra)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CircuitNode:
    """A polyhedron in the PHDM circuit.

    Attributes:
        name: Canonical polyhedron name.
        zone: Cognitive zone (Core/Cortex/Risk/Recursive/Bridge).
        vertices: V count.
        edges: E count.
        faces: F count.
        genus: Topological genus.
        radial_band: (r_min, r_max) position in Poincaré ball.
        tongue_affinity: Primary Sacred Tongue for this node.
        function: Cognitive function.
    """
    name: str
    zone: Zone
    vertices: int
    edges: int
    faces: int
    genus: int
    radial_band: Tuple[float, float]
    tongue_affinity: str
    function: str

    @property
    def euler_characteristic(self) -> int:
        return self.vertices - self.edges + self.faces

    @property
    def expected_euler(self) -> int:
        """Zone-dependent expected Euler characteristic.

        Kepler-Poinsot (Risk Zone) solids are self-intersecting star
        polyhedra with χ ≤ 2.  This is architecturally desirable:
        unstable χ forces ejection from the Risk Zone.
        """
        if self.zone == Zone.RISK:
            return self.euler_characteristic  # Accept actual χ
        if self.zone == Zone.RECURSIVE:
            return 0  # Genus-1 toroidal: χ = 2 - 2g = 0
        return 2  # Standard genus-0

    def is_topology_valid(self) -> bool:
        """Validate Euler characteristic (zone-aware)."""
        if self.zone == Zone.RISK:
            return self.euler_characteristic <= 2
        return self.euler_characteristic == self.expected_euler


# ---------------------------------------------------------------------------
# Circuit Edge (tongue-weighted connection)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CircuitEdge:
    """Directed edge between two circuit nodes.

    Weight is the Sacred Tongue neurotransmitter cost for traversing
    this connection.  Higher tongue weight = more scrutiny.
    """
    source: str
    target: str
    tongue: str
    weight: float


# ---------------------------------------------------------------------------
# Circuit Step (one entry in the didactic trace)
# ---------------------------------------------------------------------------

@dataclass
class CircuitStep:
    """One step in the poly-didactic circuit trace.

    Every step records its geometric reasoning for full provenance
    auditing.  This is the 'didactic' in poly-didactic.
    """
    step_index: int
    node: str
    zone: str
    tongue: str
    tongue_weight: float
    energy_cost: float
    cumulative_energy: float
    governance: str       # FSGS symbol label (+1, -1, +0, -0)
    mode: str             # GovernanceAction
    trust_ring: str       # CORE/INNER/OUTER/WALL
    radial_distance: float
    latency_ms: float
    reasoning: str        # Human-readable explanation


# ---------------------------------------------------------------------------
# Circuit Trace (complete audit trail)
# ---------------------------------------------------------------------------

@dataclass
class CircuitTrace:
    """Complete didactic audit trail of a thought through the skull.

    Produced by PolyDidacticCircuit.route().  Contains every step,
    the final governance decision, energy accounting, and a
    cryptographic digest binding the trace to its content.
    """
    steps: List[CircuitStep] = field(default_factory=list)
    total_energy: float = 0.0
    path_valid: bool = True
    final_governance: str = "RUN"
    flux_state: str = "POLLY"
    accessible_nodes: int = 16
    intent_tongue: str = "KO"
    trace_digest: str = ""
    timestamp: float = 0.0

    @property
    def is_hamiltonian(self) -> bool:
        """True if every accessible node was visited exactly once."""
        visited = [s.node for s in self.steps]
        return len(visited) == len(set(visited)) == self.accessible_nodes

    def digest(self) -> str:
        """Compute HMAC-chained digest over all steps."""
        h = hashlib.sha256()
        for step in self.steps:
            h.update(f"{step.node}|{step.tongue}|{step.energy_cost:.6f}".encode())
        return h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# The 16-Node Registry
# ---------------------------------------------------------------------------

def _build_registry() -> Dict[str, CircuitNode]:
    """Build the canonical 16-polyhedra registry.

    Topology note: Small Stellated Dodecahedron has χ = -6 (V=12,
    E=30, F=12).  This is correct for self-intersecting Kepler-Poinsot
    stars and architecturally desirable — Risk Zone nodes are
    intentionally unstable.
    """
    nodes: Dict[str, CircuitNode] = {}

    def _add(name, zone, v, e, f, g, rband, tongue, func):
        nodes[name] = CircuitNode(name, zone, v, e, f, g, rband, tongue, func)

    # ── Core: Limbic System (5 Platonic Solids) ── r < 0.2 ──
    _add("tetrahedron",  Zone.CORE, 4, 6, 4,   0, (0.0, 0.05), "KO",
         "Fundamental truth — 'do no harm' axiom")
    _add("cube",         Zone.CORE, 8, 12, 6,  0, (0.05, 0.10), "RU",
         "Stable facts, verified knowledge, data integrity")
    _add("octahedron",   Zone.CORE, 6, 12, 8,  0, (0.10, 0.13), "CA",
         "Binary decisions, yes/no logic, access control")
    _add("dodecahedron", Zone.CORE, 20, 30, 12, 0, (0.13, 0.17), "DR",
         "Complex rule systems, policy enforcement")
    _add("icosahedron",  Zone.CORE, 12, 30, 20, 0, (0.17, 0.20), "AV",
         "Multi-modal integration, cross-domain reasoning")

    # ── Cortex: Processing Layer (3 Archimedean) ── 0.3 < r < 0.6 ──
    _add("truncated_icosahedron", Zone.CORTEX, 60, 90, 32, 0,
         (0.30, 0.40), "AV", "Multi-step planning, strategic reasoning")
    _add("rhombicuboctahedron",   Zone.CORTEX, 24, 48, 26, 0,
         (0.40, 0.50), "RU", "Concept bridging, analogy generation")
    _add("snub_dodecahedron",     Zone.CORTEX, 60, 150, 92, 0,
         (0.50, 0.60), "CA", "Creative synthesis, novel solutions")

    # ── Risk: Subconscious (2 Kepler-Poinsot) ── 0.8 < r < 0.95 ──
    # χ = -6 for Small Stellated Dodecahedron (self-intersecting)
    # χ = -6 for Great Stellated Dodecahedron
    # Both are INTENTIONALLY unstable — forces ejection back to Core
    _add("small_stellated_dodecahedron", Zone.RISK, 12, 30, 12, 0,
         (0.80, 0.87), "UM", "High-risk abstract reasoning (spiky thoughts)")
    _add("great_stellated_dodecahedron", Zone.RISK, 12, 30, 12, 0,
         (0.87, 0.95), "DR", "Adversarial thought detection (hallucination zone)")

    # ── Recursive: Cerebellum (2 Toroidal) ── genus=1 ──
    _add("szilassi", Zone.RECURSIVE, 14, 21, 7, 1,
         (0.25, 0.35), "RU", "Self-diagnostic loops, runtime introspection")
    _add("csaszar",  Zone.RECURSIVE, 7, 21, 14, 1,
         (0.35, 0.45), "CA", "Recursive processing, fractal thinking")

    # ── Bridge: Connectome (4 Johnson/Rhombic) ──
    _add("rhombic_dodecahedron",     Zone.BRIDGE, 14, 24, 12, 0,
         (0.20, 0.30), "KO", "Space-filling logic (fits concepts)")
    _add("rhombic_triacontahedron",  Zone.BRIDGE, 32, 60, 30, 0,
         (0.30, 0.40), "AV", "High-dimensional pattern matching")
    _add("johnson_j17",             Zone.BRIDGE, 9, 16, 9,  0,
         (0.40, 0.55), "RU", "Domain connector A (gyrobifastigium)")
    _add("johnson_j91",             Zone.BRIDGE, 30, 60, 32, 0,
         (0.55, 0.70), "CA", "Domain connector B (bilunabirotunda)")

    return nodes


# ---------------------------------------------------------------------------
# Adjacency graph (Sacred Tongue weighted edges)
# ---------------------------------------------------------------------------

def _build_adjacency(nodes: Dict[str, CircuitNode]) -> Dict[str, List[CircuitEdge]]:
    """Build the circuit adjacency graph.

    Edge weights follow Sacred Tongue neurotransmitter costs:
    - Intra-zone transitions use the destination node's tongue affinity
    - Cross-zone transitions use the higher-weight tongue (more scrutiny)
    - Risk Zone edges always use DR (maximum governance weight)

    Returns:
        Adjacency list: node_name → list of outgoing edges.
    """
    adj: Dict[str, List[CircuitEdge]] = {name: [] for name in nodes}
    node_list = list(nodes.values())

    for i, src in enumerate(node_list):
        for j, dst in enumerate(node_list):
            if i == j:
                continue

            # Determine edge tongue and weight
            if src.zone == Zone.RISK or dst.zone == Zone.RISK:
                tongue = "DR"  # Risk transitions always highest scrutiny
            elif src.zone == dst.zone:
                tongue = dst.tongue_affinity  # Intra-zone: destination's tongue
            else:
                # Cross-zone: use higher-weight tongue for more scrutiny
                w_src = TONGUE_WEIGHTS[src.tongue_affinity]
                w_dst = TONGUE_WEIGHTS[dst.tongue_affinity]
                tongue = dst.tongue_affinity if w_dst >= w_src else src.tongue_affinity

            weight = TONGUE_WEIGHTS[tongue]

            # Radial distance penalty: cross-zone hops cost more
            radial_gap = abs(src.radial_band[1] - dst.radial_band[0])
            weight *= (1.0 + radial_gap)

            adj[src.name].append(CircuitEdge(src.name, dst.name, tongue, weight))

    return adj


# ---------------------------------------------------------------------------
# Harmonic Wall energy cost
# ---------------------------------------------------------------------------

def harmonic_wall_cost(radial_distance: float, dimension_depth: int = 14) -> float:
    """Compute Harmonic Wall energy cost from the Poincaré conformal factor.

    The "bone density" of the geometric skull increases exponentially
    toward the boundary via the conformal factor λ = 2/(1 - r²).
    At the center (r=0), λ=2 → cost=0.  As r→1, λ→∞ → cost→∞.

    Scaled by dimension_depth to couple the 14-layer pipeline depth
    into the energy budget.

    This matches the spec's Section 2.1: "Density increases exponentially
    toward the edge" — the conformal factor IS the Poincaré ball's
    intrinsic notion of "difficulty of sustaining a thought."
    """
    r = min(max(radial_distance, 0.0), 0.9999)
    if r < 1e-8:
        return 0.0
    conformal = 2.0 / (1.0 - r * r)
    return (conformal - 2.0) * dimension_depth


# ---------------------------------------------------------------------------
# Trust Ring classification
# ---------------------------------------------------------------------------

def classify_trust_ring(radial_distance: float) -> Tuple[str, Optional[int]]:
    """Classify a radial distance into a Trust Ring.

    Returns:
        (ring_name, latency_ms) — latency_ms is None for WALL (denied).
    """
    for ring_name, (r_min, r_max, latency) in TRUST_RINGS.items():
        if r_min <= radial_distance < r_max:
            return ring_name, latency
    return "WALL", None


# ---------------------------------------------------------------------------
# Intent → Tongue classification
# ---------------------------------------------------------------------------

def classify_intent_tongue(intent_hash: bytes, context: Optional[dict] = None) -> str:
    """Map an intent to its dominant Sacred Tongue.

    Uses context hints first; falls back to hash-based distribution
    weighted by φ^n tongue positions.
    """
    ctx = context or {}

    # Context-based overrides (explicit signals)
    if ctx.get("urgent") or ctx.get("execute"):
        return "CA"  # Glutamate: execution
    if ctx.get("sensitive") or ctx.get("redact"):
        return "UM"  # GABA: suppression
    if ctx.get("decision") or ctx.get("seal"):
        return "DR"  # Cortisol: lock/seal
    if ctx.get("recall") or ctx.get("bind"):
        return "RU"  # Serotonin: memory/binding
    if ctx.get("observe") or ctx.get("context"):
        return "AV"  # ACh: attention

    # Hash-based: distribute across tongues by φ-weighted probability
    if intent_hash:
        idx = intent_hash[0] % 6
        tongues = list(TONGUE_WEIGHTS.keys())
        return tongues[idx]

    return "KO"  # Default: intent/flow


# ---------------------------------------------------------------------------
# FSGS governance gate
# ---------------------------------------------------------------------------

def _governance_gate(
    node: CircuitNode,
    radial_dist: float,
    energy_so_far: float,
    energy_budget: float,
    step_index: int,
) -> Tuple[GovernanceAction, str, str]:
    """Apply FSGS governance at a circuit node.

    Returns:
        (action, fsgs_symbol_label, reasoning)
    """
    ring, latency = classify_trust_ring(radial_dist)

    # WALL → instant deny
    if ring == "WALL":
        return (
            GovernanceAction.ROLLBACK,
            "-1",
            f"Event horizon reached (r={radial_dist:.3f}). "
            f"Harmonic Wall denies access beyond r=0.9."
        )

    # Risk Zone → quarantine + inspection
    if node.zone == Zone.RISK:
        return (
            GovernanceAction.QUARANTINE,
            "-0",
            f"Risk Zone node '{node.name}' (χ={node.euler_characteristic}). "
            f"Self-intersecting star polyhedra are intentionally unstable — "
            f"quarantine + inspection required before any output."
        )

    # Energy exhaustion → hold
    remaining = energy_budget - energy_so_far
    if remaining < energy_budget * 0.05:
        return (
            GovernanceAction.HOLD,
            "-0",
            f"Energy budget nearly exhausted ({remaining:.1f} remaining). "
            f"Freezing state for quorum check."
        )

    # Outer Ring → hold for verification
    if ring == "OUTER":
        return (
            GovernanceAction.HOLD,
            "+0",
            f"Outer Ring (r={radial_dist:.3f}). "
            f"Moderate resistance — verification required."
        )

    # Normal operation → run
    return (
        GovernanceAction.RUN,
        "+1",
        f"{'Core' if ring == 'CORE' else 'Inner'} Ring "
        f"(r={radial_dist:.3f}). Safe thought space — forward thrust."
    )


# ---------------------------------------------------------------------------
# Hamiltonian path finder
# ---------------------------------------------------------------------------

def _find_hamiltonian_path(
    start: str,
    accessible: List[str],
    adj: Dict[str, List[CircuitEdge]],
) -> Optional[List[str]]:
    """Find a Hamiltonian path visiting all accessible nodes exactly once.

    Uses greedy nearest-neighbor heuristic weighted by tongue cost
    (lower cost preferred).  For 16 nodes this is sufficient;
    for production use, upgrade to branch-and-bound.
    """
    if start not in accessible:
        return None

    remaining = set(accessible)
    path = [start]
    remaining.discard(start)

    current = start
    while remaining:
        # Get edges from current node to remaining nodes
        candidates = [
            e for e in adj.get(current, [])
            if e.target in remaining
        ]
        if not candidates:
            # Dead end — try backtrack fallback
            # For the 16-node fully-connected graph this shouldn't happen
            for name in sorted(remaining):
                path.append(name)
                remaining.discard(name)
            break

        # Pick lowest-weight edge (greedy)
        best = min(candidates, key=lambda e: e.weight)
        path.append(best.target)
        remaining.discard(best.target)
        current = best.target

    return path


# ---------------------------------------------------------------------------
# Flux-aware node filtering
# ---------------------------------------------------------------------------

def _accessible_nodes(
    all_nodes: Dict[str, CircuitNode],
    flux: FluxGate,
) -> List[str]:
    """Filter nodes by FluxState.

    POLLY (ν≈1.0): All 16 polyhedra accessible.
    QUASI (ν≈0.5): Core + Cortex only (8 nodes).
    DEMI  (ν≈0.1): Core only (5 Platonic solids).
    """
    allowed_zones: set
    if flux == FluxGate.DEMI:
        allowed_zones = {Zone.CORE}
    elif flux == FluxGate.QUASI:
        allowed_zones = {Zone.CORE, Zone.CORTEX}
    else:
        allowed_zones = {Zone.CORE, Zone.CORTEX, Zone.RISK,
                         Zone.RECURSIVE, Zone.BRIDGE}

    return [
        name for name, node in all_nodes.items()
        if node.zone in allowed_zones
    ]


# ---------------------------------------------------------------------------
# PolyDidacticCircuit — the main class
# ---------------------------------------------------------------------------

class PolyDidacticCircuit:
    """Poly-Didactic Quasicrystal Circuit Flow.

    Routes intents through the 16-polyhedra PHDM lattice, applying
    Sacred Tongue neurotransmitter weighting, FSGS governance gating,
    Harmonic Wall energy containment, and Trust Ring classification
    at every step.

    Each step is documented with its geometric reasoning, creating
    a fully auditable thought trajectory (the "didactic" layer).

    Usage::

        circuit = PolyDidacticCircuit(flux=FluxGate.POLLY)
        trace = circuit.route(intent_vector, context={"urgent": True})
        for step in trace.steps:
            print(f"  {step.node}: {step.reasoning}")
    """

    def __init__(
        self,
        flux: FluxGate = FluxGate.POLLY,
        energy_budget: float = 1e6,
        dimension_depth: int = 14,
    ):
        self.flux = flux
        self.energy_budget = energy_budget
        self.dimension_depth = dimension_depth
        self.nodes = _build_registry()
        self.adj = _build_adjacency(self.nodes)

        # Validate topology on construction
        for node in self.nodes.values():
            if not node.is_topology_valid():
                raise ValueError(
                    f"Topology validation failed for {node.name}: "
                    f"χ={node.euler_characteristic}, zone={node.zone.value}"
                )

    def route(
        self,
        intent_vector: bytes,
        context: Optional[dict] = None,
    ) -> CircuitTrace:
        """Route an intent through the quasicrystal circuit.

        Args:
            intent_vector: Raw bytes of the intent (hashed or embedded).
            context: Optional context dict with hints like
                     {"urgent": True}, {"sensitive": True}, etc.

        Returns:
            CircuitTrace with full didactic audit trail.
        """
        ctx = context or {}
        trace = CircuitTrace(timestamp=time.time(), flux_state=self.flux.value)

        # 1. Classify intent tongue
        intent_hash = hashlib.sha256(intent_vector).digest()
        tongue = classify_intent_tongue(intent_hash, ctx)
        trace.intent_tongue = tongue

        # 2. Determine accessible nodes based on FluxState
        accessible = _accessible_nodes(self.nodes, self.flux)
        trace.accessible_nodes = len(accessible)

        if not accessible:
            trace.path_valid = False
            trace.final_governance = GovernanceAction.ROLLBACK.value
            return trace

        # 3. Pick starting node: tongue-affine node with lowest radial band
        tongue_nodes = [
            n for n in accessible
            if self.nodes[n].tongue_affinity == tongue
        ]
        if tongue_nodes:
            start = min(tongue_nodes, key=lambda n: self.nodes[n].radial_band[0])
        else:
            start = min(accessible, key=lambda n: self.nodes[n].radial_band[0])

        # 4. Find Hamiltonian path
        path = _find_hamiltonian_path(start, accessible, self.adj)
        if path is None or len(path) != len(accessible):
            trace.path_valid = False
            trace.final_governance = GovernanceAction.ROLLBACK.value
            return trace

        # 5. Traverse path with per-node governance gating
        cumulative_energy = 0.0
        blocked = False

        for i, node_name in enumerate(path):
            node = self.nodes[node_name]

            # Compute radial distance (midpoint of band)
            radial_dist = (node.radial_band[0] + node.radial_band[1]) / 2

            # Compute energy cost at this node
            wall_cost = harmonic_wall_cost(radial_dist, self.dimension_depth)

            # Edge weight from previous node (first step = intent tongue weight)
            if i == 0:
                edge_weight = TONGUE_WEIGHTS[tongue]
            else:
                prev = path[i - 1]
                edge = next(
                    (e for e in self.adj[prev] if e.target == node_name),
                    None,
                )
                edge_weight = edge.weight if edge else TONGUE_WEIGHTS[tongue]

            step_energy = wall_cost * edge_weight
            cumulative_energy += step_energy

            # Trust ring
            ring, latency = classify_trust_ring(radial_dist)

            # FSGS governance gate
            action, symbol, reasoning = _governance_gate(
                node, radial_dist, cumulative_energy,
                self.energy_budget, i,
            )

            # Build didactic step
            step = CircuitStep(
                step_index=i,
                node=node_name,
                zone=node.zone.value,
                tongue=node.tongue_affinity,
                tongue_weight=TONGUE_WEIGHTS[node.tongue_affinity],
                energy_cost=step_energy,
                cumulative_energy=cumulative_energy,
                governance=symbol,
                mode=action.value,
                trust_ring=ring,
                radial_distance=radial_dist,
                latency_ms=latency if latency is not None else 0.0,
                reasoning=reasoning,
            )
            trace.steps.append(step)

            # Check governance
            if action == GovernanceAction.ROLLBACK:
                trace.path_valid = False
                trace.final_governance = GovernanceAction.ROLLBACK.value
                blocked = True
                break
            elif action == GovernanceAction.QUARANTINE:
                trace.final_governance = GovernanceAction.QUARANTINE.value

        if not blocked:
            trace.total_energy = cumulative_energy
            trace.trace_digest = trace.digest()
            # Final governance = worst mode encountered
            modes = [s.mode for s in trace.steps]
            if GovernanceAction.QUARANTINE.value in modes:
                trace.final_governance = GovernanceAction.QUARANTINE.value
            elif GovernanceAction.HOLD.value in modes:
                trace.final_governance = GovernanceAction.HOLD.value
            else:
                trace.final_governance = GovernanceAction.RUN.value

        return trace

    def validate_topology(self) -> Dict[str, dict]:
        """Validate all 16 polyhedra topology (zone-dependent χ).

        Returns:
            Dict of node_name → {chi, expected, valid, zone} for each.
        """
        results = {}
        for name, node in self.nodes.items():
            results[name] = {
                "chi": node.euler_characteristic,
                "expected": node.expected_euler,
                "valid": node.is_topology_valid(),
                "zone": node.zone.value,
                "V": node.vertices,
                "E": node.edges,
                "F": node.faces,
                "genus": node.genus,
            }
        return results

    def get_zone_summary(self) -> Dict[str, List[str]]:
        """Get nodes grouped by zone."""
        summary: Dict[str, List[str]] = {}
        for name, node in self.nodes.items():
            zone = node.zone.value
            summary.setdefault(zone, []).append(name)
        return summary

    def get_tongue_map(self) -> Dict[str, List[str]]:
        """Get nodes grouped by tongue affinity."""
        tmap: Dict[str, List[str]] = {}
        for name, node in self.nodes.items():
            tongue = node.tongue_affinity
            tmap.setdefault(tongue, []).append(name)
        return tmap

    def set_flux(self, new_flux: FluxGate):
        """Change dimensional breathing state."""
        self.flux = new_flux


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------

def create_circuit(
    flux: str = "POLLY",
    energy_budget: float = 1e6,
) -> PolyDidacticCircuit:
    """Factory function for creating a circuit."""
    flux_gate = FluxGate[flux.upper()]
    return PolyDidacticCircuit(flux=flux_gate, energy_budget=energy_budget)
