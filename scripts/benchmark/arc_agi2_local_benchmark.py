#!/usr/bin/env python3
"""Local ARC-AGI-2 baseline benchmark.

Loads tasks from artifacts/arc-data/data/{training,evaluation}/, applies
several rule-free baselines (identity, last-train-output, majority-color,
random), scores exact grid match, and records claim-bounded results.

This is not a submission to the ARC Prize. It establishes:
  1. The harness runs and scores correctly.
  2. The public data is accessible locally.
  3. Baseline solve rates before any real solver is attached.

Data source: https://github.com/arcprize/ARC-AGI-2 (cloned to artifacts/arc-data)
"""

from __future__ import annotations

import argparse
import collections
import json
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "artifacts" / "arc-data" / "data"
DEFAULT_OUT = REPO_ROOT / "artifacts" / "benchmarks" / "arc_agi2_local"

Grid = list[list[int]]


# ──────────────────────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ArcPair:
    input: Grid
    output: Grid


@dataclass(frozen=True)
class ArcTask:
    task_id: str
    train: tuple[ArcPair, ...]
    test_input: Grid
    test_output: Grid  # visible in the local data for both splits


def _load_tasks(split: str, limit: int | None = None) -> list[ArcTask]:
    split_dir = DATA_ROOT / split
    if not split_dir.exists():
        raise FileNotFoundError(
            f"ARC-AGI-2 data not found at {split_dir}. "
            "Run: git clone --depth 1 https://github.com/arcprize/ARC-AGI-2 artifacts/arc-data"
        )
    paths = sorted(split_dir.glob("*.json"))
    if limit is not None:
        paths = paths[:limit]
    tasks = []
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        train = tuple(ArcPair(input=pair["input"], output=pair["output"]) for pair in d["train"])
        test_entry = d["test"][0]
        tasks.append(
            ArcTask(
                task_id=p.stem,
                train=train,
                test_input=test_entry["input"],
                test_output=test_entry["output"],
            )
        )
    return tasks


# ──────────────────────────────────────────────────────────────────────────────
# Baseline solvers
# ──────────────────────────────────────────────────────────────────────────────


def _dims(grid: Grid) -> tuple[int, int]:
    return len(grid), len(grid[0]) if grid else 0


def solve_identity(task: ArcTask) -> Grid:
    """Return the test input unchanged — tests whether the task is identity-mapped."""
    return [row[:] for row in task.test_input]


def solve_last_train_output(task: ArcTask) -> Grid:
    """Return the last training output — a naive frequency heuristic."""
    return [row[:] for row in task.train[-1].output]


def solve_majority_color(task: ArcTask) -> Grid:
    """Fill a grid of the same size as the test input with the most common output color."""
    counter: collections.Counter[int] = collections.Counter()
    for pair in task.train:
        for row in pair.output:
            counter.update(row)
    dominant = counter.most_common(1)[0][0] if counter else 0
    rows, cols = _dims(task.test_input)
    return [[dominant] * cols for _ in range(rows)]


def solve_random(task: ArcTask, *, rng: random.Random) -> Grid:
    """Generate a random grid matching the test-input dimensions, colors from training."""
    color_pool: list[int] = []
    for pair in task.train:
        for row in pair.output:
            color_pool.extend(row)
    if not color_pool:
        color_pool = list(range(10))
    rows, cols = _dims(task.test_input)
    return [[rng.choice(color_pool) for _ in range(cols)] for _ in range(rows)]


SOLVERS: dict[str, Any] = {
    "identity": solve_identity,
    "last_train_output": solve_last_train_output,
    "majority_color": solve_majority_color,
    "random": solve_random,
}


# ──────────────────────────────────────────────────────────────────────────────
# Scoring
# ──────────────────────────────────────────────────────────────────────────────


def score_prediction(pred: Grid, gold: Grid) -> bool:
    """Exact grid match — the only accepted ARC scoring criterion."""
    if len(pred) != len(gold):
        return False
    for pred_row, gold_row in zip(pred, gold):
        if pred_row != gold_row:
            return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class SolverResult:
    solver: str
    passes: int
    task_count: int
    pass_rate: float
    duration_ms: int
    sample_failures: list[dict[str, Any]] = field(default_factory=list)


def run_solver(tasks: list[ArcTask], solver_name: str, *, seed: int = 42) -> SolverResult:
    fn = SOLVERS[solver_name]
    rng = random.Random(seed)
    passes = 0
    failures: list[dict[str, Any]] = []
    start = time.perf_counter()
    for task in tasks:
        if solver_name == "random":
            pred = fn(task, rng=rng)
        else:
            pred = fn(task)
        ok = score_prediction(pred, task.test_output)
        if ok:
            passes += 1
        elif len(failures) < 3:
            failures.append(
                {
                    "task_id": task.task_id,
                    "pred_dims": _dims(pred),
                    "gold_dims": _dims(task.test_output),
                }
            )
    duration_ms = int((time.perf_counter() - start) * 1000)
    return SolverResult(
        solver=solver_name,
        passes=passes,
        task_count=len(tasks),
        pass_rate=round(passes / len(tasks), 4) if tasks else 0.0,
        duration_ms=duration_ms,
        sample_failures=failures,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def build_report(
    *,
    split: str = "evaluation",
    limit: int | None = None,
    solvers: list[str] | None = None,
    out_dir: Path = DEFAULT_OUT,
    run_id: str | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    if solvers is None:
        solvers = ["last_train_output", "identity", "majority_color", "random"]
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir / run_id

    tasks = _load_tasks(split, limit)
    task_count = len(tasks)

    results = [run_solver(tasks, s, seed=seed) for s in solvers]

    best = max(results, key=lambda r: r.pass_rate)

    report: dict[str, Any] = {
        "schema_version": "scbe_arc_agi2_local_v1",
        "generated_at_utc": _utc_now(),
        "run_id": run_id,
        "split": split,
        "task_count": task_count,
        "limit": limit,
        "seed": seed,
        "data_source": str(DATA_ROOT),
        "baselines": [asdict(r) for r in results],
        "best_baseline": {"solver": best.solver, "pass_rate": best.pass_rate},
        "claim_boundary": [
            "Local ARC-AGI-2 evaluation using the public cloned dataset.",
            "Baselines are rule-free: identity, last-train-output, majority-color, random.",
            "No program synthesis, no LLM, no search — these are lower-bound reference points.",
            "An agent lane would need program synthesis or LLM reasoning attached to this harness.",
            "This is not a submission to arcprize.org or a public leaderboard claim.",
        ],
        "public_context": {
            "human_performance": "~60% (ARC-AGI-2 calibrated harder than ARC-AGI-1)",
            "top_ai_2025": "~4-5% on public leaderboard at competition launch",
            "arc_prize_url": "https://arcprize.org/arc-agi/2",
        },
    }

    _write_json(run_dir / "report.json", report)
    _write_json(out_dir / "latest_report.json", report)
    (run_dir / "REPORT.md").write_text(_render_markdown(report), encoding="utf-8")
    (out_dir / "LATEST.md").write_text(_render_markdown(report), encoding="utf-8")
    return report


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCBE ARC-AGI-2 Local Baseline Benchmark",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Run ID: `{report['run_id']}`",
        f"- Split: `{report['split']}`",
        f"- Tasks: `{report['task_count']}`",
        f"- Best baseline: `{report['best_baseline']['solver']}` "
        f"pass_rate=`{report['best_baseline']['pass_rate']}`",
        "",
        "## Baseline Solvers",
        "",
        "| Solver | Passes | Tasks | Pass rate | ms |",
        "|---|---:|---:|---:|---:|",
    ]
    for b in report["baselines"]:
        lines.append(
            f"| `{b['solver']}` | {b['passes']} | {b['task_count']} " f"| `{b['pass_rate']}` | {b['duration_ms']} |"
        )
    lines.extend(
        [
            "",
            "## Public Context",
            "",
            f"- Human performance: {report['public_context']['human_performance']}",
            f"- Top AI 2025: {report['public_context']['top_ai_2025']}",
            f"- ARC Prize: {report['public_context']['arc_prize_url']}",
            "",
            "## Claim Boundary",
            "",
            *[f"- {item}" for item in report["claim_boundary"]],
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split",
        default="evaluation",
        choices=["training", "evaluation"],
        help="Which data split to run (default: evaluation, 120 tasks).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of tasks (useful for smoke tests).",
    )
    parser.add_argument(
        "--solvers",
        default="last_train_output,identity,majority_color,random",
        help="Comma-separated solver names.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(
        split=args.split,
        limit=args.limit,
        solvers=args.solvers.split(","),
        out_dir=args.out_dir,
        run_id=args.run_id or None,
        seed=args.seed,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print(
            f"arc-agi-2 local baseline: split={report['split']} "
            f"tasks={report['task_count']} "
            f"best={report['best_baseline']['solver']}@{report['best_baseline']['pass_rate']}"
        )
        for b in report["baselines"]:
            print(
                f"  {b['solver']:25s} {b['passes']:3d}/{b['task_count']}  ({b['pass_rate']:.4f})  {b['duration_ms']}ms"
            )
        print(f"report={args.out_dir / report['run_id'] / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
