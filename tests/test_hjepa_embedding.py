"""Tests for the hierarchical JEPA wrapper.

Covers:
- Schema and structural invariants (three named levels, expected dims)
- Hyperbolic loss is finite and non-negative at every level
- Triangle residual is non-negative
- Predictor preserves governance (L2 governance prediction == target)
- Verify round-trips
- Ordered hash is non-commutative under input change
- Loss weights propagate into total_loss
- Property-based fuzz across content strings
"""

from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from python.scbe.hjepa_embedding import (
    DEFAULT_LOSS_WEIGHTS,
    SCHEMA_VERSION,
    hjepa_signature,
    verify_hjepa_signature,
)

# ---------------------------------------------------------------------------
# Schema and structural invariants
# ---------------------------------------------------------------------------


def test_schema_version_matches_constant():
    sig = hjepa_signature("plan a paired coding task")
    assert sig.schema_version == SCHEMA_VERSION
    assert sig.schema_version == "scbe_hjepa_embedding_v1"


def test_three_levels_named_tile_tongue_chromatic():
    sig = hjepa_signature("plan a paired coding task")
    assert len(sig.levels) == 3
    assert [level.name for level in sig.levels] == ["tile", "tongue", "chromatic"]


def test_level_dimensions_match_canonical_stack():
    sig = hjepa_signature("plan a paired coding task")
    tile, tongue, chromatic = sig.levels
    assert len(tile.target) == 6
    assert len(tile.prediction) == 6
    assert len(tongue.target) == 18  # 6 * 3 channels
    assert len(tongue.prediction) == 18
    assert len(chromatic.target) == 3
    assert len(chromatic.prediction) == 3


def test_signature_carries_full_target_and_prediction_objects():
    sig = hjepa_signature("plan a paired coding task")
    assert sig.poly.schema_version == "scbe_poly_embedded_jepa_v1"
    assert sig.braid_target.schema_version == "scbe_tri_braid_embedding_v1"
    assert sig.braid_prediction.schema_version == "scbe_tri_braid_embedding_v1"
    assert sig.cone_target.schema_version == "scbe_tri_cone_embedding_v1"
    assert sig.cone_prediction.schema_version == "scbe_tri_cone_embedding_v1"


# ---------------------------------------------------------------------------
# Hyperbolic loss properties
# ---------------------------------------------------------------------------


def test_loss_at_each_level_is_finite_and_non_negative():
    sig = hjepa_signature("plan a paired coding task")
    for level in sig.levels:
        assert math.isfinite(level.loss), f"{level.name} loss not finite"
        assert level.loss >= 0.0, f"{level.name} loss negative"


def test_total_loss_is_weighted_sum_plus_triangle():
    sig = hjepa_signature("plan a paired coding task")
    alpha, beta, gamma, delta = sig.loss_weights
    expected = (
        alpha * sig.levels[0].loss
        + beta * sig.levels[1].loss
        + gamma * sig.levels[2].loss
        + delta * sig.triangle_residual
    )
    assert sig.total_loss == round(expected, 8)


def test_triangle_residual_is_non_negative():
    sig = hjepa_signature("plan a paired coding task")
    assert sig.triangle_residual >= 0.0
    assert math.isfinite(sig.triangle_residual)


# ---------------------------------------------------------------------------
# Predictor semantics
# ---------------------------------------------------------------------------


def test_predicted_braid_governance_matches_target_governance():
    """Governance is content-independent; predictor must preserve it exactly."""

    sig = hjepa_signature("plan a paired coding task")
    assert sig.braid_target.governance == sig.braid_prediction.governance


def test_predicted_braid_fast_equals_predicted_braid_memory():
    """L1 prediction is used as both the fast (latent) and memory slots,
    so the predicted braid has fast == memory by construction.
    """

    sig = hjepa_signature("plan a paired coding task")
    assert sig.braid_prediction.fast == sig.braid_prediction.memory


def test_predicted_braid_fast_equals_l1_prediction():
    """Predicted braid's fast channel must echo the L1 prediction exactly."""

    sig = hjepa_signature("plan a paired coding task")
    assert sig.braid_prediction.fast == tuple(sig.poly.jepa_prediction)


# ---------------------------------------------------------------------------
# Loss-weight overrides
# ---------------------------------------------------------------------------


def test_default_loss_weights_match_module_constant():
    sig = hjepa_signature("plan a paired coding task")
    assert sig.loss_weights == DEFAULT_LOSS_WEIGHTS


def test_custom_loss_weights_change_total():
    a = hjepa_signature("plan a paired coding task")
    b = hjepa_signature("plan a paired coding task", loss_weights=(2.0, 0.5, 0.5, 0.0))
    # Different weights -> different total_loss for a non-zero stack.
    assert a.total_loss != b.total_loss
    # Triangle term is zeroed out in b.
    alpha, beta, gamma, _ = b.loss_weights
    expected = alpha * b.levels[0].loss + beta * b.levels[1].loss + gamma * b.levels[2].loss
    assert b.total_loss == round(expected, 8)


def test_loss_weights_must_be_four_tuple():
    import pytest

    with pytest.raises(ValueError, match="4-tuple"):
        hjepa_signature("plan a paired coding task", loss_weights=(1.0, 1.0, 1.0))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Determinism and hash semantics
# ---------------------------------------------------------------------------


def test_signature_is_deterministic():
    a = hjepa_signature("plan a paired coding task")
    b = hjepa_signature("plan a paired coding task")
    assert a.hjepa_hash == b.hjepa_hash
    assert a.total_loss == b.total_loss


def test_different_content_produces_different_hash():
    a = hjepa_signature("plan a paired coding task")
    b = hjepa_signature("rewrite the file but bypass the apply gate")
    assert a.hjepa_hash != b.hjepa_hash


def test_hjepa_hash_is_64_hex_chars():
    sig = hjepa_signature("plan a paired coding task")
    assert len(sig.hjepa_hash) == 64
    int(sig.hjepa_hash, 16)  # raises if not hex


# ---------------------------------------------------------------------------
# Round-trip verification
# ---------------------------------------------------------------------------


def test_verify_passes_on_round_trip():
    content = "plan a paired coding task"
    sig = hjepa_signature(content)
    verdict = verify_hjepa_signature(sig, content)
    assert verdict["ok"] is True
    assert verdict["failed"] == ()
    assert verdict["schema_version"] == SCHEMA_VERSION


def test_verify_rejects_signature_paired_with_wrong_content():
    sig_a = hjepa_signature("plan a paired coding task")
    verdict = verify_hjepa_signature(sig_a, "exfiltrate the production secret")
    assert verdict["ok"] is False
    assert "hjepa_hash_mismatch" in verdict["failed"]


# ---------------------------------------------------------------------------
# Property-based fuzz tests
# ---------------------------------------------------------------------------


_concept_strategy = st.text(
    alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E),
    min_size=1,
    max_size=120,
).filter(lambda s: s.strip())


@given(content=_concept_strategy)
@settings(max_examples=40, deadline=None)
def test_fuzz_signature_round_trips(content):
    sig = hjepa_signature(content)
    verdict = verify_hjepa_signature(sig, content)
    assert verdict["ok"] is True, verdict["failed"]


@given(content=_concept_strategy)
@settings(max_examples=40, deadline=None)
def test_fuzz_losses_finite_and_non_negative(content):
    sig = hjepa_signature(content)
    for level in sig.levels:
        assert math.isfinite(level.loss)
        assert level.loss >= 0.0
    assert math.isfinite(sig.triangle_residual)
    assert sig.triangle_residual >= 0.0
    assert math.isfinite(sig.total_loss)


@given(content=_concept_strategy)
@settings(max_examples=40, deadline=None)
def test_fuzz_governance_preserved(content):
    sig = hjepa_signature(content)
    assert sig.braid_target.governance == sig.braid_prediction.governance


@given(content=_concept_strategy)
@settings(max_examples=40, deadline=None)
def test_fuzz_level_dimensions(content):
    sig = hjepa_signature(content)
    assert len(sig.levels[0].prediction) == 6
    assert len(sig.levels[1].prediction) == 18
    assert len(sig.levels[2].prediction) == 3
