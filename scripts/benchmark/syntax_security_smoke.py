"""Syntax + security smoke harness for generated code.

WHAT THIS MEASURES, PLAINLY
---------------------------
Whether a retry prompted by a **local syntax parse and a regex security scan**
improves generated code compared with the baseline output.

WHAT THIS DOES NOT MEASURE
--------------------------
**SCBE.** Nothing in this file touches the 14-layer pipeline, hyperbolic
distance, PBHG, TLCFI, the Langues metric, or ``/v1/authorize``. The gate is
``ast.parse`` plus ``detect_security_flags``, and the score it emits takes
exactly two values. Any figure produced here is a syntax checker's figure.

This file was renamed from ``scbe_code_eval.py`` on 2026-08-03 for that reason.
It shipped in PR #989 carrying ``scbe_`` in its module name, its function name,
and three record fields, which made its output read as SCBE evidence. It is a
useful smoke harness; it was mislabelled. Two independent reviews reached that
conclusion the same day.

To make this an actual SCBE benchmark, replace ``syntax_security_check`` with a
call to the real authorize path -- either the validation helpers behind
``/v1/authorize`` or live requests against the running API -- and rename the
module back at that point, not before.

Usage examples
--------------
1) Dry-run with built-in stub model::

    python scripts/benchmark/syntax_security_smoke.py --dry-run

2) Emit JSON results using fixture prompts::

    python scripts/benchmark/syntax_security_smoke.py \
        --prompts tests/fixtures/code_eval_prompts.json \
        --output artifacts/syntax_security_smoke_results.json

The default stub model intentionally returns imperfect but valid code for some
cases so the harness path can be exercised before wiring a real provider.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PromptCase:
    id: str
    category: str
    prompt: str
    entrypoint: str
    assertions: List[str]


@dataclass
class CodeCheckResult:
    syntax_ok: bool
    exec_ok: bool
    tests_passed: bool
    security_flags: List[str]
    error: Optional[str] = None


@dataclass
class EvalRecord:
    prompt_id: str
    category: str
    prompt: str
    baseline_output: str
    baseline_checks: Dict[str, Any]
    smoke_decision: str
    smoke_score: float
    smoke_explanation: Dict[str, Any]
    retry_used: bool
    final_output: str
    final_checks: Dict[str, Any]


def load_prompt_cases(path: str) -> List[PromptCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [PromptCase(**item) for item in data]


def detect_security_flags(code: str) -> List[str]:
    flags: List[str] = []
    patterns = {
        "uses_exec": r"\bexec\s*\(",
        "uses_eval": r"\beval\s*\(",
        "uses_os_system": r"\bos\.system\s*\(",
        "uses_subprocess": r"\bsubprocess\.",
        "uses_pickle": r"\bpickle\.",
        "uses_input": r"\binput\s*\(",
    }
    for name, pattern in patterns.items():
        if re.search(pattern, code):
            flags.append(name)
    return flags


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "Exception": Exception,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "str": str,
    "sum": sum,
    "ValueError": ValueError,
    "type": type,
    "isinstance": isinstance,
    "__import__": __import__,
    "eval": eval,
}


def run_code_checks(code: str, assertions: List[str]) -> CodeCheckResult:
    security_flags = detect_security_flags(code)

    try:
        ast.parse(code)
    except SyntaxError as exc:
        return CodeCheckResult(
            syntax_ok=False,
            exec_ok=False,
            tests_passed=False,
            security_flags=security_flags,
            error=f"SyntaxError: {exc}",
        )

    scope: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    try:
        exec(code, scope, scope)
    except Exception as exc:
        return CodeCheckResult(
            syntax_ok=True,
            exec_ok=False,
            tests_passed=False,
            security_flags=security_flags,
            error=f"ExecutionError: {exc}",
        )

    try:
        for assertion in assertions:
            exec(assertion, scope, scope)
    except Exception as exc:
        return CodeCheckResult(
            syntax_ok=True,
            exec_ok=True,
            tests_passed=False,
            security_flags=security_flags,
            error=f"AssertionError: {exc}",
        )

    return CodeCheckResult(
        syntax_ok=True,
        exec_ok=True,
        tests_passed=True,
        security_flags=security_flags,
        error=None,
    )


class StubModel:
    """Simple model adapter for local smoke runs.

    Replace this with a real adapter later. The callable contract is:
        generate(prompt: str) -> str
    """

    def generate(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "reverse_string" in prompt_lower:
            return "def reverse_string(s: str) -> str:\n    return s[::-1]\n"
        if "safe_divide" in prompt_lower:
            return (
                "def safe_divide(a: float, b: float):\n" "    if b == 0:\n" "        return None\n" "    return a / b\n"
            )
        if "extract_name" in prompt_lower:
            return (
                "import json\n"
                "def extract_name(payload: str):\n"
                "    try:\n"
                "        data = json.loads(payload)\n"
                "    except Exception:\n"
                "        return None\n"
                "    return data.get('name')\n"
            )
        if "factorial" in prompt_lower and "revise" not in prompt_lower:
            return (
                "def factorial(n: int) -> int:\n"
                "    if n == 0:\n"
                "        return 1\n"
                "    return n * factorial(n - 1)\n"
            )
        if "factorial" in prompt_lower and "revise" in prompt_lower:
            return (
                "def factorial(n: int) -> int:\n"
                "    if n < 0:\n"
                "        raise ValueError('n must be non-negative')\n"
                "    if n == 0:\n"
                "        return 1\n"
                "    return n * factorial(n - 1)\n"
            )
        if "run_expr" in prompt_lower or ("eval" in prompt_lower and "revise" not in prompt_lower):
            # Intentionally insecure - triggers the regex security flag, forces retry
            return "def run_expr(expr: str) -> object:\n    return eval(expr)\n"
        if "run_expr" in prompt_lower and "revise" in prompt_lower:
            # After the smoke-gate retry: sandboxed version
            return (
                "def run_expr(expr: str) -> object:\n"
                "    _ALLOWED = {'__builtins__': {}}\n"
                "    return eval(expr, _ALLOWED)\n"
            )
        return "def placeholder():\n    return None\n"


def syntax_security_check(code: str, prompt: str) -> Dict[str, Any]:
    """Local syntax parse + regex security scan. NOT an SCBE authorize call.

    Emits the same field shape as ``/v1/authorize`` (decision / score /
    explanation) so a caller can be swapped over later, but the decision comes
    from ``ast.parse`` and ``detect_security_flags`` only, and ``score`` takes
    exactly two values. Do not report anything from this function as an SCBE
    result.

    This keeps the benchmark usable without a running API server while preserving
    the same key fields that matter for evaluation.
    """
    security_flags = detect_security_flags(code)
    syntax_ok = True
    try:
        ast.parse(code)
    except SyntaxError:
        syntax_ok = False

    if security_flags or not syntax_ok:
        decision = "QUARANTINE"
        score = 0.35
    else:
        decision = "ALLOW"
        score = 0.82

    return {
        "decision": decision,
        "score": score,
        "explanation": {
            "prompt_excerpt": prompt[:120],
            "security_flags": security_flags,
            "syntax_ok": syntax_ok,
        },
    }


def evaluate_case(case: PromptCase, model: Any) -> EvalRecord:
    baseline_output = model.generate(case.prompt)
    baseline_checks = asdict(run_code_checks(baseline_output, case.assertions))

    smoke_result = syntax_security_check(baseline_output, case.prompt)
    retry_used = smoke_result["decision"] != "ALLOW"

    final_output = baseline_output
    if retry_used:
        revised_prompt = (
            case.prompt
            + "\nRevise for safety, correctness, and edge-case handling."
            + f"\nsmoke decision: {smoke_result['decision']}"
            + f"\nsmoke explanation: {json.dumps(smoke_result['explanation'], sort_keys=True)}"
        )
        final_output = model.generate(revised_prompt)

    final_checks = asdict(run_code_checks(final_output, case.assertions))

    return EvalRecord(
        prompt_id=case.id,
        category=case.category,
        prompt=case.prompt,
        baseline_output=baseline_output,
        baseline_checks=baseline_checks,
        smoke_decision=smoke_result["decision"],
        smoke_score=float(smoke_result["score"]),
        smoke_explanation=smoke_result["explanation"],
        retry_used=retry_used,
        final_output=final_output,
        final_checks=final_checks,
    )


def summarize(records: List[EvalRecord]) -> Dict[str, Any]:
    total = len(records)
    baseline_pass = sum(1 for r in records if r.baseline_checks["tests_passed"])
    final_pass = sum(1 for r in records if r.final_checks["tests_passed"])
    retries = sum(1 for r in records if r.retry_used)
    quarantines = sum(1 for r in records if r.smoke_decision == "QUARANTINE")
    denies = sum(1 for r in records if r.smoke_decision == "DENY")
    allows = sum(1 for r in records if r.smoke_decision == "ALLOW")

    return {
        "total": total,
        "baseline_pass_rate": round(baseline_pass / total, 3) if total else 0.0,
        "final_pass_rate": round(final_pass / total, 3) if total else 0.0,
        "retry_rate": round(retries / total, 3) if total else 0.0,
        "decision_counts": {
            "ALLOW": allows,
            "QUARANTINE": quarantines,
            "DENY": denies,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run syntax + security smoke harness (NOT an SCBE evaluation)")
    parser.add_argument(
        "--prompts",
        default="tests/fixtures/code_eval_prompts.json",
        help="Path to prompt fixture JSON",
    )
    parser.add_argument(
        "--output",
        default="artifacts/syntax_security_smoke_results.json",
        help="Path to write JSON results",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only",
    )
    args = parser.parse_args()

    cases = load_prompt_cases(args.prompts)
    model = StubModel()
    records = [evaluate_case(case, model) for case in cases]
    summary = summarize(records)

    payload = {
        "summary": summary,
        "records": [asdict(r) for r in records],
    }

    if args.dry_run:
        print(json.dumps(payload["summary"], indent=2))
        return 0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
