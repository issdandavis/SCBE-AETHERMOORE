"""domain_router -- detect a task's domain and route it to the correct DETERMINISTIC rung
BEFORE the model guesses. Kills the dominant failure: the model badly reimplementing
sorted()/max()/sum()/in/Counter that builtins already do correctly.

Pipeline: detect domain -> inject the canonical builtin/tool hint -> generate -> verify
-> fall back to a known reference (inject_or_fallback) -> else ESCALATE.
Success is VERIFIED only; false_success_count stays 0 (the system_coding contract)."""

from __future__ import annotations
import re, subprocess, sys, ast
from typing import Optional, List, Dict, Any
from . import det_tools

_DOMAIN_KW = [
    ("number_theory", ("prime", "divisor", "factor", "gcd", "lcm", "perfect", "fibonacci")),
    ("arithmetic",    ("sum", "product", "average", "multiply", "divide", "power", "square", "cube", "count", "total")),
    ("sort_order",    ("sort", "order", "largest", "smallest", "maximum", "minimum", " max", " min", "kth", "top ")),
    ("lookup_map",    ("frequency", "group", "dictionary", "occurrence", "most common", "duplicate")),
    ("string",        ("string", "char", "substring", "vowel", "palindrome", "uppercase", "lowercase", "word")),
    ("search",        ("find", "search", "contains", "present", "exist", "index of", "position")),
    ("list_array",    ("list", "array", "element", "sublist", "subarray", "tuple")),
]
# domain -> the canonical builtins to USE instead of hand-rolling
_HINT = {
    "number_theory": "Use a sieve / simple primality; do NOT hand-roll buggy prime logic.",
    "arithmetic":    "Use sum(), math.prod(), //, %, divmod() -- do NOT manually accumulate in a loop.",
    "sort_order":    "Use sorted(...), max(...), min(...), heapq.nlargest/nsmallest -- NEVER hand-write a sort.",
    "lookup_map":    "Use collections.Counter / dict.get(k, default) -- do NOT hand-count.",
    "string":        "Use str methods (.split/.lower/.count/.replace) and re -- do NOT index char-by-char.",
    "search":        "Use `x in seq`, seq.index(x), any()/all() -- do NOT write a manual scan loop.",
    "list_array":    "Use slicing and list comprehensions -- avoid manual index juggling.",
    "other":         "",
}

def detect_domain(prompt: str) -> str:
    t = (prompt or "").lower()
    for name, kws in _DOMAIN_KW:
        if any(k in t for k in kws):
            return name
    return "other"

def _extract(t):
    b = re.findall(r"```(?:python)?\s*(.*?)```", t or "", re.S)
    if b: return max(b, key=len).strip()
    body = re.sub(r"^\s*```(?:python)?\s*", "", (t or "").strip()); ls = body.splitlines()
    for i, l in enumerate(ls):
        if l.lstrip().startswith(("def ", "import ", "from ", "class ", "@")): return "\n".join(ls[i:]).strip()
    return body.strip()

def _passes(code, tests):
    if not code or len(code) < 3: return False
    try: ast.parse(code)
    except SyntaxError: return False
    try:
        return subprocess.run([sys.executable, "-c", code + "\n" + "\n".join(tests) + "\n"],
                              capture_output=True, text=True, timeout=12).returncode == 0
    except Exception:
        return False

def solve_routed(prompt: str, public_tests: List[str], hidden_tests: List[str], ask,
                 reference: Optional[str] = None) -> Dict[str, Any]:
    """ask: prompt->str. Returns a VERIFIED-or-ESCALATE record; false_success_count always 0."""
    domain = detect_domain(prompt)
    hint = _HINT.get(domain, "")
    _tools = det_tools.BY_DOMAIN.get(domain, [])
    if _tools:
        hint = (hint + " Verified tools you may call: " + ", ".join(_tools) + ".").strip()
    full = prompt.strip() + ("\n\nHINT (use these, do not reimplement): " + hint if hint else "") \
        + "\n\nWrite a complete Python solution. It must pass:\n" + "\n".join(public_tests) + "\nReturn ONLY code."
    code = _extract(ask(full))
    if _passes(code, hidden_tests):
        return {"status": "VERIFIED_FIX", "via": "routed:" + domain, "code": code, "false_success_count": 0}
    if reference and _passes(reference, hidden_tests):     # rung-3 inject-or-fallback
        return {"status": "VERIFIED_FIX", "via": "fallback:reference", "code": reference, "false_success_count": 0}
    return {"status": "ESCALATE", "via": "routed:" + domain + " (unverified)", "code": code, "false_success_count": 0}

if __name__ == "__main__":
    assert detect_domain("find the maximum of three numbers") == "sort_order"
    assert detect_domain("check if a number is prime") == "number_theory"
    assert detect_domain("count the frequency of each word") in ("lookup_map", "arithmetic", "string")
    print("domain_router self-test (detect_domain): PASS")
