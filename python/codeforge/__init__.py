"""codeforge — the assembled workflow machine: messy intent in, verified code out.

Composes **crank** (the chassis: checkpointed phases + a tamper-evident receipt
chain) with **loom** (forced discrete states: one program woven into many
languages, with loop/mirror checks). ``forge(intent)`` turns a plain-English
arithmetic request into a Loom program that is verified across languages *and*
against Python's own arithmetic, and returns the crank Catalog — the receipted,
tamper-evident record of the whole run.

This is the deterministic capstone: the 'build' phase is a programmatic Loom
synthesizer (no LLM) standing in for an AI executor — but the verification and the
machine are entirely real. An LLM 'build' executor can drop in later unchanged.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from python.crank import GateVerdict, Phase, turn
from python.loom import cross_check, emit_c, emit_js, emit_python, mirror_check, parse, run
from python.loom.synth import arith_program

_OP_WORDS = {
    "add": "add",
    "plus": "add",
    "sum": "add",
    "multiply": "multiply",
    "times": "multiply",
    "product": "multiply",
}


def _understand(intent: str, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = intent.lower()
    op = next((_OP_WORDS[w] for w in _OP_WORDS if re.search(rf"\b{w}\b", text)), None)
    if op is None:
        return None  # -> drift: codeforge only knows arithmetic
    nums = [int(n) for n in re.findall(r"\d+", text)]
    a, b = (nums + [3, 4])[:2]  # sample operands if none were given
    return {"op": op, "a": a, "b": b}


def _build(intent: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    spec = ctx["outputs"]["understand"]
    return {"op": spec["op"], "a": spec["a"], "b": spec["b"], "assembly": arith_program(spec["op"])}


def _verify(intent: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    b = ctx["outputs"]["build"]
    prog = parse(b["assembly"])
    init = {"r1": b["a"], "r2": b["b"]}
    expected = b["a"] + b["b"] if b["op"] == "add" else b["a"] * b["b"]
    source = {
        "python": emit_python(prog, init),
        "javascript": emit_js(prog, init),
        "c": emit_c(prog, init),
    }
    # Run the bounded, loop-detecting reference FIRST. An LLM-proposed program may
    # not halt; cross_check execs the emitted Python in-process (no budget), so we
    # never cross-check a program that hasn't already halted with the right answer.
    ref = run(prog, init, max_steps=500_000)
    if not ref.halted or ref.output != [expected]:
        return {
            "verified": False,
            "expected": expected,
            "got": ref.output,
            "ref_status": ref.status,
            "backends": ["reference"],
            "source": source,
        }
    report = cross_check(prog, [init])  # safe now: the reference halted with the expected answer
    return {
        "verified": report["all_agree"],
        "expected": expected,
        "got": ref.output,
        "ref_status": ref.status,
        "backends": report["backends"],
        "source": source,
    }


def _review(intent: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    b = ctx["outputs"]["build"]
    prog = parse(b["assembly"])
    op = b["op"]
    cases = [(0, 0), (1, 0), (3, 4), (5, 2), (7, 6)]
    behavioral_ok = all(run(prog, {"r1": x, "r2": y}).output == [x + y if op == "add" else x * y] for x, y in cases)
    return {"behavioral_ok": behavioral_ok, "cases": len(cases), "mirror": mirror_check(b["assembly"])}


def _deliver(intent: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    build, verify, review = (ctx["outputs"][k] for k in ("build", "verify", "review"))
    return {
        "op": build["op"],
        "operands": [build["a"], build["b"]],
        "verified": verify["verified"],
        "behavioral_ok": review["behavioral_ok"],
        "backends": verify["backends"],
        "assembly": build["assembly"],
        "source": verify["source"],
        "status": "shipped",
    }


def _gate(phase: str, output: Any) -> GateVerdict:
    """Block the run unless verification and the behavioral battery actually pass."""
    if phase == "verify" and not output.get("verified"):
        return GateVerdict(False, f"verification failed: got {output.get('got')} expected [{output.get('expected')}]")
    if phase == "review" and not output.get("behavioral_ok"):
        return GateVerdict(False, "behavioral battery disagreed with Python arithmetic")
    return GateVerdict(True)


_LOOM_PROMPT = (
    "You write programs for a tiny register machine called Loom. Instruction set:\n"
    "  inc R     ; R += 1\n"
    "  dec R L   ; if R > 0 then R -= 1 (fall through) else goto L\n"
    "  jmp L     ; goto L\n"
    "  out R     ; append R to the output\n"
    "  halt      ; stop\n"
    "Registers are non-negative integers starting at 0; the inputs are in r1 and r2; "
    "a label is 'name:' (its own line or prefixing an instruction); ';' starts a comment.\n\n"
    "Write a Loom program that computes the {op} of r1 and r2, leaves the result in r3, "
    "then does 'out r3' and 'halt'. Output ONLY the program inside a ```loom code block."
)


def _extract_loom(raw: str) -> str:
    """Pull a Loom program out of an LLM reply (a fenced ```code``` block if present)."""
    if not raw:
        return ""
    match = re.search(r"```(?:loom|asm|text|)\s*(.+?)```", raw, re.DOTALL)
    return (match.group(1) if match else raw).strip()


def make_llm_build_executor(ask: Callable[[str], str]) -> Callable[[str, Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Wrap an LLM ``ask(prompt) -> str`` into a build phase.

    The LLM *proposes* a Loom program; the verify/review phases then GATE it — a
    wrong, looping, or malformed program is caught (verification fails -> blocked,
    or it doesn't parse -> drift). AI proposes, the machine verifies.
    """

    def build(intent: str, ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        spec = ctx["outputs"]["understand"]
        assembly = _extract_loom(ask(_LOOM_PROMPT.format(op=spec["op"])))
        try:
            parse(assembly)  # must be a valid Loom program, else -> drift
        except Exception:
            return None
        return {"op": spec["op"], "a": spec["a"], "b": spec["b"], "assembly": assembly, "source": "llm"}

    return build


def forge(intent: str, build: Optional[Callable[[str, Dict[str, Any]], Any]] = None):
    """Run the full workflow machine on a plain-English request; return the crank Catalog.

    By default the 'build' phase is the deterministic Loom synthesizer. Pass a build
    executor — e.g. ``make_llm_build_executor(ask)`` — to have an AI propose the
    program instead; the verify/review phases gate whatever it produces.
    """
    phases = [
        Phase("understand", _understand),
        Phase("build", build if build is not None else _build),
        Phase("verify", _verify),
        Phase("review", _review),
        Phase("deliver", _deliver),
    ]
    return turn(intent, phases, gate=_gate)
