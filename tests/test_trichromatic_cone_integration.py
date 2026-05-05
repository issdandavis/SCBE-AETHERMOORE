"""Tests for the cone-extended trichromatic governance scoring.

Verifies that ``score_state_with_cones`` correctly fuses the existing
per-tongue band scoring (from ``TrichromaticGovernanceEngine``) with
the new tri-cone signature (from ``python.scbe.tri_cone_embedding``)
into a single ``TrichromaticConeScores`` blob whose ``unified_governance``
is the more conservative of the two underlying decisions.
"""

from __future__ import annotations


from python.scbe.tri_braid_embedding import TriBraidSignature
from python.scbe.tri_cone_embedding import tri_cone_signature
from src.governance.trichromatic_governance import (
    TrichromaticConeScores,
    TrichromaticGovernanceEngine,
    TrichromaticScores,
    score_state_with_cones,
)


def _braid(fast: float, memory: float, governance: float) -> TriBraidSignature:
    return TriBraidSignature(
        schema_version="test",
        fast=tuple([fast] * 6),
        memory=tuple([memory] * 6),
        governance=tuple([governance] * 6),
        dominant_axes=(),
        crossing_count=0,
        triadic_stable=0.5,
        ordered_hash="x" * 64,
        decision="ALLOW",
        invariants=(),
    )


def _benign_band_scores() -> TrichromaticScores:
    """A clean, low-risk band-score blob (used to isolate cone contribution)."""

    return TrichromaticScores(
        triplet_coherence_score=0.95,
        lattice_energy_score=0.10,
        whole_state_anomaly_score=0.10,
        risk_score=0.10,
        strongest_bridge="KO-AV",
        strongest_bridge_norm=0.20,
    )


def _hot_band_scores() -> TrichromaticScores:
    """A high-risk band-score blob (forces unified verdict toward DENY)."""

    return TrichromaticScores(
        triplet_coherence_score=0.20,
        lattice_energy_score=0.85,
        whole_state_anomaly_score=0.80,
        risk_score=0.85,
        strongest_bridge="UM-DR",
        strongest_bridge_norm=0.95,
    )


# ---------------------------------------------------------------------------
# Returns the right shape
# ---------------------------------------------------------------------------


def test_score_state_with_cones_returns_extended_blob():
    cone = tri_cone_signature(_braid(0.0, 0.0, 0.0))
    out = score_state_with_cones(_benign_band_scores(), cone)
    assert isinstance(out, TrichromaticConeScores)
    assert isinstance(out.band_scores, TrichromaticScores)
    assert out.cone_governance in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    assert out.unified_governance in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    assert 0 <= out.positive_membership_count <= 3
    assert 0 <= out.shadow_membership_count <= 3


# ---------------------------------------------------------------------------
# Unified governance picks the conservative side
# ---------------------------------------------------------------------------


def test_clean_lit_braid_with_benign_band_scores_yields_allow():
    cone = tri_cone_signature(_braid(-5.0, -5.0, -5.0))  # ALL-LOW braid -> cone ALLOW
    out = score_state_with_cones(_benign_band_scores(), cone)
    assert out.cone_governance == "ALLOW"
    assert out.unified_governance == "ALLOW"


def test_clean_shadow_braid_yields_deny_regardless_of_band_scores():
    """Cone DENY always escalates the unified verdict to DENY."""

    cone = tri_cone_signature(_braid(5.0, 5.0, 5.0))  # ALL-HIGH braid -> cone DENY
    out = score_state_with_cones(_benign_band_scores(), cone)
    assert out.cone_governance == "DENY"
    assert out.unified_governance == "DENY"


def test_hot_band_scores_force_deny_even_when_cone_says_allow():
    """High band risk overrides a permissive cone reading."""

    cone = tri_cone_signature(_braid(-5.0, -5.0, -5.0))  # cone ALLOW
    out = score_state_with_cones(_hot_band_scores(), cone)
    assert out.cone_governance == "ALLOW"
    assert out.unified_governance == "DENY"


def test_quarantine_band_scores_lift_allow_to_quarantine():
    cone = tri_cone_signature(_braid(-5.0, -5.0, -5.0))  # cone ALLOW
    mid = TrichromaticScores(
        triplet_coherence_score=0.5,
        lattice_energy_score=0.5,
        whole_state_anomaly_score=0.5,
        risk_score=0.5,  # >= 0.40 threshold
        strongest_bridge="KO-AV",
        strongest_bridge_norm=0.5,
    )
    out = score_state_with_cones(mid, cone)
    assert out.unified_governance == "QUARANTINE"


# ---------------------------------------------------------------------------
# Cone risk score blends correctly
# ---------------------------------------------------------------------------


def test_cone_risk_score_increases_with_interference():
    benign = _benign_band_scores()
    cone_low_interference = tri_cone_signature(_braid(-5.0, -5.0, -5.0))
    cone_high_interference = tri_cone_signature(_braid(5.0, 5.0, 5.0))

    a = score_state_with_cones(benign, cone_low_interference)
    b = score_state_with_cones(benign, cone_high_interference)
    # ALL-HIGH has positive interference (both lit AND shadow triple-overlap fire);
    # ALL-LOW has negligible interference. The cone risk score should reflect that.
    assert b.cone_risk_score >= a.cone_risk_score


def test_cone_risk_score_clamped_to_unit_interval():
    cone = tri_cone_signature(_braid(5.0, -5.0, 0.0))
    out = score_state_with_cones(_hot_band_scores(), cone)
    assert 0.0 <= out.cone_risk_score <= 1.0
    assert 0.0 <= out.unified_risk_score <= 1.0


# ---------------------------------------------------------------------------
# Engine integration smoke
# ---------------------------------------------------------------------------


def test_engine_score_state_feeds_cleanly_into_score_state_with_cones():
    """End-to-end: engine produces band scores, cone module produces signature,
    score_state_with_cones fuses them without raising.
    """

    engine = TrichromaticGovernanceEngine()
    state = engine.build_state(
        coords=[0.5, 0.4, 0.6, 0.3, 0.7, 0.5],
        cost=10.0,
        spin_magnitude=2,
        trust_history=[1, 1, 0, 1, 1],
        cumulative_cost=50.0,
        session_query_count=8,
    )
    band_scores = engine.score_state(state)
    cone = tri_cone_signature(_braid(0.0, 0.0, 0.0))
    out = score_state_with_cones(band_scores, cone)
    assert out.unified_governance in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
