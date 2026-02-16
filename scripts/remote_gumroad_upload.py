#!/usr/bin/env python3
"""Remote-only Gumroad image upload orchestrator with training telemetry.

The script launches or attaches to a Chrome DevTools remote debugging session and
invokes the existing Selenium uploader in ``--debugger-address`` mode.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_TARGETS = [
    "WorldForge",
    "HYDRA Protocol",
    "Notion Templates",
    "WorldForge duplicate",
]

DEFAULT_UPLOADER = Path.home() / ".codex" / "skills" / "gumroad-upload-management" / "scripts" / "gumroad_image_uploader.py"
RUNNER_DEFAULTS = {
    "debugger_port": 9222,
    "products_url": "https://app.gumroad.com/products",
}

MATCH_RE = re.compile(r"MATCH product='([^']+)' -> image='([^']+)'", re.IGNORECASE)
SKIP_RE = re.compile(r"SKIP product='([^']+)' \(no filename match in images dir\)", re.IGNORECASE)
UPLOADED_RE = re.compile(r"Uploaded and clicked save for '([^']+)'")
LOGGED_RE = re.compile(r"Uploaded for '([^']+)' \(save button not auto-detected; verify in UI\)")
ERROR_RE = re.compile(r"\b(ERROR|Failure|Timeout)\b", re.IGNORECASE)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")


def _resolve_script(path: str) -> Path:
    script = Path(path).expanduser().resolve()
    if not script.exists():
        raise FileNotFoundError(f"Uploader script not found: {script}")
    return script


def _resolve_images_dir(images_dir: str | None) -> Path:
    if images_dir:
        return Path(images_dir).expanduser().resolve()
    candidates = [
        Path.home() / "Downloads",
        Path.home() / "OneDrive" / "Downloads",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return (Path.home() / "Downloads").resolve()


def _resolve_chrome_binary(chrome_path: str | None) -> str:
    if chrome_path:
        candidate = Path(chrome_path).expanduser()
        if candidate.exists():
            return str(candidate)
    windows_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in windows_candidates:
        if candidate.exists():
            return str(candidate)
    return "chrome"


def _wait_for_debugger_ready(address: str, timeout_seconds: int = 20, interval_seconds: float = 0.5) -> None:
    endpoint = f"http://{address}/json/version"
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(endpoint, timeout=2) as resp:
                if resp.status == 200:
                    return
        except (ConnectionRefusedError, OSError, urllib.error.URLError) as exc:
            last_error = exc
            time.sleep(interval_seconds)
    if last_error is not None:
        raise TimeoutError(f"Debugger endpoint not ready at {endpoint}") from last_error
    raise TimeoutError(f"Debugger endpoint not ready at {endpoint}")


def _start_remote_chrome(chrome_path: str | None, port: int, products_url: str, user_data_dir: str | None) -> subprocess.Popen:
    chrome_binary = _resolve_chrome_binary(chrome_path)
    args = [
        chrome_binary,
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-popup-blocking",
    ]
    if user_data_dir:
        args.append(f"--user-data-dir={user_data_dir}")
    args.append(products_url)
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _build_uploader_command(
    script: Path,
    images_dir: Path,
    targets: list[str],
    debugger_address: str,
    timeout: int,
    dry_run: bool,
    log_path: Path,
    headless: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        str(script),
        "--debugger-address",
        debugger_address,
        "--images-dir",
        str(images_dir),
        "--timeout",
        str(timeout),
        "--log",
        str(log_path),
    ]
    if targets:
        cmd.append("--targets")
        cmd.extend(targets)
    if dry_run:
        cmd.append("--dry-run")
    if headless:
        cmd.append("--headless")
    return cmd


def _parse_gumroad_log(path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    events: list[dict[str, Any]] = []
    metrics = {
        "matched": 0,
        "skipped": 0,
        "uploaded": 0,
        "logged": 0,
        "errors": 0,
    }
    if not path.exists():
        return events, metrics

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        match = MATCH_RE.search(line)
        if match:
            metrics["matched"] += 1
            events.append({"event": "match", "product": match.group(1), "image": match.group(2)})
            continue

        match = SKIP_RE.search(line)
        if match:
            metrics["skipped"] += 1
            events.append({"event": "skip", "product": match.group(1), "reason": "no_filename_match"})
            continue

        match = UPLOADED_RE.search(line)
        if match:
            metrics["uploaded"] += 1
            events.append({"event": "uploaded", "product": match.group(1), "status": "saved"})
            continue

        match = LOGGED_RE.search(line)
        if match:
            metrics["logged"] += 1
            events.append({"event": "uploaded", "product": match.group(1), "status": "save_not_auto_detected"})
            continue

        if ERROR_RE.search(line):
            metrics["errors"] += 1
            events.append({"event": "error", "message": line})

    return events, metrics


def _append_training_records(path: Path, run_id: str, image_dir: Path, targets: list[str], run_index: int, events: list[dict[str, Any]], extra: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as f:
        for event in events:
            rec = {
                "dataset": "gumroad_automation",
                "run_id": run_id,
                "run_index": run_index,
                "created_at_utc": created_at,
                "images_dir": str(image_dir),
                "targets": targets,
                "event_type": f"gumroad_{event['event']}",
                "product": event.get("product"),
                "image": event.get("image"),
                "status": event.get("status"),
                "reason": event.get("reason"),
                "message": event.get("message"),
            }
            rec.update(extra)
            f.write(json.dumps(rec) + "\n")


@dataclass
class RunContext:
    run_id: str
    run_index: int
    run_dir: Path
    log_path: Path


def _run_once(
    run_id: str,
    run_index: int,
    images_dir: Path,
    targets: list[str],
    dry_run: bool,
    timeout: int,
    debug_port: int,
    headless: bool,
    uploader_script: Path,
    train_log: Path,
) -> tuple[int, dict[str, Any]]:
    run_dir = Path("training") / "runs" / "gumroad-upload" / run_id / f"pass-{run_index:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "gumroad_upload.log"
    ctx = RunContext(run_id=run_id, run_index=run_index, run_dir=run_dir, log_path=log_path)

    cmd = _build_uploader_command(
        script=uploader_script,
        images_dir=images_dir,
        targets=targets,
        debugger_address=f"127.0.0.1:{debug_port}",
        timeout=timeout,
        dry_run=dry_run,
        log_path=log_path,
        headless=headless,
    )

    print(f"[run={run_id}:{run_index}] executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    events, metrics = _parse_gumroad_log(log_path)
    manifest = {
        "run_id": run_id,
        "run_index": run_index,
        "dry_run": dry_run,
        "uploader_script": str(uploader_script),
        "images_dir": str(images_dir),
        "targets": targets,
        "debugger": f"127.0.0.1:{debug_port}",
        "log_path": str(log_path),
        "return_code": result.returncode,
        "events": metrics,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with (ctx.run_dir / "run_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    extra = {
        "run_manifest": str(ctx.run_dir / "run_manifest.json"),
        "return_code": result.returncode,
        "run_path": str(ctx.run_dir),
    }
    _append_training_records(train_log, run_id, images_dir, targets, run_index, events, extra)
    print(json.dumps(manifest, indent=2))
    return result.returncode, {"events": metrics, "run_index": run_index}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remote Gumroad upload automation runner")
    parser.add_argument("--images-dir", default=None, help="Folder containing product images")
    parser.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS, help="Product names to target")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches without uploading")
    parser.add_argument("--timeout", type=int, default=30, help="Per-page timeout for Selenium actions")
    parser.add_argument("--debugger-port", type=int, default=RUNNER_DEFAULTS["debugger_port"], help="Remote Chrome debug port")
    parser.add_argument("--debugger-address", default=None, help="Attach to existing Chrome remote debugger host:port")
    parser.add_argument("--chrome-path", default=None, help="Optional Chrome executable path")
    parser.add_argument("--chrome-profile-dir", default=None, help="Optional Chrome --user-data-dir for persistent login")
    parser.add_argument("--products-url", default=RUNNER_DEFAULTS["products_url"], help="Gumroad products page URL")
    parser.add_argument("--training-log", default=str(Path("training") / "aethermoore_ops_training.jsonl"), help="Output JSONL training log")
    parser.add_argument("--uploader-script", default=str(DEFAULT_UPLOADER), help="Path to gumroad_image_uploader.py")
    parser.add_argument("--headless", action="store_true", help="Run browser with headless mode")
    parser.add_argument("--passes", type=int, default=1, help="How many full passes to run")
    parser.add_argument("--timeout-step", type=int, default=0, help="Increase timeout per pass (for deeper retries)")
    parser.add_argument("--pause-between-passes", type=float, default=3.0, help="Seconds to wait between passes")
    parser.add_argument("--start-chrome", action=argparse.BooleanOptionalAction, default=True, help="Start Chrome with remote debugging")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.passes <= 0:
        raise ValueError("--passes must be >= 1")

    images_dir = _resolve_images_dir(args.images_dir)
    uploader_script = _resolve_script(args.uploader_script)
    train_log = Path(args.training_log).expanduser().resolve()

    debugger_address = args.debugger_address
    if not debugger_address:
        debugger_address = f"127.0.0.1:{args.debugger_port}"

    if not args.start_chrome and not args.debugger_address:
        raise RuntimeError("Provide --debugger-address when --start-chrome is disabled")

    # Keep automation output deterministic.
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

    chrome_proc: subprocess.Popen | None = None
    all_metrics: list[dict[str, Any]] = []
    run_id = _utc_now()
    return_code = 0

    try:
        if args.start_chrome:
            chrome_proc = _start_remote_chrome(
                chrome_path=args.chrome_path,
                port=args.debugger_port,
                products_url=args.products_url,
                user_data_dir=args.chrome_profile_dir,
            )
            _wait_for_debugger_ready(debugger_address, timeout_seconds=30)

        for pass_index in range(args.passes):
            pass_timeout = args.timeout + (args.timeout_step * pass_index)
            return_code, metrics = _run_once(
                run_id=run_id,
                run_index=pass_index,
                images_dir=images_dir,
                targets=args.targets,
                dry_run=args.dry_run,
                timeout=pass_timeout,
                debug_port=args.debugger_port,
                headless=args.headless,
                uploader_script=uploader_script,
                train_log=train_log,
            )
            all_metrics.append(metrics)
            if pass_index < args.passes - 1:
                time.sleep(args.pause_between_passes)
            if return_code != 0:
                break

        manifest_path = Path("training") / "runs" / "gumroad-upload" / run_id / "run_summary.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "run_id": run_id,
                    "passes": len(all_metrics),
                    "requested_passes": args.passes,
                    "dry_run": args.dry_run,
                    "return_code": return_code,
                    "pass_metrics": all_metrics,
                },
                f,
                indent=2,
            )
        print(f"run summary: {manifest_path}")

        return int(return_code)
    finally:
        if chrome_proc is not None:
            try:
                chrome_proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
