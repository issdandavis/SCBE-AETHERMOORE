"""
SCBE-AETHERMOORE Canonical 21D State Vector — v1 Reference Implementation.

Schema: state21_v1 (fixed named slots, versioned)
Layout:
    Block A — Tongue Position (hyperbolic): s[0:6]  u in B^6_c
    Block B — Tongue Phase (toroidal):      s[6:12] theta in T^6
    Block C — Governance Telemetry (mixed):  s[12:19]
    Block D — Derived Cache:                 s[19:21]

Product metric on M = B^6 x T^6 x R^9:
    ds^2 = w_h * d_hyp(u_a, u_b)^2
         + w_t * d_torus(theta_a, theta_b)^2
         + (z_a - z_b)^T W_z (z_a - z_b)

@module harmonic/canonical_state
@layer Layer 1-14 (Unified)
@version 1.0.0
@since 2026-02-23
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# ═══════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════

STATE21_DIM = 21
SCHEMA_VERSION = "state21_v1"

# Block boundaries (0-indexed, half-open)
TONGUE_POS_SLICE = slice(0, 6)     # Block A
TONGUE_PHASE_SLICE = slice(6, 12)  # Block B
TELEMETRY_SLICE = slice(12, 19)    # Block C
DERIVED_SLICE = slice(19, 21)      # Block D

TELEMETRY_DIM = 7
DERIVED_DIM = 2

# Slot names for Block C telemetry
TELEMETRY_SLOTS = [
    "flux_participation",      # [12]
    "coherence_spectral",      # [13]
    "coherence_spin",          # [14]
    "coherence_triadic",       # [15]
    "risk_aggregate",          # [16]
    "entropy_density",         # [17]
    "stabilization",           # [18]
]

# Slot names for Block D derived cache
DERIVED_SLOTS = [
    "radial_norm",             # [19]  ||u||
    "energy_harmonic",         # [20]  H(6, R) = R^(d^2), d=6
]

ALL_SLOT_NAMES = (
    ["u_ko", "u_av", "u_ru", "u_ca", "u_um", "u_dr"]
    + ["theta_ko", "theta_av", "theta_ru", "theta_ca", "theta_um", "theta_dr"]
    + TELEMETRY_SLOTS
    + DERIVED_SLOTS
)

# Default telemetry weights for product metric
# Last 2 (derived cache) get zero weight to avoid double-counting geometry.
DEFAULT_TELEMETRY_WEIGHTS = [1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.5, 0.0, 0.0]


# ═══════════════════════════════════════════════════════════════
# Errors
# ═══════════════════════════════════════════════════════════════

class CanonicalStateError(ValueError):
    """Raised when a canonical state fails validation."""
    pass


# ═══════════════════════════════════════════════════════════════
# Core dataclass
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CanonicalState:
    """Immutable 21D canonical state vector (state21_v1).

    Enforces:
      - Exact 21D dimensionality
      - Tongue position inside Poincare ball (||u|| < 1)
      - Telemetry range constraints
      - Derived cache consistency
    """
    vec: List[float]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        if len(self.vec) != STATE21_DIM:
            raise CanonicalStateError(
                f"Expected {STATE21_DIM}D vector, got {len(self.vec)}D"
            )

    # ─── Block accessors ──────────────────────────────────────

    @property
    def u(self) -> List[float]:
        """Tongue position in Poincare ball B^6."""
        return self.vec[TONGUE_POS_SLICE]

    @property
    def theta(self) -> List[float]:
        """Tongue phase angles on T^6."""
        return self.vec[TONGUE_PHASE_SLICE]

    @property
    def telemetry(self) -> List[float]:
        """Governance telemetry (7 channels)."""
        return self.vec[TELEMETRY_SLICE]

    # ─── Named telemetry fields ───────────────────────────────

    @property
    def flux_participation(self) -> float:
        return self.vec[12]

    @property
    def coherence_spectral(self) -> float:
        return self.vec[13]

    @property
    def coherence_spin(self) -> float:
        return self.vec[14]

    @property
    def coherence_triadic(self) -> float:
        return self.vec[15]

    @property
    def risk_aggregate(self) -> float:
        return self.vec[16]

    @property
    def entropy_density(self) -> float:
        return self.vec[17]

    @property
    def stabilization(self) -> float:
        return self.vec[18]

    @property
    def radial_norm(self) -> float:
        """Cached ||u|| (derived from Block A)."""
        return self.vec[19]

    @property
    def energy_harmonic(self) -> float:
        """Cached H(6, R) (derived from Block A)."""
        return self.vec[20]

    # ─── Computed helpers ─────────────────────────────────────

    def u_norm(self) -> float:
        """Compute ||u|| from tongue position."""
        return math.sqrt(sum(x * x for x in self.u))

    def hash(self) -> str:
        """SHA-256 content hash (first 16 hex chars)."""
        raw = json.dumps(self.vec, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def to_dict(self) -> Dict[str, float]:
        """Named dict of all 21 slots."""
        return dict(zip(ALL_SLOT_NAMES, self.vec))

    # ─── Validation ───────────────────────────────────────────

    def validate(self, eps: float = 1e-6) -> Dict[str, float]:
        """Validate state against canonical constraints.

        Returns diagnostics dict. Raises CanonicalStateError on hard failures.
        """
        r = self.u_norm()

        # A4: Poincare ball containment
        if r >= 1.0:
            raise CanonicalStateError(
                f"Tongue position outside Poincare ball: ||u|| = {r:.8f} >= 1"
            )

        # Coherence channels in [0, 1]
        for name, idx in [
            ("coherence_spectral", 13),
            ("coherence_spin", 14),
            ("coherence_triadic", 15),
        ]:
            v = self.vec[idx]
            if v < -eps or v > 1.0 + eps:
                raise CanonicalStateError(f"{name} = {v:.6f} outside [0, 1]")

        # Risk in [0, 1]
        if self.risk_aggregate < -eps or self.risk_aggregate > 1.0 + eps:
            raise CanonicalStateError(
                f"risk_aggregate = {self.risk_aggregate:.6f} outside [0, 1]"
            )

        # Non-negative telemetry channels
        if self.entropy_density < -eps:
            raise CanonicalStateError(f"entropy_density = {self.entropy_density:.6f} < 0")
        if self.stabilization < -eps:
            raise CanonicalStateError(f"stabilization = {self.stabilization:.6f} < 0")
        if self.flux_participation < -eps:
            raise CanonicalStateError(f"flux_participation = {self.flux_participation:.6f} < 0")

        # Derived cache consistency
        expected_radial = r
        expected_energy = _compute_energy_harmonic(r)

        radial_err = abs(self.radial_norm - expected_radial)
        energy_err = abs(self.energy_harmonic - expected_energy)

        return {
            "u_norm": r,
            "radial_abs_err": radial_err,
            "energy_abs_err": energy_err,
        }


# ═══════════════════════════════════════════════════════════════
# Constructors
# ═══════════════════════════════════════════════════════════════

def build_canonical_state(
    u: Sequence[float],
    theta: Sequence[float],
    flux_participation: float = 0.0,
    coherence_spectral: float = 0.0,
    coherence_spin: float = 0.0,
    coherence_triadic: float = 0.0,
    risk_aggregate: float = 0.0,
    entropy_density: float = 0.0,
    stabilization: float = 0.0,
) -> CanonicalState:
    """Build a CanonicalState from components, auto-computing derived cache."""
    if len(u) != 6:
        raise CanonicalStateError(f"Tongue position must be 6D, got {len(u)}D")
    if len(theta) != 6:
        raise CanonicalStateError(f"Tongue phase must be 6D, got {len(theta)}D")

    r = math.sqrt(sum(x * x for x in u))
    energy = _compute_energy_harmonic(r)

    vec = list(u) + list(theta) + [
        flux_participation,
        coherence_spectral,
        coherence_spin,
        coherence_triadic,
        risk_aggregate,
        entropy_density,
        stabilization,
        r,        # radial_norm (derived)
        energy,   # energy_harmonic (derived)
    ]
    return CanonicalState(vec=vec)


def safe_origin() -> CanonicalState:
    """The canonical safe origin — center of manifold, zero risk."""
    return build_canonical_state(
        u=[0.0] * 6,
        theta=[0.0] * 6,
        coherence_spectral=1.0,
        coherence_spin=1.0,
        coherence_triadic=1.0,
        stabilization=1.0,
    )


# ═══════════════════════════════════════════════════════════════
# Geometry: ds² product metric
# ═══════════════════════════════════════════════════════════════

def compute_ds_squared(
    a: CanonicalState,
    b: CanonicalState,
    w_h: float = 1.0,
    w_t: float = 0.5,
    telemetry_weights: Optional[Sequence[float]] = None,
) -> Dict[str, float]:
    """Compute the product metric distance² between two canonical states.

    ds² = w_h * d_hyp(u_a, u_b)²
        + w_t * d_torus(theta_a, theta_b)²
        + Σ_i w_i * (z_a_i - z_b_i)²

    Returns breakdown dict with per-block contributions and total.

    The hyperbolic term is NOT clamped — boundary amplification is
    the security mechanism (near the Poincare edge, small Euclidean
    shifts produce large hyperbolic distances).
    """
    # Block A: Hyperbolic distance on B^6
    d_hyp_sq = _hyperbolic_distance_sq(a.u, b.u)

    # Block B: Torus distance on T^6
    d_tor_sq = _torus_distance_sq(a.theta, b.theta)

    # Block C+D: Weighted Euclidean on telemetry + derived
    w = list(telemetry_weights) if telemetry_weights is not None else DEFAULT_TELEMETRY_WEIGHTS
    if len(w) != TELEMETRY_DIM + DERIVED_DIM:
        raise CanonicalStateError(
            f"telemetry_weights must have {TELEMETRY_DIM + DERIVED_DIM} entries, got {len(w)}"
        )

    z_a = a.vec[12:21]
    z_b = b.vec[12:21]
    d_tel_sq = sum(w[i] * (z_a[i] - z_b[i]) ** 2 for i in range(len(w)))

    total = w_h * d_hyp_sq + w_t * d_tor_sq + d_tel_sq

    return {
        "ds_squared": total,
        "ds": math.sqrt(max(0.0, total)),
        "hyp_sq": d_hyp_sq,
        "tor_sq": d_tor_sq,
        "tel_sq": d_tel_sq,
        "w_h": w_h,
        "w_t": w_t,
    }


# ═══════════════════════════════════════════════════════════════
# Audit: state transition logging
# ═══════════════════════════════════════════════════════════════

class StateTransitionAuditor:
    """Append-only audit log for canonical state transitions.

    Records (before, after, ds², metadata) for every governance decision.
    Hash-chains entries for tamper detection.
    """

    def __init__(self, max_entries: int = 10000):
        self._entries: List[Dict] = []
        self._hash_chain: List[str] = []
        self._max = max_entries

    def audit_state_transition(
        self,
        before: CanonicalState,
        after: CanonicalState,
        decision: str,
        agent_id: str = "",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Record a state transition with full ds² breakdown.

        Args:
            before: State before the governance decision.
            after: State after the governance decision.
            decision: The verdict string (ALLOW / WARN / DENY / etc).
            agent_id: Agent or request identifier.
            metadata: Extra context to store.

        Returns:
            The audit entry dict.
        """
        ds2 = compute_ds_squared(before, after)

        entry = {
            "index": len(self._entries),
            "before_hash": before.hash(),
            "after_hash": after.hash(),
            "decision": decision,
            "agent_id": agent_id,
            "ds_squared": ds2["ds_squared"],
            "ds": ds2["ds"],
            "hyp_sq": ds2["hyp_sq"],
            "tor_sq": ds2["tor_sq"],
            "tel_sq": ds2["tel_sq"],
            "before_u_norm": before.u_norm(),
            "after_u_norm": after.u_norm(),
            "metadata": metadata or {},
        }

        # Hash chain: each entry hashes with the previous
        prev_hash = self._hash_chain[-1] if self._hash_chain else ""
        chain_input = json.dumps(
            {"prev": prev_hash, "idx": entry["index"], "bh": entry["before_hash"],
             "ah": entry["after_hash"], "d": decision},
            separators=(",", ":"),
        ).encode("utf-8")
        entry_hash = hashlib.sha256(chain_input).hexdigest()

        self._entries.append(entry)
        self._hash_chain.append(entry_hash)

        # Evict oldest if over capacity
        if len(self._entries) > self._max:
            self._entries.pop(0)
            self._hash_chain.pop(0)

        return entry

    @property
    def count(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> List[Dict]:
        return list(self._entries)

    def verify_chain(self) -> bool:
        """Verify hash chain integrity."""
        for i, entry in enumerate(self._entries):
            prev_hash = self._hash_chain[i - 1] if i > 0 else ""
            chain_input = json.dumps(
                {"prev": prev_hash, "idx": entry["index"], "bh": entry["before_hash"],
                 "ah": entry["after_hash"], "d": entry["decision"]},
                separators=(",", ":"),
            ).encode("utf-8")
            expected = hashlib.sha256(chain_input).hexdigest()
            if expected != self._hash_chain[i]:
                return False
        return True


# Module-level singleton auditor (wire into decision paths)
_global_auditor = StateTransitionAuditor()


def audit_state_transition(
    before: CanonicalState,
    after: CanonicalState,
    decision: str,
    agent_id: str = "",
    metadata: Optional[Dict] = None,
) -> Dict:
    """Module-level audit function — delegates to global auditor."""
    return _global_auditor.audit_state_transition(
        before, after, decision, agent_id, metadata
    )


def get_auditor() -> StateTransitionAuditor:
    """Return the module-level auditor for inspection/testing."""
    return _global_auditor


# ═══════════════════════════════════════════════════════════════
# Internal geometry helpers
# ═══════════════════════════════════════════════════════════════

EPS = 1e-12


def _hyperbolic_distance_sq(u: Sequence[float], v: Sequence[float]) -> float:
    """d_hyp(u, v)² on the Poincare ball.

    d = arccosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))

    Inputs are clamped INTO the ball. The output is NOT clamped —
    boundary amplification is the security mechanism.
    """
    uu = sum(x * x for x in u)
    vv = sum(x * x for x in v)

    # Clamp inputs to open ball (reject points outside)
    if uu >= 1.0 or vv >= 1.0:
        raise CanonicalStateError(
            f"Poincare points must satisfy ||u|| < 1, got ||u||²={uu:.8f}, ||v||²={vv:.8f}"
        )

    diff_sq = sum((a - b) ** 2 for a, b in zip(u, v))
    denom = max(EPS, (1.0 - uu) * (1.0 - vv))
    arg = 1.0 + 2.0 * diff_sq / denom

    d = math.acosh(max(1.0, arg))
    return d * d


def _torus_distance_sq(theta_a: Sequence[float], theta_b: Sequence[float]) -> float:
    """d_torus(a, b)² on T^6 with wrapped angle difference."""
    total = 0.0
    for a, b in zip(theta_a, theta_b):
        delta = math.atan2(math.sin(a - b), math.cos(a - b))
        total += delta * delta
    return total


def _compute_energy_harmonic(r: float, d: int = 6) -> float:
    """H(d, R) = R^(d²) where R = 1/(1-r).

    Uses d=6 (tongue subspace dimension), not d=21.
    """
    if r >= 1.0:
        raise CanonicalStateError(f"Cannot compute harmonic energy for r={r:.8f} >= 1")
    if r < EPS:
        return 1.0  # R_eff = 1/(1-0) = 1, 1^36 = 1
    R_eff = 1.0 / max(EPS, 1.0 - r)
    exponent = d * d  # 36 for d=6
    # Clamp exponent to prevent float overflow
    log_val = exponent * math.log(R_eff)
    if log_val > 700:  # near float64 max
        return float("inf")
    return R_eff ** exponent
