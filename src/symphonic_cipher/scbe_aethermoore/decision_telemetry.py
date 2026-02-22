"""
Decision Telemetry — Unified State Vector per Governance Decision
=================================================================

@file decision_telemetry.py
@module scbe_aethermoore/decision_telemetry
@layer Cross-cutting (L1-L14)
@version 1.0.0
@patent USPTO #63/961,403

Emits the complete dimensional state for every governance decision:

  - 21D brain state     (from unified_state.py, B^21 Poincare ball)
  - 9D governance proj  (from grand_unified.py, R^9 slice)
  - 6D tongue phases    (BLOCK_PHASE [6:12] of brain state)
  - 1D radial coord     r = ||embed(xi)||  (DERIVED, not independent)
  - Polyhedral assignment (archetype_id + polyhedron type)
  - MMX signals          (agreement, reliability, drift, conflict)
  - Decision + rationale

Product manifold: B^21 x T^2   (Poincare ball x Riemannian torus)
The radial coordinate is the norm of the Poincare embedding, not a
separate degree of freedom.  Tongue weights in log-phi space for
distance calculations: log_phi(w_i) = i for i in {0..5}.

Symmetry group justification for polyhedral zones:
  Core (Platonic):     |Sym| = 24-120  -> maximally invariant decisions
  Cortex (Archimedean): |Sym| = 12-60  -> moderate orientation sensitivity
  Risk (Kepler-Poinsot): self-intersecting -> non-convex, specialized processing
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Log-phi tongue weights for distance calculations
PHI = (1 + math.sqrt(5)) / 2
LOG_PHI = math.log(PHI)
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]
TONGUE_LOG_WEIGHTS = [float(i) for i in range(6)]  # 0,1,2,3,4,5 in log-phi


def _safe_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


# ---------------------------------------------------------------------------
#  Decision Event — the canonical telemetry record
# ---------------------------------------------------------------------------

@dataclass
class DecisionEvent:
    """Complete state vector emitted per governance decision.

    This is the observability atom.  Every decision path (governance_adapter,
    grand_unified, multi_model_matrix) produces one of these.
    """

    # -- Identity --
    timestamp: float
    decision_path: str              # "governance_adapter" | "grand_unified" | "mmx_reducer"
    decision: str                   # ALLOW | QUARANTINE | ESCALATE | DENY
    rationale: str

    # -- 21D Brain State (B^21 Poincare ball) --
    brain_state_21d: Optional[List[float]] = None
    brain_poincare_21d: Optional[List[float]] = None  # after embed

    # -- 9D Governance Projection (R^9) --
    governance_9d: Optional[List[float]] = None

    # -- 6D Tongue Phases (BLOCK_PHASE slice) --
    tongue_phases_6d: Optional[List[float]] = None
    tongue_log_weights: List[float] = field(default_factory=lambda: list(TONGUE_LOG_WEIGHTS))

    # -- Derived Radial Coordinate --
    radial_r: float = 0.0          # ||embed(xi)|| — derived, not independent
    boundary_distance: float = 0.0  # 1.0 - r

    # -- Polyhedral Assignment --
    archetype_id: str = ""
    polyhedron: str = ""
    radial_zone: Tuple[float, float] = (0.0, 1.0)
    symmetry_order: int = 0         # |Sym(polyhedron)|

    # -- MMX Signals (multi-model, when available) --
    mmx_agreement: Optional[Dict[str, float]] = None
    mmx_reliability: Optional[Dict[str, float]] = None
    mmx_cross_drift: float = 0.0
    mmx_conflict_mass: float = 0.0

    # -- Governance Adapter Signals (21D path) --
    mirror_asymmetry: float = 0.0
    fractal_anomaly: float = 0.0
    charge_imbalance: float = 0.0
    combined_score: float = 0.0
    flux_contracted: bool = False
    persistence_count: int = 0

    # -- Grand Unified Signals (9D path) --
    euler_chi: int = 0
    entropy_eta: float = 0.0
    tau_dot: float = 0.0
    coherence: float = 0.0
    harmonic_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "ts": self.timestamp,
            "path": self.decision_path,
            "decision": self.decision,
            "rationale": self.rationale,
            "radial_r": round(self.radial_r, 6),
            "boundary_distance": round(self.boundary_distance, 6),
        }
        if self.brain_state_21d is not None:
            d["brain_21d"] = [round(x, 6) for x in self.brain_state_21d]
        if self.brain_poincare_21d is not None:
            d["poincare_21d"] = [round(x, 6) for x in self.brain_poincare_21d]
        if self.governance_9d is not None:
            d["gov_9d"] = [round(float(x.real) if hasattr(x, 'real') else float(x), 6)
                           for x in self.governance_9d]
        if self.tongue_phases_6d is not None:
            d["tongue_6d"] = [round(x, 6) for x in self.tongue_phases_6d]
        d["tongue_log_weights"] = self.tongue_log_weights
        if self.archetype_id:
            d["archetype"] = {
                "id": self.archetype_id,
                "polyhedron": self.polyhedron,
                "radial_zone": list(self.radial_zone),
                "symmetry_order": self.symmetry_order,
            }
        if self.mmx_agreement is not None:
            d["mmx"] = {
                "agreement": self.mmx_agreement,
                "reliability": self.mmx_reliability,
                "cross_drift": round(self.mmx_cross_drift, 6),
                "conflict_mass": round(self.mmx_conflict_mass, 6),
            }
        # Governance adapter signals
        if self.decision_path == "governance_adapter":
            d["adapter"] = {
                "mirror_asymmetry": round(self.mirror_asymmetry, 6),
                "fractal_anomaly": round(self.fractal_anomaly, 6),
                "charge_imbalance": round(self.charge_imbalance, 6),
                "combined_score": round(self.combined_score, 6),
                "flux_contracted": self.flux_contracted,
                "persistence_count": self.persistence_count,
            }
        # Grand unified signals
        if self.decision_path == "grand_unified":
            d["unified"] = {
                "euler_chi": self.euler_chi,
                "entropy_eta": round(self.entropy_eta, 6),
                "tau_dot": round(self.tau_dot, 6),
                "coherence": round(self.coherence, 6),
                "harmonic_cost": round(self.harmonic_cost, 6),
            }
        return d


# ---------------------------------------------------------------------------
#  Polyhedron Symmetry Table
# ---------------------------------------------------------------------------

POLYHEDRON_SYMMETRY: Dict[str, int] = {
    # Core: Platonic (highest symmetry)
    "tetrahedron": 24,
    "cube": 48,
    "octahedron": 48,
    "dodecahedron": 120,
    "icosahedron": 120,
    # Cortex: Archimedean (moderate symmetry)
    "truncated_icosahedron": 120,
    "rhombicuboctahedron": 48,
    "snub_dodecahedron": 60,
    # Risk: Kepler-Poinsot (self-intersecting)
    "small_stellated_dodecahedron": 120,
    "great_stellated_dodecahedron": 120,
    # Cerebellum: Toroidal
    "szilassi": 7,
    "csaszar": 1,
    # Connectome: Johnson/Rhombic
    "rhombic_dodecahedron": 48,
    "rhombic_triacontahedron": 120,
    "johnson_a": 4,
    "johnson_b": 4,
}


# ---------------------------------------------------------------------------
#  Decision Log — append-only ring buffer
# ---------------------------------------------------------------------------

class DecisionLog:
    """Append-only log of DecisionEvents with query API."""

    def __init__(self, max_events: int = 10_000) -> None:
        self._events: List[DecisionEvent] = []
        self._max = max_events

    def emit(self, event: DecisionEvent) -> None:
        """Append a decision event."""
        self._events.append(event)
        if len(self._events) > self._max:
            self._events = self._events[-self._max:]

    def query(
        self,
        path: Optional[str] = None,
        decision: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[DecisionEvent]:
        out: List[DecisionEvent] = []
        for e in reversed(self._events):
            if path and e.decision_path != path:
                continue
            if decision and e.decision != decision:
                continue
            if since and e.timestamp < since:
                break
            out.append(e)
            if len(out) >= limit:
                break
        return list(reversed(out))

    @property
    def total(self) -> int:
        return len(self._events)

    @property
    def latest(self) -> Optional[DecisionEvent]:
        return self._events[-1] if self._events else None

    def summary(self) -> Dict[str, Any]:
        by_path: Dict[str, int] = {}
        by_decision: Dict[str, int] = {}
        for e in self._events:
            by_path[e.decision_path] = by_path.get(e.decision_path, 0) + 1
            by_decision[e.decision] = by_decision.get(e.decision, 0) + 1
        return {
            "total_events": len(self._events),
            "by_path": by_path,
            "by_decision": by_decision,
        }


# ---------------------------------------------------------------------------
#  Global singleton (importable by all decision paths)
# ---------------------------------------------------------------------------

_GLOBAL_LOG: Optional[DecisionLog] = None
_BRIDGE: Any = None  # lazy-loaded MatrixCatalogBridge


def get_decision_log() -> DecisionLog:
    """Get or create the global decision telemetry log."""
    global _GLOBAL_LOG
    if _GLOBAL_LOG is None:
        _GLOBAL_LOG = DecisionLog()
    return _GLOBAL_LOG


def _get_bridge() -> Any:
    """Lazy-load the MatrixCatalogBridge to avoid circular imports."""
    global _BRIDGE
    if _BRIDGE is None:
        try:
            from .concept_blocks.matrix_catalog_bridge import MatrixCatalogBridge
            _BRIDGE = MatrixCatalogBridge()
        except Exception:
            _BRIDGE = False  # disable on import failure
    return _BRIDGE if _BRIDGE is not False else None


def _enrich_and_emit(event: DecisionEvent) -> DecisionEvent:
    """Enrich event with archetype assignment, then emit to log."""
    bridge = _get_bridge()
    if bridge is not None and not event.archetype_id:
        try:
            bridge.enrich_event(event)
        except Exception:
            pass  # archetype enrichment is best-effort
    get_decision_log().emit(event)
    return event


# ---------------------------------------------------------------------------
#  Emitter helpers — one per decision path
# ---------------------------------------------------------------------------

def emit_from_governance_adapter(
    verdict_decision: str,
    brain_state_vector: List[float],
    poincare_point: List[float],
    mirror_asymmetry: float = 0.0,
    fractal_anomaly: float = 0.0,
    charge_imbalance: float = 0.0,
    combined_score: float = 0.0,
    flux_contracted: bool = False,
    persistence_count: int = 0,
    alignment_corrections: int = 0,
    archetype_id: str = "",
    polyhedron: str = "",
    radial_zone: Tuple[float, float] = (0.0, 1.0),
) -> DecisionEvent:
    """Emit a DecisionEvent from the governance_adapter path (21D brain state)."""
    r = _safe_norm(poincare_point)
    tongue_phases = brain_state_vector[6:12] if len(brain_state_vector) >= 12 else []

    event = DecisionEvent(
        timestamp=time.time(),
        decision_path="governance_adapter",
        decision=verdict_decision,
        rationale=f"combined={combined_score:.3f} mirror={mirror_asymmetry:.3f} "
                  f"fractal={fractal_anomaly:.3f} charge={charge_imbalance:.3f}",
        brain_state_21d=list(brain_state_vector),
        brain_poincare_21d=list(poincare_point),
        tongue_phases_6d=list(tongue_phases),
        radial_r=r,
        boundary_distance=1.0 - r,
        archetype_id=archetype_id,
        polyhedron=polyhedron,
        radial_zone=radial_zone,
        symmetry_order=POLYHEDRON_SYMMETRY.get(polyhedron, 0),
        mirror_asymmetry=mirror_asymmetry,
        fractal_anomaly=fractal_anomaly,
        charge_imbalance=charge_imbalance,
        combined_score=combined_score,
        flux_contracted=flux_contracted,
        persistence_count=persistence_count,
    )
    _enrich_and_emit(event)
    return event


def emit_from_grand_unified(
    decision: str,
    rationale: str,
    xi_9d: List[float],
    euler_chi: int = 2,
    entropy_eta: float = 0.0,
    tau_dot_val: float = 1.0,
    coherence: float = 0.0,
    harmonic_cost: float = 0.0,
    archetype_id: str = "",
    polyhedron: str = "",
    radial_zone: Tuple[float, float] = (0.0, 1.0),
) -> DecisionEvent:
    """Emit a DecisionEvent from the grand_unified path (9D governance)."""
    # Extract real parts for radial calculation
    real_vals = []
    for x in xi_9d:
        if hasattr(x, 'real'):
            real_vals.append(float(x.real))
        else:
            real_vals.append(float(x))
    r = _safe_norm(real_vals)

    event = DecisionEvent(
        timestamp=time.time(),
        decision_path="grand_unified",
        decision=decision,
        rationale=rationale,
        governance_9d=list(xi_9d),
        radial_r=r,
        boundary_distance=max(0.0, 1.0 - r),
        archetype_id=archetype_id,
        polyhedron=polyhedron,
        radial_zone=radial_zone,
        symmetry_order=POLYHEDRON_SYMMETRY.get(polyhedron, 0),
        euler_chi=euler_chi,
        entropy_eta=entropy_eta,
        tau_dot=tau_dot_val,
        coherence=coherence,
        harmonic_cost=harmonic_cost,
    )
    _enrich_and_emit(event)
    return event


def emit_from_mmx_reducer(
    decision: str,
    confidence: float,
    support: Dict[str, float],
    signals: Dict[str, Any],
    rationale: str,
    archetype_id: str = "",
    polyhedron: str = "",
    radial_zone: Tuple[float, float] = (0.0, 1.0),
) -> DecisionEvent:
    """Emit a DecisionEvent from the multi-model modal matrix reducer."""
    event = DecisionEvent(
        timestamp=time.time(),
        decision_path="mmx_reducer",
        decision=decision,
        rationale=rationale,
        mmx_agreement=signals.get("agreement_by_modality"),
        mmx_reliability=signals.get("reliability_by_model"),
        mmx_cross_drift=float(signals.get("cross_model_drift", 0.0)),
        mmx_conflict_mass=float(signals.get("conflict_mass", 0.0)),
        combined_score=confidence,
        archetype_id=archetype_id,
        polyhedron=polyhedron,
        radial_zone=radial_zone,
        symmetry_order=POLYHEDRON_SYMMETRY.get(polyhedron, 0),
    )
    _enrich_and_emit(event)
    return event
