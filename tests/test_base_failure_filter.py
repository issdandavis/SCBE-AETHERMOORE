"""Tests for base_failure_filter -- keep only problems the base fails (ref passes), execution-verified."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import base_failure_filter as bff  # noqa: E402

# real schema: "code" is the reference solution (public_bench.reference_generator + func_name read it)
PROBS = [
    # base fails (returns a-b), ref passes -> KEPT (genuine headroom)
    {
        "task_id": "add",
        "code": "def add(a, b):\n    return a + b",
        "test_list": ["assert add(2,3)==5", "assert add(0,0)==0"],
    },
    # base solves it -> DROPPED (no headroom)
    {
        "task_id": "mul",
        "code": "def mul(a, b):\n    return a * b",
        "test_list": ["assert mul(2,3)==6", "assert mul(1,1)==1"],
    },
    # the reference itself fails (broken spec) -> DROPPED (not a usable problem)
    {
        "task_id": "broken",
        "code": "def broken(x):\n    return 0",
        "test_list": ["assert broken(1)==1", "assert broken(2)==2"],
    },
    # only one test -> no hidden test -> SKIPPED
    {"task_id": "nohidden", "code": "def solo(x):\n    return x", "test_list": ["assert solo(1)==1"]},
]

BASE = {
    "add": "def add(a, b):\n    return a - b",  # wrong -> base fails -> kept
    "mul": "def mul(a, b):\n    return a * b",  # right -> base solves -> dropped
    "broken": "def broken(x):\n    return x",  # would pass, but ref already failed -> dropped anyway
}


def _base_gen(p):
    return BASE[p["task_id"]]


def test_keeps_only_base_failing_reference_passing_problems():
    rep = bff.select_base_failures(PROBS, _base_gen, attempts=1, public_k=1)
    assert rep["kept_count"] == 1
    assert [p["task_id"] for p in rep["kept"]] == ["add"]  # base fails it, ref passes it
    assert rep["base_solved"] == 1  # mul
    assert rep["ref_failed"] == 1  # broken
    assert rep["skipped_no_hidden"] == 1  # nohidden
    assert rep["attempted"] == 4


def test_a_problem_the_base_solves_is_not_kept_even_over_multiple_attempts():
    def always_solves(p):
        return "def add(a, b):\n    return a + b"

    rep = bff.select_base_failures([PROBS[0]], always_solves, attempts=3, public_k=1)
    assert rep["kept_count"] == 0 and rep["base_solved"] == 1


def test_kept_problems_carry_their_tests():
    rep = bff.select_base_failures(PROBS, _base_gen, attempts=2, public_k=1)
    for p in rep["kept"]:
        assert "test_list" in p and len(p["test_list"]) > 1  # still a real, runnable problem
