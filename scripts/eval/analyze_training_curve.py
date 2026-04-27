"""Analyze training logs for loss, token accuracy, and overfit-risk signals.

This is intentionally lightweight: it parses copied HF Jobs/Kaggle logs that
contain trainer metric dictionaries and emits a report we can use before
promotion. It does not decide model quality; it flags whether the run is
learning smoothly or likely memorizing before frozen eval.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "training_reports"
METRIC_RE = re.compile(r"\{[^{}]*(?:'loss'|'mean_token_accuracy')[^{}]*\}")


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_metrics(text: str) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for match in METRIC_RE.finditer(text):
        try:
            raw = ast.literal_eval(match.group(0))
        except (SyntaxError, ValueError):
            continue
        row: dict[str, float] = {}
        for key, value in raw.items():
            parsed = as_float(value)
            if parsed is not None and math.isfinite(parsed):
                row[str(key)] = parsed
        if "loss" in row or "mean_token_accuracy" in row:
            rows.append(row)
    return rows


def slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return values[-1] - values[0]


def summarize(rows: list[dict[str, float]]) -> dict[str, Any]:
    losses = [row["loss"] for row in rows if "loss" in row]
    accs = [row["mean_token_accuracy"] for row in rows if "mean_token_accuracy" in row]
    epochs = [row["epoch"] for row in rows if "epoch" in row]
    grad_norms = [row["grad_norm"] for row in rows if "grad_norm" in row]

    summary: dict[str, Any] = {
        "metric_rows": len(rows),
        "first_loss": losses[0] if losses else None,
        "last_loss": losses[-1] if losses else None,
        "best_loss": min(losses) if losses else None,
        "loss_delta": slope(losses),
        "first_token_accuracy": accs[0] if accs else None,
        "last_token_accuracy": accs[-1] if accs else None,
        "best_token_accuracy": max(accs) if accs else None,
        "token_accuracy_delta": slope(accs),
        "last_epoch": epochs[-1] if epochs else None,
        "max_grad_norm": max(grad_norms) if grad_norms else None,
    }

    flags: list[str] = []
    if summary["last_token_accuracy"] is not None and summary["last_token_accuracy"] >= 0.92:
        flags.append("high_token_accuracy_overfit_watch")
    if summary["last_epoch"] is not None and summary["last_epoch"] > 1.05:
        flags.append("effective_epoch_over_one")
    if len(losses) >= 4 and losses[-1] > min(losses[:-1]) * 1.08:
        flags.append("loss_rebounded_after_best")
    if summary["max_grad_norm"] is not None and summary["max_grad_norm"] > 5.0:
        flags.append("large_grad_norm")
    if not rows:
        flags.append("no_metric_rows_found")
    summary["flags"] = flags

    if not rows:
        verdict = "NO_METRICS"
    elif any(flag in flags for flag in ("large_grad_norm",)):
        verdict = "UNSTABLE"
    elif any(flag in flags for flag in ("high_token_accuracy_overfit_watch", "effective_epoch_over_one")):
        verdict = "LEARNING_BUT_WATCH_OVERFIT"
    elif summary["loss_delta"] is not None and summary["loss_delta"] < 0:
        verdict = "LEARNING"
    else:
        verdict = "WATCH"
    summary["training_curve_verdict"] = verdict
    return summary


def write_markdown(path: Path, source: str, rows: list[dict[str, float]], summary: dict[str, Any]) -> None:
    lines = [
        "# Training Curve Report",
        "",
        f"Generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"Source: `{source}`",
        f"Verdict: **{summary['training_curve_verdict']}**",
        "",
        "## Summary",
        "",
    ]
    for key in (
        "metric_rows",
        "first_loss",
        "last_loss",
        "best_loss",
        "loss_delta",
        "first_token_accuracy",
        "last_token_accuracy",
        "best_token_accuracy",
        "token_accuracy_delta",
        "last_epoch",
        "max_grad_norm",
    ):
        lines.append(f"- `{key}`: `{summary.get(key)}`")
    lines.append(f"- `flags`: `{', '.join(summary.get('flags') or []) or 'none'}`")
    lines.extend(["", "## Tail Metrics", ""])
    for row in rows[-12:]:
        lines.append(
            "- "
            + ", ".join(
                f"{key}={value:.6g}"
                for key, value in row.items()
                if key in {"loss", "mean_token_accuracy", "grad_norm", "learning_rate", "epoch"}
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log_file", type=Path)
    parser.add_argument("--label", default="")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    text = args.log_file.read_text(encoding="utf-8", errors="replace")
    rows = parse_metrics(text)
    summary = summarize(rows)
    generated = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    label = args.label or args.log_file.stem
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "training-curve"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"{safe_label}_training_curve_{generated}.json"
    md_path = args.out_dir / f"{safe_label}_training_curve_{generated}.md"
    payload = {
        "schema_version": "scbe_training_curve_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": str(args.log_file),
        "label": label,
        "summary": summary,
        "metrics": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(md_path, str(args.log_file), rows, summary)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "summary": summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
