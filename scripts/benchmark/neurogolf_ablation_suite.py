#!/usr/bin/env python
"""Run and summarize the core NeuroGolf competition ablations.

This suite keeps the competition loop on one rail:
1. solver coverage on training
2. solver coverage on evaluation
3. token-braid family ranking on training
4. token-braid family ranking on evaluation

It writes the underlying benchmark JSON reports to `artifacts/` and emits a
single compact summary that is easy to compare across iterations.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO_ROOT / "artifacts"
TRAIN_REPORT = ARTIFACTS / "neurogolf_ablation_train.json"
EVAL_REPORT = ARTIFACTS / "neurogolf_ablation_eval.json"
BRAID_TRAIN_REPORT = ARTIFACTS / "neurogolf_braid_rank_train.json"
BRAID_EVAL_REPORT = ARTIFACTS / "neurogolf_braid_rank_eval.json"
EVAL_TASKS_DIR = REPO_ROOT / "artifacts" / "arc-data" / "ARC-AGI-master" / "data" / "evaluation"


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _family_set(report: dict[str, object]) -> set[str]:
    return {
        row["family"]
        for row in report["families"]
        if row["family"] != "no_program"
    }


def _format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def build_summary() -> dict[str, object]:
    train = _load(TRAIN_REPORT)
    eval_ = _load(EVAL_REPORT)
    braid_train = _load(BRAID_TRAIN_REPORT)
    braid_eval = _load(BRAID_EVAL_REPORT)

    train_summary = train["summary"]
    eval_summary = eval_["summary"]
    braid_train_metrics = braid_train["rank_metrics"]
    braid_eval_metrics = braid_eval["rank_metrics"]

    train_families = _family_set(train)
    eval_families = _family_set(eval_)

    return {
        "solver": {
            "train_solve_rate": train_summary["solve_rate"],
            "eval_solve_rate": eval_summary["solve_rate"],
            "generalization_ratio": (
                eval_summary["solve_rate"] / train_summary["solve_rate"]
                if train_summary["solve_rate"]
                else 0.0
            ),
            "train_solved": train_summary["solved"],
            "eval_solved": eval_summary["solved"],
            "train_avg_ms": train_summary["avg_elapsed_ms"],
            "eval_avg_ms": eval_summary["avg_elapsed_ms"],
            "family_overlap": sorted(train_families & eval_families),
            "train_only_families": sorted(train_families - eval_families),
            "eval_only_families": sorted(eval_families - train_families),
        },
        "ranking": {
            "train": {
                "flat_mean_rank": braid_train_metrics["flat_mean_rank"],
                "lattice_mean_rank": braid_train_metrics["lattice_mean_rank"],
                "charge_mean_rank": braid_train_metrics["charge_mean_rank"],
                "braid_mean_rank": braid_train_metrics["braid_mean_rank"],
                "null_braid_mean_rank": braid_train_metrics["null_braid_mean_rank"],
            },
            "eval": {
                "flat_mean_rank": braid_eval_metrics["flat_mean_rank"],
                "lattice_mean_rank": braid_eval_metrics["lattice_mean_rank"],
                "charge_mean_rank": braid_eval_metrics["charge_mean_rank"],
                "braid_mean_rank": braid_eval_metrics["braid_mean_rank"],
                "null_braid_mean_rank": braid_eval_metrics["null_braid_mean_rank"],
            },
        },
    }


def print_summary(summary: dict[str, object]) -> None:
    solver = summary["solver"]
    ranking = summary["ranking"]
    print(f"{'=' * 72}")
    print("NEUROGOLF ABLATION SUITE")
    print(f"{'=' * 72}")
    print("solver")
    print(f"  training solve rate : {_format_pct(solver['train_solve_rate'])} ({solver['train_solved']}/400)")
    print(f"  evaluation solve rate: {_format_pct(solver['eval_solve_rate'])} ({solver['eval_solved']}/400)")
    print(f"  generalization ratio: {solver['generalization_ratio']:.3f}")
    print(f"  avg ms/task (train) : {solver['train_avg_ms']}")
    print(f"  avg ms/task (eval)  : {solver['eval_avg_ms']}")
    print(f"  family overlap      : {', '.join(solver['family_overlap']) if solver['family_overlap'] else '(none)'}")
    print(f"  eval-only families  : {', '.join(solver['eval_only_families']) if solver['eval_only_families'] else '(none)'}")
    print()
    print("ranking")
    print(
        "  train ranks        : "
        f"flat={ranking['train']['flat_mean_rank']} "
        f"lattice={ranking['train']['lattice_mean_rank']} "
        f"charge={ranking['train']['charge_mean_rank']} "
        f"braid={ranking['train']['braid_mean_rank']} "
        f"null={ranking['train']['null_braid_mean_rank']}"
    )
    print(
        "  eval ranks         : "
        f"flat={ranking['eval']['flat_mean_rank']} "
        f"lattice={ranking['eval']['lattice_mean_rank']} "
        f"charge={ranking['eval']['charge_mean_rank']} "
        f"braid={ranking['eval']['braid_mean_rank']} "
        f"null={ranking['eval']['null_braid_mean_rank']}"
    )


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    _run([sys.executable, "scripts/benchmark/arc_batch.py", "--json", "--out", str(TRAIN_REPORT)])
    _run([sys.executable, "scripts/benchmark/arc_batch.py", "--eval", "--json", "--out", str(EVAL_REPORT)])
    _run([sys.executable, "scripts/benchmark/family_token_braid_rank.py", "--out", str(BRAID_TRAIN_REPORT)])
    _run(
        [
            sys.executable,
            "scripts/benchmark/family_token_braid_rank.py",
            "--tasks-dir",
            str(EVAL_TASKS_DIR),
            "--out",
            str(BRAID_EVAL_REPORT),
        ]
    )
    summary = build_summary()
    print_summary(summary)
    (ARTIFACTS / "neurogolf_ablation_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"\nsummary written to {ARTIFACTS / 'neurogolf_ablation_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
