"""loomfn: arrays (data structures) and user-defined functions (call/return, recursion) emit +
run identically across language faces.

The Python interpreter of the IR is the reference; emitted faces are RUN and compared. Reference,
parsing, array semantics, and recursion are checked unconditionally; js/rust agreement runs only
when the toolchain is present (skipped otherwise, never faked).
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.loomfn import EXAMPLES, emit, interpret, parse, verify  # noqa: E402

_HAVE_NODE = shutil.which("node") is not None
_HAVE_RUST = shutil.which("rustc") is not None

_EXPECT = {
    "array_sum": 15.0,
    "array_max": 9.0,
    "add_fn": 7.0,
    "factorial_recursive": 120.0,
    "fib_recursive": 55.0,
    "sum_array_fn": 60.0,
}


def _ref(name):
    return interpret(parse(EXAMPLES[name]))[-1]


# --- data structures (arrays) --------------------------------------------------


def test_reference_arrays_build_index_and_aggregate():
    assert _ref("array_sum") == 15.0  # push 1..5, then sum the array
    assert _ref("array_max") == 9.0  # index every element, keep the max


def test_array_ops_round_trip():
    # set overwrites by index; get reads it back; alen tracks length
    prog = parse(
        "arr a / const v 5 / push a v / const v 9 / push a v / const i 0 / const w 42 / set a i w / "
        "get r a i / alen n a / print r / halt"
    )
    assert interpret(prog)[-1] == 42.0
    prog2 = parse("arr a / const v 5 / push a v / const v 9 / push a v / alen n a / print n / halt")
    assert interpret(prog2)[-1] == 2.0


# --- user-defined functions (call / return / recursion) ------------------------


def test_reference_functions_and_recursion():
    assert _ref("add_fn") == 7.0  # 2-arg function
    assert _ref("factorial_recursive") == 120.0  # 5! via recursion
    assert _ref("fib_recursive") == 55.0  # fib(10), two recursive calls per frame


def test_recursion_uses_independent_frames():
    # if frames were not saved/restored, n would be clobbered by the recursive call and 5! would be wrong
    assert _ref("factorial_recursive") == 120.0
    assert _ref("sum_array_fn") == 60.0  # a function reading a shared (heap) array


def test_unknown_op_and_unknown_function_raise():
    with pytest.raises(ValueError, match="unknown op"):
        parse("frobnicate a b")
    with pytest.raises(ValueError, match="unknown function"):
        interpret(parse("call r nope / halt"))


# --- strings (a string is an array of char codes) ------------------------------


def test_strlit_loads_a_string_as_char_codes():
    # strlit builds the code-point array; get reads one code back
    assert interpret(parse("strlit s abc / const i 0 / get c s i / print c / halt"))[-1] == 97.0  # 'a'
    assert interpret(parse("strlit s abc / alen n s / print n / halt"))[-1] == 3.0  # length
    assert interpret(parse("strlit s / alen n s / print n / halt"))[-1] == 0.0  # empty string


def test_chr_gives_a_char_code():
    assert interpret(parse("chr d a / print d / halt"))[-1] == 97.0
    assert interpret(parse("chr d z / print d / halt"))[-1] == 122.0


def test_reference_string_programs():
    assert _ref("str_len") == 5.0  # len('hello')
    assert _ref("vowel_count") == 3.0  # 'programming' -> o, a, i


@pytest.mark.skipif(not (_HAVE_NODE and _HAVE_RUST), reason="node+rustc needed")
def test_string_program_agrees_across_faces():
    # the real point: a string program computes the same answer in python, js, and rust
    r = verify(parse(EXAMPLES["vowel_count"]))
    assert r["reference"] == 3.0
    assert r["verified_count"] == 3 and not r["disagree"]


# --- emit + cross-face agreement ----------------------------------------------


def test_emit_produces_a_dispatch_loop_for_each_face():
    prog = parse(EXAMPLES["factorial_recursive"])
    assert "while 0 <= pc" in emit(prog, "python")
    assert "while (pc >= 0" in emit(prog, "javascript")
    assert "while pc >= 0" in emit(prog, "rust")


def test_python_face_matches_reference_unconditionally():
    for name in ("array_sum", "factorial_recursive", "sum_array_fn"):
        r = verify(parse(EXAMPLES[name]), faces=("python",))
        assert r["reference"] == _EXPECT[name]
        assert r["results"]["python"] == {"status": "AGREE", "value": _EXPECT[name]}


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_javascript_face_agrees_on_arrays_and_recursion():
    for name in ("array_max", "factorial_recursive", "fib_recursive", "sum_array_fn"):
        r = verify(parse(EXAMPLES[name]), faces=("javascript",))
        assert r["results"]["javascript"] == {"status": "AGREE", "value": _EXPECT[name]}


@pytest.mark.skipif(not _HAVE_RUST, reason="rustc not installed")
def test_rust_face_agrees_on_arrays_and_recursion():
    for name in ("array_max", "factorial_recursive", "fib_recursive", "sum_array_fn"):
        r = verify(parse(EXAMPLES[name]), faces=("rust",))
        assert r["results"]["rust"] == {"status": "AGREE", "value": _EXPECT[name]}
