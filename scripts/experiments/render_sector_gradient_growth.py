"""Render and measure the bounded sector-gradient node-growth mechanics."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.algebraic_radial_token_table import (
    AlgebraicRadialTokenTable,
    RadialTableSpec,
)
from python.scbe.sector_gradient_growth import build_sector_gradient_mesh


def _fixture_opcodes(cell_count: int, sector_count: int) -> tuple[int, ...]:
    cells_per_sector = cell_count // sector_count
    values: list[int] = []
    for sector in range(sector_count):
        if sector % 2 == 0:
            values.extend((sector * 4 + ordinal * 7) % 64 for ordinal in range(cells_per_sector))
        else:
            low = (sector * 7) % 32
            high = 63 - low
            values.extend(low if ordinal < cells_per_sector // 2 else high for ordinal in range(cells_per_sector))
    return tuple(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--seed", type=int, default=20261110)
    args = parser.parse_args()

    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)

    spec = RadialTableSpec(
        cell_count=64,
        sector_count=8,
        dimensions=8,
        depth_count=4,
        neighbor_count=3,
        portal_count=1,
        seed=args.seed,
    )
    opcodes = _fixture_opcodes(spec.cell_count, spec.sector_count)
    table = AlgebraicRadialTokenTable(spec)
    mesh = build_sector_gradient_mesh(
        table,
        opcodes,
        max_depth=3,
        max_gradient_stops=3,
        split_error_threshold=16.0,
        min_samples_to_split=4,
    )

    shuffled = list(opcodes)
    random.Random(args.seed).shuffle(shuffled)
    shuffled_mesh = build_sector_gradient_mesh(
        table,
        shuffled,
        max_depth=3,
        max_gradient_stops=3,
        split_error_threshold=16.0,
        min_samples_to_split=4,
    )

    image_path = args.output / "sector-gradient-growth.png"
    background = (1, 2, 3)
    png_sha256 = mesh.save_png(image_path, size=args.size, background=background)
    image = mesh.render(size=args.size, background=background)
    unique_rendered_colors = len(set(image.get_flattened_data()) - {background})

    receipt = mesh.receipt()
    (args.output / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    metrics = {
        "schema": "scbe.sector-gradient-growth-experiment.v1",
        "claim_boundary": receipt["claim_boundary"],
        "seed": args.seed,
        "image_size": args.size,
        "png_sha256": png_sha256,
        "unique_source_colors": len(set(mesh.colors)),
        "unique_rendered_colors": unique_rendered_colors,
        "candidate": asdict(mesh.metrics),
        "shuffled_binding_control": asdict(shuffled_mesh.metrics),
        "checks": {
            "growth_observed": mesh.metrics.grown_node_count > 0,
            "fixed_gradient_not_worse_than_flat": mesh.metrics.fixed_gradient_mse <= mesh.metrics.flat_mse,
            "adaptive_not_worse_than_fixed": mesh.metrics.adaptive_gradient_mse <= mesh.metrics.fixed_gradient_mse,
            "pixel_interpolation_added_shades": unique_rendered_colors > len(set(mesh.colors)),
        },
    }
    (args.output / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2, sort_keys=True, allow_nan=False))
    return 0 if all(metrics["checks"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
