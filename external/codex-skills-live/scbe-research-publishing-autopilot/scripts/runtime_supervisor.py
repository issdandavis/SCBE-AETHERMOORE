#!/usr/bin/env python3
"""
Run a multi-hour SCBE research publishing loop with retrigger monitoring.

This orchestrates existing scripts in this skill:
- context_packer.py
- claim_gate.py
- campaign_orchestrator.py
- publish_dispatch.py
- retrigger_monitor.py
- write_obsidian_report.py (optional)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-hour autopilot supervisor.")
    parser.add_argument("--working-dir", required=True, help="Working directory for artifacts")
    parser.add_argument("--repo-root", required=True, help="Repo root for claim source checks")
    parser.add_argument("--campaign", required=True, help="Campaign JSON")
    parser.add_argument("--posts", required=True, help="Campaign posts JSON")
    parser.add_argument("--posts-history", required=True, help="Historical posts JSONL")
    parser.add_argument("--dataset-manifest", required=True, help="Dataset manifest JSON")
    parser.add_argument("--connectors", required=True, help="Connectors JSON")
    parser.add_argument("--approval", default="", help="Approval JSON")
    parser.add_argument("--retrigger-rules", required=True, help="Retrigger rules JSON")
    parser.add_argument("--metrics", required=True, help="Metrics JSONL")
    parser.add_argument("--run-hours", type=float, default=8.0, help="Supervisor runtime in hours")
    parser.add_argument("--heartbeat-minutes", type=int, default=15, help="Cycle interval")
    parser.add_argument("--vault-dir", default="", help="Optional Obsidian vault path")
    parser.add_argument("--campaign-id", default="campaign", help="Campaign id for daily note naming")
    parser.add_argument("--allow-unapproved", action="store_true", help="Bypass approval gate")
    parser.add_argument("--dry-run", action="store_true", help="Dry run dispatch")
    parser.add_argument("--once", action="store_true", help="Run one cycle only")
    return parser.parse_args()


def ts_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_cmd(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0:
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    py = sys.executable

    working = Path(args.working_dir)
    working.mkdir(parents=True, exist_ok=True)

    context_pack = working / "self_context_pack.json"
    claim_report = working / "claim_gate_report.json"
    dispatch_plan = working / "dispatch_plan.json"
    dispatch_log = working / "dispatch_log.jsonl"
    dispatch_state = working / "dispatch_state.json"
    retrigger_actions = working / "retrigger_actions.json"
    retrigger_state = working / "retrigger_state.json"
    runtime_status = working / "runtime_status.json"

    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=max(1.0, args.run_hours))
    cycle = 0

    while True:
        now = datetime.now(timezone.utc)
        if args.once and cycle > 0:
            break
        if now > end:
            break

        print(f"[supervisor] cycle={cycle} now={ts_iso(now)}")

        # Step 1: context-of-self refresh
        run_cmd(
            [
                py,
                str(script_dir / "context_packer.py"),
                "--posts-history",
                args.posts_history,
                "--dataset-manifest",
                args.dataset_manifest,
                "--out",
                str(context_pack),
            ]
        )

        # Step 2: claim gate (hard block on fail)
        run_cmd(
            [
                py,
                str(script_dir / "claim_gate.py"),
                "--posts",
                args.posts,
                "--repo-root",
                args.repo_root,
                "--out",
                str(claim_report),
            ]
        )

        # Step 3: refresh schedule window
        run_cmd(
            [
                py,
                str(script_dir / "campaign_orchestrator.py"),
                "--campaign",
                args.campaign,
                "--out",
                str(dispatch_plan),
                "--now",
                ts_iso(now),
            ]
        )

        # Step 4: dispatch due events (approval-gated)
        execute_until = now + timedelta(minutes=max(5, args.heartbeat_minutes))
        dispatch_cmd = [
            py,
            str(script_dir / "publish_dispatch.py"),
            "--plan",
            str(dispatch_plan),
            "--posts",
            args.posts,
            "--connectors",
            args.connectors,
            "--claim-report",
            str(claim_report),
            "--out-log",
            str(dispatch_log),
            "--state",
            str(dispatch_state),
            "--execute-until",
            ts_iso(execute_until),
        ]
        if args.approval:
            dispatch_cmd.extend(["--approval", args.approval])
        if args.allow_unapproved:
            dispatch_cmd.append("--allow-unapproved")
        if args.dry_run:
            dispatch_cmd.append("--dry-run")
        run_cmd(dispatch_cmd)

        # Step 5: retrigger monitor
        run_cmd(
            [
                py,
                str(script_dir / "retrigger_monitor.py"),
                "--metrics",
                args.metrics,
                "--rules",
                args.retrigger_rules,
                "--state",
                str(retrigger_state),
                "--out",
                str(retrigger_actions),
                "--now",
                ts_iso(datetime.now(timezone.utc)),
            ]
        )

        # Step 6: optional Obsidian report write
        if args.vault_dir:
            run_cmd(
                [
                    py,
                    str(script_dir / "write_obsidian_report.py"),
                    "--vault-dir",
                    args.vault_dir,
                    "--dispatch-log",
                    str(dispatch_log),
                    "--claim-report",
                    str(claim_report),
                    "--retrigger-actions",
                    str(retrigger_actions),
                    "--self-context",
                    str(context_pack),
                    "--campaign-id",
                    args.campaign_id,
                ]
            )

        runtime_status.write_text(
            (
                "{\n"
                f'  "cycle": {cycle},\n'
                f'  "updated_at": "{ts_iso(datetime.now(timezone.utc))}",\n'
                f'  "window_end": "{ts_iso(end)}"\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        cycle += 1
        if args.once:
            break
        sleep_seconds = max(60, args.heartbeat_minutes * 60)
        time.sleep(sleep_seconds)

    print("[supervisor] completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
