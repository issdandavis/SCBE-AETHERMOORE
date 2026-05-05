"""argparse surface for training subcommands.

Designed to be embeddable inside scripts/scbe-system-cli.py via build_parser(),
or run standalone via `python -m src.training_cli`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.training_cli import guides as guides_module
from src.training_cli.heartbeat import read_heartbeat
from src.training_cli.quickstart import plan_quickstart, supported_trainers
from src.training_cli.runs import list_runs
from src.training_cli.status import collect_status
from src.training_cli.verdicts import load_verdicts

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def _fmt_ts(epoch_seconds: float) -> str:
    if epoch_seconds <= 0:
        return "-"
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    if n < 1024**3:
        return f"{n / 1024 / 1024:.1f} MB"
    return f"{n / 1024 / 1024 / 1024:.1f} GB"


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_status(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    status = collect_status(repo_root, verdict_limit=args.verdict_limit)
    if args.json:
        _print_json(status.to_dict())
        return 0

    print("=" * 72)
    print(f"SCBE training status @ {repo_root}")
    print("=" * 72)
    print(f"Latest verdict status: {status.latest_status}")
    if status.latest_pass_rate is not None:
        print(f"Latest pass_rate:      {status.latest_pass_rate:.2%}")
    print()
    print(f"Heartbeat ({status.heartbeat.health}):")
    if status.heartbeat.exists:
        print(f"  {status.heartbeat.line}")
        print(
            f"  length={status.heartbeat.length}  "
            f"ok={status.heartbeat.success_count}  "
            f"fail={status.heartbeat.fail_count}  "
            f"err={status.heartbeat.error_count}"
        )
    else:
        print(f"  no heartbeat file at {status.heartbeat.path}")
    print()
    print(f"Local runs ({len(status.runs)}):")
    for r in status.runs[:8]:
        print(
            f"  {r.name:<55} verdicts={r.verdict_count:<3} size={_fmt_size(r.size_bytes):<10} mtime={_fmt_ts(r.last_modified_ts)}"
        )
    if len(status.runs) > 8:
        print(f"  ... and {len(status.runs) - 8} more")
    print()
    print(f"Recent verdicts ({len(status.recent_verdicts)}):")
    for v in status.recent_verdicts:
        scaffold = "scaffold" if v.scaffold else "no-scaffold" if v.scaffold is False else "?"
        rate = f"{v.pass_rate:.0%}" if v.pass_rate is not None else "?"
        print(f"  {v.status:<6} {rate:<5} {scaffold:<11} {v.run_name:<50} job={v.job_id}")
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    runs_root = repo_root / "training" / "runs"
    runs = list_runs(runs_root)
    if args.json:
        _print_json([r.to_summary_dict() for r in runs])
        return 0

    print(f"Training runs at {runs_root}: {len(runs)}")
    for r in runs:
        print(
            f"  {r.name:<55} verdicts={r.verdict_count:<3} size={_fmt_size(r.size_bytes):<10} mtime={_fmt_ts(r.last_modified_ts)}"
        )
    return 0


def cmd_verdicts(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    runs_root = repo_root / "training" / "runs"
    verdicts = load_verdicts(runs_root, limit=args.last)
    if args.json:
        _print_json([v.to_summary_dict() for v in verdicts])
        return 0

    print(f"Recent verdicts (last {args.last}):")
    print(f"  {'STATUS':<7} {'RATE':<5} {'SCAFFOLD':<12} {'RUN':<50} {'JOB':<30}")
    for v in verdicts:
        scaffold = "scaffold" if v.scaffold else "no-scaffold" if v.scaffold is False else "?"
        rate = f"{v.pass_rate:.0%}" if v.pass_rate is not None else "?"
        print(f"  {v.status:<7} {rate:<5} {scaffold:<12} {v.run_name:<50} {v.job_id:<30}")
    return 0


def cmd_heartbeat(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    hb = read_heartbeat(repo_root)
    if args.json:
        _print_json(hb.to_summary_dict())
        return 0

    print(f"Heartbeat: {hb.path}")
    print(f"  exists:        {hb.exists}")
    print(f"  health:        {hb.health}")
    print(f"  line ({hb.length} chars):")
    if hb.line:
        print(f"  {hb.line}")
    print(f"  ok={hb.success_count}  fail={hb.fail_count}  err={hb.error_count}")
    return 0


def cmd_guide(args: argparse.Namespace) -> int:
    topics = guides_module.list_topics()
    if not args.topic:
        print(f"Available guides: {', '.join(topics)}")
        print("Usage: training guide <topic>")
        return 0

    body = guides_module.read_guide(args.topic)
    if body is None:
        print(f"unknown topic '{args.topic}'. Available: {', '.join(topics)}", file=sys.stderr)
        return 1
    print(body, end="" if body.endswith("\n") else "\n")
    return 0


def cmd_quickstart(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    plan = plan_quickstart(
        base_model=args.base_model,
        dataset_path=args.data,
        run_name=args.run_name,
        trainer=args.trainer,
        flavor=args.flavor,
        repo_root=repo_root,
    )
    if args.json:
        _print_json(plan.to_dict())
        return 0

    print("=" * 72)
    print(f"Quickstart plan for run '{plan.run_name}' (trainer={plan.trainer})")
    print("=" * 72)
    print(f"Base model: {plan.base_model}")
    print(f"Dataset:    {plan.dataset_path}")
    print(f"Flavor:     {plan.flavor}")
    print()
    print("Run this command to dispatch:")
    print()
    print("  " + " ".join(plan.command))
    print()
    if plan.notes:
        print("Notes:")
        for note in plan.notes:
            print(f"  - {note}")
    return 0


def build_parser(prog: str = "training") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description="SCBE training extension CLI")
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Path to the SCBE-AETHERMOORE repo root (default: this checkout).",
    )

    sub = parser.add_subparsers(dest="train_cmd", required=True)

    p_status = sub.add_parser("status", help="Unified training status: runs + verdicts + heartbeat")
    p_status.add_argument("--verdict-limit", type=int, default=10)
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_runs = sub.add_parser("runs", help="List local training runs")
    p_runs.add_argument("--json", action="store_true")
    p_runs.set_defaults(func=cmd_runs)

    p_verd = sub.add_parser("verdicts", help="List recent run verdicts")
    p_verd.add_argument("--last", type=int, default=10)
    p_verd.add_argument("--json", action="store_true")
    p_verd.set_defaults(func=cmd_verdicts)

    p_hb = sub.add_parser("heartbeat", help="Show the night-training-watch heartbeat line")
    p_hb.add_argument("--json", action="store_true")
    p_hb.set_defaults(func=cmd_heartbeat)

    p_guide = sub.add_parser("guide", help="Built-in training guides")
    p_guide.add_argument("topic", nargs="?", default=None, help=f"One of: {', '.join(guides_module.list_topics())}")
    p_guide.set_defaults(func=cmd_guide)

    p_quick = sub.add_parser("quickstart", help="Print a dispatch command for a new training run (does not execute)")
    p_quick.add_argument("--run-name", required=True)
    p_quick.add_argument("--base-model", required=True)
    p_quick.add_argument("--data", required=True, help="Dataset path relative to repo root")
    p_quick.add_argument("--trainer", default="sft", choices=supported_trainers())
    p_quick.add_argument("--flavor", default="default")
    p_quick.add_argument("--json", action="store_true")
    p_quick.set_defaults(func=cmd_quickstart)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
