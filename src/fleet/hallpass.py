"""
Hall Pass: Hamiltonian Corridor Pathfinding for Skill Cards
============================================================
Maps SkillCards to PHDM polyhedra, finds minimum-energy Hamiltonian
paths, projects skills to single faces for context funneling,
and bundles everything into a guidance-only HallPass corridor.

Based on:
- PHDM Chapter 6 (16 polyhedra, energy costs, edge penalties)
- Hamiltonian Braid Specification (rails, trust tube, MSR algebra)
- Hexa-Phase sectors (KO/AV/RU/CA/UM/DR tongue phases)

A HallPass is a pre-compiled rail through PHDM polyhedral space.
It shapes routing, timing, and phase projection, but it does not
grant access or replace existing permission systems.
"""

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from src.fleet.skill_card_forge import SkillCard, Deck, SynergyType, CardType
from src.fleet.skill_deck_engine import (
    DeckOptimizer,
    SynergyEngine,
    WorkflowCompiler,
    classify_permissions,
)

PHI = (1 + math.sqrt(5)) / 2  # Golden ratio ~1.618


# ============================================================
# PHDM Polyhedra — the 16 cognitive nodes
# ============================================================


@dataclass(frozen=True)
class Polyhedron:
    """A PHDM polyhedral node with energy cost and position."""

    id: int
    name: str
    category: str  # platonic, archimedean, kepler, toroidal, rhombic, johnson
    faces: int  # number of geometric faces
    energy_base: float  # base energy cost to visit
    position_6d: Tuple[float, ...]  # position in tongue-space (KO,AV,RU,CA,UM,DR)


# The 16 PHDM polyhedra (from Notion Chapter 6)
POLYHEDRA: List[Polyhedron] = [
    # Platonic Five — safe core (E0 = 1.0–2.5)
    Polyhedron(0, "Tetrahedron", "platonic", 4, 1.0, (0.0, 0.0, 0.0, 0.0, 0.0, 1.0)),
    Polyhedron(1, "Cube", "platonic", 6, 1.2, (0.2, 0.0, 0.0, 0.0, 0.0, 0.9)),
    Polyhedron(2, "Octahedron", "platonic", 8, 1.5, (0.0, 0.2, 0.0, 0.0, 0.0, 0.85)),
    Polyhedron(3, "Dodecahedron", "platonic", 12, 2.0, (0.3, 0.1, 0.0, 0.0, 0.0, 0.8)),
    Polyhedron(4, "Icosahedron", "platonic", 20, 2.5, (0.1, 0.3, 0.0, 0.0, 0.0, 0.75)),
    # Archimedean Three — complex reasoning (E1 = 4.0–7.0)
    Polyhedron(
        5,
        "Truncated Icosahedron",
        "archimedean",
        32,
        4.0,
        (0.4, 0.4, 0.0, 0.0, 0.0, 0.5),
    ),
    Polyhedron(
        6,
        "Rhombicosidodecahedron",
        "archimedean",
        62,
        5.5,
        (0.5, 0.3, 0.1, 0.0, 0.0, 0.45),
    ),
    Polyhedron(
        7, "Snub Dodecahedron", "archimedean", 92, 7.0, (0.6, 0.4, 0.2, 0.0, 0.0, 0.4)
    ),
    # Kepler-Poinsot Two — high-risk / adversarial (E2 = 12.0–15.0)
    Polyhedron(
        8,
        "Small Stellated Dodecahedron",
        "kepler",
        12,
        12.0,
        (0.8, 0.7, 0.5, 0.0, 0.0, 0.9),
    ),
    Polyhedron(
        9,
        "Great Stellated Dodecahedron",
        "kepler",
        12,
        15.0,
        (0.9, 0.8, 0.6, 0.0, 0.0, 0.95),
    ),
    # Toroidal Two — cyclic (E3 = 8.0–10.0)
    Polyhedron(
        10, "Genus-1 Torus", "toroidal", 24, 8.0, (0.5, 0.5, 0.5, 0.8, 0.0, 0.6)
    ),
    Polyhedron(
        11, "Hexagonal Torus", "toroidal", 36, 10.0, (0.6, 0.5, 0.5, 0.9, 0.0, 0.65)
    ),
    # Rhombic Two — space-filling (E3 = 6.0–8.0)
    Polyhedron(
        12, "Rhombic Dodecahedron", "rhombic", 12, 6.0, (0.4, 0.3, 0.3, 0.0, 0.5, 0.5)
    ),
    Polyhedron(
        13,
        "Rhombic Triacontahedron",
        "rhombic",
        30,
        8.0,
        (0.5, 0.4, 0.3, 0.0, 0.6, 0.55),
    ),
    # Johnson Two — edge-case (E3 = 5.0–7.0)
    Polyhedron(
        14, "Square Gyrobicupola", "johnson", 18, 5.0, (0.3, 0.4, 0.2, 0.0, 0.3, 0.5)
    ),
    Polyhedron(
        15,
        "Pentagonal Orthobirotunda",
        "johnson",
        32,
        7.0,
        (0.4, 0.5, 0.3, 0.0, 0.4, 0.55),
    ),
]

POLYHEDRA_BY_ID: Dict[int, Polyhedron] = {p.id: p for p in POLYHEDRA}


# Edge transition penalties (from PHDM Chapter 6.2.3)
EDGE_PENALTIES: Dict[Tuple[str, str], float] = {
    ("platonic", "platonic"): 0.5,
    ("platonic", "archimedean"): 1.5,
    ("platonic", "toroidal"): 4.0,
    ("platonic", "rhombic"): 2.0,
    ("platonic", "johnson"): 1.5,
    ("platonic", "kepler"): 8.0,
    ("archimedean", "archimedean"): 1.0,
    ("archimedean", "toroidal"): 3.0,
    ("archimedean", "rhombic"): 2.0,
    ("archimedean", "johnson"): 2.0,
    ("archimedean", "kepler"): 8.0,
    ("kepler", "kepler"): 12.0,
    ("kepler", "toroidal"): 6.0,
    ("kepler", "rhombic"): 5.0,
    ("kepler", "johnson"): 5.0,
    ("toroidal", "toroidal"): 3.0,
    ("toroidal", "rhombic"): 2.5,
    ("toroidal", "johnson"): 2.5,
    ("rhombic", "rhombic"): 1.5,
    ("rhombic", "johnson"): 2.0,
    ("johnson", "johnson"): 2.0,
}


# Sacred Tongue phases — the 6 faces of each skill's polyhedron
TONGUE_PHASES = {
    0: {"code": "KO", "name": "Kor'aelin", "domain": "Flow", "phase": 0.0},
    1: {"code": "AV", "name": "Avali", "domain": "Context", "phase": math.pi / 3},
    2: {
        "code": "RU",
        "name": "Runethic",
        "domain": "Binding",
        "phase": 2 * math.pi / 3,
    },
    3: {"code": "CA", "name": "Cassisivadan", "domain": "Bitcraft", "phase": math.pi},
    4: {"code": "UM", "name": "Umbroth", "domain": "Veil", "phase": 4 * math.pi / 3},
    5: {
        "code": "DR",
        "name": "Draumric",
        "domain": "Structure",
        "phase": 5 * math.pi / 3,
    },
}


# ============================================================
# Skill → Polyhedron Mapping
# ============================================================


def map_card_to_polyhedron(card: SkillCard) -> Polyhedron:
    """Map a SkillCard to a PHDM polyhedron based on synergy, type, and power.

    Mapping rules:
    - Agent cards → Toroidal (cyclic coordination)
    - Workflow cards → Rhombic (space-filling, composable)
    - Defense cards → Archimedean (complex reasoning, governance)
    - Research cards → Johnson (edge-case exploration)
    - Arcane synergy → Kepler-Poinsot (high-dimensional)
    - Offensive/Utility/Support → Platonic (safe core), scaled by power
    - Orchestrator → Archimedean
    """
    synergy = card.synergy
    card_type = card.card_type
    power = card.power

    # Type-first rules
    if card_type == CardType.AGENT.value:
        return POLYHEDRA[10] if power < 400 else POLYHEDRA[11]  # Toroidal
    if card_type == CardType.WORKFLOW.value:
        return POLYHEDRA[12] if power < 400 else POLYHEDRA[13]  # Rhombic
    if card_type == CardType.DEFENSE.value:
        return POLYHEDRA[5] if power < 400 else POLYHEDRA[6]  # Archimedean
    if card_type == CardType.RESEARCH.value:
        return POLYHEDRA[14] if power < 400 else POLYHEDRA[15]  # Johnson

    # Synergy rules for Skill/Tool types
    if synergy == SynergyType.ARCANE.value:
        return POLYHEDRA[8] if power < 500 else POLYHEDRA[9]  # Kepler

    if synergy == SynergyType.ORCHESTRATOR.value:
        return POLYHEDRA[7]  # Snub Dodecahedron

    if synergy == SynergyType.DEFENSIVE.value:
        return POLYHEDRA[5]  # Truncated Icosahedron

    # Offensive/Utility/Support → Platonic, scaled by power
    if power < 150:
        return POLYHEDRA[0]  # Tetrahedron
    elif power < 250:
        return POLYHEDRA[1]  # Cube
    elif power < 350:
        return POLYHEDRA[2]  # Octahedron
    elif power < 500:
        return POLYHEDRA[3]  # Dodecahedron
    else:
        return POLYHEDRA[4]  # Icosahedron


def get_edge_penalty(from_poly: Polyhedron, to_poly: Polyhedron) -> float:
    """Look up the edge transition penalty between two polyhedra."""
    key = (from_poly.category, to_poly.category)
    rev_key = (to_poly.category, from_poly.category)
    return EDGE_PENALTIES.get(key, EDGE_PENALTIES.get(rev_key, 3.0))


# ============================================================
# Hamiltonian Path Finder
# ============================================================


def compute_path_cost(path: List[Polyhedron]) -> float:
    """Total energy cost for a path through polyhedra."""
    if not path:
        return 0.0
    total = path[0].energy_base
    for i in range(len(path) - 1):
        total += path[i + 1].energy_base
        total += get_edge_penalty(path[i], path[i + 1])
    return total


def find_hamiltonian_path(
    nodes: List[Polyhedron],
    start: Optional[Polyhedron] = None,
) -> List[Polyhedron]:
    """Find a Hamiltonian path visiting each node exactly once.

    Uses nearest-neighbor heuristic (greedy by minimum energy cost).
    For N <= 16 nodes this is fast and produces good-enough paths.
    """
    if not nodes:
        return []
    if len(nodes) == 1:
        return list(nodes)

    remaining = list(nodes)

    # Start with the lowest-energy node (or specified start)
    if start and start in remaining:
        current = start
    else:
        current = min(remaining, key=lambda p: p.energy_base)

    remaining.remove(current)
    path = [current]

    while remaining:
        # Pick next node with minimum (edge_penalty + node_energy)
        best = min(
            remaining,
            key=lambda p: get_edge_penalty(current, p) + p.energy_base,
        )
        remaining.remove(best)
        path.append(best)
        current = best

    return path


# ============================================================
# Face Projection — context funneling
# ============================================================


def classify_tongue_phase(task_description: str) -> int:
    """Determine which tongue phase a task operates in (0-5).

    KO=Flow (execution, pipeline), AV=Context (research, search),
    RU=Binding (integration, API), CA=Bitcraft (code, build),
    UM=Veil (security, governance), DR=Structure (architecture, deploy)
    """
    desc = task_description.lower()
    scores = {
        0: sum(
            1
            for kw in ["run", "execute", "pipeline", "flow", "process", "publish"]
            if kw in desc
        ),
        1: sum(
            1
            for kw in ["research", "search", "context", "learn", "read", "analyze"]
            if kw in desc
        ),
        2: sum(
            1
            for kw in ["integrate", "api", "connect", "bridge", "bind", "link"]
            if kw in desc
        ),
        3: sum(
            1
            for kw in ["code", "build", "implement", "write", "compile", "script"]
            if kw in desc
        ),
        4: sum(
            1
            for kw in ["security", "governance", "audit", "gate", "safety", "encrypt"]
            if kw in desc
        ),
        5: sum(
            1
            for kw in [
                "deploy",
                "structure",
                "architect",
                "design",
                "organize",
                "system",
            ]
            if kw in desc
        ),
    }
    best = max(scores, key=lambda k: scores[k])
    return best


@dataclass
class FaceProjection:
    """A skill projected to a single polyhedron face."""

    card_id: str
    card_name: str
    polyhedron_id: int
    polyhedron_name: str
    face_index: int  # which of 6 tongue faces (0-5)
    face_code: str  # KO, AV, RU, CA, UM, DR
    full_token_cost: int  # cost if loading entire skill
    projected_token_cost: int  # cost of just this face
    phase_angle: float  # hexa-phase position

    @property
    def savings_pct(self) -> float:
        """Context savings from projection."""
        if self.full_token_cost == 0:
            return 0.0
        return 1.0 - (self.projected_token_cost / self.full_token_cost)


def project_to_face(card: SkillCard, tongue_phase: int) -> FaceProjection:
    """Project a skill card to a single face of its polyhedron.

    The key insight: a workflow only needs 1/6th of a skill's context —
    the face aligned with the tongue dimension it operates in.
    """
    poly = map_card_to_polyhedron(card)
    perms = classify_permissions(card)
    full_cost = perms.token_cost

    # Projected cost: base floor (200 tokens) + 1/6th of the variable cost
    variable_cost = max(0, full_cost - 200)
    projected_cost = 200 + variable_cost // 6

    phase_info = TONGUE_PHASES[tongue_phase]

    return FaceProjection(
        card_id=card.card_id,
        card_name=card.name,
        polyhedron_id=poly.id,
        polyhedron_name=poly.name,
        face_index=tongue_phase,
        face_code=phase_info["code"],
        full_token_cost=full_cost,
        projected_token_cost=projected_cost,
        phase_angle=phase_info["phase"],
    )


# ============================================================
# Trust Tube + Harmonic Wall
# ============================================================

TUBE_RADIUS = 0.15  # from Hamiltonian Braid Specification


def harmonic_wall_cost(distance: float) -> float:
    """Barrier cost: phi^(d^2). Zero inside tube, exponential outside.

    From the Hamiltonian Braid Spec Section 6.1:
    - Inside tube (d <= epsilon): cost = 0
    - Outside: cost = phi^(d^2)
    """
    if distance <= TUBE_RADIUS:
        return 0.0
    return PHI ** (distance**2)


def hyperbolic_distance_approx(
    pos_a: Tuple[float, ...], pos_b: Tuple[float, ...]
) -> float:
    """Approximate hyperbolic distance between two 6D positions.

    Uses the Poincare ball metric: d = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    """
    diff_sq = sum((a - b) ** 2 for a, b in zip(pos_a, pos_b))
    norm_a_sq = sum(a**2 for a in pos_a)
    norm_b_sq = sum(b**2 for b in pos_b)

    denom = (1.0 - min(norm_a_sq, 0.99)) * (1.0 - min(norm_b_sq, 0.99))
    if denom <= 0:
        denom = 1e-10

    arg = 1.0 + 2.0 * diff_sq / denom
    return math.acosh(max(arg, 1.0))


# ============================================================
# HallPass — the guidance corridor
# ============================================================


def infer_branch_policy(task_description: str) -> str:
    """Infer a routing policy for the corridor overlay."""
    desc = task_description.lower()
    if any(kw in desc for kw in ["roundabout", "circle", "orbital"]):
        return "roundabout"
    if any(kw in desc for kw in ["split", "branch", "fanout", "parallel"]):
        return "split"
    if any(kw in desc for kw in ["merge", "join", "funnel", "combine"]):
        return "merge"
    if any(kw in desc for kw in ["unknown", "frontier", "explore", "probe"]):
        return "frontier"
    return "linear"


def infer_workflow_role(card: SkillCard, workflow_compiler: WorkflowCompiler) -> str:
    """Reuse the fleet workflow role classifier for corridor nodes."""
    return workflow_compiler._classify_role(card)


def infer_switchboard_role(card_type: str, workflow_role: str) -> str:
    """Pick a switchboard role from card and workflow semantics."""
    card_type_normalized = str(card_type).strip().lower()
    if card_type_normalized == "agent":
        return "agent"
    if card_type_normalized == "workflow":
        return "workflow"
    if card_type_normalized == "defense":
        return "defense"
    if card_type_normalized == "research":
        return "research"

    workflow_map = {
        "gather": "agent",
        "orchestrate": "workflow",
        "output": "workflow",
        "validate": "defense",
        "process": "skill",
    }
    return workflow_map.get(workflow_role, "skill")


@dataclass
class HallPassNode:
    """One node in the hall pass guidance corridor."""

    order: int
    card_id: str
    card_name: str
    card_type: str
    workflow_role: str
    polyhedron_id: int
    polyhedron_name: str
    face: FaceProjection
    node_energy: float  # polyhedron base energy
    edge_penalty: float  # penalty from previous node (0 for first)
    cumulative_energy: float  # total energy up to this point
    permissions: List[str]  # legacy compatibility; treated as hints only
    latency_ms: int
    risk_level: float
    slot_start_ms: int
    slot_end_ms: int

    @property
    def capability_hints(self) -> List[str]:
        """Non-authoritative hints about touched systems."""
        return self.permissions

    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "card_id": self.card_id,
            "card_name": self.card_name,
            "card_type": self.card_type,
            "workflow_role": self.workflow_role,
            "polyhedron": self.polyhedron_name,
            "face": self.face.face_code,
            "node_energy": self.node_energy,
            "edge_penalty": self.edge_penalty,
            "cumulative_energy": round(self.cumulative_energy, 2),
            "projected_tokens": self.face.projected_token_cost,
            "capability_hints": self.capability_hints,
            "permissions": self.permissions,
            "latency_ms": self.latency_ms,
            "risk_level": round(self.risk_level, 3),
            "reservation_window_ms": [self.slot_start_ms, self.slot_end_ms],
        }


@dataclass
class HallPass:
    """A pre-compiled Hamiltonian corridor through PHDM polyhedra.

    The hall pass is a guidance plan:
    - The rail (ordered path through polyhedra)
    - Context funneled to single faces per skill
    - Energy budget pre-computed
    - Trust tube radius and drift budgets set
    - Reservation timing for smooth multi-agent flow

    Authorization remains external to this object.
    """

    pass_id: str
    workflow_name: str
    tongue_phase: int  # which dimension (0-5)
    tongue_code: str  # KO, AV, RU, CA, UM, DR
    corridor: List[HallPassNode]  # the Hamiltonian path
    total_energy: float  # sum of all node + edge costs
    total_projected_tokens: int  # context cost after face projection
    total_full_tokens: int  # what it would cost without projection
    context_savings_pct: float  # how much context we saved
    permissions: List[str]  # legacy compatibility; capability hints only
    trust_tube_radius: float  # epsilon
    max_barrier_cost: float  # phi^(epsilon^2) at tube boundary
    lane_id: str
    corridor_graph_id: str
    branch_policy: str
    expected_step_order: List[str]
    reservation_windows_ms: List[Tuple[int, int]]
    ttl_ms: int
    drift_budget: float
    congestion_budget: float
    guidance_only: bool
    grants_access: bool
    compiled_at: float
    source_task: str

    @property
    def node_count(self) -> int:
        return len(self.corridor)

    @property
    def capability_hints(self) -> List[str]:
        return self.permissions

    def to_dict(self) -> dict:
        return {
            "pass_id": self.pass_id,
            "workflow_name": self.workflow_name,
            "tongue_phase": self.tongue_phase,
            "tongue_code": self.tongue_code,
            "node_count": self.node_count,
            "total_energy": round(self.total_energy, 2),
            "total_projected_tokens": self.total_projected_tokens,
            "total_full_tokens": self.total_full_tokens,
            "context_savings_pct": round(self.context_savings_pct * 100, 1),
            "guidance_only": self.guidance_only,
            "grants_access": self.grants_access,
            "lane_id": self.lane_id,
            "corridor_graph_id": self.corridor_graph_id,
            "branch_policy": self.branch_policy,
            "expected_step_order": self.expected_step_order,
            "reservation_windows_ms": [
                list(window) for window in self.reservation_windows_ms
            ],
            "ttl_ms": self.ttl_ms,
            "drift_budget": round(self.drift_budget, 4),
            "congestion_budget": round(self.congestion_budget, 4),
            "capability_hints": self.capability_hints,
            "permissions": self.permissions,
            "trust_tube_radius": self.trust_tube_radius,
            "max_barrier_cost": round(self.max_barrier_cost, 4),
            "compiled_at": self.compiled_at,
            "source_task": self.source_task,
            "corridor": [n.to_dict() for n in self.corridor],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def display(self) -> str:
        """Human-readable hall pass display."""
        lines = [
            f"=== HALL PASS: {self.workflow_name} ===",
            f"Tongue: {self.tongue_code} ({TONGUE_PHASES[self.tongue_phase]['domain']})",
            f"Nodes: {self.node_count} | Energy: {self.total_energy:.1f}",
            f"Context: {self.total_projected_tokens} tokens "
            f"(saved {self.context_savings_pct:.0%} from {self.total_full_tokens})",
            f"Guidance: lane={self.lane_id} | branch={self.branch_policy} | ttl={self.ttl_ms}ms",
            f"Authorization: external | capability hints={', '.join(self.capability_hints) or '(none)'}",
            f"Trust Tube: epsilon={self.trust_tube_radius}, "
            f"barrier at boundary={self.max_barrier_cost:.4f}",
            "",
        ]
        for node in self.corridor:
            arrow = "  " if node.order == 0 else " →"
            edge = f" +{node.edge_penalty:.1f}e" if node.edge_penalty > 0 else ""
            lines.append(
                f"{arrow} [{node.order}] {node.card_name} "
                f"@ {node.polyhedron_name} "
                f"(E={node.node_energy:.1f}{edge}, "
                f"face={node.face.face_code}, "
                f"{node.face.projected_token_cost}tok, "
                f"slot={node.slot_start_ms}-{node.slot_end_ms}ms)"
            )
        lines.append(f"\nPass ID: {self.pass_id}")
        return "\n".join(lines)


# ============================================================
# HallPassCompiler — builds passes from tasks
# ============================================================


class HallPassCompiler:
    """Compiles a task description into a HallPass corridor.

    Pipeline:
    1. Optimize deck for the task (via DeckOptimizer)
    2. Map each selected card to a PHDM polyhedron
    3. Find Hamiltonian path through those polyhedra
    4. Classify which tongue dimension the task operates in
    5. Project each skill to that dimension's face
    6. Bundle into HallPass guidance with timing, drift, and lane metadata
    """

    def __init__(
        self,
        optimizer: Optional[DeckOptimizer] = None,
        synergy_engine: Optional[SynergyEngine] = None,
        workflow_compiler: Optional[WorkflowCompiler] = None,
    ) -> None:
        self.synergy_engine = synergy_engine or SynergyEngine()
        self.optimizer = optimizer or DeckOptimizer(synergy_engine=self.synergy_engine)
        self.workflow_compiler = workflow_compiler or WorkflowCompiler()

    def compile(
        self,
        task: str,
        pool: List[SkillCard],
        max_cards: int = 10,
        workflow_name: Optional[str] = None,
        tongue_override: Optional[int] = None,
    ) -> HallPass:
        """Compile a task into a HallPass corridor.

        Args:
            task: Natural language task description
            pool: Available skill cards
            max_cards: Maximum skills to include
            workflow_name: Optional name for the pass
            tongue_override: Force a specific tongue phase (0-5)
        """
        # Step 1: Select best cards for the task
        selected = self.optimizer.optimize(task, pool, max_cards=max_cards)

        # Step 2: Map each card to a polyhedron
        card_poly_pairs = [(card, map_card_to_polyhedron(card)) for card in selected]

        # Step 3: Find Hamiltonian path through the polyhedra
        # We need to maintain card-polyhedron association through the path
        polys = [p for _, p in card_poly_pairs]
        poly_path = find_hamiltonian_path(polys)

        # Reorder cards to match the polyhedron path order
        poly_to_cards: Dict[int, List[SkillCard]] = {}
        for card, poly in card_poly_pairs:
            poly_to_cards.setdefault(poly.id, []).append(card)

        ordered_pairs: List[Tuple[SkillCard, Polyhedron]] = []
        for poly in poly_path:
            cards_for_poly = poly_to_cards.get(poly.id, [])
            if cards_for_poly:
                card = cards_for_poly.pop(0)
                ordered_pairs.append((card, poly))

        # Step 4: Classify tongue dimension
        tongue_phase = (
            tongue_override
            if tongue_override is not None
            else classify_tongue_phase(task)
        )

        # Step 5: Project each card to that face + build corridor nodes
        corridor: List[HallPassNode] = []
        all_permissions: Set[str] = set()
        cumulative_energy = 0.0
        total_projected = 0
        total_full = 0
        reservation_cursor = 0
        expected_step_order: List[str] = []
        reservation_windows: List[Tuple[int, int]] = []

        for i, (card, poly) in enumerate(ordered_pairs):
            face = project_to_face(card, tongue_phase)
            perms = classify_permissions(card)
            workflow_role = infer_workflow_role(card, self.workflow_compiler)

            edge_penalty = 0.0
            if i > 0:
                prev_poly = ordered_pairs[i - 1][1]
                edge_penalty = get_edge_penalty(prev_poly, poly)

            cumulative_energy += poly.energy_base + edge_penalty
            all_permissions.update(perms.granted)
            total_projected += face.projected_token_cost
            total_full += face.full_token_cost
            slot_duration = max(100, perms.latency_ms + int(edge_penalty * 100))
            slot_start = reservation_cursor
            slot_end = slot_start + slot_duration
            reservation_cursor = slot_end
            expected_step_order.append(card.card_id)
            reservation_windows.append((slot_start, slot_end))

            corridor.append(
                HallPassNode(
                    order=i,
                    card_id=card.card_id,
                    card_name=card.name,
                    card_type=card.card_type,
                    workflow_role=workflow_role,
                    polyhedron_id=poly.id,
                    polyhedron_name=poly.name,
                    face=face,
                    node_energy=poly.energy_base,
                    edge_penalty=edge_penalty,
                    cumulative_energy=cumulative_energy,
                    permissions=sorted(perms.granted),
                    latency_ms=perms.latency_ms,
                    risk_level=perms.risk_level,
                    slot_start_ms=slot_start,
                    slot_end_ms=slot_end,
                )
            )

        # Step 6: Bundle into HallPass
        name = workflow_name or f"hallpass-{task[:30].replace(' ', '-')}"
        pass_id = hashlib.sha256(
            f"{name}:{tongue_phase}:{','.join(c.card_id for c, _ in ordered_pairs)}".encode()
        ).hexdigest()[:16]
        branch_policy = infer_branch_policy(task)
        corridor_graph_id = hashlib.sha256(
            f"{pass_id}:{branch_policy}:{','.join(expected_step_order)}".encode()
        ).hexdigest()[:16]
        lane_id = f"{TONGUE_PHASES[tongue_phase]['code'].lower()}-{branch_policy}-{pass_id[:6]}"

        savings = 1.0 - (total_projected / total_full) if total_full > 0 else 0.0

        return HallPass(
            pass_id=pass_id,
            workflow_name=name,
            tongue_phase=tongue_phase,
            tongue_code=TONGUE_PHASES[tongue_phase]["code"],
            corridor=corridor,
            total_energy=cumulative_energy,
            total_projected_tokens=total_projected,
            total_full_tokens=total_full,
            context_savings_pct=savings,
            permissions=sorted(all_permissions),
            trust_tube_radius=TUBE_RADIUS,
            max_barrier_cost=harmonic_wall_cost(TUBE_RADIUS + 0.01),
            lane_id=lane_id,
            corridor_graph_id=corridor_graph_id,
            branch_policy=branch_policy,
            expected_step_order=expected_step_order,
            reservation_windows_ms=reservation_windows,
            ttl_ms=max(1000, reservation_cursor + 1000),
            drift_budget=TUBE_RADIUS,
            congestion_budget=max(0.5, len(corridor) * 0.25),
            guidance_only=True,
            grants_access=False,
            compiled_at=time.time(),
            source_task=task,
        )

    def compile_from_deck(
        self,
        task: str,
        deck_path: str,
        max_cards: int = 10,
        **kwargs,
    ) -> HallPass:
        """Compile from a saved deck file."""
        deck = Deck.load(deck_path)
        return self.compile(task, deck.cards, max_cards, **kwargs)


# ============================================================
# HallPassDispatcher — dispatch corridor to Switchboard
# ============================================================


@dataclass
class DispatchResult:
    """Result of dispatching a hall pass to the switchboard."""

    pass_id: str
    dispatched: int  # number of tasks enqueued
    task_ids: List[str]  # switchboard task IDs in corridor order
    role_channel: str  # role channel for this corridor
    corridor_order: List[str]  # card names in execution order

    def to_dict(self) -> dict:
        return {
            "pass_id": self.pass_id,
            "dispatched": self.dispatched,
            "task_ids": self.task_ids,
            "role_channel": self.role_channel,
            "corridor_order": self.corridor_order,
        }


class HallPassDispatcher:
    """Dispatches a compiled HallPass corridor to the HYDRA Switchboard.

    Each corridor node becomes a Switchboard task:
    - Role: derived from the skill's card/workflow role
    - Payload: face-projected context, guidance metadata, corridor position
    - Priority: corridor order (first node = highest priority)
    - Dedupe: pass_id + node order prevents double-dispatch

    Workers claim tasks by role and receive pre-projected guidance.
    Authorization remains external to HallPass.
    """

    CARD_TYPE_TO_ROLE = {
        "Agent": "agent",
        "Workflow": "workflow",
        "Tool": "tool",
        "Skill": "skill",
        "Defense": "defense",
        "Research": "research",
    }

    def __init__(self, switchboard=None):
        """Initialize with a Switchboard instance.

        Args:
            switchboard: A hydra.switchboard.Switchboard instance.
                         If None, creates one with default path.
        """
        self._switchboard = switchboard

    @property
    def switchboard(self):
        if self._switchboard is None:
            from hydra.switchboard import Switchboard

            self._switchboard = Switchboard()
        return self._switchboard

    def dispatch(self, hall_pass: HallPass) -> DispatchResult:
        """Enqueue each corridor node as a switchboard task.

        Tasks are ordered by corridor position (priority = order * 10).
        Each task carries:
        - The face-projected skill context (1/6 of full)
        - Guidance metadata (lane, drift budget, reservation window)
        - Capability hints (non-authoritative)
        - Energy budget up to this point
        """
        task_ids: List[str] = []
        corridor_order: List[str] = []
        role_channel = f"hallpass-{hall_pass.pass_id}"

        for node in hall_pass.corridor:
            role = infer_switchboard_role(node.card_type, node.workflow_role)

            payload = {
                "hallpass": {
                    "pass_id": hall_pass.pass_id,
                    "workflow_name": hall_pass.workflow_name,
                    "tongue_code": hall_pass.tongue_code,
                    "tongue_phase": hall_pass.tongue_phase,
                    "node_count": hall_pass.node_count,
                    "trust_tube_radius": hall_pass.trust_tube_radius,
                    "lane_id": hall_pass.lane_id,
                    "corridor_graph_id": hall_pass.corridor_graph_id,
                    "branch_policy": hall_pass.branch_policy,
                    "ttl_ms": hall_pass.ttl_ms,
                    "guidance_only": hall_pass.guidance_only,
                    "grants_access": hall_pass.grants_access,
                },
                "node": {
                    "order": node.order,
                    "card_id": node.card_id,
                    "card_name": node.card_name,
                    "card_type": node.card_type,
                    "workflow_role": node.workflow_role,
                    "polyhedron": node.polyhedron_name,
                    "polyhedron_id": node.polyhedron_id,
                    "face_code": node.face.face_code,
                    "projected_tokens": node.face.projected_token_cost,
                    "full_tokens": node.face.full_token_cost,
                    "phase_angle": round(node.face.phase_angle, 4),
                },
                "guidance": {
                    "mode": "routing_guidance",
                    "expected_step_order": hall_pass.expected_step_order,
                    "reservation_window_ms": [node.slot_start_ms, node.slot_end_ms],
                    "drift_budget": hall_pass.drift_budget,
                    "congestion_budget": hall_pass.congestion_budget,
                    "slot_latency_ms": node.latency_ms,
                    "capability_hints": node.capability_hints,
                },
                "energy": {
                    "node_cost": node.node_energy,
                    "edge_penalty": node.edge_penalty,
                    "cumulative": round(node.cumulative_energy, 2),
                    "total_budget": round(hall_pass.total_energy, 2),
                },
                "authorization": {
                    "mode": "external",
                    "grants_access": False,
                },
                "capability_hints": node.capability_hints,
                "permissions": node.permissions,
                "source_task": hall_pass.source_task,
            }

            result = self.switchboard.enqueue_task(
                role=role,
                payload=payload,
                dedupe_key=f"{hall_pass.pass_id}:{node.order}",
                priority=node.order * 10,
            )

            task_ids.append(result["task_id"])
            corridor_order.append(node.card_name)

        # Post a summary message to the corridor's role channel
        self.switchboard.post_role_message(
            channel=role_channel,
            sender="hallpass-compiler",
            message={
                "event": "corridor_dispatched",
                "mode": "guidance",
                "pass_id": hall_pass.pass_id,
                "workflow": hall_pass.workflow_name,
                "tongue": hall_pass.tongue_code,
                "nodes": hall_pass.node_count,
                "total_energy": round(hall_pass.total_energy, 2),
                "context_savings": f"{hall_pass.context_savings_pct:.0%}",
                "task_ids": task_ids,
            },
        )

        return DispatchResult(
            pass_id=hall_pass.pass_id,
            dispatched=len(task_ids),
            task_ids=task_ids,
            role_channel=role_channel,
            corridor_order=corridor_order,
        )
