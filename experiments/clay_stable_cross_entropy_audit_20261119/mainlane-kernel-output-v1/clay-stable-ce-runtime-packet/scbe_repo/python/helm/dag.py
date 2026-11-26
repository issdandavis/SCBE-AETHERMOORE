"""Concurrent Helm DAG runner.

Steps run as soon as their criteria pass. Independent ready steps run in the same
wave; gated steps converge after upstream results arrive.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

from .machine import Action, OperatorRun, Receipt, Step, _digest, _evaluate

Executor = Callable[[Step], Action]


def _real_executor(step: Step) -> Action:
    return step.do


def run_dag(
    objective: str,
    steps: List[Step],
    context: Optional[Dict[str, Any]] = None,
    max_workers: int = 8,
    executor: Optional[Executor] = None,
) -> OperatorRun:
    """Run steps as a concurrent dependency graph and converge at criteria gates."""

    pick = executor or _real_executor
    ctx: Dict[str, Any] = {"objective": objective, "results": {}}
    ctx.update(context or {})
    ctx.setdefault("results", {})

    receipts: List[Receipt] = []
    denied: List[Dict[str, Any]] = []
    chain = _digest(["helm.dag.v1", objective])
    approved = failed = 0
    remaining: Dict[str, Step] = {step.name: step for step in steps}

    while remaining:
        ready: List[Tuple[Step, List[Dict[str, Any]]]] = []
        blocked: Dict[str, Tuple[List[Dict[str, Any]], List[str]]] = {}
        for name in sorted(remaining):
            rows, unmet = _evaluate(remaining[name], objective, ctx)
            if unmet:
                blocked[name] = (rows, unmet)
            else:
                ready.append((remaining[name], rows))

        if not ready:
            for name in sorted(remaining):
                rows, unmet = blocked[name]
                step = remaining[name]
                chain = _digest([chain, name, "denied"])
                receipts.append(
                    Receipt(
                        name,
                        step.kind,
                        "denied",
                        chain,
                        criteria=rows,
                        reason="criteria not met: " + ", ".join(unmet),
                    )
                )
                denied.append({"step": name, "kind": step.kind, "unmet": unmet, "note": step.note})
            break

        with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(ready)))) as pool:
            futures = {pool.submit(pick(step), objective, ctx): (step, rows) for step, rows in ready}
            outcomes: List[Tuple[Step, List[Dict[str, Any]], Any, Optional[Exception]]] = []
            for future, (step, rows) in futures.items():
                try:
                    outcomes.append((step, rows, future.result(), None))
                except Exception as exc:
                    outcomes.append((step, rows, None, exc))

        for step, rows, result, exc in sorted(outcomes, key=lambda item: item[0].name):
            del remaining[step.name]
            if exc is not None:
                chain = _digest([chain, step.name, "failed"])
                receipts.append(
                    Receipt(
                        step.name,
                        step.kind,
                        "failed",
                        chain,
                        criteria=rows,
                        reason=f"{type(exc).__name__}: {exc}",
                    )
                )
                failed += 1
                continue

            digest = _digest(result)
            ctx["results"][step.name] = result
            chain = _digest([chain, step.name, "approved", digest])
            receipts.append(Receipt(step.name, step.kind, "approved", chain, criteria=rows, result_digest=digest))
            approved += 1

    return OperatorRun(
        objective=objective,
        receipts=receipts,
        results=ctx["results"],
        approval_queue=[],
        chain_digest=chain,
        autonomous_done=approved,
        failed=failed,
        denied=denied,
    )
