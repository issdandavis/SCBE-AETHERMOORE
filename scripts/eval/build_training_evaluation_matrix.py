#!/usr/bin/env python3
"""Build the SCBE training evaluation matrix from current run review data.

This script is the release-facing merge-readiness view. It intentionally does
not promote adapters by loss alone; it condenses the latest gain board into a
small decision matrix and points each lane at the next hard gate.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW_JSON = REPO_ROOT / "artifacts" / "training_reports" / "training_review_latest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "training_evaluation_matrix"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def gate_status(status: str, blockers: list[str], train_records: int, eval_records: int) -> tuple[str, str]:
    if status == "promote_candidate" and not blockers and eval_records > 0:
        return "ROUTE_CANDIDATE", "Run frozen adapter eval plus functional benchmark before any weighted merge."
    if status == "needs_eval_gate":
        return "PROMOTION_BLOCKED", "Repair or rerun the explicit HOLD/FAIL eval artifact before promotion."
    if status == "polished_needs_frozen_gate":
        return "EVAL_REQUIRED", "Run the frozen eval gate; do not merge on metric score alone."
    if train_records > 0 and eval_records == 0:
        return "EVAL_REQUIRED", "Freeze an eval split before using this lane for adapter promotion."
    if status == "sidecar_signal_not_in_merge":
        return "SIDECAR_ONLY", "Keep as sidecar signal until it is mapped to an active specialist bucket."
    if blockers:
        return "PROMOTION_BLOCKED", "Resolve blockers before route or merge."
    return "EVAL_REQUIRED", "Attach frozen eval, executable, Stage 6, and functional evidence."


def build_rows(review: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    gain_board = review.get("gain_board") or {}
    if not isinstance(gain_board, dict):
        return rows

    for lane, bucket in sorted(gain_board.items()):
        if not isinstance(bucket, dict):
            continue
        status = str(bucket.get("status") or "unknown")
        blockers = [str(item) for item in (bucket.get("blockers") or [])]
        train_records = int(bucket.get("train_records") or 0)
        eval_records = int(bucket.get("eval_records") or 0)
        decision, next_action = gate_status(status, blockers, train_records, eval_records)
        top_runs = bucket.get("top_runs") if isinstance(bucket.get("top_runs"), list) else []
        top_run = top_runs[0] if top_runs and isinstance(top_runs[0], dict) else {}
        quality = top_run.get("quality_signal")
        loss = top_run.get("loss_signal")
        rows.append(
            {
                "lane": lane,
                "source_status": status,
                "decision": decision,
                "train_records": train_records,
                "eval_records": eval_records,
                "top_promotion_score": bucket.get("top_promotion_score"),
                "top_quality_signal": quality,
                "top_loss_signal": loss,
                "blockers": blockers,
                "top_run": top_run.get("path", ""),
                "recommended_action": bucket.get("recommended_action") or next_action,
                "next_action": next_action,
            }
        )
    return rows


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Training Evaluation Matrix",
        "",
        f"Generated: `{payload['generated_at']}`",
        "",
        "## Decision Board",
        "",
        "| Lane | Train | Eval | Score | Quality | Loss | Decision | Next Action |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in payload["rows"]:
        score = row["top_promotion_score"]
        quality = row["top_quality_signal"]
        loss = row["top_loss_signal"]
        lines.append(
            "| `{lane}` | {train} | {eval} | {score} | {quality} | {loss} | `{decision}` | {next_action} |".format(
                lane=row["lane"],
                train=row["train_records"],
                eval=row["eval_records"],
                score="-" if score is None else f"{float(score):.3f}",
                quality="-" if quality is None else f"{float(quality):.3f}",
                loss="-" if loss is None else f"{float(loss):.3f}",
                decision=row["decision"],
                next_action=str(row["next_action"]).replace("|", "/"),
            )
        )

    lines.extend(
        [
            "",
            "## Merge Rule",
            "",
            "- `ROUTE_CANDIDATE` means the lane can be tried behind a router after frozen eval and functional checks.",
            "- `EVAL_REQUIRED` means the lane has signal but lacks enough hard evidence for promotion.",
            "- `PROMOTION_BLOCKED` means a blocker or explicit HOLD/FAIL artifact must be repaired first.",
            "- `SIDECAR_ONLY` means useful signal, but not part of the active adapter merge plan.",
            "",
            "## Evidence Details",
            "",
        ]
    )
    for row in payload["rows"]:
        lines.extend(
            [
                f"### {row['lane']}",
                "",
                f"- Source status: `{row['source_status']}`",
                f"- Top run: `{row['top_run'] or '-'}`",
                f"- Recommended action: {row['recommended_action']}",
                f"- Blockers: {', '.join(row['blockers']) if row['blockers'] else 'none'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build current SCBE training evaluation matrix.")
    parser.add_argument("--review-json", default=str(DEFAULT_REVIEW_JSON))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true", help="Print result payload.")
    args = parser.parse_args()

    review_path = Path(args.review_json)
    if not review_path.exists():
        raise SystemExit(f"Missing review JSON: {review_path}")

    review = load_json(review_path)
    rows = build_rows(review)
    payload = {
        "schema_version": "scbe_training_evaluation_matrix_v2",
        "generated_at": utc_now(),
        "source_review": repo_rel(review_path),
        "rows": rows,
        "decision_counts": dict(sorted({row["decision"]: sum(1 for item in rows if item["decision"] == row["decision"]) for row in rows}.items())),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "latest.json"
    md_path = out_dir / "latest.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    result = {"json_path": repo_rel(json_path), "markdown_path": repo_rel(md_path), "row_count": len(rows), "decision_counts": payload["decision_counts"]}
    print(json.dumps(result if not args.json else payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
