#!/usr/bin/env python3
"""
24x7 SCBE operations loop (free/low-cost default).

Runs the local self-improvement stack in a safe, periodic cadence:
1) run_ops_autopilot.py (scan + postprocess + optional HF smoke + AI comm packet)
2) money_ops.py (revenue operations + readiness + provider probes)
3) local HF smoke SFT pass (non-GPU)

This wrapper is intentionally cheap-by-default and resumable:
- uses a lock file with stale-reaper window
- captures structured artifacts
- keeps a compact status report
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
AUTOPILOT_DIR = ROOT / "artifacts" / "ops-autopilot"
LOOP_DIR = AUTOPILOT_DIR / "24x7"
LOCK_FILE = LOOP_DIR / "24x7.lock"
LOG_FILE = LOOP_DIR / "loop.jsonl"
LATEST = AUTOPILOT_DIR / "24x7-latest.json"

RUN_OPS = ROOT / "scripts" / "run_ops_autopilot.py"
MONEY_OPS = ROOT / "scripts" / "money_ops.py"
MONEY_NIGHTLY = ROOT / "scripts" / "money_ops_nightly.py"
SMOKE_TRAIN = ROOT / "training" / "hf_smoke_sft_uv.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _acquire_lock(lock_path: Path, *, max_stale_seconds: int) -> bool:
    if lock_path.exists():
        payload = _read_json(lock_path)
        started = payload.get("started_utc")
        if started:
            try:
                age_sec = (datetime.now(timezone.utc) - datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds()
                if age_sec <= max_stale_seconds:
                    return False
            except Exception:
                return False
        lock_path.unlink()

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "run_id": _stamp(),
                "started_utc": _utc_now(),
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


def _run_cmd(cmd: List[str], *, timeout_sec: int, cwd: Path = ROOT, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    started = datetime.now(timezone.utc)
    started_s = started.isoformat().replace("+00:00", "Z")
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_sec,
            check=False,
        )
        finished = datetime.now(timezone.utc)
        return {
            "command": cmd,
            "started_utc": started_s,
            "finished_utc": finished.isoformat().replace("+00:00", "Z"),
            "elapsed_sec": round((finished - started).total_seconds(), 3),
            "return_code": completed.returncode,
            "status": "ok" if completed.returncode == 0 else "failed",
            "stdout_tail": (completed.stdout or "")[-4000:],
            "stderr_tail": (completed.stderr or "")[-4000:],
        }
    except subprocess.TimeoutExpired:
        finished = datetime.now(timezone.utc)
        return {
            "command": cmd,
            "started_utc": started_s,
            "finished_utc": finished.isoformat().replace("+00:00", "Z"),
            "elapsed_sec": round((finished - started).total_seconds(), 3),
            "return_code": 124,
            "status": "timeout",
            "stdout_tail": "",
            "stderr_tail": f"Timed out after {timeout_sec}s",
        }
    except Exception as exc:
        finished = datetime.now(timezone.utc)
        return {
            "command": cmd,
            "started_utc": started_s,
            "finished_utc": finished.isoformat().replace("+00:00", "Z"),
            "elapsed_sec": round((finished - started).total_seconds(), 3),
            "return_code": 255,
            "status": "error",
            "stdout_tail": "",
            "stderr_tail": repr(exc),
        }


def run_ops_cycle(args: argparse.Namespace, iteration: int) -> Dict[str, Any]:
    status: Dict[str, Any] = {
        "iteration": iteration,
        "started_utc": _utc_now(),
        "steps": {},
        "status": "ok",
    }

    ops_args = [sys.executable, str(RUN_OPS), "--scan-name", args.scan_name]
    if args.skip_smoke:
        ops_args.append("--skip-smoke")
    if args.obsidian_vault:
        ops_args.extend(["--obsidian-vault", args.obsidian_vault])
    status["steps"]["ops_autopilot"] = _run_cmd(ops_args, timeout_sec=args.max_runtime_sec_ops, cwd=ROOT)
    if status["steps"]["ops_autopilot"]["status"] != "ok":
        status["status"] = "blocked"

    if args.run_money:
        money_cmd = [sys.executable, str(MONEY_OPS), "run"]
        if args.money_spin:
            money_cmd.append("--spin")
            money_cmd.extend(["--spin-depth", str(args.money_spin_depth)])
            if args.money_topic:
                money_cmd.extend(["--spin-topic", args.money_topic])
        if args.money_probe:
            money_cmd.append("--probe")
        if args.marketplace_quote:
            money_cmd.append("--marketplace")
        status["steps"]["money_ops"] = _run_cmd(money_cmd, timeout_sec=args.max_runtime_sec_money, cwd=ROOT)
        if status["steps"]["money_ops"]["status"] != "ok":
            status["status"] = "blocked"

    if args.run_smoke:
        smoke_env = os.environ.copy()
        smoke_env.setdefault("SCBE_SMOKE_USE_CPU", "1")
        smoke_env.setdefault("SCBE_SMOKE_MAX_STEPS", str(args.hf_steps))
        status["steps"]["hf_smoke"] = _run_cmd(
            [sys.executable, str(SMOKE_TRAIN)],
            timeout_sec=args.max_runtime_sec_hf,
            cwd=ROOT,
            env=smoke_env,
        )
        if status["steps"]["hf_smoke"]["status"] != "ok":
            status["status"] = "blocked"

    status["finished_utc"] = _utc_now()
    return status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="24x7 SCBE ops loop runner")
    parser.add_argument("--scan-name", default="full_codebase", help="Scan label for run_ops_autopilot")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip run_ops_autopilot local smoke step")
    parser.add_argument("--obsidian-vault", default="", help="Optional Obsidian vault for run_ops_autopilot notes")
    parser.add_argument(
        "--run-money",
        action="store_true",
        default=False,
        help="Run money_ops during each cycle (cannot be used with --no-run-money)",
    )
    parser.add_argument(
        "--no-run-money",
        action="store_true",
        help="Skip money_ops during each cycle",
    )
    parser.add_argument("--money-spin", action="store_true", help="Enable spin topic expansion in money_ops")
    parser.add_argument("--money-spin-depth", type=int, default=2, help="Spin depth when --money-spin is set")
    parser.add_argument("--money-topic", default="", help="Spin topic string override")
    parser.add_argument("--money-probe", action="store_true", help="Probe up to 3 tentacles in money_ops")
    parser.add_argument("--marketplace-quote", action="store_true", help="Generate one quote via marketplace flow")
    parser.add_argument(
        "--run-smoke",
        action="store_true",
        default=False,
        help="Run local HF smoke SFT (cannot be used with --no-run-smoke)",
    )
    parser.add_argument(
        "--no-run-smoke",
        action="store_true",
        help="Skip local HF smoke SFT",
    )
    parser.add_argument("--hf-steps", type=int, default=6, help="Max HF smoke steps (small and cheap)")
    parser.add_argument("--repeat-every-minutes", type=int, default=240, help="Loop interval in minutes (0 = one-shot)")
    parser.add_argument("--iterations", type=int, default=1, help="How many cycles to run (default one-shot)")
    parser.add_argument("--max-runtime-sec-ops", type=int, default=1800, help="Timeout for ops_autopilot run")
    parser.add_argument("--max-runtime-sec-money", type=int, default=600, help="Timeout for money_ops run")
    parser.add_argument("--max-runtime-sec-hf", type=int, default=600, help="Timeout for hf smoke run")
    parser.add_argument("--max-stale-lock-sec", type=int, default=7200, help="Stale lock reclaim window")
    parser.add_argument("--skip-defaults", action="store_true", help="Do not enable money/smoke by default")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # Preserve cheap defaults while allowing explicit disable switches.
    # Keep money and smoke enabled by default for the free/low-cost loop.
    if args.skip_defaults:
        args.run_money = False
        args.run_smoke = False
    else:
        if args.no_run_money:
            args.run_money = False
        elif args.run_money is False:
            args.run_money = True

        if args.no_run_smoke:
            args.run_smoke = False
        elif args.run_smoke is False:
            args.run_smoke = True

    LOOP_DIR.mkdir(parents=True, exist_ok=True)

    if not _acquire_lock(LOCK_FILE, max_stale_seconds=args.max_stale_lock_sec):
        print("ops_24x7_autopilot: another run is already active. exiting.")
        return 2

    iteration = 0
    cycle_results: List[Dict[str, Any]] = []
    start_all = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        while True:
            iteration += 1
            cycle = run_ops_cycle(args, iteration)
            cycle_results.append(cycle)

            output_line = json.dumps(cycle, separators=(",", ":"))
            with LOG_FILE.open("a", encoding="utf-8") as fh:
                fh.write(output_line + "\n")

            latest_status = {
                "run_id": cycle.get("iteration"),
                "started_utc": start_all,
                "latest_cycle": cycle,
                "history_tail": cycle_results[-3:],
                "status": cycle["status"],
            }
            AUTOPILOT_DIR.mkdir(parents=True, exist_ok=True)
            LATEST.write_text(json.dumps(latest_status, indent=2), encoding="utf-8")

            if args.repeat_every_minutes <= 0 or iteration >= args.iterations:
                break

            sleep_sec = max(30, args.repeat_every_minutes * 60)
            print(f"ops_24x7_autopilot: sleeping {sleep_sec}s before next cycle...")
            time.sleep(sleep_sec)

    finally:
        _release_lock(LOCK_FILE)

    return 0 if (not cycle_results or cycle_results[-1].get("status") == "ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
