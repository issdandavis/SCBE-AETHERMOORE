#!/usr/bin/env python3
"""Monitor training metrics and confirm growth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor training growth from HF training metrics")
    parser.add_argument("--run-dir", required=True, help="Training run directory")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when growth is not confirmed")
    return parser.parse_args()


def load_metrics(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "hf_training_metrics.json"
    if not p.exists():
        raise FileNotFoundError(f"Missing metrics file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir)
    metrics = load_metrics(run_dir)
    hist = metrics.get("training", {}).get("history", [])
    growth = metrics.get("growth", {})
    if not hist:
        raise RuntimeError("Training history is empty")

    first = hist[0]
    last = hist[-1]
    summary = {
        "run_id": metrics.get("run_id"),
        "samples": metrics.get("data", {}).get("sample_count"),
        "labels": metrics.get("data", {}).get("label_count"),
        "first_val_accuracy": round(float(first.get("val_accuracy", 0.0)), 6),
        "last_val_accuracy": round(float(last.get("val_accuracy", 0.0)), 6),
        "first_val_loss": round(float(first.get("val_loss", 0.0)), 6),
        "last_val_loss": round(float(last.get("val_loss", 0.0)), 6),
        "val_accuracy_gain": float(growth.get("val_accuracy_gain", 0.0)),
        "val_loss_drop": float(growth.get("val_loss_drop", 0.0)),
        "growth_confirmed": bool(growth.get("confirmed", False)),
    }
    out = run_dir / "growth_monitor_report.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("Training growth monitor report:")
    print(json.dumps(summary, indent=2))
    print("Report path:", out)

    if args.strict and not summary["growth_confirmed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

