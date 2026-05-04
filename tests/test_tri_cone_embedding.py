"""Tests for the tri-chromatic signed-cone embedding layer.

Exercises both the deterministic semantics (specific braids should map
to specific governance reads) and structural invariants (membership in
0..3, hash non-commutativity, sign-flip symmetry between lit and shadow
sides) using property-based fuzz tests.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from python.scbe.poly_embedded_jepa import build_poly_embedding
from python.scbe.tri_braid_embedding import TriBraidSignature, tri_braid_signature
from python.scbe.tri_cone_embedding import (
    ALLOW,
    DENY,
    ESCALATE,
    QUARANTINE,
    SCHEMA_VERSION,
    chromatic_shadow,
    signed_cone_governance,
    tri_cone_signature,
    tri_cone_signature_from_content,
    verify_tri_cone_signature,
)


def _braid(fast: float, memory: float, governance: float, length: int = 6) -> TriBraidSignature:
    """Build a synthetic tri-braid signature with constant per-channel components."""

    return TriBraidSignature(
        schema_version="test",
        fast=tuple([fast] * length),
        memory=tuple([memory] * length),
        governance=tuple([governance] * length),
        dominant_axes=(),
        crossing_count=0,
        triadic_stable=0.5,
        ordered_hash="x" * 64,
        decision="ALLOW",
        invariants=(),
    )


# ---------------------------------------------------------------------------
# Schema and structural invariants
# ---------------------------------------------------------------------------


def test_schema_version_matches_constant():
    sig = tri_cone_signature(_braid(0.0, 0.0, 0.0))
    assert sig.schema_version == SCHEMA_VERSION
    assert sig.schema_version == "scbe_tri_cone_embedding_v1"


def test_signature_carries_six_signed_cones():
    sig = tri_cone_signature(_braid(0.0, 0.0, 0.0))
    assert len(sig.cones) == 6
    polarities = [c.polarity for c in sig.cones]
    assert polarities.count(+1) == 3
    assert polarities.count(-1) == 3
    bands_pos = {c.band for c in sig.cones if c.polarity == +1}
    bands_neg = {c.band for c in sig.cones if c.polarity == -1}
    assert bands_pos == bands_neg == {"infrared", "visible", "ultraviolet"}


def test_membership_counts_each_in_zero_to_three():
    sig = tri_cone_signature(_braid(0.5, -0.5, 0.0))
    assert 0 <= sig.positive_membership_count <= 3
    assert 0 <= sig.shadow_membership_count <= 3


# ---------------------------------------------------------------------------
# Deterministic semantic reads
# ---------------------------------------------------------------------------


def test_all_low_braid_reads_as_allow():
    """Negligible activations on all bands -> nothing fires -> benign by default.

    (NegativeTongueLattice convention: low lattice energy = harmonious.)
    """

    sig = tri_cone_signature(_braid(-5.0, -5.0, -5.0))
    assert sig.cone_governance == ALLOW
    assert sig.positive_membership_count == 3
    assert sig.shadow_membership_count == 0


def test_all_high_braid_reads_as_deny():
    """Saturated activations on every band -> high lattice energy -> adversarial."""

    sig = tri_cone_signature(_braid(5.0, 5.0, 5.0))
    assert sig.cone_governance == DENY
    assert sig.positive_membership_count == 0
    assert sig.shadow_membership_count == 3


def test_balanced_braid_reads_as_escalate():
    """Mid-range activations sit just below the soap-bubble threshold."""

    sig = tri_cone_signature(_braid(0.0, 0.0, 0.0))
    assert sig.cone_governance == ESCALATE
    # Both joint embeddings live near (0.5, 0.5, 0.5); neither side dominates.
    assert sig.positive_membership_count == sig.shadow_membership_count


def test_one_band_dominant_reads_as_escalate_or_quarantine():
    """A single band firing strongly is mixed signal, never ALLOW or DENY."""

    sig = tri_cone_signature(_braid(5.0, -5.0, -5.0))
    assert sig.cone_governance in {ESCALATE, QUARANTINE}


# ---------------------------------------------------------------------------
# Sign-flip symmetry between positive and shadow sides
# ---------------------------------------------------------------------------


def test_chromatic_shadow_is_one_minus_positive():
    points = ((0.1, 0.2, 0.3), (0.9, 0.5, 0.4))
    shadow = chromatic_shadow(points)
    assert shadow[0] == pytest.approx((0.9, 0.8, 0.7), abs=1e-9)
    assert shadow[1] == pytest.approx((0.1, 0.5, 0.6), abs=1e-9)


def test_negating_braid_swaps_positive_and_shadow_counts():
    """Negating every channel value sign-flips chromatic projection,
    which should swap (positive, shadow) membership counts.
    """

    pos_braid = _braid(2.0, 2.0, 2.0)
    neg_braid = _braid(-2.0, -2.0, -2.0)
    sig_pos = tri_cone_signature(pos_braid)
    sig_neg = tri_cone_signature(neg_braid)
    assert sig_pos.positive_membership_count == sig_neg.shadow_membership_count
    assert sig_pos.shadow_membership_count == sig_neg.positive_membership_count


# ---------------------------------------------------------------------------
# Joint embedding geometry
# ---------------------------------------------------------------------------


def test_joint_embedding_lives_in_unit_cube():
    sig = tri_cone_signature(_braid(1.5, -2.0, 0.7))
    for component in sig.joint_embedding:
        assert 0.0 <= component <= 1.0
    for component in sig.joint_shadow:
        assert 0.0 <= component <= 1.0


def test_joint_and_shadow_sum_to_unity():
    """For constant-channel braids, joint + joint_shadow = (1, 1, 1)."""

    sig = tri_cone_signature(_braid(1.2, -0.7, 0.4))
    summed = tuple(round(j + s, 6) for j, s in zip(sig.joint_embedding, sig.joint_shadow))
    assert summed == (1.0, 1.0, 1.0)


# ---------------------------------------------------------------------------
# Plateau imbalance
# ---------------------------------------------------------------------------


def test_plateau_imbalance_zero_for_perfectly_balanced_braid():
    sig = tri_cone_signature(_braid(0.0, 0.0, 0.0))
    assert sig.plateau_imbalance == pytest.approx(0.0, abs=1e-6)


def test_plateau_imbalance_grows_for_lopsided_braid():
    balanced = tri_cone_signature(_braid(0.0, 0.0, 0.0))
    lopsided = tri_cone_signature(_braid(5.0, -5.0, 0.0))
    assert lopsided.plateau_imbalance > balanced.plateau_imbalance


def test_plateau_imbalance_in_unit_range():
    sig = tri_cone_signature(_braid(5.0, -5.0, 0.0))
    assert 0.0 <= sig.plateau_imbalance <= 1.0


# ---------------------------------------------------------------------------
# Cone-hash non-commutativity
# ---------------------------------------------------------------------------


def test_different_braids_produce_different_cone_hashes():
    a = tri_cone_signature(_braid(1.0, 0.0, 0.0))
    b = tri_cone_signature(_braid(0.0, 1.0, 0.0))
    assert a.cone_hash != b.cone_hash


def test_same_braid_produces_same_cone_hash():
    a = tri_cone_signature(_braid(0.7, -0.3, 0.1))
    b = tri_cone_signature(_braid(0.7, -0.3, 0.1))
    assert a.cone_hash == b.cone_hash


# ---------------------------------------------------------------------------
# verify_tri_cone_signature
# ---------------------------------------------------------------------------


def test_verify_passes_on_round_trip():
    braid = _braid(1.1, -0.4, 0.6)
    sig = tri_cone_signature(braid)
    verdict = verify_tri_cone_signature(sig, braid)
    assert verdict["ok"] is True
    assert verdict["failed"] == ()
    assert verdict["schema_version"] == SCHEMA_VERSION


def test_verify_rejects_signature_paired_with_wrong_braid():
    braid_a = _braid(1.0, 0.0, 0.0)
    braid_b = _braid(0.0, 1.0, 0.0)
    sig = tri_cone_signature(braid_a)
    verdict = verify_tri_cone_signature(sig, braid_b)
    assert verdict["ok"] is False
    assert "cone_hash_mismatch" in verdict["failed"]


# ---------------------------------------------------------------------------
# signed_cone_governance helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pos,shadow,expected",
    [
        (3, 0, ALLOW),
        (3, 1, QUARANTINE),
        (3, 2, QUARANTINE),
        (3, 3, QUARANTINE),
        (0, 3, DENY),
        (0, 0, ESCALATE),
        (0, 1, ESCALATE),
        (0, 2, ESCALATE),
        (1, 0, ESCALATE),
        (1, 2, ESCALATE),
        (2, 1, ESCALATE),
        (2, 2, ESCALATE),
    ],
)
def test_signed_cone_governance_matches_truth_table(pos, shadow, expected):
    assert signed_cone_governance(pos, shadow) == expected


def test_signed_cone_governance_rejects_out_of_range():
    with pytest.raises(ValueError):
        signed_cone_governance(-1, 0)
    with pytest.raises(ValueError):
        signed_cone_governance(0, 4)


# ---------------------------------------------------------------------------
# Integration with tri_braid_signature on a real prompt
# ---------------------------------------------------------------------------


def test_real_prompt_produces_valid_cone_signature():
    embedding = build_poly_embedding("plan a paired coding task with verification gate")
    braid = tri_braid_signature(embedding)
    sig = tri_cone_signature(braid)
    assert sig.cone_governance in {ALLOW, QUARANTINE, ESCALATE, DENY}
    assert verify_tri_cone_signature(sig, braid)["ok"] is True


# ---------------------------------------------------------------------------
# tri_cone_signature_from_content convenience entry point
# ---------------------------------------------------------------------------


def test_signature_from_content_matches_explicit_chain():
    """The convenience wrapper must be byte-identical to the long-form chain."""

    content = "plan a paired coding task with verification gate"
    embedding = build_poly_embedding(content)
    braid = tri_braid_signature(embedding)
    expected = tri_cone_signature(braid)
    actual = tri_cone_signature_from_content(content)
    assert actual.cone_hash == expected.cone_hash
    assert actual.cone_governance == expected.cone_governance
    assert actual.positive_membership_count == expected.positive_membership_count
    assert actual.shadow_membership_count == expected.shadow_membership_count


def test_signature_from_content_handles_empty_string():
    """Empty content must not blow up; falls back to a placeholder concept."""

    sig = tri_cone_signature_from_content("")
    assert sig.cone_governance in {ALLOW, QUARANTINE, ESCALATE, DENY}
    assert sig.schema_version == SCHEMA_VERSION


def test_signature_from_content_is_deterministic():
    a = tri_cone_signature_from_content("safe paired coding task")
    b = tri_cone_signature_from_content("safe paired coding task")
    assert a.cone_hash == b.cone_hash


# ---------------------------------------------------------------------------
# Property-based fuzz tests
# ---------------------------------------------------------------------------


_finite_floats = st.floats(min_value=-50.0, max_value=50.0, allow_nan=False, allow_infinity=False)


@given(
    fast=st.lists(_finite_floats, min_size=4, max_size=12),
    memory=st.lists(_finite_floats, min_size=4, max_size=12),
)
@settings(max_examples=80, deadline=None)
def test_fuzz_signature_round_trips(fast, memory):
    """For any finite tri-braid signature, verify must round-trip."""

    n = min(len(fast), len(memory))
    if n < 3:
        return  # tri-braid requires at least 3 dims; hypothesis will widen.
    governance = [(f + m) / 2.0 for f, m in zip(fast[:n], memory[:n])]
    braid = TriBraidSignature(
        schema_version="test",
        fast=tuple(fast[:n]),
        memory=tuple(memory[:n]),
        governance=tuple(governance),
        dominant_axes=(),
        crossing_count=0,
        triadic_stable=0.5,
        ordered_hash="x" * 64,
        decision="ALLOW",
        invariants=(),
    )
    sig = tri_cone_signature(braid)
    assert verify_tri_cone_signature(sig, braid)["ok"] is True


@given(
    fast=_finite_floats,
    memory=_finite_floats,
    governance=_finite_floats,
)
@settings(max_examples=120, deadline=None)
def test_fuzz_membership_counts_in_range(fast, memory, governance):
    """Membership counts always live in 0..3; governance always in the four classes."""

    sig = tri_cone_signature(_braid(fast, memory, governance))
    assert 0 <= sig.positive_membership_count <= 3
    assert 0 <= sig.shadow_membership_count <= 3
    assert sig.cone_governance in {ALLOW, QUARANTINE, ESCALATE, DENY}


@given(
    fast=_finite_floats,
    memory=_finite_floats,
    governance=_finite_floats,
)
@settings(max_examples=80, deadline=None)
def test_fuzz_joint_lives_in_unit_cube(fast, memory, governance):
    sig = tri_cone_signature(_braid(fast, memory, governance))
    for component in sig.joint_embedding:
        assert 0.0 <= component <= 1.0
        assert math.isfinite(component)
    for component in sig.joint_shadow:
        assert 0.0 <= component <= 1.0
        assert math.isfinite(component)


@given(
    fast=_finite_floats,
    memory=_finite_floats,
    governance=_finite_floats,
)
@settings(max_examples=80, deadline=None)
def test_fuzz_plateau_imbalance_in_unit_range(fast, memory, governance):
    sig = tri_cone_signature(_braid(fast, memory, governance))
    assert 0.0 <= sig.plateau_imbalance <= 1.0
