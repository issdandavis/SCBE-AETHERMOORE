"""code_factory: the warehouse-topology orchestrator -- a fulfillment center for jobs.

Modeled on a distribution center (e.g. Nintendo's North Bend, WA: ~20,000 orders/day on ~400 people --
because it is mostly SYSTEMS, with a few managers watching the conveyors). The conveyors do the work;
people are mostly tech staff keeping it running + managers handing out tasks. So here:

    GATE        (Policy)         -- the shop owner's permission rules (refuse unpermitted)
    CONVEYOR    (triage/route)   -- sort each job to its station: compute | classify | judge
    STATION     (cheap worker)   -- a WEAK model / deterministic backend does the narrow task
    QC          (check output)   -- is the output well-formed + usable? (the inspection lane)
    SHIP                          -- QC pass -> the verified result leaves the dock
    MANAGER     (on EXCEPTION)   -- QC fail -> summon a CAPABLE model to redo just that station

The economics (the whole point): cost scales with the MANAGER-CALL RATE, not throughput. A good
factory ships most jobs straight off cheap stations and only rarely wakes a manager. We measure that
rate alongside accuracy + safety, so "the model is a router-manager" becomes "and here is how few
managers you actually need."

Builds on process_router (gate/triage/executors); this adds the QC + ship/escalate conveyor + metric.

    python -m python.scbe.code_factory                      # reference oracle (validates harness)
    python -m python.scbe.code_factory --station qwen2.5-coder:1.5b --manager qwen2.5-coder:3b
"""

from __future__ import annotations

import argparse
from typing import Callable, Dict, Optional, Sequence

from python.helm.reasoning_ladder import _extract_answer

from .process_router import (
    EXECUTORS,
    JOBS,
    Ask,
    Policy,
    _correct,
    make_ask,
    reference_ask,
    triage_rules,
)


def qc_ok(kind: str, out: str) -> bool:
    """Well-formedness only: a compute result must be numeric; everything else non-empty. Necessary
    but NOT sufficient -- a sealed package can still hold the wrong item (see `verify`)."""
    if not out:
        return False
    if kind == "compute":
        try:
            float(out)
            return True
        except ValueError:
            return False
    return True


def verify(kind: str, prompt: str, out: str, ask: Ask) -> bool:
    """The real inspection lane: QC = a verification where one exists, not just well-formedness.
    classify -> deterministic sieve, always trustworthy.
    compute  -> DIFFERENTIAL cross-check: the executed code's answer must AGREE with the model's
                direct answer (two independent methods). Agreement is not proof, but a DISAGREEMENT
                is a real 'this station is unsure' signal -> summon the manager.
    judge    -> only well-formedness (no cheap runtime verifier exists)."""
    if not qc_ok(kind, out):
        return False
    if kind == "classify":
        return True
    if kind == "compute":
        direct = _extract_answer(ask(prompt + "\n\nAnswer with ONLY the final number, nothing else."))
        return bool(direct) and _correct(out, direct)
    return True


class CodeFactory:
    """gate -> conveyor -> station -> QC -> ship | summon manager. The manager (a capable model) is
    woken ONLY when QC fails, and only redoes that one station."""

    def __init__(self, policy: Optional[Policy] = None, router: Callable[[str, Ask], str] = triage_rules) -> None:
        self.policy = policy or Policy()
        self.router = router

    def fulfill(self, prompt: str, station_ask: Ask, manager_ask: Ask) -> Dict[str, object]:
        if not self.policy.permits(prompt):  # GATE
            return {"out": "REFUSED", "manager": False, "kind": "refused"}
        kind = self.router(prompt, station_ask)  # CONVEYOR
        out = EXECUTORS.get(kind, EXECUTORS["judge"])(prompt, station_ask)  # STATION (cheap)
        if verify(kind, prompt, out, station_ask):  # QC = real verification
            return {"out": out, "manager": False, "kind": kind}  # SHIP
        out = EXECUTORS.get(kind, EXECUTORS["judge"])(prompt, manager_ask)  # EXCEPTION -> MANAGER redoes it
        return {"out": out, "manager": True, "kind": kind}


def run_factory(
    jobs: Sequence[Dict[str, str]],
    station_ask: Ask,
    manager_ask: Ask,
    router: Callable[[str, Ask], str] = triage_rules,
) -> Dict[str, object]:
    """Ship every job; report accuracy, safety, and the MANAGER-CALL RATE (the economics)."""
    factory = CodeFactory(router=router)
    correct = unsafe = managers = 0
    for j in jobs:
        r = factory.fulfill(j["prompt"], station_ask, manager_ask)
        out = str(r["out"])
        if _correct(out, j["answer"]):
            correct += 1
        if j["answer"] == "REFUSED" and out != "REFUSED":
            unsafe += 1
        if r["manager"]:
            managers += 1
    n = len(jobs)
    return {
        "correct": correct,
        "of": n,
        "acc": round(correct / n, 3),
        "unsafe": unsafe,
        "manager_calls": managers,
        "manager_rate": round(managers / n, 3),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-code-factory", description="warehouse-topology job fulfillment")
    ap.add_argument("--station", default=None, help="cheap worker model (omit for reference oracle)")
    ap.add_argument("--manager", default=None, help="capable model summoned on QC failure (defaults to station)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    station = make_ask(model=a.station) if a.station else reference_ask
    manager = make_ask(model=a.manager) if a.manager else station
    res = run_factory(JOBS, station, manager)
    print(
        "CODE FACTORY  (%d jobs)  station=%s  manager=%s\n"
        % (len(JOBS), a.station or "oracle", a.manager or a.station or "oracle")
    )
    print("  shipped correct : %d/%d  acc=%.3f" % (res["correct"], res["of"], res["acc"]))
    print("  unsafe          : %d" % res["unsafe"])
    print(
        "  MANAGER CALLS    : %d/%d  rate=%.3f   <- the economics (few = cheap)"
        % (res["manager_calls"], res["of"], res["manager_rate"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
