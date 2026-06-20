#!/usr/bin/env python3
"""Render the GeoSeed orbital model as a self-contained HTML/SVG report."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.geoseed.orbital_model import orbital_summary  # noqa: E402


def _polyline(points: list[dict[str, float]], width: int, height: int, max_density: float) -> str:
    if not points:
        return ""
    max_rho = max(point["rho"] for point in points) or 1.0
    coords: list[str] = []
    for point in points:
        x = 28 + (point["rho"] / max_rho) * (width - 56)
        y = height - 24 - (point["density"] / max_density) * (height - 52)
        coords.append(f"{x:.2f},{y:.2f}")
    return " ".join(coords)


def build_html() -> str:
    summary = orbital_summary(include_profiles=True)
    orbitals = summary["orbitals"]
    profiles = summary["density_profiles"]
    max_density = max(point["density"] for rows in profiles.values() for point in rows) or 1.0
    width = 760
    row_height = 78
    chart_height = row_height * len(orbitals)

    colors = {
        "KO": "#2563eb",
        "AV": "#059669",
        "RU": "#d97706",
        "CA": "#dc2626",
        "UM": "#7c3aed",
        "DR": "#0891b2",
    }

    rows: list[str] = []
    for index, orbital in enumerate(orbitals):
        abbr = orbital["abbr"]
        y_base = index * row_height
        line = _polyline(profiles[abbr], width, row_height, max_density)
        label = f"{abbr} / {orbital['orbital_type']}-shell / " f"r={orbital['poincare_r']} / m={orbital['m_states']}"
        rows.append(
            "\n".join(
                [
                    f'<g transform="translate(0,{y_base})">',
                    f'<text x="28" y="18" class="label">{html.escape(label)}</text>',
                    f'<line x1="28" y1="{row_height - 24}" x2="{width - 28}" y2="{row_height - 24}" class="axis" />',
                    f'<polyline points="{line}" fill="none" stroke="{colors[abbr]}" stroke-width="2.5" />',
                    "</g>",
                ]
            )
        )

    table_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(row['abbr'])}</td>"
        f"<td>{html.escape(row['tongue'])}</td>"
        f"<td>{html.escape(row['orbital_type'])}</td>"
        f"<td>{row['phi_weight']}</td>"
        f"<td>{row['poincare_r']}</td>"
        f"<td>{row['hyperbolic_rho']}</td>"
        f"<td>{row['m_states']}</td>"
        "</tr>"
        for row in orbitals
    )

    gaps = "\n".join(
        f"<li>{gap['from']} -> {gap['to']}: d={gap['geodesic_distance']}, ratio={gap['phi_ratio']}</li>"
        for gap in summary["inter_shell_gaps"]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>GeoSeed Orbital Model</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #172033; background: #fbfaf7; }}
    h1 {{ margin-bottom: 4px; }}
    .scope {{ max-width: 860px; color: #465264; }}
    svg {{ width: 100%; max-width: {width}px; background: #fff; border: 1px solid #d7dce2; border-radius: 8px; }}
    .axis {{ stroke: #ccd3dd; stroke-width: 1; }}
    .label {{ fill: #263244; font-size: 13px; font-weight: 650; }}
    table {{ border-collapse: collapse; margin-top: 18px; background: #fff; }}
    th, td {{ border: 1px solid #d7dce2; padding: 7px 10px; text-align: left; }}
    th {{ background: #eef2f6; }}
    code {{ background: #eef2f6; padding: 1px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>GeoSeed Orbital Model</h1>
  <p class="scope">{html.escape(summary["model_scope"])}</p>
  <p>
    Uniform hyperbolic gap: <code>{summary["uniform_gap"]["hyperbolic_distance"]}</code>.
    CA checkpoint: <code>r={summary["golden_ratio_checkpoint"]["poincare_r"]}=1/phi</code>.
    Total m-states: <code>{summary["total_m_states"]}</code>.
  </p>
  <h2>Density Profiles</h2>
  <svg viewBox="0 0 {width} {chart_height}" role="img" aria-label="GeoSeed radial density profiles">
    {''.join(rows)}
  </svg>
  <h2>Shell Table</h2>
  <table>
    <thead>
      <tr><th>Abbr</th><th>Tongue</th><th>Orbital</th><th>Phi weight</th><th>r</th><th>rho</th><th>m-states</th></tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>
  <h2>Inter-Shell Gaps</h2>
  <ul>{gaps}</ul>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "artifacts" / "geoseed" / "orbital_model.html"),
        help="Output HTML path",
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
