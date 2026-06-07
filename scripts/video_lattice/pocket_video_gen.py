#!/usr/bin/env python3
"""Generate a tiny inside-out animation from pocket drawing poses.

This is intentionally small: no diffusion model, no Unreal dependency, no
FFmpeg requirement. It renders a pose sequence into PNG frames and an animated
GIF so the video-generation control loop can be tested on any workstation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.video_lattice.pocket_drawing_tutor import (  # noqa: E402
    body_target,
    hand_target,
    synthetic_body,
    synthetic_hand,
)
from src.video_lattice import (
    Landmark,
    PoseChecker,
    render_body_sketch,
    render_hand_sketch,
)  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "artifacts" / "video_lattice" / "pocket_video_gen"


@dataclass(frozen=True)
class AnimationFrame:
    frame_index: int
    progress: float
    pose_type: str
    target: str
    drift: float
    verdict: str
    worst_chain: str | None
    png: str


def interpolate_landmarks(
    a: Sequence[Landmark], b: Sequence[Landmark], t: float
) -> list[Landmark]:
    return [
        Landmark(
            x=(1.0 - t) * pa.x + t * pb.x,
            y=(1.0 - t) * pa.y + t * pb.y,
            z=(1.0 - t) * pa.z + t * pb.z,
            visibility=(1.0 - t) * pa.visibility + t * pb.visibility,
        )
        for pa, pb in zip(a, b)
    ]


def _start_pose(pose_type: str, target: str) -> list[Landmark]:
    if pose_type == "hand":
        if target == "open":
            return synthetic_hand(curl=0.70, thumb_tuck=0.45)
        return hand_target("open")
    if target == "reach":
        return synthetic_body(arm_raise=0.0)
    return synthetic_body(arm_raise=0.45, lean=0.25)


def _target_pose(pose_type: str, target: str) -> list[Landmark]:
    return hand_target(target) if pose_type == "hand" else body_target(target)


def _render_pose_png(
    pose_type: str,
    landmarks: Sequence[Landmark],
    path: Path,
    *,
    title: str,
    subtitle: str,
    drift: float,
    verdict: str,
    worst_chain: str | None,
) -> None:
    sketch = (
        render_hand_sketch(landmarks, width=512, height=512)
        if pose_type == "hand"
        else render_body_sketch(landmarks, width=512, height=512)
    )
    tmp = path.with_suffix(".sketch.png")
    sketch.save_png(tmp)

    canvas = Image.new("RGB", (1280, 720), (14, 18, 29))
    draw = ImageDraw.Draw(canvas)
    sketch_img = Image.open(tmp).convert("RGB")
    canvas.paste(sketch_img, (64, 104))

    title_font = _font(42, bold=True)
    body_font = _font(28)
    mono_font = _font(24)
    draw.text((640, 110), title, fill=(232, 238, 248), font=title_font)
    draw.text((640, 168), subtitle, fill=(160, 176, 200), font=body_font)
    draw.text((640, 250), f"drift: {drift:.4f}", fill=(250, 204, 21), font=mono_font)
    draw.text(
        (640, 292), f"verdict: {verdict}", fill=_verdict_color(verdict), font=mono_font
    )
    draw.text(
        (640, 334),
        f"repair focus: {worst_chain or 'stable'}",
        fill=(190, 210, 230),
        font=mono_font,
    )
    draw.text((640, 430), "inside-out order:", fill=(117, 215, 255), font=body_font)
    for i, line in enumerate(
        ("skeleton", "polygon chains", "lattice score", "render frame")
    ):
        draw.text(
            (676, 472 + i * 34),
            f"{i + 1}. {line}",
            fill=(205, 214, 229),
            font=mono_font,
        )
    draw.rectangle((48, 88, 592, 648), outline=(117, 215, 255), width=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    try:
        tmp.unlink()
    except OSError:
        pass


def _font(size: int, *, bold: bool = False):
    names = (
        ["arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold
        else ["arial.ttf", "DejaVuSans.ttf"]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
        win = Path("C:/Windows/Fonts") / name
        if win.exists():
            try:
                return ImageFont.truetype(str(win), size)
            except OSError:
                pass
    return ImageFont.load_default()


def _verdict_color(verdict: str) -> tuple[int, int, int]:
    if verdict == "pass":
        return (74, 222, 128)
    if verdict == "soft":
        return (250, 204, 21)
    return (248, 113, 113)


def run_generation(
    pose_type: str,
    target: str,
    *,
    frames: int = 16,
    out_dir: Path = DEFAULT_OUT,
    duration_ms: int = 110,
) -> dict:
    if frames < 2:
        raise ValueError("frames must be >= 2")
    target_pose = _target_pose(pose_type, target)
    start_pose = _start_pose(pose_type, target)
    checker = PoseChecker(soft_threshold=0.18, hard_threshold=0.8)

    run_dir = out_dir / f"{pose_type}_{target}_{frames}f"
    frame_dir = run_dir / "frames"
    frame_records: list[AnimationFrame] = []
    images: list[Image.Image] = []

    for index in range(frames):
        t = index / (frames - 1)
        # Smoothstep makes the motion less robotic while staying deterministic.
        progress = t * t * (3.0 - 2.0 * t)
        pose = interpolate_landmarks(start_pose, target_pose, progress)
        result = (
            checker.check_hand(target_pose, pose)
            if pose_type == "hand"
            else checker.check_body(target_pose, pose)
        )
        png_path = frame_dir / f"frame_{index:03d}.png"
        _render_pose_png(
            pose_type,
            pose,
            png_path,
            title=f"Pocket video: {pose_type} {target}",
            subtitle=f"frame {index + 1}/{frames} | progress {progress:.2f}",
            drift=result.overall_drift,
            verdict=result.verdict.value,
            worst_chain=result.worst_chain,
        )
        images.append(Image.open(png_path).convert("P", palette=Image.Palette.ADAPTIVE))
        frame_records.append(
            AnimationFrame(
                frame_index=index,
                progress=round(progress, 4),
                pose_type=pose_type,
                target=target,
                drift=round(result.overall_drift, 5),
                verdict=result.verdict.value,
                worst_chain=result.worst_chain,
                png=str(png_path),
            )
        )

    gif_path = run_dir / "animation.gif"
    gif_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=duration_ms,
        loop=0,
        optimize=False,
    )

    manifest = {
        "schema": "scbe_pocket_video_generation_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pose_type": pose_type,
        "target": target,
        "frame_count": frames,
        "duration_ms": duration_ms,
        "animation_gif": str(gif_path),
        "frames_dir": str(frame_dir),
        "frames": [record.__dict__ for record in frame_records],
        "interpretation": (
            "A deterministic inside-out video test: rough pose moves toward target pose, "
            "each frame is rendered as a sketch and scored by the pose lattice."
        ),
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a pocket-lattice animation GIF."
    )
    parser.add_argument("pose_type", choices=("hand", "body"))
    parser.add_argument("target", help="hand: open/fist/point; body: stand/reach/lean")
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--duration-ms", type=int, default=110)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    manifest = run_generation(
        args.pose_type,
        args.target,
        frames=args.frames,
        out_dir=args.out_dir,
        duration_ms=args.duration_ms,
    )
    print(
        json.dumps(
            {
                "animation_gif": manifest["animation_gif"],
                "frames_dir": manifest["frames_dir"],
                "frame_count": manifest["frame_count"],
                "first_drift": manifest["frames"][0]["drift"],
                "last_drift": manifest["frames"][-1]["drift"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
