"""Bounded Sacred Tongues assembler and VM.

This is the local compiler lane for `.sts` command programs. It deliberately
stays below the canon/semantic layer: source text is assembled into bytecode and
run inside an in-process VM, not routed to a shell.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SacredTonguesToolchainError(ValueError):
    """Raised when assembly or VM execution fails."""


KO_PREFIXES = [
    "sil",
    "kor",
    "vel",
    "zar",
    "keth",
    "thul",
    "nav",
    "ael",
    "ra",
    "med",
    "gal",
    "lan",
    "joy",
    "good",
    "nex",
    "vara",
]
KO_SUFFIXES = [
    "a",
    "ae",
    "ei",
    "ia",
    "oa",
    "uu",
    "eth",
    "ar",
    "or",
    "il",
    "an",
    "en",
    "un",
    "ir",
    "oth",
    "esh",
]

CA_PREFIXES = [
    "bip",
    "bop",
    "klik",
    "loopa",
    "ifta",
    "thena",
    "elsa",
    "spira",
    "rythm",
    "quirk",
    "fizz",
    "gear",
    "pop",
    "zip",
    "mix",
    "chass",
]
CA_SUFFIXES = [
    "a",
    "e",
    "i",
    "o",
    "u",
    "y",
    "ta",
    "na",
    "sa",
    "ra",
    "lo",
    "mi",
    "ki",
    "zi",
    "qwa",
    "sh",
]

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


@dataclass(frozen=True)
class ParsedLine:
    lineno: int
    opcode: int
    args: list[str]


def _build_token_map(prefixes: list[str], suffixes: list[str]) -> dict[str, int]:
    return {f"{prefixes[byte >> 4]}'{suffixes[byte & 0x0F]}": byte for byte in range(256)}


KO_TOKENS = _build_token_map(KO_PREFIXES, KO_SUFFIXES)
CA_TOKENS = _build_token_map(CA_PREFIXES, CA_SUFFIXES)


def _clean_line(raw: str) -> str:
    return raw.split(";", 1)[0].strip()


def _normalize_opcode(token: str) -> int:
    token = token.strip().lower()
    if token in MNEMONIC_TO_OPCODE:
        return MNEMONIC_TO_OPCODE[token]
    if token.startswith("ko:") and token[3:] in KO_TOKENS:
        return KO_TOKENS[token[3:]]
    if token.startswith("ca:") and token[3:] in CA_TOKENS:
        return CA_TOKENS[token[3:]]
    raise SacredTonguesToolchainError(f"unknown opcode token: {token}")


def _parse_register(text: str) -> int:
    text = text.strip().lower()
    if not text.startswith("r"):
        raise SacredTonguesToolchainError(f"expected register r0..r15, got: {text}")
    try:
        idx = int(text[1:])
    except ValueError as exc:
        raise SacredTonguesToolchainError(f"invalid register: {text}") from exc
    if not 0 <= idx <= 15:
        raise SacredTonguesToolchainError(f"register out of range: {text}")
    return idx


def _parse_byte(text: str) -> int:
    text = text.strip().lower()
    try:
        value = int(text, 16) if text.startswith("0x") else int(text, 10)
    except ValueError as exc:
        raise SacredTonguesToolchainError(f"invalid byte value: {text}") from exc
    if not 0 <= value <= 255:
        raise SacredTonguesToolchainError(f"byte value out of range 0..255: {text}")
    return value


def _first_pass(lines: list[str]) -> tuple[list[tuple[int, str]], dict[str, int]]:
    instructions: list[tuple[int, str]] = []
    labels: dict[str, int] = {}
    for lineno, raw in enumerate(lines, start=1):
        line = _clean_line(raw)
        if not line:
            continue
        if line.endswith(":"):
            label = line[:-1].strip()
            if not label:
                raise SacredTonguesToolchainError(f"line {lineno}: empty label")
            if label in labels:
                raise SacredTonguesToolchainError(f"line {lineno}: duplicate label '{label}'")
            labels[label] = len(instructions)
            continue
        instructions.append((lineno, line))
    return instructions, labels


def _parse_instruction(lineno: int, line: str) -> ParsedLine:
    if " " in line:
        head, tail = line.split(" ", 1)
        args = [arg.strip() for arg in tail.split(",") if arg.strip()]
    else:
        head = line
        args = []

    opcode = _normalize_opcode(head)
    expected = EXPECTED_ARITY.get(opcode)
    if expected is None:
        raise SacredTonguesToolchainError(f"line {lineno}: unsupported opcode byte 0x{opcode:02x}")
    if len(args) != expected:
        raise SacredTonguesToolchainError(f"line {lineno}: opcode '{head}' expects {expected} args, got {len(args)}")
    return ParsedLine(lineno=lineno, opcode=opcode, args=args)


def _resolve_arg(opcode: int, arg_pos: int, text: str, labels: dict[str, int]) -> int:
    if opcode == 0x02:
        return labels[text] if text in labels else _parse_byte(text)
    if opcode in {0x03, 0x04}:
        if arg_pos == 0:
            return _parse_register(text)
        return labels[text] if text in labels else _parse_byte(text)
    if opcode == 0x05:
        return _parse_register(text) if arg_pos == 0 else _parse_byte(text)
    if opcode in {0x06, 0x07}:
        return _parse_register(text)
    if opcode in {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17}:
        return _parse_register(text)
    return 0


def assemble_text(text: str) -> list[int]:
    """Assemble `.sts` text into four-byte instruction bytecode."""
    instruction_lines, labels = _first_pass(text.splitlines())
    bytecode: list[int] = []
    for lineno, line in instruction_lines:
        parsed = _parse_instruction(lineno, line)
        args = [_resolve_arg(parsed.opcode, i, arg, labels) for i, arg in enumerate(parsed.args)]
        while len(args) < 3:
            args.append(0)
        bytecode.extend([parsed.opcode, args[0], args[1], args[2]])
    return bytecode


def load_program(path: Path) -> list[int]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise SacredTonguesToolchainError("JSON program must be a byte array")
        return [int(value) & 0xFF for value in data]
    return list(path.read_bytes())


class SacredTongueVM:
    def __init__(self, program: list[int]):
        if len(program) % 4 != 0:
            raise SacredTonguesToolchainError("program length must be a multiple of 4 bytes")
        self.program = [int(value) & 0xFF for value in program]
        self.reg = [0] * 16
        self.pc = 0
        self.halted = False
        self.output: list[int] = []
        self.steps = 0

    @property
    def instruction_count(self) -> int:
        return len(self.program) // 4

    def _fetch(self) -> tuple[int, int, int, int]:
        if not 0 <= self.pc < self.instruction_count:
            self.halted = True
            return (0x01, 0, 0, 0)
        i = self.pc * 4
        return self.program[i], self.program[i + 1], self.program[i + 2], self.program[i + 3]

    def step(self) -> None:
        if self.halted:
            return

        op, a, b, c = self._fetch()
        next_pc = self.pc + 1
        if op == 0x00:
            pass
        elif op == 0x01:
            self.halted = True
        elif op == 0x02:
            next_pc = a
        elif op == 0x03:
            if self.reg[a] == 0:
                next_pc = b
        elif op == 0x04:
            if self.reg[a] != 0:
                next_pc = b
        elif op == 0x05:
            self.reg[a] = b & 0xFF
        elif op == 0x06:
            self.reg[a] = self.reg[b] & 0xFF
        elif op == 0x07:
            self.output.append(self.reg[a] & 0xFF)
        elif op == 0x10:
            self.reg[a] = (self.reg[b] + self.reg[c]) & 0xFF
        elif op == 0x11:
            self.reg[a] = (self.reg[b] - self.reg[c]) & 0xFF
        elif op == 0x12:
            self.reg[a] = (self.reg[b] * self.reg[c]) & 0xFF
        elif op == 0x13:
            if self.reg[c] == 0:
                raise SacredTonguesToolchainError(f"division by zero at pc={self.pc}")
            self.reg[a] = (self.reg[b] // self.reg[c]) & 0xFF
        elif op == 0x14:
            self.reg[a] = (self.reg[b] ^ self.reg[c]) & 0xFF
        elif op == 0x15:
            self.reg[a] = (self.reg[b] & self.reg[c]) & 0xFF
        elif op == 0x16:
            self.reg[a] = (self.reg[b] | self.reg[c]) & 0xFF
        elif op == 0x17:
            self.reg[a] = 1 if self.reg[b] == self.reg[c] else 0
        else:
            raise SacredTonguesToolchainError(f"unknown opcode 0x{op:02x} at pc={self.pc}")

        self.pc = next_pc
        self.steps += 1

    def run(self, max_steps: int = 10000) -> dict[str, Any]:
        while not self.halted and self.steps < max_steps:
            self.step()
        if self.steps >= max_steps and not self.halted:
            raise SacredTonguesToolchainError(f"execution exceeded max_steps={max_steps}")
        return {
            "output": self.output,
            "registers": self.reg,
            "pc": self.pc,
            "halted": self.halted,
            "steps": self.steps,
        }


def compile_packet(source: str, *, source_name: str = "inline") -> dict[str, Any]:
    bytecode = assemble_text(source)
    bytecode_bytes = bytes(bytecode)
    return {
        "schema_version": "scbe_tongues_toolchain_compile_v1",
        "source_name": source_name,
        "source_sha256": hashlib.sha256(source.encode("utf-8", errors="replace")).hexdigest(),
        "bytecode": bytecode,
        "bytecode_sha256": hashlib.sha256(bytecode_bytes).hexdigest(),
        "instruction_count": len(bytecode) // 4,
        "byte_length": len(bytecode),
        "opcodes": {
            "semantic_layer": "sts-assembly",
            "transport_layer": "bounded-bytecode",
            "vm": "scbe-sacred-tongue-vm-v1",
        },
    }


def run_packet(program: list[int], *, max_steps: int = 10000) -> dict[str, Any]:
    vm = SacredTongueVM(program)
    result = vm.run(max_steps=max_steps)
    return {
        "schema_version": "scbe_tongues_toolchain_run_v1",
        "program_sha256": hashlib.sha256(bytes(program)).hexdigest(),
        "instruction_count": len(program) // 4,
        **result,
    }
