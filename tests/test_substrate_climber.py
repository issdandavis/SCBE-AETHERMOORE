"""substrate_climber: code THROUGH the board (loomfn) and prove the advantage is real -- every
board answer is cross-face verified (python+js+rust agree), not one unverified language.

The reference board programs must clear the numeric sub-ladder with the faces in agreement; a
climber that returns the right shape but the wrong answer must FAIL (faces agreeing on a wrong
value is not a pass -- value-correctness is checked too); and assemble must wrap a function into a
runnable closed program.
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm.substrate_climber import (  # noqa: E402
    BOARD_LADDER,
    assemble,
    climb_on_board,
    reference_board_climber,
)
from python.scbe import loomfn as L  # noqa: E402

_HAVE_RUST = shutil.which("rustc") is not None


def test_assemble_wraps_a_function_into_a_runnable_program():
    fib = next(p for p in BOARD_LADDER if p["name"] == "fib")
    prog = L.parse(assemble(fib["ref"], "fib", ["n"], (10,)))
    assert L.interpret(prog)[-1] == 55.0  # binds n=10, calls fib, prints 55


def test_reference_climber_clears_the_numeric_ladder_cross_face():
    # python + javascript here (fast); rust is checked separately below
    s = climb_on_board(faces=("python", "javascript"))
    assert s["solved"] == s["total"] == len(BOARD_LADDER)
    assert s["all_cross_face_verified"] is True
    for r in s["rows"]:
        assert r["cleared"] and r["faces_agree"] == r["tests"]


def test_wrong_answer_is_not_saved_by_faces_agreeing():
    # a climber with the right signature but a constant-wrong body: every face agrees on 0,
    # but 0 is the wrong value, so nothing clears. cross-face agreement != correctness.
    def zero_climber(problem):
        return "func %s %s / const r 0 / ret r" % (problem["name"], " ".join(problem["params"]))

    zero_climber.__name__ = "zero_climber"
    s = climb_on_board(zero_climber, faces=("python", "javascript"))
    assert s["solved"] == 0


def test_malformed_board_program_fails_loudly_not_silently():
    def broken(problem):
        return "func %s %s / call r nope / ret r" % (problem["name"], " ".join(problem["params"]))

    broken.__name__ = "broken"
    s = climb_on_board(broken, faces=("python",))
    assert s["solved"] == 0
    assert any(r["note"] for r in s["rows"])  # the failure is recorded, not hidden


@pytest.mark.skipif(not _HAVE_RUST, reason="rustc not installed")
def test_rust_face_agrees_on_the_board():
    fib = [p for p in BOARD_LADDER if p["name"] == "fib"]
    s = climb_on_board(reference_board_climber, ladder=fib, faces=("python", "javascript", "rust"))
    assert s["solved"] == 1
    assert s["rows"][0]["faces_agree"] == s["rows"][0]["tests"]  # py + js + rust all agree
