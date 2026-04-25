#!/usr/bin/env python3
"""Review SCBE training/eval runs and build a gain-merge board.

This script is intentionally read-only. It scans local run artifacts and the
existing consolidation inventory, extracts measurable signals, and writes a
report that can drive specialist adapter promotion without flat-merging data.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONSOLIDATION_DIR = REPO_ROOT / "artifacts" / "ai_training_consolidation" / "latest"
DEFAULT_OUTPUT_JSON = DEFAULT_CONSOLIDATION_DIR / "run_review.json"
DEFAULT_OUTPUT_MD = DEFAULT_CONSOLIDATION_DIR / "RUN_REVIEW.md"

RUN_SCAN_ROOTS = (
    "artifacts/training_reports",
    "artifacts/benchmark",
    "artifacts/benchmarks",
    "artifacts/atomic_discovery_tonight",
    "artifacts/colab_training_handoffs",
    "artifacts/colab_smoke",
    "artifacts/training_terminal",
    "artifacts/hf_coding_agent_jobs",
    "artifacts/hf_coding_model_merges",
    "artifacts/web_tool",
    "training/runs",
)

METRIC_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?:^|_)(?:eval_)?loss$", "loss"),
    (r"perplexity|ppl", "loss"),
    (r"accuracy|acc$", "quality"),
    (r"f1|exact_match|em$", "quality"),
    (r"pass(?:_at_1|@1|_rate)?$", "quality"),
    (r"success(?:_rate)?$", "quality"),
    (r"score$", "quality"),
    (r"win(?:_rate)?$", "quality"),
    (r"recall|precision", "quality"),
    (r"latency|runtime|duration|seconds|wall", "cost"),
    (r"tokens_per_second|throughput", "efficiency"),
)

PURPOSE_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("coding_model", ("coding", "coder", "code", "geoseal", "stage6", "polyglot", "benchmark")),
    ("operator_agent_bus", ("agent", "bus", "operator", "apollo", "browser", "workflow", "route", "shell")),
    ("governance_security", ("governance", "security", "adversarial", "compliance", "risk", "null_space")),
    ("aligned_foundations", ("aligned", "chemistry", "tongue", "langues", "semantic", "foundation", "atomic")),
    ("research_bridge", ("research", "arxiv", "source", "paper", "citation")),
    ("story_lore", ("polly", "lore", "story", "aethermoor", "spiralverse")),
    ("commerce_product", ("commerce", "stripe", "checkout", "tax", "product", "gumroad")),
)


@dataclass(frozen=True)
class MetricSignal:
    name: str
    value: float
    kind: str
    json_path: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def classify_purpose(path_text: str, payload: dict[str, Any] | None = None) -> str:
    text = path_text.lower().replace("\\", "/")
    if payload:
        for key in ("purpose", "profile_id", "run_id", "title", "name", "merge_id", "dataset", "base_model"):
            value = payload.get(key)
            if isinstance(value, str):
                text += " " + value.lower()
            elif isinstance(value, dict):
                text += " " + json.dumps(value, sort_keys=True).lower()
    for purpose, hints in PURPOSE_HINTS:
        if any(hint in text for hint in hints):
            return purpose
    return "uncategorized"


def metric_kind(key: str) -> str | None:
    lowered = key.lower()
    for pattern, kind in METRIC_PATTERNS:
        if re.search(pattern, lowered):
            return kind
    return None


def as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().replace("%", "")
        try:
            number = float(stripped)
        except ValueError:
            return None
        if "%" in value:
            number /= 100.0
        return number if math.isfinite(number) else None
    return None


def extract_metric_signals(payload: Any, prefix: str = "") -> list[MetricSignal]:
    signals: list[MetricSignal] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            kind = metric_kind(str(key))
            number = as_number(value)
            if kind and number is not None:
                signals.append(MetricSignal(name=str(key), value=number, kind=kind, json_path=path))
            if isinstance(value, (dict, list)):
                signals.extend(extract_metric_signals(value, path))
    elif isinstance(payload, list):
        for idx, value in enumerate(payload[:500]):
            signals.extend(extract_metric_signals(value, f"{prefix}[{idx}]"))
    return signals


def load_json_file(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def iter_json_artifacts(roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for root_text in roots:
        root = REPO_ROOT / root_text
        if not root.exists():
            continue
        for pattern in ("*.json", "*.ipynb"):
            try:
                files.extend(path for path in root.rglob(pattern) if path.is_file())
            except OSError:
                continue
    return sorted(set(files), key=lambda p: str(p).lower())


def score_run(signals: list[MetricSignal]) -> dict[str, Any]:
    quality_values = [s.value for s in signals if s.kind == "quality"]
    loss_values = [s.value for s in signals if s.kind == "loss"]
    cost_values = [s.value for s in signals if s.kind == "cost"]
    efficiency_values = [s.value for s in signals if s.kind == "efficiency"]
    best_quality = max(quality_values) if quality_values else None
    best_loss = min(loss_values) if loss_values else None
    best_efficiency = max(efficiency_values) if efficiency_values else None
    best_cost = min(cost_values) if cost_values else None
    score = 0.0
    if best_quality is not None:
        score += min(max(best_quality, 0.0), 1.0) * 100.0 if best_quality <= 1.0 else best_quality
    if best_loss is not None:
        score += max(0.0, 20.0 - min(best_loss, 20.0))
    if best_efficiency is not None:
        score += min(best_efficiency, 1000.0) / 100.0
    if best_cost is not None and best_cost > 0:
        score += min(10.0, 10.0 / best_cost)
    return {
        "quality_signal": best_quality,
        "loss_signal": best_loss,
        "efficiency_signal": best_efficiency,
        "cost_signal": best_cost,
        "promotion_score": round(score, 6),
    }


def collect_run_reviews(roots: tuple[str, ...] = RUN_SCAN_ROOTS) -> list[dict[str, Any]]:
    reviews: list[dict[str, Any]] = []
    for path in iter_json_artifacts(roots):
        payload = load_json_file(path)
        if not isinstance(payload, (dict, list)):
            continue
        root_payload = payload if isinstance(payload, dict) else {}
        signals = extract_metric_signals(payload)
        if not signals and path.suffix.lower() != ".ipynb":
            continue
        review = {
            "path": repo_rel(path),
            "purpose": classify_purpose(str(path), root_payload),
            "metric_count": len(signals),
            "metrics": [
                {"name": s.name, "value": s.value, "kind": s.kind, "json_path": s.json_path}
                for s in sorted(signals, key=lambda item: (item.kind, item.name, item.json_path))[:50]
            ],
            **score_run(signals),
        }
        reviews.append(review)
    return sorted(reviews, key=lambda item: item.get("promotion_score", 0.0), reverse=True)


def load_consolidation_plan(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json_file(path)
    return payload if isinstance(payload, dict) else {}


def build_gain_board(reviews: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    by_purpose: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in reviews:
        by_purpose[str(review["purpose"])].append(review)

    specialists = {item.get("purpose"): item for item in plan.get("specialists", []) if isinstance(item, dict)}
    board: dict[str, Any] = {}
    all_purposes = sorted(set(by_purpose) | set(specialists))
    for purpose in all_purposes:
        runs = sorted(by_purpose.get(purpose, []), key=lambda item: item.get("promotion_score", 0.0), reverse=True)
        specialist = specialists.get(purpose, {})
        train_records = int(specialist.get("train_records") or 0)
        eval_records = int(specialist.get("eval_records") or 0)
        top_score = float(runs[0].get("promotion_score", 0.0)) if runs else 0.0
        blockers: list[str] = []
        in_merge_plan = purpose in specialists
        if train_records <= 0 and in_merge_plan:
            blockers.append("no regularized train records")
        if eval_records <= 0 and in_merge_plan:
            blockers.append("no frozen eval records")
        if not runs:
            blockers.append("no measurable run artifacts")
        status = "promote_candidate" if not blockers and top_score > 0 else "blocked"
        if not in_merge_plan and top_score > 0:
            status = "sidecar_signal_not_in_merge"
            blockers.append("not part of active specialist merge plan")
        if blockers and top_score > 0 and train_records > 0:
            status = "needs_eval_gate"
        board[purpose] = {
            "status": status,
            "blockers": blockers,
            "train_records": train_records,
            "eval_records": eval_records,
            "top_promotion_score": round(top_score, 6),
            "recommended_action": recommend_action(purpose, status, blockers),
            "top_runs": [
                {
                    "path": run["path"],
                    "promotion_score": run["promotion_score"],
                    "quality_signal": run["quality_signal"],
                    "loss_signal": run["loss_signal"],
                    "metric_count": run["metric_count"],
                }
                for run in runs[:8]
            ],
        }
    return board


def recommend_action(purpose: str, status: str, blockers: list[str]) -> str:
    if status == "promote_candidate":
        return "train or keep specialist adapter, then run its frozen eval before weighted adapter merge"
    if "no regularized train records" in blockers:
        if purpose == "operator_agent_bus":
            return "extract runnable command traces from agent bus, helpdesk loop, Apollo, and browser logs into messages records"
        if purpose == "research_bridge":
            return "convert source-grounded research notes/transcripts into citation-backed instruction records"
        return "regularize train candidates before dispatch"
    if "no frozen eval records" in blockers:
        return "create or freeze eval set before promotion; do not merge on train loss alone"
    return "inspect run artifacts and map them to a purpose bucket"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# SCBE Training Run Review and Gain Merge Board",
        "",
        f"Generated: {payload['generated_at_utc']}",
        "",
        "## External Lessons Applied",
        "",
        "- DeepSeek-V3 pattern: staged high-quality data, SFT plus RL, stable training instrumentation, no rollback-driven chaos.",
        "- DeepSeek-R1 pattern: use verifiable reward tasks for math/code/STEM instead of trusting demonstrations alone.",
        "- Kimi K2/K2.5 pattern: agentic workflow data matters; tool-use, environment interaction, and parallel specialist agents are model capability data, not just orchestration code.",
        "",
        "## Surface Counts",
        "",
    ]
    counts = payload["counts"]
    lines.extend(
        [
            f"- Reviewed artifact files with metrics: {counts['reviewed_run_count']}",
            f"- Purposes with signal: {counts['purpose_count']}",
            "",
            "## Gain Board",
            "",
        ]
    )
    for purpose, item in sorted(payload["gain_board"].items()):
        blockers = ", ".join(item["blockers"]) if item["blockers"] else "none"
        lines.append(
            f"- {purpose}: {item['status']}; train {item['train_records']}; eval {item['eval_records']}; "
            f"top score {item['top_promotion_score']}; blockers {blockers}"
        )
        lines.append(f"  Action: {item['recommended_action']}")
        for run in item["top_runs"][:3]:
            lines.append(
                f"  Run: {run['path']} | score {run['promotion_score']} | "
                f"quality {run['quality_signal']} | loss {run['loss_signal']}"
            )
    lines.extend(
        [
            "",
            "## Merge Rule",
            "",
            "Merge gains by adapter and purpose bucket, not by dumping every record into one dataset.",
            "A run can influence the final model only after its bucket has train data, frozen eval data, and a measurable promotion score.",
            "",
            "## Next Extraction Targets",
            "",
            "- Operator agent bus: convert helpdesk requests, agentbus pipe runs, mirror-room state, Apollo command logs, and browser route traces into runnable command SFT records.",
            "- Research bridge: convert EML/Kimi/DeepSeek/source notes into claim/citation/verification records, then freeze a citation eval set.",
            "- Governance security: add eval records before any adapter merge; current train signal is usable but under-gated.",
            "- Coding model: keep as primary lane; train/evaluate coding and aligned-foundation adapters before final weighted merge.",
            "",
        ]
    )
    return "\n".join(lines)


def build_review(output_json: Path, output_md: Path, consolidation_dir: Path) -> dict[str, Any]:
    plan = load_consolidation_plan(consolidation_dir / "consolidation_plan.json")
    reviews = collect_run_reviews()
    board = build_gain_board(reviews, plan)
    payload = {
        "schema_version": "scbe_training_run_review_v1",
        "generated_at_utc": utc_now(),
        "source_roots": list(RUN_SCAN_ROOTS),
        "counts": {
            "reviewed_run_count": len(reviews),
            "purpose_count": len({row["purpose"] for row in reviews}),
        },
        "gain_board": board,
        "top_runs": reviews[:30],
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Review SCBE training/eval runs and merge gains by bucket")
    parser.add_argument("--consolidation-dir", default=str(DEFAULT_CONSOLIDATION_DIR))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    args = parser.parse_args()
    payload = build_review(
        output_json=Path(args.output_json),
        output_md=Path(args.output_md),
        consolidation_dir=Path(args.consolidation_dir),
    )
    print(
        json.dumps(
            {
                "schema_version": "scbe_training_run_review_result_v1",
                "output_json": str(Path(args.output_json)),
                "output_md": str(Path(args.output_md)),
                "reviewed_run_count": payload["counts"]["reviewed_run_count"],
                "purpose_count": payload["counts"]["purpose_count"],
                "statuses": Counter(item["status"] for item in payload["gain_board"].values()),
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
