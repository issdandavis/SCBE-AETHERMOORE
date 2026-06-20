"""Dynamic Helm storylet engine.

This is the ChoiceScript/QBN layer: derive factors, choose the most salient legal
storylet, run it, fold its effect, repeat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .machine import OperatorRun, Receipt, Step, _digest, _evaluate

Factors = Dict[str, Any]
Derive = Callable[[Dict[str, Any]], Factors]
Effect = Callable[[Factors, Any], Factors]
Salience = Callable[[Factors], float]


def _no_effect(factors: Factors, result: Any) -> Factors:
    return factors


def _no_salience(factors: Factors) -> float:
    return 0.0


def _no_derive(ctx: Dict[str, Any]) -> Factors:
    return {}


@dataclass
class Storylet:
    step: Step
    effect: Effect = _no_effect
    salience: Salience = _no_salience


def run_storylets(
    objective: str,
    storylets: List[Storylet],
    context: Optional[Dict[str, Any]] = None,
    derive: Optional[Derive] = None,
    max_steps: int = 10000,
) -> OperatorRun:
    """Forward-chain over storylets until no legal storylet remains."""

    derive = derive or _no_derive
    ctx: Dict[str, Any] = {"objective": objective, "results": {}}
    ctx.update(context or {})
    ctx.setdefault("results", {})
    factors: Factors = dict(ctx.pop("factors", {}) or {})

    receipts: List[Receipt] = []
    denied: List[Dict[str, Any]] = []
    chain = _digest(["helm.storylet.v1", objective])
    approved = failed = 0
    remaining: Dict[str, Storylet] = {storylet.step.name: storylet for storylet in storylets}

    guard = 0
    while remaining and guard < max_steps:
        guard += 1
        factors = {**factors, **derive(ctx)}
        evalctx = {**ctx, **factors}

        legal = []
        for name in sorted(remaining):
            rows, unmet = _evaluate(remaining[name].step, objective, evalctx)
            if not unmet:
                legal.append((remaining[name], rows))
        if not legal:
            break

        legal.sort(key=lambda item: (-item[0].salience(factors), item[0].step.name))
        storylet, rows = legal[0]
        del remaining[storylet.step.name]

        try:
            result = storylet.step.do(objective, evalctx)
        except Exception as exc:
            chain = _digest([chain, storylet.step.name, "failed"])
            receipts.append(
                Receipt(
                    storylet.step.name,
                    storylet.step.kind,
                    "failed",
                    chain,
                    criteria=rows,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            )
            failed += 1
            continue

        digest = _digest(result)
        ctx["results"][storylet.step.name] = result
        factors = storylet.effect({**factors}, result)
        chain = _digest([chain, storylet.step.name, "approved", digest, _digest(factors)])
        receipts.append(
            Receipt(storylet.step.name, storylet.step.kind, "approved", chain, criteria=rows, result_digest=digest)
        )
        approved += 1

    for name in sorted(remaining):
        rows, unmet = _evaluate(remaining[name].step, objective, {**ctx, **factors})
        chain = _digest([chain, name, "denied"])
        receipts.append(
            Receipt(
                name,
                remaining[name].step.kind,
                "denied",
                chain,
                criteria=rows,
                reason="never became legal: " + ", ".join(unmet),
            )
        )
        denied.append({"step": name, "kind": remaining[name].step.kind, "unmet": unmet})

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
