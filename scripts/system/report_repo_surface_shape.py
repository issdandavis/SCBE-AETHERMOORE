#!/usr/bin/env python3
"""Report SCBE repo top-level directory shape against configured lanes."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "system" / "repo_surface_lanes.json"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "repo_shape"


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def top_level_dirs(root: Path) -> list[str]:
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name != ".git")


def classify(dirs: list[str], config: dict) -> dict:
    path_to_lane: dict[str, str] = {}
    duplicate_paths: dict[str, list[str]] = defaultdict(list)

    for lane, meta in config["lanes"].items():
        for path in meta.get("paths", []):
            duplicate_paths[path].append(lane)
            path_to_lane[path] = lane

    lanes: dict[str, list[str]] = {lane: [] for lane in config["lanes"]}
    unknown: list[str] = []

    for name in dirs:
        lane = path_to_lane.get(name)
        if lane:
            lanes[lane].append(name)
        else:
            unknown.append(name)

    duplicates = {path: sorted(lanes_) for path, lanes_ in duplicate_paths.items() if len(lanes_) > 1}
    return {"lanes": lanes, "unknown": unknown, "duplicates": duplicates}


def score_shape(total: int, unknown_count: int, generated_count: int, private_count: int) -> dict:
    known_ratio = 1.0 if total == 0 else (total - unknown_count) / total
    generated_ratio = 0.0 if total == 0 else generated_count / total
    private_ratio = 0.0 if total == 0 else private_count / total
    score = round(100 * known_ratio - 10 * generated_ratio - 5 * private_ratio, 1)
    return {
        "score": max(0.0, min(100.0, score)),
        "known_ratio": round(known_ratio, 4),
        "generated_ratio": round(generated_ratio, 4),
        "private_ratio": round(private_ratio, 4),
    }


def recommendations(report: dict) -> list[str]:
    lanes = report["lanes"]
    recs: list[str] = []

    if report["unknown"]:
        recs.append("Classify unknown top-level directories before moving files.")

    generated_count = len(lanes.get("generated", []))
    private_count = len(lanes.get("private", []))
    product_count = len(lanes.get("product", []))
    research_count = len(lanes.get("research", []))

    if generated_count:
        recs.append(
            "Keep generated/cache directories out of public narratives and package surfaces; clean only after verification."
        )
    if private_count:
        recs.append("Treat private/local directories as non-public state; never publish them without explicit review.")
    if product_count > 20:
        recs.append("Product lane is wide; pick one public demo/sales path and archive or defer the rest.")
    if research_count > 10:
        recs.append("Research lane is wide; require a one-line status for each active experiment before proposal reuse.")

    recs.append("Use this report as a map first, not a deletion plan.")
    return recs


def render_markdown(report: dict) -> str:
    lines = [
        "# Repo Surface Shape Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Root: `{report['root']}`",
        "",
        f"Shape score: **{report['score']['score']} / 100**",
        "",
        "| Lane | Count | Paths |",
        "| --- | ---: | --- |",
    ]
    for lane, paths in report["lanes"].items():
        rendered = ", ".join(f"`{p}`" for p in paths) if paths else "-"
        lines.append(f"| {lane} | {len(paths)} | {rendered} |")

    lines.extend(
        [
            "",
            "## Recommended Next Actions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["recommendations"])

    lines.extend(
        [
            "",
            "## Unknown Top-Level Directories",
            "",
        ]
    )
    if report["unknown"]:
        lines.extend(f"- `{name}`" for name in report["unknown"])
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This report is non-destructive and does not move files.",
            "- Unknown directories are not automatically bad; they are review targets.",
            "- Generated and private lanes should stay out of public/package surfaces unless explicitly needed.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(config_path: Path) -> dict:
    config = load_config(config_path)
    dirs = top_level_dirs(REPO_ROOT)
    classified = classify(dirs, config)
    lanes = classified["lanes"]
    total = len(dirs)
    score = score_shape(
        total=total,
        unknown_count=len(classified["unknown"]),
        generated_count=len(lanes.get("generated", [])),
        private_count=len(lanes.get("private", [])),
    )
    report = {
        "schema": "scbe_repo_surface_shape_report_v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": str(REPO_ROOT),
        "config": str(config_path),
        "total_top_level_dirs": total,
        "score": score,
        "lanes": lanes,
        "unknown": classified["unknown"],
        "duplicates": classified["duplicates"],
    }
    report["recommendations"] = recommendations(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.config)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out_dir / "latest.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"json": str(args.out_dir / "latest.json"), "markdown": str(args.out_dir / "latest.md"), "score": report["score"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
