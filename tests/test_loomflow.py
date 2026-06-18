"""loomflow: full (branching, looping) programs emit + run identically across language faces.

The cheap path past the straight-line scalar core: a dispatch loop, no relooper. A Python
interpreter of the IR is the reference; emitted faces are RUN and compared. Reference + parsing
+ branch semantics are checked unconditionally; the js/rust agreement runs only when the
toolchain is present (skip otherwise, never faked).
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.loomflow import EXAMPLES, emit, interpret, parse, verify  # noqa: E402

_HAVE_NODE = shutil.which("node") is not None
_HAVE_RUST = shutil.which("rustc") is not None


def test_reference_runs_a_real_loop():
    assert interpret(parse(EXAMPLES["sum_1_to_5"]))[-1] == 15.0  # 1+2+3+4+5
    assert interpret(parse(EXAMPLES["factorial_5"]))[-1] == 120.0  # 5!


def test_branch_actually_branches():
    # brz jumps when the slot is zero -> picks a different printed value
    taken = "const x 0\nbrz x zero\nconst r 99\njmp end\nlabel zero\nconst r 1\nlabel end\nprint r\nhalt"
    not_taken = taken.replace("const x 0", "const x 7")
    assert interpret(parse(taken))[-1] == 1.0  # branch taken
    assert interpret(parse(not_taken))[-1] == 99.0  # branch not taken


def test_unknown_op_raises():
    with pytest.raises(ValueError, match="unknown op"):
        parse("frobnicate a b")


def test_emit_produces_a_dispatch_loop_for_each_face():
    prog = parse(EXAMPLES["sum_1_to_5"])
    for lang in ("python", "javascript", "rust", "c"):
        src = emit(prog, lang)
        assert "pc" in src and len(src) > 0
    assert "while 0 <= pc" in emit(prog, "python")
    assert "while (pc >= 0" in emit(prog, "rust")


def test_python_face_matches_reference_unconditionally():
    r = verify(parse(EXAMPLES["sum_1_to_5"]), faces=("python",))
    assert r["reference"] == 15.0
    assert r["results"]["python"]["status"] == "AGREE"
    assert r["verified_count"] == 1


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_javascript_face_runs_the_loop_and_agrees():
    r = verify(parse(EXAMPLES["factorial_5"]), faces=("javascript",))
    assert r["results"]["javascript"] == {"status": "AGREE", "value": 120.0}


@pytest.mark.skipif(not _HAVE_RUST, reason="rustc not installed")
def test_rust_face_runs_the_loop_and_agrees():
    r = verify(parse(EXAMPLES["sum_1_to_5"]), faces=("rust",))
    assert r["results"]["rust"] == {"status": "AGREE", "value": 15.0}
