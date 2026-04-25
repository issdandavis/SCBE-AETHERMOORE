from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiments.atomic_tokenizer_rename_benchmark import (
    DEFAULT_INPUT,
    run as run_rename,
)
from scripts.experiments.binary_branch_braid_router import run as run_binary_router
from scripts.experiments.cross_primary_braid_consistency import run as run_cross_braid
from python.scbe.semantic_gate import (
    SemanticBlendPolicy,
    SemanticSignal,
    evaluate_semantic_gate,
)

DEFAULT_OUTPUT = Path("artifacts") / "mathbac" / "basket_weave_consistency"


def run(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rename_report = run_rename(
        DEFAULT_INPUT, output_dir / "rename", "hex", shuffle_runs=32
    )
    cross_report = run_cross_braid(DEFAULT_INPUT, output_dir / "cross_braid", "hex")
    binary_report = run_binary_router(
        DEFAULT_INPUT, output_dir / "binary_router", "hex"
    )

    default_lane = rename_report["situational_lane_selection"]["profiles"][
        "recovery_default"
    ]["primary_lane"]
    geometry_lane = rename_report["situational_lane_selection"]["profiles"][
        "geometry_context"
    ]["primary_lane"]
    cross_best = cross_report["best_closure_feature"]
    binary_best = binary_report["best_feature"]
    workflow_lanes = set(
        json.loads(
            (output_dir / "rename" / "semantic_chemistry_workflows.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )["lanes"]
    )
    semantic_gate = evaluate_semantic_gate(
        [
            SemanticSignal(
                label="rename-default-score",
                value=rename_report["situational_lane_selection"]["profiles"][
                    "recovery_default"
                ]["ranked_lanes"][0]["score"],
                source="fact",
                confidence=0.95,
                provenance="atomic_tokenizer_rename_benchmark",
            ),
            SemanticSignal(
                label="layered-geometry-analogy",
                value=cross_report["features"]["layered_geometry_semantic"]["overall"][
                    "closure_accuracy"
                ],
                source="analogy",
                confidence=0.80,
                provenance="cross_primary_braid_consistency",
            ),
            SemanticSignal(
                label="eml-t-operator-prototype",
                value=1.0,
                source="experimental",
                confidence=0.70,
                provenance="t_operator_prototype",
            ),
        ],
        SemanticBlendPolicy(
            context="routing",
            risk="medium",
            allow_analogy=False,
            allow_experimental=False,
        ),
    )

    checks = {
        "workflow_exports_geometry_lane": "layered_geometry_semantic" in workflow_lanes,
        "default_lane_is_available_in_cross_braid": default_lane
        in cross_report["features"],
        "geometry_lane_is_available_in_cross_braid": geometry_lane
        in cross_report["features"],
        "cross_best_is_available_in_binary_router": cross_best
        in binary_report["features"],
        "binary_best_is_available_in_cross_braid": binary_best
        in cross_report["features"],
        "cross_best_has_above_chance_closure": cross_report["features"][cross_best][
            "overall"
        ]["closure_accuracy"]
        > 1 / 14,
        "binary_best_has_above_chance_closure": binary_report["features"][binary_best][
            "closure_accuracy"
        ]
        > 1 / 14,
        "semantic_gate_blocks_unapproved_blends": semantic_gate.decision == "QUARANTINE"
        and set(semantic_gate.blocked_sources) == {"analogy", "experimental"}
        and semantic_gate.allowed_sources == ("fact",),
    }
    report = {
        "version": "basket-weave-consistency-gate-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": all(checks.values()),
        "checks": checks,
        "lanes": {
            "rename_recovery_default": default_lane,
            "rename_geometry_context": geometry_lane,
            "cross_primary_best": cross_best,
            "binary_router_best": binary_best,
            "workflow_export_lanes": sorted(workflow_lanes),
        },
        "metrics": {
            "cross_best_closure": cross_report["features"][cross_best]["overall"][
                "closure_accuracy"
            ],
            "binary_best_closure": binary_report["features"][binary_best][
                "closure_accuracy"
            ],
            "rename_default_score": rename_report["situational_lane_selection"][
                "profiles"
            ]["recovery_default"]["ranked_lanes"][0]["score"],
            "rename_geometry_score": rename_report["situational_lane_selection"][
                "profiles"
            ]["geometry_context"]["ranked_lanes"][0]["score"],
            "semantic_gate_blended_value": semantic_gate.blended_value,
        },
        "semantic_gate": semantic_gate.to_dict(),
        "notes": (
            "This gate weaves back down across prior layers. It does not require every best lane to be identical; "
            "it requires that selected lanes remain available across reports, that closure stays above chance, and that "
            "analogy/experimental lanes cannot silently act as fact channels."
        ),
    }
    (output_dir / "basket_weave_consistency_gate.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = run(args.output_dir)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"basket_weave passed={report['passed']} checks={sum(report['checks'].values())}/{len(report['checks'])}"
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
