"""
Matrix ↔ Catalog Bridge — Connects Governance Decisions to Task Archetypes
===========================================================================

@file matrix_catalog_bridge.py
@module concept_blocks/matrix_catalog_bridge
@layer Cross-cutting (L1-L14)
@version 1.0.0
@patent USPTO #63/961,403

Bridges the gap between governance decision outputs and the Context Catalog's
25 task archetypes.  Given a governance decision + optional 21D brain state,
this module:

  1. Computes the radial coordinate  r = ||embed(x_21d)||  in the Poincaré ball
  2. Queries the catalog for archetypes whose radial_zone contains r
  3. Scores candidates by decision compatibility, modality match, and
     complexity alignment
  4. Returns the best-fit archetype with its polyhedron, denomination,
     required layers, and credit parameters

Integration points:
  - Accepts output from any decision path (governance_adapter, grand_unified,
    mmx_reducer) via the DecisionEvent from decision_telemetry
  - Enriches the DecisionEvent with archetype_id, polyhedron, radial_zone,
    and symmetry_order before it hits the log
  - Provides the bridge data needed for gap #4 (Catalog → Credit mint)

21D State Verification:
  The canonical 21D state vector is defined in ai_brain/unified_state.py:
    BLOCK_HYPER[0:6]    — Poincaré ball coordinates (trust geometry)
    BLOCK_PHASE[6:12]   — Tongue phase angles (intent alignment)
    BLOCK_HAM[12:16]    — Hamiltonian momenta (dynamics)
    BLOCK_LATTICE[16:18] — Lattice path indices (quasicrystal)
    BLOCK_FLUX[18]      — Breathing/flux scalar (drift rate)
    BLOCK_SPEC[19:21]   — Spectral summary (coherence metrics)

  Product manifold: B^21 × T^2  (Poincaré ball × Riemannian torus)
  Radial coordinate r = ||embed(xi)|| is DERIVED, not independent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .context_catalog.catalog import (
    ARCHETYPE_REGISTRY,
    ComplexityTier,
    ContextCatalog,
    PolyhedronType,
    TaskArchetype,
)
from ..ai_brain.unified_state import (
    BLOCK_RANGES,
    BRAIN_DIMENSIONS,
    safe_poincare_embed,
    validate_21d_coherence,
)
from ..decision_telemetry import (
    DecisionEvent,
    POLYHEDRON_SYMMETRY,
)


# ---------------------------------------------------------------------------
#  Decision → Complexity mapping
# ---------------------------------------------------------------------------

# Maps governance decisions to minimum expected complexity tiers
_DECISION_COMPLEXITY_FLOOR: Dict[str, ComplexityTier] = {
    "ALLOW": ComplexityTier.TRIVIAL,
    "QUARANTINE": ComplexityTier.STANDARD,
    "ESCALATE": ComplexityTier.COMPLEX,
    "DENY": ComplexityTier.EXTREME,
}

# Complexity tier ordering for comparison
_TIER_ORDER: Dict[ComplexityTier, int] = {
    ComplexityTier.TRIVIAL: 0,
    ComplexityTier.STANDARD: 1,
    ComplexityTier.COMPLEX: 2,
    ComplexityTier.EXTREME: 3,
    ComplexityTier.FORBIDDEN: 4,
}

# Modality → tag affinities (which catalog tags match which MMX modalities)
_MODALITY_TAG_MAP: Dict[str, List[str]] = {
    "text": ["encoding", "tokenization", "translation", "content"],
    "web": ["web", "navigation", "autonomous", "publishing"],
    "security": ["security", "antivirus", "scanning", "threat-detection", "defense"],
    "trade": ["economy", "transport", "optimization", "market-analysis"],
    "fleet": ["fleet", "coordination", "multi-agent", "formation"],
    "governance": ["governance", "enforcement", "scanning", "rules"],
    "combat": ["combat", "adversarial", "high-risk", "real-time"],
    "mission": ["mission", "delivery", "campaign", "multi-stage"],
    "crypto": ["encryption", "geoseal", "pqc", "context-aware", "vault"],
    "brain": ["introspection", "self-check", "planning", "recursive", "creative"],
    "credit": ["minting", "credit", "exchange", "escrow"],
}


def _vec_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _tier_distance(a: ComplexityTier, b: ComplexityTier) -> int:
    """Absolute distance between two complexity tiers (0 = exact match)."""
    return abs(_TIER_ORDER.get(a, 2) - _TIER_ORDER.get(b, 2))


# ---------------------------------------------------------------------------
#  Archetype Scoring
# ---------------------------------------------------------------------------

@dataclass
class ArchetypeMatch:
    """Result of matching a governance decision to a catalog archetype."""

    archetype: TaskArchetype
    score: float               # Total match score (higher = better)
    radial_r: float            # Radial coordinate used for matching
    radial_fit: float          # How well r fits the archetype's zone [0,1]
    complexity_fit: float      # Complexity tier alignment [0,1]
    modality_fit: float        # Modality tag overlap [0,1]
    decision_compatible: bool  # Does the decision meet min_governance_verdict?

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype_id": self.archetype.archetype_id,
            "polyhedron": self.archetype.polyhedron.value,
            "denomination": self.archetype.denomination,
            "score": round(self.score, 4),
            "radial_r": round(self.radial_r, 6),
            "radial_fit": round(self.radial_fit, 4),
            "complexity_fit": round(self.complexity_fit, 4),
            "modality_fit": round(self.modality_fit, 4),
            "decision_compatible": self.decision_compatible,
        }


def _score_archetype(
    archetype: TaskArchetype,
    r: float,
    decision: str,
    modalities: List[str],
    conflict_mass: float,
) -> ArchetypeMatch:
    """Score how well a single archetype matches the current decision context.

    Scoring formula:
      score = 0.4 * radial_fit + 0.3 * complexity_fit + 0.2 * modality_fit + 0.1 * compat_bonus

    radial_fit:    1.0 if r is centered in the zone, decays linearly to edges
    complexity_fit: 1.0 if decision complexity matches archetype tier
    modality_fit:  fraction of archetype tags that overlap with active modalities
    compat_bonus:  1.0 if decision meets archetype's min_governance_verdict
    """
    # Radial fit: 1.0 at zone center, 0.0 at edges
    r_min, r_max = archetype.radial_zone
    zone_width = max(r_max - r_min, 0.01)

    if r_min <= r <= r_max:
        zone_center = (r_min + r_max) / 2.0
        dist_from_center = abs(r - zone_center) / (zone_width / 2.0)
        radial_fit = max(0.0, 1.0 - dist_from_center)
    else:
        # Outside zone — penalize by distance
        overshoot = min(abs(r - r_min), abs(r - r_max))
        radial_fit = max(0.0, 1.0 - overshoot * 3.0)

    # Complexity fit: based on decision → expected tier vs archetype tier
    expected_tier = _DECISION_COMPLEXITY_FLOOR.get(decision, ComplexityTier.STANDARD)
    # Boost complexity if conflict_mass is high
    if conflict_mass > 0.5:
        tier_idx = min(_TIER_ORDER.get(expected_tier, 1) + 1, 4)
        expected_tier = [t for t, i in _TIER_ORDER.items() if i == tier_idx][0]

    tier_dist = _tier_distance(expected_tier, archetype.complexity_tier)
    complexity_fit = max(0.0, 1.0 - tier_dist * 0.3)

    # Modality fit: tag overlap
    archetype_tags = set(archetype.tags)
    modality_tags: set = set()
    for mod in modalities:
        modality_tags.update(_MODALITY_TAG_MAP.get(mod, []))

    if modality_tags and archetype_tags:
        overlap = len(archetype_tags & modality_tags)
        modality_fit = overlap / max(len(archetype_tags), 1)
    else:
        modality_fit = 0.5  # neutral if no modality info

    # Decision compatibility: does the decision meet the archetype's minimum?
    _verdict_order = {"ALLOW": 0, "QUARANTINE": 1, "ESCALATE": 2, "DENY": 3}
    decision_level = _verdict_order.get(decision, 0)
    min_level = _verdict_order.get(archetype.min_governance_verdict, 0)
    decision_compatible = decision_level >= min_level

    compat_bonus = 1.0 if decision_compatible else 0.0

    # Weighted total
    score = (
        0.4 * radial_fit
        + 0.3 * complexity_fit
        + 0.2 * modality_fit
        + 0.1 * compat_bonus
    )

    return ArchetypeMatch(
        archetype=archetype,
        score=score,
        radial_r=r,
        radial_fit=radial_fit,
        complexity_fit=complexity_fit,
        modality_fit=modality_fit,
        decision_compatible=decision_compatible,
    )


# ---------------------------------------------------------------------------
#  Public API — The Bridge
# ---------------------------------------------------------------------------

class MatrixCatalogBridge:
    """Bridges governance decisions to Context Catalog archetypes.

    Usage::

        bridge = MatrixCatalogBridge()

        # From MMX reducer output + 21D brain state
        match = bridge.resolve(
            decision="ALLOW",
            brain_state_21d=[...],  # 21 floats
            modalities=["text", "web"],
            conflict_mass=0.15,
        )
        print(match.archetype.archetype_id)   # e.g. "WEB_NAVIGATE"
        print(match.archetype.polyhedron)      # truncated_icosahedron
        print(match.archetype.denomination)    # "KO"

        # From decision telemetry event
        enriched = bridge.enrich_event(event)
    """

    def __init__(self) -> None:
        self._catalog = ContextCatalog()

    def compute_radial(
        self,
        brain_state_21d: Optional[List[float]] = None,
        poincare_point: Optional[List[float]] = None,
        fallback_confidence: float = 0.5,
    ) -> float:
        """Compute the radial coordinate r from the best available source.

        Priority:
          1. Pre-computed Poincaré point (norm directly)
          2. Raw 21D state (embed, then norm)
          3. Fallback from confidence (r ≈ 1 - confidence)

        Returns:
            r in [0, 1) — distance from Poincaré ball center.
        """
        if poincare_point is not None and len(poincare_point) > 0:
            return min(_vec_norm(poincare_point), 0.9999)

        if brain_state_21d is not None and len(brain_state_21d) == BRAIN_DIMENSIONS:
            embedded = safe_poincare_embed(brain_state_21d)
            return min(_vec_norm(embedded), 0.9999)

        # Fallback: high confidence → near origin, low confidence → near boundary
        return min(max(1.0 - fallback_confidence, 0.0), 0.9999)

    def resolve(
        self,
        decision: str,
        brain_state_21d: Optional[List[float]] = None,
        poincare_point: Optional[List[float]] = None,
        modalities: Optional[List[str]] = None,
        conflict_mass: float = 0.0,
        confidence: float = 0.5,
        top_k: int = 3,
    ) -> ArchetypeMatch:
        """Resolve a governance decision to the best-matching catalog archetype.

        Args:
            decision: ALLOW / QUARANTINE / ESCALATE / DENY
            brain_state_21d: Optional raw 21D state vector
            poincare_point: Optional pre-embedded Poincaré point
            modalities: Active modality IDs from the MMX matrix
            conflict_mass: From MMX signals (0 = unanimous, 1 = total conflict)
            confidence: Decision confidence (used as radial fallback)
            top_k: Return top-k matches (best is index 0)

        Returns:
            Best-matching ArchetypeMatch.

        Raises:
            ValueError: If no archetypes match at all.
        """
        r = self.compute_radial(brain_state_21d, poincare_point, confidence)
        mods = modalities or []

        matches = []
        for archetype in self._catalog.all():
            match = _score_archetype(archetype, r, decision, mods, conflict_mass)
            matches.append(match)

        matches.sort(key=lambda m: m.score, reverse=True)

        if not matches:
            raise ValueError("No archetypes in catalog")

        return matches[0]

    def resolve_top_k(
        self,
        decision: str,
        brain_state_21d: Optional[List[float]] = None,
        poincare_point: Optional[List[float]] = None,
        modalities: Optional[List[str]] = None,
        conflict_mass: float = 0.0,
        confidence: float = 0.5,
        top_k: int = 3,
    ) -> List[ArchetypeMatch]:
        """Like resolve() but returns top-k matches."""
        r = self.compute_radial(brain_state_21d, poincare_point, confidence)
        mods = modalities or []

        matches = []
        for archetype in self._catalog.all():
            match = _score_archetype(archetype, r, decision, mods, conflict_mass)
            matches.append(match)

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:top_k]

    def enrich_event(self, event: DecisionEvent) -> DecisionEvent:
        """Enrich a DecisionEvent with archetype/polyhedron assignment.

        Reads the event's existing state (brain_21d, poincare_21d, decision)
        and resolves to the best archetype.  Mutates the event in place and
        returns it.

        This is the primary integration point — call this after emitting
        the raw event but before it hits the log.
        """
        # Determine modalities from the event
        modalities: List[str] = []
        if event.mmx_agreement is not None:
            modalities = list(event.mmx_agreement.keys())

        # Determine confidence
        confidence = event.combined_score if event.combined_score > 0 else 0.5

        # Determine conflict mass
        conflict_mass = event.mmx_conflict_mass

        match = self.resolve(
            decision=event.decision,
            brain_state_21d=event.brain_state_21d,
            poincare_point=event.brain_poincare_21d,
            modalities=modalities,
            conflict_mass=conflict_mass,
            confidence=confidence,
        )

        # Enrich the event
        event.archetype_id = match.archetype.archetype_id
        event.polyhedron = match.archetype.polyhedron.value
        event.radial_zone = match.archetype.radial_zone
        event.symmetry_order = POLYHEDRON_SYMMETRY.get(
            match.archetype.polyhedron.value, 0
        )

        # If we computed a better radial, update the event
        if match.radial_r > 0 and event.radial_r == 0:
            event.radial_r = match.radial_r
            event.boundary_distance = 1.0 - match.radial_r

        return event

    def validate_21d_state(self, vector: List[float]) -> Dict[str, Any]:
        """Validate a 21D state vector and return coherence report.

        Delegates to unified_state.validate_21d_coherence() and adds
        bridge-level context (which archetypes are reachable at this r).
        """
        coherence = validate_21d_coherence(vector)

        if not coherence["valid"]:
            return {
                **coherence,
                "reachable_archetypes": [],
                "block_summary": {},
            }

        # Compute r and find reachable archetypes
        embedded = safe_poincare_embed(vector)
        r = _vec_norm(embedded)
        reachable = self._catalog.for_radial_distance(r)

        # Block summary
        block_summary = {}
        for name, (start, end) in BLOCK_RANGES.items():
            block_vals = vector[start:end]
            block_summary[name] = {
                "range": [start, end],
                "values": [round(v, 6) for v in block_vals],
                "norm": round(_vec_norm(block_vals), 6),
            }

        return {
            **coherence,
            "radial_r": round(r, 6),
            "reachable_archetypes": [a.archetype_id for a in reachable],
            "block_summary": block_summary,
        }
