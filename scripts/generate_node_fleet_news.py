#!/usr/bin/env python3
"""Generate a plain-language news brief from a node-fleet training run."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate node-fleet training news")
    parser.add_argument("--run-dir", default=None, help="Run directory containing fleet_training_metrics.json")
    parser.add_argument("--base-dir", default="training/runs/node_fleet")
    parser.add_argument("--out-dir", default="docs/news")
    return parser.parse_args()


def find_run_dir(base_dir: Path, explicit: str | None) -> Path:
    if explicit:
        run = Path(explicit)
        if run.is_dir():
            return run
        raise FileNotFoundError(f"Run directory not found: {run}")
    runs = sorted([p for p in base_dir.iterdir() if p.is_dir()], key=lambda p: p.name)
    if not runs:
        raise FileNotFoundError(f"No runs found in {base_dir}")
    return runs[-1]


def verdict_label(report: dict) -> str:
    growth = report["growth"]
    if growth.get("overall_confirmed"):
        return "Growth confirmed across node-fleet"
    if growth.get("specialists_confirmed") and not growth.get("fleet_confirmed"):
        return "Specialists improved; fleet coordinator needs more data"
    return "Mixed or weak growth; tune and retrain"


def main() -> int:
    args = parse_args()
    base_dir = Path(args.base_dir)
    run_dir = find_run_dir(base_dir, args.run_dir)
    metrics_path = run_dir / "fleet_training_metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Missing metrics file: {metrics_path}")

    report = json.loads(metrics_path.read_text(encoding="utf-8"))
    run_id = report.get("run_id", run_dir.name)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fg = report["fleet_coordinator"]["growth"]
    lines = [
        f"# Node-Fleet Training News ({run_id})",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Verdict: **{verdict_label(report)}**",
        f"- Samples: `{report['data']['sample_count']}`",
        f"- Split: `{report['data']['train_count']} train / {report['data']['val_count']} val`",
        f"- Overall confirmed: `{report['growth']['overall_confirmed']}`",
        f"- Hugging Face upload: `{report.get('huggingface_upload', {}).get('status', 'unknown')}`",
        "",
        "## Specialist Results",
    ]

    for name, model in report["specialist_models"].items():
        g = model["growth"]
        lines.extend(
            [
                f"- `{name}`: confirmed `{g['confirmed']}`, val acc `{g['first_val_accuracy']} -> {g['last_val_accuracy']}`, val loss drop `{g['val_loss_drop']}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Fleet Coordinator",
            f"- confirmed: `{fg['confirmed']}`",
            f"- val acc: `{fg['first_val_accuracy']} -> {fg['last_val_accuracy']}`",
            f"- val loss drop: `{fg['val_loss_drop']}`",
            "",
            "## Plain-English Readout",
            "- The specialist heads are learning role-specific behavior.",
            "- The fleet coordinator is improving when loss goes down consistently.",
            "- Next quality jump comes from adding more real docs and story corpora, not only augmented data.",
        ]
    )

    run_news = out_dir / f"node_fleet_{run_id}.md"
    latest_news = out_dir / "latest.md"
    summary_json = out_dir / f"node_fleet_{run_id}.json"
    run_news.write_text("\n".join(lines), encoding="utf-8")
    latest_news.write_text("\n".join(lines), encoding="utf-8")
    summary_json.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "verdict": verdict_label(report),
                "overall_confirmed": report["growth"]["overall_confirmed"],
                "specialists_confirmed": report["growth"]["specialists_confirmed"],
                "fleet_confirmed": report["growth"]["fleet_confirmed"],
                "sample_count": report["data"]["sample_count"],
                "huggingface_upload": report.get("huggingface_upload", {}),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("News generated.")
    print("Run news:", run_news)
    print("Latest news:", latest_news)
    print("Summary JSON:", summary_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

