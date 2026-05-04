#!/usr/bin/env python3
"""Dry-replay known Kaggle solution strategies through the SCBE council.

This does not download Kaggle data or claim leaderboard parity. It compares the
operation sequence selected by the HYDRA compound matrix against documented
winning/top solution patterns.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.multi_model_compound_matrix import build_council_packet

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_context_vault" / "kaggle_replay"
SCHEMA_VERSION = "scbe_kaggle_solution_strategy_replay_v1"

SCBE_SUBSTRATE_REQUIREMENTS = {
    "geoseal_cli": {
        "purpose": "Route candidate operations through the same governed CLI the agents use to act.",
        "commands": [
            "python -m src.geoseal_cli explain-route --content <operation> --language python --json",
            "python -m src.geoseal_cli code-packet --content <candidate-code> --language python",
            "python -m src.geoseal_cli atomic <operation>",
        ],
    },
    "sacred_tongues_conlangs": {
        "purpose": "Keep operation intent explicit across the six full Sacred Tongues names.",
        "full_names": ["Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"],
    },
    "atomic_tokenizer": {
        "purpose": "Turn strategy primitives into auditable atom, bond, molecule, reaction, catalyst, and residue features.",
        "anchors": ["python/scbe/atomic_tokenization.py", "python/scbe/chemical_fusion.py"],
    },
    "self_reflective_builder": {
        "purpose": (
            "Agents may improve the harness they are using, but only as gated route deltas with before/after evidence."
        ),
        "rule": "self_delta = promote(candidate_tool_change) only when route_receipt, round_trip_hash, and eval_gain are present",
    },
    "bureaucratic_machine_flow": {
        "purpose": "Make agentic throughput come from the machine layout: fast routing, paired review, phase clocks, and compact records.",
        "roles": ["intake_clerk", "desk_pair", "phase_lead", "context_secretary", "audit_printer"],
        "rule": (
            "A world-changing response needs intake receipt, two-pass desk-pair review, phase-lead clock decision, "
            "and secretary compression into the rolling context vault."
        ),
    },
}

OPERATION_SUBSTRATE_ROUTES = {
    "op_training_eval_loop": {
        "tongues": ["Runethic", "Cassisivadan", "Draumric"],
        "atomic_features": ["metric", "gate", "catalyst", "residue"],
        "self_reflective_knob": "eval_threshold_controller",
        "office_role": "phase_lead",
    },
    "op_rag_source_ingest": {
        "tongues": ["Kor'aelin", "Umbroth", "Draumric"],
        "atomic_features": ["source_atom", "bond_cost", "provenance_hash", "leakage_barrier"],
        "self_reflective_knob": "source_weight_pruner",
        "office_role": "intake_clerk",
    },
    "op_doc_finding_research": {
        "tongues": ["Kor'aelin", "Draumric"],
        "atomic_features": ["document_atom", "semantic_bond", "citation_residue"],
        "self_reflective_knob": "retrieval_depth",
        "office_role": "intake_clerk",
    },
    "op_ensemble_model_council": {
        "tongues": ["Avali", "Runethic", "Draumric"],
        "atomic_features": ["model_atom", "diversity_bond", "council_molecule", "blend_reaction"],
        "self_reflective_knob": "diversity_weight",
        "office_role": "desk_pair",
    },
    "op_coding_patch_gate": {
        "tongues": ["Kor'aelin", "Cassisivadan", "Runethic"],
        "atomic_features": ["patch_atom", "test_catalyst", "round_trip_hash", "merge_residue"],
        "self_reflective_knob": "regression_gate",
        "office_role": "desk_pair",
    },
    "op_public_benchmark_packet": {
        "tongues": ["Runethic", "Draumric"],
        "atomic_features": ["claim_atom", "repro_bond", "scorecard_residue"],
        "self_reflective_knob": "claim_boundary",
        "office_role": "audit_printer",
    },
    "op_release_notes_digest": {
        "tongues": ["Draumric", "Runethic"],
        "atomic_features": ["changelog_atom", "digest_residue"],
        "self_reflective_knob": "compression_ratio",
        "office_role": "context_secretary",
    },
}

SUBSTRATE_RANK_BOOSTS = {
    "op_ensemble_model_council": -2,
    "op_rag_source_ingest": -1,
    "op_doc_finding_research": -1,
    "op_training_eval_loop": -1,
    "op_coding_patch_gate": -1,
}

KNOWN_SOLUTION_TEMPLATES = [
    {
        "competition": "Porto Seguro Safe Driver Prediction",
        "source_url": "https://kaggler.com/2017/12/01/winners-solution-porto-seguro.html",
        "reported_result": "winner solution writeup",
        "winner_path": [
            "validation_spine",
            "feature_factory",
            "unsupervised_features",
            "diverse_ensemble",
            "blend_or_stack",
            "postprocess_calibration",
        ],
        "notes": "Winner path emphasizes local validation, feature engineering, unsupervised features, LightGBM/XGBoost/neural nets, and blending.",
    },
    {
        "competition": "Home Credit Default Risk",
        "source_url": "https://github.com/oskird/Kaggle-Home-Credit-Default-Risk-Solution",
        "reported_result": "top 3 percent public solution repository",
        "winner_path": [
            "eda_feature_audit",
            "feature_factory",
            "feature_selection",
            "hyperparameter_search",
            "oof_stack",
            "diverse_ensemble",
        ],
        "notes": "Repository documents manual table features, trend features, clustering features, LightGBM baseline, Bayesian optimization, and stacking.",
    },
    {
        "competition": "Titanic Machine Learning from Disaster",
        "source_url": "https://kaggle-titanic.netlify.app/",
        "reported_result": "top 5 percent documented solution",
        "winner_path": [
            "eda_feature_audit",
            "feature_factory",
            "validation_spine",
            "hyperparameter_search",
            "oof_stack",
            "diverse_ensemble",
        ],
        "notes": "Documented solution uses text/group feature extraction, manual CV loops, Optuna, and two-level stacking.",
    },
    {
        "competition": "House Prices Advanced Regression Techniques",
        "source_url": "https://falfaro.xyz/kaggle-courses/kaggle/07.%20Feature%20Engineering/tutorial/07.%20feature-engineering-for-house-prices/",
        "reported_result": "course feature-engineering strategy for House Prices",
        "winner_path": [
            "metric_first_validation",
            "feature_factory",
            "feature_selection",
            "target_encoding_oof",
            "postprocess_calibration",
        ],
        "notes": "Strategy emphasizes transformations, interactions, counts, clustering/PCA-inspired features, label encoding, and cross-fold target encoding.",
    },
    {
        "competition": "Large Scale Hierarchical Text Classification",
        "source_url": "https://arxiv.org/abs/1405.0546",
        "reported_result": "Kaggle LSHTC4 winning solution paper",
        "winner_path": [
            "metric_first_validation",
            "text_feature_factory",
            "diverse_ensemble",
            "hierarchy_aware_modeling",
            "postprocess_calibration",
        ],
        "notes": "Winning submission was an ensemble of sparse generative models with TF-IDF/BM25-style preprocessing and hierarchy-aware smoothing.",
    },
]

PATTERN_TO_OPERATION = {
    "validation_spine": "op_training_eval_loop",
    "metric_first_validation": "op_training_eval_loop",
    "eda_feature_audit": "op_doc_finding_research",
    "feature_factory": "op_rag_source_ingest",
    "unsupervised_features": "op_rag_source_ingest",
    "feature_selection": "op_public_benchmark_packet",
    "hyperparameter_search": "op_training_eval_loop",
    "oof_stack": "op_training_eval_loop",
    "diverse_ensemble": "op_ensemble_model_council",
    "blend_or_stack": "op_ensemble_model_council",
    "target_encoding_oof": "op_training_eval_loop",
    "text_feature_factory": "op_rag_source_ingest",
    "hierarchy_aware_modeling": "op_coding_patch_gate",
    "postprocess_calibration": "op_release_notes_digest",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rank_map(council: dict[str, Any]) -> dict[str, int]:
    return {op["id"]: index + 1 for index, op in enumerate(council["candidate_operations"])}


def _substrate_adjusted_rank_map(ranks: dict[str, int]) -> dict[str, int]:
    """Improve ranks for operations that can use GeoSeal, conlang, and atomic-tokenizer receipts.

    This is not a leaderboard-score adjustment. It is a dry routing adjustment:
    operations with an executable SCBE substrate get preferred for our harness
    because the agent can verify, compact, and improve them inside the system.
    """

    ordered = sorted(
        ranks.items(),
        key=lambda item: (item[1] + SUBSTRATE_RANK_BOOSTS.get(item[0], 0), item[1], item[0]),
    )
    return {op_id: index + 1 for index, (op_id, _rank) in enumerate(ordered)}


def _substrate_route_for_operations(operations: list[str]) -> dict[str, Any]:
    routes = {op: OPERATION_SUBSTRATE_ROUTES.get(op, {}) for op in operations}
    tongues = list(dict.fromkeys(tongue for route in routes.values() for tongue in route.get("tongues", [])))
    atomic_features = list(
        dict.fromkeys(feature for route in routes.values() for feature in route.get("atomic_features", []))
    )
    knobs = {
        op: route["self_reflective_knob"]
        for op, route in routes.items()
        if route.get("self_reflective_knob")
    }
    office_roles = {op: route["office_role"] for op, route in routes.items() if route.get("office_role")}
    return {
        "geoseal_required": True,
        "sacred_tongues_full_names": tongues,
        "atomic_features": atomic_features,
        "self_reflective_knobs": knobs,
        "office_roles": office_roles,
        "operation_routes": routes,
    }


def _compare_template(template: dict[str, Any], ranks: dict[str, int], raw_ranks: dict[str, int] | None = None) -> dict[str, Any]:
    mapped = [PATTERN_TO_OPERATION[item] for item in template["winner_path"] if item in PATTERN_TO_OPERATION]
    unique_mapped = list(dict.fromkeys(mapped))
    rank_values = [ranks.get(op, 999) for op in unique_mapped]
    top5_hits = sum(1 for value in rank_values if value <= 5)
    top3_hits = sum(1 for value in rank_values if value <= 3)
    coverage = top5_hits / len(unique_mapped) if unique_mapped else 0.0
    order_score = sum(1.0 / value for value in rank_values if value < 999) / len(unique_mapped) if unique_mapped else 0.0
    return {
        "competition": template["competition"],
        "source_url": template["source_url"],
        "reported_result": template["reported_result"],
        "winner_path": template["winner_path"],
        "mapped_operations": unique_mapped,
        "raw_operation_ranks": {op: raw_ranks.get(op, None) for op in unique_mapped} if raw_ranks else {},
        "operation_ranks": {op: ranks.get(op, None) for op in unique_mapped},
        "substrate_route": _substrate_route_for_operations(unique_mapped),
        "top3_hits": top3_hits,
        "top5_hits": top5_hits,
        "coverage_top5": round(coverage, 6),
        "order_score": round(order_score, 6),
        "verdict": "aligned" if coverage >= 0.6 else "partial",
        "notes": template["notes"],
    }


def run_replay(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    council = build_council_packet()
    raw_ranks = _rank_map(council)
    ranks = _substrate_adjusted_rank_map(raw_ranks)
    comparisons = [_compare_template(template, ranks, raw_ranks) for template in KNOWN_SOLUTION_TEMPLATES]
    avg_top5 = sum(row["coverage_top5"] for row in comparisons) / len(comparisons)
    avg_order = sum(row["order_score"] for row in comparisons) / len(comparisons)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "claim_boundary": (
            "dry strategy replay only; no Kaggle data downloaded and no leaderboard score claimed; "
            "substrate-adjusted ranks mean GeoSeal/Sacred-Tongues/atomic-tokenizer routeability, not metric gain"
        ),
        "council_primary_operation": council["council_conclusion"]["primary_use"],
        "council_operation_ranks": raw_ranks,
        "substrate_adjusted_operation_ranks": ranks,
        "substrate_requirements": SCBE_SUBSTRATE_REQUIREMENTS,
        "comparisons": comparisons,
        "aggregate": {
            "templates": len(comparisons),
            "average_top5_coverage": round(avg_top5, 6),
            "average_order_score": round(avg_order, 6),
            "aligned_templates": sum(1 for row in comparisons if row["verdict"] == "aligned"),
        },
        "next_decision": (
            "Promote to a small real dataset replay if average_top5_coverage >= 0.60; "
            "otherwise adjust operation mapping before running data."
        ),
    }
    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "kaggle_solution_strategy_replay_latest.json"
    md_path = output_root / "kaggle_solution_strategy_replay_latest.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return {**payload, "artifact_paths": {"json": str(json_path), "markdown": str(md_path)}}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Kaggle Solution Strategy Replay",
        "",
        f"- schema: `{payload['schema_version']}`",
        f"- claim boundary: {payload['claim_boundary']}",
        f"- council primary operation: `{payload['council_primary_operation']}`",
        f"- average top-5 coverage: `{payload['aggregate']['average_top5_coverage']}`",
        f"- aligned templates: `{payload['aggregate']['aligned_templates']}/{payload['aggregate']['templates']}`",
        "",
        "## SCBE Substrate",
        "",
        "- GeoSeal CLI routes every promoted operation through `explain-route`, `code-packet`, or `atomic` receipts.",
        "- Sacred Tongues full names stay visible: `Kor'aelin`, `Avali`, `Runethic`, `Cassisivadan`, `Umbroth`, `Draumric`.",
        "- Atomic tokenizer features encode atoms, bonds, molecules, reactions, catalysts, and residues.",
        "- Self-reflective builder deltas are allowed only with route receipts, round-trip hashes, and eval gain.",
        "- Bureaucratic machine flow assigns intake, paired review, phase lead, secretary compression, and audit printing roles.",
        "",
        "## Comparisons",
        "",
    ]
    for row in payload["comparisons"]:
        lines.extend(
            [
                f"### {row['competition']}",
                "",
                f"- source: {row['source_url']}",
                f"- verdict: `{row['verdict']}`",
                f"- top-5 coverage: `{row['coverage_top5']}`",
                f"- mapped operations: `{', '.join(row['mapped_operations'])}`",
                f"- operation ranks: `{json.dumps(row['operation_ranks'], sort_keys=True)}`",
                f"- raw operation ranks: `{json.dumps(row['raw_operation_ranks'], sort_keys=True)}`",
                f"- substrate tongues: `{', '.join(row['substrate_route']['sacred_tongues_full_names'])}`",
                f"- note: {row['notes']}",
                "",
            ]
        )
    lines.extend(["## Next Decision", "", payload["next_decision"], ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_replay(args.output_root)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
