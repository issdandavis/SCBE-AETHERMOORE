"""GeoSeal Operator System-Space Model (Python reference implementation).

Extends GeoSeal's geographic ring model to cover the operator's position in
**system topology space** — not physical coordinates, but the structural
location of the operator: which access plane they arrived through (web /
terminal / app / API) and whether they are authenticated.

The access plane + auth state together determine:
  - A file-system topology (what paths are reachable and writable)
  - A governance ring (core / outer / restricted / blocked)
  - A deterministic space ID analogous to the geographic geoid
  - Governance flags that surface cross-plane claims and auth anomalies

Why this matters:
  A web-anonymous operator claiming /home/user/documents is structurally
  impossible — their sandbox grants no native FS at all. The governance layer
  should catch the claim before it reaches the FS.  Similarly, a terminal+sudo
  operator carries elevated risk that warrants its own flag even at high trust.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

# ---------------------------------------------------------------------------
# Types / enumerations
# ---------------------------------------------------------------------------

AccessPlane = Literal["web", "terminal", "app", "api"]
AuthState = Literal["authenticated", "anonymous", "service_account", "sudo"]
SandboxLevel = Literal["none", "partial", "full"]
OperatorRing = Literal["core", "outer", "restricted", "blocked"]
GovernanceTier = Literal["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]

GOVERNANCE_FLAGS = {
    "ELEVATED_TERMINAL",
    "UNAUTHENTICATED_WEB",
    "UNAUTHENTICATED_API",
    "CROSS_PLANE_CLAIM",
    "SESSION_MISSING_LOGIN_TIME",
    "TEMP_FS_ONLY",
    "SERVICE_ACCOUNT_ELEVATED",
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FsTopology:
    """File-system access topology for an operator's plane + auth combination."""

    sandbox_level: SandboxLevel
    accessible_roots: List[str]
    writable_paths: List[str]
    persists_across_sessions: bool
    temp_only: bool
    mount_points: List[str]


@dataclass(frozen=True)
class OperatorSpaceInput:
    """Input to the operator space evaluator."""

    access_plane: AccessPlane
    auth_state: AuthState
    session_fingerprint: Optional[str] = None
    login_time_ms: Optional[int] = None
    claimed_paths: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class OperatorSpaceDecision:
    """Governance decision for an operator's system-space position."""

    ring: OperatorRing
    trust_score: float
    space_id: str
    fs_topology: FsTopology
    governance_flags: List[str]
    status: str
    reason: str


# ---------------------------------------------------------------------------
# FS topology derivation
# ---------------------------------------------------------------------------

_FS_TOPOLOGY: dict[tuple[AccessPlane, AuthState], FsTopology] = {
    # --- web ---
    ("web", "anonymous"): FsTopology(
        sandbox_level="full",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=False,
        temp_only=True,
        mount_points=[],
    ),
    ("web", "authenticated"): FsTopology(
        sandbox_level="full",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=[],
    ),
    ("web", "service_account"): FsTopology(
        sandbox_level="full",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=[],
    ),
    ("web", "sudo"): FsTopology(
        sandbox_level="full",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=[],
    ),
    # --- terminal ---
    ("terminal", "sudo"): FsTopology(
        sandbox_level="none",
        accessible_roots=["/", "C:\\"],
        writable_paths=["/", "C:\\"],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=["/", "/proc", "/sys", "/dev", "C:\\", "D:\\"],
    ),
    ("terminal", "authenticated"): FsTopology(
        sandbox_level="none",
        accessible_roots=["~", "/home", "/var", "/tmp", "C:\\Users", "C:\\ProgramData"],
        writable_paths=["~", "/tmp", "C:\\Users\\{user}", "C:\\Temp"],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=["/", "C:\\", "D:\\"],
    ),
    ("terminal", "service_account"): FsTopology(
        sandbox_level="none",
        accessible_roots=["~", "/home", "/var", "/tmp", "C:\\Users", "C:\\ProgramData"],
        writable_paths=["~", "/tmp", "C:\\Users\\{user}", "C:\\Temp"],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=["/", "C:\\", "D:\\"],
    ),
    ("terminal", "anonymous"): FsTopology(
        sandbox_level="partial",
        accessible_roots=["/tmp", "C:\\Temp"],
        writable_paths=["/tmp", "C:\\Temp"],
        persists_across_sessions=False,
        temp_only=True,
        mount_points=[],
    ),
    # --- app ---
    ("app", "authenticated"): FsTopology(
        sandbox_level="partial",
        accessible_roots=["~/AppData", "~/.local/share", "~/Library/Application Support"],
        writable_paths=["~/AppData/{app}", "~/.local/share/{app}"],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=[],
    ),
    ("app", "service_account"): FsTopology(
        sandbox_level="partial",
        accessible_roots=["~/AppData", "~/.local/share", "~/Library/Application Support"],
        writable_paths=["~/AppData/{app}", "~/.local/share/{app}"],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=[],
    ),
    ("app", "anonymous"): FsTopology(
        sandbox_level="partial",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=False,
        temp_only=True,
        mount_points=[],
    ),
    ("app", "sudo"): FsTopology(
        sandbox_level="partial",
        accessible_roots=["~/AppData", "~/.local/share", "~/Library/Application Support"],
        writable_paths=["~/AppData/{app}", "~/.local/share/{app}"],
        persists_across_sessions=True,
        temp_only=False,
        mount_points=[],
    ),
    # --- api ---
    ("api", "service_account"): FsTopology(
        sandbox_level="partial",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=False,
        temp_only=True,
        mount_points=[],
    ),
    ("api", "authenticated"): FsTopology(
        sandbox_level="partial",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=False,
        temp_only=True,
        mount_points=[],
    ),
    ("api", "anonymous"): FsTopology(
        sandbox_level="full",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=False,
        temp_only=True,
        mount_points=[],
    ),
    ("api", "sudo"): FsTopology(
        sandbox_level="partial",
        accessible_roots=[],
        writable_paths=[],
        persists_across_sessions=False,
        temp_only=True,
        mount_points=[],
    ),
}


def derive_fs_topology(plane: AccessPlane, auth: AuthState) -> FsTopology:
    """Return the FS topology for a given plane + auth combination."""
    return _FS_TOPOLOGY[(plane, auth)]


# ---------------------------------------------------------------------------
# Ring + trust lookup
# ---------------------------------------------------------------------------

_RING_TABLE: dict[tuple[AccessPlane, AuthState], tuple[OperatorRing, float]] = {
    ("terminal", "sudo"): ("core", 0.95),
    ("terminal", "authenticated"): ("core", 0.85),
    ("terminal", "service_account"): ("core", 0.80),
    ("terminal", "anonymous"): ("restricted", 0.35),
    ("app", "authenticated"): ("outer", 0.70),
    ("app", "service_account"): ("outer", 0.65),
    ("app", "anonymous"): ("restricted", 0.25),
    ("app", "sudo"): ("outer", 0.70),
    ("api", "service_account"): ("core", 0.80),
    ("api", "authenticated"): ("outer", 0.70),
    ("api", "anonymous"): ("blocked", 0.05),
    ("api", "sudo"): ("outer", 0.70),
    ("web", "authenticated"): ("outer", 0.60),
    ("web", "anonymous"): ("blocked", 0.05),
    ("web", "service_account"): ("outer", 0.55),
    ("web", "sudo"): ("outer", 0.60),
}


# ---------------------------------------------------------------------------
# Space ID
# ---------------------------------------------------------------------------

_WEB_NATIVE_PATH = re.compile(r"^[/\\]|^[A-Za-z]:\\")
_URL = re.compile(r"^https?://", re.IGNORECASE)
_UNC = re.compile(r"^\\\\")


def _derive_space_id(plane: AccessPlane, auth: AuthState, fingerprint: str) -> str:
    payload = f"{plane}|{auth}|{fingerprint}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Cross-plane claim validation
# ---------------------------------------------------------------------------


def _is_path_cross_plane(path: str, plane: AccessPlane) -> bool:
    if plane == "web":
        return bool(_WEB_NATIVE_PATH.match(path) or _UNC.match(path))
    if plane == "api":
        return True  # API callers have no direct FS
    # terminal / app
    return bool(_URL.match(path))


# ---------------------------------------------------------------------------
# Flag evaluation
# ---------------------------------------------------------------------------


def _evaluate_flags(
    plane: AccessPlane,
    auth: AuthState,
    fs_topology: FsTopology,
    claimed_paths: List[str],
    login_time_ms: Optional[int],
) -> List[str]:
    flags: List[str] = []

    if plane == "terminal" and auth == "sudo":
        flags.append("ELEVATED_TERMINAL")
    if plane == "terminal" and auth == "service_account":
        flags.append("SERVICE_ACCOUNT_ELEVATED")
    if plane == "web" and auth == "anonymous":
        flags.append("UNAUTHENTICATED_WEB")
    if plane == "api" and auth == "anonymous":
        flags.append("UNAUTHENTICATED_API")
    if fs_topology.temp_only:
        flags.append("TEMP_FS_ONLY")
    if auth in ("authenticated", "sudo") and login_time_ms is None:
        flags.append("SESSION_MISSING_LOGIN_TIME")

    if any(_is_path_cross_plane(p, plane) for p in claimed_paths):
        flags.append("CROSS_PLANE_CLAIM")

    return flags


# ---------------------------------------------------------------------------
# Primary evaluator
# ---------------------------------------------------------------------------


def evaluate_operator_space(inp: OperatorSpaceInput) -> OperatorSpaceDecision:
    """Evaluate an operator's system-space position and return a governance decision.

    The decision integrates with GeoSeal's ring model: ``ring`` maps directly
    to the same ALLOW/QUARANTINE/ESCALATE/DENY tier thresholds used in L13.

    Examples::

        decision = evaluate_operator_space(OperatorSpaceInput(
            access_plane="terminal",
            auth_state="authenticated",
            session_fingerprint="sess-uuid-123",
            login_time_ms=1716000000000,
            claimed_paths=["/home/user/docs"],
        ))
        assert decision.ring == "core"
        assert decision.trust_score == 0.85
    """
    plane = inp.access_plane
    auth = inp.auth_state
    fingerprint = inp.session_fingerprint or f"{plane}:{auth}:anon"

    space_id = _derive_space_id(plane, auth, fingerprint)
    fs_topology = derive_fs_topology(plane, auth)
    ring, trust_score = _RING_TABLE[(plane, auth)]

    flags = _evaluate_flags(plane, auth, fs_topology, inp.claimed_paths, inp.login_time_ms)

    # Penalise trust for violations
    effective_trust = trust_score
    if "CROSS_PLANE_CLAIM" in flags:
        effective_trust = max(0.0, effective_trust - 0.30)
    if "SESSION_MISSING_LOGIN_TIME" in flags:
        effective_trust = max(0.0, effective_trust - 0.15)

    if effective_trust < 0.1:
        effective_ring: OperatorRing = "blocked"
    elif effective_trust <= 0.4:
        effective_ring = "restricted"
    else:
        effective_ring = ring  # type: ignore[assignment]

    status = f"operator_space_{plane}_{auth}"
    flag_str = f" flags=[{','.join(flags)}]" if flags else ""
    reason = f"plane={plane} auth={auth} sandbox={fs_topology.sandbox_level}{flag_str}"

    return OperatorSpaceDecision(
        ring=effective_ring,
        trust_score=round(effective_trust, 4),
        space_id=space_id,
        fs_topology=fs_topology,
        governance_flags=flags,
        status=status,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ring_to_governance_tier(ring: OperatorRing) -> GovernanceTier:
    """Map an OperatorRing to the L13 governance tier vocabulary."""
    mapping: dict[OperatorRing, GovernanceTier] = {
        "core": "ALLOW",
        "outer": "QUARANTINE",
        "restricted": "ESCALATE",
        "blocked": "DENY",
    }
    return mapping[ring]


def decision_to_metadata(decision: OperatorSpaceDecision) -> dict:
    """Convert a decision to a JSON-friendly plain dict (receipt format)."""
    return {
        "ring": decision.ring,
        "trust_score": decision.trust_score,
        "space_id": decision.space_id,
        "sandbox_level": decision.fs_topology.sandbox_level,
        "accessible_roots": decision.fs_topology.accessible_roots,
        "writable_paths": decision.fs_topology.writable_paths,
        "persists_across_sessions": decision.fs_topology.persists_across_sessions,
        "temp_only": decision.fs_topology.temp_only,
        "mount_points": decision.fs_topology.mount_points,
        "governance_flags": decision.governance_flags,
        "status": decision.status,
        "reason": decision.reason,
    }
