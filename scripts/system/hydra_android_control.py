#!/usr/bin/env python3
"""CLI wrapper for the HYDRA Android hand control loop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.browser.hydra_android_hand import DEFAULT_PACKAGE, DEFAULT_READER_ROUTE, HydraAndroidHand


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HYDRA Android hand control loop for emulator and device operation.")
    parser.add_argument("--head-id", default="android-alpha", help="Logical HYDRA head id")
    parser.add_argument("--serial", default="", help="ADB serial to target")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="Android package name")
    parser.add_argument("--adb-path", default="", help="Explicit adb executable path")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Report connected Android device state")

    p_launch = sub.add_parser("launch-reader", help="Launch the app or browser reader route")
    p_launch.add_argument("--route", default=DEFAULT_READER_ROUTE, help="Reader URL when using browser route launch")
    p_launch.add_argument(
        "--browser", action="store_true", help="Open the route in Android browser instead of app shell"
    )

    p_observe = sub.add_parser("observe", help="Capture screenshot and optional UI dump")
    p_observe.add_argument("--name", default="observation", help="Artifact basename")
    p_observe.add_argument("--no-ui-dump", action="store_true", help="Skip uiautomator XML dump")

    p_tap = sub.add_parser("tap", help="Send a tap event")
    p_tap.add_argument("--x", type=int, required=True)
    p_tap.add_argument("--y", type=int, required=True)

    p_swipe = sub.add_parser("swipe", help="Send a swipe event")
    p_swipe.add_argument("--x1", type=int, required=True)
    p_swipe.add_argument("--y1", type=int, required=True)
    p_swipe.add_argument("--x2", type=int, required=True)
    p_swipe.add_argument("--y2", type=int, required=True)
    p_swipe.add_argument("--duration-ms", type=int, default=250)

    p_key = sub.add_parser("keyevent", help="Send an Android key event")
    p_key.add_argument("--keycode", required=True)

    p_text = sub.add_parser("text", help="Type text via adb input")
    p_text.add_argument("--value", required=True)

    p_preview = sub.add_parser("preview-loop", help="Run webtoon preview capture loop")
    p_preview.add_argument("--steps", type=int, default=4)
    p_preview.add_argument("--settle-ms", type=int, default=700)
    p_preview.add_argument("--include-ui-dump", action="store_true")
    p_preview.add_argument("--route", default=DEFAULT_READER_ROUTE)
    p_preview.add_argument("--browser", action="store_true")
    p_preview.add_argument("--skip-launch", action="store_true")

    p_seq = sub.add_parser("sequence", help="Run a JSON task list against the Android hand")
    p_seq.add_argument("--input", required=True, help="Path to JSON file containing a list of tasks")

    return parser


def _make_hand(args: argparse.Namespace) -> HydraAndroidHand:
    return HydraAndroidHand(
        head_id=args.head_id,
        serial=args.serial,
        package_name=args.package,
        adb_path=args.adb_path,
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    hand = _make_hand(args)

    if args.command == "status":
        payload = hand.status()
    elif args.command == "launch-reader":
        payload = hand.launch_reader(route_url=args.route, use_browser=args.browser).to_dict()
    elif args.command == "observe":
        payload = hand.observe(name=args.name, include_ui_dump=not args.no_ui_dump)
    elif args.command == "tap":
        payload = hand.tap(args.x, args.y).to_dict()
    elif args.command == "swipe":
        payload = hand.swipe(args.x1, args.y1, args.x2, args.y2, duration_ms=args.duration_ms).to_dict()
    elif args.command == "keyevent":
        payload = hand.keyevent(args.keycode).to_dict()
    elif args.command == "text":
        payload = hand.input_text(args.value).to_dict()
    elif args.command == "preview-loop":
        payload = hand.preview_loop(
            steps=args.steps,
            settle_ms=args.settle_ms,
            include_ui_dump=args.include_ui_dump,
            route_url=args.route,
            use_browser=args.browser,
            launch_reader=not args.skip_launch,
        )
    elif args.command == "sequence":
        task_path = Path(args.input)
        payload = hand.multi_action(json.loads(task_path.read_text(encoding="utf-8")))
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
