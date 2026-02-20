#!/usr/bin/env python3
"""
Sacred Tongue VM core primitives.

Phase-1 scope:
- Fixed-width instruction encoding (8 bytes)
- Small bootstrap ISA subset across 6 tongues
- Deterministic VM execution
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import importlib.util
import struct


MAGIC = b"STV1"
INSTR_SIZE = 8
HEADER_SIZE = 8

TONGUE_TO_ID: Dict[str, int] = {"ko": 0, "ca": 1, "ru": 2, "av": 3, "dr": 4, "um": 5}
ID_TO_TONGUE: Dict[int, str] = {v: k for k, v in TONGUE_TO_ID.items()}


@dataclass(frozen=True)
class Instr:
    tongue_id: int
    opcode: int
    a: int = 0
    b: int = 0
    imm: int = 0


@dataclass(frozen=True)
class InstrSpec:
    key: str
    tongue: str
    opcode: int
    signature: str


ISA_SPECS: Dict[str, InstrSpec] = {
    # KO (control flow)
    "KO.NOP": InstrSpec("KO.NOP", "ko", 0x00, ""),
    "KO.HALT": InstrSpec("KO.HALT", "ko", 0x01, ""),
    "KO.JMP": InstrSpec("KO.JMP", "ko", 0x02, "target"),
    "KO.JZ": InstrSpec("KO.JZ", "ko", 0x03, "reg target"),
    "KO.JNZ": InstrSpec("KO.JNZ", "ko", 0x04, "reg target"),
    "KO.CALL": InstrSpec("KO.CALL", "ko", 0x05, "target"),
    "KO.RET": InstrSpec("KO.RET", "ko", 0x06, ""),
    "KO.YIELD": InstrSpec("KO.YIELD", "ko", 0x07, ""),
    # CA (arithmetic / logic)
    "CA.MOVI": InstrSpec("CA.MOVI", "ca", 0x10, "reg imm"),
    "CA.MOV": InstrSpec("CA.MOV", "ca", 0x11, "dst src"),
    "CA.ADD": InstrSpec("CA.ADD", "ca", 0x12, "dst src"),
    "CA.SUB": InstrSpec("CA.SUB", "ca", 0x13, "dst src"),
    "CA.MUL": InstrSpec("CA.MUL", "ca", 0x14, "dst src"),
    "CA.DIV": InstrSpec("CA.DIV", "ca", 0x15, "dst src"),
    "CA.MOD": InstrSpec("CA.MOD", "ca", 0x16, "dst src"),
    "CA.CMP": InstrSpec("CA.CMP", "ca", 0x17, "lhs rhs"),
    "CA.AND": InstrSpec("CA.AND", "ca", 0x18, "dst src"),
    "CA.OR": InstrSpec("CA.OR", "ca", 0x19, "dst src"),
    "CA.XOR": InstrSpec("CA.XOR", "ca", 0x1A, "dst src"),
    # RU (memory)
    "RU.LOAD": InstrSpec("RU.LOAD", "ru", 0x20, "reg addr"),
    "RU.STORE": InstrSpec("RU.STORE", "ru", 0x21, "reg addr"),
    # AV (syscalls/ipc)
    "AV.SEND": InstrSpec("AV.SEND", "av", 0x30, "reg channel"),
    "AV.RECV": InstrSpec("AV.RECV", "av", 0x31, "reg channel"),
    "AV.SYSCALL": InstrSpec("AV.SYSCALL", "av", 0x32, "id"),
    # DR (validation)
    "DR.ASSERT": InstrSpec("DR.ASSERT", "dr", 0x40, "reg"),
    "DR.VERIFY": InstrSpec("DR.VERIFY", "dr", 0x41, "reg"),
    # UM (security ops)
    "UM.HASH": InstrSpec("UM.HASH", "um", 0x50, "reg"),
    "UM.REDACT": InstrSpec("UM.REDACT", "um", 0x51, "reg"),
}

OP_TO_SPEC: Dict[Tuple[str, int], InstrSpec] = {(v.tongue, v.opcode): v for v in ISA_SPECS.values()}


def encode_instr(instr: Instr) -> bytes:
    return struct.pack("<BBBBi", instr.tongue_id, instr.opcode, instr.a, instr.b, int(instr.imm))


def decode_instr(data: bytes) -> Instr:
    tid, op, a, b, imm = struct.unpack("<BBBBi", data)
    return Instr(tid, op, a, b, imm)


def build_bytecode(instructions: List[Instr]) -> bytes:
    payload = b"".join(encode_instr(i) for i in instructions)
    return MAGIC + struct.pack("<I", len(instructions)) + payload


def parse_bytecode(blob: bytes) -> List[Instr]:
    if len(blob) < HEADER_SIZE:
        raise ValueError("bytecode too small")
    if blob[:4] != MAGIC:
        raise ValueError("invalid magic header")
    n = struct.unpack("<I", blob[4:8])[0]
    expected = HEADER_SIZE + n * INSTR_SIZE
    if len(blob) != expected:
        raise ValueError(f"invalid bytecode length: got {len(blob)}, expected {expected}")
    out: List[Instr] = []
    off = HEADER_SIZE
    for _ in range(n):
        out.append(decode_instr(blob[off : off + INSTR_SIZE]))
        off += INSTR_SIZE
    return out


def parse_reg(token: str) -> int:
    t = token.strip().lower()
    if not t.startswith("r"):
        raise ValueError(f"expected register token, got '{token}'")
    idx = int(t[1:])
    if idx < 0 or idx >= 21:
        raise ValueError(f"register out of range: r{idx} (expected r0..r20)")
    return idx


def parse_int(token: str) -> int:
    t = token.strip().lower()
    if t.startswith("0x"):
        return int(t, 16)
    return int(t, 10)


def _load_sixtongues_module():
    repo_root = Path(__file__).resolve().parents[1]
    mod_path = repo_root / "packages" / "sixtongues" / "sixtongues.py"
    if not mod_path.exists():
        raise FileNotFoundError(f"missing sixtongues module: {mod_path}")
    spec = importlib.util.spec_from_file_location("sixtongues_local", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load sixtongues module spec")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def token_to_opcode_byte(tongue_code: str, token: str) -> int:
    mod = _load_sixtongues_module()
    tongue = mod.TONGUES[tongue_code]
    return int(mod.token_to_byte(token, tongue))


def opcode_byte_to_token(tongue_code: str, opcode: int) -> str:
    mod = _load_sixtongues_module()
    tongue = mod.TONGUES[tongue_code]
    return str(mod.byte_to_token(int(opcode) & 0xFF, tongue))


def resolve_label_or_int(token: str, labels: Dict[str, int]) -> int:
    t = token.strip()
    if t in labels:
        return labels[t]
    return parse_int(t)


def fnv1a64(value: int) -> int:
    """Deterministic 64-bit hash for UM.HASH."""
    v = int(value) & 0xFFFFFFFFFFFFFFFF
    data = v.to_bytes(8, "little", signed=False)
    h = 0xCBF29CE484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


class STVM:
    def __init__(self, memory_words: int = 1024):
        self.regs = [0] * 21
        self.mem = [0] * int(memory_words)
        self.pc = 0
        self.call_stack: List[int] = []
        self.zero_flag = False
        self.running = True
        self.last_error: Optional[str] = None
        self.events: List[str] = []
        self.channel_mailbox: Dict[int, int] = {}

    def _trap(self, reason: str) -> None:
        self.last_error = reason
        self.running = False

    def _bounds_pc(self, n: int) -> bool:
        return 0 <= self.pc < n

    def run(self, program: List[Instr], max_steps: int = 10000) -> None:
        steps = 0
        while self.running:
            if not self._bounds_pc(len(program)):
                self._trap(f"pc out of bounds: {self.pc}")
                break
            if steps >= max_steps:
                self._trap("step limit exceeded")
                break
            steps += 1
            ins = program[self.pc]
            self._exec(ins)

    def _exec(self, ins: Instr) -> None:
        tongue = ID_TO_TONGUE.get(ins.tongue_id, "??")
        op = ins.opcode

        if tongue == "ko":
            if op == 0x00:  # NOP
                self.pc += 1
            elif op == 0x01:  # HALT
                self.running = False
            elif op == 0x02:  # JMP
                self.pc = ins.imm
            elif op == 0x03:  # JZ
                self.pc = ins.imm if self.regs[ins.a] == 0 else self.pc + 1
            elif op == 0x04:  # JNZ
                self.pc = ins.imm if self.regs[ins.a] != 0 else self.pc + 1
            elif op == 0x05:  # CALL
                self.call_stack.append(self.pc + 1)
                self.pc = ins.imm
            elif op == 0x06:  # RET
                if not self.call_stack:
                    self.running = False
                else:
                    self.pc = self.call_stack.pop()
            elif op == 0x07:  # YIELD
                self.events.append(f"yield@{self.pc}")
                self.pc += 1
            else:
                self._trap(f"unknown KO opcode 0x{op:02x}")
            return

        if tongue == "ca":
            a, b = ins.a, ins.b
            if op == 0x10:  # MOVI
                self.regs[a] = int(ins.imm)
            elif op == 0x11:  # MOV
                self.regs[a] = int(self.regs[b])
            elif op == 0x12:  # ADD
                self.regs[a] = int(self.regs[a]) + int(self.regs[b])
            elif op == 0x13:  # SUB
                self.regs[a] = int(self.regs[a]) - int(self.regs[b])
            elif op == 0x14:  # MUL
                self.regs[a] = int(self.regs[a]) * int(self.regs[b])
            elif op == 0x15:  # DIV
                if self.regs[b] == 0:
                    self._trap("division by zero")
                    return
                self.regs[a] = int(self.regs[a]) // int(self.regs[b])
            elif op == 0x16:  # MOD
                if self.regs[b] == 0:
                    self._trap("modulo by zero")
                    return
                self.regs[a] = int(self.regs[a]) % int(self.regs[b])
            elif op == 0x17:  # CMP
                self.zero_flag = bool(self.regs[a] == self.regs[b])
            elif op == 0x18:  # AND
                self.regs[a] = int(self.regs[a]) & int(self.regs[b])
            elif op == 0x19:  # OR
                self.regs[a] = int(self.regs[a]) | int(self.regs[b])
            elif op == 0x1A:  # XOR
                self.regs[a] = int(self.regs[a]) ^ int(self.regs[b])
            else:
                self._trap(f"unknown CA opcode 0x{op:02x}")
                return
            self.pc += 1
            return

        if tongue == "ru":
            addr = int(ins.imm) % len(self.mem)
            if op == 0x20:  # LOAD
                self.regs[ins.a] = int(self.mem[addr])
            elif op == 0x21:  # STORE
                self.mem[addr] = int(self.regs[ins.a])
            else:
                self._trap(f"unknown RU opcode 0x{op:02x}")
                return
            self.pc += 1
            return

        if tongue == "av":
            channel = int(ins.imm)
            if op == 0x30:  # SEND
                val = int(self.regs[ins.a])
                self.channel_mailbox[channel] = val
                self.events.append(f"send ch={channel} value={val}")
            elif op == 0x31:  # RECV
                self.regs[ins.a] = int(self.channel_mailbox.get(channel, 0))
                self.events.append(f"recv ch={channel} value={self.regs[ins.a]}")
            elif op == 0x32:  # SYSCALL
                self.events.append(f"syscall id={channel}")
            else:
                self._trap(f"unknown AV opcode 0x{op:02x}")
                return
            self.pc += 1
            return

        if tongue == "dr":
            if op == 0x40:  # ASSERT
                if int(self.regs[ins.a]) == 0:
                    self._trap(f"assert failed r{ins.a} == 0")
                    return
            elif op == 0x41:  # VERIFY
                self.events.append(f"verify r{ins.a}={self.regs[ins.a]}")
            else:
                self._trap(f"unknown DR opcode 0x{op:02x}")
                return
            self.pc += 1
            return

        if tongue == "um":
            if op == 0x50:  # HASH
                self.regs[ins.a] = fnv1a64(int(self.regs[ins.a]))
            elif op == 0x51:  # REDACT
                self.regs[ins.a] = 0
            else:
                self._trap(f"unknown UM opcode 0x{op:02x}")
                return
            self.pc += 1
            return

        self._trap(f"unknown tongue id={ins.tongue_id}")

