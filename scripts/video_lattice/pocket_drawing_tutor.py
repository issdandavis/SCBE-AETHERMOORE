#!/usr/bin/env python3
"""Keyboard-only pocket drawing tutor.

This is the Fizzle globe as a small command-line lesson:

1. create a bounded target pose,
2. create a deliberately rough attempt,
3. render both as simple SVG/PNG sketches,
4. score the attempt with the existing pose checker,
5. write one repair instruction for the next try.

No GUI is required. The SVG is the trace surface.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.video_lattice import (  # noqa: E402
    BodyLandmark,
    HandLandmark,
    Landmark,
    PoseChecker,
    render_body_sketch,
    render_hand_sketch,
)

DEFAULT_OUT = REPO_ROOT / "artifacts" / "video_lattice" / "pocket_drawing_tutor"


def synthetic_hand(curl: float = 0.0, thumb_tuck: float = 0.0, x_shift: float = 0.0) -> list[Landmark]:
    landmarks = [Landmark(0.0, 0.0) for _ in range(21)]
    landmarks[HandLandmark.WRIST] = Landmark(0.50 + x_shift, 0.82)
    bases = {
        HandLandmark.THUMB_CMC: (0.35, 0.70),
        HandLandmark.INDEX_MCP: (0.42, 0.55),
        HandLandmark.MIDDLE_MCP: (0.50, 0.52),
        HandLandmark.RING_MCP: (0.58, 0.55),
        HandLandmark.PINKY_MCP: (0.66, 0.60),
    }
    chains = [
        (HandLandmark.THUMB_CMC, HandLandmark.THUMB_MCP, HandLandmark.THUMB_IP, HandLandmark.THUMB_TIP),
        (HandLandmark.INDEX_MCP, HandLandmark.INDEX_PIP, HandLandmark.INDEX_DIP, HandLandmark.INDEX_TIP),
        (HandLandmark.MIDDLE_MCP, HandLandmark.MIDDLE_PIP, HandLandmark.MIDDLE_DIP, HandLandmark.MIDDLE_TIP),
        (HandLandmark.RING_MCP, HandLandmark.RING_PIP, HandLandmark.RING_DIP, HandLandmark.RING_TIP),
        (HandLandmark.PINKY_MCP, HandLandmark.PINKY_PIP, HandLandmark.PINKY_DIP, HandLandmark.PINKY_TIP),
    ]
    for chain in chains:
        base = chain[0]
        x, y = bases[base]
        x += x_shift
        landmarks[base] = Landmark(x, y)
        is_thumb = base == HandLandmark.THUMB_CMC
        for step, joint in enumerate(chain[1:], start=1):
            straight_x = x + (-0.09 * step if is_thumb else 0.0)
            straight_y = y - (0.10 * step if is_thumb else 0.13 * step)
            folded_x = x + (0.04 * step) * np.sign(x - 0.5 if x != 0.5 else 1.0)
            folded_y = y - (0.04, 0.02, -0.01)[step - 1]
            local_curl = max(curl, thumb_tuck) if is_thumb else curl
            landmarks[joint] = Landmark(
                float((1.0 - local_curl) * straight_x + local_curl * folded_x),
                float((1.0 - local_curl) * straight_y + local_curl * folded_y),
            )
    return landmarks


def synthetic_body(arm_raise: float = 0.0, lean: float = 0.0) -> list[Landmark]:
    landmarks = [Landmark(0.5, 0.5) for _ in range(33)]
    coords = {
        BodyLandmark.NOSE: (0.50 + lean * 0.05, 0.12),
        BodyLandmark.LEFT_SHOULDER: (0.38 + lean * 0.06, 0.28),
        BodyLandmark.RIGHT_SHOULDER: (0.62 + lean * 0.06, 0.28),
        BodyLandmark.LEFT_ELBOW: (0.28 + lean * 0.08, 0.42 - arm_raise * 0.20),
        BodyLandmark.RIGHT_ELBOW: (0.72 + lean * 0.08, 0.42 - arm_raise * 0.20),
        BodyLandmark.LEFT_WRIST: (0.24 + lean * 0.10, 0.58 - arm_raise * 0.38),
        BodyLandmark.RIGHT_WRIST: (0.76 + lean * 0.10, 0.58 - arm_raise * 0.38),
        BodyLandmark.LEFT_HIP: (0.42 + lean * 0.04, 0.60),
        BodyLandmark.RIGHT_HIP: (0.58 + lean * 0.04, 0.60),
        BodyLandmark.LEFT_KNEE: (0.40 + lean * 0.02, 0.78),
        BodyLandmark.RIGHT_KNEE: (0.60 + lean * 0.02, 0.78),
        BodyLandmark.LEFT_ANKLE: (0.38, 0.94),
        BodyLandmark.RIGHT_ANKLE: (0.62, 0.94),
    }
    for index, (x, y) in coords.items():
        landmarks[index] = Landmark(x, y)
    return landmarks


def hand_target(name: str) -> list[Landmark]:
    if name == "open":
        return synthetic_hand(curl=0.0)
    if name == "fist":
        return synthetic_hand(curl=0.78, thumb_tuck=0.65)
    if name == "point":
        hand = synthetic_hand(curl=0.75, thumb_tuck=0.45)
        open_index = synthetic_hand(curl=0.0)
        for index in (HandLandmark.INDEX_MCP, HandLandmark.INDEX_PIP, HandLandmark.INDEX_DIP, HandLandmark.INDEX_TIP):
            hand[index] = open_index[index]
        return hand
    raise ValueError(f"unknown hand target: {name}")


def body_target(name: str) -> list[Landmark]:
    if name == "stand":
        return synthetic_body(arm_raise=0.0)
    if name == "reach":
        return synthetic_body(arm_raise=0.9)
    if name == "lean":
        return synthetic_body(arm_raise=0.2, lean=0.8)
    raise ValueError(f"unknown body target: {name}")


def rough_attempt(pose_type: str, target_name: str) -> list[Landmark]:
    if pose_type == "hand":
        if target_name == "open":
            return synthetic_hand(curl=0.35, thumb_tuck=0.20, x_shift=0.02)
        if target_name == "fist":
            return synthetic_hand(curl=0.45, thumb_tuck=0.20, x_shift=-0.02)
        if target_name == "point":
            return synthetic_hand(curl=0.45, thumb_tuck=0.10)
    if pose_type == "body":
        if target_name == "stand":
            return synthetic_body(arm_raise=0.20, lean=0.20)
        if target_name == "reach":
            return synthetic_body(arm_raise=0.45, lean=-0.10)
        if target_name == "lean":
            return synthetic_body(arm_raise=0.0, lean=0.30)
    raise ValueError(f"unknown lesson: {pose_type} {target_name}")


def repair_sentence(score: dict) -> str:
    verdict = score["verdict"]
    worst = score.get("worst_chain") or "overall shape"
    if verdict == "pass":
        return f"Good trace. Keep the {worst} stable and repeat once for confidence."
    if score["pose_type"] == "hand":
        return f"Repair one thing: redraw the {worst} chain closer to the target before changing the rest of the hand."
    return f"Repair one thing: adjust the {worst} angle toward the target before changing the whole body."


def run_lesson(pose_type: str, target_name: str, out_dir: Path) -> dict:
    target = hand_target(target_name) if pose_type == "hand" else body_target(target_name)
    attempt = rough_attempt(pose_type, target_name)
    checker = PoseChecker(soft_threshold=0.18, hard_threshold=0.8)
    result = checker.check_hand(target, attempt) if pose_type == "hand" else checker.check_body(target, attempt)

    lesson_dir = out_dir / f"{pose_type}_{target_name}"
    lesson_dir.mkdir(parents=True, exist_ok=True)

    target_pad = render_hand_sketch(target) if pose_type == "hand" else render_body_sketch(target)
    attempt_pad = render_hand_sketch(attempt) if pose_type == "hand" else render_body_sketch(attempt)
    target_svg = target_pad.save_svg(lesson_dir / "target.svg")
    attempt_svg = attempt_pad.save_svg(lesson_dir / "attempt.svg")
    try:
        target_png = target_pad.save_png(lesson_dir / "target.png")
        attempt_png = attempt_pad.save_png(lesson_dir / "attempt.png")
    except RuntimeError:
        target_png = None
        attempt_png = None

    score = result.to_dict()
    payload = {
        "lesson": f"{pose_type} {target_name}",
        "target_svg": str(target_svg),
        "attempt_svg": str(attempt_svg),
        "target_png": str(target_png) if target_png else None,
        "attempt_png": str(attempt_png) if attempt_png else None,
        "score": score,
        "repair": repair_sentence(score),
    }
    (lesson_dir / "score.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (lesson_dir / "repair.md").write_text(
        f"# Pocket Drawing Tutor: {pose_type} {target_name}\n\n"
        f"- Verdict: `{score['verdict']}`\n"
        f"- Drift: `{score['overall_drift']}`\n"
        f"- Worst chain: `{score.get('worst_chain')}`\n"
        f"- Repair: {payload['repair']}\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Fizzle-style command-line drawing lesson.")
    parser.add_argument("pose_type", choices=("hand", "body"))
    parser.add_argument("target", help="hand: open/fist/point; body: stand/reach/lean")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    payload = run_lesson(args.pose_type, args.target, args.out_dir)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
