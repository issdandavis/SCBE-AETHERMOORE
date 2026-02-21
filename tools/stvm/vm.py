from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List


class VMError(Exception):
    pass


class SacredTongueVM:
    def __init__(self, program: List[int]):
        if len(program) % 4 != 0:
            raise VMError("program length must be a multiple of 4 bytes")
        self.program = program
        self.reg = [0] * 16
        self.pc = 0
        self.halted = False
        self.output: List[int] = []

    @property
    def instruction_count(self) -> int:
        return len(self.program) // 4

    def fetch(self) -> tuple[int, int, int, int]:
        if not (0 <= self.pc < self.instruction_count):
            self.halted = True
            return (0x01, 0, 0, 0)
        i = self.pc * 4
        return self.program[i], self.program[i + 1], self.program[i + 2], self.program[i + 3]

    def step(self) -> None:
        if self.halted:
            return

        op, a, b, c = self.fetch()
        next_pc = self.pc + 1

        if op == 0x00:  # nop
            pass
        elif op == 0x01:  # halt
            self.halted = True
        elif op == 0x02:  # jmp target
            next_pc = a
        elif op == 0x03:  # jz reg,target
            if self.reg[a] == 0:
                next_pc = b
        elif op == 0x04:  # jnz reg,target
            if self.reg[a] != 0:
                next_pc = b
        elif op == 0x05:  # set reg,imm
            self.reg[a] = b & 0xFF
        elif op == 0x06:  # mov dst,src
            self.reg[a] = self.reg[b] & 0xFF
        elif op == 0x07:  # print reg
            value = self.reg[a] & 0xFF
            self.output.append(value)
            print(value)
        elif op == 0x10:  # add
            self.reg[a] = (self.reg[b] + self.reg[c]) & 0xFF
        elif op == 0x11:  # sub
            self.reg[a] = (self.reg[b] - self.reg[c]) & 0xFF
        elif op == 0x12:  # mul
            self.reg[a] = (self.reg[b] * self.reg[c]) & 0xFF
        elif op == 0x13:  # div
            if self.reg[c] == 0:
                raise VMError(f"division by zero at pc={self.pc}")
            self.reg[a] = (self.reg[b] // self.reg[c]) & 0xFF
        elif op == 0x14:  # xor
            self.reg[a] = (self.reg[b] ^ self.reg[c]) & 0xFF
        elif op == 0x15:  # and
            self.reg[a] = (self.reg[b] & self.reg[c]) & 0xFF
        elif op == 0x16:  # or
            self.reg[a] = (self.reg[b] | self.reg[c]) & 0xFF
        elif op == 0x17:  # cmp_eq
            self.reg[a] = 1 if self.reg[b] == self.reg[c] else 0
        else:
            raise VMError(f"unknown opcode 0x{op:02x} at pc={self.pc}")

        self.pc = next_pc

    def run(self, max_steps: int = 10000) -> List[int]:
        steps = 0
        while not self.halted and steps < max_steps:
            self.step()
            steps += 1

        if steps >= max_steps:
            raise VMError(f"execution exceeded max_steps={max_steps}")

        return self.output


def load_program(path: Path) -> List[int]:
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return [int(v) & 0xFF for v in data]
    return list(path.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Sacred Tongue VM (stvm)")
    parser.add_argument("program", type=Path, help="Bytecode file (.bin or .json)")
    parser.add_argument("--max-steps", type=int, default=10000)
    args = parser.parse_args()

    vm = SacredTongueVM(load_program(args.program))
    vm.run(max_steps=args.max_steps)


if __name__ == "__main__":
    main()
