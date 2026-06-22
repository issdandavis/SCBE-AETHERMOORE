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
    from . import query_dispatch, domain_router
except ImportError:  # run as a script
    import query_dispatch, domain_router


def agent_solve(task: str, ask=None, tests: Optional[List[str]] = None,
                reference: Optional[str] = None) -> Dict[str, Any]:
    # 1. deterministic dispatch (rung 0/1) -- a tool answers the question directly, no model
    hit = query_dispatch.dispatch(task)
    if hit is not None:
        return {"status": "VERIFIED_FIX", "via": "dispatch:" + hit["tool"],
                "answer": hit["answer"], "deterministic": True, "false_success_count": 0}

    # 2. verifiable code task -> router (model + tools + reference fallback + verify)
    if tests and ask is not None:
        public = tests[:1]
        hidden = tests[1:] or tests
        return domain_router.solve_routed(task, public, hidden, ask, reference=reference)

    # 3. nothing deterministic and nothing verifiable -> escalate honestly
    return {"status": "ESCALATE", "via": "no deterministic source, no verifiable task",
            "deterministic": False, "false_success_count": 0}


if __name__ == "__main__":
    # deterministic paths (no model needed)
    r1 = agent_solve("what is the 10th prime?")
    assert r1["status"] == "VERIFIED_FIX" and r1["answer"] == 29 and r1["deterministic"], r1
    r2 = agent_solve("roman numeral for 1994")
    assert r2["answer"] == "MCMXCIV", r2
    r3 = agent_solve("100 c to f")
    assert r3["answer"] == 212.0, r3
    # no source + no task -> escalate (never a fake win)
    r4 = agent_solve("write a function that balances a red-black tree")
    assert r4["status"] == "ESCALATE", r4
    print("agent_solve self-test: PASS (dispatch-first -> deterministic answers; novel -> ESCALATE)")
