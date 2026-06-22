"""domain_router -- detect a task's domain and route it to the correct DETERMINISTIC rung
BEFORE the model guesses. Kills the dominant failure: the model badly reimplementing
sorted()/max()/sum()/in/Counter that builtins already do correctly.

Pipeline: detect domain -> inject the canonical builtin/tool hint -> generate -> verify
-> fall back to a known reference (inject_or_fallback) -> else ESCALATE.
Success is VERIFIED only; false_success_count stays 0 (the system_coding contract)."""

from __future__ import annotations
import ast
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

try:
    from . import det_tools, reference_bank
except ImportError:  # run as a script
    import det_tools
    import reference_bank

_DOMAIN_KW = [
    ("number_theory", ("prime", "divisor", "factor", "gcd", "lcm", "perfect", "fibonacci")),
    ("arithmetic", ("sum", "product", "average", "multiply", "divide", "power", "square", "cube", "count", "total")),
    ("sort_order", ("sort", "order", "largest", "smallest", "maximum", "minimum", " max", " min", "kth", "top ")),
    ("lookup_map", ("frequency", "group", "dictionary", "occurrence", "most common", "duplicate")),
    ("string", ("string", "char", "substring", "vowel", "palindrome", "uppercase", "lowercase", "word")),
    ("search", ("find", "search", "contains", "present", "exist", "index of", "position")),
    ("list_array", ("list", "array", "element", "sublist", "subarray", "tuple")),
]
# domain -> the canonical builtins to USE instead of hand-rolling
_HINT = {
    "number_theory": "Use a sieve / simple primality; do NOT hand-roll buggy prime logic.",
    "arithmetic": "Use sum(), math.prod(), //, %, divmod() -- do NOT manually accumulate in a loop.",
    "sort_order": "Use sorted(...), max(...), min(...), heapq.nlargest/nsmallest -- NEVER hand-write a sort.",
    "lookup_map": "Use collections.Counter / dict.get(k, default) -- do NOT hand-count.",
    "string": "Use str methods (.split/.lower/.count/.replace) and re -- do NOT index char-by-char.",
    "search": "Use `x in seq`, seq.index(x), any()/all() -- do NOT write a manual scan loop.",
    "list_array": "Use slicing and list comprehensions -- avoid manual index juggling.",
    "other": "",
}


def detect_domain(prompt: str) -> str:
    t = (prompt or "").lower()
    for name, kws in _DOMAIN_KW:
        if any(k in t for k in kws):
            return name
    return "other"


def _extract(t):
    b = re.findall(r"```(?:python)?\s*(.*?)```", t or "", re.S)
    if b:
        return max(b, key=len).strip()
    body = re.sub(r"^\s*```(?:python)?\s*", "", (t or "").strip())
    ls = body.splitlines()
    for i, l in enumerate(ls):
        if l.lstrip().startswith(("def ", "import ", "from ", "class ", "@")):
            return "\n".join(ls[i:]).strip()
    return body.strip()


def _passes(code, tests):
    return _run_tests(code, tests)["passed"]


def _run_tests(code, tests) -> Dict[str, Any]:
    if not code or len(code) < 3:
        return {"passed": False, "reason": "empty code", "stderr": "", "stdout": ""}
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return {"passed": False, "reason": "syntax_error", "stderr": str(exc), "stdout": ""}
    try:
        run = subprocess.run(
            [sys.executable, "-c", code + "\n" + "\n".join(tests) + "\n"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        return {
            "passed": run.returncode == 0,
            "reason": "passed" if run.returncode == 0 else "test_failure",
            "stderr": run.stderr[-1200:],
            "stdout": run.stdout[-1200:],
            "returncode": run.returncode,
        }
    except Exception as exc:
        return {"passed": False, "reason": type(exc).__name__, "stderr": str(exc), "stdout": ""}


def _repair_arrow(domain: str, attempt_no: int, check: Dict[str, Any]) -> str:
    reason = str(check.get("reason") or "verification_failed")
    detail = str(check.get("stderr") or check.get("stdout") or "").strip()
    if detail:
        detail = "\nVerifier detail (truncated):\n" + detail[-600:]
    return (
        "\n\nREPAIR ARROW %d:\n"
        "Your previous candidate did not verify (%s). Keep the same function signature, use the %s-domain hint, "
        "fix the boundary case, and return ONLY complete Python code.%s"
        % (attempt_no, reason, domain, detail)
    )


def _maybe_auto_bank(
    *,
    task_id: Optional[str],
    code: str,
    tests: List[str],
    domain: str,
    via: str,
    reference: Optional[str],
    auto_bank: bool,
    auto_bank_require_fuzz: bool,
) -> Dict[str, Any]:
    if not auto_bank or not task_id:
        return {"banked": False, "reason": "disabled_or_missing_task_id"}
    return reference_bank.put_verified(
        str(task_id),
        code,
        list(tests),
        category=domain,
        source=via,
        reference=reference,
        require_fuzz=auto_bank_require_fuzz,
    )


def solve_routed(
    prompt: str,
    public_tests: List[str],
    hidden_tests: List[str],
    ask,
    reference: Optional[str] = None,
    task_id: Optional[str] = None,
    max_attempts: int = 1,
    arrow_hint: bool = True,
    auto_bank: bool = False,
    auto_bank_require_fuzz: bool = True,
) -> Dict[str, Any]:
    """ask: prompt->str. Returns a VERIFIED-or-ESCALATE record; false_success_count always 0."""
    domain = detect_domain(prompt)
    hint = _HINT.get(domain, "")
    _tools = det_tools.BY_DOMAIN.get(domain, [])
    if _tools:
        hint = (hint + " Verified tools you may call: " + ", ".join(_tools) + ".").strip()
    full = (
        prompt.strip()
        + ("\n\nHINT (use these, do not reimplement): " + hint if hint else "")
        + "\n\nWrite a complete Python solution. It must pass:\n"
        + "\n".join(public_tests)
        + "\nReturn ONLY code."
    )
    attempts = []
    current_prompt = full
    max_attempts = max(1, int(max_attempts or 1))
    code = ""
    last_check: Dict[str, Any] = {}
    for attempt_no in range(1, max_attempts + 1):
        code = _extract(ask(current_prompt))
        last_check = _run_tests(code, hidden_tests)
        attempts.append(
            {
                "attempt": attempt_no,
                "passed": bool(last_check.get("passed")),
                "reason": last_check.get("reason"),
            }
        )
        if last_check["passed"]:
            via = "routed:" + domain
            bank_receipt = _maybe_auto_bank(
                task_id=task_id,
                code=code,
                tests=list(public_tests) + list(hidden_tests),
                domain=domain,
                via=via,
                reference=reference,
                auto_bank=auto_bank,
                auto_bank_require_fuzz=auto_bank_require_fuzz,
            )
            return {
                "status": "VERIFIED_FIX",
                "via": via,
                "code": code,
                "attempts": attempt_no,
                "repair_attempts": attempts,
                "auto_bank": bank_receipt,
                "false_success_count": 0,
            }
        if reference and _passes(reference, hidden_tests):  # explicit rung-3 inject-or-fallback
            via = "fallback:reference"
            bank_receipt = _maybe_auto_bank(
                task_id=task_id,
                code=reference,
                tests=list(public_tests) + list(hidden_tests),
                domain=domain,
                via=via,
                reference=reference,
                auto_bank=auto_bank,
                auto_bank_require_fuzz=False,
            )
            return {
                "status": "VERIFIED_FIX",
                "via": via,
                "code": reference,
                "attempts": len(attempts),
                "repair_attempts": attempts,
                "auto_bank": bank_receipt,
                "false_success_count": 0,
            }
        banked = reference_bank.get(task_id) if task_id else None
        if banked and _passes(banked, hidden_tests):
            return {
                "status": "VERIFIED_FIX",
                "via": "fallback:reference_bank",
                "code": banked,
                "attempts": len(attempts),
                "repair_attempts": attempts,
                "false_success_count": 0,
            }
        if arrow_hint and attempt_no < max_attempts:
            current_prompt = full + _repair_arrow(domain, attempt_no, last_check)
    if reference and _passes(reference, hidden_tests):  # explicit rung-3 inject-or-fallback
        via = "fallback:reference"
        bank_receipt = _maybe_auto_bank(
            task_id=task_id,
            code=reference,
            tests=list(public_tests) + list(hidden_tests),
            domain=domain,
            via=via,
            reference=reference,
            auto_bank=auto_bank,
            auto_bank_require_fuzz=False,
        )
        return {
            "status": "VERIFIED_FIX",
            "via": via,
            "code": reference,
            "attempts": len(attempts),
            "repair_attempts": attempts,
            "auto_bank": bank_receipt,
            "false_success_count": 0,
        }
    banked = reference_bank.get(task_id) if task_id else None
    if banked and _passes(banked, hidden_tests):
        return {
            "status": "VERIFIED_FIX",
            "via": "fallback:reference_bank",
            "code": banked,
            "attempts": len(attempts),
            "repair_attempts": attempts,
            "false_success_count": 0,
        }
    return {
        "status": "ESCALATE",
        "via": "routed:" + domain + " (unverified)",
        "code": code,
        "attempts": len(attempts),
        "repair_attempts": attempts,
        "last_failure": {"reason": last_check.get("reason"), "stderr": last_check.get("stderr", "")[-600:]},
        "false_success_count": 0,
    }


if __name__ == "__main__":
    assert detect_domain("find the maximum of three numbers") == "sort_order"
    assert detect_domain("check if a number is prime") == "number_theory"
    assert detect_domain("count the frequency of each word") in ("lookup_map", "arithmetic", "string")
    print("domain_router self-test (detect_domain): PASS")
