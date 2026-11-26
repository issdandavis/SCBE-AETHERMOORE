"""governed_tools: the deterministic agent tools (calc / is_prime / factor / run_code), but every call is
gate-screened and forward-chain SEALED -- so a harvested tool-use trajectory is GOVERNED tool use,
auditable by construction, not merely correct.

The tool-use harvester (python/helm/tool_trajectory.py, Codex's lane) runs ungoverned in-process tools.
This is the optional governed BACKEND it can point at, built entirely on my side (no edit to the harvester):
calc/is_prime/factor are pure-numeric and pass through; run_code is an RCE surface, so its code is screened
by the never-delete/destructive regex AND the L13 intent gate BEFORE it runs -- a destructive snippet is
REFUSED and never executed, and the refusal is sealed too. Every call (allowed or refused) appends a sealed
receipt (reuses desktop_access._seal, the same chain as AetherDesk / golf). The model learns to operate
tools that are governed; the trajectory carries its own audit trail.

This unifies the two halves: "tool-use is the skill" (the harvester) + "the tools are governed" (this) =
the agent learns to drive GOVERNED tools, and the harvested data is gate-passed + receipted by construction.

    box = GovernedToolbox()
    box.call("run_code", "import shutil\nshutil.rmtree('/important')", problem=p)  # REFUSED, never run
    box.call("calc", "2 + 3 * 4")["result"]                                        # "14", sealed
    tools, box = governed_callables(problem=p)   # {name: arg->str} drop-in for the harvester's build_tools
    box.verify()                                 # the receipt chain holds
"""

from __future__ import annotations

import ast
import hashlib
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

from .desktop_access import _DESTRUCTIVE, _gate, _seal

_TOOL_NAMES = ("run_code", "calc", "is_prime", "factor")
_CALC_NODES = (
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
)


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# --- the deterministic tools (result strings match the harvester's so this is behaviorally a drop-in) --


def _calc(expr: str) -> str:
    """Evaluate ARITHMETIC on numbers only (AST-gated: no names, calls, attributes -- not a generic eval)."""
    try:
        tree = ast.parse(str(expr), mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, _CALC_NODES) or (
                isinstance(node, ast.Constant) and not isinstance(node.value, (int, float))
            ):
                return "calc error: only arithmetic on numbers is allowed"
        return str(eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, {}))  # noqa: S307 (AST-gated)
    except Exception as exc:  # noqa: BLE001
        return "calc error: %s" % exc


def _is_prime(n_str: str) -> str:
    try:
        n = int(str(n_str).strip())
    except Exception:  # noqa: BLE001
        return "is_prime error: not an integer"
    if n < 2:
        return "False"
    i = 2
    while i * i <= n:
        if n % i == 0:
            return "False"
        i += 1
    return "True"


def _factor(n_str: str) -> str:
    try:
        n = int(str(n_str).strip())
    except Exception:  # noqa: BLE001
        return "factor error: not an integer"
    out = []
    m, d = abs(n), 2
    while d * d <= m:
        while m % d == 0:
            out.append(d)
            m //= d
        d += 1
    if m > 1:
        out.append(m)
    return str(out or [n])


def _run_code(code: str, tests: Sequence[str], imports: Sequence[str]) -> str:
    from python.helm import public_bench as pb

    code = (code or "").strip()
    if not code:
        return "run_code error: no code block found above the CALL"
    passed = pb._verify(code, list(tests), [], list(imports))["public_passed"]
    return "PASS (example test)" if passed else "FAIL: did not pass the example test"


# --- the governed toolbox: screen -> run -> seal -------------------------------------------------------


class GovernedToolbox:
    """Runs the deterministic tools behind the SCBE screens, sealing every call into a forward chain. The
    RCE-bearing tool (run_code) is screened before it runs; numeric tools pass through; all are sealed."""

    def __init__(self, nonce: str = "governed-tools") -> None:
        self.nonce = nonce
        self.receipts: list = []

    def _screen(self, name: str, arg: str) -> Tuple[str, str]:
        """run_code is the only RCE surface: refuse a destructive snippet (never-delete regex) or an
        ESCALATE/DENY L13 intent BEFORE running. Numeric tools are always ALLOWED."""
        if name == "run_code":
            if _DESTRUCTIVE.search(arg or ""):
                return "REFUSED", "destructive op in code (never-delete screen)"
            g = _gate(arg or "")
            if g in ("ESCALATE", "DENY"):
                return "REFUSED", "L13 intent gate: %s" % g
        return "ALLOWED", ""

    def _run(self, name: str, arg: str, problem: Optional[Dict[str, Any]], public_k: int) -> str:
        if name == "calc":
            return _calc(arg)
        if name == "is_prime":
            return _is_prime(arg)
        if name == "factor":
            return _factor(arg)
        if name == "run_code":
            tl = list((problem or {}).get("test_list", []))
            tests = tl[:public_k] if public_k else tl
            return _run_code(arg, tests, list((problem or {}).get("test_imports", [])))
        return "unknown tool: %s" % name

    def call(
        self,
        name: str,
        arg: str,
        problem: Optional[Dict[str, Any]] = None,
        public_k: int = 1,
        confirm: Optional[str] = None,
    ) -> Dict[str, Any]:
        decision, reason = self._screen(name, arg)
        result = ("REFUSED: " + reason) if decision == "REFUSED" else self._run(name, arg, problem, public_k)
        rec: dict = {
            "hop": len(self.receipts) + 1,
            "tool": name,
            "arg_sha256": _sha(arg),
            "decision": decision,
            "result": result[:300],
        }
        if confirm:
            rec["confirm"] = str(confirm)
        rec["_prev"] = self.receipts[-1]["seal"] if self.receipts else self.nonce
        rec["seal"] = _seal(rec)
        self.receipts.append(rec)
        return {"tool": name, "decision": decision, "result": result, "seal": rec["seal"]}

    def verify(self) -> bool:
        prev = self.nonce
        for r in self.receipts:
            if r.get("seal") != _seal(r) or r.get("_prev") != prev:
                return False
            prev = r["seal"]
        return True


def governed_callables(
    problem: Optional[Dict[str, Any]] = None, public_k: int = 1, box: Optional[GovernedToolbox] = None
) -> Tuple[Dict[str, Callable[[str], str]], GovernedToolbox]:
    """A drop-in for the harvester's build_tools: {name: arg->str}, each governed + sealed via a SHARED box.
    Point the harvester's ReAct tools here and its trajectory becomes governed tool use, receipt chain and
    all -- without changing the harvester's loop. Returns (callables, the box that holds the sealed trail)."""
    box = box or GovernedToolbox()

    def mk(name: str) -> Callable[[str], str]:
        return lambda arg: box.call(name, arg, problem=problem, public_k=public_k)["result"]

    return {n: mk(n) for n in _TOOL_NAMES}, box


def demo() -> Dict[str, Any]:
    """A destructive run_code is REFUSED before it runs (and sealed); the numeric tools pass + seal."""
    box = GovernedToolbox()
    bad = box.call("run_code", "import shutil\nshutil.rmtree('/important')", problem={"test_list": ["assert f() == 1"]})
    rm = box.call("run_code", "def f():\n    return 1  # rm -rf / in a comment still trips the screen")
    good = box.call("run_code", "def add(a, b):\n    return a + b", problem={"test_list": ["assert add(2, 3) == 5"]})
    return {
        "destructive_refused": bad["decision"] == "REFUSED",
        "rmrf_comment_refused": rm["decision"] == "REFUSED",
        "benign_passed": good["result"].startswith("PASS"),
        "calc": box.call("calc", "2 + 3 * 4")["result"],
        "is_prime_97": box.call("is_prime", "97")["result"],
        "factor_84": box.call("factor", "84")["result"],
        "sealed": box.verify(),
        "box": box,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    out = demo()
    print("GOVERNED TOOLS (every call gate-screened + sealed)")
    for r in out["box"].receipts:
        print("  %-9s %-9s %s" % (r["tool"], r["decision"], r["result"]))
    print()
    print(
        "destructive refused: %s | rm-rf-comment refused: %s | benign passed: %s | sealed: %s"
        % (out["destructive_refused"], out["rmrf_comment_refused"], out["benign_passed"], out["sealed"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
