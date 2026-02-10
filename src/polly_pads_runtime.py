"""
Polly Pads Runtime - Per-Pad AI Code Assistance
================================================

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


# ---------------------------------------------------------------------------
# Deterministic content-addressing
# ---------------------------------------------------------------------------


def cube_id(
    scope: str,
    unit_id: Optional[str],
    squad_id: Optional[str],
    lang: str,
    voxel: Voxel6 | List[float],
    epoch: int,
    pad_mode: str,
) -> str:
    """Deterministic cubeId = sha256(canonical JSON payload)."""
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


# ---------------------------------------------------------------------------
# Unit state and spatial helpers
# ---------------------------------------------------------------------------


@dataclass
class UnitState:
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
                    out[ids[i]].append(ids[j])
                    out[ids[j]].append(ids[i])
        return out

    def quorum_ok(self, votes: int, n: int = 6, threshold: int = 4) -> bool:
        """Byzantine quorum check: n=6 tolerates f=1, needs >=4."""
        return votes >= threshold and n >= 2 * threshold - n

    def commit_voxel(self, record: VoxelRecord, quorum_votes: int) -> bool:
        """Commit a VoxelRecord to shared space if quorum is met."""
        if not self.quorum_ok(quorum_votes):
            return False
        self.voxels[record.cube_id] = record
        return True


# ---------------------------------------------------------------------------
# Polly Pad (per-unit AI workspace)
# ---------------------------------------------------------------------------


@dataclass
class PollyPad:
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
        """Check whether HOT -> SAFE promotion is allowed.

        Requires SCBE decision == ALLOW and optional 4/6 quorum.
        """
        decision = scbe_decide(state.d_star, state.coherence, state.h_eff, self.thr)
        if decision != "ALLOW":
            return False
        if quorum_votes is not None and quorum_votes < 4:
            return False
        return True

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
