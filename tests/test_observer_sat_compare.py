"""The measured custom-vs-CP-SAT core comparison -- runs only where ortools is installed (skips in CI).

Pins the decision-grade finding: pure-Python minimal_core and CP-SAT get_core extract the SAME minimal
contradicting pair, so the cores agree; the timing (the actual reason to adopt or not) is reported by the
research script research/sat_comparison/observer_sat_compare.py.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

if importlib.util.find_spec("ortools") is None:  # CI does not install ortools; that is intentional
    pytest.skip("ortools not installed (research-only dependency)", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "_observer_sat_compare", ROOT / "research" / "sat_comparison" / "observer_sat_compare.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)


def test_custom_and_cpsat_agree_on_a_minimal_pair():
    for n, k in [(50, 4), (200, 20)]:
        r = _mod.compare(n, k)
        assert r["custom_core_size"] == 2  # pure-Python core is a minimal contradicting pair
        assert r["cpsat_core_size"] == 2  # CP-SAT core is the same size
        assert r["both_minimal_pair"] and r["agree_is_a_valid_pair"]  # both are a valid ALLOW+DENY pair


def test_custom_is_not_slower_than_cpsat_on_this_task():
    # the load-bearing measurement: for consistency-core extraction the zero-dep path is competitive (in
    # practice far faster -- model build + solver startup dominate CP-SAT). We assert only the weak,
    # robust claim so the test is not flaky on slow CI: custom is no slower than CP-SAT here.
    r = _mod.compare(200, 20)
    assert r["custom_ms"] <= r["cpsat_ms"]
