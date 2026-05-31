#!/usr/bin/env python3
"""Synthetic video-lattice coherence demo.

This does not render video. It tests the math core that a video renderer or
Unreal plugin would call: frame features enter multiple Poincare lattices,
temporal drift is measured, and correction events are emitted on abrupt shifts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "video_lattice"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.video_lattice import (  # noqa: E402
    BodyLandmark,
    HandLandmark,
    Landmark,
    LatticeAxis,
    MultiLattice,
    PerspectiveMap,
    TemporalTracker,
    body_polygon_features,
    hand_polygon_features,
    render_body_sketch,
    render_hand_sketch,
)


def _synthetic_hand(curl: float = 0.0, x_shift: float = 0.0) -> list[Landmark]:
    landmarks = [Landmark(x_shift, 0.0) for _ in range(21)]
    landmarks[HandLandmark.WRIST] = Landmark(x_shift, 0.0)
    bases = {
        HandLandmark.THUMB_CMC: (-0.24, 0.12),
        HandLandmark.INDEX_MCP: (-0.12, 0.30),
        HandLandmark.MIDDLE_MCP: (0.00, 0.34),
        HandLandmark.RING_MCP: (0.12, 0.30),
        HandLandmark.PINKY_MCP: (0.24, 0.24),
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
        landmarks[base] = Landmark(x + x_shift, y)
        for step, joint in enumerate(chain[1:], start=1):
            folded_x = x + (0.05 * step) * np.sign(x if x else 1.0)
            straight_y = y + 0.20 * step
            folded_y = y + (0.10, 0.08, 0.02)[step - 1]
            landmarks[joint] = Landmark(
                float((1.0 - curl) * x + curl * folded_x + x_shift),
                float((1.0 - curl) * straight_y + curl * folded_y),
            )
    return landmarks


def _synthetic_body(arm_raise: float = 0.0, x_shift: float = 0.0) -> list[Landmark]:
    landmarks = [Landmark(x_shift, 0.0) for _ in range(33)]
    coords = {
        BodyLandmark.NOSE: (0.0, 0.0),
        BodyLandmark.LEFT_SHOULDER: (-0.4, 0.6),
        BodyLandmark.RIGHT_SHOULDER: (0.4, 0.6),
        BodyLandmark.LEFT_ELBOW: (-0.7, 1.0 - arm_raise),
        BodyLandmark.RIGHT_ELBOW: (0.7, 1.0 - arm_raise),
        BodyLandmark.LEFT_WRIST: (-0.8, 1.4 - 1.6 * arm_raise),
        BodyLandmark.RIGHT_WRIST: (0.8, 1.4 - 1.6 * arm_raise),
        BodyLandmark.LEFT_HIP: (-0.3, 1.6),
        BodyLandmark.RIGHT_HIP: (0.3, 1.6),
        BodyLandmark.LEFT_KNEE: (-0.3, 2.3),
        BodyLandmark.RIGHT_KNEE: (0.3, 2.3),
        BodyLandmark.LEFT_ANKLE: (-0.3, 3.0),
        BodyLandmark.RIGHT_ANKLE: (0.3, 3.0),
    }
    for key, (x, y) in coords.items():
        landmarks[key] = Landmark(x + x_shift, y)
    return landmarks


def _frame_features(index: int) -> dict[LatticeAxis, np.ndarray]:
    """Generate deterministic frame features with two intentional disruptions."""

    t = index / 10.0
    base_motion = np.array([math.sin(t), math.cos(t), 0.05 * index])
    base_identity = np.array([0.2, 0.1, 0.05])
    base_scene = np.array([0.3, 0.2, 0.1])
    base_color = np.array([0.5 + 0.01 * math.sin(t), 0.4, 0.3])
    base_depth = np.array([0.2 + 0.01 * index, 0.1, 0.05])
    hand_curl = 0.15
    arm_raise = 0.1
    body_shift = 0.0

    # Motion shock: subject abruptly jumps/camera pans.
    if 12 <= index <= 14:
        base_motion = np.array([8.0, -7.0, 4.0])
        base_depth = np.array([5.0, 2.0, 1.0])
        hand_curl = 0.95
        arm_raise = 0.85

    # Scene cut: background, color, and structure shift together.
    if index == 22:
        base_scene = np.array([9.0, 8.0, 7.0])
        base_color = np.array([6.0, 4.0, 2.0])
        hand_curl = 0.75
        arm_raise = 0.65
        body_shift = 2.5

    hand = hand_polygon_features(_synthetic_hand(curl=hand_curl, x_shift=body_shift))
    body = body_polygon_features(_synthetic_body(arm_raise=arm_raise, x_shift=body_shift))
    body_structure = np.concatenate([hand, body])

    return {
        LatticeAxis.IDENTITY: base_identity,
        LatticeAxis.MOTION: base_motion,
        LatticeAxis.SCENE: base_scene,
        LatticeAxis.COLOR: base_color,
        LatticeAxis.DEPTH: base_depth,
        LatticeAxis.STRUCTURE: body_structure,
    }


def run_demo(frame_count: int = 30) -> dict:
    tracker = TemporalTracker(
        MultiLattice(
            dim=3,
            axis_dims={LatticeAxis.STRUCTURE: 35},
            correction_threshold=5.0,
        )
    )
    perspective = PerspectiveMap(max_depth=10.0)

    frames = []
    for index in range(frame_count):
        features = _frame_features(index)
        state = tracker.observe(features)
        depth_value = float(np.linalg.norm(features[LatticeAxis.DEPTH]))
        projected = perspective.project(depth=depth_value, angle=index / max(1, frame_count - 1) * math.tau)
        frames.append(
            {
                **state.to_dict(),
                "perspective_radius": projected.radius,
            }
        )

    correction_frames = [frame for frame in frames if frame["correction_triggered"]]
    max_frame = max(frames, key=lambda frame: frame["aggregate_drift"]) if frames else None

    return {
        "schema": "scbe_video_lattice_synthetic_demo_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frame_count": frame_count,
        "body_model": "33-landmark body pose + 21-landmark hand pose",
        "hand_model": "wrist, thumb chain, and four straight-finger chains",
        "generation_order": "2D skeleton -> hand/body polygons -> perspective/depth -> style/render",
        "correction_count": len(correction_frames),
        "correction_frames": [frame["frame_index"] for frame in correction_frames],
        "max_drift_frame": max_frame,
        "frames": frames,
        "summary": tracker.lattice.summary(),
        "interpretation": (
            "Stable frames should stay under threshold. The synthetic motion shock and scene cut "
            "should produce correction events, proving the lattice can detect temporal incoherence."
        ),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# SCBE Video Lattice Synthetic Demo",
        "",
        f"- **generated_at**: `{report['generated_at']}`",
        f"- **frame_count**: {report['frame_count']}",
        f"- **body_model**: {report['body_model']}",
        f"- **hand_model**: {report['hand_model']}",
        f"- **generation_order**: {report['generation_order']}",
        f"- **correction_count**: {report['correction_count']}",
        f"- **correction_frames**: {report['correction_frames']}",
        "",
        "## Max Drift",
        "",
    ]
    max_frame = report["max_drift_frame"] or {}
    lines.extend(
        [
            f"- frame: `{max_frame.get('frame_index')}`",
            f"- aggregate drift: `{max_frame.get('aggregate_drift')}`",
            f"- max axis: `{max_frame.get('max_drift_axis')}`",
            "",
            "## Frame Table",
            "",
            "| frame | drift | correction | max axis | perspective radius |",
            "|---:|---:|---|---|---:|",
        ]
    )
    for frame in report["frames"]:
        lines.append(
            f"| {frame['frame_index']} | {frame['aggregate_drift']:.4f} | "
            f"{'yes' if frame['correction_triggered'] else 'no'} | "
            f"{frame['max_drift_axis']} | {frame['perspective_radius']:.4f} |"
        )
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_demo(frame_count=args.frames)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "synthetic_video_lattice_demo.json"
    md_path = args.out_dir / "synthetic_video_lattice_demo.md"
    manifest_path = args.out_dir / "control_frame_manifest.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    _write_sketch_artifacts(args.out_dir)
    manifest_path.write_text(
        json.dumps(build_control_frame_manifest(report, args.out_dir), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")
        print(f"wrote {manifest_path}")
    return 0


def _write_sketch_artifacts(out_dir: Path) -> None:
    sketches_dir = out_dir / "sketches"
    base_hand = render_hand_sketch(_synthetic_hand(curl=0.15), width=512, height=512)
    fist_hand = render_hand_sketch(_synthetic_hand(curl=0.95), width=512, height=512)
    base_body = render_body_sketch(_synthetic_body(arm_raise=0.10), width=768, height=768)
    action_body = render_body_sketch(_synthetic_body(arm_raise=0.85), width=768, height=768)

    for name, sketch in {
        "hand_base": base_hand,
        "hand_fist": fist_hand,
        "body_base": base_body,
        "body_action": action_body,
    }.items():
        sketch.save_svg(sketches_dir / f"{name}.svg")
        sketch.save_png(sketches_dir / f"{name}.png")


def build_control_frame_manifest(report: dict, out_dir: Path) -> dict:
    """Create an inside-out video-generation control manifest.

    The manifest is deliberately renderer-neutral. A diffusion workflow can use
    the PNG/SVG sketches as conditioning images; Unreal or another renderer can
    read the same pose parameters as deterministic scene constraints.
    """

    sketches_dir = out_dir / "sketches"
    frames = []
    for frame in report["frames"]:
        index = frame["frame_index"]
        is_motion_shock = 12 <= index <= 14
        is_scene_cut = index == 22
        pose_name = "action" if is_motion_shock or is_scene_cut else "base"
        hand_name = "fist" if is_motion_shock or is_scene_cut else "base"
        frames.append(
            {
                "frame_index": index,
                "pose_state": {
                    "body": pose_name,
                    "hand": hand_name,
                    "inside_out_stage": report["generation_order"],
                    "arm_raise": 0.85 if is_motion_shock else 0.65 if is_scene_cut else 0.10,
                    "hand_curl": 0.95 if is_motion_shock else 0.75 if is_scene_cut else 0.15,
                },
                "control_assets": {
                    "body_svg": str((sketches_dir / f"body_{pose_name}.svg").relative_to(REPO_ROOT)),
                    "body_png": str((sketches_dir / f"body_{pose_name}.png").relative_to(REPO_ROOT)),
                    "hand_svg": str((sketches_dir / f"hand_{hand_name}.svg").relative_to(REPO_ROOT)),
                    "hand_png": str((sketches_dir / f"hand_{hand_name}.png").relative_to(REPO_ROOT)),
                },
                "prompt_layers": {
                    "structure": "follow the 2D skeleton, palm polygon, thumb chain, and four finger chains",
                    "perspective": "preserve depth and camera continuity unless the frame is marked as a scene cut",
                    "style": "apply style after anatomy and motion constraints are satisfied",
                    "negative": "extra fingers, missing thumb, melted hands, broken wrists, disconnected limbs",
                },
                "lattice": {
                    "aggregate_drift": frame["aggregate_drift"],
                    "max_drift_axis": frame["max_drift_axis"],
                    "correction_triggered": frame["correction_triggered"],
                    "perspective_radius": frame["perspective_radius"],
                },
            }
        )

    return {
        "schema": "scbe_video_control_frame_manifest_v1",
        "source_schema": report["schema"],
        "frame_count": report["frame_count"],
        "generation_order": report["generation_order"],
        "body_model": report["body_model"],
        "hand_model": report["hand_model"],
        "renderer_targets": ["svg_control", "png_control", "diffusion_conditioning", "ue5_scene_constraints"],
        "frames": frames,
    }


if __name__ == "__main__":
    raise SystemExit(main())
