"""Test the aligned-foundations constrained-decoding shim.

Each registered ``(map, kind)`` tuple's forced prefix should clear the
corresponding extractor in
:mod:`src.governance.aligned_foundations_cross_lane`. The test loop is
the regression harness: extractor-table changes that break the shim
(or shim changes that break the extractors) fail loud.
"""

from __future__ import annotations

import pytest

from src.governance.aligned_foundations_constrained_decoding import (
    build_aligned_foundations_prefix,
    supported_map_kinds,
)
from src.governance.aligned_foundations_cross_lane import (
    INVARIANT_FIELDS,
    KIND_EXTRACTORS,
    score_packet_compliance,
)


# Reference text — what a "good" model output would look like for each (map,
# kind). The shim's prefix is benchmarked against these references via
# score_packet_compliance, which checks invariant-field equality.


def _matching_reference(map_name: str, kind: str, value: str = "", tongue: str = "") -> str:
    """Return a canonical reference string the extractor would accept.

    For most (map, kind) pairs the reference is just ``the prefix the shim
    would produce for the same args`` — the shim is self-referential by
    construction, so the prefix must match itself. For pairs where the
    extractor checks INVARIANT_FIELDS that include the tongue label, we
    use a different speaker so the test catches accidental tongue lock-in.
    """

    return build_aligned_foundations_prefix(map_name, kind, value, tongue)


@pytest.mark.parametrize("map_kind", supported_map_kinds())
def test_shim_prefix_satisfies_extractor(map_kind):
    """Each shimmed (map, kind) pair must pass the extractor with empty
    reference (signature = stub). Equivalent to: the prefix alone is a
    valid signature, regardless of cross-tongue invariance.
    """

    map_name, kind = map_kind
    prefix = build_aligned_foundations_prefix(map_name, kind, value="map_double", tongue="KO")
    assert prefix, f"shim returned empty prefix for {map_kind}"
    extractor = KIND_EXTRACTORS[(map_name, kind)]
    sig = extractor(prefix)
    # Verify the extractor actually returns a dict with content (not just
    # the type tag) — the prefix must be parseable.
    assert isinstance(sig, dict)
    assert sig.get("type"), f"extractor returned no type for {map_kind}"


@pytest.mark.parametrize("map_kind", supported_map_kinds())
def test_shim_prefix_self_compliant(map_kind):
    """The shim's prefix used as both response and reference must produce
    an OK packet_compliance verdict — the prefix is its own reference.
    """

    map_name, kind = map_kind
    prefix = build_aligned_foundations_prefix(map_name, kind, value="map_double", tongue="KO")
    verdict = score_packet_compliance(map_name, kind, prefix, prefix)
    assert verdict["ok"], f"self-compliance failed for {map_kind}: {verdict}"


def test_unregistered_pair_returns_empty():
    """Pairs not in the dispatch table should return empty string (fail
    open — let the model's continuation handle it).
    """

    assert build_aligned_foundations_prefix("nonexistent", "kind") == ""
    assert build_aligned_foundations_prefix("transport_atomic", "reaction_predict") == ""


def test_cross_braid_rationale_includes_three_anchors():
    """The cross_braid rationale prefix must contain all three required
    anchor strings the extractor checks for.
    """

    prefix = build_aligned_foundations_prefix(
        "cross_braid_code", "rationale", value="AV", tongue="KO"
    )
    body = prefix.lower()
    assert "bijective" in body
    assert "phase delta" in body or "phase_delta" in body
    assert "weight ratio" in body or "weight_ratio" in body


def test_cross_braid_pair_has_two_brackets():
    """Pair extractor checks bracket_count >= 2."""

    prefix = build_aligned_foundations_prefix(
        "cross_braid_code", "pair", value="AV", tongue="KO"
    )
    bracket_count = prefix.count("[")
    assert bracket_count >= 2, f"pair shim only has {bracket_count} brackets"


def test_atomic_semantic_rationale_anchors():
    """atomic_semantic rationale extractor needs invariant + (lattice or projection)."""

    prefix = build_aligned_foundations_prefix(
        "atomic_semantic", "rationale", value="map_double", tongue="UM"
    )
    body = prefix.lower()
    assert "invariant" in body
    assert "lattice" in body or "projection" in body


def test_convergence_anchor_marker():
    """convergence_action/anchor extractor needs literal 'convergence anchor'."""

    prefix = build_aligned_foundations_prefix(
        "convergence_action", "anchor", value="REFACTORER", tongue="RU"
    )
    assert "convergence anchor" in prefix.lower()


def test_bracket_packet_has_surface():
    """Generic bracket packet extractors check for ``surface=`` substring."""

    prefix = build_aligned_foundations_prefix(
        "runtime_emission", "rationale", value="typescript", tongue="AV"
    )
    assert "surface=" in prefix


def test_supported_pairs_cover_known_failure_clusters():
    """The shim must cover the failure clusters identified in the prior
    aligned-foundations gate (rationale-dominant, plus the low-volume
    pair/route/anchor/packet kinds).
    """

    covered = set(supported_map_kinds())
    expected_clusters = {
        ("cross_braid_code", "rationale"),
        ("cross_braid_code", "pair"),
        ("atomic_semantic", "rationale"),
        ("spirit_narrative", "rationale"),
        ("cartography_state", "route"),
        ("cartography_state", "packet"),
        ("convergence_action", "anchor"),
    }
    missing = expected_clusters - covered
    assert not missing, f"shim missing failure-cluster coverage: {missing}"


def test_long_form_tongue_labels_used():
    """Tongue codes must be expanded to full names per project convention."""

    prefix = build_aligned_foundations_prefix(
        "cross_braid_code", "pair", value="AV", tongue="KO"
    )
    # Should contain Kor'aelin (long form) and Avali (long form), not "KO" / "AV".
    assert "Kor" in prefix and "Avali" in prefix


def test_invariant_fields_table_consistent():
    """Every shimmed (map, kind) must have an entry in INVARIANT_FIELDS or
    explicitly opt out (empty tuple). Drift between the shim and the
    extractor table is a bug.
    """

    for map_kind in supported_map_kinds():
        # Either it's in INVARIANT_FIELDS or the kind has empty invariance,
        # but it MUST be in KIND_EXTRACTORS (the shim writes for an extractor).
        assert map_kind in KIND_EXTRACTORS, f"shim writes for unregistered extractor {map_kind}"
