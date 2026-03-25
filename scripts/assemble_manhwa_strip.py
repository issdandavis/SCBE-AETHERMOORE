#!/usr/bin/env python3
"""
Assemble manhwa panels into a vertical scroll strip for webtoon/app delivery.

Resizes all panels to a uniform width, adds scroll gaps between panels,
and slices the final strip into max-height segments for mobile rendering.

Usage:
    python scripts/assemble_manhwa_strip.py --chapter ch01
    python scripts/assemble_manhwa_strip.py --chapter ch01 --width 800 --gap 40
    python scripts/assemble_manhwa_strip.py --chapter ch01 --slice-height 1400
    python scripts/assemble_manhwa_strip.py --input artifacts/webtoon/ch01/v3 --output artifacts/manhwa/strips/ch01
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from webtoon_quality_gate import load_quality_report
except ImportError:  # pragma: no cover - import path fallback for tests
    from scripts.webtoon_quality_gate import load_quality_report

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WIDTH = 800
DEFAULT_GAP = 30
DEFAULT_SLICE_HEIGHT = 1280
DEFAULT_BG = (18, 18, 18)  # dark background between panels


def find_panels(input_dir: Path) -> list[Path]:
    """Find and sort panel images by panel number."""
    panels = []
    for f in input_dir.iterdir():
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            m = re.search(r"p(\d+)", f.stem)
            if m:
                panels.append((int(m.group(1)), f))
    panels.sort(key=lambda x: x[0])
    return [p[1] for p in panels]


def default_quality_report_path(chapter: str) -> Path:
    return ROOT / "artifacts" / "webtoon" / "panel_prompts" / f"{chapter}_quality_report.json"


def require_approved_packet(report_path: Path, chapter: str, panel_count: int | None = None) -> dict:
    if not report_path.exists():
        raise FileNotFoundError(f"Quality report not found: {report_path}")

    report = load_quality_report(report_path)
    if report.get("chapter_id") and report["chapter_id"] != chapter:
        raise ValueError(f"Quality report chapter mismatch: expected {chapter}, found {report.get('chapter_id')}")
    if not report.get("approved"):
        raise ValueError(f"Packet report is not approved: {report_path}")
    if panel_count is not None and isinstance(report.get("panel_count"), int) and report["panel_count"] != panel_count:
        raise ValueError(
            f"Panel count mismatch for approved packet: report expects {report['panel_count']}, found {panel_count}"
        )
    return report


def _require_pillow() -> None:
    if Image is None:
        raise ImportError("Pillow required: pip install Pillow")


def assemble_strip(
    panels: list[Path],
    width: int = DEFAULT_WIDTH,
    gap: int = DEFAULT_GAP,
    bg_color: tuple = DEFAULT_BG,
) -> Image.Image:
    """Assemble panels into a single vertical strip."""
    _require_pillow()
    resized = []
    for p in panels:
        img = Image.open(p).convert("RGB")
        ratio = width / img.width
        new_h = int(img.height * ratio)
        img = img.resize((width, new_h), Image.LANCZOS)
        resized.append(img)

    total_height = sum(img.height for img in resized) + gap * (len(resized) - 1)
    strip = Image.new("RGB", (width, total_height), bg_color)

    y = 0
    for i, img in enumerate(resized):
        strip.paste(img, (0, y))
        y += img.height
        if i < len(resized) - 1:
            y += gap

    return strip


def slice_strip(
    strip: Image.Image,
    max_height: int = DEFAULT_SLICE_HEIGHT,
    output_dir: Path = None,
    prefix: str = "slice",
) -> list[Path]:
    """Slice a tall strip into segments for mobile rendering."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slices = []
    y = 0
    idx = 1
    while y < strip.height:
        bottom = min(y + max_height, strip.height)
        segment = strip.crop((0, y, strip.width, bottom))
        out_path = output_dir / f"{prefix}-{idx:03d}.jpg"
        segment.save(out_path, "JPEG", quality=92)
        slices.append(out_path)
        y = bottom
        idx += 1
    return slices


def main():
    parser = argparse.ArgumentParser(description="Assemble manhwa vertical strip")
    parser.add_argument("--chapter", default="ch01", help="Chapter ID (default: ch01)")
    parser.add_argument("--input", help="Input directory with panel images")
    parser.add_argument("--output", help="Output directory for strip and slices")
    parser.add_argument(
        "--width", type=int, default=DEFAULT_WIDTH, help=f"Strip width in px (default: {DEFAULT_WIDTH})"
    )
    parser.add_argument(
        "--gap", type=int, default=DEFAULT_GAP, help=f"Gap between panels in px (default: {DEFAULT_GAP})"
    )
    parser.add_argument(
        "--slice-height",
        type=int,
        default=DEFAULT_SLICE_HEIGHT,
        help=f"Max slice height (default: {DEFAULT_SLICE_HEIGHT})",
    )
    parser.add_argument("--no-slice", action="store_true", help="Output full strip only, no slicing")
    parser.add_argument("--prefer-hq", action="store_true", help="Use HQ panels when available, fall back to v3")
    parser.add_argument("--report", help="Optional governed packet report path")
    parser.add_argument("--allow-unapproved-packet", action="store_true", help="Skip approved-packet enforcement")
    args = parser.parse_args()

    # Resolve input directory
    if args.input:
        input_dir = Path(args.input)
    else:
        input_dir = ROOT / "artifacts" / "webtoon" / args.chapter / "v3"

    if not input_dir.exists():
        sys.exit(f"Input directory not found: {input_dir}")

    # If prefer-hq, build a merged panel list
    if args.prefer_hq:
        hq_dir = ROOT / "kindle-app" / "www" / "manhwa" / args.chapter / "hq"
        v3_panels = find_panels(input_dir)
        hq_panels = find_panels(hq_dir) if hq_dir.exists() else []
        hq_map = {}
        for p in hq_panels:
            m = re.search(r"p(\d+)", p.stem)
            if m:
                hq_map[int(m.group(1))] = p
        panels = []
        for p in v3_panels:
            m = re.search(r"p(\d+)", p.stem)
            num = int(m.group(1)) if m else None
            if num and num in hq_map:
                panels.append(hq_map[num])
            else:
                panels.append(p)
    else:
        panels = find_panels(input_dir)

    if not panels:
        sys.exit(f"No panels found in {input_dir}")

    if not args.allow_unapproved_packet:
        report_path = Path(args.report) if args.report else default_quality_report_path(args.chapter)
        try:
            require_approved_packet(report_path, args.chapter, panel_count=len(panels))
        except (FileNotFoundError, ValueError) as exc:
            sys.exit(str(exc))
        print(f"Quality gate: approved packet report {report_path}")

    print(f"Assembling {len(panels)} panels at {args.width}px wide, {args.gap}px gaps...")

    # Resolve output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = ROOT / "artifacts" / "manhwa" / "strips" / args.chapter

    output_dir.mkdir(parents=True, exist_ok=True)

    # Assemble
    strip = assemble_strip(panels, width=args.width, gap=args.gap)
    strip_path = output_dir / f"{args.chapter}-full-strip.png"
    strip.save(strip_path, "PNG")
    print(f"Full strip: {strip_path} ({strip.width}x{strip.height})")

    # Slice
    if not args.no_slice:
        slices = slice_strip(
            strip, max_height=args.slice_height, output_dir=output_dir, prefix=f"{args.chapter}-scroll"
        )
        print(f"Sliced into {len(slices)} segments at max {args.slice_height}px height")
        for s in slices:
            print(f"  {s.name}")

    # Copy to app delivery
    app_dir = ROOT / "kindle-app" / "www" / "manhwa" / args.chapter / "strip"
    app_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_slice:
        for s in slices:
            dest = app_dir / s.name
            import shutil

            shutil.copy2(s, dest)
        print(f"Copied to app: {app_dir}")

    print("Done.")


if __name__ == "__main__":
    main()
