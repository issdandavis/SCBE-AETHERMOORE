"""Playability checks for Helm DAGs.

This is the Quicktest/Randomtest layer: static descriptors catch broken edges
before execution, and the dry runner auto-fills declared gates while replacing
real actions with deterministic mock results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from .dag import run_dag
from .machine import Action, OperatorRun, Step


@dataclass
class PlayabilityReport:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def static_check(steps: Sequence[Step]) -> PlayabilityReport:
    """Check duplicate names and structured upstream references."""

    errors: List[str] = []
    warnings: List[str] = []
    names = [step.name for step in steps]
    seen = set()
    duplicates = sorted({name for name in names if name in seen or seen.add(name)})
    for name in duplicates:
        errors.append(f"duplicate step name: {name}")

    name_set = set(names)
    for step in steps:
        for criterion in step.criteria:
            descriptor = criterion.descriptor
            if descriptor is None:
                warnings.append(f"{step.name}.{criterion.name}: opaque predicate; dry-run cannot infer inputs")
                continue
            if descriptor.kind == "upstream":
                if descriptor.target not in name_set:
                    errors.append(f"{step.name}.{criterion.name}: missing upstream step {descriptor.target}")
                if descriptor.target == step.name:
                    errors.append(f"{step.name}.{criterion.name}: self-dependency")

    return PlayabilityReport(ok=not errors, errors=errors, warnings=warnings)


def _context_from_descriptors(steps: Sequence[Step]) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    for step in steps:
        for criterion in step.criteria:
            descriptor = criterion.descriptor
            if descriptor is None:
                continue
            if descriptor.kind in {"flag", "human"} and descriptor.key:
                context[descriptor.key] = True
    return context


def _mock_executor(step: Step) -> Action:
    def action(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"mocked": True, "step": step.name, "kind": step.kind}
        for other in context.get("playability_steps", []):
            for criterion in getattr(other, "criteria", ()):
                descriptor = criterion.descriptor
                if descriptor and descriptor.kind == "upstream" and descriptor.target == step.name:
                    result[descriptor.key] = descriptor.equals
        return result

    return action


def dry_run(
    objective: str,
    steps: Sequence[Step],
    context: Dict[str, Any] | None = None,
    max_workers: int = 8,
) -> OperatorRun:
    """Run a graph without invoking real Step.do bodies."""

    report = static_check(steps)
    if not report.ok:
        raise ValueError("; ".join(report.errors))
    merged = _context_from_descriptors(steps)
    merged.update(context or {})
    merged["playability_steps"] = list(steps)
    return run_dag(objective, list(steps), context=merged, max_workers=max_workers, executor=_mock_executor)
