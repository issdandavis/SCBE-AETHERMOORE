"""Score Kaggle training rounds against reusable winner-pattern safeguards.

This is not a leaderboard predictor. It checks whether a round has the traits
that repeatedly show up in strong Kaggle workflows: trusted validation, a
small experiment surface, checkpointed history, anchor data, and promotion
discipline before ensembling/merging.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_PATH = REPO_ROOT / "scripts" / "kaggle_auto" / "launch.py"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "training_reports"


def load_rounds() -> dict[str, dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("scbe_kaggle_launch", LAUNCH_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {LAUNCH_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return dict(module.ROUNDS)


def has_any(files: list[str], needles: tuple[str, ...]) -> bool:
    haystack = "\n".join(files).lower()
    return any(needle in haystack for needle in needles)


def score_round(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    files = cfg.get("files")
    train_files = [] if files == "__ALL__" else list(files or [])
    eval_files = list(cfg.get("eval_files") or [])
    all_files = train_files + eval_files
    checks: list[dict[str, Any]] = []

    def add(check: str, passed: bool, weight: int, note: str) -> None:
        checks.append({"check": check, "passed": bool(passed), "weight": weight, "note": note})

    add(
        "trusted_validation",
        bool(eval_files),
        20,
        "Winning Kaggle workflows trust validation/CV before leaderboard or merge decisions.",
    )
    add(
        "bounded_experiment",
        int(cfg.get("max_records", 999999)) <= 5000 and int(cfg.get("max_steps", 999999)) <= 500,
        15,
        "Small bounded runs are easier to compare and debug than long uncontrolled runs.",
    )
    add(
        "anchor_replay",
        has_any(all_files, ("aligned", "governance", "stage6", "command_lattice", "repair")),
        20,
        "Anchor/replay data reduces catastrophic forgetting in specialist adapters.",
    )
    add(
        "low_overfit_capacity",
        int(cfg.get("lora_r", 999)) <= 16 and float(cfg.get("lora_dropout", 0.0)) >= 0.05,
        15,
        "Lower LoRA capacity and dropout reduce memorization risk on narrow lanes.",
    )
    add(
        "remote_lineage",
        bool(cfg.get("hf_repo")) and bool(cfg.get("hf_dataset_repo")),
        10,
        "Remote adapter and dataset lineage make outputs reproducible and auditable.",
    )
    add(
        "t4_safe_shape",
        int(cfg.get("max_length", 999999)) <= 1024 and int(cfg.get("batch_size", 99)) <= 2,
        10,
        "T4-safe sequence/batch sizes reduce OOM and silent runtime failure.",
    )
    add(
        "specialist_not_monolith",
        files != "__ALL__" and 1 <= len(train_files) <= 20,
        10,
        "Winning builds iterate narrow hypotheses before blending/ensembling.",
    )

    total = sum(item["weight"] for item in checks)
    earned = sum(item["weight"] for item in checks if item["passed"])
    score = round(100 * earned / total, 2) if total else 0.0
    if score >= 85:
        verdict = "LAUNCH_READY_PATTERN"
    elif score >= 65:
        verdict = "USABLE_WITH_GAPS"
    else:
        verdict = "REWORK_BEFORE_LAUNCH"
    return {
        "round": name,
        "description": cfg.get("desc", ""),
        "score": score,
        "verdict": verdict,
        "train_file_count": len(train_files),
        "eval_file_count": len(eval_files),
        "checks": checks,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Kaggle Winner-Pattern Round Score",
        "",
        f"Generated: `{report['generated_at_utc']}`",
        "",
        "| Round | Score | Verdict | Train Files | Eval Files |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for row in report["rounds"]:
        lines.append(
            f"| `{row['round']}` | {row['score']} | `{row['verdict']}` | "
            f"{row['train_file_count']} | {row['eval_file_count']} |"
        )
    lines.extend(
        [
            "",
            "## Pattern Checks",
            "",
            "- `trusted_validation`: eval or CV exists before promotion.",
            "- `bounded_experiment`: capped records/steps for quick iteration.",
            "- `anchor_replay`: governance/alignment/Stage 6/command anchors are present.",
            "- `low_overfit_capacity`: LoRA rank/dropout reduce memorization.",
            "- `remote_lineage`: adapter and dataset repos are explicit.",
            "- `t4_safe_shape`: sequence and batch fit free Kaggle GPUs.",
            "- `specialist_not_monolith`: round tests a narrow hypothesis before merging.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", dest="round_name", help="Score one round only.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    rounds = load_rounds()
    names = [args.round_name] if args.round_name else sorted(rounds)
    scored = []
    for name in names:
        if name not in rounds:
            raise SystemExit(f"unknown round: {name}")
        scored.append(score_round(name, rounds[name]))
    scored.sort(key=lambda row: (-row["score"], row["round"]))

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "schema_version": "scbe_kaggle_winner_pattern_score_v1",
        "generated_at_utc": generated,
        "source": str(LAUNCH_PATH.relative_to(REPO_ROOT)),
        "rounds": scored,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = args.round_name or "all"
    json_path = args.output_dir / f"kaggle_winner_patterns_{suffix}.json"
    md_path = args.output_dir / f"kaggle_winner_patterns_{suffix}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(md_path, report)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "rounds": scored}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
