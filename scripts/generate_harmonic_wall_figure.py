#!/usr/bin/env python3
"""Generate Harmonic Wall (H(d,R)=R^(d^2)) patent figure artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = "artifacts/ip"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aethermoore_patent_math import harmonic_security_scaling


@dataclass
class Series:
    R: float
    points: List[Dict[str, float]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate data + SVG for Harmonic Wall Figure 1."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--r-values",
        default="1.25,1.5,2.0",
        help="Comma-separated R values for H(d,R)=R^(d^2).",
    )
    parser.add_argument("--d-min", type=int, default=0, help="Minimum d value.")
    parser.add_argument("--d-max", type=int, default=12, help="Maximum d value.")
    parser.add_argument("--figure-name", default="harmonic_wall_figure1", help="Figure base filename.")
    return parser.parse_args()


def parse_r_values(raw: str) -> List[float]:
    values: List[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(float(part))
    if not values:
        raise ValueError("At least one R value is required.")
    for value in values:
        if value <= 1.0:
            raise ValueError("All R values must be > 1.0 for superexponential scaling.")
    return values


def build_series(r_values: List[float], d_min: int, d_max: int) -> List[Series]:
    if d_min < 0:
        raise ValueError("d-min must be >= 0")
    if d_max < d_min:
        raise ValueError("d-max must be >= d-min")

    data: List[Series] = []
    for R in r_values:
        points: List[Dict[str, float]] = []
        for d in range(d_min, d_max + 1):
            H = harmonic_security_scaling(d, R)
            points.append(
                {
                    "d": float(d),
                    "R": float(R),
                    "H": float(H),
                    "log10_H": float(math.log10(H)) if H > 0 else float("-inf"),
                }
            )
        data.append(Series(R=R, points=points))
    return data


def write_csv(path: Path, data: List[Series]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["d", "R", "H_d_R", "log10_H_d_R"])
        for series in data:
            for point in series.points:
                writer.writerow(
                    [
                        int(point["d"]),
                        f"{series.R:.10g}",
                        f"{point['H']:.16g}",
                        f"{point['log10_H']:.16g}",
                    ]
                )


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def build_svg(data: List[Series], d_min: int, d_max: int) -> str:
    width = 1024
    height = 640
    margin_left = 90
    margin_right = 40
    margin_top = 40
    margin_bottom = 80
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    colors = ["#0b6e4f", "#1f4e79", "#b23a48", "#6a4c93", "#f77f00", "#2a9d8f"]

    all_logs = [pt["log10_H"] for s in data for pt in s.points]
    y_min = min(all_logs)
    y_max = max(all_logs)
    if y_max <= y_min:
        y_max = y_min + 1.0

    def x_of(d: float) -> float:
        if d_max == d_min:
            return margin_left
        return margin_left + ((d - d_min) / (d_max - d_min)) * plot_w

    def y_of(log10_h: float) -> float:
        return margin_top + (1.0 - (log10_h - y_min) / (y_max - y_min)) * plot_h

    svg: List[str] = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    svg.append('<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>')
    svg.append(f'<text x="{margin_left}" y="24" font-family="monospace" font-size="18" fill="#222">Figure 1: Harmonic Wall Scaling (log10 H(d,R))</text>')

    # Axes
    x0 = margin_left
    y0 = margin_top + plot_h
    x1 = margin_left + plot_w
    y1 = margin_top
    svg.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#333" stroke-width="2"/>')
    svg.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="#333" stroke-width="2"/>')

    # Grid + ticks X
    for d in range(d_min, d_max + 1):
        x = x_of(float(d))
        svg.append(f'<line x1="{x:.2f}" y1="{margin_top}" x2="{x:.2f}" y2="{y0}" stroke="#e8e8e8" stroke-width="1"/>')
        svg.append(f'<text x="{x:.2f}" y="{y0 + 22}" text-anchor="middle" font-family="monospace" font-size="12" fill="#444">{d}</text>')

    # Grid + ticks Y
    steps = 8
    for i in range(steps + 1):
        frac = i / steps
        log_v = y_min + frac * (y_max - y_min)
        y = y_of(log_v)
        svg.append(f'<line x1="{x0}" y1="{y:.2f}" x2="{x1}" y2="{y:.2f}" stroke="#f1f1f1" stroke-width="1"/>')
        svg.append(
            f'<text x="{x0 - 8}" y="{y + 4:.2f}" text-anchor="end" font-family="monospace" font-size="11" fill="#444">{log_v:.2f}</text>'
        )

    # Series lines
    for idx, series in enumerate(data):
        color = colors[idx % len(colors)]
        poly = " ".join(f"{x_of(pt['d']):.2f},{y_of(pt['log10_H']):.2f}" for pt in series.points)
        svg.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for pt in series.points:
            svg.append(
                f'<circle cx="{x_of(pt["d"]):.2f}" cy="{y_of(pt["log10_H"]):.2f}" r="2.2" fill="{color}"/>'
            )

    # Labels
    svg.append(
        f'<text x="{margin_left + plot_w / 2:.2f}" y="{height - 24}" text-anchor="middle" font-family="monospace" font-size="14" fill="#222">d (hyperbolic distance index)</text>'
    )
    svg.append(
        f'<text transform="translate(20 {margin_top + plot_h / 2:.2f}) rotate(-90)" text-anchor="middle" font-family="monospace" font-size="14" fill="#222">log10(H(d,R))</text>'
    )

    # Legend
    legend_x = x1 - 170
    legend_y = margin_top + 14
    svg.append(f'<rect x="{legend_x - 10}" y="{legend_y - 18}" width="180" height="{26 * len(data) + 14}" fill="#fafafa" stroke="#ddd"/>')
    for idx, series in enumerate(data):
        color = colors[idx % len(colors)]
        y = legend_y + idx * 24
        svg.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 26}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        svg.append(
            f'<text x="{legend_x + 34}" y="{y + 4}" font-family="monospace" font-size="12" fill="#333">R = {series.R:.4g}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


def main() -> int:
    args = parse_args()
    r_values = parse_r_values(args.r_values)
    data = build_series(r_values, args.d_min, args.d_max)

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.figure_name
    csv_path = output_dir / f"{stem}.csv"
    svg_path = output_dir / f"{stem}.svg"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    write_csv(csv_path, data)
    svg = build_svg(data, args.d_min, args.d_max)
    svg_path.write_text(svg, encoding="utf-8")

    sample_points = {
        f"R={series.R:.4g}": {
            "d=6": harmonic_security_scaling(6, series.R),
            "d=10": harmonic_security_scaling(10, series.R),
        }
        for series in data
    }

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "formula": "H(d,R)=R^(d^2)",
        "domain": {"d_min": args.d_min, "d_max": args.d_max, "R_values": r_values},
        "sample_points": sample_points,
        "artifacts": {
            "csv": str(csv_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "svg": str(svg_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        },
    }
    write_json(json_path, payload)

    md = [
        "# Figure 1 - Harmonic Wall Scaling",
        "",
        f"- Formula: `H(d,R)=R^(d^2)`",
        f"- Domain: `d={args.d_min}..{args.d_max}`, `R={','.join(f'{r:.4g}' for r in r_values)}`",
        f"- Data: `{csv_path.relative_to(REPO_ROOT).as_posix()}`",
        f"- Figure: `{svg_path.relative_to(REPO_ROOT).as_posix()}`",
        "",
        "## Sample values",
    ]
    for key, values in sample_points.items():
        md.append(f"- `{key}`: d=6 -> `{values['d=6']:.8g}`, d=10 -> `{values['d=10']:.8g}`")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "csv": str(csv_path),
                "svg": str(svg_path),
                "json": str(json_path),
                "markdown": str(md_path),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
