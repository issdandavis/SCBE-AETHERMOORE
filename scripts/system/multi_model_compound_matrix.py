#!/usr/bin/env python3
"""HYDRA compound matrix council for agentic research operations.

Combines Kaggle-style competitive strategy heuristics with the SCBE formation
matrix so model councils can choose bounded operations for research, sorting,
coding, pathfinding, and validation.
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

from scripts.system.tune_formation_matrix import run_sweep  # noqa: E402

SCHEMA_VERSION = "scbe_multi_model_compound_matrix_v1"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "agent_context_vault" / "compound_matrix"
DEFAULT_TUNING_PATH = REPO_ROOT / "artifacts" / "agent_context_vault" / "formation_matrix_tuning.json"

KAGGLE_STRATEGY_WEIGHTS = {
    "problem_metric_fit": 0.95,
    "eda_feature_audit": 0.82,
    "validation_spine": 1.0,
    "leakage_guard": 0.98,
    "oof_predictions": 0.86,
    "ensemble_diversity": 0.88,
    "post_processing": 0.58,
    "documentation": 0.64,
    "automation": 0.72,
    "leaderboard_skepticism": 0.92,
}

SOURCE_NOTES = [
    {
        "title": "NVIDIA Kaggle Grandmasters insights",
        "url": "https://developer.nvidia.com/blog/competition-and-community-insights-from-nvidias-kaggle-grandmasters/",
        "takeaway": "Start from the competition metric and validation design; pseudo-labeling and ensembling must be fold-aware.",
    },
    {
        "title": "NVIDIA Kaggle Grandmasters Playbook",
        "url": "https://developer.nvidia.com/blog/the-kaggle-grandmasters-playbook-7-battle-tested-modeling-techniques-for-tabular-data",
        "takeaway": "Match cross-validation to test structure, engineer features at scale, and use stacking after diverse base models exist.",
    },
    {
        "title": "Kaggle Coders competition tips",
        "url": "https://kagglecoders.com/tips.html",
        "takeaway": "Understand the problem, explore data, start simple, engineer features, validate locally, document runs.",
    },
    {
        "title": "Agent K paper",
        "url": "https://arxiv.org/abs/2411.03562",
        "takeaway": "Structured LLM orchestration for Kaggle-style data science benefits from systematic planning, feature engineering, and hyperparameter search.",
    },
    {
        "title": "Reducing overfitting in challenge-based competitions",
        "url": "https://arxiv.org/abs/1607.00091",
        "takeaway": "Leaderboard feedback can be overfit; robust gates should penalize repeated probing and unstable validation.",
    },
]

SOLUTION_PATTERNS = [
    {
        "id": "metric_first_validation",
        "name": "Metric-first validation spine",
        "how_it_gets_there": "Read the task metric and test split shape before model choice; build local folds that mimic private evaluation.",
        "works_because": "Every later improvement can be trusted only if local validation predicts the hidden test direction.",
        "scbe_translation": "Before agents optimize a workflow, define the gate metric and evaluation contract they must improve.",
        "failure_mode": "Public-score chasing, repeated probes, and overfitting to a visible feedback channel.",
        "council_owner": "agent.claude",
        "strategy_keys": ["problem_metric_fit", "validation_spine", "leaderboard_skepticism"],
    },
    {
        "id": "feature_factory",
        "name": "Large feature factory with pruning",
        "how_it_gets_there": "Generate many candidate features, group aggregations, encodings, interactions, and domain-derived variables, then select only those that survive validation.",
        "works_because": "Feature signal often beats architecture changes in tabular and operational systems.",
        "scbe_translation": "Generate many task descriptors, route features, proof fields, and context hashes; keep only fields that improve downstream gates.",
        "failure_mode": "Feature bloat, leakage through target-aware transforms, and brittle one-off gains.",
        "council_owner": "agent.codex",
        "strategy_keys": ["eda_feature_audit", "leakage_guard", "automation"],
    },
    {
        "id": "oof_stack",
        "name": "Out-of-fold stacking",
        "how_it_gets_there": "Train base models on folds and store validation-fold predictions; train higher-level models only on out-of-sample predictions.",
        "works_because": "The stacker learns model complementarity without seeing predictions made by models trained on the same row.",
        "scbe_translation": "Let model lanes produce compact verdicts on disjoint task shards, then train/score the council layer from held-out lane outputs.",
        "failure_mode": "In-fold leakage that makes council decisions look stronger than they are.",
        "council_owner": "agent.kimi",
        "strategy_keys": ["oof_predictions", "ensemble_diversity", "validation_spine"],
    },
    {
        "id": "diverse_ensemble",
        "name": "Diverse ensemble with hill climbing",
        "how_it_gets_there": "Start from the strongest validated candidate, add different models or feature sets one at a time, and keep only weight changes that improve validation.",
        "works_because": "Different error surfaces reduce variance when combined under a trusted validation spine.",
        "scbe_translation": "Combine Codex, Claude, Kimi, local Ollama, Hugging Face, and Moonshot only when their outputs are non-redundant.",
        "failure_mode": "Too many similar lanes, more chatter, and no real error diversity.",
        "council_owner": "agent.moonshot",
        "strategy_keys": ["ensemble_diversity", "validation_spine", "documentation"],
    },
    {
        "id": "fold_safe_pseudo_labeling",
        "name": "Fold-safe pseudo-labeling",
        "how_it_gets_there": "Use strong teacher predictions as extra training signal, but compute them fold-by-fold so validation data is never labeled by a model trained on itself.",
        "works_because": "It adds signal from unlabeled or weakly labeled data while keeping the validation mirror clean.",
        "scbe_translation": "Let successful agent traces seed new training rows only when they pass held-out task gates and provenance checks.",
        "failure_mode": "Self-confirming training loops that amplify errors and hide leakage.",
        "council_owner": "agent.huggingface",
        "strategy_keys": ["oof_predictions", "leakage_guard", "automation"],
    },
    {
        "id": "postprocess_calibration",
        "name": "Post-processing and calibration",
        "how_it_gets_there": "Tune thresholds, calibrate outputs, apply constraints, and clean final predictions after the main model is stable.",
        "works_because": "Small final transformations can align outputs to the metric and domain constraints without retraining the whole system.",
        "scbe_translation": "After agents produce outputs, normalize release notes, route labels, verdicts, and package metadata through deterministic gates.",
        "failure_mode": "Metric gaming or cosmetic polish before the core result is real.",
        "council_owner": "agent.ollama",
        "strategy_keys": ["post_processing", "validation_spine", "documentation"],
    },
]

COUNCIL_LANES = [
    {
        "agent": "agent.codex",
        "role": "systems_integrator",
        "model_ref": "codex",
        "strengths": ["repo_grounding", "tests", "patches", "packaging"],
    },
    {
        "agent": "agent.claude",
        "role": "review_architect",
        "model_ref": "claude",
        "strengths": ["long_context_review", "risk_finding", "design_docs"],
    },
    {
        "agent": "agent.kimi",
        "role": "coding_lane",
        "model_ref": "kimi-code:kimi-for-coding",
        "strengths": ["code_search", "patch_suggestions", "agentic_cli"],
    },
    {
        "agent": "agent.ollama",
        "role": "local_privacy_lane",
        "model_ref": "ollama:local",
        "strengths": ["secret_safe_review", "offline_triage", "cheap_iteration"],
    },
    {
        "agent": "agent.huggingface",
        "role": "training_eval_lane",
        "model_ref": "huggingface:router_or_jobs",
        "strengths": ["remote_eval", "dataset_packaging", "adapter_runs"],
    },
    {
        "agent": "agent.moonshot",
        "role": "large_reasoning_lane",
        "model_ref": "moonshot:kimi-k2.6",
        "strengths": ["planning", "code_reasoning", "review"],
    },
]

CANDIDATE_OPERATIONS = [
    {
        "id": "op_pathfinding_repo",
        "name": "Pathfinding through repo entrypoints",
        "task_type": "pathfinding",
        "goal": "Find the shortest tested route from user goal to existing script, test, and artifact.",
        "strategy_keys": ["problem_metric_fit", "validation_spine", "documentation"],
        "risk": 0.14,
        "cost": 0.18,
        "formation_preference": "triad",
    },
    {
        "id": "op_doc_finding_research",
        "name": "Document finding and source grounding",
        "task_type": "doc_finding",
        "goal": "Locate source docs, cite them, and separate evidence from inference.",
        "strategy_keys": ["eda_feature_audit", "documentation", "leaderboard_skepticism", "validation_spine"],
        "risk": 0.14,
        "cost": 0.18,
        "formation_preference": "quad",
    },
    {
        "id": "op_coding_patch_gate",
        "name": "Coding patch with focused regression gate",
        "task_type": "coding",
        "goal": "Make a bounded patch, run focused tests, and emit proof paths.",
        "strategy_keys": ["validation_spine", "leakage_guard", "automation"],
        "risk": 0.24,
        "cost": 0.26,
        "formation_preference": "quad",
    },
    {
        "id": "op_sort_dirty_tree",
        "name": "Dirty worktree sorting and release cleanup",
        "task_type": "sorting",
        "goal": "Classify changed files as product, generated artifact, local state, or defer.",
        "strategy_keys": ["eda_feature_audit", "leakage_guard", "documentation"],
        "risk": 0.22,
        "cost": 0.20,
        "formation_preference": "triad",
    },
    {
        "id": "op_task_decomposition",
        "name": "Task decomposition into agent lanes",
        "task_type": "tasks",
        "goal": "Convert ambiguous user requests into bounded repo-grounded lanes with clarity gates.",
        "strategy_keys": ["problem_metric_fit", "automation", "documentation"],
        "risk": 0.16,
        "cost": 0.16,
        "formation_preference": "triad",
    },
    {
        "id": "op_training_eval_loop",
        "name": "Training evaluation loop",
        "task_type": "training_eval",
        "goal": "Compare local, Kaggle, and Hugging Face runs using one evaluation contract.",
        "strategy_keys": ["validation_spine", "oof_predictions", "leaderboard_skepticism"],
        "risk": 0.32,
        "cost": 0.38,
        "formation_preference": "hex",
    },
    {
        "id": "op_ensemble_model_council",
        "name": "Model council ensemble review",
        "task_type": "model_council",
        "goal": "Collect compact conclusions from multiple model lanes without leaking raw repo context.",
        "strategy_keys": ["ensemble_diversity", "documentation", "leakage_guard"],
        "risk": 0.22,
        "cost": 0.28,
        "formation_preference": "hex",
    },
    {
        "id": "op_public_benchmark_packet",
        "name": "Public benchmark readiness packet",
        "task_type": "benchmark",
        "goal": "Prepare a reproducible benchmark claim with command, artifact, and caveat fields.",
        "strategy_keys": ["validation_spine", "leaderboard_skepticism", "documentation"],
        "risk": 0.30,
        "cost": 0.30,
        "formation_preference": "quad",
    },
    {
        "id": "op_release_notes_digest",
        "name": "Release notes and package digest",
        "task_type": "release",
        "goal": "Convert changed paths into scoped release notes, package gates, and rollback notes.",
        "strategy_keys": ["documentation", "automation", "post_processing"],
        "risk": 0.20,
        "cost": 0.20,
        "formation_preference": "quad",
    },
    {
        "id": "op_rag_source_ingest",
        "name": "RAG source ingest and leakage check",
        "task_type": "rag",
        "goal": "Ingest public sources into manifests with hashes, provenance, and secret filters.",
        "strategy_keys": ["eda_feature_audit", "leakage_guard", "automation", "problem_metric_fit"],
        "risk": 0.22,
        "cost": 0.24,
        "formation_preference": "hex",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_tuning(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return run_sweep(grid=5, top_n=10, output_path=path)


def _strategy_strength(keys: list[str]) -> float:
    if not keys:
        return 0.0
    return sum(KAGGLE_STRATEGY_WEIGHTS[key] for key in keys) / len(keys)


def _formation_value(tuning: dict[str, Any], formation: str) -> dict[str, Any]:
    by_form = tuning.get("best_by_formation", {})
    if formation in by_form:
        return by_form[formation]
    return tuning["best"]


def _score_operation(operation: dict[str, Any], tuning: dict[str, Any]) -> dict[str, Any]:
    formation = str(operation["formation_preference"])
    form = _formation_value(tuning, formation)
    metrics = form.get("metrics", {})
    strategy = _strategy_strength(list(operation.get("strategy_keys", [])))
    formation_score = float(form.get("score", 0.0))
    coverage = float(metrics.get("coverage", 0.0))
    validation = float(metrics.get("validation", 0.0))
    chatter = float(metrics.get("chatter", 0.0))
    external_mapping = float(metrics.get("external_variable_mapping", 0.0))
    risk = float(operation.get("risk", 0.0))
    cost = float(operation.get("cost", 0.0))
    score = (
        0.30 * strategy
        + 0.22 * formation_score
        + 0.18 * coverage
        + 0.16 * validation
        + 0.10 * external_mapping
        - 0.10 * chatter
        - 0.09 * risk
        - 0.07 * cost
    )
    return {
        **operation,
        "strategy_strength": round(strategy, 6),
        "formation_score": round(formation_score, 6),
        "score": round(score, 6),
        "selected_formation": formation,
        "formation_metrics": metrics,
        "recommended_lanes": _lanes_for_operation(str(operation["task_type"]), formation),
    }


def _lanes_for_operation(task_type: str, formation: str) -> list[str]:
    if task_type in {"coding", "benchmark", "release"}:
        base = ["agent.codex", "agent.kimi", "agent.claude", "agent.ollama"]
    elif task_type in {"training_eval", "model_council", "rag"}:
        base = ["agent.codex", "agent.huggingface", "agent.claude", "agent.moonshot", "agent.ollama", "agent.kimi"]
    elif task_type in {"doc_finding", "pathfinding"}:
        base = ["agent.codex", "agent.claude", "agent.kimi", "agent.ollama"]
    else:
        base = ["agent.codex", "agent.claude", "agent.ollama"]
    counts = {"pair": 2, "triad": 3, "quad": 4, "hex": 6, "oct": 8}
    return base[: min(len(base), counts.get(formation, 3))]


def build_council_packet(
    *,
    tuning_path: Path = DEFAULT_TUNING_PATH,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    top_n: int = 10,
) -> dict[str, Any]:
    tuning = _load_tuning(tuning_path)
    operations = [_score_operation(op, tuning) for op in CANDIDATE_OPERATIONS]
    operations.sort(key=lambda row: (-float(row["score"]), float(row["risk"]), str(row["id"])))
    packet = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "purpose": "choose agentic research/coding/sorting operations using Kaggle-style strategy and SCBE formation-matrix tuning",
        "sources": SOURCE_NOTES,
        "solution_patterns": SOLUTION_PATTERNS,
        "strategy_weights": KAGGLE_STRATEGY_WEIGHTS,
        "formation_tuning_path": str(tuning_path),
        "formation_best": tuning.get("best", {}),
        "model_council": COUNCIL_LANES,
        "candidate_operations": operations[:top_n],
        "council_conclusion": {
            "primary_use": operations[0]["id"],
            "primary_reason": "highest score after strategy, validation, coverage, cost, chatter, and risk penalties",
            "default_formation": tuning.get("best", {}).get("formation", "quad"),
            "safe_start": "run top operation as a dry packet first, then promote to live agents only after proof artifacts exist",
        },
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "compound_matrix_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "full_system_review.md").write_text(render_review_doc(packet), encoding="utf-8")
    return packet


def render_review_doc(packet: dict[str, Any]) -> str:
    lines = [
        "# HYDRA Compound Matrix Council Review",
        "",
        f"- schema: `{packet['schema_version']}`",
        f"- created_at: `{packet['created_at']}`",
        f"- formation tuning: `{packet['formation_tuning_path']}`",
        f"- default formation: `{packet['council_conclusion']['default_formation']}`",
        "",
        "## Source-Backed Strategy Notes",
    ]
    for source in packet["sources"]:
        lines.append(f"- [{source['title']}]({source['url']}) — {source['takeaway']}")
    lines.extend(["", "## Winning-Solution Patterns To Reuse"])
    for pattern in packet["solution_patterns"]:
        lines.extend(
            [
                f"- `{pattern['id']}` — {pattern['name']}",
                f"  - how it gets there: {pattern['how_it_gets_there']}",
                f"  - why it works: {pattern['works_because']}",
                f"  - SCBE use: {pattern['scbe_translation']}",
                f"  - failure mode: {pattern['failure_mode']}",
            ]
        )
    lines.extend(["", "## Model Council Lanes"])
    for lane in packet["model_council"]:
        lines.append(
            f"- `{lane['agent']}` / `{lane['role']}` / `{lane['model_ref']}`: {', '.join(lane['strengths'])}"
        )
    lines.extend(["", "## Ranked Candidate Operations"])
    for index, op in enumerate(packet["candidate_operations"], start=1):
        lines.extend(
            [
                f"{index}. `{op['id']}` — {op['name']}",
                f"   - score: `{op['score']}`",
                f"   - formation: `{op['selected_formation']}`",
                f"   - lanes: `{', '.join(op['recommended_lanes'])}`",
                f"   - goal: {op['goal']}",
            ]
        )
    conclusion = packet["council_conclusion"]
    lines.extend(
        [
            "",
            "## Council Conclusion",
            "",
            f"Primary operation: `{conclusion['primary_use']}`.",
            "",
            conclusion["safe_start"],
            "",
            "Package this result into the HYDRA brain as the repeatable `hydra-compound-matrix` skill.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tuning-path", type=Path, default=DEFAULT_TUNING_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    packet = build_council_packet(tuning_path=args.tuning_path, output_root=args.output_root, top_n=max(1, args.top))
    print(json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
