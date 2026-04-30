"""Small compatibility VM for turning-lane fixed-width byte programs.

The full STVM toolchain was extracted to its own repository, but the
turning-lane tests still need a deterministic in-repo executor for the tiny
program family used as transport witnesses.
"""

from __future__ import annotations

from typing import Sequence


class SacredTongueVM:
    """Execute the four-byte instruction subset used by turning_lane."""

    def __init__(self, program: Sequence[int]):
        if len(program) % 4 != 0:
            raise ValueError("turning-lane VM program length must be divisible by 4")
        self.program = [int(byte) & 0xFF for byte in program]
        self.registers = [0] * 256
        self.pc = 0
        self.output: list[int] = []
        self.halted = False

    def run(self, max_steps: int = 10000) -> list[int]:
        steps = 0
        instruction_count = len(self.program) // 4
        while not self.halted:
            if steps >= max_steps:
                raise RuntimeError("turning-lane VM step limit exceeded")
            if self.pc < 0 or self.pc >= instruction_count:
                raise RuntimeError(f"turning-lane VM pc out of bounds: {self.pc}")
            steps += 1
            offset = self.pc * 4
            opcode, a, b, c = self.program[offset : offset + 4]
            self._exec(opcode, a, b, c)
        return list(self.output)

    def _exec(self, opcode: int, a: int, b: int, c: int) -> None:
        if opcode == 0x01:  # halt
            self.halted = True
            return
        if opcode == 0x03:  # jz reg, target
            self.pc = b if self.registers[a] == 0 else self.pc + 1
            return
        if opcode == 0x04:  # jnz reg, target
            self.pc = b if self.registers[a] != 0 else self.pc + 1
            return
        if opcode == 0x05:  # set reg, imm
            self.registers[a] = b
            self.pc += 1
            return
        if opcode == 0x06:  # mov dst, src
            self.registers[a] = self.registers[b]
            self.pc += 1
            return
        if opcode == 0x07:  # print reg
            value = int(self.registers[a])
            self.output.append(value)
            print(value)
            self.pc += 1
            return
        if opcode == 0x10:  # add dst, lhs, rhs
            self.registers[a] = self.registers[b] + self.registers[c]
            self.pc += 1
            return
        if opcode == 0x11:  # sub dst, lhs, rhs
            self.registers[a] = self.registers[b] - self.registers[c]
            self.pc += 1
            return
        if opcode == 0x17:  # cmp_eq dst, lhs, rhs
            self.registers[a] = 1 if self.registers[b] == self.registers[c] else 0
            self.pc += 1
            return
        raise RuntimeError(f"turning-lane VM unknown opcode 0x{opcode:02x}")
