from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


KO_PREFIXES = [
    "sil", "kor", "vel", "zar", "keth", "thul", "nav", "ael",
    "ra", "med", "gal", "lan", "joy", "good", "nex", "vara",
]
KO_SUFFIXES = [
    "a", "ae", "ei", "ia", "oa", "uu", "eth", "ar",
    "or", "il", "an", "en", "un", "ir", "oth", "esh",
]

CA_PREFIXES = [
    "bip", "bop", "klik", "loopa", "ifta", "thena", "elsa", "spira",
    "rythm", "quirk", "fizz", "gear", "pop", "zip", "mix", "chass",
]
CA_SUFFIXES = [
    "a", "e", "i", "o", "u", "y", "ta", "na",
    "sa", "ra", "lo", "mi", "ki", "zi", "qwa", "sh",
]


def build_token_map(prefixes: List[str], suffixes: List[str]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for byte in range(256):
        token = f"{prefixes[byte >> 4]}'{suffixes[byte & 0x0F]}"
        mapping[token] = byte
    return mapping


KO_TOKENS = build_token_map(KO_PREFIXES, KO_SUFFIXES)
CA_TOKENS = build_token_map(CA_PREFIXES, CA_SUFFIXES)


MNEMONIC_TO_OPCODE = {
    "ko:nop": 0x00,
    "ko:halt": 0x01,
    "ko:jmp": 0x02,
    "ko:jz": 0x03,
    "ko:jnz": 0x04,
    "ko:set": 0x05,
    "ko:mov": 0x06,
    "ko:print": 0x07,
    "ca:add": 0x10,
    "ca:sub": 0x11,
    "ca:mul": 0x12,
    "ca:div": 0x13,
    "ca:xor": 0x14,
    "ca:and": 0x15,
    "ca:or": 0x16,
    "ca:cmp_eq": 0x17,
}

EXPECTED_ARITY = {
    0x00: 0,
    0x01: 0,
    0x02: 1,
    0x03: 2,
    0x04: 2,
    0x05: 2,
    0x06: 2,
    0x07: 1,
    0x10: 3,
    0x11: 3,
    0x12: 3,
    0x13: 3,
    0x14: 3,
    0x15: 3,
    0x16: 3,
    0x17: 3,
}


@dataclass
class ParsedLine:
    lineno: int
    opcode: int
    args: List[str]


def normalize_opcode(token: str) -> int:
    token = token.strip().lower()
    if token in MNEMONIC_TO_OPCODE:
        return MNEMONIC_TO_OPCODE[token]

    if token.startswith("ko:"):
        tongue_token = token[3:]
        if tongue_token in KO_TOKENS:
            return KO_TOKENS[tongue_token]
    if token.startswith("ca:"):
        tongue_token = token[3:]
        if tongue_token in CA_TOKENS:
            return CA_TOKENS[tongue_token]

    raise ValueError(f"unknown opcode token: {token}")


def parse_register(text: str) -> int:
    text = text.strip().lower()
    if not text.startswith("r"):
        raise ValueError(f"expected register (r0..r15), got: {text}")
    idx = int(text[1:])
    if not (0 <= idx <= 15):
        raise ValueError(f"register out of range: {text}")
    return idx


def parse_byte(text: str) -> int:
    text = text.strip().lower()
    if text.startswith("0x"):
        val = int(text, 16)
    else:
        val = int(text, 10)
    if not (0 <= val <= 255):
        raise ValueError(f"byte value out of range (0..255): {text}")
    return val


def clean_line(raw: str) -> str:
    return raw.split(";", 1)[0].strip()


def first_pass(lines: List[str]) -> Tuple[List[Tuple[int, str]], Dict[str, int]]:
    instructions: List[Tuple[int, str]] = []
    labels: Dict[str, int] = {}

    for lineno, raw in enumerate(lines, start=1):
        line = clean_line(raw)
        if not line:
            continue

        if line.endswith(":"):
            label = line[:-1].strip()
            if not label:
                raise ValueError(f"line {lineno}: empty label")
            if label in labels:
                raise ValueError(f"line {lineno}: duplicate label '{label}'")
            labels[label] = len(instructions)
            continue

        instructions.append((lineno, line))

    return instructions, labels


def parse_instruction(lineno: int, line: str) -> ParsedLine:
    if " " in line:
        head, tail = line.split(" ", 1)
        args = [a.strip() for a in tail.split(",") if a.strip()]
    else:
        head = line
        args = []

    opcode = normalize_opcode(head)
    expected = EXPECTED_ARITY.get(opcode)
    if expected is None:
        raise ValueError(f"line {lineno}: unsupported opcode byte 0x{opcode:02x}")
    if len(args) != expected:
        raise ValueError(
            f"line {lineno}: opcode '{head}' expects {expected} args, got {len(args)}"
        )

    return ParsedLine(lineno=lineno, opcode=opcode, args=args)


def resolve_arg(opcode: int, arg_pos: int, text: str, labels: Dict[str, int]) -> int:
    if opcode in {0x02}:  # jmp target
        return labels[text] if text in labels else parse_byte(text)
    if opcode in {0x03, 0x04}:  # jz/jnz reg,target
        if arg_pos == 0:
            return parse_register(text)
        return labels[text] if text in labels else parse_byte(text)
    if opcode in {0x05}:  # set reg,imm
        return parse_register(text) if arg_pos == 0 else parse_byte(text)
    if opcode in {0x06}:  # mov dst,src
        return parse_register(text)
    if opcode in {0x07}:  # print reg
        return parse_register(text)
    if opcode in {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17}:  # tri-reg
        return parse_register(text)
    return 0


def assemble_text(text: str) -> List[int]:
    lines = text.splitlines()
    instruction_lines, labels = first_pass(lines)
    out: List[int] = []

    for lineno, line in instruction_lines:
        parsed = parse_instruction(lineno, line)
        args = [resolve_arg(parsed.opcode, i, a, labels) for i, a in enumerate(parsed.args)]
        while len(args) < 3:
            args.append(0)
        out.extend([parsed.opcode, args[0], args[1], args[2]])

    return out


def assemble_file(source: Path, out_path: Path, json_out: bool = False) -> None:
    bytecode = assemble_text(source.read_text(encoding="utf-8"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if json_out:
        out_path.write_text(json.dumps(bytecode, indent=2) + "\n", encoding="utf-8")
    else:
        out_path.write_bytes(bytes(bytecode))


def main() -> None:
    parser = argparse.ArgumentParser(description="Sacred Tongue assembler (stasm)")
    parser.add_argument("source", type=Path, help="Assembly source (.sts)")
    parser.add_argument("output", type=Path, help="Output bytecode file")
    parser.add_argument("--json", action="store_true", help="Write bytecode as JSON array")
    args = parser.parse_args()

    assemble_file(args.source, args.output, json_out=args.json)


if __name__ == "__main__":
    main()
