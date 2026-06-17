"""Loom — a tiny universal loop machine (a Minsky register machine).

Write one program; weave it into many languages (see ``emit``); read the
*topology* of its run. A run is a sequence of state-points ``(pc, registers)``.
Because the machine is deterministic, a **revisited state closes a loop**
(a self-intersection of the trajectory) and proves the program never halts.

Halting is undecidable in general, so loop detection here is **sound but
incomplete**: a detected revisit is *certainly* an infinite loop; failing to
detect one within the step budget means "undetermined" — never "halts". That
gap is the honest version of "you can't fully match yourself": the machine
cannot, in general, decide its own behavior.

Instruction set (Turing-complete with >= 2 registers — the Minsky 2-counter result):

    inc R        ; R += 1
    dec R L      ; if R > 0 then R -= 1 (fall through) else goto L
    jmp L        ; goto L
    out R        ; append R to the output trace
    halt         ; stop

Syntax: one instruction per line; ``#`` or ``;`` starts a comment; ``name:`` is a
label (it may sit on its own line or prefix an instruction). Names match
``[A-Za-z_][A-Za-z0-9_]*``. Registers are non-negative integers, default 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_WORD = r"[A-Za-z_][A-Za-z0-9_]*"
_LABEL_RE = re.compile(rf"^({_WORD})\s*:\s*(.*)$")


class LoomSyntaxError(ValueError):
    """Raised for malformed Loom source."""


@dataclass(frozen=True)
class Instr:
    op: str  # inc | dec | jmp | out | halt
    reg: Optional[str] = None
    target: Optional[int] = None  # resolved instruction index (dec / jmp)
    target_label: Optional[str] = None  # original label name (for unparse / debugging)


@dataclass
class Program:
    instrs: List[Instr]
    registers: Tuple[str, ...]
    labels: Dict[str, int] = field(default_factory=dict)

    def signature(self) -> Tuple:
        """Structural identity: (op, reg, resolved target) per instruction.

        Label *names* are ignored, so two programs that differ only in label
        spelling have the same signature — this is what an exact mirror compares.
        """
        return tuple((i.op, i.reg, i.target) for i in self.instrs)


def parse(source: str) -> Program:
    """Parse Loom assembly into a resolved Program."""
    label_to_index: Dict[str, int] = {}
    instr_tokens: List[Tuple[int, List[str]]] = []  # (source lineno, tokens)
    pending_labels: List[str] = []

    for lineno, line in enumerate(source.splitlines(), 1):
        line = line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line:
            continue
        # peel any leading "label:" prefixes off the front of the line
        while True:
            m = _LABEL_RE.match(line)
            if not m:
                break
            pending_labels.append(m.group(1))
            line = m.group(2).strip()
            if not line:
                break
        if not line:
            continue  # label(s) only — they attach to the next instruction
        idx = len(instr_tokens)
        for lab in pending_labels:
            if lab in label_to_index:
                raise LoomSyntaxError(f"line {lineno}: duplicate label {lab!r}")
            label_to_index[lab] = idx
        pending_labels = []
        instr_tokens.append((lineno, line.split()))

    end_index = len(instr_tokens)  # labels after the last instruction point past the end (= halt)
    for lab in pending_labels:
        if lab in label_to_index:
            raise LoomSyntaxError(f"duplicate label {lab!r}")
        label_to_index[lab] = end_index

    registers: List[str] = []

    def note(reg: str) -> str:
        if reg not in registers:
            registers.append(reg)
        return reg

    def resolve(lab: str, lineno: int) -> int:
        if lab not in label_to_index:
            raise LoomSyntaxError(f"line {lineno}: unknown label {lab!r}")
        return label_to_index[lab]

    instrs: List[Instr] = []
    for lineno, toks in instr_tokens:
        op = toks[0].lower()
        if op == "inc" and len(toks) == 2:
            instrs.append(Instr("inc", reg=note(toks[1])))
        elif op == "dec" and len(toks) == 3:
            instrs.append(Instr("dec", reg=note(toks[1]), target=resolve(toks[2], lineno), target_label=toks[2]))
        elif op == "jmp" and len(toks) == 2:
            instrs.append(Instr("jmp", target=resolve(toks[1], lineno), target_label=toks[1]))
        elif op == "out" and len(toks) == 2:
            instrs.append(Instr("out", reg=note(toks[1])))
        elif op == "halt" and len(toks) == 1:
            instrs.append(Instr("halt"))
        else:
            raise LoomSyntaxError(f"line {lineno}: bad instruction {' '.join(toks)!r}")

    return Program(instrs=instrs, registers=tuple(sorted(registers)), labels=label_to_index)


@dataclass
class RunResult:
    output: List[int]
    steps: int
    status: str  # "halted" | "loop" | "budget"
    loop_state: Optional[Tuple[int, Tuple[int, ...]]] = None
    registers: Dict[str, int] = field(default_factory=dict)

    @property
    def halted(self) -> bool:
        return self.status == "halted"

    @property
    def loops(self) -> bool:
        return self.status == "loop"


def run(
    prog: Program, init: Optional[Dict[str, int]] = None, max_steps: int = 100_000, detect_loops: bool = True
) -> RunResult:
    """Execute a Program. Detects infinite loops by spotting a revisited state."""
    regs: Dict[str, int] = {r: 0 for r in prog.registers}
    for key, val in (init or {}).items():
        if key in regs:  # ignore inits for registers the program never touches
            regs[key] = int(val)

    pc = 0
    out: List[int] = []
    seen: set = set()
    steps = 0
    n = len(prog.instrs)

    while 0 <= pc < n:
        if steps >= max_steps:
            return RunResult(out, steps, "budget", None, dict(regs))
        if detect_loops:
            state = (pc, tuple(regs[r] for r in prog.registers))
            if state in seen:
                return RunResult(out, steps, "loop", state, dict(regs))
            seen.add(state)
        ins = prog.instrs[pc]
        if ins.op == "inc":
            regs[ins.reg] += 1
            pc += 1
        elif ins.op == "dec":
            if regs[ins.reg] > 0:
                regs[ins.reg] -= 1
                pc += 1
            else:
                pc = ins.target
        elif ins.op == "jmp":
            pc = ins.target
        elif ins.op == "out":
            out.append(regs[ins.reg])
            pc += 1
        elif ins.op == "halt":
            return RunResult(out, steps, "halted", None, dict(regs))
        steps += 1

    return RunResult(out, steps, "halted", None, dict(regs))  # fell off the end = halt


def unparse(prog: Program) -> str:
    """Render a Program back to canonical Loom assembly (the mirror of parse).

    Labels are regenerated (L0, L1, ...), so parse(unparse(p)) is structurally
    identical to p whenever every jump target is a real instruction. A target
    that points *past* the last instruction (jump-to-end) is materialized as an
    explicit trailing ``halt`` — behaviorally identical, structurally one
    instruction longer: a "near mirror", not an exact one.
    """
    n = len(prog.instrs)
    real_targets = sorted({i.target for i in prog.instrs if i.target is not None and i.target < n})
    label_at = {idx: f"L{k}" for k, idx in enumerate(real_targets)}
    end_needed = any(i.target == n for i in prog.instrs)
    end_label = "L_end"

    def tlabel(target: int) -> str:
        return label_at[target] if target < n else end_label

    lines: List[str] = []
    for idx, ins in enumerate(prog.instrs):
        prefix = f"{label_at[idx]}: " if idx in label_at else ""
        if ins.op == "inc":
            body = f"inc {ins.reg}"
        elif ins.op == "dec":
            body = f"dec {ins.reg} {tlabel(ins.target)}"
        elif ins.op == "jmp":
            body = f"jmp {tlabel(ins.target)}"
        elif ins.op == "out":
            body = f"out {ins.reg}"
        else:
            body = "halt"
        lines.append(prefix + body)
    if end_needed:
        lines.append(f"{end_label}: halt")
    return "\n".join(lines)
