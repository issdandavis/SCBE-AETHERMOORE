#!/usr/bin/env python3
"""
stasm: Sacred Tongue assembler (Phase-1).

Input: text assembly
Output: STV1 bytecode
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

from stvm_core import (
    ID_TO_TONGUE,
    ISA_SPECS,
    Instr,
    OP_TO_SPEC,
    TONGUE_TO_ID,
    build_bytecode,
    opcode_byte_to_token,
    parse_int,
    parse_reg,
    resolve_label_or_int,
    token_to_opcode_byte,
)


def strip_comment(line: str) -> str:
    for marker in (";", "#"):
        i = line.find(marker)
        if i >= 0:
            line = line[:i]
    return line.strip()


def normalize_tokens(line: str) -> List[str]:
    line = line.replace(",", " ")
    return [x for x in line.split() if x]


def parse_opcode_token(tok: str) -> Tuple[str, int]:
    up = tok.upper()
    if up in ISA_SPECS:
        spec = ISA_SPECS[up]
        return spec.tongue, spec.opcode

    # Sacred token form: ko:kor'ae
    if ":" in tok:
        tcode, token = tok.split(":", 1)
        tcode = tcode.strip().lower()
        if tcode not in TONGUE_TO_ID:
            raise ValueError(f"unknown tongue code in token opcode: {tcode}")
        op = token_to_opcode_byte(tcode, token.strip())
        return tcode, op

    raise ValueError(f"unknown opcode token: {tok}")


def first_pass(lines: List[str]) -> Dict[str, int]:
    labels: Dict[str, int] = {}
    pc = 0
    for raw in lines:
        line = strip_comment(raw)
        if not line:
            continue
        if line.endswith(":"):
            name = line[:-1].strip()
            if not name:
                raise ValueError("empty label")
            if name in labels:
                raise ValueError(f"duplicate label: {name}")
            labels[name] = pc
            continue
        pc += 1
    return labels


def assemble_line(tokens: List[str], labels: Dict[str, int]) -> Instr:
    if not tokens:
        raise ValueError("empty instruction")
    opcode_tok = tokens[0]
    args = tokens[1:]
    tongue, op = parse_opcode_token(opcode_tok)
    tid = TONGUE_TO_ID[tongue]
    key = (tongue, op)
    spec = OP_TO_SPEC.get(key)

    # Generic raw path for explicit sacred token opcodes not mapped in phase-1 ISA.
    if spec is None:
        a = parse_reg(args[0]) if len(args) >= 1 and args[0].lower().startswith("r") else (parse_int(args[0]) if len(args) >= 1 else 0)
        b = parse_reg(args[1]) if len(args) >= 2 and args[1].lower().startswith("r") else (parse_int(args[1]) if len(args) >= 2 else 0)
        imm = resolve_label_or_int(args[2], labels) if len(args) >= 3 else 0
        return Instr(tid, op, a & 0xFF, b & 0xFF, imm)

    ukey = spec.key
    if ukey in ("KO.NOP", "KO.HALT", "KO.RET", "KO.YIELD"):
        if args:
            raise ValueError(f"{ukey} takes no arguments")
        return Instr(tid, op)

    if ukey in ("KO.JMP", "KO.CALL"):
        if len(args) != 1:
            raise ValueError(f"{ukey} requires 1 argument: target")
        return Instr(tid, op, 0, 0, resolve_label_or_int(args[0], labels))

    if ukey in ("KO.JZ", "KO.JNZ"):
        if len(args) != 2:
            raise ValueError(f"{ukey} requires 2 arguments: reg target")
        return Instr(tid, op, parse_reg(args[0]), 0, resolve_label_or_int(args[1], labels))

    if ukey == "CA.MOVI":
        if len(args) != 2:
            raise ValueError("CA.MOVI requires 2 arguments: reg imm")
        return Instr(tid, op, parse_reg(args[0]), 0, parse_int(args[1]))

    if ukey in ("CA.MOV", "CA.ADD", "CA.SUB", "CA.MUL", "CA.DIV", "CA.MOD", "CA.CMP", "CA.AND", "CA.OR", "CA.XOR"):
        if len(args) != 2:
            raise ValueError(f"{ukey} requires 2 arguments: reg reg")
        return Instr(tid, op, parse_reg(args[0]), parse_reg(args[1]), 0)

    if ukey in ("RU.LOAD", "RU.STORE"):
        if len(args) != 2:
            raise ValueError(f"{ukey} requires 2 arguments: reg addr")
        return Instr(tid, op, parse_reg(args[0]), 0, resolve_label_or_int(args[1], labels))

    if ukey in ("AV.SEND", "AV.RECV"):
        if len(args) != 2:
            raise ValueError(f"{ukey} requires 2 arguments: reg channel")
        return Instr(tid, op, parse_reg(args[0]), 0, parse_int(args[1]))

    if ukey == "AV.SYSCALL":
        if len(args) != 1:
            raise ValueError("AV.SYSCALL requires 1 argument: id")
        return Instr(tid, op, 0, 0, parse_int(args[0]))

    if ukey in ("DR.ASSERT", "DR.VERIFY", "UM.HASH", "UM.REDACT"):
        if len(args) != 1:
            raise ValueError(f"{ukey} requires 1 argument: reg")
        return Instr(tid, op, parse_reg(args[0]), 0, 0)

    raise ValueError(f"unhandled instruction: {ukey}")


def assemble_text(src: str) -> Tuple[List[Instr], Dict[str, int], List[str]]:
    lines = src.splitlines()
    labels = first_pass(lines)
    listing: List[str] = []
    out: List[Instr] = []
    pc = 0
    for idx, raw in enumerate(lines, start=1):
        line = strip_comment(raw)
        if not line:
            continue
        if line.endswith(":"):
            continue
        toks = normalize_tokens(line)
        ins = assemble_line(toks, labels)
        out.append(ins)
        tongue = ID_TO_TONGUE[ins.tongue_id]
        token = opcode_byte_to_token(tongue, ins.opcode)
        listing.append(f"{pc:04d} | {line:<32} | {tongue}:{token} | a={ins.a} b={ins.b} imm={ins.imm}")
        pc += 1
    return out, labels, listing


def main() -> int:
    ap = argparse.ArgumentParser(description="stasm - Sacred Tongue assembler (Phase-1)")
    ap.add_argument("input", help="Assembly source file")
    ap.add_argument("-o", "--output", default="out.stv", help="Output bytecode path (default: out.stv)")
    ap.add_argument("--listing", action="store_true", help="Print assembly listing")
    args = ap.parse_args()

    src_path = Path(args.input)
    source = src_path.read_text(encoding="utf-8")

    instructions, labels, listing = assemble_text(source)
    blob = build_bytecode(instructions)
    out_path = Path(args.output)
    out_path.write_bytes(blob)

    print(f"Assembled {len(instructions)} instructions -> {out_path}")
    if labels:
        print(f"Labels: {labels}")
    if args.listing:
        print("---- LISTING ----")
        for row in listing:
            print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

