#!/usr/bin/env python3
"""Cron-ready wrapper for money_ops with lock + logging + machine-readable summaries."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def paths() -> Dict[str, Path]:
    root = REPO_ROOT / "artifacts" / "money_ops" / "nightly"
    return {
        "root": root,
        "log_dir": root,
        "lock": root / "money_ops_nightly.lock",
        "latest": root / "latest.json",
    }


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _acquire_lock(lock_path: Path, max_stale_seconds: int) -> bool:
    if lock_path.exists():
        existing = _read_json(lock_path)
        started = existing.get("started_utc", "")
        if started:
            try:
                started_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                age_sec = (datetime.now(timezone.utc) - started_dt).total_seconds()
                if age_sec <= max_stale_seconds:
                    return False
            except Exception:
                return False
        lock_path.unlink()

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps(
            {
                "started_utc": _utc_now(),
                "pid": os.getpid(),
                "run_id": _stamp(),
                "host": os.getenv("COMPUTERNAME", "local"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return True


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def build_command(args: argparse.Namespace) -> List[str]:
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "money_ops.py"), "run"]
    if args.spin:
        cmd.append("--spin")
    if args.spin_topic:
        cmd += ["--spin-topic", args.spin_topic]
    if args.spin_depth:
        cmd += ["--spin-depth", str(args.spin_depth)]
    if args.probe:
        cmd.append("--probe")
    if args.marketplace:
        cmd.append("--marketplace")
    if args.push_hf:
        cmd.append("--push-hf")
    return cmd


def run_money_cmd(cmd: List[str], log_file: Path, timeout_sec: int) -> Dict[str, Any]:
    started = datetime.now(timezone.utc)
    started_s = started.isoformat().replace("+00:00", "Z")

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        finished = datetime.now(timezone.utc)
        text = f"Timed out after {exc.timeout:.1f}s"
        log_file.write_text(text + "\n", encoding="utf-8")
        return {
            "started_utc": started_s,
            "finished_utc": finished.isoformat().replace("+00:00", "Z"),
            "return_code": 124,
            "elapsed_sec": round((finished - started).total_seconds(), 3),
            "command": cmd,
            "output_preview": text,
            "log": str(log_file),
            "status": "timeout",
        }

    finished = datetime.now(timezone.utc)
    output = (completed.stdout or "") + (completed.stderr or "")
    payload = [
        f"Run started: {started_s}",
        f"Run finished: {finished.isoformat().replace('+00:00', 'Z')}",
        f"Command: {' '.join(cmd)}",
        f"Return code: {completed.returncode}",
        "=" * 80,
        output,
    ]
    log_file.write_text("\n".join(payload), encoding="utf-8")

    return {
        "started_utc": started_s,
        "finished_utc": finished.isoformat().replace("+00:00", "Z"),
        "return_code": completed.returncode,
        "elapsed_sec": round((finished - started).total_seconds(), 3),
        "command": cmd,
        "output_preview": output[-3000:],
        "log": str(log_file),
        "status": "ok" if completed.returncode == 0 else "failed",
    }


def money_last_summary() -> Dict[str, Any]:
    path = REPO_ROOT / "artifacts" / "money_ops" / "last_run.json"
    return _read_json(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run money_ops as a non-interactive nightly workflow"
    )
    parser.add_argument("--spin", action="store_true", help="Run revenue spin pipeline")
    parser.add_argument("--spin-topic", default="", help="Override topic for spin pipeline")
    parser.add_argument("--spin-depth", type=int, default=2, help="Spin depth")
    parser.add_argument("--probe", action="store_true", help="Probe 1-3 tentacles")
    parser.add_argument("--marketplace", action="store_true", help="Generate sample marketplace quote")
    parser.add_argument("--push-hf", action="store_true", help="Push training log to HuggingFace")
    parser.add_argument("--dry-run", action="store_true", help="Show planned command without running")
    parser.add_argument("--max-runtime-sec", type=int, default=600, help="Subprocess timeout in seconds")
    parser.add_argument("--max-stale-lock-sec", type=int, default=10800, help="Stale-lock reclaim window")
    parser.add_argument("--force", action="store_true", help="Ignore stale lock and force run")
    parser.add_argument("--note-dir", default="", help="Optional notes output directory")
    return parser.parse_args()


def maybe_write_note(note_dir: str, payload: Dict[str, Any]) -> str | None:
    if not note_dir:
        return None

    note_path = Path(note_dir)
    note_path.mkdir(parents=True, exist_ok=True)
    target = note_path / f"{_stamp()}_nightly_money_ops.md"
    target.write_text(
        "\n".join(
            [
                f"# Money Ops Nightly ({payload['run_id']})",
                "",
                f"status: {payload['status']}",
                f"started_utc: {payload['started_utc']}",
                f"finished_utc: {payload['finished_utc']}",
                f"command: {' '.join(payload['money_ops_run']['command'])}",
                f"return_code: {payload['money_ops_run']['return_code']}",
                f"log: {payload['money_ops_run']['log']}",
                "",
                "## Money Ops Last Summary",
                json.dumps(payload.get("money_ops_last_run", {}), indent=2),
            ]
        ),
        encoding="utf-8",
    )
    return str(target)


def main() -> int:
    args = parse_args()
    p = paths()
    p["root"].mkdir(parents=True, exist_ok=True)

    lock_file = p["lock"]
    if not args.force and not _acquire_lock(lock_file, args.max_stale_lock_sec):
        payload = {
            "status": "skipped",
            "reason": "lock_active",
            "lock": str(lock_file),
            "started_utc": _utc_now(),
        }
        p["latest"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("money_ops_nightly: another run is active. exiting.")
        return 2

    try:
        cmd = build_command(args)
        if args.dry_run:
            result = {
                "status": "skipped",
                "reason": "dry_run",
                "command": cmd,
                "started_utc": _utc_now(),
                "finished_utc": _utc_now(),
                "return_code": 0,
                "output_preview": "dry-run only",
                "log": "",
                "elapsed_sec": 0.0,
            }
            payload = {
                "run_id": _stamp(),
                "status": "skipped",
                "money_ops_run": result,
                "money_ops_last_run": money_last_summary(),
                "command": cmd,
                "started_utc": result["started_utc"],
                "finished_utc": result["finished_utc"],
            }
            p["latest"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print("dry-run command:")
            print(" ".join(cmd))
            return 0

        log_file = p["log_dir"] / f"{_stamp()}_money_ops_nightly.log"
        run = run_money_cmd(cmd, log_file, timeout_sec=args.max_runtime_sec)

        payload = {
            "run_id": _stamp(),
            "status": run["status"],
            "command": cmd,
            "money_ops_run": run,
            "money_ops_last_run": money_last_summary(),
            "started_utc": run["started_utc"],
            "finished_utc": run["finished_utc"],
        }

        if payload["status"] == "ok":
            payload["note"] = maybe_write_note(args.note_dir, payload)

        p["latest"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0 if payload["status"] == "ok" else 1
    finally:
        _release_lock(lock_file)


if __name__ == "__main__":
    raise SystemExit(main())
