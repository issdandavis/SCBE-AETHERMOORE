"""Tests for safety_face -- the independent sound-up-to-bound safety analyzer + C/CBMC face (wedge #2).

Pins the honest behaviour: the bounded checker detects each violation class AND clears safe programs; it is
EXHAUSTIVE so it catches a single-point bug that sampling misses (the credibility jump over wedge #1's
sampled gates); it refuses to silently pass a domain too large to enumerate; the C face emits a CBMC-ready
harness; and the cbmc gate is honest when cbmc is absent (never SAFE without running).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe import safety_face as sf  # noqa: E402


def _by_name(name):
    return dict(sf._demo_programs())[name]


def test_detects_each_violation_class_and_clears_safe_programs():
    expect = {
        "safe_read": ("SAFE", None),
        "oob_read": ("UNSAFE", sf.OOB),
        "div_bug": ("UNSAFE", sf.DIV0),
        "div_safe": ("SAFE", None),
        "overflow_bug": ("UNSAFE", sf.OVERFLOW),
        "overflow_safe": ("SAFE", None),
        "assert_fail": ("UNSAFE", sf.ASSERT),
    }
    for name, (want_status, want_kind) in expect.items():
        status, ev = sf.check_bounded(_by_name(name))
        assert status == want_status, (name, status)
        if want_status == "UNSAFE":
            assert ev.kind == want_kind, (name, ev.kind)


def test_counterexample_is_a_real_unsafe_input():
    # the reported counterexample must actually trigger the violation when re-run (not a phantom)
    status, ev = sf.check_bounded(_by_name("oob_read"))
    assert status == "UNSAFE"
    import pytest

    with pytest.raises(sf._Unsafe):
        sf._run_once(_by_name("oob_read"), ev.inputs)


def test_bounded_catches_single_point_bug_that_sampling_misses():
    # the credibility jump: exhaustive needs no luck where sampled checking does
    needle = sf._single_point_bug()
    assert sf.sample_check(needle, n=20, seed=0) is None  # sampling misses the lone unsafe input
    status, ev = sf.check_bounded(needle)
    assert status == "UNSAFE" and ev.inputs == {"x": 333}  # exhaustive finds it for certain


def test_bound_too_large_is_reported_not_silently_safe():
    huge = sf.Program(
        "huge", {"a": (0, 9_999), "b": (0, 9_999)}, {}, [sf.Set("r", sf.Bin("+", sf.Var("a"), sf.Var("b")))]
    )
    status, n = sf.check_bounded(huge)
    assert status == "BOUND_TOO_LARGE" and n > sf.MAX_BOUND  # never claims SAFE on an unchecked domain


def test_c_face_emits_a_cbmc_ready_harness():
    c = sf.to_c(_by_name("oob_read"))
    assert "int main(void)" in c
    assert "nondet_int" in c and "__CPROVER_assume" in c  # nondet inputs + range assumptions
    assert "int a[5] = {10, 20, 30, 40, 50};" in c  # the array under test
    assert "cbmc oob_read.c --bounds-check" in c  # the documented external command
    # an assertion program emits a C assert()
    assert "assert(" in sf.to_c(_by_name("assert_fail"))


def test_parse_cbmc_reads_the_verdict():
    assert sf.parse_cbmc("** 0 of 12 failed\nVERIFICATION SUCCESSFUL\n") == "SAFE"
    assert sf.parse_cbmc("[main.assertion.1] line 9 assertion: FAILURE\nVERIFICATION FAILED\n") == "UNSAFE"
    assert sf.parse_cbmc("usage: cbmc [options]") == "UNKNOWN"


def test_cbmc_gate_is_honest_when_absent():
    status, info = sf.check_cbmc(_by_name("safe_read"))
    if shutil.which("cbmc") is None:
        assert status == "UNAVAILABLE"  # never reports SAFE without actually running the analyzer
    else:
        assert status in ("SAFE", "UNSAFE", "UNKNOWN", "ERROR")


def test_verify_combines_into_an_honest_verdict():
    v = sf.verify(_by_name("oob_read"))
    assert v["builtin"] == "UNSAFE" and "UNSAFE" in v["verdict"]
    safe = sf.verify(_by_name("safe_read"))
    assert safe["builtin"] == "SAFE" and "SAFE-UP-TO-BOUND" in safe["verdict"]  # bounded, not unconditional


def test_bounded_check_is_deterministic():
    a = sf.check_bounded(_by_name("overflow_bug"))
    b = sf.check_bounded(_by_name("overflow_bug"))
    assert a[0] == b[0] and a[1].inputs == b[1].inputs


# ---- regressions for the soundness/honesty holes the skeptic panel found ---------------------------------
def test_division_overflow_int_min_over_minus_one_is_caught():
    # INT_MIN // -1 overflows (e.g. width 8: -128//-1 = 128 > 127) -- divmod results MUST be width-checked
    prog = sf.Program(
        "div_ovf",
        {"n": (-128, -128), "d": (-1, -1)},
        {},
        [sf.Set("r", sf.Bin("//", sf.Var("n"), sf.Var("d")))],
        width=8,
    )
    status, ev = sf.check_bounded(prog)
    assert status == "UNSAFE" and ev.kind == sf.OVERFLOW


def test_out_of_width_input_is_caught():
    # an input that cannot fit the declared width overflows the type -> not silently SAFE
    prog = sf.Program("wide_in", {"x": (200, 200)}, {}, [sf.Set("r", sf.Var("x"))], width=8)
    status, ev = sf.check_bounded(prog)
    assert status == "UNSAFE" and ev.kind == sf.OVERFLOW


def test_out_of_width_constant_is_caught():
    prog = sf.Program("wide_const", {"x": (0, 0)}, {}, [sf.Set("r", sf.Const(200))], width=8)
    status, ev = sf.check_bounded(prog)
    assert status == "UNSAFE" and ev.kind == sf.OVERFLOW


def test_undefined_variable_raises_a_defined_error_not_a_crash():
    import pytest

    bad = sf.Program("bad", {"x": (0, 2)}, {}, [sf.Set("r", sf.Var("nope"))])
    with pytest.raises(ValueError):
        sf.check_bounded(bad)


def test_empty_domain_is_not_silently_safe():
    empty = sf.Program("empty", {"x": (5, 1)}, {}, [sf.Assert(sf.Const(0))])  # lo>hi, always-fail assert
    status, n = sf.check_bounded(empty)
    assert status == "EMPTY_DOMAIN" and n == 0  # body never ran -> never reports SAFE


def test_c_face_is_width_aware_so_cbmc_checks_the_same_overflow():
    # at width<32 the emitted C carries an explicit declared-width assert so cbmc catches what the built-in does
    c = sf.to_c(_by_name("overflow_bug"))  # width=8
    assert "8-bit overflow" in c and "-128 <=" in c and "<= 127" in c
    # at width 32 no redundant per-assignment width assert is emitted (--signed-overflow-check does it)
    assert "-bit overflow" not in sf.to_c(_by_name("safe_read"))


def test_verify_reports_width_caveat_not_a_silent_contradiction():
    v = sf.verify(_by_name("overflow_bug"))  # width=8
    assert any("width<32" in c for c in v["caveats"])
