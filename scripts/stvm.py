#!/usr/bin/env python3
"""
stvm: Sacred Tongue VM runner and disassembler (Phase-1).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from stvm_core import (
    ID_TO_TONGUE,
    OP_TO_SPEC,
    STVM,
    opcode_byte_to_token,
    parse_bytecode,
)


def disassemble(path: Path) -> None:
    blob = path.read_bytes()
    program = parse_bytecode(blob)
    print(f"{path} -> {len(program)} instructions")
    for pc, ins in enumerate(program):
        tongue = ID_TO_TONGUE.get(ins.tongue_id, f"id{ins.tongue_id}")
        spec = OP_TO_SPEC.get((tongue, ins.opcode))
        token = opcode_byte_to_token(tongue, ins.opcode) if tongue in ("ko", "ca", "ru", "av", "dr", "um") else "?"
        if spec:
            line = f"{spec.key:<10} a={ins.a:<2} b={ins.b:<2} imm={ins.imm:<6}"
        else:
            line = f"{tongue.upper()}.OP_0x{ins.opcode:02X} a={ins.a:<2} b={ins.b:<2} imm={ins.imm:<6}"
        print(f"{pc:04d}: {line} ; {tongue}:{token}")


def run(path: Path, max_steps: int, dump_mem: bool) -> int:
    blob = path.read_bytes()
    program = parse_bytecode(blob)
    vm = STVM()
    vm.run(program, max_steps=max_steps)

    print(f"Program: {path}")
    print(f"Steps complete. running={vm.running} pc={vm.pc} error={vm.last_error}")
    print("Registers (r0..r20):")
    for i in range(0, 21, 7):
        seg = " ".join(f"r{j}={vm.regs[j]}" for j in range(i, min(i + 7, 21)))
        print(f"  {seg}")

    if vm.events:
        print("Events:")
        for e in vm.events:
            print(f"  - {e}")

    if dump_mem:
        print("Memory snapshot [0..31]:")
        print("  " + " ".join(str(x) for x in vm.mem[:32]))

    return 0 if vm.last_error is None else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="stvm - Sacred Tongue VM")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_dis = sub.add_parser("dis", help="Disassemble bytecode")
    p_dis.add_argument("bytecode", help="STV1 file path")

    p_run = sub.add_parser("run", help="Run bytecode")
    p_run.add_argument("bytecode", help="STV1 file path")
    p_run.add_argument("--max-steps", type=int, default=10000, help="Step limit")
    p_run.add_argument("--dump-mem", action="store_true", help="Print memory [0..31]")

    args = ap.parse_args()
    path = Path(args.bytecode)

    if args.cmd == "dis":
        disassemble(path)
        return 0
    if args.cmd == "run":
        return run(path, max_steps=args.max_steps, dump_mem=args.dump_mem)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

