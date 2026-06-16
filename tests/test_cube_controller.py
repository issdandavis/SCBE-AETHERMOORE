"""Bop-It cube controller — twists -> opcodes -> spoken command -> run."""
import pytest

from python.scbe import cube_controller as C
from python.scbe import polyglot as P


def test_every_move_maps_to_a_core_op():
    assert len(C.MOVE_OP) == 12
    for m, op in C.MOVE_OP.items():
        assert op in P.SCALAR_OPS
        assert m[0] in C.FACE_NAME and C.FACE_TONGUE[m[0]] in ("ko", "av", "ru", "ca", "um", "dr")


def test_parse_and_program():
    moves = C.parse_moves("R U F'")
    assert moves == ["R", "U", "F'"]
    assert C.moves_to_program(moves) == P.program_bytes("add", "inc", "pow")


def test_parse_rejects_unknown_twist():
    with pytest.raises(ValueError):
        C.parse_moves("R X")                      # X is not a face


def test_narrate_speaks_moves_and_result(capsys):
    prog, lines = C.narrate(["R", "U", "F"])      # add, inc, sqrt  (well-defined)
    assert prog == P.program_bytes("add", "inc", "sqrt")
    joined = " ".join(lines)
    assert "right clockwise -> ADD" in joined
    assert "front clockwise -> SQRT" in joined
    assert any(line.startswith('command "add, inc, sqrt"') for line in lines)


def test_narrate_handles_undefined_zone():
    # F' is pow; a sequence that divides by a zero falls back to the roundabout, never crashes
    _, lines = C.narrate(["U'", "U'", "U'", "L'"])  # dec dec dec div -> may underflow/roundabout
    assert any("command" in ln for ln in lines)    # always announces, never raises


def test_repl_quits_clean(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: ":q")
    assert C.bop_it(voice=False) == 0
