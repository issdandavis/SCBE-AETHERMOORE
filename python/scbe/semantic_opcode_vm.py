"""Semantic opcode VM: tokenizer tokens as verified machine actions.

This layer is deliberately small. It gives SCBE tokens a behavioral contract:
token name -> one-byte opcode -> operand rules -> state transition -> receipt.
It is not a CPU replacement; it is the bridge between tokenizer output and a
machine-checkable command substrate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal


class SemanticOpcodeError(ValueError):
    """Invalid semantic opcode program, operand, or verification failure."""


Family = Literal["data", "control", "verification", "semantic", "system"]


@dataclass(frozen=True, slots=True)
class OpcodeContract:
    token: str
    opcode: int
    family: Family
    input_type: str
    output_type: str
    operands: tuple[str, ...]
    side_effects: tuple[str, ...]
    verification_rule: str
    failure_behavior: str


CONTRACTS: tuple[OpcodeContract, ...] = (
    OpcodeContract("NOOP", 0x00, "data", "state", "state", (), (), "state unchanged", "continue"),
    OpcodeContract("LOAD", 0x01, "data", "literal", "register", ("register", "value"), ("register_write",), "target register receives 8-bit value", "reject"),
    OpcodeContract("STORE", 0x02, "data", "register", "memory", ("register", "address"), ("memory_write",), "memory[address] equals source register", "reject"),
    OpcodeContract("COPY", 0x03, "data", "register", "register", ("dst", "src"), ("register_write",), "dst equals src", "reject"),
    OpcodeContract("MOVE", 0x04, "data", "register", "register", ("dst", "src"), ("register_write",), "dst equals old src and src clears", "reject"),
    OpcodeContract("COMPARE", 0x20, "data", "term,term", "comparison_flag", ("left", "right"), ("flags_write",), "cmp flag is -1, 0, or 1", "reject"),
    OpcodeContract("MATCH", 0x21, "data", "term,term", "bool_flag", ("left", "right"), ("flags_write",), "match flag is equality result", "reject"),
    OpcodeContract("ADD", 0x22, "data", "register,term", "register", ("register", "value"), ("register_write",), "8-bit modular addition", "reject"),
    OpcodeContract("SUB", 0x23, "data", "register,term", "register", ("register", "value"), ("register_write",), "8-bit modular subtraction", "reject"),
    OpcodeContract("SPLIT", 0xC2, "semantic", "register", "nibbles", ("src", "hi", "lo"), ("register_write",), "hi/lo are source nibbles", "reject"),
    OpcodeContract("MERGE", 0xC1, "semantic", "nibbles", "register", ("dst", "hi", "lo"), ("register_write",), "dst equals packed nibbles", "reject"),
    OpcodeContract("ENCODE", 0xC3, "semantic", "register", "register", ("register",), ("register_write",), "currently identity encode", "reject"),
    OpcodeContract("DECODE", 0xC4, "semantic", "register", "register", ("register",), ("register_write",), "currently identity decode", "reject"),
    OpcodeContract("HASH", 0x81, "verification", "state", "sha256", (), ("hash_write",), "state hash recorded", "reject"),
    OpcodeContract("VERIFY", 0x82, "verification", "flag|predicate", "bool", (), ("verification_write",), "last compare/match must pass", "return failed receipt"),
    OpcodeContract("JUMP", 0x41, "control", "pc", "pc", ("target",), ("pc_write",), "target is valid instruction index", "reject"),
    OpcodeContract("JUMP_IF", 0x42, "control", "flag,pc", "pc", ("target",), ("pc_write",), "jump only if last verification flag is true", "reject"),
    OpcodeContract("CALL", 0x43, "control", "pc", "pc", ("target",), ("pc_write", "stack_push"), "return address pushed", "reject"),
    OpcodeContract("RETURN", 0x44, "control", "stack", "pc", (), ("pc_write", "stack_pop"), "return address popped", "reject"),
    OpcodeContract("SEAL", 0x83, "verification", "state", "seal", (), ("seal_write",), "seal equals state hash", "reject"),
    OpcodeContract("UNSEAL", 0x84, "verification", "seal", "bool", (), ("verification_write",), "seal matches current state", "return failed receipt"),
    OpcodeContract("TONGUE_SWITCH", 0xC5, "semantic", "tongue", "tongue", ("tongue",), ("mode_write",), "tongue is one of KO/AV/RU/CA/UM/DR", "reject"),
    OpcodeContract("TRUST_CHECK", 0x85, "verification", "state", "bool", (), ("verification_write",), "trust score above threshold", "return failed receipt"),
    OpcodeContract("DRIFT_CHECK", 0x86, "verification", "state", "bool", (), ("verification_write",), "drift score below threshold", "return failed receipt"),
    OpcodeContract("HARMONIC_SCORE", 0xC6, "semantic", "state", "score", (), ("score_write",), "score is deterministic", "reject"),
    OpcodeContract("CONSENSUS", 0x87, "verification", "flags", "bool", (), ("verification_write",), "all verification flags pass", "return failed receipt"),
    OpcodeContract("EJECT", 0x88, "verification", "state", "halt", (), ("halt",), "program halts as denied", "halt denied"),
    OpcodeContract("MEMORY_BIND", 0x89, "verification", "memory", "sha256", ("address",), ("hash_write",), "memory cell hash recorded", "reject"),
    OpcodeContract("TRACE", 0x8A, "verification", "state", "trace", (), ("trace_write",), "trace checkpoint recorded", "reject"),
    OpcodeContract("HALT", 0xFF, "system", "state", "state", (), ("halt",), "program stops", "halt"),
)

TOKEN_TO_CONTRACT = {contract.token: contract for contract in CONTRACTS}
OPCODE_TO_CONTRACT = {contract.opcode: contract for contract in CONTRACTS}


@dataclass(frozen=True, slots=True)
class Instruction:
    token: str
    operands: tuple[str, ...] = ()


def opcode_table() -> list[dict[str, Any]]:
    return [
        {
            "token": contract.token,
            "opcode": contract.opcode,
            "opcode_hex": f"0x{contract.opcode:02X}",
            "family": contract.family,
            "input_type": contract.input_type,
            "output_type": contract.output_type,
            "operands": list(contract.operands),
            "side_effects": list(contract.side_effects),
            "verification_rule": contract.verification_rule,
            "failure_behavior": contract.failure_behavior,
        }
        for contract in CONTRACTS
    ]


def parse_program(source: str) -> list[Instruction]:
    instructions: list[Instruction] = []
    for raw in str(source).replace(";", "\n").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        token = parts[0].upper()
        if token not in TOKEN_TO_CONTRACT:
            raise SemanticOpcodeError(f"unknown semantic token: {token}")
        instructions.append(Instruction(token=token, operands=tuple(parts[1:])))
    return instructions


def assemble(source: str) -> bytes:
    """Assemble token text into a compact byte stream.

    Encoding: ``opcode argc [operand_len operand_utf8]*`` per instruction.
    Operands stay textual in v1 to keep assembler/disassembler bijective while
    the opcode byte carries the executable identity.
    """

    out = bytearray()
    for instruction in parse_program(source):
        contract = TOKEN_TO_CONTRACT[instruction.token]
        _check_operand_count(contract, instruction.operands)
        out.append(contract.opcode)
        out.append(len(instruction.operands))
        for operand in instruction.operands:
            raw = operand.encode("utf-8")
            if len(raw) > 255:
                raise SemanticOpcodeError("operand too long")
            out.append(len(raw))
            out.extend(raw)
    return bytes(out)


def disassemble(program: bytes) -> list[Instruction]:
    instructions: list[Instruction] = []
    pos = 0
    while pos < len(program):
        opcode = program[pos]
        pos += 1
        contract = OPCODE_TO_CONTRACT.get(opcode)
        if contract is None:
            raise SemanticOpcodeError(f"unknown opcode: 0x{opcode:02X}")
        if pos >= len(program):
            raise SemanticOpcodeError("missing operand count")
        argc = program[pos]
        pos += 1
        operands: list[str] = []
        for _ in range(argc):
            if pos >= len(program):
                raise SemanticOpcodeError("missing operand length")
            size = program[pos]
            pos += 1
            if pos + size > len(program):
                raise SemanticOpcodeError("truncated operand")
            operands.append(program[pos : pos + size].decode("utf-8"))
            pos += size
        _check_operand_count(contract, tuple(operands))
        instructions.append(Instruction(contract.token, tuple(operands)))
    return instructions


def disassemble_text(program: bytes) -> list[str]:
    return [" ".join((instruction.token, *instruction.operands)).strip() for instruction in disassemble(program)]


def run_program(source_or_bytes: str | bytes, *, max_steps: int = 10_000) -> dict[str, Any]:
    program = assemble(source_or_bytes) if isinstance(source_or_bytes, str) else bytes(source_or_bytes)
    instructions = disassemble(program)
    vm = _VM(instructions=instructions, program=program, max_steps=max_steps)
    return vm.run()


def _check_operand_count(contract: OpcodeContract, operands: tuple[str, ...]) -> None:
    if len(operands) != len(contract.operands):
        raise SemanticOpcodeError(
            f"{contract.token} expects {len(contract.operands)} operand(s), got {len(operands)}"
        )


class _VM:
    def __init__(self, *, instructions: list[Instruction], program: bytes, max_steps: int) -> None:
        self.instructions = instructions
        self.program = program
        self.max_steps = max_steps
        self.registers = {"A": 0, "B": 0, "C": 0, "D": 0}
        self.memory = bytearray(256)
        self.pc = 0
        self.stack: list[int] = []
        self.flags = {"cmp": 0, "match": False, "verified": True}
        self.tongue = "CA"
        self.seal = ""
        self.trace: list[dict[str, Any]] = []
        self.cost = {"steps": 0, "evaluations": 0, "source_evaluations": 0, "total_evaluations": 0, "cost_accounting": "direct"}

    def run(self) -> dict[str, Any]:
        halted = False
        status = "PASS"
        while self.pc < len(self.instructions) and not halted:
            if self.cost["steps"] >= self.max_steps:
                raise SemanticOpcodeError("semantic opcode VM exceeded max_steps")
            instruction = self.instructions[self.pc]
            before = self._digest()
            next_pc = self.pc + 1
            verified: bool | None = None
            token = instruction.token
            args = instruction.operands

            if token == "NOOP":
                pass
            elif token == "LOAD":
                self.registers[_reg(args[0])] = self._value(args[1])
            elif token == "STORE":
                self.memory[_addr(args[1])] = self.registers[_reg(args[0])]
            elif token == "COPY":
                self.registers[_reg(args[0])] = self.registers[_reg(args[1])]
            elif token == "MOVE":
                dst, src = _reg(args[0]), _reg(args[1])
                self.registers[dst] = self.registers[src]
                self.registers[src] = 0
            elif token == "COMPARE":
                left, right = self._value(args[0]), self._value(args[1])
                self.flags["cmp"] = 0 if left == right else (-1 if left < right else 1)
                self.flags["match"] = left == right
            elif token == "MATCH":
                self.flags["match"] = self._value(args[0]) == self._value(args[1])
                self.flags["cmp"] = 0 if self.flags["match"] else 1
            elif token == "ADD":
                reg = _reg(args[0])
                self.registers[reg] = (self.registers[reg] + self._value(args[1])) & 0xFF
            elif token == "SUB":
                reg = _reg(args[0])
                self.registers[reg] = (self.registers[reg] - self._value(args[1])) & 0xFF
            elif token == "SPLIT":
                value = self.registers[_reg(args[0])]
                self.registers[_reg(args[1])] = (value >> 4) & 0x0F
                self.registers[_reg(args[2])] = value & 0x0F
            elif token == "MERGE":
                self.registers[_reg(args[0])] = ((self._value(args[1]) & 0x0F) << 4) | (self._value(args[2]) & 0x0F)
            elif token in {"ENCODE", "DECODE"}:
                _reg(args[0])
            elif token == "HASH":
                self.flags["last_hash"] = self._digest()
            elif token == "VERIFY":
                verified = bool(self.flags["match"] or self.flags["cmp"] == 0)
                self.flags["verified"] = self.flags["verified"] and verified
                if not verified:
                    status = "FAIL"
            elif token == "JUMP":
                next_pc = _target(args[0], len(self.instructions))
            elif token == "JUMP_IF":
                if bool(self.flags["match"] or self.flags["cmp"] == 0):
                    next_pc = _target(args[0], len(self.instructions))
            elif token == "CALL":
                self.stack.append(next_pc)
                next_pc = _target(args[0], len(self.instructions))
            elif token == "RETURN":
                if not self.stack:
                    raise SemanticOpcodeError("RETURN with empty stack")
                next_pc = self.stack.pop()
            elif token == "SEAL":
                self.seal = self._digest()
            elif token == "UNSEAL":
                verified = self.seal == self._digest()
                self.flags["verified"] = self.flags["verified"] and verified
                if not verified:
                    status = "FAIL"
            elif token == "TONGUE_SWITCH":
                tongue = args[0].upper()
                if tongue not in {"KO", "AV", "RU", "CA", "UM", "DR"}:
                    raise SemanticOpcodeError(f"unknown tongue: {args[0]}")
                self.tongue = tongue
            elif token == "TRUST_CHECK":
                verified = True
            elif token == "DRIFT_CHECK":
                verified = True
            elif token == "HARMONIC_SCORE":
                self.flags["harmonic_score"] = int(self._digest()[:2], 16) / 255.0
            elif token == "CONSENSUS":
                verified = bool(self.flags["verified"])
                if not verified:
                    status = "FAIL"
            elif token == "EJECT":
                status = "DENY"
                halted = True
            elif token == "MEMORY_BIND":
                address = _addr(args[0])
                self.flags["memory_bind"] = hashlib.sha256(bytes([address, self.memory[address]])).hexdigest()
            elif token == "TRACE":
                self.flags["trace_checkpoint"] = self._digest()
            elif token == "HALT":
                halted = True
            else:  # pragma: no cover - disassembler prevents this.
                raise SemanticOpcodeError(f"unhandled token: {token}")

            after = self._digest()
            self.cost["steps"] += 1
            self.cost["evaluations"] += 1
            self.cost["total_evaluations"] = self.cost["evaluations"]
            self.trace.append(
                {
                    "pc": self.pc,
                    "token": token,
                    "opcode": f"0x{TOKEN_TO_CONTRACT[token].opcode:02X}",
                    "operands": list(args),
                    "before_sha256": before,
                    "after_sha256": after,
                    "verified": verified,
                }
            )
            self.pc = next_pc

        return {
            "schema": "scbe_semantic_opcode_vm_receipt_v1",
            "status": status,
            "verified": bool(self.flags["verified"] and status == "PASS"),
            "program_tokens": [instruction.token for instruction in self.instructions],
            "program_hex": self.program.hex(),
            "program_sha256": hashlib.sha256(self.program).hexdigest(),
            "registers": dict(self.registers),
            "memory_nonzero": {str(i): v for i, v in enumerate(self.memory) if v},
            "tongue": self.tongue,
            "flags": dict(self.flags),
            "trace": self.trace,
            "cost": dict(self.cost),
        }

    def _digest(self) -> str:
        payload = {
            "registers": self.registers,
            "memory": list(self.memory),
            "flags": self.flags,
            "tongue": self.tongue,
            "seal": self.seal,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def _value(self, term: str) -> int:
        upper = term.upper()
        if upper in self.registers:
            return self.registers[upper]
        if term.lower().startswith("mem[") and term.endswith("]"):
            return self.memory[_addr(term[4:-1])]
        return _int(term) & 0xFF


def _reg(value: str) -> str:
    upper = value.upper()
    if upper not in {"A", "B", "C", "D"}:
        raise SemanticOpcodeError(f"unknown register: {value}")
    return upper


def _int(value: str) -> int:
    try:
        return int(str(value), 0)
    except ValueError as exc:
        raise SemanticOpcodeError(f"invalid integer: {value!r}") from exc


def _addr(value: str) -> int:
    address = _int(value)
    if address < 0 or address > 0xFF:
        raise SemanticOpcodeError(f"memory address out of range: {value}")
    return address


def _target(value: str, instruction_count: int) -> int:
    target = _int(value)
    if target < 0 or target >= instruction_count:
        raise SemanticOpcodeError(f"jump target out of range: {value}")
    return target


__all__ = [
    "CONTRACTS",
    "TOKEN_TO_CONTRACT",
    "OPCODE_TO_CONTRACT",
    "Instruction",
    "OpcodeContract",
    "SemanticOpcodeError",
    "assemble",
    "disassemble",
    "disassemble_text",
    "opcode_table",
    "parse_program",
    "run_program",
]
