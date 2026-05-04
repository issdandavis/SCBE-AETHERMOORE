#!/usr/bin/env python3
"""Build the model-score coordination matrix for agentic training.

The scorecard's model score moves only when evidence lands in three places:
dataset floor, quality metric, and promotion gate. This scaffold turns those
into a repeatable process with a compact box graph instead of loose notes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = (
    REPO_ROOT / "artifacts" / "training_hub" / "model_score_coordination_matrix.json"
)
DEFAULT_MD = (
    REPO_ROOT / "artifacts" / "training_hub" / "model_score_coordination_matrix.md"
)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _box_graph() -> str:
    return "\n".join(
        [
            "+----------------------+     +----------------------+     +----------------------+",
            "| 1. DATASET FLOOR     | --> | 2. QUALITY METRIC    | --> | 3. PROMOTION GATE    |",
            "| rows + tokenizer ok  |     | real train/eval run  |     | frozen gate + push   |",
            "+----------+-----------+     +----------+-----------+     +----------+-----------+",
            "           |                            |                            |",
            "           v                            v                            v",
            "+----------------------+     +----------------------+     +----------------------+",
            "| GeoShell 126 / 28    |     | best_metric present  |     | gate_pass_rate 1.0   |",
            "| 14 population turns  |     | loss + eval artifacts|     | pushed_adapter true  |",
            "+----------------------+     +----------------------+     +----------------------+",
        ]
    )


def build_matrix() -> dict[str, Any]:
    profile_path = Path(
        "config/model_training/coding-agent-qwen-geoshell-pair-agent-v1.json"
    )
    eval_report_path = Path(
        "artifacts/training_hub/geoshell_pair_agent_dataset_eval.json"
    )
    profile = _load_json(REPO_ROOT / profile_path)
    eval_report = _load_json(REPO_ROOT / eval_report_path)
    train_count = int(eval_report.get("row_count", 0)) - 28 if eval_report else 126
    holdout_count = 28 if eval_report else 28

    levers = [
        {
            "id": "dataset_floor",
            "scorecard_line": "hf_dataset_floor and kaggle_dataset_floor",
            "why_it_moves_score": "The scorecard awards dataset-floor points only when train/eval row counts clear the floor.",
            "target_state": {
                "hf_train_rows": 126,
                "hf_eval_rows": 28,
                "kaggle_train_rows_min": 250,
                "kaggle_eval_rows_min": 100,
            },
            "current_evidence": {
                "geoshell_rows_total": eval_report.get("row_count"),
                "geoshell_train_rows": train_count,
                "geoshell_holdout_rows": holdout_count,
                "tokenizer_eval_ok": eval_report.get("ok"),
            },
            "commands": [
                "python -m src.geoseal_cli pair-agent-training --json",
                "python scripts/eval/evaluate_geoshell_pair_agent_dataset.py --json",
                "npm run training:agentic-workbench",
            ],
            "artifact_paths": [
                "training-data/sft/geoshell_pair_agent_v1_train.sft.jsonl",
                "training-data/sft/geoshell_pair_agent_v1_holdout.sft.jsonl",
                "artifacts/training_hub/geoshell_pair_agent_dataset_eval.json",
            ],
        },
        {
            "id": "quality_metric",
            "scorecard_line": "kaggle_quality_metric",
            "why_it_moves_score": "Kaggle quality stays red until DONE.json or TRAINING_HISTORY.json has best_metric.",
            "target_state": {"best_metric": "non-null", "training_history": "present"},
            "commands": [
                "npm run training:kaggle:approval-v2:ready",
                "npm run training:kaggle:approval-v2:launch",
                "python scripts/kaggle_auto/launch.py --pull --round coding-approval-metrics-v2",
            ],
            "artifact_paths": [
                "artifacts/kaggle_output/polly-auto-coding-approval-metrics-v1/DONE.json",
                "artifacts/kaggle_output/polly-auto-coding-approval-metrics-v1/TRAINING_HISTORY.json",
            ],
        },
        {
            "id": "promotion_gate",
            "scorecard_line": "hf_promotion_gate and adapter_promoted",
            "why_it_moves_score": "HF promotion remains red until the remote log reports gate_pass_rate and pushed_adapter.",
            "target_state": {
                "gate_pass_rate": 1.0,
                "gate_overall_pass": True,
                "pushed_adapter": True,
            },
            "commands": [
                "python scripts/system/dispatch_coding_agent_hf_job.py dispatch --profile-path config/model_training/coding-agent-qwen-geoshell-pair-agent-v1.json --json",
                "python scripts/eval/score_agentic_training_system.py --refresh-hf-logs --write --json",
            ],
            "artifact_paths": [
                "artifacts/hf_coding_agent_jobs/coding-agent-qwen-geoshell-pair-agent-v1/**/job_packet.json",
                "artifacts/training_evals/agentic_system_scorecard_2026-05-02.json",
            ],
        },
    ]

    return {
        "schema_version": "scbe_model_score_coordination_matrix_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "profile_path": str(profile_path),
        "profile_limits": profile.get("training", {}),
        "phi_spiral": {
            "principle": "expand data, train/evaluate, promote only after gate evidence; then spiral back with repair residues",
            "stages": ["dataset_floor", "quality_metric", "promotion_gate"],
        },
        "box_graph": _box_graph(),
        "levers": levers,
    }


def write_outputs(
    matrix: dict[str, Any], json_path: Path, md_path: Path
) -> dict[str, str]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Model Score Coordination Matrix",
        "",
        "```text",
        matrix["box_graph"],
        "```",
        "",
        "## Three Score Movers",
        "",
    ]
    for lever in matrix["levers"]:
        lines.extend(
            [
                f"### {lever['id']}",
                f"- Scorecard line: `{lever['scorecard_line']}`",
                f"- Why: {lever['why_it_moves_score']}",
                "- Commands:",
            ]
        )
        lines.extend(f"  - `{command}`" for command in lever["commands"])
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    matrix = build_matrix()
    paths = write_outputs(matrix, args.json_out, args.md_out)
    payload = {"ok": True, "paths": paths, "lever_count": len(matrix["levers"])}
    print(json.dumps(payload if args.json else matrix, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
