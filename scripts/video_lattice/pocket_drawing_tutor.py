#!/usr/bin/env python3
"""Deterministic pocket drawing tutor for video-lattice pose repair.

The tutor writes a target sketch, a deliberately imperfect attempt sketch, and
the pose-check receipt that explains what to repair. It is intentionally local:
no model calls, no camera input, no renderer dependency beyond the existing
SketchPad/Pillow path.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.video_lattice import (
    Landmark,
    PoseChecker,
    render_body_sketch,
    render_hand_sketch,
)  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "artifacts" / "video_lattice" / "pocket_drawing_tutor"


def _lm(x: float, y: float, z: float = 0.0, visibility: float = 1.0) -> Landmark:
    return Landmark(x=x, y=y, z=z, visibility=visibility)


def synthetic_hand(*, curl: float = 0.0, thumb_tuck: float = 0.0) -> list[Landmark]:
    """Build a 21-point hand pose with controllable finger curl."""
    curl = max(0.0, min(1.0, curl))
    thumb_tuck = max(0.0, min(1.0, thumb_tuck))
    points = [_lm(0.5, 0.86)]

    # Thumb: folded thumbs move inward and down toward the palm.
    thumb_base = [(0.40, 0.72), (0.31, 0.63), (0.24, 0.54), (0.18, 0.45)]
    for i, (x, y) in enumerate(thumb_base, start=1):
        tuck = thumb_tuck * i / 4.0
        points.append(_lm(x + 0.25 * tuck, y + 0.23 * tuck, -0.01 * i))

    finger_specs = [
        (0.37, 0.62, -0.12, "index"),
        (0.46, 0.57, -0.18, "middle"),
        (0.55, 0.59, -0.15, "ring"),
        (0.64, 0.64, -0.10, "pinky"),
    ]
    for base_x, base_y, open_dx, _name in finger_specs:
        points.append(_lm(base_x, base_y))
        for joint in range(1, 4):
            open_step = joint / 3.0
            folded_step = curl * open_step
            x = base_x + open_dx * open_step + 0.08 * folded_step
            y = base_y - 0.34 * open_step + 0.40 * folded_step
            points.append(_lm(x, y, -0.02 * joint))
    return points


def hand_target(target: str) -> list[Landmark]:
    if target == "open":
        return synthetic_hand(curl=0.02, thumb_tuck=0.0)
    if target == "fist":
        return synthetic_hand(curl=0.88, thumb_tuck=0.72)
    raise ValueError("hand target must be 'open' or 'fist'")


def synthetic_body(*, arm_raise: float = 0.0, lean: float = 0.0) -> list[Landmark]:
    """Build a 33-point body pose compatible with MediaPipe-style indices."""
    arm_raise = max(0.0, min(1.0, arm_raise))
    lean = max(-1.0, min(1.0, lean))
    points = [_lm(0.5 + 0.03 * lean, 0.18) for _ in range(33)]

    def put(index: int, x: float, y: float) -> None:
        points[index] = _lm(x + 0.03 * lean, y)

    put(0, 0.50, 0.12)
    put(11, 0.38, 0.32)
    put(12, 0.62, 0.32)
    put(13, 0.30, 0.44 - 0.18 * arm_raise)
    put(14, 0.70, 0.44 - 0.18 * arm_raise)
    put(15, 0.26, 0.58 - 0.36 * arm_raise)
    put(16, 0.74, 0.58 - 0.36 * arm_raise)
    put(23, 0.42, 0.60)
    put(24, 0.58, 0.60)
    put(25, 0.39, 0.78)
    put(26, 0.61, 0.78)
    put(27, 0.36, 0.94)
    put(28, 0.64, 0.94)
    return points


def body_target(target: str) -> list[Landmark]:
    if target == "reach":
        return synthetic_body(arm_raise=0.95)
    if target == "walk":
        return synthetic_body(arm_raise=0.25, lean=0.35)
    raise ValueError("body target must be 'reach' or 'walk'")


def _attempt_pose(pose_type: str, target: str) -> list[Landmark]:
    if pose_type == "hand":
        if target == "open":
            return synthetic_hand(curl=0.48, thumb_tuck=0.34)
        return synthetic_hand(curl=0.26, thumb_tuck=0.12)
    if target == "reach":
        return synthetic_body(arm_raise=0.28)
    return synthetic_body(arm_raise=0.12, lean=-0.25)


def _render(pose_type: str, pose: list[Landmark]):
    return render_hand_sketch(pose) if pose_type == "hand" else render_body_sketch(pose)


def run_lesson(pose_type: str, target: str, out_dir: Path = DEFAULT_OUT) -> dict:
    if pose_type not in {"hand", "body"}:
        raise ValueError("pose_type must be 'hand' or 'body'")
    target_pose = hand_target(target) if pose_type == "hand" else body_target(target)
    attempt_pose = _attempt_pose(pose_type, target)
    checker = PoseChecker(soft_threshold=0.18, hard_threshold=0.8)
    score = (
        checker.check_hand(target_pose, attempt_pose)
        if pose_type == "hand"
        else checker.check_body(target_pose, attempt_pose)
    )

    run_dir = out_dir / f"{pose_type}_{target}"
    target_svg = _render(pose_type, target_pose).save_svg(run_dir / "target.svg")
    attempt_svg = _render(pose_type, attempt_pose).save_svg(run_dir / "attempt.svg")
    target_png = _render(pose_type, target_pose).save_png(run_dir / "target.png")
    attempt_png = _render(pose_type, attempt_pose).save_png(run_dir / "attempt.png")

    repair = f"Repair one thing: reduce drift in {score.worst_chain or 'the main pose chain'}."
    payload = {
        "schema": "scbe_pocket_drawing_tutor_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lesson": f"{pose_type} {target}",
        "pose_type": pose_type,
        "target": target,
        "target_svg": str(target_svg),
        "attempt_svg": str(attempt_svg),
        "target_png": str(target_png),
        "attempt_png": str(attempt_png),
        "score": score.to_dict(),
        "repair": repair,
    }
    (run_dir / "lesson.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render and score a pocket drawing lesson."
    )
    parser.add_argument("pose_type", choices=["hand", "body"])
    parser.add_argument("target")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        payload = run_lesson(args.pose_type, args.target, args.out_dir)
    except ValueError as exc:
        print(f"pocket-drawing-tutor error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"{payload['lesson']}: {payload['score']['verdict']} drift={payload['score']['overall_drift']}"
        )
        print(payload["repair"])
        print(payload["attempt_png"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
