"""Evaluate the SCBE view-dependent token overlay worth gate.

This script produces a small, repeatable artifact that shows whether the
overlay is useful enough to keep developing. It intentionally tests the
overlay as a semantic/router layer over conventional payload references.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ai_orchestration.search_field import trace_candidate
from src.interop.view_token_envelope import (
    ViewFrame,
    assess_overlay_worth,
    create_view_token_envelope,
    resolve_frame,
)


def _payload() -> dict[str, Any]:
    return {
        "mission": "cross_platform_interpretation",
        "candidate_id": "view-token-ko-dr-routing-v1",
        "canonical_formats": ["sysmlv2", "protobuf", "xtce", "openapi"],
        "intent": "route candidate without changing canonical payload semantics",
        "transform": "control_frame_to_structure_frame",
    }


def evaluate() -> dict[str, Any]:
    frame_a = ViewFrame("KO", "control_flow", "sysmlv2://scbe/view-token/control")
    frame_b = ViewFrame("DR", "structure_verification", "protobuf://scbe/view-token/structure")
    envelope = create_view_token_envelope(
        _payload(),
        frame_a,
        frame_b,
        payload_formats=("sysmlv2", "protobuf", "xtce", "openapi"),
        critical=True,
    )
    resolved_a, decision_a = resolve_frame(envelope, "A")
    resolved_b, decision_b = resolve_frame(envelope, "B")
    worth = assess_overlay_worth(envelope)
    search_trace = trace_candidate(
        {
            "id": envelope.token_id,
            "transform_class": "interop_overlay",
            "symmetry": envelope.surface_type,
            "intent": "cross_platform_routing",
            "grades": {"structure": 0.9, "semantic": 0.85, "consistency": 0.95},
        },
        {
            "entropy": 0.18,
            "agreement": worth.confidence,
            "stability": 0.88,
            "harmonic": 3.5,
        },
    )
    weak_overlay = create_view_token_envelope(
        _payload(),
        ViewFrame("KO", "control_flow", "json://scbe/control"),
        ViewFrame("AV", "transport_context", "json://scbe/context"),
        payload_formats=("json",),
        visual_constraints={"complementarity_min": 0.4},
    )
    _, weak_decision = resolve_frame(weak_overlay, "A")

    return {
        "schema": "scbe_view_token_overlay_eval_v1",
        "result": "worth_continuing" if worth.decision == "ALLOW" and search_trace.decision == "ALLOW" else "hold",
        "envelope": envelope.to_dict(),
        "frame_a": resolved_a,
        "frame_a_decision": decision_a.to_dict(),
        "frame_b": resolved_b,
        "frame_b_decision": decision_b.to_dict(),
        "worth_decision": worth.to_dict(),
        "geoseal_search_trace": search_trace.to_dict(),
        "negative_control": {
            "formation": weak_overlay.formation,
            "decision": weak_decision.to_dict(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="artifacts/interop/view_token_overlay_eval.json",
        help="Path to write the evaluation artifact.",
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = evaluate()
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"result": result["result"], "output": str(output)}, sort_keys=True))
    return 0 if result["result"] == "worth_continuing" else 1


if __name__ == "__main__":
    raise SystemExit(main())
