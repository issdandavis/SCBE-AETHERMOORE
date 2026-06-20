"""tool_trajectory: harvest VERIFIED tool-USE trajectories -- training data for ORCHESTRATION, not recall.

The becoming-lift on plain final-code SFT came back ~0 because that trains INTELLIGENCE (write the answer)
on a benchmark the base model already saw. The learnable, non-saturated skill is TOOL USE: recognize you
need a tool, CALL it, USE its result, then answer. This harvests that loop as SFT.

A ReAct-style transcript: the model emits explicit `CALL <tool>: <arg>` (or `CALL run_code` with a code
block); the harness runs the tool and injects `TOOL <tool>: <result>`; the model continues until `ANSWER:`
+ code. ONLY trajectories whose final answer passes HELD-BACK tests (test_list[1:], never shown to the
model -- Codex's weak-oracle discipline; the shown example is test_list[0]) are kept. Truth = execution on
tests the model did not see. The kept record's messages include the tool turns, so SFT teaches the
call->use->answer loop, not the final answer alone.

    from python.helm.tool_trajectory import harvest_tool_traces, ollama_ask
    res = harvest_tool_traces(problems, ollama_ask("qwen2.5-coder:1.5b"))
    # res["records"] -> verified tool-use SFT; res["with_tool_use"] -> how many actually called a tool
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

from .public_bench import _verify

# the model slot for a multi-turn tool dialogue: full message list -> next assistant text
Ask = Callable[[List[Dict[str, str]]], str]

SYSTEM = (
    "You solve a Python problem by USING TOOLS, then giving a final answer.\n"
    "Tools (one call per message):\n"
    "  CALL run_code   -> include a ```python``` block above this line; it runs against the example test "
    "and returns PASS or the got-vs-expected failure.\n"
    "  CALL calc: <expr>     -> evaluates an arithmetic expression.\n"
    "  CALL is_prime: <n>    -> True/False.\n"
    "  CALL factor: <n>      -> prime factors.\n"
    "When confident, reply:\nANSWER:\n```python\n<complete solution>\n```\n"
    "Prefer to run_code at least once before answering."
)

REPAIR_BIASED_SYSTEM = (
    SYSTEM + "\n\nRepair-biased harvest mode:\n"
    "  1. Make a small first candidate quickly, even if uncertain.\n"
    "  2. CALL run_code on that candidate before giving ANSWER.\n"
    "  3. If the tool returns FAIL, use the got-vs-expected feedback to repair and CALL run_code again.\n"
    "  4. Only give ANSWER after using the tool feedback."
)

# A worked example shown to coax a weak model into the CALL/TOOL/ANSWER protocol. It is PROMPTING
# scaffolding only -- solve_with_tools strips it from the saved record so we never train on the demo,
# just on the model's own real trajectory. Uses a throwaway problem (no leakage into any eval).
FEWSHOT_TURNS: List[Dict[str, str]] = [
    {
        "role": "user",
        "content": "Write triple(n) returning n*3.\n\nExample test (you may run_code against it):\n"
        "assert triple(2) == 6",
    },
    {"role": "assistant", "content": "```python\ndef triple(n):\n    return n * 3\n```\nCALL run_code"},
    {"role": "user", "content": "TOOL run_code: PASS (example test)"},
    {"role": "assistant", "content": "ANSWER:\n```python\ndef triple(n):\n    return n * 3\n```"},
]


# --------------------------------------------------------------------------------------------------
# tools (deterministic; the model calls them, the harness runs them)
# --------------------------------------------------------------------------------------------------
@dataclass
class Tool:
    name: str
    run: Callable[[str], str]  # string arg -> string result
    doc: str


_ALLOWED_AST = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Tuple,
    ast.Load,
)


def _safe_calc(expr: str) -> str:
    """Evaluate an arithmetic expression with no names/calls/builtins -- a pure calculator."""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_AST):
                return "calc error: only arithmetic on numbers is allowed"
        return str(eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, {}))  # noqa: S307 (AST-gated)
    except Exception as exc:
        return "calc error: %s" % exc


def _is_prime(s: str) -> str:
    try:
        n = int(s.strip())
    except Exception:
        return "is_prime error: not an integer"
    if n < 2:
        return "False"
    i = 2
    while i * i <= n:
        if n % i == 0:
            return "False"
        i += 1
    return "True"


def _factor(s: str) -> str:
    try:
        n = abs(int(s.strip()))
    except Exception:
        return "factor error: not an integer"
    out: List[int] = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            out.append(d)
            n //= d
        d += 1
    if n > 1:
        out.append(n)
    return str(out or [int(s)])


def build_tools(problem: Dict[str, Any], public_k: int = 1) -> Dict[str, Tool]:
    """Per-problem tool registry. run_code closes over THIS problem's PUBLIC (shown) test only -- it is a
    debugging tool, not the answer key; acceptance is on held-back tests the model never sees."""
    public = list(problem.get("test_list", []))[:public_k]
    imports = list(problem.get("test_imports", []))

    def run_code(code: str) -> str:
        from .free_generator import _diagnose

        if len(code.strip()) < 5:
            return "run_code error: no code block found above the CALL"
        diags = _diagnose(code, public, imports)
        return "PASS (example test)" if not diags else "FAIL: " + " | ".join(str(d) for d in diags)[:400]

    return {
        "run_code": Tool("run_code", run_code, "run the code block against the example test"),
        "calc": Tool("calc", _safe_calc, "evaluate arithmetic"),
        "is_prime": Tool("is_prime", _is_prime, "primality test"),
        "factor": Tool("factor", _factor, "prime factorization"),
    }


# --------------------------------------------------------------------------------------------------
# parsing the model's turn
# --------------------------------------------------------------------------------------------------
_CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)
_CALL_RE = re.compile(r"CALL\s+(\w+)\s*:?[ \t]*(.*)", re.I)


def _last_code_block(text: str) -> str:
    m = _CODE_RE.findall(text)
    return m[-1].strip() if m else ""


def parse_turn(text: str) -> Dict[str, Any]:
    """Classify the model's message: an ANSWER (with code), a tool CALL, or nothing actionable."""
    if re.search(r"\bANSWER\b", text, re.I):
        after = re.split(r"\bANSWER\b\s*:?", text, maxsplit=1, flags=re.I)[-1]
        code = _last_code_block(after) or _last_code_block(text)
        return {"kind": "answer", "code": code}
    m = _CALL_RE.search(text)
    if m:
        tool = m.group(1).lower()
        arg = m.group(2).strip()
        if tool == "run_code":
            arg = _last_code_block(text)  # run_code operates on the code block in this message
        return {"kind": "call", "tool": tool, "arg": arg}
    return {"kind": "none"}


# --------------------------------------------------------------------------------------------------
# the ReAct loop -> one verified-or-not tool-use trajectory
# --------------------------------------------------------------------------------------------------
def solve_with_tools(
    problem: Dict[str, Any],
    ask: Ask,
    tools: Optional[Dict[str, Tool]] = None,
    max_steps: int = 5,
    public_k: int = 1,
    system: str = SYSTEM,
    few_shot: bool = True,
    prompt_mode: str = "confirm",
) -> Dict[str, Any]:
    """Run the model through a tool dialogue and record EVERY turn. Verify the final answer on HELD-BACK
    tests (test_list[public_k:]) the model never saw. With few_shot, a worked example is prepended to coax
    a weak model into the protocol, then STRIPPED from the saved record (we don't train on the demo).
    Returns the (demo-stripped) transcript + whether it verified and whether it actually used a tool."""
    tools = tools or build_tools(problem, public_k)
    head = (problem.get("prompt") or problem.get("text") or "").strip()
    tl = list(problem.get("test_list", []))
    public, held = tl[:public_k], tl[public_k:]
    imports = list(problem.get("test_imports", []))

    if prompt_mode == "repair-biased" and system == SYSTEM:
        system = REPAIR_BIASED_SYSTEM

    demo = list(FEWSHOT_TURNS) if few_shot else []
    mode_note = ""
    if prompt_mode == "repair-biased":
        mode_note = (
            "\n\nRepair harvest instruction: first test a quick minimal candidate with run_code. "
            "If it fails, revise from the TOOL feedback and test again before ANSWER."
        )
    elif prompt_mode != "confirm":
        raise ValueError("unsupported prompt_mode: %s" % prompt_mode)
    real_user = {
        "role": "user",
        "content": head + mode_note + "\n\nExample test (you may run_code against it):\n" + "\n".join(public),
    }
    msgs: List[Dict[str, str]] = [{"role": "system", "content": system}] + demo + [real_user]
    keep_from = 1 + len(demo)  # record = system + real problem onward; the demo is scaffolding, not data
    final_code = ""
    tool_calls = 0
    tools_used: List[str] = []
    for _ in range(max_steps):
        try:
            reply = ask(msgs)
        except Exception:
            break
        msgs.append({"role": "assistant", "content": reply})
        turn = parse_turn(reply)
        if turn["kind"] == "answer":
            final_code = turn["code"]
            break
        if turn["kind"] == "call" and turn["tool"] in tools:
            tool_calls += 1
            tools_used.append(turn["tool"])
            result = tools[turn["tool"]].run(turn["arg"])
            msgs.append({"role": "user", "content": "TOOL %s: %s" % (turn["tool"], result)})
            continue
        # nothing actionable -> nudge once toward the protocol
        msgs.append({"role": "user", "content": "Use a tool (CALL ...) or give ANSWER: with a code block."})
    # TRUTH: held-back tests the model never saw (the shown example is public[0])
    verified = bool(final_code) and bool(_verify(final_code, public, held, imports).get("hidden_passed"))
    record_messages = [msgs[0]] + msgs[keep_from:]  # drop the few-shot demo: train on the real trajectory only
    return {
        "messages": record_messages,
        "final_code": final_code,
        "verified": verified,
        "tool_calls": tool_calls,
        "tools_used": sorted(set(tools_used)),
        "used_tool": tool_calls > 0,
    }


def harvest_tool_traces(
    problems: Sequence[Dict[str, Any]],
    ask: Ask,
    tools: Optional[Dict[str, Tool]] = None,
    max_steps: int = 5,
    public_k: int = 1,
    require_tool_use: bool = True,
    prompt_mode: str = "confirm",
) -> Dict[str, Any]:
    """Keep ONLY verified trajectories (held-back tests passed). With require_tool_use, also require the
    model actually called a tool -- so the corpus teaches ORCHESTRATION, not just lucky one-shot answers."""
    records: List[Dict[str, Any]] = []
    attempted = with_tool_use = 0
    for p in problems:
        attempted += 1
        tr = solve_with_tools(p, ask, tools, max_steps, public_k, prompt_mode=prompt_mode)
        if tr["used_tool"]:
            with_tool_use += 1
        if tr["verified"] and (tr["used_tool"] or not require_tool_use):
            records.append(
                {
                    "messages": tr["messages"],
                    "meta": {
                        "verified": True,
                        "task_id": p.get("task_id"),
                        "tool_calls": tr["tool_calls"],
                        "tools_used": tr["tools_used"],
                        "prompt_mode": prompt_mode,
                        "source": "tool_trajectory",
                    },
                }
            )
    n = len(problems) or 1
    return {
        "records": records,
        "attempted": attempted,
        "verified": len(records),
        "with_tool_use": with_tool_use,
        "verified_rate": round(len(records) / n, 3),
    }


def ollama_ask(model: str, base: Optional[str] = None, key: Optional[str] = None) -> Ask:
    """Wrap an OpenAI-compatible (Ollama) chat endpoint as a message-list -> next-text Ask."""
    import os

    from .free_generator import DEFAULT_BASE, _chat

    b = base or os.environ.get("SCBE_LLM_BASE", DEFAULT_BASE)
    k = key or os.environ.get("SCBE_LLM_KEY", "ollama")
    return lambda msgs: _chat(list(msgs), base=b, key=k, model=model)


def reference_tool_solver(problem: Dict[str, Any]) -> Ask:
    """A scripted Ask (no model) that performs a correct tool-use trajectory: run_code the answer key,
    read PASS, then ANSWER. Validates the loop + verification + SFT shape offline."""
    code = problem.get("code", "")
    state = {"step": 0}

    def ask(_msgs: List[Dict[str, str]]) -> str:
        state["step"] += 1
        if state["step"] == 1:
            return "Let me test a candidate.\n```python\n%s\n```\nCALL run_code" % code
        return "ANSWER:\n```python\n%s\n```" % code

    return ask
