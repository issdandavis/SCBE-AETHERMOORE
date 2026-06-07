"""Render prime alphabet circuits as color panels.

Each color is a behavior-derived symbol from ``prime_alphabet_circuit_probe``.
The SVG panels are for inspection: they make modular bands, gap texture, and
rotation effects visible without changing the underlying null-tested circuit.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

try:
    from prime_alphabet_circuit_probe import (
        ALPHABET,
        ALPHABET_SIZE,
        CIRCUIT_SIZE,
        ENCODERS,
        apply_rotating_circuit,
        quantile_buckets,
    )
    from run_prime_calibration_targeting_probe import simple_sieve
except ModuleNotFoundError:  # pragma: no cover - package import path for tests
    from scripts.research.prime_alphabet_circuit_probe import (
        ALPHABET,
        ALPHABET_SIZE,
        CIRCUIT_SIZE,
        ENCODERS,
        apply_rotating_circuit,
        quantile_buckets,
    )
    from scripts.research.run_prime_calibration_targeting_probe import simple_sieve


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "prime_color_circuit"


@dataclass(frozen=True)
class ColorPanel:
    encoding: str
    mode: str
    circuit_count: int
    symbol_count: int
    svg_path: str


def float_gap_ratio(primes: list[int]) -> list[int]:
    values = [
        (next_prime - prime) / max(math.log(prime), 1.0)
        for prime, next_prime in zip(primes, primes[1:])
    ]
    return quantile_buckets(values)


def float_log_step(primes: list[int]) -> list[int]:
    values = [
        math.log(next_prime / prime) for prime, next_prime in zip(primes, primes[1:])
    ]
    return quantile_buckets(values)


def float_ratio_curvature(primes: list[int]) -> list[int]:
    values = []
    for left, middle, right in zip(primes, primes[1:], primes[2:]):
        values.append(math.log(right / middle) - math.log(middle / left))
    return quantile_buckets(values)


def float_gap_acceleration(primes: list[int]) -> list[int]:
    values = []
    for left, middle, right in zip(primes, primes[1:], primes[2:]):
        values.append((right - middle) - (middle - left))
    return quantile_buckets(values)


COLOR_ENCODERS: dict[str, Callable[[list[int]], list[int]]] = {
    **ENCODERS,
    "float_gap_ratio": float_gap_ratio,
    "float_log_step": float_log_step,
    "float_ratio_curvature": float_ratio_curvature,
    "float_gap_acceleration": float_gap_acceleration,
}


def color_palette(size: int = ALPHABET_SIZE) -> list[str]:
    """Return a stable high-contrast palette as hex colors."""
    colors: list[str] = []
    for index in range(size):
        # The offset prevents A/Z-neighbor colors from being too similar.
        hue = ((index * 11) % size) / size
        red, green, blue = colorsys.hsv_to_rgb(hue, 0.78, 0.92)
        colors.append(
            f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"
        )
    return colors


def trim_to_circuits(symbols: list[int], circuits: int) -> list[int]:
    if circuits <= 0:
        raise ValueError("circuits must be positive")
    return symbols[: circuits * CIRCUIT_SIZE]


def render_svg(
    symbols: list[int],
    title: str,
    path: Path,
    cell_size: int = 7,
    columns: int = ALPHABET_SIZE,
) -> None:
    if cell_size <= 0:
        raise ValueError("cell_size must be positive")
    if columns <= 0:
        raise ValueError("columns must be positive")
    palette = color_palette()
    rows = (len(symbols) + columns - 1) // columns
    legend_height = 46
    label_height = 24
    width = columns * cell_size
    height = rows * cell_size + legend_height + label_height
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#111318"/>',
        f'<text x="4" y="16" fill="#f2f4f8" font-family="Consolas, monospace" font-size="12">{title}</text>',
    ]
    y_offset = label_height
    for index, symbol in enumerate(symbols):
        x = (index % columns) * cell_size
        y = (index // columns) * cell_size + y_offset
        fill = palette[symbol % len(palette)]
        lines.append(
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{fill}"/>'
        )

    legend_y = rows * cell_size + y_offset + 10
    swatch = max(6, min(12, cell_size + 2))
    for index, letter in enumerate(ALPHABET):
        x = index * (width / ALPHABET_SIZE)
        lines.append(
            f'<rect x="{x:.2f}" y="{legend_y}" width="{swatch}" height="{swatch}" fill="{palette[index]}"/>'
        )
        lines.append(
            f'<text x="{x:.2f}" y="{legend_y + swatch + 10}" fill="#cfd6e6" '
            f'font-family="Consolas, monospace" font-size="8">{letter}</text>'
        )
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def build_panels(
    limit: int,
    max_primes: int,
    circuits: int,
    out_dir: Path,
    encodings: tuple[str, ...] | None = None,
) -> dict[str, object]:
    primes = simple_sieve(limit)
    if max_primes > 0:
        primes = primes[:max_primes]
    if len(primes) < CIRCUIT_SIZE:
        raise ValueError(f"need at least {CIRCUIT_SIZE} primes for one full circuit")

    selected = encodings or tuple(COLOR_ENCODERS)
    panel_dir = out_dir / "panels"
    panel_dir.mkdir(parents=True, exist_ok=True)
    panels: list[ColorPanel] = []
    for encoding in selected:
        if encoding not in COLOR_ENCODERS:
            raise ValueError(f"unknown encoding: {encoding}")
        base_symbols = COLOR_ENCODERS[encoding](primes)
        if len(base_symbols) < circuits * CIRCUIT_SIZE:
            raise ValueError(
                f"encoding {encoding} has only {len(base_symbols)} symbols, need {circuits * CIRCUIT_SIZE}"
            )
        for mode in ("direct", "rotating"):
            symbols = trim_to_circuits(base_symbols, circuits)
            if mode == "rotating":
                symbols = apply_rotating_circuit(symbols)
            filename = f"{encoding}_{mode}.svg"
            svg_path = panel_dir / filename
            render_svg(symbols, f"{encoding} / {mode} / {circuits} circuits", svg_path)
            panels.append(
                ColorPanel(
                    encoding=encoding,
                    mode=mode,
                    circuit_count=circuits,
                    symbol_count=len(symbols),
                    svg_path=str(svg_path.relative_to(out_dir)),
                )
            )

    return {
        "schema_version": "prime_color_circuit_v1",
        "config": {
            "limit": limit,
            "prime_count": len(primes),
            "circuits": circuits,
            "symbols_per_circuit": CIRCUIT_SIZE,
            "alphabet": "".join(ALPHABET),
        },
        "panels": [asdict(panel) for panel in panels],
    }


def write_markdown(report: dict[str, object], path: Path) -> None:
    config = report["config"]  # type: ignore[index]
    panels = report["panels"]  # type: ignore[index]
    lines = [
        "# Prime Color Circuit",
        "",
        "Colorized behavior-derived prime alphabet circuits.",
        "",
        "## Config",
        "",
        f"- limit: `{config['limit']}`",
        f"- prime_count: `{config['prime_count']}`",
        f"- circuits_rendered: `{config['circuits']}`",
        "",
        "## Panels",
        "",
        "| Encoding | Mode | SVG |",
        "| --- | --- | --- |",
    ]
    for panel in panels:  # type: ignore[assignment]
        lines.append(
            f"| {panel['encoding']} | {panel['mode']} | [{panel['svg_path']}]({panel['svg_path']}) |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- Color is a visualization layer over the same behavior symbols used by the alphabet probe.",
            "- Strong bands usually mean known modular/wheel structure, not a new targeter.",
            "- Broken texture or repeated islands are candidates for later null-tested compression, not proof by eye.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1_000_000)
    parser.add_argument("--max-primes", type=int, default=50_000)
    parser.add_argument("--circuits", type=int, default=8)
    parser.add_argument(
        "--encodings",
        default=(
            "value_mod26,gap_mod26,wheel210_bucket26,normalized_gap_bucket,ratio_curvature_bucket,"
            "float_gap_ratio,float_log_step,float_ratio_curvature,float_gap_acceleration"
        ),
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    encodings = tuple(
        part.strip() for part in args.encodings.split(",") if part.strip()
    )
    report = build_panels(
        args.limit, args.max_primes, args.circuits, args.out_dir, encodings
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "latest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(report, args.out_dir / "LATEST.md")
    print(f"Wrote {args.out_dir / 'LATEST.md'}")


if __name__ == "__main__":
    main()
