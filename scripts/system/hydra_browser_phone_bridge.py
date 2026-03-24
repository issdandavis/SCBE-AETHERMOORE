#!/usr/bin/env python3
"""Bridge AetherBrowse host control with HYDRA Android phone preview loops."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.browser_chain_dispatcher import BrowserChainDispatcher, build_default_fleet
from src.browser.hydra_android_hand import DEFAULT_READER_ROUTE, HydraAndroidHand


def _utc_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        return DEFAULT_READER_ROUTE
    if "://" not in cleaned:
        return f"https://{cleaned}"
    return cleaned


def domain_from_url(url: str) -> str:
    parsed = urlparse(normalize_url(url))
    return parsed.netloc.lower()


def assign_host_lane(url: str, task: str = "navigate", engine: str = "playwriter") -> Dict[str, Any]:
    dispatcher = BrowserChainDispatcher()
    for tentacle in build_default_fleet():
        dispatcher.register_tentacle(tentacle)
    return dispatcher.assign_task(
        domain=domain_from_url(url),
        task_type=task,
        payload={"url": normalize_url(url), "engine": engine},
    )


def build_host_action_script(url: str) -> List[Dict[str, str]]:
    target = normalize_url(url)
    return [
        {"action": "navigate", "target": target},
        {"action": "snapshot", "target": target},
        {"action": "extract", "target": target},
    ]


def run_host_actions(
    script_path: Path,
    *,
    backend: str = "cdp",
    audit_only: bool = False,
    headless: bool = False,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "agents" / "aetherbrowse_cli.py"),
        "--backend",
        backend,
    ]
    if headless:
        cmd.append("--headless")
    else:
        cmd.append("--no-headless")
    if audit_only:
        cmd.append("--audit-only")
    cmd.extend(["run-script", str(script_path)])

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    payload: Dict[str, Any] = {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    if completed.stdout.strip():
        try:
            payload["json"] = json.loads(completed.stdout)
        except json.JSONDecodeError:
            pass
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge AetherBrowse host control and HYDRA Android phone preview.")
    parser.add_argument("--url", default=DEFAULT_READER_ROUTE, help="Target URL for host browser and/or phone browser.")
    parser.add_argument("--host-engine", default="playwriter", help="Dispatcher engine label for host lane assignment.")
    parser.add_argument("--host-backend", default="cdp", help="Actual backend for AetherBrowse CLI execution.")
    parser.add_argument(
        "--phone-target",
        choices=["app", "browser"],
        default="app",
        help="Preview inside the app shell or phone browser.",
    )
    parser.add_argument("--serial", default="", help="ADB serial for the phone/emulator target.")
    parser.add_argument("--steps", type=int, default=3, help="Number of phone preview captures.")
    parser.add_argument("--settle-ms", type=int, default=500, help="Delay after each phone swipe.")
    parser.add_argument("--execute-host", action="store_true", help="Run the host-side AetherBrowse action script.")
    parser.add_argument("--audit-only", action="store_true", help="Validate host actions without executing them.")
    parser.add_argument(
        "--headless", action="store_true", help="Run host browser backend headless when executing host actions."
    )
    parser.add_argument(
        "--skip-phone-launch", action="store_true", help="Do not relaunch the phone app/browser before capturing."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_url = normalize_url(args.url)

    bridge_dir = REPO_ROOT / "artifacts" / "kindle" / "control_bridge" / f"bridge-{_utc_slug()}"
    bridge_dir.mkdir(parents=True, exist_ok=True)

    host_assignment = assign_host_lane(target_url, engine=args.host_engine)
    host_script = build_host_action_script(target_url)
    host_script_path = bridge_dir / "aetherbrowse_actions.json"
    host_script_path.write_text(json.dumps(host_script, indent=2), encoding="utf-8")

    payload: Dict[str, Any] = {
        "ok": True,
        "target_url": target_url,
        "bridge_dir": str(bridge_dir),
        "host_assignment": host_assignment,
        "host_script_path": str(host_script_path),
        "phone_target": args.phone_target,
    }

    if args.execute_host:
        payload["host_run"] = run_host_actions(
            host_script_path,
            backend=args.host_backend,
            audit_only=args.audit_only,
            headless=args.headless,
        )

    android_hand = HydraAndroidHand(head_id="android-bridge", serial=args.serial)
    payload["phone_run"] = android_hand.preview_loop(
        steps=args.steps,
        settle_ms=args.settle_ms,
        include_ui_dump=False,
        route_url=target_url,
        use_browser=args.phone_target == "browser",
        launch_reader=not args.skip_phone_launch,
    )

    summary_path = bridge_dir / "bridge_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["summary_path"] = str(summary_path)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
