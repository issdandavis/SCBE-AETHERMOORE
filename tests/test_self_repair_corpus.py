"""Tests for self_repair_corpus -- execution-verified synthesis of self-repair trajectories."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import retry_corpus_validate as rcv  # noqa: E402
from python.helm import self_repair_corpus as src  # noqa: E402

GOOD = "def add(a, b):\n    return a + b"
ASSERT = "assert add(2, 3) == 5"


def test_runs_ok_distinguishes_pass_from_fail():
    ok, _ = src.runs_ok(GOOD, ASSERT)
    assert ok is True
    bad, _ = src.runs_ok("def add(a, b):\n    return a - b", ASSERT)
    assert bad is False


def test_make_failing_variant_actually_fails_and_good_passes():
    variant = src.make_failing_variant(GOOD, ASSERT)
    assert variant is not None
    bad, name, msg = variant
    assert src.runs_ok(bad, ASSERT)[0] is False  # the variant genuinely fails
    assert src.runs_ok(GOOD, ASSERT)[0] is True  # the good code genuinely passes
    assert name and msg  # carries a mutator name + a real failure message


def test_synthesized_record_validates_as_self_repair_success():
    rec = src.make_self_repair_record(
        "Add two numbers.\n%s" % ASSERT, GOOD, "def add(a,b): return a-b", "flip +/-", "AssertionError", task_id=1
    )
    assert rcv.analyze_record(rec)["category"] == rcv.SELF_REPAIR_SUCCESS


def test_teacher_bailout_record_waits_until_second_failure():
    rec = src.make_teacher_bailout_record(
        "Add two numbers.\n%s" % ASSERT,
        GOOD,
        "def add(a,b): return a-b",
        "flip +/-",
        "AssertionError",
        "def add(a,b): return None",
        "return -> return None",
        "AssertionError",
        task_id=2,
    )
    analysis = rcv.analyze_record(rec)
    assert analysis["category"] == rcv.TEACHER_BAILOUT
    assert sum(1 for m in rec["messages"] if m["role"] == "assistant") == 2
    assert rec["messages"][-1]["role"] == "teacher"


def test_extract_example_and_pool_from_vtc_shape():
    vtc = [
        {
            "messages": [
                {"role": "system", "content": "x"},
                {
                    "role": "user",
                    "content": "Add two numbers.\n\nIt must make this example pass:\n%s\nReturn ONLY the code."
                    % ASSERT,
                },
                {"role": "assistant", "content": GOOD},
            ],
            "meta": {"task_id": 7, "verified": True},
        }
    ]
    pool = src.verified_pool_from_vtc(vtc)
    assert len(pool) == 1 and pool[0][2] == ASSERT and pool[0][3] == 7


def test_synthesize_only_emits_verified_trajectories():
    pool = [("Add.\n%s" % ASSERT, GOOD, ASSERT, 1)]
    recs = src.synthesize(pool)
    assert len(recs) == 1
    # every emitted record is a real self-repair success (bad fails, good passes, validated)
    assert all(rcv.analyze_record(r)["category"] == rcv.SELF_REPAIR_SUCCESS for r in recs)


def test_synthesize_teacher_bailouts_emits_verified_two_failure_shape():
    pool = [("Add.\n%s" % ASSERT, GOOD, ASSERT, 1)]
    recs = src.synthesize_teacher_bailouts(pool)
    assert len(recs) == 1
    assert all(rcv.analyze_record(r)["category"] == rcv.TEACHER_BAILOUT for r in recs)


def test_synthesize_retry_mix_contains_success_and_bailout():
    pool = [("Add.\n%s" % ASSERT, GOOD, ASSERT, i) for i in range(3)]
    mix = src.synthesize_retry_mix(pool, self_limit=2, teacher_limit=2)
    assert mix["self_records"] == 2
    assert mix["teacher_bailouts"] == 2
    assert mix["validation"]["counts"][rcv.SELF_REPAIR_SUCCESS] == 2
    assert mix["validation"]["counts"][rcv.TEACHER_BAILOUT] == 2


def test_augment_raises_self_ratio_above_the_warning_threshold():
    # a corpus that is 100% teacher-bailout (trips the dependence warning)
    def bailout():
        return {
            "messages": [
                {"role": "system", "content": "x"},
                {"role": "user", "content": "p"},
                {"role": "assistant", "content": "bad"},
                {"role": "user", "content": "AssertionError: failed"},
                {"role": "assistant", "content": "retry"},
                {"role": "user", "content": "AssertionError: failed"},
                {"role": "assistant", "content": "Here is the correct solution"},
            ],
            "meta": {"final_source": "teacher"},
        }

    corpus = [bailout() for _ in range(6)]
    assert rcv.validate(corpus)["teacher_dependence_warning"] is True
    pool = [("Add.\n%s" % ASSERT, GOOD, ASSERT, i) for i in range(10)]
    new, report = src.augment(corpus, pool, target_self_ratio=0.4)
    assert report["after_self_ratio"] >= 0.4 and report["reached_target"] is True
    assert rcv.validate(new)["teacher_dependence_warning"] is False  # rebalanced


def test_deterministic():
    pool = [("Add.\n%s" % ASSERT, GOOD, ASSERT, 1)]
    assert src.synthesize(pool) == src.synthesize(pool)
