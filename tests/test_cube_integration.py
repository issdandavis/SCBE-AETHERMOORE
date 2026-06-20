"""Whole-stack integration — fuzz the pipeline and assert every embedding's invariant.

tokens -> opcode object -> {board, torus, DNA, 18 faces, tongue, run} must all stay
mutually consistent on random programs. This is the "does the thesis hold" test."""

import random

import pytest

from python.scbe import bijective_dna as DNA
from python.scbe import board as B
from python.scbe import frontdoor as F
from python.scbe import polyglot as P
from python.scbe import torus as T

_ALPHABET = sorted(P.SCALAR_OPS)


def _rand(n, seed):
    rng = random.Random(seed)
    return [rng.choice(_ALPHABET) for _ in range(n)]


@pytest.mark.parametrize("seed", range(80))
def test_whole_stack_consistent(seed):
    names = _rand(seed % 18, seed)  # programs of length 0..17
    text = " ".join(names)

    nm, prog = F.tokens_to_program(text)
    assert nm == names

    # board: discrete reversible address
    assert B.recover(B.place(prog)) == prog
    for b in prog:
        assert B.from_point(*B.to_point(b)) == b
        assert B.from_cube(*B.to_cube(b)) == b

    # bijective DNA: 18 faces decode to one object, seekable, antiparallel, sealed
    rep = DNA.verify(names)
    assert rep["all_faces_agree"] and rep["faces_agree"] == 18
    assert rep["seekable"] and rep["rc_involution"] and rep["base_pairs_ok"]
    assert rep.get("seal_roundtrip", True)

    # polyglot: every face re-decodes to exactly the program
    for lang in P.languages():
        assert DNA.decode_from_source(P.emit(prog, lang)) == prog

    # tongue keyboard: spell -> decode round-trips
    if F._HAVE_TONGUES:
        spell = F.tongue_spell(prog, "ko")
        _, back = F.tokens_to_program(spell, tongue="ko")
        assert back == prog

    # torus: distance is a symmetric metric (>=0, d(a,a)=0)
    for a in prog:
        assert T.torus_distance(a, a) == 0.0
        for b in prog:
            assert T.torus_distance(a, b) >= 0
            assert abs(T.torus_distance(a, b) - T.torus_distance(b, a)) < 1e-12

    # the front door renders the whole thing without crashing (board on)
    out = F.render(text, ("python", "rust"), color=False, board=True)
    assert "cube code" in out


def test_all_64_opcodes_have_distinct_coordinates():
    pts = {B.to_point(b) for b in range(64)}
    cubes = {B.to_cube(b) for b in range(64)}
    colors = {B.rgb(b) for b in range(64)}
    assert len(pts) == len(cubes) == len(colors) == 64  # no embedding collides


def test_band_axis_agrees_across_board_and_cube():
    for b in range(64):
        row, _col = B.to_point(b)
        band, _mid, _c = B.to_cube(b)
        assert row == band  # the band is the same axis both ways


@pytest.mark.parametrize("seed", range(40))
def test_run_on_enter_never_raises(seed):
    names = _rand(seed % 10 + 1, seed + 999)
    out = F.render(" ".join(names), ("python",), color=False)
    assert "runs" in out  # always produces a runs line, never throws
