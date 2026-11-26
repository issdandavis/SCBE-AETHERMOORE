#!/usr/bin/env python3
"""Turing Rubix: cube turns as a tiny Turing-complete instruction surface.

A physical 3x3 Rubik's Cube has finite state, so it is not Turing complete by
itself. This module defines the useful SCBE version: cube moves are the control
surface, while the machine owns an unbounded sparse tape. The instruction set is
Brainfuck-equivalent, so the virtual Rubix machine is Turing complete under the
same assumptions: unbounded tape and unbounded execution time.
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Iterable

from python.scbe.atomic_tokenization import map_token_to_atomic_state
from python.scbe.bit_spine import BitSpineError, bf_to_ops, build_loop_map, run_ops_receipt

FACE_TONGUE = {"R": "KO", "L": "AV", "U": "RU", "D": "CA", "F": "UM", "B": "DR"}
TONGUE_ORDER = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_FIELD = {
    "KO": "authority / control / flow start",
    "AV": "transport / messaging / context carriage",
    "RU": "policy / constraints / binding",
    "CA": "compute / transform / ciphertext",
    "UM": "security / secrets / sensitive pressure",
    "DR": "schema / integrity / authentication",
}
TONGUE_PHI_WEIGHT = {
    "KO": 1.00,
    "AV": 1.62,
    "RU": 2.62,
    "CA": 4.24,
    "UM": 6.85,
    "DR": 11.09,
}
FACE_ATOMIC_BINDING = {
    "R": ("run", "operator"),
    "L": ("then", "operator"),
    "U": ("block", "safety"),
    "D": ("build", "operator"),
    "F": ("deny", "safety"),
    "B": ("if", "operator"),
}
FACE_QUARK = {
    "U": ("up", 2),
    "D": ("down", -1),
    "R": ("charm", 2),
    "L": ("strange", -1),
    "F": ("top", 2),
    "B": ("bottom", -1),
}
QUARK_COLORS = ("red", "green", "blue")

MOVE_INSTRUCTION = {
    "R": ">",
    "R'": "<",
    "U": "+",
    "U'": "-",
    "D": ".",
    "D'": ",",
    "F": "[",
    "F'": "]",
    "B": "!",
    "B'": "#",
    "L": "@",
    "L'": "~",
}

INSTRUCTION_NAME = {
    ">": "ptr_right",
    "<": "ptr_left",
    "+": "cell_inc",
    "-": "cell_dec",
    ".": "emit",
    ",": "read",
    "[": "loop_open",
    "]": "loop_close",
    "!": "seal_checkpoint",
    "#": "receipt_checkpoint",
    "@": "tongue_rotate",
    "~": "tongue_rotate_back",
}

EXECUTABLE = {">", "<", "+", "-", ".", ",", "[", "]"}


def parse_moves(text: str) -> list[str]:
    moves: list[str] = []
    for raw in text.replace(",", " ").split():
        move = raw.strip().upper().replace("`", "'").replace("’", "'")
        if move not in MOVE_INSTRUCTION:
            raise ValueError(f"unknown Rubix move {raw!r}")
        moves.append(move)
    return moves


def moves_to_program(moves: Iterable[str]) -> str:
    return "".join(MOVE_INSTRUCTION[move] for move in moves if MOVE_INSTRUCTION[move] in EXECUTABLE)


def program_to_moves(program: str) -> list[str]:
    reverse = {op: move for move, op in MOVE_INSTRUCTION.items()}
    out = []
    for char in program:
        if char in reverse and char in EXECUTABLE:
            out.append(reverse[char])
    return out


def build_jump_table(program: str) -> dict[int, int]:
    try:
        return build_loop_map(bf_to_ops(program))
    except BitSpineError as exc:
        raise ValueError(str(exc)) from exc


def conlang_projection(moves: Iterable[str]) -> list[dict[str, str]]:
    rows = []
    for index, move in enumerate(moves):
        face = move[0]
        op = MOVE_INSTRUCTION[move]
        rows.append(
            {
                "index": str(index),
                "move": move,
                "face": face,
                "tongue": FACE_TONGUE[face],
                "instruction": op,
                "instruction_name": INSTRUCTION_NAME[op],
            }
        )
    return rows


def quark_projection(moves: Iterable[str]) -> list[dict[str, Any]]:
    """Tag cube moves as quark-like command packets, not physics simulation."""

    rows = []
    for index, move in enumerate(moves):
        face = move[0]
        flavor, charge_thirds = FACE_QUARK[face]
        anti = move.endswith("'")
        color = QUARK_COLORS[index % len(QUARK_COLORS)]
        rows.append(
            {
                "index": index,
                "move": move,
                "face": face,
                "flavor": flavor,
                "anti": anti,
                "color": f"anti-{color}" if anti else color,
                "electric_charge_thirds": -charge_thirds if anti else charge_thirds,
                "instruction": MOVE_INSTRUCTION[move],
                "instruction_name": INSTRUCTION_NAME[MOVE_INSTRUCTION[move]],
            }
        )
    return rows


def _atomic_state_packet(face: str, token: str, context_class: str) -> dict[str, Any]:
    state = map_token_to_atomic_state(token, context_class=context_class)
    tongue = FACE_TONGUE[face]
    tongue_id = TONGUE_ORDER.index(tongue)
    return {
        "face": face,
        "tongue": tongue,
        "field": TONGUE_FIELD[tongue],
        "phi_weight": TONGUE_PHI_WEIGHT[tongue],
        "token": token,
        "context_class": context_class,
        "semantic_class": state.semantic_class,
        "element": {
            "symbol": state.element.symbol,
            "Z": state.element.Z,
            "group": state.element.group,
            "period": state.element.period,
            "valence": state.element.valence,
            "electronegativity": state.element.electronegativity,
            "witness_stable": state.element.witness_stable,
        },
        "tau": state.tau.as_dict(),
        "negative_state": state.negative_state,
        "dual_state": state.dual_state,
        "band_flag": state.band_flag,
        "resilience": state.resilience,
        "adaptivity": state.adaptivity,
        "trust_baseline": state.trust_baseline,
        "atomic_op_8_vector": [
            tongue_id + 1,
            state.element.group,
            state.element.period,
            state.element.valence,
            state.element.electronegativity,
            state.band_flag,
            tongue_id,
            0.0,
        ],
    }


def atomic_face_projection() -> dict[str, dict[str, Any]]:
    """Map the six Rubix faces onto SCBE's existing atomic-token states."""

    return {
        face: _atomic_state_packet(face, token, context)
        for face, (token, context) in FACE_ATOMIC_BINDING.items()
    }


def face_spin_state(moves: Iterable[str]) -> dict[str, int]:
    """Track each face as a quarter-turn orientation, modulo four."""

    spin = {face: 0 for face in FACE_TONGUE}
    for move in moves:
        face = move[0]
        delta = -1 if move.endswith("'") else 1
        spin[face] = (spin[face] + delta) % 4
    return spin


def display_faces(result: dict[str, Any]) -> dict[str, Any]:
    """Project a run receipt onto the six fixed Rubix display faces."""

    machine = result["machine"]
    projection = result["conlang_projection"]
    quarks = result["quark_projection"]
    atoms = result["atomic_faces"]
    last_move = projection[-1] if projection else None
    last_quark = quarks[-1] if quarks else None
    legal_moves = sorted(MOVE_INSTRUCTION)
    spin = face_spin_state(result["moves"])
    return {
        "schema": "scbe_turing_rubix_display_faces_v1",
        "spin_state": spin,
        "faces": {
            "R": {
                "tongue": "KO",
                "app": "terminal",
                "title": "Shell",
                "lines": [
                    f"spin {spin['R']}",
                    f"quark {FACE_QUARK['R'][0]}",
                    f"atom {atoms['R']['element']['symbol']}/{atoms['R']['semantic_class']}",
                    f"program {result['program'] or '<empty>'}",
                    f"ptr {machine['ptr']}",
                    f"steps {machine['steps']}",
                ],
            },
            "L": {
                "tongue": "AV",
                "app": "tools",
                "title": "Tool Ports",
                "lines": [
                    f"spin {spin['L']}",
                    f"quark {FACE_QUARK['L'][0]}",
                    f"atom {atoms['L']['element']['symbol']}/{atoms['L']['semantic_class']}",
                    "spine python.scbe.bit_spine.run_ops_receipt",
                    "cli python -m python.scbe.turing_rubix",
                    "display six fixed faces",
                ],
            },
            "U": {
                "tongue": "RU",
                "app": "task_state",
                "title": "State",
                "lines": [
                    f"spin {spin['U']}",
                    f"quark {FACE_QUARK['U'][0]}",
                    f"atom {atoms['U']['element']['symbol']}/{atoms['U']['semantic_class']}",
                    f"moves {len(result['moves'])}",
                    f"last {last_move['move'] if last_move else '<none>'}",
                    f"lane {last_move['instruction_name'] if last_move else '<none>'}",
                ],
            },
            "D": {
                "tongue": "CA",
                "app": "output",
                "title": "Output",
                "lines": [
                    f"spin {spin['D']}",
                    f"quark {FACE_QUARK['D'][0]}",
                    f"atom {atoms['D']['element']['symbol']}/{atoms['D']['semantic_class']}",
                    f"bytes {machine['output_bytes']}",
                    f"text {machine['output_text']!r}",
                    f"tape {machine['tape']}",
                ],
            },
            "F": {
                "tongue": "UM",
                "app": "legal_moves",
                "title": "Moves",
                "lines": [
                    f"spin {spin['F']}",
                    f"quark {FACE_QUARK['F'][0]}",
                    f"atom {atoms['F']['element']['symbol']}/{atoms['F']['semantic_class']}",
                    " ".join(legal_moves[:6]),
                    " ".join(legal_moves[6:]),
                    "> < + - . , [ ] executable",
                ],
            },
            "B": {
                "tongue": "DR",
                "app": "receipt",
                "title": "Receipt",
                "lines": [
                    f"spin {spin['B']}",
                    f"quark {FACE_QUARK['B'][0]}",
                    f"atom {atoms['B']['element']['symbol']}/{atoms['B']['semantic_class']}",
                    f"last_particle {last_quark['flavor'] if last_quark else '<none>'}",
                    result["schema"],
                    result["spine_core"],
                    "finite cube surface, spine runtime",
                ],
            },
        },
    }


def run_moves(text: str, *, input_text: str = "", max_steps: int = 100_000) -> dict[str, Any]:
    moves = parse_moves(text)
    program = moves_to_program(moves)
    receipt = run_ops_receipt(
        bf_to_ops(program),
        input_bytes=input_text.encode("utf-8"),
        max_steps=max_steps,
    )
    result = {
        "schema": "scbe_turing_rubix_run_v1",
        "moves": moves,
        "program": program,
        "spine_core": "python.scbe.bit_spine.run_ops_receipt",
        "conlang_projection": conlang_projection(moves),
        "quark_projection": quark_projection(moves),
        "atomic_faces": atomic_face_projection(),
        "machine": {
            "ptr": receipt["ptr"],
            "steps": receipt["steps"],
            "tape": {str(k): v for k, v in sorted(receipt["tape"].items())},
            "output_bytes": receipt["output_bytes"],
            "output_text": receipt["output_text"],
        },
    }
    result["display_faces"] = display_faces(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Turing Rubix move program.")
    parser.add_argument("moves", nargs="*", help="Move sequence, e.g. U U U D")
    parser.add_argument("--input", default="")
    parser.add_argument("--max-steps", type=int, default=100_000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_moves(" ".join(args.moves), input_text=args.input, max_steps=args.max_steps)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(result["machine"]["output_text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
