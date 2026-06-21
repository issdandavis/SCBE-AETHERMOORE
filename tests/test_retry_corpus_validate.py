"""Tests for retry_corpus_validate -- the v3 retry-teacher corpus validator + teacher-dependence metric."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import retry_corpus_validate as rcv  # noqa: E402


def _teacher_bailout():
    # bad attempt -> tool fail -> critique+retry -> tool fail -> teacher correction
    return {
        "messages": [
            {"role": "system", "content": "solve it"},
            {"role": "user", "content": "Write a function ..."},
            {"role": "assistant", "content": "def f(): return 0  # bad attempt"},
            {"role": "user", "content": "AssertionError: f() != 1, test failed"},
            {"role": "assistant", "content": "critique: off by one; retry"},
            {"role": "user", "content": "AssertionError: still failed"},
            {"role": "assistant", "content": "Here is the correct solution: def f(): return 1"},
        ],
        "meta": {"repaired": True, "final_source": "teacher"},
    }


def _self_repair_success():
    # bad attempt -> tool fail -> critique+retry -> PASS (no teacher)
    return {
        "messages": [
            {"role": "system", "content": "solve it"},
            {"role": "user", "content": "Write a function ..."},
            {"role": "assistant", "content": "def f(): return 0  # bad attempt"},
            {"role": "user", "content": "AssertionError: failed"},
            {"role": "assistant", "content": "fixed: def f(): return 1"},
            {"role": "user", "content": "All tests passed"},
        ],
        "meta": {"repaired": True, "final_source": "self"},
    }


def _malformed():
    return {
        "messages": [{"role": "user", "content": "problem"}, {"role": "assistant", "content": "answer"}],
        "meta": {},
    }


def test_classifies_teacher_bailout():
    a = rcv.analyze_record(_teacher_bailout())
    assert a["category"] == rcv.TEACHER_BAILOUT and a["assistant_attempts"] == 3 and a["fail_signals"] == 2


def test_classifies_self_repair_success():
    a = rcv.analyze_record(_self_repair_success())
    assert a["category"] == rcv.SELF_REPAIR_SUCCESS and a["self_repair_pass"] is True and a["teacher"] is False


def test_malformed_is_flagged_with_reasons():
    a = rcv.analyze_record(_malformed())
    assert a["category"] == rcv.MALFORMED and a["reasons"]


def test_meta_drives_teacher_detection_without_content_marker():
    rec = _self_repair_success()
    rec["meta"] = {"final_source": "teacher"}  # meta says teacher even though content reads like self-repair
    assert rcv.analyze_record(rec)["teacher"] is True


def test_all_teacher_corpus_raises_the_dependence_warning():
    # the user's v3 (every record ends in a teacher correction) -> 100% bailout, 0% self-repair
    v = rcv.validate([_teacher_bailout() for _ in range(10)])
    assert v["teacher_bailout_ratio"] == 1.0
    assert v["self_repair_success_ratio"] == 0.0
    assert v["teacher_dependence_warning"] is True


def test_mixed_corpus_does_not_warn_and_counts_self_repair():
    v = rcv.validate([_teacher_bailout() for _ in range(3)] + [_self_repair_success() for _ in range(7)])
    assert v["counts"][rcv.SELF_REPAIR_SUCCESS] == 7 and v["counts"][rcv.TEACHER_BAILOUT] == 3
    assert v["teacher_dependence_warning"] is False


def test_sharegpt_format_is_understood():
    # ShareGPT shape (conversations + from/value) must classify, not fall to MALFORMED
    rec = {
        "conversations": [
            {"from": "human", "value": "Write a function ..."},
            {"from": "gpt", "value": "def f(): return 0"},
            {"from": "human", "value": "AssertionError: failed"},
            {"from": "gpt", "value": "retry: def f(): return 1"},
            {"from": "human", "value": "All tests passed"},
        ]
    }
    a = rcv.analyze_record(rec)
    assert a["category"] == rcv.SELF_REPAIR_SUCCESS and a["assistant_attempts"] == 2


def test_diagnose_reports_unknown_message_schema():
    weird = [{"turns": [{"speaker": "x", "text": "hi"}], "meta": {}}]  # unrecognized -> MALFORMED + diagnosed
    v = rcv.validate(weird)
    assert v["counts"][rcv.MALFORMED] == 1
    diag = rcv.diagnose(weird)
    assert diag and "turns" in diag[0]["record_keys"]


def test_load_jsonl_roundtrip(tmp_path):
    import json

    p = tmp_path / "corpus.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in (_teacher_bailout(), _self_repair_success())), encoding="utf-8")
    v = rcv.validate(rcv.load_jsonl(str(p)))
    assert v["total"] == 2 and v["well_formed"] == 2
