r"""Turing-complete block foundry.

This file does three concrete things:

1. Defines the minimum Turing-complete control core: write bit, move cursor,
   conditional branch, jump, halt.
2. Defines a picture-building block library that cuts composites down to
   binary atoms.
3. Emits a small training pack where missing blocks must be built from atoms.

Run:
    python C:\dev\loom\turing_blocks.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


OUT_DIR = Path(r"C:\dev\loom")
TRAINING_JSONL = OUT_DIR / "block_training_pack.jsonl"
REPORT_MD = OUT_DIR / "BLOCK_TRAINING_REPORT.md"


@dataclass(frozen=True)
class Block:
    block_id: str
    kind: str
    expands_to: Tuple[str, ...] = ()
    binary_expectation: Optional[str] = None
    note: str = ""


class BlockLibrary:
    def __init__(self) -> None:
        self.blocks: Dict[str, Block] = {}

    def add(self, block: Block) -> None:
        if block.block_id in self.blocks:
            raise ValueError(f"duplicate block id: {block.block_id}")
        self.blocks[block.block_id] = block

    def expand(self, block_id: str) -> List[str]:
        if block_id not in self.blocks:
            raise KeyError(f"unknown block: {block_id}")
        block = self.blocks[block_id]
        if block.kind == "atom":
            return [block_id]
        atoms: List[str] = []
        for child in block.expands_to:
            atoms.extend(self.expand(child))
        return atoms

    def bits(self, block_id: str) -> str:
        atoms = self.expand(block_id)
        out = []
        for atom in atoms:
            if atom == "BIT_0":
                out.append("0")
            elif atom == "BIT_1":
                out.append("1")
            else:
                raise ValueError(f"{block_id} cut down to non-bit atom {atom}")
        return "".join(out)

    def verify(self, block_id: str) -> bool:
        block = self.blocks[block_id]
        return block.binary_expectation is None or self.bits(block_id) == block.binary_expectation


def build_picture_library() -> BlockLibrary:
    lib = BlockLibrary()

    lib.add(Block("BIT_0", "atom", binary_expectation="0", note="place one off pixel"))
    lib.add(Block("BIT_1", "atom", binary_expectation="1", note="place one on pixel"))

    # Complete 2-bit pair set. The user named 01 and 10; 00 and 11 are the missing pair brushes.
    lib.add(Block("PAIR_00", "composite", ("BIT_0", "BIT_0"), "00"))
    lib.add(Block("PAIR_01", "composite", ("BIT_0", "BIT_1"), "01"))
    lib.add(Block("PAIR_10", "composite", ("BIT_1", "BIT_0"), "10"))
    lib.add(Block("PAIR_11", "composite", ("BIT_1", "BIT_1"), "11"))

    # Nibbles used by the first picture exercise.
    lib.add(Block("NIBBLE_0101", "composite", ("PAIR_01", "PAIR_01"), "0101"))
    lib.add(Block("NIBBLE_0110", "composite", ("PAIR_01", "PAIR_10"), "0110"))
    lib.add(Block("NIBBLE_1001", "composite", ("PAIR_10", "PAIR_01"), "1001"))
    lib.add(Block("NIBBLE_1010", "composite", ("PAIR_10", "PAIR_10"), "1010"))

    # Picture row blocks.
    lib.add(Block("BYTE_EYE_A", "composite", ("NIBBLE_0110", "NIBBLE_0110"), "01100110"))
    lib.add(Block("BYTE_EYE_B", "composite", ("NIBBLE_1001", "NIBBLE_1001"), "10011001"))
    lib.add(Block("BYTE_PUPIL", "composite", ("NIBBLE_0101", "NIBBLE_1010"), "01011010"))

    lib.add(
        Block(
            "PICTURE_EYE_8X8",
            "composite",
            (
                "BYTE_EYE_A",
                "BYTE_EYE_B",
                "BYTE_PUPIL",
                "BYTE_EYE_B",
                "BYTE_EYE_B",
                "BYTE_PUPIL",
                "BYTE_EYE_B",
                "BYTE_EYE_A",
            ),
            "0110011010011001010110101001100110011001010110101001100101100110",
        )
    )

    return lib


def render_bits(bits: str, width: int = 8) -> str:
    rows = [bits[i : i + width] for i in range(0, len(bits), width)]
    return "\n".join("".join("#" if b == "1" else "." for b in row) for row in rows)


@dataclass
class TuringMachine:
    """Small bit-tape VM for the Turing-complete control core."""

    program: Dict[str, Tuple[str, Optional[str]]]
    start: str = "start"
    tape: Dict[int, int] = field(default_factory=dict)
    cursor: int = 0
    ip: str = "start"
    halted: bool = False
    steps: int = 0

    def read(self) -> int:
        return self.tape.get(self.cursor, 0)

    def write(self, bit: int) -> None:
        if bit not in (0, 1):
            raise ValueError("bit must be 0 or 1")
        self.tape[self.cursor] = bit

    def run(self, max_steps: int = 1000) -> None:
        self.ip = self.start
        while not self.halted and self.steps < max_steps:
            op, arg = self.program[self.ip]
            self.steps += 1
            if op == "WRITE_0":
                self.write(0)
                self.ip = str(arg)
            elif op == "WRITE_1":
                self.write(1)
                self.ip = str(arg)
            elif op == "MOVE_L":
                self.cursor -= 1
                self.ip = str(arg)
            elif op == "MOVE_R":
                self.cursor += 1
                self.ip = str(arg)
            elif op == "BRANCH_0":
                yes, no = str(arg).split("|", 1)
                self.ip = yes if self.read() == 0 else no
            elif op == "BRANCH_1":
                yes, no = str(arg).split("|", 1)
                self.ip = yes if self.read() == 1 else no
            elif op == "JUMP":
                self.ip = str(arg)
            elif op == "HALT":
                self.halted = True
            else:
                raise ValueError(f"unknown op: {op}")
        if not self.halted:
            raise RuntimeError(f"machine did not halt within {max_steps} steps")

    def window(self, start: int, end: int) -> str:
        return "".join(str(self.tape.get(i, 0)) for i in range(start, end))


def demo_turing_core() -> Tuple[str, int]:
    """Erase a run of 1s until the first 0. Exercises loop + branch + write + move."""

    program = {
        "start": ("BRANCH_0", "done|erase"),
        "erase": ("WRITE_0", "right"),
        "right": ("MOVE_R", "start"),
        "done": ("HALT", None),
    }
    tm = TuringMachine(program=program, tape={0: 1, 1: 1, 2: 1, 3: 0})
    tm.run()
    return tm.window(0, 4), tm.steps


def make_training_rows(lib: BlockLibrary) -> List[dict]:
    rows = [
        {
            "task": "Build the missing pair brush PAIR_00 from atoms.",
            "available": ["BIT_0", "BIT_1"],
            "target_block": "PAIR_00",
            "target_bits": "00",
            "answer": ["BIT_0", "BIT_0"],
        },
        {
            "task": "Build the missing pair brush PAIR_11 from atoms.",
            "available": ["BIT_0", "BIT_1"],
            "target_block": "PAIR_11",
            "target_bits": "11",
            "answer": ["BIT_1", "BIT_1"],
        },
        {
            "task": "Build NIBBLE_1010 from pair brushes.",
            "available": ["PAIR_01", "PAIR_10", "BIT_0", "BIT_1"],
            "target_block": "NIBBLE_1010",
            "target_bits": "1010",
            "answer": ["PAIR_10", "PAIR_10"],
        },
        {
            "task": "Finish the pupil row BYTE_PUPIL from two nibbles.",
            "available": ["NIBBLE_0101", "NIBBLE_0110", "NIBBLE_1001", "NIBBLE_1010"],
            "target_block": "BYTE_PUPIL",
            "target_bits": "01011010",
            "answer": ["NIBBLE_0101", "NIBBLE_1010"],
        },
    ]

    for row in rows:
        built_bits = "".join(bits_for_sequence(lib, row["answer"]))
        row["verified"] = built_bits == row["target_bits"]
        row["built_bits"] = built_bits
        row["verifier"] = "built_bits == target_bits"
    return rows


def bits_for_sequence(lib: BlockLibrary, sequence: Sequence[str]) -> List[str]:
    return [lib.bits(block_id) for block_id in sequence]


def write_training_pack(rows: Iterable[dict]) -> None:
    with TRAINING_JSONL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def write_report(lib: BlockLibrary, rows: List[dict], turing_result: str, turing_steps: int) -> None:
    picture_bits = lib.bits("PICTURE_EYE_8X8")
    lines = [
        "# Block Training Report",
        "",
        "## Turing Core Smoke Test",
        "",
        f"Program erased `1110` to `{turing_result}` in {turing_steps} steps.",
        "",
        "This does not prove every future visual block is correct. It verifies the control core has branch, loop, write, move, and halt behavior.",
        "",
        "## Picture Build",
        "",
        "Target block: `PICTURE_EYE_8X8`",
        "",
        "```text",
        render_bits(picture_bits),
        "```",
        "",
        f"Binary expansion length: {len(picture_bits)} bits",
        f"Picture verifies: {lib.verify('PICTURE_EYE_8X8')}",
        "",
        "## Composite Cutdowns",
        "",
    ]

    for block_id in [
        "PAIR_00",
        "PAIR_01",
        "PAIR_10",
        "PAIR_11",
        "NIBBLE_0101",
        "NIBBLE_0110",
        "NIBBLE_1001",
        "NIBBLE_1010",
        "BYTE_PUPIL",
    ]:
        block = lib.blocks[block_id]
        lines.append(
            f"- `{block_id}` -> {' '.join(block.expands_to) or block_id} -> `{lib.bits(block_id)}`"
        )

    lines.extend(["", "## Training Rows", ""])
    for row in rows:
        status = "PASS" if row["verified"] else "FAIL"
        lines.append(f"- {status}: {row['task']} `{row['built_bits']}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    lib = build_picture_library()
    bad = [block_id for block_id in lib.blocks if not lib.verify(block_id)]
    if bad:
        raise SystemExit(f"block verification failed: {bad}")

    turing_result, turing_steps = demo_turing_core()
    if turing_result != "0000":
        raise SystemExit(f"turing core smoke test failed: {turing_result}")

    rows = make_training_rows(lib)
    if not all(row["verified"] for row in rows):
        raise SystemExit("one or more training rows failed verification")

    write_training_pack(rows)
    write_report(lib, rows, turing_result, turing_steps)

    print("=== TURING-COMPLETE BLOCK FOUNDRY ===")
    print(f"core smoke: 1110 -> {turing_result} in {turing_steps} steps")
    print("picture:")
    print(render_bits(lib.bits("PICTURE_EYE_8X8")))
    print(f"\ntraining rows -> {TRAINING_JSONL}")
    print(f"report -> {REPORT_MD}")


if __name__ == "__main__":
    main()
