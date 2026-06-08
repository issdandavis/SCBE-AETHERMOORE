#!/usr/bin/env python3
"""Deterministic pocket drawing tutor for video-lattice pose repair.

The tutor gives the agent a small visual/math loop:
  target pose -> imperfect attempt -> lattice score -> repair hint.
It is intentionally model-free so it can run in CI and feed the pocket video
generator without requiring a camera, detector, or cloud renderer.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.video_lattice import Landmark, PoseChecker, render_body_sketch, render_hand_sketch  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "artifacts" / "video_lattice" / "pocket_drawing_tutor"


def synthetic_hand(*, curl: float = 0.0, thumb_tuck: float = 0.0) -> list[Landmark]:
    """Create a 21-point hand pose.

    curl=0 is open; larger curl folds fingertips toward the palm. thumb_tuck
    folds the thumb inward independently.
    """
    curl = _clamp(curl)
    thumb_tuck = _clamp(thumb_tuck)
    points = [Landmark(0.5, 0.82, 0.0) for _ in range(21)]
    wrist = points[0]
    fingers = {
        "thumb": (1, 0.37, 0.68, -0.22, thumb_tuck),
        "index": (5, 0.43, 0.61, -0.30, curl),
        "middle": (9, 0.50, 0.58, -0.34, curl),
        "ring": (13, 0.57, 0.61, -0.30, curl),
        "pinky": (17, 0.64, 0.66, -0.24, curl),
    }
    points[0] = wrist
    for name, (start, base_x, base_y, open_rise, local_curl) in fingers.items():
        side = -1.0 if name in {"thumb", "index"} else 1.0
        for offset in range(4):
            t = (offset + 1) / 4.0
            folded = local_curl * t * t
            x = base_x + side * 0.035 * folded
            y = base_y + open_rise * t + 0.20 * folded
            z = 0.015 * folded
            points[start + offset] = Landmark(x, y, z)
    return points


def hand_target(target: str) -> list[Landmark]:
    target = target.lower()
    if target == "open":
        return synthetic_hand(curl=0.0, thumb_tuck=0.0)
    if target == "fist":
        return synthetic_hand(curl=1.0, thumb_tuck=0.85)
    if target == "point":
        pose = synthetic_hand(curl=0.85, thumb_tuck=0.6)
        for index, y in zip((6, 7, 8), (0.45, 0.32, 0.18)):
            pose[index] = Landmark(0.43, y, 0.0)
        return pose
    raise ValueError(f"unknown hand target: {target}")


def synthetic_body(*, arm_raise: float = 0.0, lean: float = 0.0) -> list[Landmark]:
    """Create a compact 33-point body pose."""
    arm_raise = _clamp(arm_raise)
    lean = max(-1.0, min(1.0, lean))
    points = [Landmark(0.5, 0.5, 0.0) for _ in range(33)]

    def setp(index: int, x: float, y: float, z: float = 0.0) -> None:
        points[index] = Landmark(x + 0.035 * lean, y, z)

    setp(0, 0.50, 0.18)
    for index, x, y in (
        (1, 0.47, 0.16),
        (2, 0.46, 0.16),
        (3, 0.45, 0.16),
        (4, 0.53, 0.16),
        (5, 0.54, 0.16),
        (6, 0.55, 0.16),
        (7, 0.43, 0.18),
        (8, 0.57, 0.18),
        (9, 0.47, 0.22),
        (10, 0.53, 0.22),
    ):
        setp(index, x, y)

    shoulder_y = 0.30
    hip_y = 0.56
    setp(11, 0.38, shoulder_y)
    setp(12, 0.62, shoulder_y)
    setp(13, 0.31, 0.44 - 0.18 * arm_raise)
    setp(14, 0.69, 0.44 - 0.18 * arm_raise)
    setp(15, 0.27, 0.58 - 0.36 * arm_raise)
    setp(16, 0.73, 0.58 - 0.36 * arm_raise)
    setp(17, 0.25, 0.60 - 0.36 * arm_raise)
    setp(18, 0.75, 0.60 - 0.36 * arm_raise)
    setp(19, 0.27, 0.57 - 0.36 * arm_raise)
    setp(20, 0.73, 0.57 - 0.36 * arm_raise)
    setp(21, 0.29, 0.56 - 0.36 * arm_raise)
    setp(22, 0.71, 0.56 - 0.36 * arm_raise)
    setp(23, 0.43, hip_y)
    setp(24, 0.57, hip_y)
    setp(25, 0.40 - 0.03 * lean, 0.74)
    setp(26, 0.60 + 0.03 * lean, 0.74)
    setp(27, 0.39 - 0.05 * lean, 0.92)
    setp(28, 0.61 + 0.05 * lean, 0.92)
    setp(29, 0.37 - 0.05 * lean, 0.94)
    setp(30, 0.63 + 0.05 * lean, 0.94)
    setp(31, 0.41 - 0.05 * lean, 0.95)
    setp(32, 0.59 + 0.05 * lean, 0.95)
    return points


def body_target(target: str) -> list[Landmark]:
    target = target.lower()
    if target in {"stand", "neutral"}:
        return synthetic_body()
    if target == "reach":
        return synthetic_body(arm_raise=1.0)
    if target == "walk":
        return synthetic_body(arm_raise=0.35, lean=0.8)
    raise ValueError(f"unknown body target: {target}")


def run_lesson(pose_type: str, target: str, out_dir: Path = DEFAULT_OUT) -> dict:
    pose_type = pose_type.lower()
    target = target.lower()
    run_dir = out_dir / f"{pose_type}_{target}"
    run_dir.mkdir(parents=True, exist_ok=True)

    if pose_type == "hand":
        reference = hand_target(target)
        attempt = synthetic_hand(curl=0.55, thumb_tuck=0.35) if target == "open" else hand_target("open")
        score = PoseChecker(soft_threshold=0.18, hard_threshold=0.8).check_hand(reference, attempt)
        target_pad = render_hand_sketch(reference, width=512, height=512)
        attempt_pad = render_hand_sketch(attempt, width=512, height=512)
    elif pose_type == "body":
        reference = body_target(target)
        attempt = synthetic_body(arm_raise=0.0, lean=0.0)
        score = PoseChecker(soft_threshold=0.18, hard_threshold=0.8).check_body(reference, attempt)
        target_pad = render_body_sketch(reference, width=512, height=512)
        attempt_pad = render_body_sketch(attempt, width=512, height=512)
    else:
        raise ValueError("pose_type must be 'hand' or 'body'")

    target_svg = target_pad.save_svg(run_dir / "target.svg")
    attempt_svg = attempt_pad.save_svg(run_dir / "attempt.svg")
    target_png = target_pad.save_png(run_dir / "target.png")
    attempt_png = attempt_pad.save_png(run_dir / "attempt.png")
    payload = {
        "schema": "scbe_pocket_drawing_tutor_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lesson": f"{pose_type} {target}",
        "target_svg": str(target_svg),
        "attempt_svg": str(attempt_svg),
        "target_png": str(target_png),
        "attempt_png": str(attempt_png),
        "score": score.to_dict(),
        "repair": _repair_hint(score.worst_chain),
    }
    (run_dir / "lesson.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _repair_hint(worst_chain: str | None) -> str:
    focus = worst_chain or "silhouette"
    return f"Repair one thing first: align the {focus} chain before adding style or texture."


def _clamp(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a deterministic pocket drawing lesson.")
    parser.add_argument("pose_type", choices=("hand", "body"))
    parser.add_argument("target")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    payload = run_lesson(args.pose_type, args.target, args.out_dir)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
