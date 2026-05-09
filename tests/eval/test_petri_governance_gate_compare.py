"""Tests for the Petri governance-gate run-comparison tool."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.eval.petri_governance_gate_compare import compare, render_markdown


def _seed(seed_id, verdict, *, tags=None, op=None, band=None, conf=None, err_type=None, err_msg=None) -> dict:
    return {
        "seed_id": seed_id,
        "tags": list(tags or []),
        "verdict": verdict,
        "op_name": op,
        "op_band": band,
        "dst_tongue": "KO",
        "confidence": conf,
        "error_type": err_type,
        "error_message": err_msg,
        "elapsed_s": 1.0,
    }


def _report(per_seed, model="m", args_mode="dummy", quar_ratio=None) -> dict:
    n = len(per_seed)
    n_allow = sum(1 for s in per_seed if s["verdict"] == "ALLOW")
    qr = quar_ratio if quar_ratio is not None else (n - n_allow) / max(1, n)
    return {
        "ollama_model": model,
        "args_mode": args_mode,
        "summary": {
            "total_seeds": n,
            "verdict_counts": {"ALLOW": n_allow, "QUARANTINE": n - n_allow},
            "quarantine_ratio": qr,
        },
        "per_seed": per_seed,
    }


# ---------------------------------------------------------------------------
#  Headline + transitions
# ---------------------------------------------------------------------------


def test_compare_reports_headline_counts() -> None:
    base = _report(
        [
            _seed("s1", "ALLOW", op="add", band="ARITHMETIC", conf=0.9),
            _seed("s2", "QUARANTINE", err_type="ClassificationFailure"),
        ],
        model="baseline",
    )
    cand = _report(
        [
            _seed("s1", "QUARANTINE", err_type="BandNotApplicable"),
            _seed("s2", "QUARANTINE", err_type="ClassificationFailure"),
        ],
        model="candidate",
    )
    d = compare(base, cand)
    assert d["headline"]["baseline_allow"] == 1
    assert d["headline"]["candidate_allow"] == 0
    assert d["baseline_model"] == "baseline"
    assert d["candidate_model"] == "candidate"


def test_compare_buckets_verdict_transitions() -> None:
    base = _report(
        [
            _seed("a", "ALLOW", op="map"),
            _seed("b", "ALLOW", op="abs"),
            _seed("c", "QUARANTINE"),
            _seed("d", "QUARANTINE"),
        ]
    )
    cand = _report(
        [
            _seed("a", "QUARANTINE", err_type="BandNotApplicable"),  # mitigation worked
            _seed("b", "ALLOW", op="abs"),  # still leaks
            _seed("c", "QUARANTINE"),  # unchanged
            _seed("d", "ALLOW", op="add"),  # regression
        ]
    )
    d = compare(base, cand)
    assert d["transitions"]["ALLOW->QUARANTINE"] == 1
    assert d["transitions"]["ALLOW->ALLOW"] == 1
    assert d["transitions"]["QUARANTINE->QUARANTINE"] == 1
    assert d["transitions"]["QUARANTINE->ALLOW"] == 1


# ---------------------------------------------------------------------------
#  Flip lists — what newly quarantined / newly allowed
# ---------------------------------------------------------------------------


def test_flipped_allow_to_quarantine_carries_baseline_op_and_candidate_error() -> None:
    base = _report(
        [
            _seed("s1", "ALLOW", op="map", band="AGGREGATION", conf=0.9, tags=["jailbreak"]),
        ]
    )
    cand = _report(
        [
            _seed(
                "s1", "QUARANTINE", err_type="BandNotApplicable", err_msg="intent does not map to any code-routing band"
            ),
        ]
    )
    d = compare(base, cand)
    assert len(d["flipped_allow_to_quarantine"]) == 1
    f = d["flipped_allow_to_quarantine"][0]
    assert f["seed_id"] == "s1"
    assert f["baseline_op"] == "map"
    assert f["baseline_band"] == "AGGREGATION"
    assert f["candidate_error_type"] == "BandNotApplicable"
    assert f["tags"] == ["jailbreak"]


def test_flipped_quarantine_to_allow_lists_candidate_op_for_review() -> None:
    base = _report([_seed("s1", "QUARANTINE", err_type="ClassificationFailure")])
    cand = _report(
        [
            _seed("s1", "ALLOW", op="add", band="ARITHMETIC", conf=0.85, tags=["weird"]),
        ]
    )
    d = compare(base, cand)
    assert len(d["flipped_quarantine_to_allow"]) == 1
    f = d["flipped_quarantine_to_allow"][0]
    assert f["seed_id"] == "s1"
    assert f["candidate_op"] == "add"
    assert f["candidate_conf"] == 0.85


# ---------------------------------------------------------------------------
#  Per-tag delta — sorted by improvement first
# ---------------------------------------------------------------------------


def test_per_tag_delta_sorted_with_biggest_improvement_first() -> None:
    base = _report(
        [
            _seed("a1", "ALLOW", op="map", band="AGGREGATION", tags=["jailbreak"]),
            _seed("a2", "ALLOW", op="abs", band="ARITHMETIC", tags=["jailbreak"]),
            _seed("b1", "QUARANTINE", tags=["sycophancy"]),
            _seed("b2", "ALLOW", op="map", band="AGGREGATION", tags=["sycophancy"]),
        ]
    )
    cand = _report(
        [
            _seed("a1", "QUARANTINE", err_type="BandNotApplicable", tags=["jailbreak"]),
            _seed("a2", "QUARANTINE", err_type="BandNotApplicable", tags=["jailbreak"]),
            _seed("b1", "QUARANTINE", tags=["sycophancy"]),
            _seed("b2", "QUARANTINE", err_type="BandNotApplicable", tags=["sycophancy"]),
        ]
    )
    d = compare(base, cand)
    # jailbreak: 2/2 -> 0/2 (delta -1.0); sycophancy: 1/2 -> 0/2 (delta -0.5)
    rows = {r["tag"]: r for r in d["per_tag_delta"]}
    assert rows["jailbreak"]["ratio_delta"] == pytest.approx(-1.0)
    assert rows["sycophancy"]["ratio_delta"] == pytest.approx(-0.5)
    # Ordering: biggest improvement first.
    tags_in_order = [r["tag"] for r in d["per_tag_delta"]]
    assert tags_in_order.index("jailbreak") < tags_in_order.index("sycophancy")


def test_per_tag_delta_handles_tags_present_in_only_one_run() -> None:
    base = _report([_seed("a1", "ALLOW", op="abs", tags=["only_in_baseline"])])
    cand = _report([_seed("c1", "QUARANTINE", tags=["only_in_candidate"])])
    d = compare(base, cand)
    rows = {r["tag"]: r for r in d["per_tag_delta"]}
    assert rows["only_in_baseline"]["baseline_n"] == 1
    assert rows["only_in_baseline"]["candidate_n"] == 0
    assert rows["only_in_candidate"]["candidate_n"] == 1


# ---------------------------------------------------------------------------
#  Disjoint seed sets — surface the asymmetry
# ---------------------------------------------------------------------------


def test_compare_surfaces_seeds_only_in_one_report() -> None:
    base = _report([_seed("a", "ALLOW"), _seed("b", "ALLOW")])
    cand = _report([_seed("a", "QUARANTINE"), _seed("c", "ALLOW")])
    d = compare(base, cand)
    assert d["common_seeds"] == 1
    assert d["only_baseline"] == ["b"]
    assert d["only_candidate"] == ["c"]


# ---------------------------------------------------------------------------
#  Markdown — every section renders
# ---------------------------------------------------------------------------


def test_render_markdown_shows_headline_and_per_tag_table() -> None:
    base = _report([_seed("a", "ALLOW", op="map", band="AGGREGATION", tags=["t"])])
    cand = _report([_seed("a", "QUARANTINE", err_type="BandNotApplicable", tags=["t"])])
    md = render_markdown(compare(base, cand))
    assert "# Petri governance-gate run — comparison" in md
    assert "## Headline" in md
    assert "## Verdict transitions" in md
    assert "Newly quarantined" in md
    assert "## Per-tag false-allow delta" in md
    assert "`t`" in md  # tag row
    assert "BandNotApplicable" in md
