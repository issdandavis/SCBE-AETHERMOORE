"""
Cube controller — the Bop-It Rubik's computer control surface.
==============================================================

The physical dream: a cube with a transmitter in the centre; you twist a face and
the motion fires an action on the computer, and it tells you the command out loud.
This is the software brain of that device.

The centre is the CA opcode core (the "transmitter"). Each of the 6 faces is one
Sacred Tongue; a quarter-turn of a face is an EVENT that the core transmits as one
opcode. A sequence of twists is a program — which the harness then compiles to code,
runs, and speaks back ("right turn... add... it computes seven").

    python -m python.scbe.cube_controller "R U F'"     # twist sequence -> command
    python -m python.scbe.cube_controller --repl        # Bop-It loop: twist, hear it
    python -m python.scbe.cube_controller "R U F'" --voice   # actually speak (Windows SAPI)

Twelve moves (Singmaster notation): a face letter, primed (') = counter-clockwise.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Dict, List, Sequence, Tuple

from . import polyglot as P

# face -> tongue (the 6 faces ARE the 6 Sacred Tongues); face -> spoken name
FACE_TONGUE = {"R": "ko", "L": "av", "U": "ru", "D": "ca", "F": "um", "B": "dr"}
FACE_NAME = {"U": "up", "D": "down", "L": "left", "R": "right", "F": "front", "B": "back"}

# a quarter-turn -> a core opcode. clockwise / counter-clockwise = an op and its partner.
MOVE_OP: Dict[str, str] = {
    "R": "add",
    "R'": "sub",
    "L": "mul",
    "L'": "div",
    "U": "inc",
    "U'": "dec",
    "D": "max",
    "D'": "min",
    "F": "sqrt",
    "F'": "pow",
    "B": "mod",
    "B'": "neg",
}

try:  # tongue token for each twist (optional)
    from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER as _STT

    _HAVE_TONGUES = True
except Exception:  # pragma: no cover - optional
    _HAVE_TONGUES = False


def _expand_names(text: str) -> str:
    """Lazily expand speedcuber trigger names (sexy, sledge, sune ...) to moves; no-op if the
    triggers module is absent. Imported lazily so triggers can import this module back."""
    try:
        from .triggers import expand_names

        return expand_names(text)
    except Exception:  # pragma: no cover - optional
        return text


def parse_moves(text: str) -> List[str]:
    """Text like "R U F'" -> a validated move list (raises on an unknown twist)."""
    out: List[str] = []
    for raw in text.replace(",", " ").split():
        m = raw.strip().upper().replace("’", "'")
        if m not in MOVE_OP:
            raise ValueError("unknown twist %r — moves are %s" % (raw, " ".join(sorted(MOVE_OP))))
        out.append(m)
    return out


def moves_to_program(moves: Sequence[str]) -> List[int]:
    return P.program_bytes(*[MOVE_OP[m] for m in moves])


def _tongue_token(face: str, op_byte: int) -> str:
    if not _HAVE_TONGUES:
        return ""
    return _STT.byte_to_token[FACE_TONGUE[face]][op_byte]


def say_move(m: str) -> str:
    """One twist, in words: 'right clockwise -> ADD  (ko: sil'a)'."""
    face = m[0]
    spin = "counter-clockwise" if m.endswith("'") else "clockwise"
    op = MOVE_OP[m]
    tok = _tongue_token(face, P.NAME_TO_BYTE[op])
    tail = "  (%s: %s)" % (FACE_TONGUE[face], tok) if tok else ""
    return "%s %s -> %s%s" % (FACE_NAME[face], spin, op.upper(), tail)


def run_program(prog: Sequence[int]) -> Tuple[object, str | None]:
    """Run the Python face on the default args; roundabout on undefined zones."""

    def call(safe):
        ns: dict = {}
        exec(compile(P.emit(prog, "python", safe=safe), "<cube>", "exec"), ns)  # noqa: S102
        return ns["tongue_fn"](2.0, 3.0, 4.0)

    try:
        return call(False), None
    except (ZeroDivisionError, ValueError, OverflowError) as e:
        try:
            return call(True), type(e).__name__
        except Exception as e2:  # pragma: no cover - defensive
            return None, type(e2).__name__
    except Exception as e:
        return None, type(e).__name__


def speak(text: str, voice: bool = False) -> None:
    """Print the narration; with voice=True, say it aloud via Windows SAPI."""
    print("  " + text)
    if voice and sys.platform == "win32":
        safe = text.replace("'", " ").replace('"', " ")
        try:  # non-destructive; opt-in only
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Add-Type -AssemblyName System.Speech; "
                    "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('%s')" % safe,
                ],
                timeout=15,
                capture_output=True,
            )
        except Exception:
            pass


def narrate(moves: Sequence[str], voice: bool = False) -> Tuple[List[int], List[str]]:
    """Announce each twist, build the program, run it, speak the command + result."""
    lines: List[str] = []
    for m in moves:
        s = say_move(m)
        speak(s, voice)
        lines.append(s)
    prog = moves_to_program(moves)
    cmd = ", ".join(MOVE_OP[m] for m in moves) or "(no twists)"
    val, note = run_program(prog)
    if val is None:
        res = 'command "%s" -> incomplete twist (need more operands)' % cmd
    elif note:
        res = 'command "%s" -> %s  (roundabout: %s)' % (cmd, val, note)
    else:
        res = 'command "%s" -> %s' % (cmd, val)
    speak(res, voice)
    lines.append(res)
    return prog, lines


def bop_it(voice: bool = False) -> int:
    print("CUBE CONTROLLER — twist a face, hear the command.  moves: " + " ".join(sorted(MOVE_OP)) + "   (':q' quits)")
    while True:
        try:
            line = input("  twist › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line in (":q", ":quit", "exit"):
            return 0
        if not line:
            continue
        try:
            narrate(parse_moves(_expand_names(line)), voice)
        except ValueError as e:
            print("  " + str(e))


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="scbe-bopit", description="twist the cube, hear the command")
    ap.add_argument("moves", nargs="*", help="twist sequence or trigger names, e.g. R U F'  or  sexy sledge")
    ap.add_argument("--voice", action="store_true", help="say it aloud (Windows SAPI)")
    ap.add_argument("--repl", action="store_true", help="interactive twist loop")
    ap.add_argument("--triggers", action="store_true", help="list speedcuber triggers (the move stdlib)")
    a = ap.parse_args(argv)
    if a.triggers:
        from .triggers import main as triggers_main

        return triggers_main(["--list"])
    if a.repl or not a.moves:
        return bop_it(a.voice)
    try:
        print("CUBE CONTROLLER")
        narrate(parse_moves(_expand_names(" ".join(a.moves))), a.voice)
        return 0
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
