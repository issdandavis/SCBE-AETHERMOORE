"""Runnable Helm demo.

Run with:

    python -m python.helm.demo

The demo is intentionally stdlib-only and side-effect free. It shows the user
what Helm buys them right now: playability checking, dry-run proof, concurrent
workflow execution, storylet selection, and a receipt chain.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from . import Step, Storylet, dry_run, flag, run_dag, run_storylets, static_check, upstream


def _workflow_steps() -> List[Step]:
    def collect(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"inputs": 3, "ready": True}

    def build(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"verified": True, "coverage": 0.92}

    def package(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "bundle": "workflow-snapshot.zip",
            "verified": context["results"]["build"]["verified"],
        }

    return [
        Step("collect", "research", collect),
        Step("build", "build", build, criteria=(upstream("collect", "ready", True),)),
        Step("package", "package", package, criteria=(upstream("build", "verified", True), flag("ship_approved"))),
    ]


def _storylets() -> List[Storylet]:
    def discover(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"notes": 2}

    def draft(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"drafted": True, "based_on_notes": context["results"]["discover"]["notes"]}

    def polish(objective: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"polished": context["results"]["draft"]["drafted"]}

    return [
        Storylet(Step("discover", "research", discover), salience=lambda factors: 10.0),
        Storylet(Step("draft", "draft", draft, criteria=(flag("has_notes"),)), salience=lambda factors: 5.0),
        Storylet(
            Step("polish", "edit", polish, criteria=(upstream("draft", "drafted", True),)), salience=lambda factors: 1.0
        ),
    ]


def _derive_story_factors(context: Dict[str, Any]) -> Dict[str, Any]:
    return {"has_notes": "discover" in context["results"]}


def _receipt_rows(receipts: Iterable[Any]) -> List[Dict[str, Any]]:
    return [{"step": receipt.step, "status": receipt.status, "kind": receipt.kind} for receipt in receipts]


def run_demo() -> Dict[str, Any]:
    """Run the side-effect-free demo and return machine-readable results."""

    steps = _workflow_steps()
    static = static_check(steps)
    proof = dry_run("ship a workflow snapshot", steps)
    real = run_dag("ship a workflow snapshot", steps, context={"ship_approved": True})
    story = run_storylets("write a support scene", _storylets(), derive=_derive_story_factors)

    broken = [Step("ship", "deploy", lambda objective, context: {"ok": True}, criteria=(upstream("missing", "ok"),))]
    broken_report = static_check(broken)

    return {
        "playability_ok": static.ok,
        "playability_errors": static.errors,
        "dry_run": {
            "approved": proof.approved,
            "denied": proof.denied_count,
            "chain": proof.chain_digest,
            "receipts": _receipt_rows(proof.receipts),
        },
        "dag_run": {
            "approved": real.approved,
            "denied": real.denied_count,
            "chain": real.chain_digest,
            "receipts": _receipt_rows(real.receipts),
        },
        "storylet_run": {
            "approved": story.approved,
            "denied": story.denied_count,
            "chain": story.chain_digest,
            "order": [receipt.step for receipt in story.receipts if receipt.status == "approved"],
        },
        "broken_graph": {
            "ok": broken_report.ok,
            "errors": broken_report.errors,
        },
    }


def render_demo(result: Dict[str, Any]) -> str:
    """Render the demo in a compact human-readable form."""

    lines = [
        "Helm demo: AI workflow playability checker",
        f"playability: {'OK' if result['playability_ok'] else 'FAILED'}",
        (
            "dry-run proof: "
            f"{result['dry_run']['approved']} approved, "
            f"{result['dry_run']['denied']} denied, chain {result['dry_run']['chain']}"
        ),
        (
            "real DAG run: "
            f"{result['dag_run']['approved']} approved, "
            f"{result['dag_run']['denied']} denied, chain {result['dag_run']['chain']}"
        ),
        "storylet order: " + " -> ".join(result["storylet_run"]["order"]),
        "broken graph caught: " + "; ".join(result["broken_graph"]["errors"]),
        "",
        "json:",
        json.dumps(result, indent=2, sort_keys=True),
    ]
    return "\n".join(lines)


def main() -> int:
    print(render_demo(run_demo()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
