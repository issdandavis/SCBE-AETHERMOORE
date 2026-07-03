#!/usr/bin/env python
"""Cat's Cradle Coding Cube: physical schematic + executable simulator.

Plain framing:
  - The automatic engine is Brainfuck / Machine Crystal runtime.
  - The manual transmission is a cube with colored faces, corner anchors, and
    string routes. The human turns/plucks/routes string paths to select ops.

If a gesture sequence lowers to Brainfuck and runs loops, it can compute.
This script proves that layer by executing gesture programs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "artifacts" / "cat_cradle_cube"


BF_OPS = {
    "red": "+",      # add current cell
    "blue": "-",     # subtract current cell
    "green": ">",    # move tape right
    "yellow": "<",   # move tape left
    "white": ".",    # output current cell
    "black": ",",    # input current cell
    "silver": "[",   # loop open
    "gold": "]",     # loop close
}

GESTURES = {
    "pluck-red": "red",
    "pluck-blue": "blue",
    "slide-green": "green",
    "slide-yellow": "yellow",
    "tap-white": "white",
    "mute-black": "black",
    "hook-silver": "silver",
    "release-gold": "gold",
}


@dataclass(frozen=True)
class Demo:
    name: str
    gestures: list[str]
    expected_cell0: int | None = None
    expected_output: list[int] | None = None


DEMOS = [
    Demo(
        "add_2_plus_3",
        [
            "pluck-red",
            "pluck-red",
            "slide-green",
            "pluck-red",
            "pluck-red",
            "pluck-red",
            "hook-silver",
            "slide-yellow",
            "pluck-red",
            "slide-green",
            "pluck-blue",
            "release-gold",
            "slide-yellow",
        ],
        expected_cell0=5,
    ),
    Demo(
        "double_3",
        [
            "pluck-red",
            "pluck-red",
            "pluck-red",
            "hook-silver",
            "slide-green",
            "pluck-red",
            "pluck-red",
            "slide-yellow",
            "pluck-blue",
            "release-gold",
            "slide-green",
        ],
        expected_cell0=6,
    ),
    Demo(
        "count_to_4_output",
        ["pluck-red", "pluck-red", "pluck-red", "pluck-red", "tap-white"],
        expected_output=[4],
    ),
]


def gestures_to_bf(gestures: list[str]) -> str:
    faces = [GESTURES[g] for g in gestures]
    return "".join(BF_OPS[face] for face in faces)


def run_bf(program: str, input_values: list[int] | None = None, max_steps: int = 100_000) -> dict:
    input_values = list(input_values or [])
    tape = [0] * 64
    ptr = 0
    pc = 0
    steps = 0
    output = []
    jumps = build_jumps(program)
    while pc < len(program):
        if steps > max_steps:
            raise RuntimeError("step limit exceeded")
        op = program[pc]
        if op == "+":
            tape[ptr] = (tape[ptr] + 1) % 256
        elif op == "-":
            tape[ptr] = (tape[ptr] - 1) % 256
        elif op == ">":
            ptr += 1
            if ptr >= len(tape):
                tape.append(0)
        elif op == "<":
            ptr = max(0, ptr - 1)
        elif op == ".":
            output.append(tape[ptr])
        elif op == ",":
            tape[ptr] = input_values.pop(0) if input_values else 0
        elif op == "[" and tape[ptr] == 0:
            pc = jumps[pc]
        elif op == "]" and tape[ptr] != 0:
            pc = jumps[pc]
        pc += 1
        steps += 1
    return {"tape": tape[:12], "ptr": ptr, "output": output, "steps": steps}


def build_jumps(program: str) -> dict[int, int]:
    stack = []
    jumps = {}
    for i, op in enumerate(program):
        if op == "[":
            stack.append(i)
        elif op == "]":
            if not stack:
                raise ValueError("unmatched loop close")
            start = stack.pop()
            jumps[start] = i
            jumps[i] = start
    if stack:
        raise ValueError("unmatched loop open")
    return jumps


def schematic() -> dict:
    return {
        "name": "Cat's Cradle Coding Cube",
        "purpose": "Manual transmission for a Turing-complete coding engine.",
        "materials": [
            "one 3D printed or wooden cube, 80-120 mm per side",
            "8 corner eyelets or small screw hooks",
            "12 edge grooves or small posts",
            "elastic string or conductive thread",
            "8 face labels/colors",
            "optional: magnets or reed switches for sensing face/edge routes",
        ],
        "faces": [
            {"face": "red", "op": "+", "gesture": "pluck-red", "meaning": "increment current tape cell"},
            {"face": "blue", "op": "-", "gesture": "pluck-blue", "meaning": "decrement current tape cell"},
            {"face": "green", "op": ">", "gesture": "slide-green", "meaning": "move tape pointer right"},
            {"face": "yellow", "op": "<", "gesture": "slide-yellow", "meaning": "move tape pointer left"},
            {"face": "white", "op": ".", "gesture": "tap-white", "meaning": "emit current tape cell"},
            {"face": "black", "op": ",", "gesture": "mute-black", "meaning": "read input into current tape cell"},
            {"face": "silver", "op": "[", "gesture": "hook-silver", "meaning": "open loop while current cell nonzero"},
            {"face": "gold", "op": "]", "gesture": "release-gold", "meaning": "close loop"},
        ],
        "physical_logic": [
            "A face color selects the opcode.",
            "A string crossing from one corner to another records sequence order.",
            "Turning the cube changes which face is presented next, like shifting a manual transmission.",
            "Loop gestures must pair silver/gold; the verifier refuses unmatched loops.",
            "The runtime remains automatic and exact; the cube is the manual control surface.",
        ],
        "sensor_version": {
            "low_tech": "user enters gesture names manually",
            "mid_tech": "camera detects colored face + hand/string route",
            "hardware": "reed switches or hall sensors on face/edge routes emit gesture events",
        },
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for demo in DEMOS:
        program = gestures_to_bf(demo.gestures)
        run = run_bf(program)
        ok = True
        if demo.expected_cell0 is not None:
            ok = ok and run["tape"][run["ptr"]] == demo.expected_cell0
        if demo.expected_output is not None:
            ok = ok and run["output"] == demo.expected_output
        results.append(
            {
                "name": demo.name,
                "gestures": demo.gestures,
                "brainfuck": program,
                "run": run,
                "ok": ok,
            }
        )
    receipt = {
        "ok": all(r["ok"] for r in results),
        "claim": "A cube/string gesture alphabet can act as a manual coding interface when lowered to a Turing-complete runtime.",
        "honest_scope": "The physical cube is the input/transmission. Turing completeness is from the Brainfuck-equivalent runtime it controls.",
        "schematic": schematic(),
        "demos": results,
    }
    (OUT_DIR / "schematic.json").write_text(json.dumps(schematic(), indent=2), encoding="utf-8")
    (OUT_DIR / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("CAT_CRADLE_CUBE_DONE")
    for r in results:
        print(f"{r['name']}: {r['brainfuck']} -> tape0/ptr={r['run']['tape'][r['run']['ptr']]} output={r['run']['output']} ok={r['ok']}")
    print(f"receipt: {OUT_DIR / 'receipt.json'}")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
