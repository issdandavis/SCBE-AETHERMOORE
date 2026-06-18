"""Speedcuber triggers as a code stdlib, and return-to-solved as undo.

A trigger is a named muscle-memory combo; under the cube controller's fixed move->opcode
map it expands to a fixed opcode subroutine, so naming changes nothing about the program.
recognize() parses a raw move stream back into the triggers it contains (the smart-cube
path). inverse()/undo() walk the cube back to solved -- exactly, by group theory -- which
is why 'unsexy' is the inverse of 'sexy' and 'hedge' is the inverse of 'sledge'.
"""

from python.scbe import polyglot as P
from python.scbe.cube_controller import _expand_names, run_program
from python.scbe.triggers import (
    MOVE_OP,
    TRIGGERS,
    expand_trigger,
    inverse,
    invert_move,
    recognize,
    trigger_moves,
    trigger_program,
    undo,
)


def test_every_trigger_uses_only_real_controller_moves():
    for t in TRIGGERS.values():
        assert t.moves, t.name
        assert all(m in MOVE_OP for m in t.moves), t.name
        assert t.ops == [MOVE_OP[m] for m in t.moves]


def test_x2_double_turn_unrolls():
    # sune contains U2, which must unroll into two U quarter-turns
    assert expand_trigger("sune") == ["R", "U", "R'", "U", "R", "U", "U", "R'"]


def test_sexy_expands_and_programs_like_its_raw_moves():
    assert expand_trigger("sexy") == ["R", "U", "R'", "U'"]
    # naming changes nothing: the trigger program == the raw-move program
    assert trigger_program("sexy") == P.program_bytes("add", "inc", "sub", "dec")
    assert trigger_program("sexy") == trigger_program("R U R' U'")


def test_recognize_segments_a_solve_into_triggers():
    # a raw stream of moves is parsed back into the named subroutines it contains
    assert recognize(trigger_moves("R U R' U'")) == ["sexy"]
    assert recognize(trigger_moves("sexy sledge")) == ["sexy", "sledge"]
    # an unmatched move passes through as itself, between recognized triggers
    assert recognize(["R", "U", "R'", "U'", "D"]) == ["sexy", "D"]


def test_inverse_is_an_involution():
    for text in ("sexy", "sledge", "sune", "R U F' L'"):
        moves = trigger_moves(text)
        assert inverse(inverse(moves)) == moves
    assert invert_move("R") == "R'"
    assert invert_move("R'") == "R"
    assert invert_move("U2") == "U2"  # a double turn is its own inverse


def test_named_undo_pairs_are_real_inverses():
    # the module already contains undo pairs, and these are cuber facts:
    assert inverse(expand_trigger("sexy")) == expand_trigger("unsexy")
    assert inverse(expand_trigger("sledge")) == expand_trigger("hedge")


def test_undo_of_a_sequence_cancels_it_movewise():
    moves = trigger_moves("sexy sledge")
    # seq followed by its undo nets to a balanced sequence: reversing the back half
    # reproduces the forward half inverted, i.e. inverse(undo) == original
    assert inverse(undo("sexy sledge")) == moves


def test_unary_undo_restores_the_computation():
    # baseline: an empty program returns the last input (4.0) under run_program(2,3,4)
    base, _ = run_program(P.program_bytes())
    # U U (inc inc) are UNARY, so U U + its undo (U' U') restores the number exactly
    seq = ["U", "U"]
    restored, _ = run_program(P.program_bytes(*[MOVE_OP[m] for m in seq + undo(" ".join(seq))]))
    assert restored == base


def test_controller_cli_accepts_trigger_names():
    # the scbe-bopit hook expands trigger names to moves; raw moves are untouched
    assert _expand_names("sexy") == "R U R' U'"
    assert _expand_names("R U") == "R U"
    assert _expand_names("sexy R") == "R U R' U' R"
