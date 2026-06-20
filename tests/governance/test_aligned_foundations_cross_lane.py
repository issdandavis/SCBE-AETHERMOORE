"""Drift-guard tests for the aligned-foundations cross-lane eval scaffold.

Two layers:

1. **Unit extractors** — synthetic canonical samples per (map, kind), confirm
   each extractor returns the right envelope shape.
2. **Self-test** — run every extractor against the actual canonical training
   targets in ``training-data/sft/drill_langues_full_train.sft.jsonl`` and
   assert that same-(map, kind, value) groups produce matching invariant
   signatures. If canonical training targets fail invariance, the extractor
   (not the model) is wrong.

The self-test is the contract: it locks in the meaning of "the extractor is
correct" against ground truth, so any future change to extractors or
INVARIANT_FIELDS must keep the canonical training data passing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.governance.aligned_foundations_cross_lane import (
    INVARIANT_FIELDS,
    KIND_EXTRACTORS,
    aligned_foundations_concept_verdict,
    extract_packet_signature,
    group_records_by_concept,
    reference_assistant_text,
    score_cross_lane_invariance,
    score_packet_compliance,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRAIN_PATH = PROJECT_ROOT / "training-data" / "sft" / "drill_langues_full_train.sft.jsonl"
HOLDOUT_PATH = PROJECT_ROOT / "training-data" / "sft" / "drill_langues_full_holdout.sft.jsonl"


# ---------------------------------------------------------------------------
# Unit extractor tests (synthetic samples)
# ---------------------------------------------------------------------------


def test_transport_atomic_reaction_predict_extractor():
    sample = (
        "[Cassisivadan/mathematica] predict products under atom conservation.\n"
        "reactants: 2Na + 2H2O\n"
        "reaction_class: displacement\n"
        "stability: unstable\n"
        "products: 2NaOH + H2"
    )
    sig = extract_packet_signature("transport_atomic", "reaction_predict", sample)
    assert sig["type"] == "transport_atomic_packet"
    assert sig["verb_phrase"] == "predict products under atom conservation"
    assert sig["kv_keys"] == frozenset({"reactants", "reaction_class", "stability", "products"})


def test_transport_atomic_reaction_predict_invariance_across_tongues():
    ca_sample = (
        "[Cassisivadan/mathematica] predict products under atom conservation.\n"
        "reactants: 2Na + 2H2O\n"
        "reaction_class: displacement\n"
        "stability: unstable\n"
        "products: 2NaOH + H2"
    )
    um_sample = (
        "[Umbroth/haskell] predict products under atom conservation.\n"
        "reactants: 2H2 + O2\n"
        "reaction_class: synthesis\n"
        "stability: stable\n"
        "products: 2H2O"
    )
    verdict = score_cross_lane_invariance(
        "transport_atomic",
        "reaction_predict",
        {"CA": ca_sample, "UM": um_sample},
    )
    assert verdict["ok"], verdict["mismatches"]


def test_transport_atomic_reaction_predict_invariance_breaks_on_missing_field():
    full = (
        "[Cassisivadan/mathematica] predict products under atom conservation.\n"
        "reactants: 2Na + 2H2O\n"
        "reaction_class: displacement\n"
        "stability: unstable\n"
        "products: 2NaOH + H2"
    )
    truncated = "[Umbroth/haskell] predict products under atom conservation.\n" "reactants: 2H2 + O2"
    verdict = score_cross_lane_invariance(
        "transport_atomic",
        "reaction_predict",
        {"CA": full, "UM": truncated},
    )
    assert not verdict["ok"]
    assert any(m["field"] == "kv_keys" for m in verdict["mismatches"])


def test_bracket_packet_extractor_runtime_emission():
    sample = (
        "[runtime_emission]\n"
        "tongue=Avali binary_lane=001 comma_step=1 decimal_drift=1.0136432648 gear=couple\n"
        "lane_value=typescript family=runtime\n"
        "surface=const square = (x: number): number => x * x;"
    )
    sig = extract_packet_signature("runtime_emission", "code", sample)
    assert sig["header_label"] == "runtime_emission"
    assert sig["has_surface"] is True
    assert {"tongue", "binary_lane", "lane_value", "family", "surface"} <= sig["kv_keys"]


def test_cross_braid_pair_extractor():
    sample = (
        "Cross-braid Draumric -> Umbroth (phase_delta=5.2360 rad, weight_ratio=0.6180):\n"
        "[Draumric]\n- Reduce `xs` under addition.\n"
        "[Umbroth]\nsum xs"
    )
    sig = extract_packet_signature("cross_braid_code", "pair", sample)
    assert sig["has_header"] is True
    assert sig["bracket_count"] == 2


def test_qa_invariance_extractor_phi_ladder():
    sample = "phi^n where phi = (1 + sqrt(5))/2. phi = (1 + sqrt(5))/2 = 1.618034. " "phi^10 = 122.991869."
    sig = extract_packet_signature("qa_invariance", "phi_ladder", sample)
    assert sig["type"] == "qa_invariance"
    assert sig["has_equals"] is True


def test_unmapped_kind_fails_closed():
    verdict = score_packet_compliance("nonexistent_map", "nonexistent_kind", "x", "y")
    assert verdict["ok"] is False
    assert verdict["error"] == "not_implemented"

    inv = score_cross_lane_invariance("nonexistent_map", "nonexistent_kind", {"KO": "a", "AV": "b"})
    assert inv["ok"] is False
    assert inv["error"] == "not_implemented"

    concept = aligned_foundations_concept_verdict(
        "nonexistent_map",
        "nonexistent_kind",
        "v",
        {"KO": "a"},
        {"KO": "ref"},
    )
    assert concept["ok"] is False
    assert concept["error"] == "not_implemented"


def test_concept_verdict_single_tongue_skips_invariance():
    sample = (
        "[Cassisivadan/mathematica] predict products under atom conservation.\n"
        "reactants: 2Na + 2H2O\n"
        "reaction_class: displacement\n"
        "stability: unstable\n"
        "products: 2NaOH + H2"
    )
    verdict = aligned_foundations_concept_verdict(
        "transport_atomic",
        "reaction_predict",
        "unstable",
        {"CA": sample},
        {"CA": sample},
    )
    assert verdict["ok"] is True
    assert verdict["n_tongues"] == 1
    assert verdict["invariance"]["skipped_reason"] == "single_tongue_concept"


def test_invariant_fields_are_subset_of_extractor_keys():
    """Every field listed in INVARIANT_FIELDS must be a key the extractor
    actually returns. Catches typos at module load time."""
    for (map_name, kind), fields in INVARIANT_FIELDS.items():
        if not fields:
            continue
        extractor = KIND_EXTRACTORS[(map_name, kind)]
        sample_sig = extractor("placeholder body")
        for field in fields:
            assert field in sample_sig, (
                f"INVARIANT_FIELDS for ({map_name}, {kind}) lists "
                f"{field!r} but extractor doesn't return it. "
                f"Extractor keys: {sorted(sample_sig)}"
            )


def test_every_extractor_has_invariant_field_entry():
    """Every (map, kind) in KIND_EXTRACTORS must have an INVARIANT_FIELDS entry
    (even if empty tuple). Forces explicit decision on what's invariant."""
    missing = [k for k in KIND_EXTRACTORS if k not in INVARIANT_FIELDS]
    assert not missing, f"Missing INVARIANT_FIELDS for: {missing}"


# ---------------------------------------------------------------------------
# Self-test against canonical training data
# ---------------------------------------------------------------------------


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        pytest.skip(f"data file not present: {path}")
    out: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def test_train_holdout_coverage_no_unmapped_kinds():
    """Every (map, kind) appearing in train+holdout must be in KIND_EXTRACTORS.
    Drift-guard: catches new kinds added to the dataset before they can
    silently fail-closed in scoring runs."""
    rows = _load_jsonl(TRAIN_PATH) + _load_jsonl(HOLDOUT_PATH)
    seen = {(r["meta"]["map"], r["meta"]["kind"]) for r in rows}
    unmapped = sorted(seen - set(KIND_EXTRACTORS.keys()))
    assert not unmapped, f"Unmapped (map, kind) pairs in dataset (will fail-closed in scoring): " f"{unmapped}"


def test_canonical_train_targets_pass_invariance():
    """The strongest contract: run every extractor against canonical training
    targets and confirm same-(map, kind, value) groups produce matching
    invariant signatures.

    If this test fails, either:
      - The extractor is wrong (does not capture the right envelope), OR
      - INVARIANT_FIELDS lists a field that legitimately varies per tongue
        in the canonical data (which means the field isn't actually invariant).

    Either way, the model could not be expected to satisfy a check that
    canonical training data fails. So this test must always pass."""
    rows = _load_jsonl(TRAIN_PATH)
    groups = group_records_by_concept(rows)
    failures: list[dict] = []
    for (map_name, kind, value), recs in groups.items():
        if (map_name, kind) not in KIND_EXTRACTORS:
            failures.append(
                {
                    "concept": (map_name, kind, value),
                    "reason": "unmapped_kind",
                }
            )
            continue
        per_tongue = {rec["meta"]["tongue"]: reference_assistant_text(rec) for rec in recs}
        if len(per_tongue) < 2:
            continue
        verdict = score_cross_lane_invariance(map_name, kind, per_tongue)
        if not verdict["ok"]:
            failures.append(
                {
                    "concept": (map_name, kind, value),
                    "n_tongues": len(per_tongue),
                    "mismatches": verdict["mismatches"][:3],
                }
            )
    assert not failures, f"{len(failures)} canonical training concept(s) fail invariance. " f"First 3: {failures[:3]}"


def test_canonical_train_targets_pass_self_compliance():
    """Each canonical training target must be packet-compliant against itself.
    Tautological but it confirms the extractor returns stable signatures
    (deterministic) and that invariant fields don't depend on field order."""
    rows = _load_jsonl(TRAIN_PATH)
    failures: list[dict] = []
    for rec in rows:
        meta = rec["meta"]
        target = reference_assistant_text(rec)
        verdict = score_packet_compliance(meta["map"], meta["kind"], target, target)
        if not verdict["ok"]:
            failures.append(
                {
                    "meta": meta,
                    "diffs": verdict.get("diffs"),
                    "error": verdict.get("error"),
                }
            )
    assert not failures, f"Self-compliance failed for {len(failures)} targets. First 3: {failures[:3]}"
