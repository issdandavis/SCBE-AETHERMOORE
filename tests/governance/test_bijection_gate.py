from __future__ import annotations

import json
import subprocess
import sys

import pytest

from src.governance.bijection_gate import (
    BIJECTIVE_SOLVER,
    COUNT_PERFECT_IDENTITY_SWAPPED,
    INCOMPLETE_OR_HALLUCINATING,
    NON_INJECTIVE,
    PARTIAL_ALIGNMENT,
    audit_bijection,
    evaluate_bijection,
    require_bijective,
)


def _truth(n: int = 8) -> dict[str, str]:
    return {f"A{i}": f"S{i}" for i in range(n)}


def test_perfect_bijection_is_usable_router() -> None:
    truth = _truth()
    audit = evaluate_bijection(truth, dict(truth), seed=7)
    assert audit.verdict == BIJECTIVE_SOLVER
    assert audit.is_bijective is True
    assert audit.usable_as_router is True
    assert (
        audit.misses,
        audit.ghosts,
        audit.duplicate_targets,
        audit.wrong_matches,
    ) == ((), (), (), ())
    assert audit.identity_accuracy == pytest.approx(1.0)


def test_count_perfect_but_identity_swapped_fails_with_wrong_matches() -> None:
    truth = _truth()
    rotated = {f"A{i}": f"S{(i + 1) % 8}" for i in range(8)}
    audit = evaluate_bijection(truth, rotated, seed=7)

    assert audit.verdict == COUNT_PERFECT_IDENTITY_SWAPPED
    assert audit.usable_as_router is False
    assert audit.misses == ()
    assert audit.ghosts == ()
    assert audit.target_misses == ()
    assert audit.target_ghosts == ()
    assert len(audit.wrong_matches) == 8
    assert audit.identity_accuracy == pytest.approx(0.0)
    assert audit.beats_identity_null is False


def test_partial_alignment_beats_null_but_is_not_router() -> None:
    truth = _truth()
    pred = dict(truth)
    pred["A0"], pred["A1"] = "S1", "S0"
    audit = evaluate_bijection(truth, pred, seed=7)

    assert audit.verdict == PARTIAL_ALIGNMENT
    assert audit.identity_errors == 2
    assert audit.identity_accuracy == pytest.approx(0.75)
    assert audit.beats_identity_null is True
    assert audit.usable_as_router is False


def test_misses_and_target_misses_are_reported() -> None:
    truth = _truth()
    pred = dict(truth)
    pred["A0"] = None
    pred["A1"] = None
    audit = audit_bijection(truth, pred)

    assert audit.verdict == INCOMPLETE_OR_HALLUCINATING
    assert audit.misses == ("A0", "A1")
    assert audit.target_misses == ("S0", "S1")
    assert audit.usable_as_router is False


def test_ghost_source_and_ghost_target_are_reported() -> None:
    truth = _truth()
    pred = dict(truth)
    pred["A2"] = "S_ghost"
    pred["A_not_real"] = "S0"
    audit = audit_bijection(truth, pred)

    assert audit.verdict == INCOMPLETE_OR_HALLUCINATING
    assert audit.ghosts == ("A_not_real",)
    assert audit.target_ghosts == ("S_ghost",)
    assert audit.usable_as_router is False


def test_duplicate_target_flags_non_injectivity() -> None:
    truth = _truth()
    pred = dict(truth)
    pred["A3"] = "S4"
    audit = audit_bijection(truth, pred)

    assert audit.verdict == NON_INJECTIVE
    assert audit.duplicate_targets[0].target_id == "S4"
    assert audit.duplicate_targets[0].source_ids == ("A3", "A4")
    assert audit.usable_as_router is False


def test_truth_must_be_a_bijection() -> None:
    bad_truth = {"A0": "S0", "A1": "S0"}
    with pytest.raises(ValueError, match="bijection"):
        audit_bijection(bad_truth, dict(bad_truth))


def test_empty_truth_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        audit_bijection({}, {})


def test_require_bijective_returns_audit_or_raises() -> None:
    truth = {"A0": "S0"}
    assert require_bijective(truth, {"A0": "S0"}).verdict == BIJECTIVE_SOLVER

    with pytest.raises(ValueError, match="not bijective"):
        require_bijective(truth, {"A0": "S1"})


def test_cli_exits_zero_only_for_usable_router(tmp_path) -> None:
    truth_path = tmp_path / "truth.json"
    good_path = tmp_path / "good.json"
    swapped_path = tmp_path / "swapped.json"
    truth_path.write_text(json.dumps({"A0": "S0", "A1": "S1"}), encoding="utf-8")
    good_path.write_text(json.dumps({"A0": "S0", "A1": "S1"}), encoding="utf-8")
    swapped_path.write_text(json.dumps({"A0": "S1", "A1": "S0"}), encoding="utf-8")

    good = subprocess.run(
        [
            sys.executable,
            "scripts/eval/bijection_gate.py",
            "--truth",
            str(truth_path),
            "--candidate",
            str(good_path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    swapped = subprocess.run(
        [
            sys.executable,
            "scripts/eval/bijection_gate.py",
            "--truth",
            str(truth_path),
            "--candidate",
            str(swapped_path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )

    assert good.returncode == 0, good.stderr
    assert json.loads(good.stdout)["verdict"] == BIJECTIVE_SOLVER
    assert swapped.returncode == 1
    assert json.loads(swapped.stdout)["verdict"] == COUNT_PERFECT_IDENTITY_SWAPPED
