"""Guitar/tab surface for the Machine Crystal tape runtime.

This is Turing-complete by reduction to the eight Brainfuck-class operations
already hosted by ``python.scbe.machine_crystal``. The guitar layer is only an
interface: frets encode repeat counts, techniques encode operations, and the
repo Machine Crystal executes the lowered program with finite local bounds.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.machine_crystal import MachineCrystalProgram, run_crystal


OPEN_MIDI = [40, 45, 50, 55, 59, 64]
NOTE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

TECH_OP = {
    "pluck": "+",
    "damp": "-",
    "slide_up": ">",
    "slide_down": "<",
    "hammer": "[",
    "pull": "]",
    "tap": ".",
    "mute": ",",
}
VALUE_TECH = {"pluck", "damp", "slide_up", "slide_down"}


def tab_to_bf(events: list[tuple[int, int, str]]) -> str:
    """Compile ``(string, fret, technique)`` events to Brainfuck-class source."""

    out: list[str] = []
    for string, fret, technique in events:
        if not 0 <= int(string) <= 5:
            raise ValueError(f"string out of range: {string!r}")
        if fret < 0:
            raise ValueError(f"fret must be non-negative: {fret!r}")
        try:
            op = TECH_OP[technique]
        except KeyError as exc:
            raise ValueError(f"unknown guitar technique: {technique!r}") from exc
        if technique in VALUE_TECH:
            count = int(fret)
            if technique in {"slide_up", "slide_down"} and count == 0:
                count = 1
            out.append(op * count)
        else:
            out.append(op)
    return "".join(out)


def note_name(string: int, fret: int) -> str:
    midi = OPEN_MIDI[string] + fret
    return f"{NOTE[midi % 12]}{midi // 12 - 1}"


def run_guitar_tab(
    events: list[tuple[int, int, str]],
    *,
    max_steps: int = 100_000,
) -> dict:
    """Compile a guitar tab and execute it on the Machine Crystal runtime."""

    brainfuck = tab_to_bf(events)
    program = MachineCrystalProgram.from_brainfuck(brainfuck, source_label="guitar_tab")
    receipt = run_crystal(program, max_steps=max_steps)
    return {
        "schema": "scbe_guitar_turing_receipt_v1",
        "events": [
            {"string": s, "fret": f, "technique": t, "note": note_name(s, f)}
            for s, f, t in events
        ],
        "brainfuck": brainfuck,
        "program": program.packet(),
        "receipt": receipt,
    }


def tape_value(receipt: dict, index: int) -> int:
    return int(receipt["receipt"]["tape_window"].get(index, 0))


def demo_receipts() -> dict:
    add = [
        (0, 2, "pluck"),
        (0, 1, "slide_up"),
        (1, 3, "pluck"),
        (0, 0, "hammer"),
        (0, 1, "slide_down"),
        (0, 1, "pluck"),
        (0, 1, "slide_up"),
        (0, 1, "damp"),
        (0, 0, "pull"),
    ]
    count = [(0, 4, "pluck"), (0, 0, "tap")]
    double = [
        (0, 3, "pluck"),
        (0, 0, "hammer"),
        (0, 1, "slide_up"),
        (0, 2, "pluck"),
        (0, 1, "slide_down"),
        (0, 1, "damp"),
        (0, 0, "pull"),
    ]
    receipts = {
        "add_2_3": run_guitar_tab(add),
        "count_to_4": run_guitar_tab(count),
        "double_3": run_guitar_tab(double),
    }
    checks = {
        "add_2_3_cell0_is_5": tape_value(receipts["add_2_3"], 0) == 5,
        "count_to_4_outputs_04": receipts["count_to_4"]["receipt"]["output_hex"] == "04",
        "double_3_cell1_is_6": tape_value(receipts["double_3"], 1) == 6,
        "loops_present": "[" in receipts["add_2_3"]["brainfuck"]
        and "]" in receipts["double_3"]["brainfuck"],
    }
    return {
        "schema": "scbe_guitar_turing_demo_v1",
        "claim": "guitar tab is an interface onto the Machine Crystal Brainfuck-class runtime",
        "receipts": receipts,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> int:
    demo = demo_receipts()
    print("=== guitar tab -> Machine Crystal runtime ===\n")
    for name, receipt in demo["receipts"].items():
        played = "  ".join(
            f"{event['note']}/{event['technique']}" for event in receipt["events"]
        )
        tape = [tape_value(receipt, i) for i in range(4)]
        print(f"  {name}")
        print(f"    played: {played}")
        print(f"    -> brainfuck: {receipt['brainfuck']}")
        print(
            f"    -> tape[0:4]={tape} output_hex={receipt['receipt']['output_hex']} "
            f"steps={receipt['receipt']['steps']}"
        )
    print(f"\n  VERDICT: {demo['verdict']}")
    print(
        "  HONEST: Turing-completeness is by reduction to the established "
        "Brainfuck-class runtime; the guitar is the interface."
    )
    return 0 if demo["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
