"""repair_synth: deterministically synthesized DEEP repair trajectories (FAIL -> repair -> PASS).

These prove the synthesizer emits the deep "becoming" shape the harvested corpus is thin on, in the
harvester's exact tool-dialogue format, and ONLY when it is real: the buggy draft must actually fail and
the fix must actually pass, re-checked by an independent audit that never trusts the synthesizer's claim.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.repair_synth import audit, build, from_mbpp, from_pitfalls, repair_trajectory  # noqa: E402

_BUGGY = "def upto(n):\n    return list(range(1, n))"
_FIX = "def upto(n):\n    return list(range(1, n + 1))"
_PUBLIC = ["assert upto(3) == [1, 2, 3]"]
_HELD = ["assert upto(1) == [1]"]


def test_repair_trajectory_has_the_deep_fail_then_pass_shape():
    tr = repair_trajectory("t", "Return 1..n inclusive.", _BUGGY, _FIX, _PUBLIC, _HELD)
    assert tr is not None
    roles = [m["role"] for m in tr["messages"]]
    assert roles == ["system", "user", "assistant", "user", "assistant", "user", "assistant"]
    assert tr["messages"][3]["content"].startswith("TOOL run_code: FAIL")  # the failure turn is real
    assert tr["messages"][5]["content"] == "TOOL run_code: PASS (example test)"
    calls = sum(m["content"].count("CALL run_code") for m in tr["messages"] if m["role"] == "assistant")
    assert calls == 2  # two ACTUAL tool calls (the model's turns): the failed draft, then the repair
    assert "n + 1" in tr["messages"][-1]["content"]  # the ANSWER is the fix
    assert tr["meta"]["grade"] == "repair" and tr["meta"]["tool_calls"] == 2


def test_rejects_a_pair_that_is_not_a_real_repair():
    # if the "buggy" code actually passes the shown test, it is not a repair -> None (nothing unverified)
    assert repair_trajectory("t", "p", _FIX, _FIX, _PUBLIC, _HELD) is None


def test_from_pitfalls_are_all_audit_clean():
    pit = from_pitfalls()
    assert len(pit) >= 6
    a = audit(pit)
    assert a["mismatches"] == 0 and a["verified"] == a["audited"]  # every pitfall repair re-verifies


@pytest.mark.slow
def test_from_mbpp_mines_audit_clean_repairs():
    mb = from_mbpp(limit=40)
    assert len(mb) >= 1  # operator-swap mining finds at least one real repair in 40 problems
    assert audit(mb)["mismatches"] == 0  # all independently re-verified


def test_audit_catches_a_tampered_fix():
    tr = repair_trajectory("t", "p", _BUGGY, _FIX, _PUBLIC, _HELD)
    tr["messages"][-1]["content"] = "ANSWER:\n```python\ndef upto(n):\n    return []\n```"  # wrong fix
    assert audit([tr])["mismatches"] == 1  # the independent re-run catches it


@pytest.mark.slow
def test_build_writes_only_audit_clean_repairs(tmp_path):
    out = build(str(tmp_path / "repairs.jsonl"), mbpp_limit=40)
    assert out["total"] >= 6 and out["audit"]["mismatches"] == 0
    assert out["all_repair_shape"] is True
    lines = (tmp_path / "repairs.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == out["total"]
