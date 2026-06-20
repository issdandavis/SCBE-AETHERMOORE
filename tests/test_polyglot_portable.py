"""The verified-portable EMITTER extension: the ops added beyond the original 22-op universal core,
each proven identical across python/js/rust by the conformance harness.

Two kinds of check:
  * python-face semantics -- toolchain-free, deterministic, runs in any CI (exec the emitted python).
  * cross-language agreement -- runs ONLY the backends this box has (node/rustc/...); asserts that no
    backend that ran DISAGREED. That is robust to CI toolchain availability: absence is not agreement,
    but presence-without-disagreement is the honest portability signal.

Also pins: the universal/portable split, the int32 bitwise domain boundary is CAUGHT (not hidden), and
that a bundled language face which hasn't implemented an extension op raises a clean error (no KeyError).
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe import polyglot as P  # noqa: E402
from python.scbe.polyglot_conformance import conformance, run_python  # noqa: E402

# (op, (a,b,c) args, expected python-face result). FUNC1 acts on c; FUNC2 acts on (b,c).
_PY_FACE = [
    ("sign", (0, 0, -3), -1.0),
    ("sign", (0, 0, 7), 1.0),
    ("cmp", (0, 5, 3), 1.0),
    ("cmp", (0, 3, 5), -1.0),
    ("log", (0, 0, 1), 0.0),
    ("exp", (0, 0, 0), 1.0),
    ("isnan", (0, 0, float("nan")), 1.0),
    ("isinf", (0, 0, float("inf")), 1.0),
    ("isfinite", (0, 0, 5), 1.0),
    ("and", (0, 12, 10), 8.0),
    ("or", (0, 12, 10), 14.0),
    ("xor", (0, 12, 10), 6.0),
    ("not", (0, 0, 5), -6.0),
    ("shl", (0, 1, 4), 16.0),
    ("shr", (0, 255, 1), 127.0),
]

# representative cross-language cases per extension op (within the verified domain)
_AGREE_CASES = {
    "sign": [(0, 0, 5), (0, 0, -3), (0, 0, 0)],
    "cmp": [(0, 5, 3), (0, 3, 5), (0, 4, 4)],
    "log": [(0, 0, 1), (0, 0, 2.5), (0, 0, 10)],
    "exp": [(0, 0, 0), (0, 0, 1), (0, 0, -1)],
    "isnan": [(0, 0, 5), (0, 0, float("nan"))],
    "isinf": [(0, 0, 5), (0, 0, float("inf")), (0, 0, float("-inf"))],
    "isfinite": [(0, 0, 5), (0, 0, float("inf")), (0, 0, float("nan"))],
    "and": [(0, 12, 10), (0, 255, 15)],
    "or": [(0, 12, 10), (0, 8, 4)],
    "xor": [(0, 12, 10), (0, 5, 5)],
    "not": [(0, 0, 5), (0, 0, 255)],
    "shl": [(0, 1, 4), (0, 7, 3)],
    "shr": [(0, 255, 1), (0, 1024, 5)],
}


def test_universal_core_is_a_subset_of_the_portable_core():
    assert P.SCALAR_OPS < P.PORTABLE_OPS  # strict subset
    assert len(P.SCALAR_OPS) == 22
    new = P.PORTABLE_OPS - P.SCALAR_OPS
    assert new == {"sign", "cmp", "log", "exp", "isnan", "isinf", "isfinite", "and", "or", "xor", "not", "shl", "shr"}


@pytest.mark.parametrize("op,args,expected", _PY_FACE)
def test_python_face_semantics(op, args, expected):
    # toolchain-free: emit the python face and run it; the op must compute the documented value
    got = run_python(P.program_bytes(op), args)
    assert got == expected


@pytest.mark.parametrize("op", sorted(_AGREE_CASES))
def test_no_backend_that_ran_disagrees(op):
    # honest portability: among the backends this box can run, none may DISAGREE with the python ref
    rep = conformance(P.program_bytes(op), _AGREE_CASES[op])
    assert rep["summary"]["disagree"] == [], "op %r diverged on %s" % (op, rep["summary"]["disagree"])
    assert rep["reference"][0] is not None  # python reference actually produced a value


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node to show the int32 divergence")
def test_bitwise_domain_boundary_is_caught_not_hidden():
    # the honest limit: past 2^31, JS int32 wraps and the harness MUST report the divergence
    rep = conformance(P.program_bytes("shl"), [(0, 1, 31)])  # 1 << 31 = 2^31
    assert "javascript" in rep["summary"]["disagree"]


def test_close_handles_infinities_correctly():
    # the comparator must require the SAME signed infinity: equal infinities AGREE, opposite ones DISAGREE.
    # (the naive tolerance form mis-handled both: abs(inf-inf)=nan -> false DISAGREE; inf<=inf -> false AGREE)
    from python.scbe.polyglot_conformance import _close

    inf = float("inf")
    assert _close(inf, inf) is True
    assert _close(-inf, -inf) is True
    assert _close(inf, -inf) is False  # a maximally-wrong opposite-sign backend must NOT be excused
    assert _close(inf, 1.0) is False
    assert _close(float("nan"), float("nan")) is True  # nan handling still intact


@pytest.mark.skipif(shutil.which("node") is None, reason="needs a second backend to compare against")
def test_infinite_results_are_verified_not_falsely_flagged():
    # neg of +inf is -inf on every face; with the _close fix the harness must AGREE, not falsely DISAGREE
    rep = conformance(P.program_bytes("neg"), [(0, 0, float("inf"))])
    assert rep["summary"]["disagree"] == []
    assert rep["reference"][0] == float("-inf")


def test_log_safe_mode_roundabout_matches_sqrt():
    # in safe mode, log of a non-positive routes to 0.0 (the same chosen handler as sqrt), no exception
    src = P.emit(P.program_bytes("log"), "python", safe=True)
    ns = {}
    exec(compile(src, "<t>", "exec"), ns)  # noqa: S102 - our own emitter output
    assert ns["tongue_fn"](0.0, 0.0, -5.0) == 0.0  # log(-5) -> roundabout 0.0, did not raise


def test_a_face_without_an_extension_op_raises_cleanly():
    # the per-dialect guard: a bundled track that hasn't implemented 'xor' yields a clear error, not KeyError
    unsupported = [lang for lang in P.languages() if not P._dialect_supports(P.REGISTRY[lang], "xor")]
    assert unsupported, "expected at least one bundled face without the extension ops"
    with pytest.raises(ValueError, match="not implemented in"):
        P.emit(P.program_bytes("xor"), unsupported[0])
