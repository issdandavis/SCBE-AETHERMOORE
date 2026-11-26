"""agent_solve -- the live loop, deterministic-FIRST.

Order of resolution (the ladder of knownness):
  1. query_dispatch  -- tool-shaped question -> deterministic answer, NO model
  2. domain_router    -- code task (tests given) -> model + named tools + reference fallback + verify
  3. ESCALATE         -- no deterministic source and no verifiable task; never a fake win

The model is the LAST resort; nothing returns success that wasn't verified or deterministic.
false_success_count stays 0 by construction (system_coding contract)."""

from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    from . import calc
    from . import domain_router
    from . import query_dispatch
except ImportError:  # run as a script
    import calc
    import domain_router
    import query_dispatch


def agent_solve(
    task: str,
    ask=None,
    tests: Optional[List[str]] = None,
    reference: Optional[str] = None,
    task_id: Optional[str] = None,
    max_attempts: int = 1,
    arrow_hint: bool = True,
    auto_bank: bool = False,
    auto_bank_require_fuzz: bool = True,
) -> Dict[str, Any]:
    # 1. deterministic dispatch (rung 0/1) -- a named tool answers the question directly, no model
    hit = query_dispatch.dispatch(task)
    if hit is not None:
        return {
            "status": "VERIFIED_FIX",
            "via": "dispatch:" + hit["tool"],
            "answer": hit["answer"],
            "deterministic": True,
            "false_success_count": 0,
        }

    # 1b. the fancy calculator -- hard arithmetic / estimation offloaded to a deterministic tool
    c = calc.try_calc(task)
    if c is not None:
        return {
            "status": "VERIFIED_FIX",
            "via": "calc:" + c["how"],
            "answer": c["answer"],
            "deterministic": True,
            "false_success_count": 0,
        }

    # 2. verifiable code task -> router (model + tools + reference fallback + verify)
    if tests and ask is not None:
        public = tests[:1]
        hidden = tests[1:] or tests
        return domain_router.solve_routed(
            task,
            public,
            hidden,
            ask,
            reference=reference,
            task_id=task_id,
            max_attempts=max_attempts,
            arrow_hint=arrow_hint,
            auto_bank=auto_bank,
            auto_bank_require_fuzz=auto_bank_require_fuzz,
        )

    # 3. nothing deterministic and nothing verifiable -> escalate honestly
    return {
        "status": "ESCALATE",
        "via": "no deterministic source, no verifiable task",
        "deterministic": False,
        "false_success_count": 0,
    }


if __name__ == "__main__":
    # deterministic paths (no model needed)
    r1 = agent_solve("what is the 10th prime?")
    assert r1["status"] == "VERIFIED_FIX" and r1["answer"] == 29 and r1["deterministic"], r1
    r2 = agent_solve("roman numeral for 1994")
    assert r2["answer"] == "MCMXCIV", r2
    r3 = agent_solve("100 c to f")
    assert r3["answer"] == 212.0, r3
    # the fancy calculator rung: hard arithmetic offloaded, no model
    r4 = agent_solve("what is 37 to the power of 12")
    assert r4["answer"] == 37**12 and r4["via"].startswith("calc"), r4
    r5 = agent_solve("estimate 123456 times 789012")
    assert r5["answer"] == 97000000000, r5
    # no source + no task -> escalate (never a fake win)
    r6 = agent_solve("write a function that balances a red-black tree")
    assert r6["status"] == "ESCALATE", r6
    print("agent_solve self-test: PASS (dispatch -> calc -> router; novel -> ESCALATE)")
