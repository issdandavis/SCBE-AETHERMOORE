#!/usr/bin/env python3
"""Phone Eye - stable latest-frame wrapper around the Android hand observation lane."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.system.phone_navigation_telemetry import build_navigation_telemetry
from src.browser.hydra_android_hand import HydraAndroidHand


OUT_DIR = REPO_ROOT / "artifacts" / "kindle" / "emulator"
LATEST = OUT_DIR / "eye_latest.png"
LATEST_XML = OUT_DIR / "eye_latest.xml"
LATEST_NAV = OUT_DIR / "eye_latest.nav.json"
LATEST_META = OUT_DIR / "eye_latest.json"
HISTORY_DIR = OUT_DIR / "eye_history"


def build_capture_metadata(
    *,
    serial: str,
    latest_path: Path,
    latest_xml_path: Path,
    latest_nav_path: Path,
    session_dir: str,
    status: Dict[str, Any],
    history_path: str = "",
) -> Dict[str, Any]:
    return {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "serial": serial,
        "latest_path": str(latest_path),
        "latest_xml_path": str(latest_xml_path),
        "latest_nav_path": str(latest_nav_path),
        "history_path": history_path,
        "session_dir": session_dir,
        "status": status,
    }


def capture(*, preferred_serial: str = "", save_history: bool = False) -> Dict[str, Any]:
    """Capture screenshot, UI dump, and navigation telemetry into stable latest files."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hand = HydraAndroidHand(serial=preferred_serial)
    observed = hand.observe(name="eye_latest", include_ui_dump=True)

    screenshot_path = Path(observed["screenshot"]["artifact_path"])
    ui_dump_path = Path(observed["ui_dump"]["artifact_path"])
    status = observed.get("status", {})
    serial = str(status.get("serial") or preferred_serial or "")

    if not screenshot_path.exists():
        raise RuntimeError(f"screenshot missing: {screenshot_path}")
    if not ui_dump_path.exists():
        raise RuntimeError(f"ui dump missing: {ui_dump_path}")

    shutil.copyfile(screenshot_path, LATEST)
    shutil.copyfile(ui_dump_path, LATEST_XML)

    nav_payload = build_navigation_telemetry(
        ui_dump_path,
        screenshot_path=str(LATEST),
        status=status,
        source="phone_eye",
    )
    LATEST_NAV.write_text(json.dumps(nav_payload, indent=2), encoding="utf-8")
    history_path = ""
    if save_history:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        history_png = HISTORY_DIR / f"frame_{timestamp}.png"
        history_xml = HISTORY_DIR / f"frame_{timestamp}.xml"
        history_nav = HISTORY_DIR / f"frame_{timestamp}.nav.json"
        shutil.copyfile(LATEST, history_png)
        shutil.copyfile(LATEST_XML, history_xml)
        shutil.copyfile(LATEST_NAV, history_nav)
        history_path = str(history_png)

    metadata = build_capture_metadata(
        serial=serial,
        latest_path=LATEST,
        latest_xml_path=LATEST_XML,
        latest_nav_path=LATEST_NAV,
        session_dir=str(status.get("session_dir") or hand.session_dir),
        status=status,
        history_path=history_path,
    )
    LATEST_META.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def run_loop(interval: float = 2.0, *, preferred_serial: str = "", save_history: bool = False) -> None:
    print(f"Phone Eye running - {interval}s interval - {LATEST}")
    print("Ctrl+C to stop")
    frames = 0
    while True:
        try:
            metadata = capture(preferred_serial=preferred_serial, save_history=save_history)
            frames += 1
            print(f"\rFrame {frames} captured from {metadata['serial']}", end="", flush=True)
        except Exception as exc:  # pragma: no cover - live loop guard
            print(f"\rCapture error: {exc}", end="", flush=True)
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phone Eye - continuous emulator/device screenshots")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between captures")
    parser.add_argument("--once", action="store_true", help="Single capture then exit")
    parser.add_argument("--history", action="store_true", help="Save timestamped history frames")
    parser.add_argument("--serial", default="", help="Preferred adb serial")
    args = parser.parse_args()

    if args.once:
        try:
            metadata = capture(preferred_serial=args.serial, save_history=args.history)
        except Exception as exc:
            print(f"Capture failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(metadata, indent=2))
        return 0

    try:
        run_loop(args.interval, preferred_serial=args.serial, save_history=args.history)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
