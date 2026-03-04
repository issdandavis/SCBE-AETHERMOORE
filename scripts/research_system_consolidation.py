#!/usr/bin/env python3
"""SCBE research consolidation orchestrator.

Chains the existing cloud kernel dataset pipeline and local->cloud autosync runner
into one auditable execution path, without duplicating existing logic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = "training/research_consolidation.json"
DEFAULT_RUN_ROOT = "training/runs/research_consolidation"
DEFAULT_LATEST_POINTER = "training/ingest/latest_research_consolidation.txt"


@dataclass
class StepResult:
    step: str
    command: List[str]
    returncode: int
    duration_ms: int
    started_at: str
    ended_at: str
    log_path: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run SCBE deep research consolidation and cloud automation chain."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Config path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--run-root", default=DEFAULT_RUN_ROOT, help=f"Run root (default: {DEFAULT_RUN_ROOT})")
    parser.add_argument(
        "--latest-pointer",
        default=DEFAULT_LATEST_POINTER,
        help=f"Latest pointer path (default: {DEFAULT_LATEST_POINTER})",
    )
    parser.add_argument("--no-upload", action="store_true", help="Disable cloud upload in both steps.")
    parser.add_argument("--sync-notion", action="store_true", help="Force Notion sync during cloud ingest.")
    parser.add_argument("--ship-targets", default="", help="CSV targets override for both steps.")
    parser.add_argument("--once", action="store_true", help="Force one-shot local autosync.")
    parser.add_argument("--force-local-snapshot", action="store_true", help="Force local autosync snapshot.")
    parser.add_argument("--skip-cloud", action="store_true", help="Skip cloud kernel pipeline step.")
    parser.add_argument("--skip-local", action="store_true", help="Skip local autosync step.")
    parser.add_argument("--allow-quarantine", action="store_true", help="Allow quarantined cloud dataset run.")
    parser.add_argument("--ship-on-quarantine", action="store_true", help="Ship even on quarantine.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only.")
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Invalid config payload: {path}")
    return parsed


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_step(step: str, command: List[str], run_dir: Path, dry_run: bool) -> StepResult:
    started = datetime.now(timezone.utc)
    log_file = run_dir / f"{step}.log"
    if dry_run:
        log_file.write_text("[dry-run] " + " ".join(shlex.quote(x) for x in command) + "\n", encoding="utf-8")
        ended = datetime.now(timezone.utc)
        return StepResult(
            step=step,
            command=command,
            returncode=0,
            duration_ms=int((ended - started).total_seconds() * 1000),
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            log_path=str(log_file.relative_to(REPO_ROOT)).replace("\\", "/"),
        )

    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log_file.write_text(proc.stdout or "", encoding="utf-8")
    ended = datetime.now(timezone.utc)
    return StepResult(
        step=step,
        command=command,
        returncode=proc.returncode,
        duration_ms=int((ended - started).total_seconds() * 1000),
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        log_path=str(log_file.relative_to(REPO_ROOT)).replace("\\", "/"),
    )


def csv_targets(raw: str) -> str:
    values = [part.strip().lower() for part in raw.split(",") if part.strip()]
    allowed = {"hf", "github", "dropbox", "adobe", "gdrive", "proton"}
    filtered = [v for v in values if v in allowed]
    return ",".join(filtered)


def command_cloud(cfg: Dict[str, Any], args: argparse.Namespace) -> List[str]:
    cloud_cfg = cfg.get("cloud", {})
    command = [
        sys.executable,
        "scripts/cloud_kernel_data_pipeline.py",
        "--config",
        str(cloud_cfg.get("config", "training/cloud_kernel_pipeline.json")),
        "--run-root",
        str(cloud_cfg.get("run_root", "training/runs/cloud_kernel_sync")),
    ]

    keep_runs = int(cloud_cfg.get("keep_runs", 30))
    command += ["--keep-runs", str(keep_runs)]

    targets = csv_targets(args.ship_targets) or csv_targets(str(cloud_cfg.get("ship_targets", "hf,github")))
    if targets:
        command += ["--ship-targets", targets]

    if args.sync_notion or bool(cloud_cfg.get("sync_notion", False)):
        command.append("--sync-notion")

    notion_keys = cloud_cfg.get("notion_config_key", [])
    if isinstance(notion_keys, list):
        for key in notion_keys:
            if str(key).strip():
                command += ["--notion-config-key", str(key).strip()]

    if args.no_upload:
        command.append("--no-upload")

    if args.allow_quarantine or bool(cloud_cfg.get("allow_quarantine", False)):
        command.append("--allow-quarantine")

    if args.ship_on_quarantine or bool(cloud_cfg.get("ship_on_quarantine", False)):
        command.append("--ship-on-quarantine")

    extra_globs = cloud_cfg.get("extra_globs", [])
    if isinstance(extra_globs, list):
        for pattern in extra_globs:
            if str(pattern).strip():
                command += ["--glob", str(pattern).strip()]

    return command


def command_local(cfg: Dict[str, Any], args: argparse.Namespace) -> List[str]:
    local_cfg = cfg.get("local", {})
    command = [
        sys.executable,
        "scripts/local_cloud_autosync.py",
        "--config",
        str(local_cfg.get("config", "training/local_cloud_sync.json")),
        "--run-root",
        str(local_cfg.get("run_root", "training/runs/local_cloud_sync")),
        "--state-file",
        str(local_cfg.get("state_file", "training/ingest/local_cloud_sync_state.json")),
        "--latest-pointer",
        str(local_cfg.get("latest_pointer", "training/ingest/latest_local_cloud_sync.txt")),
    ]

    targets = csv_targets(args.ship_targets) or csv_targets(str(local_cfg.get("ship_targets", "")))
    if targets:
        command += ["--ship-targets", targets]

    if args.no_upload:
        command.append("--no-upload")

    if args.once or bool(local_cfg.get("once", True)):
        command.append("--once")

    interval = int(local_cfg.get("interval_seconds", 0))
    if interval > 0:
        command += ["--interval-seconds", str(interval)]

    if args.force_local_snapshot or bool(local_cfg.get("force", False)):
        command.append("--force")

    return command


def summarize_decision(step_results: List[StepResult]) -> Dict[str, Any]:
    total = len(step_results)
    passed = sum(1 for step in step_results if step.success)
    confidence = 0.0 if total == 0 else passed / total
    if passed == total:
        action = "ALLOW"
        reason = "All consolidation legs passed."
    elif passed == 0:
        action = "DENY"
        reason = "All consolidation legs failed."
    else:
        action = "QUARANTINE"
        reason = "Partial success; review failing legs."

    digest_input = "|".join(f"{s.step}:{s.returncode}:{s.duration_ms}" for s in step_results).encode("utf-8")
    signature = hashlib.sha256(digest_input).hexdigest()
    return {
        "action": action,
        "reason": reason,
        "confidence": round(confidence, 4),
        "signature": signature,
        "timestamp_utc": utc_now(),
    }


def main() -> int:
    args = parse_args()
    config_path = REPO_ROOT / args.config
    cfg = load_json(config_path)

    run_root = (REPO_ROOT / args.run_root).resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    steps: List[StepResult] = []

    if not args.skip_cloud and bool(cfg.get("cloud", {}).get("enabled", True)):
        steps.append(run_step("cloud_kernel_pipeline", command_cloud(cfg, args), run_dir, args.dry_run))

    if not args.skip_local and bool(cfg.get("local", {}).get("enabled", True)):
        steps.append(run_step("local_cloud_autosync", command_local(cfg, args), run_dir, args.dry_run))

    decision = summarize_decision(steps)

    state_vector = {
        "chain_id": str(cfg.get("chain_id", "scbe-research-consolidation-v1")),
        "run_id": run_id,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "config_path": str(config_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "steps": [
            {
                "step": s.step,
                "command": " ".join(shlex.quote(x) for x in s.command),
                "returncode": s.returncode,
                "duration_ms": s.duration_ms,
                "started_at": s.started_at,
                "ended_at": s.ended_at,
                "log_path": s.log_path,
            }
            for s in steps
        ],
    }

    manifest = {
        "generated_at": utc_now(),
        "StateVector": state_vector,
        "DecisionRecord": decision,
    }

    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    latest_pointer = REPO_ROOT / args.latest_pointer
    latest_pointer.parent.mkdir(parents=True, exist_ok=True)
    latest_pointer.write_text(str(manifest_path.relative_to(REPO_ROOT)).replace("\\", "/"), encoding="utf-8")

    print(json.dumps({"run_id": run_id, "manifest": str(manifest_path), "decision": decision}, ensure_ascii=True))
    return 0 if decision["action"] == "ALLOW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
