"""Polly Pads Runtime — Dual-Zone Squad Workspaces (Python Reference).

Extends Polly Pads into full agent runtimes with:
- Dual code zones (HOT exploratory + SAFE execution)
- Squad code space (shared, quorum-gated memory)
- Proximity tracking (Euclidean + geodesic)
- Per-pad tool gating by mode + zone
- SCBE decision gating for zone promotion
- Tri-directional Hamiltonian path validation
- Per-pad AI code assistance

Each Polly Pad is a namespaced agent workspace with:
- Mode-specific toolsets (ENGINEERING, NAVIGATION, SYSTEMS, SCIENCE, COMMS, MISSION)
- Dual code zones: HOT (draft/plan only) and SAFE (execution, requires quorum)
- Squad code space with Byzantine 4/6 quorum for shared voxel commits
- Proximity tracking via 3D Euclidean distance
- SCBE three-tier governance: ALLOW / QUARANTINE / DENY

Integration points:
- Layer 8: PHDM polyhedra validation
- Layer 12: Harmonic wall cost (h_eff) drives SCBE decision
- Layer 13: Risk decision tier (ALLOW/QUARANTINE/DENY)
- Sacred Tongues: Voxel addressing uses lang dimension
- VoxelRecord: Canonical payload envelope at 6D address

@module polly_pads_runtime
@layer Layer 8, Layer 12, Layer 13
@version 3.3.0
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

PadMode = Literal["ENGINEERING", "NAVIGATION", "SYSTEMS", "SCIENCE", "COMMS", "MISSION"]
Decision = Literal["ALLOW", "QUARANTINE", "DENY"]
CodeZone = Literal["HOT", "SAFE"]
Lang = Literal["KO", "AV", "RU", "CA", "UM", "DR"]
TraceDirection = Literal["STRUCTURE", "CONFLICT", "TIME"]
TraceResult = Literal["VALID", "DEVIATION", "BLOCKED"]
Voxel6 = Tuple[float, float, float, float, float, float]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAD_MODES: Tuple[PadMode, ...] = (
    "ENGINEERING",
    "NAVIGATION",
    "SYSTEMS",
    "SCIENCE",
    "COMMS",
    "MISSION",
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

MODE_TOOLS: Dict[PadMode, List[str]] = {
    "ENGINEERING": ["ide_draft", "code_exec_safe", "build_deploy"],
    "NAVIGATION": ["map_query", "proximity_track", "path_plan"],
    "SYSTEMS": ["telemetry_read", "config_set", "policy_enforce"],
    "SCIENCE": ["hypothesis_gen", "experiment_run", "model_tune"],
    "COMMS": ["msg_send", "negotiate", "protocol_exec"],
    "MISSION": ["goal_set", "constraint_check", "orchestrate_squad"],
}

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

PHI: float = (1 + math.sqrt(5)) / 2
"""Golden ratio constant used throughout the SCBE architecture."""


# ---------------------------------------------------------------------------
# SCBE governance (Layer 12 + 13)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Thresholds:
    """SCBE Layer-12/13 decision thresholds for risk governance."""

    """SCBE governance thresholds for risk decision."""

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
    """Compute three-tier SCBE risk decision (Layer 13).

    Decision hierarchy:
        DENY if coherence < quarantine_min OR h_eff > quarantine_max
            OR d_star > quarantine_max
        ALLOW if coherence >= allow_min AND h_eff <= allow_max
            AND d_star <= allow_max
        QUARANTINE otherwise

    Args:
        d_star: Hyperbolic drift from safe centre.
        coherence: NK coherence score in [0, 1].
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
    if coherence >= thr.allow_min_coherence and h_eff <= thr.allow_max_cost and d_star <= thr.allow_max_drift:
        return "ALLOW"
    return "QUARANTINE"


def harmonic_cost(d_star: float, r: float = 1.5) -> float:
    """Compute effective harmonic cost H(d*, R) = R * pi^(phi * d*).

    This is the Layer-12 event horizon cost function.

    Args:
        d_star: Hyperbolic drift distance.
        r: Base radial factor (default 1.5, the perfect fifth).

    Returns:
        Effective harmonic cost.
    """
    return r * math.pow(math.pi, PHI * d_star)


# ---------------------------------------------------------------------------
# CubeId & digest
# ---------------------------------------------------------------------------


def cube_id(
    scope: str,
    unit_id: str,
    pad_mode: PadMode,
    epoch: int,
    lang: str,
    voxel: List[int],
    squad_id: Optional[str] = None,
) -> str:
    """Compute deterministic CubeId from addressing fields via canonical JSON.

    Args:
        scope: Voxel scope ('unit' or 'squad').
        unit_id: Owning unit identifier.
        pad_mode: Active pad mode.
        epoch: Temporal epoch counter.
        lang: Sacred Tongue identifier.
        voxel: 6D voxel coordinates.
        squad_id: Optional squad identifier.

    Returns:
        SHA-256 hex digest of the canonical payload.
    """
    payload = {
        "epoch": int(epoch),
        "lang": lang,
        "pad_mode": pad_mode,
        "scope": scope,
        "squad_id": squad_id,
        "unit_id": unit_id,
        "voxel": list(voxel),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def pad_namespace_key(unit_id: str, pad_mode: PadMode, lang: Lang, epoch: int) -> str:
    """Generate voxel namespace key for a pad's memory.

    Args:
        unit_id: Owning unit identifier.
        pad_mode: Active pad mode.
        lang: Sacred Tongue identifier.
        epoch: Temporal epoch counter.

    Returns:
        Colon-separated namespace key string.
    """
    return f"{unit_id}:{pad_mode}:{lang}:{epoch}"


# ---------------------------------------------------------------------------
# Unit state and spatial helpers
# ---------------------------------------------------------------------------


@dataclass
class UnitState:
    """Position and governance snapshot for a single unit/drone."""

    """Physical + governance state of a single unit/drone."""

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
    """Euclidean distance between two units in 3D space.

    Args:
        a: First unit state.
        b: Second unit state.

    Returns:
        Euclidean distance.
    """
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


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
# ═══════════════════════════════════════════════════════════════
# Squad Space
# ═══════════════════════════════════════════════════════════════


@dataclass
class SquadSpace:
    """Shared code space for a squad of units.

    Provides proximity tracking, Byzantine quorum validation,
    and voxel memory. Writes require quorum (>=4/6).
    """

    squad_id: str
    units: Dict[str, UnitState] = field(default_factory=dict)
    voxels: Dict[str, VoxelRecord] = field(default_factory=dict)

    def neighbors(self, radius: float) -> Dict[str, List[str]]:
        """Find neighbour pairs within *radius* Euclidean distance.

        Args:
            radius: Maximum distance for neighbour inclusion.

        Returns:
            Mapping from unit_id to list of neighbour unit_ids.
        """
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
        """Check Byzantine quorum: n=6, f=1, threshold=4 (BFT: 3f+1).

        Args:
            votes: Number of affirmative votes received.
            n: Total number of voting nodes.
            threshold: Minimum votes required.

        Returns:
            True if quorum is satisfied.
        """
        f = (n - 1) // 3
        return votes >= threshold and n >= 3 * f + 1 and threshold >= 2 * f + 1

    def commit_voxel(self, record: VoxelRecord, quorum_votes: int = 0) -> bool:
        """Commit a voxel record to squad memory if quorum is met.

        Args:
            record: Voxel record to commit.
            quorum_votes: Number of squad votes for this commit.

        Returns:
            True if commit succeeded (quorum met), False otherwise.
        """
        if not self.quorum_ok(quorum_votes):
            return False
        self.voxels[record.cube_id] = record
        return True

    def find_leader(self) -> Optional[str]:
        """Find consensus leader: lowest h_eff + highest coherence.

        Returns:
            Unit ID of the leader, or None if squad is empty.
        """
        best_id: Optional[str] = None
        best_score = float("inf")
        for uid, state in self.units.items():
            score = state.h_eff - state.coherence * 1000
            if score < best_score:
                best_score = score
                best_id = uid
        return best_id

    def average_coherence(self) -> float:
        """Average coherence across all units.

        Returns:
            Mean coherence, or 0.0 if squad is empty.
        """
        if not self.units:
            return 0.0
        return sum(s.coherence for s in self.units.values()) / len(self.units)

    def risk_field(self, thr: Thresholds = Thresholds()) -> Dict[str, Decision]:
        """Compute SCBE decision for each unit.

        Args:
            thr: Decision thresholds.

        Returns:
            Mapping from unit_id to SCBE decision.
        """
        return {uid: scbe_decide(s.d_star, s.coherence, s.h_eff, thr) for uid, s in self.units.items()}


# ---------------------------------------------------------------------------
# Polly Pad (per-unit AI workspace with dual zones)
# ---------------------------------------------------------------------------


@dataclass
class PollyPad:
    """Personal AI workspace with mode-specific tools, dual zones, and assist().

    Each pad provides:
    - Scoped toolset determined by *mode* and *zone*
    - Dual code zones: HOT (draft only) / SAFE (exec, needs quorum)
    - ``assist()`` method for per-pad AI code assistance
    - Local voxel memory namespace
    """

    unit_id: str
    mode: PadMode
    zone: CodeZone = "HOT"
    thr: Thresholds = field(default_factory=Thresholds)
    memory: Dict[str, VoxelRecord] = field(default_factory=dict)

    @property
    def tongue(self) -> Lang:
        """Sacred Tongue for this pad's namespace."""
        return PAD_MODE_TONGUE[self.mode]

    @property
    def tools(self) -> Tuple[str, ...]:
        """Currently available tools based on mode and active zone."""
        return PAD_TOOL_MATRIX[self.mode][self.zone]

    @property
    def all_mode_tools(self) -> List[str]:
        """All tools available for this pad's mode (zone-independent)."""
        return list(MODE_TOOLS.get(self.mode, []))

    # -- Zone promotion --

    def can_promote_to_safe(self, state: UnitState, quorum_votes: Optional[int] = None) -> bool:
        """Check whether HOT -> SAFE promotion is allowed.

        Requires SCBE decision == ALLOW and optional 4/6 quorum.

        Args:
            state: Current unit governance state.
            quorum_votes: Optional quorum vote count.

        Returns:
            True if promotion is permitted.
        """
        decision = scbe_decide(state.d_star, state.coherence, state.h_eff, self.thr)
        if decision != "ALLOW":
            return False
        if quorum_votes is not None and quorum_votes < 4:
            return False
        return True

    def promote(self, state: UnitState, quorum_votes: Optional[int] = None) -> bool:
        """Attempt to promote HOT -> SAFE.

        Args:
            state: Current unit governance state.
            quorum_votes: Optional quorum vote count.

        Returns:
            True on success, False if promotion denied.
        """
        if not self.can_promote_to_safe(state, quorum_votes):
            return False
        self.zone = "SAFE"
        return True

    def demote(self) -> None:
        """Demote SAFE -> HOT."""
        self.zone = "HOT"

    # -- Task routing --

    def route_task(
        self,
        task_kind: str = "",
        state: Optional[UnitState] = None,
        squad: Optional[SquadSpace] = None,
    ) -> str:
        """Route a task through SCBE governance and mode-specific tooling.

        HOT zone returns plan/draft only. SAFE zone allows tool execution.
        When called without state/squad, returns a simple tool list.

        Args:
            task_kind: Requested task/tool identifier.
            state: Optional unit state for contextual routing.
            squad: Optional squad space for proximity queries.

        Returns:
            Routing result string.
        """
        if self.zone == "HOT":
            if state is not None:
                return "HOT: Plan/draft only (no exec)"
            return ",".join(f"tools:{t}" for t in self.tools)

        if state is not None and squad is not None:
            if task_kind not in self.all_mode_tools:
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

        return ",".join(f"tools:{t}" for t in self.tools)

    # -- Per-pad AI assistance --

    def assist(self, query: str, state: UnitState, squad: SquadSpace) -> str:
        """Per-pad AI code assistance scoped to mode and zone.

        Parses the query, routes subtasks through the pad's toolset,
        and returns a response bounded by SCBE governance.

        Args:
            query: Natural language query string.
            state: Current unit governance state.
            squad: Squad space for contextual lookup.

        Returns:
            Assistance response string.
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

        squad_ctx = next(iter(squad.voxels.values()), None) if squad.voxels else None
        return f"Assist in {self.mode}: {query} (context: {squad_ctx})"


# ---------------------------------------------------------------------------
# Tri-directional path planner (Layer 11)
# ---------------------------------------------------------------------------

DIRECTION_WEIGHTS: Dict[TraceDirection, Tuple[float, ...]] = {
    "STRUCTURE": (0.4, 0.05, 0.05, 0.4, 0.05, 0.05),
    "CONFLICT": (0.05, 0.05, 0.7, 0.05, 0.1, 0.05),
    "TIME": (0.05, 0.3, 0.05, 0.05, 0.25, 0.3),
}

STANDARD_CHECKPOINTS: List[Tuple[int, str, bool]] = [
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
    """Compute triadic temporal distance (Layer 11).

    Formula: d_tri(t) = (l1*d1^phi + l2*d2^phi + l3*dG^phi)^(1/phi)

    Args:
        d1: First directional distance.
        d2: Second directional distance.
        d_g: Geodesic (third) directional distance.
        lambda1: Weight for first direction.
        lambda2: Weight for second direction.
        lambda3: Weight for third direction.

    Returns:
        Triadic temporal distance.
    """
    eps = 1e-10
    s = lambda1 * max(d1, eps) ** PHI + lambda2 * max(d2, eps) ** PHI + lambda3 * max(d_g, eps) ** PHI
    return s ** (1.0 / PHI)


def plan_trace(
    direction: TraceDirection,
    state: Tuple[float, ...],
    d_star: float,
    checkpoints: Optional[List[Tuple[int, str, bool]]] = None,
    max_cost: float = 1e3,
    min_coherence: float = 0.5,
) -> TraceOutput:
    """Plan a single directional trace through the core function graph.

    Uses greedy forward traversal with cost accumulation.

    Args:
        direction: Trace direction (STRUCTURE, CONFLICT, or TIME).
        state: 6D state tuple.
        d_star: Hyperbolic drift distance.
        checkpoints: Ordered list of (id, name, required) checkpoints.
        max_cost: Maximum allowable trace cost.
        min_coherence: Minimum coherence threshold.

    Returns:
        TraceOutput with path, cost, and result.
    """
    if checkpoints is None:
        checkpoints = STANDARD_CHECKPOINTS

    weights = DIRECTION_WEIGHTS[direction]
    required = {cp[0] for cp in checkpoints if cp[2]}
    path: List[int] = []
    visited_required: List[int] = []
    total_cost = 0.0

    for cp_id, _, is_req in checkpoints:
        step_cost = 0.0
        for i in range(min(6, len(state))):
            step_cost += weights[i] * abs(state[i])
        step_cost += harmonic_cost(d_star, 1.0) * 0.001

        total_cost += step_cost
        if total_cost > max_cost:
            break

        path.append(cp_id)
        if is_req:
            visited_required.append(cp_id)

    missed = [r for r in required if r not in visited_required]
    coverage = len(path) / max(len(checkpoints), 1)
    coherence = coverage * 0.7 + 0.3

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
    """Execute tri-directional planning for a core function.

    Three independent traces (Structure, Conflict, Time) are planned.
    Results are aggregated via triadic temporal distance (Layer 11).
    Decision emerges from agreement count (Layer 13).

    Args:
        state: 6D state tuple.
        d_star: Hyperbolic drift distance.
        checkpoints: Optional custom checkpoint list.

    Returns:
        TriDirectionalResult with traces, distance, and decision.
    """
    directions: List[TraceDirection] = ["STRUCTURE", "CONFLICT", "TIME"]
    traces = [plan_trace(d, state, d_star, checkpoints) for d in directions]

    triadic_dist = triadic_temporal_distance(traces[0].cost, traces[1].cost, traces[2].cost)
    valid_count = sum(1 for t in traces if t.result == "VALID")

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


# ---------------------------------------------------------------------------
# CHSFN Primitives (Cymatic-Hyperbolic Semantic Field Network)
# ---------------------------------------------------------------------------


def cymatic_field_6d(
    x: Tuple[float, ...],
    n: Tuple[int, ...] = (3, 5, 7, 4, 6, 2),
    m: Tuple[int, ...] = (2, 4, 3, 5, 1, 6),
) -> float:
    """Compute 6D Chladni-style cymatic field.

    Phi(x) = sum_i cos(pi * n_i * x_i) * prod_{j!=i} sin(pi * m_j * x_j)

    Args:
        x: 6D coordinate tuple.
        n: Cosine mode numbers per dimension.
        m: Sine mode numbers per dimension.

    Returns:
        Scalar field value.
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
    """Hyperbolic distance in 6D Poincare ball.

    d_H(u,v) = acosh(1 + 2||u-v||^2 / ((1 - ||u||^2)(1 - ||v||^2)))

    Args:
        u: First point in the Poincare ball.
        v: Second point in the Poincare ball.

    Returns:
        Hyperbolic distance, or inf if outside the ball.
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
    """Hyperbolic volume approximation in 6D: V(r) ~ e^{5r}.

    Args:
        radius: Hyperbolic radius.

    Returns:
        Approximate volume.
    """
    return math.exp(5 * radius)


def access_cost(d_star: float, r: float = 1.5) -> float:
    """Layer-12 access cost: H(d*, R) = R * pi^(phi * d*).

    Args:
        d_star: Hyperbolic drift distance.
        r: Base radial factor.

    Returns:
        Access cost value.
    """
    return r * math.pow(math.pi, PHI * d_star)
