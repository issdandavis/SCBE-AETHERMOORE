"""Paint-like sketch pad for inside-out video generation.

This is a small deterministic drawing API, not a GUI. It renders the structure
that a video generator should respect before style is applied:
  1. 2D pose skeleton
  2. hand/body polygons
  3. joint markers and labels
  4. optional PNG preview for quick inspection
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .pose_polygons import (
    BODY_CHAINS,
    BODY_TORSO_POLYGON,
    HAND_FINGERS,
    HAND_PALM_POLYGON,
    BodyLandmark,
    HandLandmark,
    Landmark,
)


@dataclass(frozen=True)
class CanvasPoint:
    x: float
    y: float


@dataclass
class SketchPad:
    """Minimal SVG sketch pad with optional PNG export."""

    width: int = 768
    height: int = 768
    margin: int = 64
    background: str = "#10141f"
    strokes: list[str] = field(default_factory=list)

    def map_point(self, point: Landmark | Sequence[float]) -> CanvasPoint:
        if isinstance(point, Landmark):
            x, y = point.x, point.y
        else:
            x, y = float(point[0]), float(point[1])
        return CanvasPoint(
            self.margin + x * (self.width - 2 * self.margin),
            self.margin + y * (self.height - 2 * self.margin),
        )

    def line(
        self,
        a: Landmark | Sequence[float],
        b: Landmark | Sequence[float],
        *,
        color: str = "#e7edf8",
        width: float = 3.0,
    ) -> None:
        pa = self.map_point(a)
        pb = self.map_point(b)
        self.strokes.append(
            f'<line x1="{pa.x:.2f}" y1="{pa.y:.2f}" x2="{pb.x:.2f}" y2="{pb.y:.2f}" '
            f'stroke="{escape(color)}" stroke-width="{width:.2f}" stroke-linecap="round" />'
        )

    def polyline(
        self, points: Iterable[Landmark | Sequence[float]], *, color: str = "#e7edf8", width: float = 3.0
    ) -> None:
        mapped = [self.map_point(point) for point in points]
        if len(mapped) < 2:
            return
        attr = " ".join(f"{point.x:.2f},{point.y:.2f}" for point in mapped)
        self.strokes.append(
            f'<polyline points="{attr}" fill="none" stroke="{escape(color)}" '
            f'stroke-width="{width:.2f}" stroke-linecap="round" stroke-linejoin="round" />'
        )

    def polygon(
        self,
        points: Iterable[Landmark | Sequence[float]],
        *,
        stroke: str = "#75d7ff",
        fill: str = "rgba(117,215,255,0.14)",
        width: float = 2.0,
    ) -> None:
        mapped = [self.map_point(point) for point in points]
        if len(mapped) < 3:
            return
        attr = " ".join(f"{point.x:.2f},{point.y:.2f}" for point in mapped)
        self.strokes.append(
            f'<polygon points="{attr}" fill="{escape(fill)}" stroke="{escape(stroke)}" '
            f'stroke-width="{width:.2f}" stroke-linejoin="round" />'
        )

    def circle(self, point: Landmark | Sequence[float], *, radius: float = 4.0, color: str = "#ffffff") -> None:
        p = self.map_point(point)
        self.strokes.append(f'<circle cx="{p.x:.2f}" cy="{p.y:.2f}" r="{radius:.2f}" fill="{escape(color)}" />')

    def text(self, point: Landmark | Sequence[float], label: str, *, color: str = "#b8c7dd", size: int = 12) -> None:
        p = self.map_point(point)
        self.strokes.append(
            f'<text x="{p.x + 7:.2f}" y="{p.y - 7:.2f}" fill="{escape(color)}" '
            f'font-size="{size}" font-family="Consolas, monospace">{escape(label)}</text>'
        )

    def render_svg(self) -> str:
        body = "\n  ".join(self.strokes)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            f'  <rect width="100%" height="100%" fill="{escape(self.background)}" />\n'
            f"  {body}\n"
            "</svg>\n"
        )

    def save_svg(self, path: Path | str) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render_svg(), encoding="utf-8")
        return out

    def save_png(self, path: Path | str) -> Path:
        """Rasterize the simple sketch commands using Pillow when available."""

        try:
            from PIL import Image, ImageColor, ImageDraw
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("Pillow is required for PNG export") from exc

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (self.width, self.height), ImageColor.getrgb(self.background))
        draw = ImageDraw.Draw(img)
        # PNG export is intentionally basic; SVG remains the authoritative form.
        for command in self.strokes:
            if command.startswith("<line"):
                attrs = _svg_attrs(command)
                draw.line(
                    [
                        (float(attrs["x1"]), float(attrs["y1"])),
                        (float(attrs["x2"]), float(attrs["y2"])),
                    ],
                    fill=attrs.get("stroke", "#ffffff"),
                    width=max(1, int(float(attrs.get("stroke-width", "2")))),
                )
            elif command.startswith("<circle"):
                attrs = _svg_attrs(command)
                x = float(attrs["cx"])
                y = float(attrs["cy"])
                r = float(attrs["r"])
                draw.ellipse((x - r, y - r, x + r, y + r), fill=attrs.get("fill", "#ffffff"))
            elif command.startswith("<polyline"):
                attrs = _svg_attrs(command)
                points = _parse_svg_points(attrs.get("points", ""))
                if len(points) >= 2:
                    draw.line(
                        points,
                        fill=attrs.get("stroke", "#ffffff"),
                        width=max(1, int(float(attrs.get("stroke-width", "2")))),
                        joint="curve",
                    )
            elif command.startswith("<polygon"):
                attrs = _svg_attrs(command)
                points = _parse_svg_points(attrs.get("points", ""))
                if len(points) >= 3:
                    draw.polygon(points, fill=attrs.get("fill", "#19384b"))
                    draw.line(
                        [*points, points[0]],
                        fill=attrs.get("stroke", "#ffffff"),
                        width=max(1, int(float(attrs.get("stroke-width", "2")))),
                    )
        img.save(out)
        return out


def render_hand_sketch(
    landmarks: Sequence[Landmark] | Mapping[HandLandmark, Landmark],
    *,
    width: int = 512,
    height: int = 512,
) -> SketchPad:
    mapped = _map_landmarks(landmarks)
    pad = SketchPad(width=width, height=height)
    pad.polygon([mapped[int(i)] for i in HAND_PALM_POLYGON], stroke="#75d7ff", fill="#19384b")
    colors = {
        "thumb": "#ffb86c",
        "index": "#f8f871",
        "middle": "#8be9fd",
        "ring": "#bd93f9",
        "pinky": "#ff79c6",
    }
    for name, chain in HAND_FINGERS.items():
        points = [mapped[int(i)] for i in chain]
        pad.polyline(points, color=colors[name], width=4.0)
        pad.text(points[-1], name, color=colors[name])
    for index in HandLandmark:
        pad.circle(mapped[int(index)], radius=3.5, color="#f8f8f2")
    return pad


def render_body_sketch(
    landmarks: Sequence[Landmark] | Mapping[BodyLandmark, Landmark],
    *,
    width: int = 768,
    height: int = 768,
) -> SketchPad:
    mapped = _map_landmarks(landmarks)
    pad = SketchPad(width=width, height=height)
    pad.polygon([mapped[int(i)] for i in BODY_TORSO_POLYGON], stroke="#75d7ff", fill="#19384b")
    for name, chain in BODY_CHAINS.items():
        points = [mapped[int(i)] for i in chain]
        pad.polyline(points, color="#f8f8f2", width=5.0)
        pad.text(points[-1], name, color="#b8c7dd")
    for index in (
        BodyLandmark.NOSE,
        BodyLandmark.LEFT_SHOULDER,
        BodyLandmark.RIGHT_SHOULDER,
        BodyLandmark.LEFT_ELBOW,
        BodyLandmark.RIGHT_ELBOW,
        BodyLandmark.LEFT_WRIST,
        BodyLandmark.RIGHT_WRIST,
        BodyLandmark.LEFT_HIP,
        BodyLandmark.RIGHT_HIP,
        BodyLandmark.LEFT_KNEE,
        BodyLandmark.RIGHT_KNEE,
        BodyLandmark.LEFT_ANKLE,
        BodyLandmark.RIGHT_ANKLE,
    ):
        pad.circle(mapped[int(index)], radius=4.5, color="#f8f8f2")
    return pad


def _map_landmarks(
    landmarks: Sequence[Landmark] | Mapping[HandLandmark | BodyLandmark, Landmark],
) -> dict[int, Landmark]:
    if isinstance(landmarks, Mapping):
        return {int(key): value for key, value in landmarks.items()}
    return {index: value for index, value in enumerate(landmarks)}


def _svg_attrs(command: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in re.finditer(r'([a-zA-Z0-9:-]+)="([^"]*)"', command)}


def _parse_svg_points(points: str) -> list[tuple[float, float]]:
    parsed = []
    for item in points.split():
        if "," not in item:
            continue
        x, y = item.split(",", 1)
        parsed.append((float(x), float(y)))
    return parsed
