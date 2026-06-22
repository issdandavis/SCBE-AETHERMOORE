"""Bit spine: byte-exact binary, hex, trit, and minimal machine layers.

The spine rule is simple: bytes are canonical. Binary, hexadecimal, and fixed
width trits are reversible projections of the same payload. Higher systems
can attach meanings later, but this layer only promises bit-for-bit recovery.

The tiny machine layer uses the eight Brainfuck-class operations as 3-bit
opcodes. With an unbounded tape this instruction set is Turing complete; this
runtime keeps finite safety limits for tests and CLI use.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Literal, Sequence

TRITS_PER_BYTE = 6  # 3^6 = 729, enough for every byte with invalid states left unused.
SPINE_MAGIC = b"BSPN"
SPINE_VERSION = 1
HASH_LEN = 32


class BitSpineError(ValueError):
    """Invalid bit-spine projection, program, or integrity check."""


class SpineOp(IntEnum):
    MOVE_RIGHT = 0  # >
    MOVE_LEFT = 1  # <
    INC = 2  # +
    DEC = 3  # -
    OUT = 4  # .
    IN = 5  # ,
    LOOP_START = 6  # [
    LOOP_END = 7  # ]


BF_TO_OP = {
    ">": SpineOp.MOVE_RIGHT,
    "<": SpineOp.MOVE_LEFT,
    "+": SpineOp.INC,
    "-": SpineOp.DEC,
    ".": SpineOp.OUT,
    ",": SpineOp.IN,
    "[": SpineOp.LOOP_START,
    "]": SpineOp.LOOP_END,
}
OP_TO_BF = {op: char for char, op in BF_TO_OP.items()}

Symbol = Literal["0", "1", "B"]
Move = Literal["L", "R", "N"]
TransitionKey = tuple[str, Symbol]
TransitionValue = tuple[str, Symbol, Move]


@dataclass(frozen=True, slots=True)
class BitSpine:
    """Canonical byte payload with exact binary/hex/trit projections."""

    data: bytes

    @classmethod
    def from_bits(cls, bits: str) -> "BitSpine":
        return cls(bits_to_bytes(bits))

    @classmethod
    def from_hex(cls, hex_text: str) -> "BitSpine":
        return cls(hex_to_bytes(hex_text))

    @classmethod
    def from_trits(cls, trits: Sequence[int]) -> "BitSpine":
        return cls(trits_to_bytes(trits))

    def bits(self) -> str:
        return bytes_to_bits(self.data)

    def hex(self) -> str:
        return self.data.hex()

    def trits(self) -> list[int]:
        return bytes_to_trits(self.data)

    def digest(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    def packet(self) -> dict:
        return {
            "schema": "scbe_bit_spine_v1",
            "byte_len": len(self.data),
            "sha256": self.digest(),
            "binary": self.bits(),
            "hex": self.hex(),
            "trits": self.trits(),
        }


@dataclass(frozen=True, slots=True)
class BinaryTuringMachine:
    """Finite transition-table machine over tape alphabet {0, 1, B}.

    This is the strict binary computational spine. Higher encodings may be
    convenient, but this machine can simulate any larger alphabet by encoding
    symbols as binary strings.
    """

    transitions: dict[TransitionKey, TransitionValue]
    start_state: str
    halt_states: frozenset[str] = frozenset({"HALT"})
    blank: Symbol = "B"

    def run(
        self,
        input_bits: str,
        *,
        max_steps: int = 100_000,
        head: int = 0,
    ) -> dict:
        compact = "".join(str(input_bits).split())
        if any(ch not in "01" for ch in compact):
            raise BitSpineError("binary Turing input may only contain 0 and 1")
        tape: dict[int, Symbol] = {i: ch for i, ch in enumerate(compact)}  # type: ignore[dict-item]
        state = self.start_state
        steps = 0

        while state not in self.halt_states:
            steps += 1
            if steps > max_steps:
                raise BitSpineError("binary Turing machine exceeded max_steps")
            symbol: Symbol = tape.get(head, self.blank)
            rule = self.transitions.get((state, symbol))
            if rule is None:
                raise BitSpineError(f"missing transition for ({state!r}, {symbol!r})")
            next_state, write_symbol, move = rule
            if write_symbol not in ("0", "1", "B"):
                raise BitSpineError(f"invalid write symbol: {write_symbol!r}")
            if write_symbol == self.blank:
                tape.pop(head, None)
            else:
                tape[head] = write_symbol
            if move == "L":
                head -= 1
            elif move == "R":
                head += 1
            elif move != "N":
                raise BitSpineError(f"invalid move: {move!r}")
            state = next_state

        return {
            "state": state,
            "steps": steps,
            "head": head,
            "tape": dict(tape),
            "bits": tape_to_bits(tape),
        }


def tape_to_bits(tape: dict[int, Symbol]) -> str:
    occupied = [pos for pos, symbol in tape.items() if symbol in ("0", "1")]
    if not occupied:
        return ""
    left, right = min(occupied), max(occupied)
    return "".join(tape.get(pos, "B") for pos in range(left, right + 1)).strip("B")


def binary_increment_machine() -> BinaryTuringMachine:
    """Transition table for incrementing a binary number by one.

    The head starts at the leftmost input bit. The machine scans right to the
    first blank, carries left over trailing 1s, writes the first 0 as 1, and
    grows the number when the carry reaches the left blank.
    """

    return BinaryTuringMachine(
        start_state="seek_end",
        transitions={
            ("seek_end", "0"): ("seek_end", "0", "R"),
            ("seek_end", "1"): ("seek_end", "1", "R"),
            ("seek_end", "B"): ("carry", "B", "L"),
            ("carry", "1"): ("carry", "0", "L"),
            ("carry", "0"): ("HALT", "1", "N"),
            ("carry", "B"): ("HALT", "1", "N"),
        },
    )


@dataclass(frozen=True, slots=True)
class RelationshipStep:
    """One SCBE relationship-token instruction over an 8-bit state surface."""

    relation: str
    args: tuple[str, ...]


@dataclass(slots=True)
class RelationshipMachine:
    """Tiny 8-bit VM whose primitive is a verified relationship transition.

    This intentionally sits above binary opcodes. It is a teaching bridge from
    ``State + Instruction -> New State`` into SCBE's preferred shape:
    ``State + Relationship + Transformation + Verification``.
    """

    memory: bytearray
    registers: dict[str, int]

    @classmethod
    def from_bytes(cls, memory: bytes = b"") -> "RelationshipMachine":
        mem = bytearray(256)
        mem[: min(256, len(memory))] = memory[:256]
        return cls(memory=mem, registers={"A": 0, "B": 0, "C": 0, "D": 0})

    def state_bytes(self) -> bytes:
        regs = bytes(self.registers[name] & 0xFF for name in ("A", "B", "C", "D"))
        return regs + bytes(self.memory)

    def state_digest(self) -> str:
        return hashlib.sha256(self.state_bytes()).hexdigest()

    def read(self, address: int, register: str) -> None:
        _check_register(register)
        self.registers[register] = self.memory[_addr(address)]

    def transform(self, op: str, target: str, value: str | None = None) -> None:
        _check_register(target)
        op = op.lower()
        current = self.registers[target]
        operand = 0 if value is None else self.resolve(value)
        if op == "copy":
            result = operand
        elif op == "inc":
            result = current + 1
        elif op == "dec":
            result = current - 1
        elif op == "add":
            result = current + operand
        elif op == "sub":
            result = current - operand
        elif op == "xor":
            result = current ^ operand
        elif op == "and":
            result = current & operand
        elif op == "or":
            result = current | operand
        elif op == "not":
            result = ~current
        else:
            raise BitSpineError(f"unknown relationship transform: {op}")
        self.registers[target] = result & 0xFF

    def write(self, register: str, address: int) -> None:
        _check_register(register)
        self.memory[_addr(address)] = self.registers[register] & 0xFF

    def verify(self, left: str, op: str, right: str) -> bool:
        lhs = self.resolve(left)
        rhs = self.resolve(right)
        if op == "eq":
            return lhs == rhs
        if op == "neq":
            return lhs != rhs
        if op == "lt":
            return lhs < rhs
        if op == "lte":
            return lhs <= rhs
        if op == "gt":
            return lhs > rhs
        if op == "gte":
            return lhs >= rhs
        raise BitSpineError(f"unknown relationship verifier: {op}")

    def resolve(self, term: str) -> int:
        compact = term.strip()
        upper = compact.upper()
        if upper in self.registers:
            return self.registers[upper]
        if compact.lower().startswith("mem[") and compact.endswith("]"):
            return self.memory[_addr(_parse_int(compact[4:-1]))]
        return _parse_int(compact) & 0xFF


def _addr(value: int) -> int:
    if value < 0 or value > 0xFF:
        raise BitSpineError(f"8-bit memory address out of range: {value}")
    return value


def _check_register(register: str) -> None:
    if register not in {"A", "B", "C", "D"}:
        raise BitSpineError(f"unknown 8-bit register: {register}")


def _parse_int(value: str) -> int:
    text = str(value).strip()
    if not text:
        raise BitSpineError("empty integer term")
    try:
        return int(text, 0)
    except ValueError as exc:
        raise BitSpineError(f"invalid integer term: {value!r}") from exc


def parse_relationship_program(source: str) -> list[RelationshipStep]:
    """Parse semicolon/newline separated relationship-token instructions.

    Grammar:
      - ``read <addr> <reg>``
      - ``transform <op> <reg> [value|reg|mem[n]]``
      - ``write <reg> <addr>``
      - ``verify <left> <eq|neq|lt|lte|gt|gte> <right>``
    """

    steps: list[RelationshipStep] = []
    for raw in str(source).replace(";", "\n").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = tuple(line.split())
        relation = parts[0].lower()
        args = parts[1:]
        if relation == "read" and len(args) == 2:
            steps.append(RelationshipStep(relation, args))
        elif relation == "transform" and len(args) in (2, 3):
            steps.append(RelationshipStep(relation, args))
        elif relation == "write" and len(args) == 2:
            steps.append(RelationshipStep(relation, args))
        elif relation == "verify" and len(args) == 3:
            steps.append(RelationshipStep(relation, args))
        else:
            raise BitSpineError(f"invalid relationship instruction: {line!r}")
    return steps


def run_relationship_program(
    source: str,
    *,
    memory: bytes = b"",
    max_steps: int = 10_000,
) -> dict:
    """Run SCBE relationship tokens and return an auditable transition receipt."""

    steps = parse_relationship_program(source)
    if len(steps) > max_steps:
        raise BitSpineError("relationship program exceeded max_steps")
    machine = RelationshipMachine.from_bytes(memory)
    trace = []
    verified = True
    for index, step in enumerate(steps):
        before = machine.state_digest()
        check: bool | None = None
        if step.relation == "read":
            machine.read(_parse_int(step.args[0]), step.args[1].upper())
        elif step.relation == "transform":
            value = step.args[2].upper() if len(step.args) == 3 and step.args[2].upper() in machine.registers else (
                step.args[2] if len(step.args) == 3 else None
            )
            machine.transform(step.args[0], step.args[1].upper(), value)
        elif step.relation == "write":
            machine.write(step.args[0].upper(), _parse_int(step.args[1]))
        elif step.relation == "verify":
            left = step.args[0].upper() if step.args[0].upper() in machine.registers else step.args[0]
            right = step.args[2].upper() if step.args[2].upper() in machine.registers else step.args[2]
            check = machine.verify(left, step.args[1].lower(), right)
            verified = verified and check
        else:  # pragma: no cover - parser prevents this.
            raise BitSpineError(f"unknown relationship token: {step.relation}")
        after = machine.state_digest()
        trace.append(
            {
                "step": index,
                "relationship": step.relation,
                "args": list(step.args),
                "before_sha256": before,
                "after_sha256": after,
                "verified": check,
            }
        )

    nonzero_memory = {
        str(index): value for index, value in enumerate(machine.memory) if value
    }
    return {
        "schema": "scbe_relationship_vm_receipt_v1",
        "model": "8-bit relationship-token VM",
        "registers": dict(machine.registers),
        "memory_nonzero": nonzero_memory,
        "verified": verified,
        "steps": len(steps),
        "trace": trace,
        "state_sha256": machine.state_digest(),
    }


def bytes_to_bits(data: bytes) -> str:
    return "".join(f"{byte:08b}" for byte in data)


def bits_to_bytes(bits: str) -> bytes:
    compact = "".join(str(bits).split())
    if len(compact) % 8:
        raise BitSpineError("bit string length must be a multiple of 8")
    if any(ch not in "01" for ch in compact):
        raise BitSpineError("bit string may only contain 0 and 1")
    return bytes(int(compact[i : i + 8], 2) for i in range(0, len(compact), 8))


def hex_to_bytes(hex_text: str) -> bytes:
    compact = "".join(str(hex_text).split()).lower()
    if compact.startswith("0x"):
        compact = compact[2:]
    if len(compact) % 2:
        raise BitSpineError("hex string length must be even")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise BitSpineError("invalid hex string") from exc


def _byte_to_base3(byte: int) -> list[int]:
    digits = [0] * TRITS_PER_BYTE
    value = int(byte)
    for index in range(TRITS_PER_BYTE - 1, -1, -1):
        digits[index] = value % 3
        value //= 3
    return digits


def bytes_to_trits(data: bytes, *, balanced: bool = True) -> list[int]:
    """Encode bytes as fixed-width trits.

    Balanced mode maps base-3 digits ``0,1,2`` to ``-1,0,+1`` for SCBE's
    trit language. Set ``balanced=False`` for raw ternary digits.
    """

    out: list[int] = []
    for byte in data:
        digits = _byte_to_base3(byte)
        out.extend((digit - 1) if balanced else digit for digit in digits)
    return out


def trits_to_bytes(trits: Sequence[int], *, balanced: bool = True) -> bytes:
    if len(trits) % TRITS_PER_BYTE:
        raise BitSpineError("trit sequence length must be a multiple of 6")
    out = bytearray()
    for offset in range(0, len(trits), TRITS_PER_BYTE):
        value = 0
        for trit in trits[offset : offset + TRITS_PER_BYTE]:
            digit = int(trit) + 1 if balanced else int(trit)
            if digit not in (0, 1, 2):
                raise BitSpineError("trits must be -1/0/+1 in balanced mode or 0/1/2 raw")
            value = value * 3 + digit
        if value > 0xFF:
            raise BitSpineError(f"invalid byte trit cell: {value} > 255")
        out.append(value)
    return bytes(out)


def bf_to_ops(source: str) -> list[int]:
    """Project Brainfuck-class source to 3-bit opcodes.

    Non-instruction characters are comments and intentionally ignored; the
    resulting op tape is the canonical Turing-complete spine program.
    """

    return [int(BF_TO_OP[ch]) for ch in source if ch in BF_TO_OP]


def ops_to_bf(opcodes: Sequence[int]) -> str:
    return "".join(OP_TO_BF[SpineOp(int(op))] for op in opcodes)


def pack_ops(opcodes: Sequence[int]) -> bytes:
    """Pack 3-bit opcodes with a hash-checked header."""

    ops = [int(op) for op in opcodes]
    for op in ops:
        if op < 0 or op > 7:
            raise BitSpineError(f"opcode out of 3-bit range: {op}")
    bit_text = "".join(f"{op:03b}" for op in ops)
    pad = (-len(bit_text)) % 8
    bit_text += "0" * pad
    packed = bits_to_bytes(bit_text) if bit_text else b""
    body = SPINE_MAGIC + bytes([SPINE_VERSION, pad]) + struct.pack(">I", len(ops)) + packed
    return body + hashlib.sha256(body).digest()


def unpack_ops(blob: bytes) -> list[int]:
    if len(blob) < len(SPINE_MAGIC) + 6 + HASH_LEN:
        raise BitSpineError("spine program too small")
    body, digest = blob[:-HASH_LEN], blob[-HASH_LEN:]
    if hashlib.sha256(body).digest() != digest:
        raise BitSpineError("spine program hash mismatch")
    if not body.startswith(SPINE_MAGIC):
        raise BitSpineError("bad spine magic")
    version = body[4]
    if version != SPINE_VERSION:
        raise BitSpineError(f"unsupported spine version: {version}")
    pad = body[5]
    if pad > 7:
        raise BitSpineError("invalid spine padding")
    op_count = struct.unpack(">I", body[6:10])[0]
    packed = body[10:]
    bit_text = bytes_to_bits(packed)
    if pad:
        bit_text = bit_text[:-pad]
    expected_bits = op_count * 3
    if len(bit_text) != expected_bits:
        raise BitSpineError("spine opcode length mismatch")
    return [int(bit_text[i : i + 3], 2) for i in range(0, len(bit_text), 3)]


def build_loop_map(opcodes: Sequence[int]) -> dict[int, int]:
    stack: list[int] = []
    pairs: dict[int, int] = {}
    for index, op in enumerate(opcodes):
        if int(op) == SpineOp.LOOP_START:
            stack.append(index)
        elif int(op) == SpineOp.LOOP_END:
            if not stack:
                raise BitSpineError("unmatched loop end")
            start = stack.pop()
            pairs[start] = index
            pairs[index] = start
    if stack:
        raise BitSpineError("unmatched loop start")
    return pairs


def run_ops(
    opcodes: Sequence[int],
    *,
    input_bytes: bytes = b"",
    tape_size: int = 30_000,
    max_steps: int = 1_000_000,
) -> bytes:
    """Execute the finite-safe form of the 3-bit Turing-complete op tape."""

    return run_ops_receipt(
        opcodes,
        input_bytes=input_bytes,
        tape_size=tape_size,
        max_steps=max_steps,
    )["output"]


def run_ops_receipt(
    opcodes: Sequence[int],
    *,
    input_bytes: bytes = b"",
    tape_size: int = 30_000,
    max_steps: int = 1_000_000,
) -> dict:
    """Execute opcodes and return output plus finite-machine state."""

    jumps = build_loop_map(opcodes)
    tape = bytearray(tape_size)
    ptr = 0
    pc = 0
    steps = 0
    inp = iter(input_bytes)
    out = bytearray()
    ops = [int(op) for op in opcodes]
    while pc < len(ops):
        steps += 1
        if steps > max_steps:
            raise BitSpineError("spine program exceeded max_steps")
        op = SpineOp(ops[pc])
        if op == SpineOp.MOVE_RIGHT:
            ptr += 1
            if ptr >= tape_size:
                raise BitSpineError("tape pointer moved right out of bounds")
        elif op == SpineOp.MOVE_LEFT:
            if ptr == 0:
                raise BitSpineError("tape pointer moved left out of bounds")
            ptr -= 1
        elif op == SpineOp.INC:
            tape[ptr] = (tape[ptr] + 1) & 0xFF
        elif op == SpineOp.DEC:
            tape[ptr] = (tape[ptr] - 1) & 0xFF
        elif op == SpineOp.OUT:
            out.append(tape[ptr])
        elif op == SpineOp.IN:
            tape[ptr] = next(inp, 0)
        elif op == SpineOp.LOOP_START and tape[ptr] == 0:
            pc = jumps[pc]
        elif op == SpineOp.LOOP_END and tape[ptr] != 0:
            pc = jumps[pc]
        pc += 1
    output = bytes(out)
    return {
        "ptr": ptr,
        "steps": steps,
        "tape": {index: value for index, value in enumerate(tape) if value},
        "output": output,
        "output_bytes": list(output),
        "output_text": output.decode("utf-8", errors="replace"),
    }


def run_bf(source: str, **kwargs) -> bytes:
    return run_ops(bf_to_ops(source), **kwargs)


__all__ = [
    "BF_TO_OP",
    "BinaryTuringMachine",
    "BitSpine",
    "BitSpineError",
    "SpineOp",
    "bytes_to_bits",
    "bits_to_bytes",
    "bytes_to_trits",
    "trits_to_bytes",
    "hex_to_bytes",
    "binary_increment_machine",
    "tape_to_bits",
    "RelationshipMachine",
    "RelationshipStep",
    "parse_relationship_program",
    "run_relationship_program",
    "bf_to_ops",
    "ops_to_bf",
    "pack_ops",
    "unpack_ops",
    "run_ops",
    "run_ops_receipt",
    "run_bf",
]
