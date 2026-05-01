"""Drift-guard tests for the cross-lane scorer CLI helpers.

The primitives module (``src/governance/aligned_foundations_cross_lane.py``)
is covered by ``tests/governance/test_aligned_foundations_cross_lane.py``;
this file locks in the CLI-runner glue (concept aggregation, threshold rule,
per-record entry shape, summary numerics).
"""

from __future__ import annotations

from scripts.eval.score_aligned_foundations_cross_lane import (
    _aggregate_concept_verdicts,
    _build_per_record_entry,
    _decide,
    _format_summary,
)

CANONICAL_CA = (
    "[Cassisivadan/mathematica] predict products under atom conservation.\n"
    "reactants: 2Na + 2H2O\n"
    "reaction_class: displacement\n"
    "stability: unstable\n"
    "products: 2NaOH + H2"
)
CANONICAL_UM = (
    "[Umbroth/haskell] predict products under atom conservation.\n"
    "reactants: 2H2 + O2\n"
    "reaction_class: synthesis\n"
    "stability: stable\n"
    "products: 2H2O"
)


def _record(map_name: str, kind: str, tongue: str, value: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user prompt"},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {"map": map_name, "kind": kind, "tongue": tongue, "value": value},
    }


def test_aggregate_groups_by_concept_tuple():
    rec_ca = _record("transport_atomic", "reaction_predict", "CA", "unstable", CANONICAL_CA)
    rec_um = _record("transport_atomic", "reaction_predict", "UM", "stable", CANONICAL_UM)
    rec_ca_other = _record("transport_atomic", "reaction_predict", "CA", "stable", CANONICAL_CA)
    verdicts = _aggregate_concept_verdicts(
        [(rec_ca, CANONICAL_CA), (rec_um, CANONICAL_UM), (rec_ca_other, CANONICAL_CA)]
    )
    keys = {(v["map"], v["kind"], v["value"]) for v in verdicts}
    assert keys == {
        ("transport_atomic", "reaction_predict", "unstable"),
        ("transport_atomic", "reaction_predict", "stable"),
    }


def test_aggregate_multi_tongue_invariance_passes_for_canonical():
    rec_ca = _record("transport_atomic", "reaction_predict", "CA", "unstable", CANONICAL_CA)
    rec_um = _record("transport_atomic", "reaction_predict", "UM", "unstable", CANONICAL_UM)
    verdicts = _aggregate_concept_verdicts([(rec_ca, CANONICAL_CA), (rec_um, CANONICAL_UM)])
    assert len(verdicts) == 1
    v = verdicts[0]
    assert v["n_tongues"] == 2
    assert v["invariance_ok"] is True
    assert v["all_compliant"] is True


def test_build_per_record_entry_carries_shape_and_meta():
    rec = _record("transport_atomic", "reaction_predict", "CA", "unstable", CANONICAL_CA)
    entry = _build_per_record_entry(rec, CANONICAL_CA)
    assert entry["meta"] == {
        "map": "transport_atomic",
        "kind": "reaction_predict",
        "tongue": "CA",
        "value": "unstable",
    }
    assert entry["ok"] is True
    assert entry["error"] is None
    assert entry["actual_signature"]["type"] == "transport_atomic_packet"


def test_build_per_record_entry_unmapped_kind_fails_closed():
    rec = _record("nonexistent_map", "nonexistent_kind", "CA", "x", "body")
    entry = _build_per_record_entry(rec, "ref")
    assert entry["ok"] is False
    assert entry["error"] == "not_implemented"


def test_format_summary_numerics():
    summary = _format_summary(
        n_records=10,
        n_compliant=8,
        n_concepts=5,
        n_multi_tongue=3,
        n_invariant=2,
        n_unmapped=0,
    )
    assert summary["pass_rate_packet_compliance"] == 0.8
    assert abs(summary["pass_rate_concept_invariance"] - (2 / 3)) < 1e-9
    assert summary["n_unmapped_kinds_seen"] == 0


def test_format_summary_no_multi_tongue_concepts_yields_unit_invariance():
    """If every concept is single-tongue, invariance pass rate defaults to 1.0
    (there's nothing to violate). Avoids ZeroDivisionError + hidden False."""
    summary = _format_summary(
        n_records=2,
        n_compliant=2,
        n_concepts=2,
        n_multi_tongue=0,
        n_invariant=0,
        n_unmapped=0,
    )
    assert summary["pass_rate_concept_invariance"] == 1.0


def test_decide_promotes_when_both_thresholds_clear_and_no_unmapped():
    summary = _format_summary(
        n_records=10,
        n_compliant=9,
        n_concepts=5,
        n_multi_tongue=4,
        n_invariant=4,
        n_unmapped=0,
    )
    assert _decide(summary, 0.80, 0.80) is True


def test_decide_holds_when_unmapped_kinds_seen():
    """Even at perfect packet + invariance rates, the presence of any unmapped
    kind blocks promotion (silent passes are forbidden)."""
    summary = _format_summary(
        n_records=10,
        n_compliant=10,
        n_concepts=5,
        n_multi_tongue=4,
        n_invariant=4,
        n_unmapped=1,
    )
    assert _decide(summary, 0.80, 0.80) is False


def test_decide_holds_when_either_threshold_misses():
    summary_low_packet = _format_summary(
        n_records=10,
        n_compliant=5,
        n_concepts=5,
        n_multi_tongue=4,
        n_invariant=4,
        n_unmapped=0,
    )
    summary_low_invariance = _format_summary(
        n_records=10,
        n_compliant=10,
        n_concepts=5,
        n_multi_tongue=4,
        n_invariant=1,
        n_unmapped=0,
    )
    assert _decide(summary_low_packet, 0.80, 0.80) is False
    assert _decide(summary_low_invariance, 0.80, 0.80) is False
