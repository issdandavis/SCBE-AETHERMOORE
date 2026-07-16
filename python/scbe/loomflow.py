"""loomflow: a tiny control-flow IR that emits FULL (branching, looping) programs into many
language faces -- the cheap path past the straight-line scalar core, verified by execution.

The polyglot scalar core is straight-line: one opcode -> one statement, no branches. This adds
the missing piece -- conditionals and loops -- the CHEAP way, skipping the hard control-flow
structuring (relooper) pass entirely. Each program is emitted as a DISPATCH LOOP: a `while`
over a program counter with one `if pc == k` arm per instruction. That shape exists in EVERY
language (no goto needed -- which matters, since Python/Rust/JS/Zig have none), so a real loop
runs identically across faces today.

Honest tradeoff: the emitted code is a STATE MACHINE, not idiomatic `while`/`if` -- structured,
human-shaped output is the expensive relooper version. But it is real, executable, branching
code that computes the right answer, and a Python interpreter of the IR is the reference every
emitted face is RUN against. So "full programs work across languages" becomes a tested fact.

A program is a line-based assembly (variables are named slots; comments use ; or #):

    const acc 0 / const i 1 / const n 5
    label loop / le t i n / brz t end / add acc acc i / inc i / jmp loop
    label end / print acc / halt          # -> 15, verified in python, js, rust, c ...
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

Instr = Tuple[str, Tuple[str, ...]]

_ARITH = {"add": "+", "sub": "-", "mul": "*", "div": "/"}
_CMP = {"lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "==", "ne": "!="}
_OPS = {"const", "mov", "inc", "dec", "label", "jmp", "brz", "print", "halt"} | set(_ARITH) | set(_CMP)


def _is_number(tok: str) -> bool:
    try:
        float(tok)
        return True
    except ValueError:
        return False


def parse(text: str) -> List[Instr]:
    """Parse the line-based assembly into (op, args) instructions.

    SECURITY: every operand must be a plain identifier or a number. Slot names are interpolated
    verbatim into emitted source (`s_<name>`) which is then compiled and RUN, so an operand like
    `x[__import__('os').system('...')]` would be code injection. Identifiers/numbers can't carry a
    payload (no brackets/quotes/calls), exactly as polyglot.emit forces fn/arg names to .isidentifier().
    """
    prog: List[Instr] = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        op, args = parts[0].lower(), tuple(parts[1:])
        if op not in _OPS:
            raise ValueError("unknown op %r (have %s)" % (op, ", ".join(sorted(_OPS))))
        for a in args:
            if not (a.isidentifier() or _is_number(a)):
                raise ValueError("illegal operand %r: operands must be identifiers or numbers" % a)
        prog.append((op, args))
    return prog


def _labels(prog: Sequence[Instr]) -> Dict[str, int]:
    return {a[0]: i for i, (op, a) in enumerate(prog) if op == "label"}


def interpret(
    prog: Sequence[Instr],
    step_limit: int = 1_000_000,
    *,
    trace_hook: Optional[Callable[[int, Instr], None]] = None,
) -> List[float]:
    """The reference: run the IR directly and return everything it printed."""
    labels = _labels(prog)
    s: Dict[str, float] = {}
    out: List[float] = []
    pc, steps = 0, 0
    while 0 <= pc < len(prog):
        if trace_hook is not None:
            trace_hook(pc, prog[pc])
        steps += 1
        if steps > step_limit:
            raise RuntimeError("step limit exceeded (infinite loop?)")
        op, a = prog[pc]
        if op == "const":
            s[a[0]] = float(a[1])
            pc += 1
        elif op == "mov":
            s[a[0]] = s[a[1]]
            pc += 1
        elif op in _ARITH:
            x, y = s[a[1]], s[a[2]]
            s[a[0]] = x + y if op == "add" else x - y if op == "sub" else x * y if op == "mul" else x / y
            pc += 1
        elif op in _CMP:
            x, y = s[a[1]], s[a[2]]
            r = {"lt": x < y, "le": x <= y, "gt": x > y, "ge": x >= y, "eq": x == y, "ne": x != y}[op]
            s[a[0]] = 1.0 if r else 0.0
            pc += 1
        elif op == "inc":
            s[a[0]] += 1.0
            pc += 1
        elif op == "dec":
            s[a[0]] -= 1.0
            pc += 1
        elif op == "label":
            pc += 1
        elif op == "jmp":
            pc = labels[a[0]]
        elif op == "brz":
            pc = labels[a[1]] if s[a[0]] == 0.0 else pc + 1
        elif op == "print":
            out.append(s[a[0]])
            pc += 1
        elif op == "halt":
            break
    return out


def control_flow_edges(prog: Sequence[Instr]) -> List[Tuple[int, int]]:
    """Return the exact static PC transitions authorized by the Loomflow IR."""
    labels = _labels(prog)
    edges = set()
    for pc, (op, args) in enumerate(prog):
        if op == "halt":
            continue
        if op == "jmp":
            edges.add((pc, labels[args[0]]))
            continue
        if op == "brz":
            edges.add((pc, labels[args[1]]))
            if pc + 1 < len(prog):
                edges.add((pc, pc + 1))
            continue
        if pc + 1 < len(prog):
            edges.add((pc, pc + 1))
    return sorted(edges)


def trace_execution(prog: Sequence[Instr], step_limit: int = 1_000_000) -> dict:
    """Execute and receipt the phase-lifted PC trajectory.

    A loop revisits a base PC. Pairing it with the monotonically increasing
    ``phase`` makes every lifted state unique. Every projected transition is
    checked against the original Loomflow CFG, so the lift cannot invent an
    edge merely to make the execution linear.
    """
    pcs: List[int] = []
    outputs = interpret(
        prog,
        step_limit=step_limit,
        trace_hook=lambda pc, _instruction: pcs.append(pc),
    )
    allowed = set(control_flow_edges(prog))
    observed = list(zip(pcs, pcs[1:]))
    topology_preserved = all(edge in allowed for edge in observed)
    states = [{"phase": phase, "pc": pc, "op": prog[pc][0]} for phase, pc in enumerate(pcs)]
    canonical_program = json.dumps(list(prog), separators=(",", ":"))
    canonical_trace = json.dumps(states, separators=(",", ":"))
    return {
        "schema": "scbe.loomflow-topological-trace.v1",
        "outputs": outputs,
        "base_instruction_count": len(prog),
        "base_edges": [list(edge) for edge in sorted(allowed)],
        "pc_trace": pcs,
        "lifted_states": states,
        "program_sha256": hashlib.sha256(canonical_program.encode()).hexdigest(),
        "trace_sha256": hashlib.sha256(canonical_trace.encode()).hexdigest(),
        "proof": {
            "topology_preserved": topology_preserved,
            "unique_lifted_states": len({(row["phase"], row["pc"]) for row in states}) == len(states),
            "projection_covers_program": set(pcs) == set(range(len(prog))),
            "lift_has_hamiltonian_path": bool(states),
        },
    }


def verify_trace_integrity(reference_pcs: Sequence[int], observed_pcs: Sequence[int]) -> dict:
    """Compare an observed dispatch trajectory to the authorized PC record."""
    common = min(len(reference_pcs), len(observed_pcs))
    first_deviation = next(
        (index for index in range(common) if reference_pcs[index] != observed_pcs[index]),
        None,
    )
    if first_deviation is None and len(reference_pcs) != len(observed_pcs):
        first_deviation = common
    valid = first_deviation is None
    return {
        "valid": valid,
        "decision": "VALID" if valid else "ATTACK",
        "first_deviation_phase": first_deviation,
        "expected_length": len(reference_pcs),
        "observed_length": len(observed_pcs),
    }


def _slots(prog: Sequence[Instr]) -> List[str]:
    """Every named slot the program writes (declared up front in the emit)."""
    names: List[str] = []
    for op, a in prog:
        dst = None
        if op in ("const", "mov", "inc", "dec") or op in _ARITH or op in _CMP:
            dst = a[0]
        if dst and dst not in names:
            names.append(dst)
    return names


def _num(v: str) -> str:
    return repr(float(v))


# --- per-language dispatch-loop emit -------------------------------------------
# A face declares all slots = 0.0, then loops: while pc in range, one `if pc == k` arm per
# instruction, each arm does its effect and sets pc. No goto; works in every language.


def _arms(prog: Sequence[Instr], labels: Dict[str, int], lang: str) -> List[Tuple[str, str]]:
    """For each instruction k, the (effect, pc-update) statement pair in `lang`'s syntax."""

    def slot(n):
        name = "s_" + n
        if not name.isidentifier():  # last gate before this becomes runnable source (defense in depth)
            raise ValueError("illegal slot name %r (would inject into emitted source)" % n)
        return name

    def cmp_to_bool(op, a):
        return "%s %s %s" % (slot(a[1]), _CMP[op], slot(a[2]))

    tern = {
        "python": "(1.0 if %s else 0.0)",
        "javascript": "(%s ? 1.0 : 0.0)",
        "rust": "(if %s { 1.0 } else { 0.0 })",
        "c": "((%s) ? 1.0 : 0.0)",
    }[lang]
    out: List[Tuple[str, str]] = []
    for k, (op, a) in enumerate(prog):
        eff, nxt = "", "pc = %d" % (k + 1)
        if op == "const":
            eff = "%s = %s" % (slot(a[0]), _num(a[1]))
        elif op == "mov":
            eff = "%s = %s" % (slot(a[0]), slot(a[1]))
        elif op in _ARITH:
            eff = "%s = %s %s %s" % (slot(a[0]), slot(a[1]), _ARITH[op], slot(a[2]))
        elif op in _CMP:
            eff = "%s = %s" % (slot(a[0]), tern % cmp_to_bool(op, a))
        elif op == "inc":
            eff = "%s = %s + 1.0" % (slot(a[0]), slot(a[0]))
        elif op == "dec":
            eff = "%s = %s - 1.0" % (slot(a[0]), slot(a[0]))
        elif op == "label":
            pass
        elif op == "jmp":
            nxt = "pc = %d" % labels[a[0]]
        elif op == "brz":
            cond = "%s == 0.0" % slot(a[0])
            tgt, fall = labels[a[1]], k + 1
            if lang == "python":
                nxt = "pc = %d if %s else %d" % (tgt, cond, fall)
            else:
                nxt = (
                    "if (%s) { pc = %d; } else { pc = %d; }" % (cond, tgt, fall)
                    if lang != "rust"
                    else "if %s { pc = %d; } else { pc = %d; }" % (cond, tgt, fall)
                )
        elif op == "print":
            eff = {
                "python": "_out.append(%s)" % slot(a[0]),
                "javascript": "console.log(%s)" % slot(a[0]),
                "rust": 'println!("{}", %s)' % slot(a[0]),
                "c": 'printf("%%.17g\\n", %s)' % slot(a[0]),
            }[lang]
        elif op == "halt":
            nxt = "pc = -1"
        out.append((eff, nxt))
    return out


def emit(prog: Sequence[Instr], lang: str) -> str:
    """Emit the program as a dispatch loop in `lang` (python/javascript/rust/c)."""
    labels = _labels(prog)
    slots = _slots(prog)
    n = len(prog)
    arms = _arms(prog, labels, lang)
    if lang == "python":
        body = ["    s_%s = 0.0" % s for s in slots] + ["    _out = []", "    pc = 0", "    while 0 <= pc < %d:" % n]
        for k, (eff, nxt) in enumerate(arms):
            head = "        if pc == %d:" % k if k == 0 else "        elif pc == %d:" % k
            body.append(head)
            for line in ([eff] if eff else []) + [nxt]:
                body.append("            " + line)
        body += ["        else:", "            pc = -1", "    return _out[-1] if _out else None"]
        return "def run():\n" + "\n".join(body) + "\n\n\nif __name__ == '__main__':\n    print(run())\n"

    # brace languages (javascript / rust / c)
    decl = {
        "javascript": ["let s_%s = 0.0;" % s for s in slots] + ["let pc = 0;"],
        "rust": ["let mut s_%s: f64 = 0.0;" % s for s in slots] + ["let mut pc: i64 = 0;"],
        "c": ["double s_%s = 0.0;" % s for s in slots] + ["int pc = 0;"],
    }[lang]
    lines = ["    " + d for d in decl]
    lines.append("    while (pc >= 0 && pc < %d) {" % n)
    for k, (eff, nxt) in enumerate(arms):
        kw = "if" if k == 0 else "} else if"
        lines.append("        %s (pc == %d) {" % (kw, k))
        for line in ([eff + ";"] if eff else []) + [nxt + ("" if nxt.endswith("}") else ";")]:
            lines.append("            " + line)
    lines += ["        } else { pc = -1; }", "    }"]
    inner = "\n".join(lines)
    if lang == "javascript":
        return inner + "\n"
    if lang == "rust":
        return "fn main() {\n" + inner + "\n}\n"
    return "#include <stdio.h>\n#include <math.h>\nint main(void) {\n" + inner + "\n    return 0;\n}\n"


# --- run each emitted face and compare to the reference ------------------------
_RUN = {"python": None, "javascript": "node", "rust": "rustc", "c": "cc"}


def _last_float(stdout: str) -> Optional[float]:
    line = (stdout.strip().splitlines() or [""])[-1].strip()
    if line.lower() in ("nan", "-nan"):
        return float("nan")
    return float(line) if line not in ("", "None") else None


def run_face(prog: Sequence[Instr], lang: str) -> Optional[float]:
    src = emit(prog, lang)
    with tempfile.TemporaryDirectory() as td:
        ext = {"python": "py", "javascript": "js", "rust": "rs", "c": "c"}[lang]
        f = Path(td) / ("prog." + ext)
        f.write_text(src, encoding="utf-8")
        if lang == "python":
            import sys

            return _last_float(
                subprocess.run([sys.executable, str(f)], capture_output=True, text=True, timeout=30).stdout
            )
        if lang == "javascript":
            return _last_float(subprocess.run(["node", str(f)], capture_output=True, text=True, timeout=30).stdout)
        exe = Path(td) / ("prog.exe" if shutil.which("cmd") else "prog")
        cc = ["rustc", "-O", str(f), "-o", str(exe)] if lang == "rust" else ["cc", str(f), "-lm", "-o", str(exe)]
        subprocess.run(cc, capture_output=True, text=True, timeout=120, check=True)
        return _last_float(subprocess.run([str(exe)], capture_output=True, text=True, timeout=30).stdout)


def verify(prog: Sequence[Instr], faces: Sequence[str] = ("python", "javascript", "rust", "c")) -> dict:
    """Run the reference, then every face that has a local toolchain; compare each honestly."""
    # GUARD the reference like the face runs already are: a program whose reference raises (div-by-zero,
    # an out-of-range index) must not crash the verifier OR hide a real divergence -- surface it.
    try:
        ref = interpret(prog)
        reference, ref_error = (ref[-1] if ref else None), None
    except Exception as e:
        reference, ref_error = None, "%s: %s" % (type(e).__name__, e)
    results: Dict[str, dict] = {}
    for lang in faces:
        tool = _RUN.get(lang, "<none>")
        if tool is not None and shutil.which(tool) is None:
            results[lang] = {"status": "NO_TOOLCHAIN", "value": None}
            continue
        try:
            v = run_face(prog, lang)
        except Exception as e:
            results[lang] = {"status": "ERROR", "value": None, "note": "%s: %s" % (type(e).__name__, e)}
            continue
        if ref_error is not None:  # no reference to compare against -> we cannot certify agreement
            results[lang] = {"status": "NO_REFERENCE", "value": v}
            continue
        agree = v == reference or (v is not None and reference is not None and abs(v - reference) <= 1e-9)
        results[lang] = {"status": "AGREE" if agree else "DISAGREE", "value": v}
    verified = [lang for lang, r in results.items() if r["status"] == "AGREE"]
    return {
        "reference": reference,
        "reference_error": ref_error,
        "results": results,
        "verified": verified,
        "verified_count": len(verified),
        "disagree": [lang for lang, r in results.items() if r["status"] == "DISAGREE"],
    }


EXAMPLES = {
    "sum_1_to_5": "const acc 0\nconst i 1\nconst n 5\nlabel loop\nle t i n\nbrz t end\n"
    "add acc acc i\ninc i\njmp loop\nlabel end\nprint acc\nhalt",
    "factorial_5": "const acc 1\nconst i 1\nconst n 5\nlabel loop\nle t i n\nbrz t end\n"
    "mul acc acc i\ninc i\njmp loop\nlabel end\nprint acc\nhalt",
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        prog="scbe-loomflow", description="full (branching) programs across language faces, verified"
    )
    ap.add_argument("example", nargs="?", default="sum_1_to_5", choices=sorted(EXAMPLES), help="which example program")
    ap.add_argument("--emit", help="print the emitted source for one face (e.g. rust)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    prog = parse(EXAMPLES[a.example])
    if a.emit:
        print(emit(prog, a.emit))
        return 0
    r = verify(prog)
    print("LOOMFLOW  %s  (a real loop, branching)  reference=%s" % (a.example, r["reference"]))
    print("  verified faces: %d  ->  %s" % (r["verified_count"], ", ".join(r["verified"]) or "(none)"))
    for lang in sorted(r["results"]):
        d = r["results"][lang]
        print("    %-12s %-12s value=%s%s" % (lang, d["status"], d["value"], "  " + d.get("note", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
