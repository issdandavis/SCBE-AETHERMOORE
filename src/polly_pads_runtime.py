"""
Polly Pads Runtime — Dual-Zone Squad Workspaces (Python Reference)

@module polly_pads_runtime
@layer Layer 8, Layer 12, Layer 13
@version 3.2.4

Extends Polly Pads into full agent runtimes with:
- Dual code zones (HOT exploratory + SAFE execution)
- Squad code space (shared, quorum-gated memory)
- Proximity tracking (Euclidean + geodesic)
- Per-pad tool gating by mode + zone
- SCBE decision gating for zone promotion
- Tri-directional Hamiltonian path validation
Polly Pads Runtime - Per-Pad AI Code Assistance

Each Polly Pad is a namespaced agent workspace with:
- Mode-specific toolsets (ENGINEERING, NAVIGATION, SYSTEMS, SCIENCE, COMMS, MISSION)
- Dual code zones: HOT (draft/plan only) and SAFE (execution, requires quorum)
- Squad code space with Byzantine 4/6 quorum for shared voxel commits
- Proximity tracking via 3D Euclidean distance
- SCBE three-tier governance: ALLOW / QUARANTINE / DENY

Integration points:
- Layer 12: Harmonic wall cost (h_eff) drives SCBE decision
- Layer 13: Risk decision tier (ALLOW/QUARANTINE/DENY)
- Sacred Tongues: Voxel addressing uses lang dimension
- VoxelRecord: Canonical payload envelope at 6D address
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

# ═══════════════════════════════════════════════════════════════
# Type Aliases
# ═══════════════════════════════════════════════════════════════

PadMode = Literal["ENGINEERING", "NAVIGATION", "SYSTEMS", "SCIENCE", "COMMS", "MISSION"]
Decision = Literal["ALLOW", "QUARANTINE", "DENY"]
CodeZone = Literal["HOT", "SAFE"]
Lang = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
TraceDirection = Literal["STRUCTURE", "CONFLICT", "TIME"]
TraceResult = Literal["VALID", "DEVIATION", "BLOCKED"]

PAD_MODES: Tuple[PadMode, ...] = (
    "ENGINEERING", "NAVIGATION", "SYSTEMS", "SCIENCE", "COMMS", "MISSION"
)

LANGS: Tuple[Lang, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")

PAD_MODE_TONGUE: Dict[PadMode, Lang] = {
    "ENGINEERING": "CA",
    "NAVIGATION": "AV",
    "SYSTEMS": "DR",
    "SCIENCE": "UM",
    "COMMS": "KO",
    "MISSION": "RU",
}

# Golden ratio
PHI = (1 + math.sqrt(5)) / 2


# ═══════════════════════════════════════════════════════════════
# SCBE Thresholds & Decision
# ═══════════════════════════════════════════════════════════════
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple
import hashlib
import json
import math


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Lang = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
PadMode = Literal[
    "ENGINEERING", "NAVIGATION", "SYSTEMS", "SCIENCE", "COMMS", "MISSION"
]
Decision = Literal["ALLOW", "QUARANTINE", "DENY"]
Voxel6 = Tuple[float, float, float, float, float, float]

PAD_MODES: Tuple[PadMode, ...] = (
    "ENGINEERING",
    "NAVIGATION",
    "SYSTEMS",
    "SCIENCE",
    "COMMS",
    "MISSION",
)

# Mode-specific toolsets
MODE_TOOLS: Dict[PadMode, List[str]] = {
    "ENGINEERING": ["ide_draft", "code_exec_safe", "build_deploy"],
    "NAVIGATION": ["map_query", "proximity_track", "path_plan"],
    "SYSTEMS": ["telemetry_read", "config_set", "policy_enforce"],
    "SCIENCE": ["hypothesis_gen", "experiment_run", "model_tune"],
    "COMMS": ["msg_send", "negotiate", "protocol_exec"],
    "MISSION": ["goal_set", "constraint_check", "orchestrate_squad"],
}


# ---------------------------------------------------------------------------
# SCBE governance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Thresholds:
    """SCBE governance thresholds for risk decision."""
    """SCBE Layer-12/13 decision thresholds."""

    allow_max_cost: float = 1e3
    quarantine_max_cost: float = 1e6
    allow_min_coherence: float = 0.55
    quarantine_min_coherence: float = 0.25
    allow_max_drift: float = 1.2
    quarantine_max_drift: float = 2.2


def scbe_decide(
    d_star: float,
    coherence: float,
    h_eff: float,
    thr: Thresholds = Thresholds(),
) -> Decision:
    """
    Compute SCBE risk decision from governance state.

    Decision hierarchy:
        DENY if coherence < quarantine_min OR h_eff > quarantine_max OR d_star > quarantine_max
        ALLOW if coherence >= allow_min AND h_eff <= allow_max AND d_star <= allow_max
        QUARANTINE otherwise
    """Three-tier SCBE risk decision (Layer 13).

    Args:
        d_star: Hyperbolic drift from safe centre.
        coherence: NK coherence score [0, 1].
        h_eff: Effective Hamiltonian cost (Layer 12).
        thr: Decision thresholds.

    Returns:
        ALLOW, QUARANTINE, or DENY.
    """
    if coherence < thr.quarantine_min_coherence:
        return "DENY"
    if h_eff > thr.quarantine_max_cost:
        return "DENY"
    if d_star > thr.quarantine_max_drift:
        return "DENY"
    if (
        coherence >= thr.allow_min_coherence
        and h_eff <= thr.allow_max_cost
        and d_star <= thr.allow_max_drift
    ):
        return "ALLOW"
    return "QUARANTINE"


def harmonic_cost(d_star: float, r: float = 1.5) -> float:
    """
    Compute effective harmonic cost H(d*, R) = R * pi^(phi * d*).

    This is the Layer-12 event horizon.
    """
    return r * math.pow(math.pi, PHI * d_star)


# ═══════════════════════════════════════════════════════════════
# CubeId & Digest
# ═══════════════════════════════════════════════════════════════


def cube_id(
    scope: str,
    unit_id: str,
    pad_mode: PadMode,
    epoch: int,
    lang: str,
    voxel: List[int],
) -> str:
    """Compute deterministic CubeId from addressing fields (canonical JSON)."""
    payload = {
        "epoch": int(epoch),
        "lang": lang,
        "pad_mode": pad_mode,
        "scope": scope,
        "unit_id": unit_id,
        "voxel": voxel,
        "squad_id": squad_id,
        "unit_id": unit_id,
        "voxel": list(voxel),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def pad_namespace_key(unit_id: str, pad_mode: PadMode, lang: Lang, epoch: int) -> str:
    """Generate voxel namespace key for a pad's memory."""
    return f"{unit_id}:{pad_mode}:{lang}:{epoch}"


# ═══════════════════════════════════════════════════════════════
# Unit State
# ═══════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
# Unit state and spatial helpers
# ---------------------------------------------------------------------------


@dataclass
class UnitState:
    """Physical + governance state of a single unit/drone."""
    """Position + governance snapshot for a single unit."""

    unit_id: str
    x: float
    y: float
    z: float
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    coherence: float = 1.0
    d_star: float = 0.0
    h_eff: float = 0.0


def dist(a: UnitState, b: UnitState) -> float:
    """Euclidean distance between two units."""
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


# ═══════════════════════════════════════════════════════════════
# Squad Space
# ═══════════════════════════════════════════════════════════════
# ---------------------------------------------------------------------------
# Voxel record (Python mirror of scbe-voxel-types.ts)
# ---------------------------------------------------------------------------


@dataclass
class QuorumProof:
    """Byzantine 4/6 quorum proof for voxel commits."""

    n: int
    f: int
    threshold: int
    votes: List[Dict[str, object]]


@dataclass
class SacredEggSeal:
    """Encryption envelope with pi^(phi*d*) key derivation."""

    egg_id: str
    d_star: float
    coherence: float
    nonce: str
    aad: str
    kdf: str = "pi_phi"


@dataclass
class VoxelRecord:
    """Canonical payload envelope at 6D voxel address."""

    scope: Literal["unit", "squad"]
    lang: Lang
    voxel: Voxel6
    epoch: int
    pad_mode: PadMode
    coherence: float
    d_star: float
    h_eff: float
    decision: Decision
    cube_id: str
    payload_digest: str
    seal: SacredEggSeal
    payload_ciphertext: str
    version: int = 1
    unit_id: Optional[str] = None
    squad_id: Optional[str] = None
    quorum: Optional[QuorumProof] = None
    tags: Optional[List[str]] = None
    parents: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Squad space (shared voxel memory + proximity)
# ---------------------------------------------------------------------------


@dataclass
class SquadSpace:
    """Squad-level shared code space with proximity tracking."""

    squad_id: str
    units: Dict[str, UnitState] = field(default_factory=dict)

    def neighbors(self, radius: float) -> Dict[str, List[str]]:
        """Compute proximity graph: units within radius of each other."""
    """Shared code space for a squad of units.

    Writes require Byzantine quorum (>=4/6).
    """

    squad_id: str
    units: Dict[str, UnitState] = field(default_factory=dict)
    voxels: Dict[str, VoxelRecord] = field(default_factory=dict)

    def neighbors(self, radius: float) -> Dict[str, List[str]]:
        """Find neighbour pairs within *radius* Euclidean distance."""
        ids = list(self.units.keys())
        out: Dict[str, List[str]] = {uid: [] for uid in ids}
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a = self.units[ids[i]]
                b = self.units[ids[j]]
                if dist(a, b) <= radius:
                    out[a.unit_id].append(b.unit_id)
                    out[b.unit_id].append(a.unit_id)
        return out

    def quorum_ok(self, votes: int, n: int = 6, threshold: int = 4) -> bool:
        """Check Byzantine quorum: n=6, f=1, threshold=4 (BFT: 3f+1)."""
        f = (n - 1) // 3
        return votes >= threshold and n >= 3 * f + 1 and threshold >= 2 * f + 1

    def find_leader(self) -> Optional[str]:
        """Find consensus leader: lowest h_eff + highest coherence."""
        best_id: Optional[str] = None
        best_score = float("inf")
        for uid, state in self.units.items():
            score = state.h_eff - state.coherence * 1000
            if score < best_score:
                best_score = score
                best_id = uid
        return best_id

    def average_coherence(self) -> float:
        """Average coherence across all units."""
        if not self.units:
            return 0.0
        return sum(s.coherence for s in self.units.values()) / len(self.units)

    def risk_field(self, thr: Thresholds = Thresholds()) -> Dict[str, Decision]:
        """Compute SCBE decision for each unit."""
        return {
            uid: scbe_decide(s.d_star, s.coherence, s.h_eff, thr)
            for uid, s in self.units.items()
        }


# ═══════════════════════════════════════════════════════════════
# Polly Pad (Dual-Zone)
# ═══════════════════════════════════════════════════════════════

# Allowed tools per PadMode × CodeZone
PAD_TOOL_MATRIX: Dict[PadMode, Dict[CodeZone, Tuple[str, ...]]] = {
    "ENGINEERING": {
        "SAFE": ("build", "deploy", "config"),
        "HOT": ("plan_only", "build"),
    },
    "NAVIGATION": {
        "SAFE": ("map", "proximity"),
        "HOT": ("plan_only", "map"),
    },
    "SYSTEMS": {
        "SAFE": ("telemetry", "config", "policy"),
        "HOT": ("plan_only", "telemetry"),
    },
    "SCIENCE": {
        "SAFE": ("hypothesis", "experiment"),
        "HOT": ("plan_only", "hypothesis"),
    },
    "COMMS": {
        "SAFE": ("radio", "encrypt"),
        "HOT": ("plan_only", "radio"),
    },
    "MISSION": {
        "SAFE": ("goals", "constraints", "policy"),
        "HOT": ("plan_only", "goals"),
    },
}

# ---------------------------------------------------------------------------
# Polly Pad (per-unit AI workspace)
# ---------------------------------------------------------------------------


@dataclass
class PollyPad:
    """A single Polly Pad with dual code zones."""

    unit_id: str
    mode: PadMode
    zone: CodeZone = "HOT"
    thr: Thresholds = Thresholds()

    @property
    def tongue(self) -> Lang:
        """Sacred Tongue for this pad's namespace."""
        return PAD_MODE_TONGUE[self.mode]

    @property
    def tools(self) -> Tuple[str, ...]:
        """Currently available tools based on mode + zone."""
        return PAD_TOOL_MATRIX[self.mode][self.zone]
    """Personal AI workspace with mode-specific tools, dual zones, and assist().

    Each pad provides:
    - Scoped toolset determined by *mode*
    - Dual code zones: HOT (draft only) / SAFE (exec, needs quorum)
    - ``assist()`` method for per-pad AI code assistance
    - Local voxel memory namespace
    """

    unit_id: str
    mode: PadMode
    zone: Literal["HOT", "SAFE"] = "HOT"
    thr: Thresholds = field(default_factory=Thresholds)
    tools: List[str] = field(default_factory=list)
    memory: Dict[str, VoxelRecord] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tools:
            self.tools = list(MODE_TOOLS.get(self.mode, []))

    # -- Zone promotion --

    def can_promote_to_safe(
        self, state: UnitState, quorum_votes: Optional[int] = None
    ) -> bool:
        """
        Check if pad can promote from HOT -> SAFE.

        Requires:
        1. SCBE decision == ALLOW
        2. Optional: >= 4/6 squad quorum
        """Check whether HOT -> SAFE promotion is allowed.

        Requires SCBE decision == ALLOW and optional 4/6 quorum.
        """
        decision = scbe_decide(state.d_star, state.coherence, state.h_eff, self.thr)
        if decision != "ALLOW":
            return False
        if quorum_votes is not None and quorum_votes < 4:
            return False
        return True

    def promote(self, state: UnitState, quorum_votes: Optional[int] = None) -> bool:
        """Attempt to promote HOT -> SAFE. Returns True on success."""
        if not self.can_promote_to_safe(state, quorum_votes):
            return False
        self.zone = "SAFE"
        return True

    def demote(self) -> None:
        """Demote SAFE -> HOT."""
        self.zone = "HOT"

    def route_task(self, task_kind: str = "") -> str:
        """Route task to allowed tools for current mode + zone."""
        return ",".join(f"tools:{t}" for t in self.tools)


# ═══════════════════════════════════════════════════════════════
# Tri-Directional Path Planner
# ═══════════════════════════════════════════════════════════════

# Tongue weights per direction [KO, AV, RU, CA, UM, DR]
DIRECTION_WEIGHTS: Dict[TraceDirection, Tuple[float, ...]] = {
    "STRUCTURE": (0.4, 0.05, 0.05, 0.4, 0.05, 0.05),
    "CONFLICT": (0.05, 0.05, 0.7, 0.05, 0.1, 0.05),
    "TIME": (0.05, 0.3, 0.05, 0.05, 0.25, 0.3),
}

# Standard checkpoints for core function graph
STANDARD_CHECKPOINTS = [
    (0, "INTENT", True),
    (1, "POLICY", True),
    (2, "MEMORY_FETCH", True),
    (3, "PLAN", True),
    (4, "COST_WALL", True),
    (5, "QUORUM", False),
    (6, "EXECUTE", True),
]


@dataclass
class TraceOutput:
    """Result of a single directional trace."""

    direction: TraceDirection
    result: TraceResult
    path: List[int]
    visited_required: List[int]
    missed_required: List[int]
    cost: float
    coherence: float


@dataclass
class TriDirectionalResult:
    """Complete tri-directional planning result."""

    traces: List[TraceOutput]
    triadic_distance: float
    decision: Decision
    valid_count: int
    agreement: float


def triadic_temporal_distance(
    d1: float,
    d2: float,
    d_g: float,
    lambda1: float = 0.3,
    lambda2: float = 0.5,
    lambda3: float = 0.2,
) -> float:
    """
    Compute triadic temporal distance (Layer 11).

    d_tri(t) = (lambda1 * d1^phi + lambda2 * d2^phi + lambda3 * dG^phi)^(1/phi)
    """
    eps = 1e-10
    s = (
        lambda1 * max(d1, eps) ** PHI
        + lambda2 * max(d2, eps) ** PHI
        + lambda3 * max(d_g, eps) ** PHI
    )
    return s ** (1.0 / PHI)


def plan_trace(
    direction: TraceDirection,
    state: Tuple[float, ...],
    d_star: float,
    checkpoints: Optional[List[Tuple[int, str, bool]]] = None,
    max_cost: float = 1e3,
    min_coherence: float = 0.5,
) -> TraceOutput:
    """
    Plan a single directional trace through the core function graph.

    Uses greedy forward traversal with cost accumulation.
    """
    if checkpoints is None:
        checkpoints = STANDARD_CHECKPOINTS

    weights = DIRECTION_WEIGHTS[direction]
    required = {cp[0] for cp in checkpoints if cp[2]}
    path: List[int] = []
    visited_required: List[int] = []
    total_cost = 0.0

    for cp_id, _, is_req in checkpoints:
        # Compute step cost: weighted phase contribution
        step_cost = 0.0
        for i in range(min(6, len(state))):
            step_cost += weights[i] * abs(state[i])
        # Add harmonic cost
        step_cost += harmonic_cost(d_star, 1.0) * 0.001

        total_cost += step_cost
        if total_cost > max_cost:
            break

        path.append(cp_id)
        if is_req:
            visited_required.append(cp_id)

    missed = [r for r in required if r not in visited_required]
    coverage = len(path) / max(len(checkpoints), 1)
    coherence = coverage * 0.7 + 0.3  # Simplified coherence

    if missed:
        result: TraceResult = "BLOCKED"
    elif coherence < min_coherence:
        result = "DEVIATION"
    else:
        result = "VALID"

    return TraceOutput(
        direction=direction,
        result=result,
        path=path,
        visited_required=visited_required,
        missed_required=missed,
        cost=total_cost,
        coherence=coherence,
    )


def plan_tri_directional(
    state: Tuple[float, ...],
    d_star: float,
    checkpoints: Optional[List[Tuple[int, str, bool]]] = None,
) -> TriDirectionalResult:
    """
    Execute tri-directional planning for a core function.

    Three independent traces (Structure, Conflict, Time) are planned.
    Results aggregated via triadic temporal distance (Layer 11).
    Decision emerges from agreement (Layer 13).
    """
    directions: List[TraceDirection] = ["STRUCTURE", "CONFLICT", "TIME"]
    traces = [plan_trace(d, state, d_star, checkpoints) for d in directions]

    triadic_dist = triadic_temporal_distance(
        traces[0].cost, traces[1].cost, traces[2].cost
    )
    valid_count = sum(1 for t in traces if t.result == "VALID")

    # Agreement: average pairwise Jaccard similarity
    total_jaccard = 0.0
    pairs = 0
    for i in range(3):
        for j in range(i + 1, 3):
            set_a = set(traces[i].path)
            set_b = set(traces[j].path)
            union = set_a | set_b
            inter = set_a & set_b
            total_jaccard += len(inter) / max(len(union), 1)
            pairs += 1
    agreement = total_jaccard / max(pairs, 1)

    if valid_count == 3:
        decision: Decision = "ALLOW"
    elif valid_count >= 2 and agreement >= 0.5:
        decision = "QUARANTINE"
    elif valid_count >= 1:
        decision = "QUARANTINE"
    else:
        decision = "DENY"

    return TriDirectionalResult(
        traces=traces,
        triadic_distance=triadic_dist,
        decision=decision,
        valid_count=valid_count,
        agreement=agreement,
    )


# ═══════════════════════════════════════════════════════════════
# CHSFN Primitives (Cymatic-Hyperbolic Semantic Field Network)
# ═══════════════════════════════════════════════════════════════


def cymatic_field_6d(
    x: Tuple[float, ...],
    n: Tuple[int, ...] = (3, 5, 7, 4, 6, 2),
    m: Tuple[int, ...] = (2, 4, 3, 5, 1, 6),
) -> float:
    """
    Compute 6D Chladni-style cymatic field.

    Phi(x) = sum_i cos(pi * n_i * x_i) * prod_{j!=i} sin(pi * m_j * x_j)
    """
    total = 0.0
    for i in range(6):
        cos_val = math.cos(math.pi * n[i] * x[i])
        sin_product = 1.0
        for j in range(6):
            if j != i:
                sin_product *= math.sin(math.pi * m[j] * x[j])
        total += cos_val * sin_product
    return total


def hyperbolic_distance_6d(u: Tuple[float, ...], v: Tuple[float, ...]) -> float:
    """
    Hyperbolic distance in 6D Poincare ball.

    d_H(u,v) = acosh(1 + 2||u-v||^2 / ((1 - ||u||^2)(1 - ||v||^2)))
    """
    eps = 1e-10
    diff_sq = sum((a - b) ** 2 for a, b in zip(u, v))
    u_sq = sum(a * a for a in u)
    v_sq = sum(b * b for b in v)
    denom = (1 - u_sq) * (1 - v_sq)
    if denom <= 0:
        return float("inf")
    arg = 1 + 2 * diff_sq / max(denom, eps)
    return math.acosh(max(arg, 1.0))


def quasi_sphere_volume(radius: float) -> float:
    """Hyperbolic volume in 6D: V(r) ~ e^{5r}."""
    return math.exp(5 * radius)


def access_cost(d_star: float, r: float = 1.5) -> float:
    """Layer-12 access cost: H(d*, R) = R * pi^(phi * d*)."""
    return r * math.pow(math.pi, PHI * d_star)
    # -- Task routing --

    def route_task(
        self,
        task_kind: str,
        state: UnitState,
        squad: SquadSpace,
    ) -> str:
        """Route a task through SCBE governance and mode-specific tooling.

        HOT zone: plan/draft only.  SAFE zone: tool execution allowed.
        """
        if self.zone == "HOT":
            return "HOT: Plan/draft only (no exec)"

        if task_kind not in self.tools:
            return "DENY: Tool not allowed in mode"

        if task_kind == "proximity_track" and self.mode == "NAVIGATION":
            nbrs = squad.neighbors(radius=10.0)
            return f"Neighbors: {nbrs.get(self.unit_id, [])}"

        if task_kind == "ide_draft" and self.mode == "ENGINEERING":
            return "HOT: Code draft generated"

        if task_kind == "code_exec_safe" and self.mode == "ENGINEERING":
            return "SAFE: Exec with security envelope"

        if task_kind == "build_deploy" and self.mode == "ENGINEERING":
            return "SAFE: Build and deploy initiated"

        return "ALLOW: Task routed"

    # -- Per-pad AI assistance --

    def assist(self, query: str, state: UnitState, squad: SquadSpace) -> str:
        """Per-pad AI code assistance (scoped to mode + zone).

        Parses the query, routes subtasks through the pad's toolset,
        and returns a response bounded by SCBE governance.
        """
        q = query.lower()

        if "proximity" in q and self.mode == "NAVIGATION":
            return self.route_task("proximity_track", state, squad)

        if "code" in q and self.mode == "ENGINEERING":
            tool = "ide_draft" if self.zone == "HOT" else "code_exec_safe"
            return self.route_task(tool, state, squad)

        if "build" in q and self.mode == "ENGINEERING":
            return self.route_task("build_deploy", state, squad)

        if "telemetry" in q and self.mode == "SYSTEMS":
            return self.route_task("telemetry_read", state, squad)

        if "hypothesis" in q and self.mode == "SCIENCE":
            return self.route_task("hypothesis_gen", state, squad)

        if "message" in q and self.mode == "COMMS":
            return self.route_task("msg_send", state, squad)

        if "goal" in q and self.mode == "MISSION":
            return self.route_task("goal_set", state, squad)

        # Contextual fallback with squad context
        squad_ctx = next(iter(squad.voxels.values()), None) if squad.voxels else None
        return f"Assist in {self.mode}: {query} (context: {squad_ctx})"
