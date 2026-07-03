"""Mode-governed guitar language on top of the Machine Crystal runtime."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for path in (ROOT, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from python.scbe.machine_crystal import MachineCrystalProgram, run_crystal


NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
DEGREE_OP = ["+", "-", ">", "<", "[", "]", "."]
DEGREE_GLOSS = ["add", "sub", "right", "left", "loop-open", "loop-close", "output"]

MODES = {
    "E minor": [4, 6, 7, 9, 11, 0, 2],
    "C major": [0, 2, 4, 5, 7, 9, 11],
    "A minor pentatonic": [9, 0, 2, 4, 7],
}


def legal_notes(mode: str) -> list[str]:
    return [NOTE[pc] for pc in MODES[mode]]


def compile_phrase(mode: str, notes: list[str]) -> str:
    """Compile in-key note names to Brainfuck-class source."""

    scale = MODES[mode]
    out: list[str] = []
    for name in notes:
        try:
            pc = NOTE.index(name)
        except ValueError as exc:
            raise ValueError(f"unknown note name: {name!r}") from exc
        if pc not in scale:
            raise ValueError(
                f"{name} is not in {mode}; legal notes: {legal_notes(mode)}"
            )
        degree = scale.index(pc)
        if degree >= len(DEGREE_OP):
            raise ValueError(f"{name} degree {degree + 1} has no operation")
        out.append(DEGREE_OP[degree])
    return "".join(out)


def run_phrase(mode: str, notes: list[str]) -> dict:
    brainfuck = compile_phrase(mode, notes)
    program = MachineCrystalProgram.from_brainfuck(brainfuck, source_label="guitar_mode")
    receipt = run_crystal(program)
    return {
        "schema": "scbe_guitar_mode_receipt_v1",
        "mode": mode,
        "legal_notes": legal_notes(mode),
        "notes": notes,
        "brainfuck": brainfuck,
        "program": program.packet(),
        "receipt": receipt,
    }


def demo_receipt() -> dict:
    add_notes = ["E", "E", "G", "E", "E", "E", "B", "A", "E", "G", "F#", "C"]
    add = run_phrase("E minor", add_notes)
    rejected = False
    try:
        compile_phrase("E minor", ["C#"])
    except ValueError:
        rejected = True
    checks = {
        "e_minor_adds_2_3": int(add["receipt"]["tape_window"].get(0, 0)) == 5,
        "f_sharp_legal_in_e_minor": compile_phrase("E minor", ["F#"]) == "-",
        "f_sharp_rejected_in_c_major": _is_rejected("C major", ["F#"]),
        "c_sharp_rejected_in_e_minor": rejected,
    }
    return {
        "schema": "scbe_guitar_mode_demo_v1",
        "receipt": add,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }


def _is_rejected(mode: str, notes: list[str]) -> bool:
    try:
        compile_phrase(mode, notes)
    except ValueError:
        return True
    return False


def main() -> int:
    print("=== guitar language v2: modes as governed dialects ===\n")
    for mode in MODES:
        degrees = " ".join(
            f"{NOTE[pc]}={DEGREE_GLOSS[i]}"
            for i, pc in enumerate(MODES[mode])
            if i < len(DEGREE_OP)
        )
        print(f"  {mode:20}: {degrees}")
    demo = demo_receipt()
    receipt = demo["receipt"]
    print(f"\n  PLAY in {receipt['mode']}: {' '.join(receipt['notes'])}")
    print(
        f"    -> brainfuck {receipt['brainfuck']} "
        f"-> tape[0]={receipt['receipt']['tape_window'].get(0, 0)}"
    )
    print("\n  governance:")
    for mode in ("E minor", "C major"):
        verdict = "REJECTED" if _is_rejected(mode, ["F#"]) else "LEGAL"
        print(f"    play F# in {mode:9}: {verdict}")
    print(f"\n  VERDICT: {demo['verdict']}")
    print(
        "  HONEST: computational power still comes from reduction to the "
        "Machine Crystal Brainfuck-class runtime; the mode is the legal alphabet."
    )
    return 0 if demo["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
