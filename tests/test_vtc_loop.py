"""Tests for vtc_loop -- the one-command VTC training-data + eval loop (validate -> augment -> score)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import retry_corpus_validate as rcv  # noqa: E402
from python.helm import self_repair_corpus as src  # noqa: E402
from python.helm import staged_retry_score as srs  # noqa: E402
from python.helm import vtc_loop as vp  # noqa: E402

GOOD = "def add(a, b):\n    return a + b"
ASSERT = "assert add(2, 3) == 5"


def _bailout():
    return {
        "messages": [
            {"role": "system", "content": "x"},
            {"role": "user", "content": "p"},
            {"role": "assistant", "content": "bad"},
            {"role": "user", "content": "AssertionError: failed"},
            {"role": "assistant", "content": "retry"},
            {"role": "user", "content": "AssertionError: failed"},
            {"role": "assistant", "content": "Here is the right code"},
        ],
        "meta": {"final_source": "teacher"},
    }


def _pool_record():
    return {
        "messages": [
            {"role": "system", "content": "x"},
            {"role": "user", "content": "Add.\n\nIt must make this example pass:\n%s\nReturn ONLY the code." % ASSERT},
            {"role": "assistant", "content": GOOD},
        ],
        "meta": {"task_id": 1, "verified": True},
    }


def test_prep_rebalances_a_teacher_heavy_corpus():
    corpus = [_bailout() for _ in range(6)]
    pool = [_pool_record() for _ in range(10)]
    out, report = vp.prepare(corpus, pool, target=0.4)
    assert report["augmented"] is True
    assert report["after"]["self_repair_success_ratio"] >= report["validation"]["self_repair_success_ratio"]
    assert rcv.validate(out)["self_repair_success_ratio"] > 0  # genuinely added verified self-repair traces


def test_prep_leaves_a_balanced_corpus_alone():
    selfreps = src.synthesize([("Add.\n%s" % ASSERT, GOOD, ASSERT, i) for i in range(5)])
    out, report = vp.prepare(selfreps, [_pool_record()], target=0.4)
    assert report["augmented"] is False and out == list(selfreps)


def test_eval_scores_and_deltas():
    def rec(i, cat):
        return {"task_id": i, "category": cat}

    baseline = [rec(1, srs.FIX_FAILED), rec(2, srs.SOLVED_FIRST_TRY)]
    run = [rec(1, srs.FIX_SOLVED), rec(2, srs.SOLVED_FIRST_TRY)]
    res = vp.evaluate(run, baseline)
    assert res["score"]["total"] == 2
    assert res["delta"]["newly_repaired"] == [1]  # FIX_FAILED -> FIX_SOLVED


def test_eval_without_baseline_has_no_delta():
    res = vp.evaluate([{"task_id": 1, "category": srs.SOLVED_FIRST_TRY}])
    assert res["delta"] is None and res["score"]["total"] == 1
