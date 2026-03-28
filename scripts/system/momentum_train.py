from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class StationResult:
    ok: bool
    exit_code: int | None
    started_at: str
    finished_at: str
    duration_s: float
    stdout_path: str
    stderr_path: str
    meta_path: str
    error: str | None = None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def best_shell_command(cmd: str) -> list[str]:
    pwsh = os.environ.get("SCBE_PWSH") or "pwsh"
    return [pwsh, "-NoProfile", "-Command", cmd]


def run_shell_station(
    station_key: str,
    station_id: str,
    station_index: int,
    cmd: str,
    run_dir: Path,
    timeout_s: int | None,
) -> StationResult:
    started = time.time()
    started_at = datetime.now(timezone.utc).isoformat()

    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in station_id)[:80]
    stdout_path = run_dir / f"station_{station_index:03d}_{safe_id}_stdout.txt"
    stderr_path = run_dir / f"station_{station_index:03d}_{safe_id}_stderr.txt"
    meta_path = run_dir / f"station_{station_index:03d}_{safe_id}_meta.json"

    meta: dict[str, Any] = {
        "station_key": station_key,
        "station_id": station_id,
        "station_index": station_index,
        "cmd": cmd,
        "timeout_s": timeout_s,
        "started_at": started_at,
    }

    try:
        proc = subprocess.run(
            best_shell_command(cmd),
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        stdout_path.write_text(proc.stdout or "", encoding="utf-8", errors="replace")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8", errors="replace")
        meta["exit_code"] = proc.returncode
        meta["ok"] = proc.returncode == 0
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(meta_path, meta)
        finished = time.time()
        return StationResult(
            ok=proc.returncode == 0,
            exit_code=proc.returncode,
            started_at=started_at,
            finished_at=meta["finished_at"],
            duration_s=finished - started,
            stdout_path=str(stdout_path.relative_to(ROOT)),
            stderr_path=str(stderr_path.relative_to(ROOT)),
            meta_path=str(meta_path.relative_to(ROOT)),
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(getattr(exc, "stdout", "") or "", encoding="utf-8", errors="replace")
        stderr_path.write_text(getattr(exc, "stderr", "") or "", encoding="utf-8", errors="replace")
        meta["exit_code"] = None
        meta["ok"] = False
        meta["error"] = "timeout"
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(meta_path, meta)
        finished = time.time()
        return StationResult(
            ok=False,
            exit_code=None,
            started_at=started_at,
            finished_at=meta["finished_at"],
            duration_s=finished - started,
            stdout_path=str(stdout_path.relative_to(ROOT)),
            stderr_path=str(stderr_path.relative_to(ROOT)),
            meta_path=str(meta_path.relative_to(ROOT)),
            error="timeout",
        )
    except Exception as exc:  # noqa: BLE001
        meta["exit_code"] = None
        meta["ok"] = False
        meta["error"] = str(exc)
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(meta_path, meta)
        finished = time.time()
        return StationResult(
            ok=False,
            exit_code=None,
            started_at=started_at,
            finished_at=meta["finished_at"],
            duration_s=finished - started,
            stdout_path=str(stdout_path.relative_to(ROOT)),
            stderr_path=str(stderr_path.relative_to(ROOT)),
            meta_path=str(meta_path.relative_to(ROOT)),
            error=str(exc),
        )


def station_uid(flow: str, index: int, station_id: str) -> str:
    return f"{flow}:{index:03d}:{station_id}"


def normalize_flow_steps(flow: str, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, step in enumerate(steps):
        step = dict(step)
        if not step.get("id"):
            step["id"] = f"station_{idx:03d}"
        step["_flow"] = flow
        step["_index"] = idx
        step["_uid"] = station_uid(flow, idx, str(step["id"]))
        normalized.append(step)
    return normalized


def build_run_dirs(train_id: str) -> tuple[Path, Path]:
    run_root = ROOT / "artifacts" / "momentum_trains" / train_id / utc_timestamp()
    ensure_dir(run_root)
    return run_root, run_root / "state.json"


def run_flow(
    flows: dict[str, list[dict[str, Any]]],
    flow_name: str,
    run_dir: Path,
    state: dict[str, Any],
    execute: bool,
    max_parallel: int,
) -> None:
    steps = normalize_flow_steps(flow_name, flows.get(flow_name, []))
    for step in steps:
        uid = step["_uid"]
        if state["stations"].get(uid, {}).get("status") == "completed":
            continue

        step_type = str(step.get("type", "noop"))
        station_id = str(step.get("id", "station"))
        station_index = int(step["_index"])
        continue_on_error = bool(step.get("continue_on_error", False))

        state["stations"][uid] = {
            "status": "running",
            "flow": flow_name,
            "id": station_id,
            "type": step_type,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        write_json(Path(state["state_path"]), state)

        if not execute:
            state["stations"][uid]["status"] = "skipped"
            state["stations"][uid]["reason"] = "dry_run"
            state["stations"][uid]["finished_at"] = datetime.now(timezone.utc).isoformat()
            write_json(Path(state["state_path"]), state)
            continue

        if step_type == "shell":
            cmd = str(step.get("cmd", ""))
            timeout_s = step.get("timeout_s")
            timeout = int(timeout_s) if timeout_s is not None else None
            result = run_shell_station(uid, station_id, station_index, cmd, run_dir, timeout)
            state["stations"][uid]["result"] = result.__dict__
            state["stations"][uid]["finished_at"] = datetime.now(timezone.utc).isoformat()
            state["stations"][uid]["status"] = "completed" if result.ok else "failed"
            write_json(Path(state["state_path"]), state)
            if not result.ok and not continue_on_error:
                raise RuntimeError(f"Station failed: {uid}")
            continue

        if step_type == "include":
            include_flow = str(step.get("flow", ""))
            if not include_flow:
                state["stations"][uid]["status"] = "failed"
                state["stations"][uid]["error"] = "include flow missing"
                write_json(Path(state["state_path"]), state)
                if not continue_on_error:
                    raise RuntimeError(f"Station failed: {uid}")
                continue
            run_flow(flows, include_flow, run_dir, state, execute, max_parallel)
            state["stations"][uid]["status"] = "completed"
            state["stations"][uid]["finished_at"] = datetime.now(timezone.utc).isoformat()
            write_json(Path(state["state_path"]), state)
            continue

        if step_type == "fork":
            fork_flows = list(step.get("flows") or [])
            join = bool(step.get("join", True))
            if not fork_flows:
                state["stations"][uid]["status"] = "failed"
                state["stations"][uid]["error"] = "fork flows missing"
                write_json(Path(state["state_path"]), state)
                if not continue_on_error:
                    raise RuntimeError(f"Station failed: {uid}")
                continue

            if not join:
                state["stations"][uid]["status"] = "completed"
                state["stations"][uid]["note"] = "fork launched without join (not implemented)"
                write_json(Path(state["state_path"]), state)
                continue

            errors: list[str] = []
            with ThreadPoolExecutor(max_workers=max_parallel) as executor:
                futures = {
                    executor.submit(run_flow, flows, fn, run_dir, state, execute, max_parallel): fn for fn in fork_flows
                }
                for future in as_completed(futures):
                    flow_ran = futures[future]
                    try:
                        future.result()
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"{flow_ran}: {exc}")

            if errors:
                state["stations"][uid]["status"] = "failed"
                state["stations"][uid]["errors"] = errors
                state["stations"][uid]["finished_at"] = datetime.now(timezone.utc).isoformat()
                write_json(Path(state["state_path"]), state)
                if not continue_on_error:
                    raise RuntimeError(f"Fork failed: {uid}")
            else:
                state["stations"][uid]["status"] = "completed"
                state["stations"][uid]["finished_at"] = datetime.now(timezone.utc).isoformat()
                write_json(Path(state["state_path"]), state)
            continue

        # noop or unknown type
        state["stations"][uid]["status"] = "skipped"
        state["stations"][uid]["reason"] = "noop"
        state["stations"][uid]["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(Path(state["state_path"]), state)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run long-running momentum trains with checkpointing and forkflows.")
    parser.add_argument("--config", required=True, help="Workflow config JSON (repo-relative or absolute).")
    parser.add_argument("--flow", default=None, help="Flow name to run (default: config entry_flow).")
    parser.add_argument("--execute", action="store_true", help="Execute stations (default: dry-run).")
    parser.add_argument("--max-parallel", type=int, default=None, help="Override max parallel flows.")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    cfg = load_json(config_path)

    train_id = str(cfg.get("train_id") or "train")
    flow = str(args.flow or cfg.get("entry_flow") or "main")
    flows = dict(cfg.get("flows") or {})
    settings = dict(cfg.get("settings") or {})

    max_parallel = int(args.max_parallel or settings.get("max_parallel_flows") or 2)

    run_dir, state_path = build_run_dirs(train_id)
    run_meta = {
        "train_id": train_id,
        "flow": flow,
        "execute": bool(args.execute),
        "config_path": str(config_path.relative_to(ROOT)),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "max_parallel_flows": max_parallel,
        "run_dir": str(run_dir.relative_to(ROOT)),
    }
    write_json(run_dir / "run.json", run_meta)
    write_json(run_dir / "config.json", cfg)

    state: dict[str, Any] = {
        "train_id": train_id,
        "flow": flow,
        "execute": bool(args.execute),
        "run_dir": str(run_dir.relative_to(ROOT)),
        "state_path": str((run_dir / "state.json").relative_to(ROOT)),
        "stations": {},
    }
    write_json(state_path, state)

    try:
        run_flow(flows, flow, run_dir, state, bool(args.execute), max_parallel)
    except Exception as exc:  # noqa: BLE001
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        state["ok"] = False
        state["error"] = str(exc)
        write_json(state_path, state)
        print(json.dumps({"ok": False, "run_dir": state["run_dir"], "error": str(exc)}))
        return 2

    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    state["ok"] = True
    write_json(state_path, state)
    print(json.dumps({"ok": True, "run_dir": state["run_dir"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
