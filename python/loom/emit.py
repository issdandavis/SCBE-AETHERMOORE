"""Weave one Loom program into many languages.

Every emitter produces a complete, runnable program for one fixed input (the
initial register values are baked in), structured as a single ``pc``-dispatch
loop. The dispatch is generated identically across languages, so the three
outputs are equal by construction — the cross-language coherence is exact, not
hoped-for. ``equiv.cross_check`` verifies it by actually running them.
"""

from __future__ import annotations

from typing import Dict, Optional

from .machine import Program


def _initial_registers(prog: Program, init: Optional[Dict[str, int]]) -> Dict[str, int]:
    regs = {r: 0 for r in prog.registers}
    for key, val in (init or {}).items():
        if key in regs:
            regs[key] = int(val)
    return regs


def emit_python(prog: Program, init: Optional[Dict[str, int]] = None, func_name: str = "run") -> str:
    regs = _initial_registers(prog, init)
    n = len(prog.instrs)
    items = ", ".join(f"{r!r}: {regs[r]}" for r in prog.registers)
    out = [f"def {func_name}():", f"    R = {{{items}}}", "    pc = 0", "    trace = []"]
    if n == 0:
        out.append("    return trace")
        return "\n".join(out)
    out.append(f"    while 0 <= pc < {n}:")
    for idx, ins in enumerate(prog.instrs):
        kw = "if" if idx == 0 else "elif"
        out.append(f"        {kw} pc == {idx}:")
        if ins.op == "inc":
            out.append(f"            R[{ins.reg!r}] += 1; pc += 1")
        elif ins.op == "dec":
            out.append(f"            if R[{ins.reg!r}] > 0:")
            out.append(f"                R[{ins.reg!r}] -= 1; pc += 1")
            out.append("            else:")
            out.append(f"                pc = {ins.target}")
        elif ins.op == "jmp":
            out.append(f"            pc = {ins.target}")
        elif ins.op == "out":
            out.append(f"            trace.append(R[{ins.reg!r}]); pc += 1")
        else:  # halt
            out.append("            break")
    out.append("        else:")
    out.append("            break")
    out.append("    return trace")
    return "\n".join(out)


def emit_js(prog: Program, init: Optional[Dict[str, int]] = None, func_name: str = "run") -> str:
    regs = _initial_registers(prog, init)
    n = len(prog.instrs)
    items = ", ".join(f"{r}: {regs[r]}" for r in prog.registers)
    out = [f"function {func_name}() {{", f"  const R = {{{items}}};", "  let pc = 0;", "  const trace = [];"]
    if n:
        out.append(f"  while (pc >= 0 && pc < {n}) {{")
        for idx, ins in enumerate(prog.instrs):
            kw = "if" if idx == 0 else "else if"
            if ins.op == "inc":
                body = f"R.{ins.reg} += 1; pc += 1;"
            elif ins.op == "dec":
                body = f"if (R.{ins.reg} > 0) {{ R.{ins.reg} -= 1; pc += 1; }} else {{ pc = {ins.target}; }}"
            elif ins.op == "jmp":
                body = f"pc = {ins.target};"
            elif ins.op == "out":
                body = f"trace.push(R.{ins.reg}); pc += 1;"
            else:
                body = "break;"
            out.append(f"    {kw} (pc === {idx}) {{ {body} }}")
        out.append("    else { break; }")
        out.append("  }")
    out.append("  return trace;")
    out.append("}")
    return "\n".join(out)


def emit_c(prog: Program, init: Optional[Dict[str, int]] = None, out_cap: int = 100_000) -> str:
    regs = _initial_registers(prog, init)
    n = len(prog.instrs)
    decls = " ".join(f"long {r} = {regs[r]};" for r in prog.registers) or "/* no registers */"
    lines = [
        "#include <stdio.h>",
        "int main(void) {",
        f"    {decls}",
        "    int pc = 0;",
        f"    long trace[{out_cap}]; int tn = 0;",
    ]
    if n:
        lines.append(f"    while (pc >= 0 && pc < {n}) {{")
        for idx, ins in enumerate(prog.instrs):
            kw = "if" if idx == 0 else "else if"
            if ins.op == "inc":
                body = f"{ins.reg} += 1; pc += 1;"
            elif ins.op == "dec":
                body = f"if ({ins.reg} > 0) {{ {ins.reg} -= 1; pc += 1; }} else {{ pc = {ins.target}; }}"
            elif ins.op == "jmp":
                body = f"pc = {ins.target};"
            elif ins.op == "out":
                body = f"if (tn < {out_cap}) trace[tn++] = {ins.reg}; pc += 1;"
            else:
                body = "break;"
            lines.append(f"        {kw} (pc == {idx}) {{ {body} }}")
        lines.append("        else { break; }")
        lines.append("    }")
    lines.append('    for (int i = 0; i < tn; i++) { printf("%ld", trace[i]); if (i + 1 < tn) printf(" "); }')
    lines.append('    printf("\\n");')
    lines.append("    return 0;")
    lines.append("}")
    return "\n".join(lines)


EMITTERS = {"python": emit_python, "javascript": emit_js, "c": emit_c}
