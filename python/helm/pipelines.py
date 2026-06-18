"""A real end-to-end operator pipeline: helm criteria wired to the actual SCBE tools.

``code_ship_pipeline(objective)`` runs:

  build   — codeforge.forge: the AI writes + verifies the program (real)
  review  — the governance gate (scbe ``pipeline_quick_score``) judges the objective (real)
  stage   — assemble the verified multi-language artifact; APPROVED ONLY IF the build
            verified AND the gate did not flag AND the budget switch is on
  publish — push externally; a genuine human gate (criterion ``human("approved_publish")``)

No stub criteria: ``build.verified`` comes from codeforge actually verifying, and
``review.gate_ok`` from the real gate's decision. Everything reversible/verifiable runs
autonomously under those real criteria; the external, irreversible publish waits for a
human signal.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .machine import OperatorRun, Step, flag, human, run_objective, upstream


def _build(objective: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    from python.codeforge import forge

    cat = forge(objective)
    result = cat.result or {}
    return {
        "ok": cat.ok,
        "verified": bool(result.get("verified")) if cat.ok else False,
        "source": result.get("source") if cat.ok else None,
        "forge_chain": cat.chain_digest,
    }


def _review(objective: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from scbe import pipeline_quick_score
    except Exception as exc:  # gate unavailable -> fail safe: not ok, needs attention
        return {"decision": "UNAVAILABLE", "gate_ok": False, "note": f"gate import failed: {exc}"}
    score = pipeline_quick_score(objective)
    decision = score.get("decision", "ALLOW")
    return {"decision": decision, "gate_ok": decision == "ALLOW", "h_eff": score.get("H_eff")}


def _stage(objective: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    build = ctx["results"]["build"]
    return {
        "staged": True,
        "languages": sorted((build.get("source") or {}).keys()),
        "from_forge": build.get("forge_chain"),
    }


def _publish(objective: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"published": True, "artifact": ctx["results"]["stage"]}


def code_ship_pipeline(objective: str, context: Optional[Dict[str, Any]] = None) -> OperatorRun:
    """Run the full build -> review -> stage -> publish loop with real criteria."""
    steps = [
        Step("build", "build", _build),
        Step("review", "verify", _review),
        Step(
            "stage",
            "deploy",
            _stage,
            criteria=(
                upstream("build", "verified", True),  # codeforge actually verified the code
                upstream("review", "gate_ok", True),  # the governance gate did not flag the objective
                flag("within_budget"),  # the operator's budget switch is on
            ),
        ),
        Step(
            "publish",
            "publish",
            _publish,
            criteria=(
                upstream("stage", "staged", True),  # can't publish what wasn't staged
                human("approved_publish"),  # external/irreversible -> a real human gate
            ),
        ),
    ]
    return run_objective(objective, steps, context=context)
