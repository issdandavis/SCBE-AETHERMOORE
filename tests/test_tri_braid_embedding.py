"""Tests for the tri-vector cross-braid embedding layer."""

from dataclasses import asdict, replace

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from python.scbe.poly_embedded_jepa import build_poly_embedding
from python.scbe.tri_braid_embedding import (
    ALLOW,
    BACKWARD_CHECK,
    COLLAPSE_ATTRACTOR,
    CREATIVE_TENSION_A,
    CREATIVE_TENSION_B,
    DENY,
    FORWARD_THRUST,
    GOVERNANCE_RECEIPT_SCHEMA,
    PERPENDICULAR_NEG,
    PERPENDICULAR_POS,
    QUARANTINE,
    RESONANT_LOCK,
    SACRED_EGG_SCHEMA,
    SCHEMA_VERSION,
    SacredEggSeal,
    TriadicAxisAnchor,
    ZERO_GRAVITY_STATE,
    _adjacent_swap_generator,
    _governance_vector,
    _ordered_hash,
    braid_exponent_sum,
    braid_word,
    braid_word_length,
    braid_writhe,
    classify_braid_governance,
    extract_axis_anchors,
    governance_receipt,
    seal_sacred_egg,
    temporal_braid_admit,
    tri_braid_signature,
    verify_sacred_egg,
    verify_tri_braid_signature,
)

CONCEPTS = st.from_regex(r"[A-Za-z][A-Za-z0-9 _\-]{0,40}", fullmatch=True)
ROWS = st.integers(min_value=0, max_value=5)
COLS = st.integers(min_value=0, max_value=5)
PROP = settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def _embedding(concept="probe", row=2, col=3):
    return build_poly_embedding(concept, masked_row=row, masked_col=col)


def test_signature_round_trips_through_verifier():
    sig = tri_braid_signature(_embedding())
    report = verify_tri_braid_signature(sig, _embedding())
    assert report["ok"] is True, report["failed"]
    assert sig.schema_version == SCHEMA_VERSION


def test_decision_is_one_of_three_governance_states():
    sig = tri_braid_signature(_embedding())
    assert sig.decision in {ALLOW, QUARANTINE, DENY}


def test_dominant_axes_use_canonical_labels():
    sig = tri_braid_signature(_embedding())
    assert len(sig.dominant_axes) == len(sig.fast)
    for axis in sig.dominant_axes:
        assert axis in {"fast", "memory", "governance"}


def test_crossing_count_is_within_bounds():
    sig = tri_braid_signature(_embedding())
    assert 0 <= sig.crossing_count < len(sig.fast)


def test_ordered_hash_is_non_commutative_under_permutation():
    sig = tri_braid_signature(_embedding())
    permuted = _ordered_hash(sig.memory, sig.fast, sig.governance)
    permuted2 = _ordered_hash(sig.governance, sig.memory, sig.fast)
    assert sig.ordered_hash != permuted
    assert sig.ordered_hash != permuted2
    assert permuted != permuted2


def test_signature_is_deterministic_for_same_concept():
    a = tri_braid_signature(_embedding("same concept", row=1, col=4))
    b = tri_braid_signature(_embedding("same concept", row=1, col=4))
    assert a == b


def test_signatures_differ_for_different_concepts():
    a = tri_braid_signature(_embedding("concept alpha"))
    b = tri_braid_signature(_embedding("concept beta"))
    assert a.ordered_hash != b.ordered_hash


def test_tampered_crossing_count_fails_verification():
    sig = tri_braid_signature(_embedding())
    bumped = replace(sig, crossing_count=sig.crossing_count + 99)
    report = verify_tri_braid_signature(bumped, _embedding())
    assert report["ok"] is False
    assert "crossing_count_matches" in report["failed"]


def test_tampered_ordered_hash_fails_verification():
    sig = tri_braid_signature(_embedding())
    forged = replace(sig, ordered_hash="0" * 64)
    report = verify_tri_braid_signature(forged, _embedding())
    assert report["ok"] is False
    assert "ordered_hash_matches" in report["failed"]


def test_swapping_fast_and_memory_changes_hash():
    sig = tri_braid_signature(_embedding())
    swapped = replace(sig, fast=sig.memory, memory=sig.fast)
    # The verifier recomputes from the embedding so it should still
    # detect the surface mismatch on the tampered signature itself.
    report = verify_tri_braid_signature(swapped, _embedding())
    assert report["ok"] is False
    assert "fast_matches" in report["failed"] or "memory_matches" in report["failed"]


def test_governance_vector_has_six_dimensions():
    embedding = _embedding()
    gov = _governance_vector(embedding.coding_systems)
    assert len(gov) == 6
    # at least one entry should be non-zero given the default systems
    assert any(value != 0.0 for value in gov)


def test_signature_invariants_describe_the_contract():
    sig = tri_braid_signature(_embedding())
    expected = {
        "vectors_share_length",
        "axes_in_three_label_set",
        "crossing_count_in_zero_to_n_minus_one",
        "ordered_hash_is_non_commutative",
        "decision_in_allow_quarantine_deny",
    }
    assert set(sig.invariants) == expected


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_signature_round_trips_for_any_valid_input(concept, row, col):
    embedding = build_poly_embedding(concept, masked_row=row, masked_col=col)
    sig = tri_braid_signature(embedding)
    report = verify_tri_braid_signature(sig, embedding)
    assert report["ok"] is True, report["failed"]


def test_axis_anchors_have_valid_shape():
    sig = tri_braid_signature(_embedding())
    anchors = extract_axis_anchors(sig)
    for anchor in anchors:
        assert isinstance(anchor, TriadicAxisAnchor)
        assert len(anchor.axes) == 3
        assert all(0 <= axis <= 5 for axis in anchor.axes)
        assert len(set(anchor.axes)) == 3
        assert anchor.axes == tuple(sorted(anchor.axes))
        assert all(value in {-1, 0, 1} for value in anchor.sign_pattern)
        assert 0.0 <= anchor.cross_lane_stability <= 1.0
        assert anchor.mean_strength >= 0.0


def test_axis_anchors_sorted_by_quality_descending():
    sig = tri_braid_signature(_embedding("matrix multiply lsp"))
    anchors = extract_axis_anchors(sig)
    qualities = [anchor.quality for anchor in anchors]
    assert qualities == sorted(qualities, reverse=True)


def test_axis_anchor_quality_is_stability_times_strength():
    sig = tri_braid_signature(_embedding("Sacred Tongue chemistry valence"))
    anchors = extract_axis_anchors(sig)
    for anchor in anchors:
        expected = round(anchor.cross_lane_stability * anchor.mean_strength, 8)
        assert anchor.quality == expected


def test_strict_min_stability_keeps_only_unanimous_anchors():
    sig = tri_braid_signature(_embedding("anchor stability probe"))
    strict = extract_axis_anchors(sig, min_stability=1.0)
    for anchor in strict:
        assert anchor.cross_lane_stability == 1.0


def test_min_strength_filters_out_weak_anchors():
    sig = tri_braid_signature(_embedding("filter probe"))
    weak = extract_axis_anchors(sig, min_strength=0.0)
    strong = extract_axis_anchors(sig, min_strength=1e6)
    assert len(strong) == 0
    assert len(weak) >= len(strong)


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_anchors_always_extractable(concept, row, col):
    embedding = build_poly_embedding(concept, masked_row=row, masked_col=col)
    sig = tri_braid_signature(embedding)
    anchors = extract_axis_anchors(sig)
    assert isinstance(anchors, tuple)
    for anchor in anchors:
        assert anchor.cross_lane_stability >= 2.0 / 3.0


def test_adjacent_generators_match_b3_definition():
    assert _adjacent_swap_generator("fast", "memory") == (1,)
    assert _adjacent_swap_generator("memory", "fast") == (-1,)
    assert _adjacent_swap_generator("memory", "governance") == (2,)
    assert _adjacent_swap_generator("governance", "memory") == (-2,)
    assert _adjacent_swap_generator("fast", "governance") == (1, 2)
    assert _adjacent_swap_generator("governance", "fast") == (-2, -1)
    assert _adjacent_swap_generator("fast", "fast") == ()


def test_braid_word_uses_only_b3_generators():
    sig = tri_braid_signature(_embedding("braid word probe"))
    word = braid_word(sig)
    for generator in word:
        assert generator in {-2, -1, 1, 2}


def test_braid_word_length_matches_explicit_call():
    sig = tri_braid_signature(_embedding("length probe"))
    assert braid_word_length(sig) == len(braid_word(sig))


def test_braid_word_length_at_least_crossing_count():
    sig = tri_braid_signature(_embedding("length lower bound"))
    assert braid_word_length(sig) >= sig.crossing_count


def test_braid_word_is_deterministic_for_same_input():
    a = braid_word(tri_braid_signature(_embedding("same braid input")))
    b = braid_word(tri_braid_signature(_embedding("same braid input")))
    assert a == b


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_braid_word_is_well_formed(concept, row, col):
    embedding = build_poly_embedding(concept, masked_row=row, masked_col=col)
    sig = tri_braid_signature(embedding)
    word = braid_word(sig)
    assert isinstance(word, tuple)
    for generator in word:
        assert generator in {-2, -1, 1, 2}
    assert braid_word_length(sig) >= sig.crossing_count


# ---------------------------------------------------------------------------
# Knot/braid invariants
# ---------------------------------------------------------------------------


def test_exponent_sum_equals_signed_generator_count():
    sig = tri_braid_signature(_embedding("exponent probe"))
    word = braid_word(sig)
    expected = sum(1 if g > 0 else -1 for g in word)
    assert braid_exponent_sum(sig) == expected


def test_writhe_matches_exponent_sum():
    sig = tri_braid_signature(_embedding("writhe probe"))
    assert braid_writhe(sig) == braid_exponent_sum(sig)


def test_exponent_sum_bounded_by_word_length():
    sig = tri_braid_signature(_embedding("bound probe"))
    assert abs(braid_exponent_sum(sig)) <= braid_word_length(sig)


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_exponent_sum_is_integer_invariant(concept, row, col):
    embedding = build_poly_embedding(concept, masked_row=row, masked_col=col)
    sig = tri_braid_signature(embedding)
    summed = braid_exponent_sum(sig)
    assert isinstance(summed, int)
    assert -braid_word_length(sig) <= summed <= braid_word_length(sig)


# ---------------------------------------------------------------------------
# Hamiltonian-Braid 9-state governance
# ---------------------------------------------------------------------------

_BRAID_STATES = {
    RESONANT_LOCK,
    FORWARD_THRUST,
    CREATIVE_TENSION_A,
    PERPENDICULAR_POS,
    ZERO_GRAVITY_STATE,
    PERPENDICULAR_NEG,
    CREATIVE_TENSION_B,
    BACKWARD_CHECK,
    COLLAPSE_ATTRACTOR,
}


def test_braid_governance_returns_known_state():
    gov = classify_braid_governance(tri_braid_signature(_embedding()))
    assert gov.state in _BRAID_STATES


def test_braid_governance_trits_are_ternary():
    gov = classify_braid_governance(tri_braid_signature(_embedding()))
    assert gov.primary_trit in {-1, 0, 1}
    assert gov.mirror_trit in {-1, 0, 1}


def test_braid_governance_trust_levels_are_canonical():
    gov = classify_braid_governance(tri_braid_signature(_embedding()))
    assert gov.trust_level in {"maximum", "high", "medium", "consensus", "low", "audit", "block"}


def test_braid_governance_security_actions_are_canonical():
    gov = classify_braid_governance(tri_braid_signature(_embedding()))
    assert gov.security_action in {
        "INSTANT_APPROVE",
        "STANDARD_PATH",
        "FRACTAL_INSPECT",
        "REANCHOR",
        "HOLD_QUORUM",
        "ROLLBACK",
        "HARD_DENY",
    }


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_braid_governance_is_well_formed(concept, row, col):
    embedding = build_poly_embedding(concept, masked_row=row, masked_col=col)
    gov = classify_braid_governance(tri_braid_signature(embedding))
    assert gov.state in _BRAID_STATES
    assert gov.primary_trit in {-1, 0, 1}
    assert gov.mirror_trit in {-1, 0, 1}


# ---------------------------------------------------------------------------
# L11 temporal admissibility
# ---------------------------------------------------------------------------


def test_identical_triple_admits():
    sig = tri_braid_signature(_embedding("temporal identity"))
    report = temporal_braid_admit(sig, sig, sig)
    assert report.admit is True
    assert report.velocity == 0.0
    assert report.acceleration == 0.0
    assert report.causality_monotone is True


def test_temporal_velocity_bound_can_fail():
    sig = tri_braid_signature(_embedding("velocity probe"))
    # Set a punishingly tight velocity limit so any non-zero step trips it.
    spread_a = tri_braid_signature(_embedding("velocity probe spread A"))
    spread_b = tri_braid_signature(_embedding("velocity probe spread B"))
    report = temporal_braid_admit(sig, spread_a, spread_b, velocity_limit=0.0)
    assert report.velocity_within_bound is False
    assert report.admit is False


def test_temporal_admit_report_lists_decision_levels_correctly():
    sig = tri_braid_signature(_embedding("decision level probe"))
    report = temporal_braid_admit(sig, sig, sig)
    # all three decisions equal so causality is satisfied trivially
    assert report.causality_monotone is True


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_self_triple_always_admits(concept, row, col):
    sig = tri_braid_signature(build_poly_embedding(concept, masked_row=row, masked_col=col))
    report = temporal_braid_admit(sig, sig, sig)
    assert report.admit is True


# ---------------------------------------------------------------------------
# Sacred Egg seal
# ---------------------------------------------------------------------------


def test_sacred_egg_seal_round_trips():
    sig = tri_braid_signature(_embedding("sacred egg probe"))
    seal = seal_sacred_egg(sig)
    assert isinstance(seal, SacredEggSeal)
    assert seal.schema_version == SACRED_EGG_SCHEMA
    report = verify_sacred_egg(seal, sig)
    assert report["ok"] is True, report["failed"]


def test_sacred_egg_seal_is_deterministic():
    sig = tri_braid_signature(_embedding("egg determinism"))
    a = seal_sacred_egg(sig)
    b = seal_sacred_egg(sig)
    assert a == b


def test_sacred_egg_ring_index_in_range():
    sig = tri_braid_signature(_embedding("ring range"))
    seal = seal_sacred_egg(sig)
    assert 0 <= seal.ring_index <= 5
    assert 0.0 < seal.ring_radius <= 1.0


def test_tampered_sacred_egg_fails_verification():
    sig = tri_braid_signature(_embedding("egg tamper"))
    seal = seal_sacred_egg(sig)
    forged = SacredEggSeal(
        schema_version=seal.schema_version,
        ordered_hash=seal.ordered_hash,
        ring_index=seal.ring_index,
        ring_radius=seal.ring_radius,
        egg_seal_sha3="0" * 64,
    )
    report = verify_sacred_egg(forged, sig)
    assert report["ok"] is False
    assert "seal_recomputes" in report["failed"]


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_sacred_egg_round_trips(concept, row, col):
    sig = tri_braid_signature(build_poly_embedding(concept, masked_row=row, masked_col=col))
    seal = seal_sacred_egg(sig)
    report = verify_sacred_egg(seal, sig)
    assert report["ok"] is True, report["failed"]


# ---------------------------------------------------------------------------
# Production governance receipt
# ---------------------------------------------------------------------------


_RECEIPT_KEYS = {
    "schema_version",
    "binary_packet_sha256",
    "ordered_hash",
    "crossing_count",
    "triadic_stable",
    "decision",
    "braid_word_length",
    "braid_exponent_sum",
    "governance_state",
    "primary_trit",
    "mirror_trit",
    "trust_level",
    "security_action",
    "egg_seal_sha3",
    "ring_index",
    "ring_radius",
    "tile",
    "tongue",
    # Tri-chromatic signed-cone fields (added by tri_cone_embedding fusion).
    "cone_governance",
    "cone_hash",
    "cone_positive_count",
    "cone_shadow_count",
    "cone_triple_intersection_score",
    "cone_triple_shadow_score",
    "cone_interference_score",
    "cone_plateau_imbalance",
    "cone_joint_embedding",
    "cone_joint_shadow",
}


def test_governance_receipt_has_full_schema():
    receipt = governance_receipt("matrix multiply with LSP diagnostic")
    assert set(receipt.keys()) == _RECEIPT_KEYS
    assert receipt["schema_version"] == GOVERNANCE_RECEIPT_SCHEMA


def test_governance_receipt_decision_is_canonical():
    receipt = governance_receipt("test content for governance")
    assert receipt["decision"] in {ALLOW, QUARANTINE, DENY}


def test_governance_receipt_is_deterministic():
    a = governance_receipt("deterministic content")
    b = governance_receipt("deterministic content")
    assert a == b


def test_governance_receipt_changes_with_content():
    a = governance_receipt("content alpha")
    b = governance_receipt("content beta")
    assert a["binary_packet_sha256"] != b["binary_packet_sha256"]
    assert a["ordered_hash"] != b["ordered_hash"]


def test_governance_receipt_rejects_empty_content():
    with pytest.raises(ValueError, match="non-empty"):
        governance_receipt("")
    with pytest.raises(ValueError, match="non-empty"):
        governance_receipt("   \n\t  ")


def test_governance_receipt_is_json_serializable():
    import json

    receipt = governance_receipt("serialization probe")
    payload = json.dumps(receipt)
    restored = json.loads(payload)
    assert restored["ordered_hash"] == receipt["ordered_hash"]


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_governance_receipt_well_formed(concept, row, col):
    receipt = governance_receipt(concept, masked_row=row, masked_col=col)
    assert set(receipt.keys()) == _RECEIPT_KEYS
    assert receipt["decision"] in {ALLOW, QUARANTINE, DENY}
    assert isinstance(receipt["binary_packet_sha256"], str)
    assert len(receipt["binary_packet_sha256"]) == 64
    assert isinstance(receipt["ordered_hash"], str)
    assert len(receipt["ordered_hash"]) == 64
    assert receipt["primary_trit"] in {-1, 0, 1}
    assert receipt["mirror_trit"] in {-1, 0, 1}
    assert receipt["cone_governance"] in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
    assert isinstance(receipt["cone_hash"], str)
    assert len(receipt["cone_hash"]) == 64
    assert 0 <= receipt["cone_positive_count"] <= 3
    assert 0 <= receipt["cone_shadow_count"] <= 3
    assert 0.0 <= receipt["cone_plateau_imbalance"] <= 1.0
    assert len(receipt["cone_joint_embedding"]) == 3
    assert len(receipt["cone_joint_shadow"]) == 3


@PROP
@given(CONCEPTS, ROWS, COLS)
def test_property_signature_dataclass_is_serializable(concept, row, col):
    embedding = build_poly_embedding(concept, masked_row=row, masked_col=col)
    sig = tri_braid_signature(embedding)
    payload = asdict(sig)
    # Round-trip through dict surfaces all fields without raising.
    assert payload["schema_version"] == SCHEMA_VERSION
    assert isinstance(payload["fast"], tuple)
    assert isinstance(payload["memory"], tuple)
    assert isinstance(payload["governance"], tuple)
    assert isinstance(payload["dominant_axes"], tuple)
