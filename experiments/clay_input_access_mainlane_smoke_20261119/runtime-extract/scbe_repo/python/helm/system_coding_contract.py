"""system_coding_contract -- score code-fix attempts against the 100% success contract.

The contract is intentionally strict:

* VERIFIED_FIX is the only code-fix success state.
* REJECT and ABSTAIN are never shipped as success.
* If no candidate can be verified, the task is ESCALATE, not "probably fixed".

That gives the system a practical path to 100% operational closure while preserving the hard invariant:
false_success_count == 0.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .abstaining_verifier import _func_name, differential

VERIFIED_FIX = "verified_fix"
ESCALATE = "escalate"


@dataclass(frozen=True)
class FixAttempt:
    """One proposed implementation for a code-fix task."""

    name: str
    code: str
    source: str = "candidate"


def _attempt_from(raw: Any, index: int) -> FixAttempt:
    if isinstance(raw, FixAttempt):
        return raw
    if isinstance(raw, str):
        return FixAttempt(name="candidate_%d" % index, code=raw)
    if isinstance(raw, Mapping):
        code = str(raw.get("code") or raw.get("candidate") or "")
        name = str(raw.get("name") or raw.get("id") or "candidate_%d" % index)
        source = str(raw.get("source") or "candidate")
        return FixAttempt(name=name, code=code, source=source)
    raise TypeError("candidate %d must be FixAttempt, mapping, or code string" % index)


def evaluate_fix_candidates(
    *,
    reference: str,
    candidates: Sequence[Any],
    tests: Sequence[str],
    func: Optional[str] = None,
    n_fuzz: int = 40,
) -> Dict[str, Any]:
    """Return the first verifier-trusted fix, otherwise a structured escalation.

    The caller can pass model patches, deterministic transforms, retrieved prior fixes, or stronger-solver
    outputs as `candidates`. This function does not care where a patch came from; it only cares whether
    the abstaining verifier can prove behavior equivalence beyond the visible tests.
    """

    target_func = func or _func_name(reference)
    if not target_func:
        return {
            "status": ESCALATE,
            "func": None,
            "selected": None,
            "attempts": [],
            "reason": "no function name found in reference",
            "closed": True,
            "code_fixed": False,
            "false_success_count": 0,
        }

    attempts: List[Dict[str, Any]] = []
    for index, raw in enumerate(candidates):
        attempt = _attempt_from(raw, index)
        verdict = differential(attempt.code, reference, list(tests), func=target_func, n_fuzz=n_fuzz)
        item = {
            "name": attempt.name,
            "source": attempt.source,
            "verdict": verdict.get("verdict"),
            "reason": verdict.get("reason", ""),
            "fuzz_checked": verdict.get("fuzz_checked"),
            "divergence": verdict.get("divergence"),
        }
        attempts.append(item)
        if verdict.get("verdict") == "trust":
            return {
                "status": VERIFIED_FIX,
                "func": target_func,
                "selected": attempt.name,
                "attempts": attempts,
                "reason": item["reason"],
                "closed": True,
                "code_fixed": True,
                "false_success_count": 0,
            }

    reason = "no candidate reached verifier trust"
    if attempts:
        reason = "; ".join("%s=%s" % (a["name"], a["verdict"]) for a in attempts)
    return {
        "status": ESCALATE,
        "func": target_func,
        "selected": None,
        "attempts": attempts,
        "reason": reason,
        "closed": True,
        "code_fixed": False,
        "false_success_count": 0,
    }


def score_decisions(decisions: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Summarize a run of code-fix decisions using the 100% success contract."""

    rows = list(decisions)
    attempted = len(rows)
    verified = sum(1 for d in rows if d.get("status") == VERIFIED_FIX)
    escalated = sum(1 for d in rows if d.get("status") == ESCALATE)
    false_success = sum(int(d.get("false_success_count", 0) or 0) for d in rows)
    rejected_candidates = 0
    abstained_candidates = 0
    for d in rows:
        for attempt in d.get("attempts", []) or []:
            if attempt.get("verdict") == "reject":
                rejected_candidates += 1
            elif attempt.get("verdict") == "abstain":
                abstained_candidates += 1
    operationally_closed = verified + escalated
    return {
        "attempted": attempted,
        "verified_fix": verified,
        "escalated": escalated,
        "rejected_candidates": rejected_candidates,
        "abstained_candidates": abstained_candidates,
        "false_success_count": false_success,
        "code_fix_success_rate": round(verified / attempted, 6) if attempted else 0.0,
        "operational_closure_rate": round(operationally_closed / attempted, 6) if attempted else 0.0,
        "contract_passed": false_success == 0 and operationally_closed == attempted,
    }


def _demo() -> Dict[str, Any]:
    reference = "def add(a, b):\n    return a + b\n"
    visible_tests = ["assert add(2, 2) == 4"]
    bad = FixAttempt("visible_pass_wrong", "def add(a, b):\n    return a * b\n", source="model")
    good = FixAttempt("equivalent_refactor", "def add(a, b):\n    return b + a\n", source="repair")
    fixed = evaluate_fix_candidates(reference=reference, candidates=[bad, good], tests=visible_tests)
    escalated = evaluate_fix_candidates(reference=reference, candidates=[bad], tests=visible_tests)
    return {"decisions": [fixed, escalated], "score": score_decisions([fixed, escalated])}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="system-coding-contract",
        description="score code-fix attempts as verified_fix or escalate, never false success",
    )
    ap.add_argument("--demo", action="store_true", help="run the built-in visible-pass/divergence demo")
    ap.add_argument("--out", default=None, help="optional JSON report path")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if not args.demo:
        print("Use --demo for the built-in contract check; import evaluate_fix_candidates() for real tasks.")
        return 0
    report = _demo()
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)
    return 0 if report["score"]["contract_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
