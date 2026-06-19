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


# --- strings (text values as heap arrays of char codes) ------------------------

_STR_EXPECT = {
    "string_reverse": "olleh",
    "string_concat": "foobar",
    "fizzbuzz_15": "FizzBuzz",
    "char_match": 1.0,
}


def test_reference_strings_text_in_text_out():
    assert _ref("string_reverse") == "olleh"  # str literal -> index -> prints
    assert _ref("string_concat") == "foobar"  # concat appends one code array onto another
    assert _ref("fizzbuzz_15") == "FizzBuzz"  # mod + a text branch
    assert _ref("char_match") == 1.0  # char literal compared to a string's first code


def test_string_is_a_heap_array_of_char_codes():
    # a string literal is exactly its character codes; array ops read it
    prog = parse('str s "Hi" / const z 0 / get c s z / alen n s / print c / halt')
    assert interpret(prog)[-1] == float(ord("H"))  # get s[0] -> 'H' code 72
    prog2 = parse('str s "hello" / alen n s / print n / halt')
    assert interpret(prog2)[-1] == 5.0  # alen is string length


def test_char_and_mod_ops():
    assert interpret(parse('char d "(" / print d / halt'))[-1] == 40.0  # '(' code
    assert interpret(parse("const a 17 / const b 5 / mod r a b / print r / halt"))[-1] == 2.0
    assert interpret(parse("const a 15 / const b 5 / mod r a b / print r / halt"))[-1] == 0.0


def test_unterminated_string_literal_raises():
    with pytest.raises(ValueError, match="unterminated string"):
        parse('str s "oops')


def test_python_face_matches_reference_on_strings_unconditionally():
    for name, expect in _STR_EXPECT.items():
        r = verify(parse(EXAMPLES[name]), faces=("python",))
        assert r["reference"] == expect
        assert r["results"]["python"] == {"status": "AGREE", "value": expect}


def test_a_wrong_text_answer_is_a_disagree_not_a_pass():
    # agreement is exact-string: a face printing the wrong text must not count as verified
    prog = parse('str s "olleh" / prints s / halt')  # prints "olleh"
    r = verify(prog, faces=("python",))
    assert r["reference"] == "olleh"
    # sanity: a different reference string would not match this output
    assert "hello" != r["results"]["python"]["value"]


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_javascript_face_agrees_on_strings():
    for name, expect in _STR_EXPECT.items():
        r = verify(parse(EXAMPLES[name]), faces=("javascript",))
        assert r["results"]["javascript"] == {"status": "AGREE", "value": expect}


@pytest.mark.skipif(not _HAVE_RUST, reason="rustc not installed")
def test_rust_face_agrees_on_strings():
    for name, expect in _STR_EXPECT.items():
        r = verify(parse(EXAMPLES[name]), faces=("rust",))
        assert r["results"]["rust"] == {"status": "AGREE", "value": expect}
