"""better_corpus: the 'better data, not more' pitfall traces. These prove the traces are
execution-VOUCHED -- every buggy attempt actually fails its test and every fix actually passes -- so
nothing unverified can enter the corpus, and the union with the MBPP corpus is well-formed.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.better_corpus import PITFALLS, build, pitfall_trace, pitfall_traces, verify_pitfall  # noqa: E402


def test_every_pitfall_is_a_real_bug_and_fix():
    # the whole point: the buggy code FAILS the test and the fix PASSES it -- execution-verified
    for spec in PITFALLS:
        v = verify_pitfall(spec)
        assert v["buggy_fails"] is True, spec["name"]
        assert v["fix_passes"] is True, spec["name"]


def test_pitfall_trace_is_a_manager_shaped_repair():
    t = pitfall_trace(PITFALLS[0])
    roles = [m["role"] for m in t["messages"]]
    assert roles == ["system", "user", "assistant", "user", "assistant"]  # problem -> buggy -> diag -> fix
    assert t["meta"]["grade"] == "manager" and t["meta"]["repaired"] is True and t["meta"]["verified"] is True
    assert "got vs expected" in t["messages"][3]["content"]  # a real diagnosis, not a generic 'try again'


def test_unverified_pair_is_dropped():
    # a "pitfall" whose buggy code actually PASSES is not a real bug -> no trace (nothing unverified enters)
    fake = {
        "name": "not_a_bug",
        "prompt": "p",
        "buggy": "def f():\n    return 1",
        "fix": "def f():\n    return 1",
        "tests": ["assert f() == 1"],
    }
    assert pitfall_trace(fake) is None


def test_all_traces_present_and_verified():
    traces = pitfall_traces()
    assert len(traces) == len(PITFALLS)  # all 8 verified
    assert all(t["meta"]["source"] == "better_corpus_pitfall" for t in traces)


def test_build_unions_mbpp_and_pitfalls(tmp_path):
    mbpp = tmp_path / "mbpp.jsonl"
    mbpp.write_text(
        json.dumps({"messages": [{"role": "user", "content": "x"}], "meta": {"task_id": 1}}) + "\n", encoding="utf-8"
    )
    out = tmp_path / "better.jsonl"
    res = build(str(mbpp), str(out))
    assert res["from_mbpp"] == 1 and res["pitfalls"] == len(PITFALLS) and res["total"] == 1 + len(PITFALLS)
    lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == res["total"] and all("messages" in r for r in lines)
