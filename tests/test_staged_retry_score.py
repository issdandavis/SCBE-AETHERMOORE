"""Tests for staged_retry_score -- the durable staged retry-loop scorer + baseline delta."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import staged_retry_score as srs  # noqa: E402


def test_classify_from_explicit_category_field():
    assert srs.classify({"task_id": 1, "category": "SOLVED_FIRST_TRY"}) == srs.SOLVED_FIRST_TRY
    assert srs.classify({"status": "solve_failed_fix_attempt_solved"}) == srs.FIX_SOLVED  # normalized
    assert srs.classify({"outcome": "PUBLIC_PASS_HIDDEN_FAIL_NO_RETRY"}) == srs.PUBLIC_PASS_HIDDEN_FAIL


def test_classify_from_raw_signals_flat_and_nested():
    assert srs.classify({"first_try_hidden_pass": True}) == srs.SOLVED_FIRST_TRY
    # passed public, failed hidden, never retried -> the circular-trust residual
    assert srs.classify({"first_try": {"hidden_pass": False, "public_pass": True}}) == srs.PUBLIC_PASS_HIDDEN_FAIL
    assert (
        srs.classify(
            {
                "first_try": {"hidden_pass": False, "public_pass": False},
                "retry": {"attempted": True, "hidden_pass": True},
            }
        )
        == srs.FIX_SOLVED
    )
    assert srs.classify({"first_try_hidden_pass": False, "retried": True, "retry_hidden_pass": False}) == srs.FIX_FAILED


def test_unclassified_when_schema_unrecognized():
    assert srs.classify({"task_id": 9}) == srs.UNCLASSIFIED  # no category, no signals -> not force-fit


def _cat(cat, i):
    return {"task_id": i, "category": cat}


def test_score_matches_the_reported_breakdown():
    recs = (
        [_cat(srs.SOLVED_FIRST_TRY, i) for i in range(14)]
        + [_cat(srs.FIX_SOLVED, 100)]
        + [_cat(srs.FIX_FAILED, 200 + i) for i in range(28)]
        + [_cat(srs.PUBLIC_PASS_HIDDEN_FAIL, 300 + i) for i in range(7)]
    )
    s = srs.score(recs)
    assert s["total"] == 50
    assert s["counts"][srs.SOLVED_FIRST_TRY] == 14 and s["counts"][srs.FIX_FAILED] == 28
    assert s["solve_rate"] == round(15 / 50, 3)  # 14 first-try + 1 fix-solved
    assert s["repair_conversion"] == round(1 / 29, 3)  # the retry loop converts 1 of 29 -- the honest gap
    assert s["overfit_no_retry_rate"] == round(7 / 50, 3)


def test_delta_reproduces_newly_repaired_and_regression():
    ids = [229, 245, 274, 291, 392]
    baseline = [_cat(srs.FIX_FAILED, i) for i in ids] + [_cat(srs.FIX_SOLVED, 407)]
    candidate = [_cat(srs.FIX_SOLVED, i) for i in ids] + [_cat(srs.FIX_FAILED, 407)]
    d = srs.delta(baseline, candidate)
    assert sorted(d["newly_repaired"]) == ids  # FIX_FAILED -> FIX_SOLVED
    assert d["regressed"] == [407]
    assert d["net_solved_delta"] == 4  # the reported +4
    assert d["count_delta"][srs.FIX_SOLVED] == 4 and d["count_delta"][srs.FIX_FAILED] == -4


def test_delta_warns_on_unmatched_ids():
    d = srs.delta([_cat(srs.FIX_FAILED, 1)], [_cat(srs.FIX_SOLVED, 2)])
    assert d["compared"] == 0 and d["only_in_baseline"] == [1] and d["only_in_candidate"] == [2]


def test_load_jsonl_roundtrip(tmp_path):
    p = tmp_path / "run.jsonl"
    rows = [
        '{"task_id": 1, "category": "SOLVED_FIRST_TRY"}',
        "",  # blank lines are skipped
        '{"task_id": 2, "category": "SOLVE_FAILED_FIX_ATTEMPT_FAILED"}',
    ]
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    recs = srs.load_jsonl(str(p))
    assert len(recs) == 2 and srs.score(recs)["total"] == 2
