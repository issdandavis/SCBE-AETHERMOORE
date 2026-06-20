"""Speedcuber triggers — the muscle-memory standard library over the cube controller.

A speedcuber's whole skill is short, named, muscle-memorized move combos: the *sexy
move* (R U R' U'), the *sledgehammer* (R' F R F'), *sune* (R U R' U R U2 R'). They chain
these at 8-10 turns/second without conscious thought. Under the cube controller's fixed
move->opcode map (cube_controller.MOVE_OP), each trigger expands to a fixed opcode
SUBROUTINE — so a speedcuber's existing repertoire IS a standard library they can already
execute by hand. This module names those triggers, expands them to programs, and (the
smart-cube use case) RECOGNIZES a raw move stream back into the named triggers it contains
— the way a cuber parses their own solve.

    from python.scbe.triggers import trigger_program, recognize, parse_moves
    trigger_program("sexy sledge")            # named triggers -> one opcode program
    recognize(parse_moves("R U R' U'"))       # a raw solve  -> ['sexy']

Naming changes nothing about the computation: trigger_program(name) is byte-identical to
running the trigger's expanded moves through the controller — the name is just a handle a
cuber already owns.

Return-to-solved is UNDO. Every move has an inverse (R<->R'), and the inverse of a whole
sequence (reverse it, prime each move) is the algorithm that walks the cube back to solved
— the universal escape hatch. inverse()/undo() compute it, and this module proves two
cuber facts: 'unsexy' (U R U' R') IS the inverse of the sexy move, and 'hedge' IS the
inverse of the sledgehammer. The cube-level undo is always exact (group theory). At the
opcode level only the UNARY moves form a clean computational undo (U/U' = inc/dec restore
the number); the binary moves (add/sub, mul/div) restore the cube but not the stack, since
each binary op changes the stack depth — an honest asymmetry, not a bug.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from . import polyglot as P
from .cube_controller import MOVE_OP, moves_to_program, parse_moves


def _expand_notation(notation: str) -> Tuple[str, ...]:
    """'R U R' U2' -> ('R','U',"R'",'U','U'): split on space, unroll an X2 double turn."""
    out: List[str] = []
    for raw in notation.replace(",", " ").split():
        m = raw.strip().upper().replace("’", "'")
        if m.endswith("2"):
            base = m[:-1]
            out.extend([base, base])
        else:
            out.append(m)
    return tuple(out)


@dataclass(frozen=True)
class Trigger:
    """One named cuber combo: its human notation, its expanded base moves, its opcodes."""

    name: str
    singmaster: str  # human-facing notation, may contain X2 doubles
    note: str

    @property
    def moves(self) -> Tuple[str, ...]:
        return _expand_notation(self.singmaster)

    @property
    def ops(self) -> List[str]:
        return [MOVE_OP[m] for m in self.moves]


# The iconic triggers every speedcuber owns by muscle memory (real Singmaster notation).
_TRIGGER_LIST = [
    Trigger("trigger", "R U R'", "the basic insert trigger"),
    Trigger("sexy", "R U R' U'", "the sexy move — the most-used trigger in cubing"),
    Trigger("unsexy", "U R U' R'", "inverse sexy move"),
    Trigger("lefty_sexy", "L' U' L U", "left-hand sexy move"),
    Trigger("sledge", "R' F R F'", "the sledgehammer"),
    Trigger("hedge", "F R' F' R", "the hedslammer (inverse sledgehammer)"),
    Trigger("sune", "R U R' U R U2 R'", "the OLL sune — orients a corner triple"),
    Trigger("antisune", "R U2 R' U' R U' R'", "the antisune (inverse-handed sune)"),
]
TRIGGERS: Dict[str, Trigger] = {t.name: t for t in _TRIGGER_LIST}

# Fail loud at import if a trigger ever names a move the controller cannot fire.
for _t in _TRIGGER_LIST:
    for _m in _t.moves:
        if _m not in MOVE_OP:
            raise ValueError("trigger %r uses unknown move %r" % (_t.name, _m))


def expand_trigger(name: str) -> List[str]:
    """A trigger name -> its expanded base-move list (the moves a cuber's hands make)."""
    return list(TRIGGERS[name.lower()].moves)


def normalize_move(move: str) -> str:
    """Canonicalize a move's spelling only: trim, uppercase the face, ASCII the prime
    (curly ’ -> '). No inversion -- this is the spelling normal form invert_move builds on."""
    return move.strip().upper().replace("’", "'")


def invert_move(move: str) -> str:
    """One move -> its inverse: R<->R', and an X2 double turn is its own inverse."""
    m = normalize_move(move)
    if m.endswith("2"):
        return m
    if m.endswith("'"):
        return m[:-1]
    return m + "'"


def inverse(moves: Sequence[str]) -> List[str]:
    """The UNDO of a move sequence: reverse it, invert each move — the algorithm that walks
    the cube back to solved. Exact by group theory (inverse(seq) cancels seq). This is why
    'unsexy' is inverse('sexy') and 'hedge' is inverse('sledge')."""
    return [invert_move(m) for m in reversed(list(moves))]


def undo(text: str) -> List[str]:
    """Trigger names and/or moves -> the move sequence that returns the cube to solved."""
    return inverse(trigger_moves(text))


def expand_names(text: str) -> str:
    """Expand any trigger-NAME tokens to moves; leave raw moves untouched. Mixed input is
    fine: 'sexy R sledge' -> 'R U R' U' R R' F R F''. The handle reduces to moves."""
    out: List[str] = []
    for tok in text.replace(",", " ").split():
        key = tok.lower()
        if key in TRIGGERS:
            out.extend(TRIGGERS[key].moves)
        else:
            out.append(tok)
    return " ".join(out)


def trigger_moves(text: str) -> List[str]:
    """Trigger names and/or raw moves -> a validated flat move list (via the controller)."""
    return parse_moves(expand_names(text))


def trigger_program(text: str) -> List[int]:
    """Trigger names and/or raw moves -> the CA-opcode program (same pipeline as a twist)."""
    return moves_to_program(trigger_moves(text))


def recognize(moves: Sequence[str]) -> List[str]:
    """Segment a raw move stream into the named triggers it contains (greedy longest match).

    This is the smart-cube path: a Bluetooth cube streams moves; recognize() parses that
    stream back into the named subroutines a cuber actually performed. Unmatched moves pass
    through as themselves, so the output is a mix of trigger names and leftover raw moves.
    """
    pats = sorted(TRIGGERS.values(), key=lambda t: len(t.moves), reverse=True)
    seq = list(moves)
    out: List[str] = []
    i = 0
    while i < len(seq):
        hit = None
        for t in pats:
            n = len(t.moves)
            if tuple(seq[i : i + n]) == t.moves:
                hit = t
                break
        if hit is not None:
            out.append(hit.name)
            i += len(hit.moves)
        else:
            out.append(seq[i])
            i += 1
    return out


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    from .cube_controller import narrate

    ap = argparse.ArgumentParser(prog="scbe-triggers", description="speedcuber triggers as a code stdlib")
    ap.add_argument("program", nargs="*", help="trigger names and/or moves, e.g. sexy sledge")
    ap.add_argument("--list", action="store_true", help="list the known triggers")
    ap.add_argument("--recognize", metavar="MOVES", help="parse a raw move stream into triggers")
    ap.add_argument("--undo", metavar="PROGRAM", help="print the moves that return to solved (the undo)")
    ap.add_argument("--voice", action="store_true", help="say it aloud (Windows SAPI)")
    a = ap.parse_args(argv)

    if a.undo:
        print("undo (return to solved): " + " ".join(undo(a.undo)))
        return 0
    if a.list:
        print("TRIGGERS — a cuber's muscle memory as a standard library")
        for t in _TRIGGER_LIST:
            print("  %-11s %-22s -> %s" % (t.name, t.singmaster, ", ".join(t.ops)))
            print("  %-11s %s" % ("", t.note))
        return 0
    if a.recognize:
        seg = recognize(parse_moves(a.recognize))
        print("recognized: " + " ".join(seg))
        return 0
    if not a.program:
        ap.print_help()
        return 0
    text = " ".join(a.program)
    print("TRIGGER PROGRAM  (%s -> %s)" % (text, ", ".join(P.BYTE_TO_NAME[b] for b in trigger_program(text))))
    narrate(trigger_moves(text), a.voice)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
