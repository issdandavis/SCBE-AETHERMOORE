"""Run controlled storage-compaction sweeps for SCBE storage surfaces.

This lab is intentionally narrow: it changes one storage knob at a time and
captures the resulting allocation density so we can see whether compaction
improves before rewriting a subsystem.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from hydra.octree_sphere_grid import HyperbolicLattice25D
from src.crypto.octree import HyperbolicOctree

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "system_audit" / "storage_compaction_lab"
TONGUES = ("KO", "AV", "RU", "CA", "UM", "DR")
REALMS = ("light_realm", "shadow_realm", "path")


@dataclass(frozen=True)
class OctreeSample:
    coords: tuple[float, float, float]
    realm: str


@dataclass(frozen=True)
class BundleSample:
    x: float
    y: float
    phase_rad: float
    tongue: str
    authority: str
    intent_vector: tuple[float, float, float]
    intent_label: str
    wavelength_nm: float


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _clamp_ball(x: float, y: float, z: float, limit: float = 0.94) -> tuple[float, float, float]:
    radius = math.sqrt(x * x + y * y + z * z)
    if radius <= limit:
        return (x, y, z)
    scale = limit / max(radius, 1e-9)
    return (x * scale, y * scale, z * scale)


def _intent_vector(index: int) -> tuple[float, float, float]:
    presets = (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
        (1.0, 1.0, 0.0),
        (1.0, 0.0, 1.0),
        (0.0, 1.0, 1.0),
    )
    return presets[index % len(presets)]


def build_octree_workload(
    seed: int = 7,
    core_points: int = 40,
    ring_points: int = 28,
    edge_points: int = 20,
) -> list[OctreeSample]:
    """Create a deterministic 3-zone workload for sparse octree sweeps."""
    rng = random.Random(seed)
    samples: list[OctreeSample] = []

    for idx in range(core_points):
        x = rng.uniform(-0.18, 0.18)
        y = rng.uniform(-0.18, 0.18)
        z = rng.uniform(-0.18, 0.18)
        samples.append(OctreeSample(_clamp_ball(x, y, z, limit=0.55), REALMS[idx % len(REALMS)]))

    for idx in range(ring_points):
        theta = (2.0 * math.pi * idx) / max(1, ring_points)
        r = 0.42 + rng.uniform(-0.08, 0.08)
        z = rng.uniform(-0.24, 0.24)
        samples.append(
            OctreeSample(
                _clamp_ball(r * math.cos(theta), r * math.sin(theta), z, limit=0.78),
                REALMS[(idx + 1) % len(REALMS)],
            )
        )

    for idx in range(edge_points):
        theta = rng.uniform(0.0, 2.0 * math.pi)
        phi = rng.uniform(-math.pi / 3.0, math.pi / 3.0)
        r = 0.82 + rng.uniform(-0.04, 0.04)
        x = r * math.cos(theta) * math.cos(phi)
        y = r * math.sin(theta) * math.cos(phi)
        z = r * math.sin(phi)
        samples.append(OctreeSample(_clamp_ball(x, y, z, limit=0.93), REALMS[(idx + 2) % len(REALMS)]))

    return samples


def build_lattice_workload(
    seed: int = 11,
    cluster_count: int = 4,
    bundles_per_cluster: int = 18,
) -> list[BundleSample]:
    """Create a deterministic clustered bundle workload for the lattice hybrid."""
    rng = random.Random(seed)
    centers = [
        (0.0, 0.0),
        (0.35, 0.2),
        (-0.4, 0.35),
        (0.55, -0.32),
    ]
    authorities = ("public", "sealed", "pilot", "private")
    samples: list[BundleSample] = []

    for cluster_idx in range(cluster_count):
        cx, cy = centers[cluster_idx % len(centers)]
        for bundle_idx in range(bundles_per_cluster):
            jitter = 0.045 if cluster_idx < 2 else 0.08
            x = max(-0.94, min(0.94, cx + rng.uniform(-jitter, jitter)))
            y = max(-0.94, min(0.94, cy + rng.uniform(-jitter, jitter)))
            phase = ((bundle_idx / max(1, bundles_per_cluster)) * 2.0 * math.pi) + cluster_idx * 0.35
            samples.append(
                BundleSample(
                    x=x,
                    y=y,
                    phase_rad=phase,
                    tongue=TONGUES[(cluster_idx + bundle_idx) % len(TONGUES)],
                    authority=authorities[cluster_idx % len(authorities)],
                    intent_vector=_intent_vector(cluster_idx + bundle_idx),
                    intent_label=f"cluster_{cluster_idx}_bundle_{bundle_idx}",
                    wavelength_nm=430.0 + ((cluster_idx * 35.0) + bundle_idx * 3.0),
                )
            )

    return samples


def evaluate_hyperbolic_octree(
    *,
    max_depth: int,
    grid_size: int = 64,
    seed: int = 7,
) -> dict[str, Any]:
    """Evaluate sparse octree packing for a fixed workload."""
    octree = HyperbolicOctree(grid_size=grid_size, max_depth=max_depth)
    for sample in build_octree_workload(seed=seed):
        octree.insert(np.array(sample.coords, dtype=float), sample.realm)

    stats = octree.stats()
    occupied = max(1, stats["occupied_voxels"])
    storage_units = max(1, stats["node_count"] + stats["leaf_count"])
    stats["points_per_occupied_voxel"] = round(stats["point_count"] / occupied, 6)
    stats["storage_units"] = storage_units
    stats["compaction_score"] = round(stats["point_count"] / storage_units, 6)
    return stats


def evaluate_lattice25d(
    *,
    cell_size: float = 0.25,
    max_depth: int = 6,
    index_mode: str = "hybrid",
    quadtree_capacity: int = 8,
    quadtree_z_variance: float = 0.01,
    quadtree_query_extent: float = 0.35,
    seed: int = 11,
) -> dict[str, Any]:
    """Evaluate the lattice/octree hybrid using deterministic clustered bundles."""
    lattice = HyperbolicLattice25D(
        cell_size=cell_size,
        max_depth=max_depth,
        index_mode=index_mode,
        quadtree_capacity=quadtree_capacity,
        quadtree_z_variance=quadtree_z_variance,
        quadtree_query_extent=quadtree_query_extent,
    )
    for idx, sample in enumerate(build_lattice_workload(seed=seed)):
        lattice.insert_bundle(
            x=sample.x,
            y=sample.y,
            phase_rad=sample.phase_rad,
            tongue=sample.tongue,
            authority=sample.authority,
            intent_vector=list(sample.intent_vector),
            intent_label=sample.intent_label,
            bundle_id=f"lab_bundle_{idx:03d}",
            wavelength_nm=sample.wavelength_nm,
        )

    stats = lattice.stats()
    occupied_cells = max(1, stats["occupied_cells"])
    quadtree_stats = stats.get("quadtree", {})
    storage_units = stats["occupied_cells"] + stats["octree_voxel_count"] + quadtree_stats.get("node_count", 0)
    stats["bundles_per_cell"] = round(stats["bundle_count"] / occupied_cells, 6)
    if quadtree_stats:
        leaf_count = max(1, quadtree_stats.get("leaf_count", 0))
        stats["bundles_per_quadtree_leaf"] = round(stats["bundle_count"] / leaf_count, 6)
    stats["storage_units"] = max(1, storage_units)
    stats["compaction_score"] = round(stats["bundle_count"] / max(1, storage_units), 6)
    return stats


def sweep_storage_knob(
    *,
    system: str,
    knob: str,
    values: Sequence[str | float | int],
    seed: int,
    base_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sweep one knob and rank configurations by compaction score."""
    config = dict(base_config or {})
    cards: list[dict[str, Any]] = []

    for raw_value in values:
        trial = dict(config)
        trial[knob] = raw_value
        if system == "hyperbolic-octree":
            metrics = evaluate_hyperbolic_octree(
                max_depth=int(trial.get("max_depth", raw_value)),
                grid_size=int(trial.get("grid_size", 64)),
                seed=seed,
            )
            density = metrics["points_per_occupied_voxel"]
            overload = metrics["leaf_count"]
            color = "amber"
        elif system == "lattice25d":
            metrics = evaluate_lattice25d(
                cell_size=float(trial.get("cell_size", 0.25)),
                max_depth=int(trial.get("max_depth", 6)),
                index_mode=str(trial.get("index_mode", "hybrid")),
                quadtree_capacity=int(trial.get("quadtree_capacity", 8)),
                quadtree_z_variance=float(trial.get("quadtree_z_variance", 0.01)),
                quadtree_query_extent=float(trial.get("quadtree_query_extent", 0.35)),
                seed=seed,
            )
            density = metrics["bundles_per_cell"]
            overload = metrics["max_overlap"]
            color = "indigo"
        else:
            raise ValueError(f"Unsupported system: {system}")

        cards.append(
            {
                "suit": "storage",
                "color": color,
                "system": system,
                "knob": knob,
                "value": raw_value,
                "compaction_score": metrics["compaction_score"],
                "density": density,
                "overload": overload,
                "metrics": metrics,
            }
        )

    ranked = sorted(cards, key=lambda card: (card["compaction_score"], card["density"], -card["overload"]), reverse=True)
    for idx, card in enumerate(ranked, start=1):
        card["rank"] = idx
        if card["rank"] == 1:
            card["verdict"] = "best-current-tradeoff"
        elif card["overload"] > ranked[0]["overload"]:
            card["verdict"] = "denser-but-hotter"
        else:
            card["verdict"] = "safer-but-looser"

    return {
        "experiment": "storage_compaction_lab",
        "timestamp_utc": _timestamp(),
        "system": system,
        "knob": knob,
        "seed": seed,
        "cards": ranked,
        "best_card": ranked[0] if ranked else None,
    }


def _default_values(system: str, knob: str) -> list[float | int]:
    if system == "hyperbolic-octree" and knob == "max_depth":
        return [3, 4, 5, 6]
    if system == "lattice25d" and knob == "cell_size":
        return [0.2, 0.25, 0.333333, 0.5]
    if system == "lattice25d" and knob == "quadtree_capacity":
        return [2, 4, 8, 12]
    if system == "lattice25d" and knob == "quadtree_z_variance":
        return [0.0, 0.01, 0.05, 0.1]
    raise ValueError(f"No default sweep values for {system}:{knob}")


def _coerce_values(raw_values: Iterable[str], system: str, knob: str) -> list[float | int]:
    values = [value.strip() for value in raw_values if value.strip()]
    if not values:
        return _default_values(system, knob)

    if knob in {"max_depth", "quadtree_capacity", "grid_size"}:
        return [int(value) for value in values]
    return [float(value) for value in values]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a bounded storage compaction sweep for SCBE storage surfaces.")
    parser.add_argument(
        "--system",
        choices=("hyperbolic-octree", "lattice25d"),
        default="hyperbolic-octree",
        help="Storage surface to evaluate.",
    )
    parser.add_argument("--knob", default="max_depth", help="One storage variable to sweep.")
    parser.add_argument(
        "--values",
        default="",
        help="Comma-separated list of values for the chosen knob. Uses defaults when omitted.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Deterministic seed for workload generation.")
    parser.add_argument("--output-json", default="", help="Optional explicit artifact path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    values = _coerce_values(args.values.split(","), args.system, args.knob)
    base_config: dict[str, Any]
    if args.system == "lattice25d":
        base_config = {"index_mode": "hybrid"}
        if args.knob == "max_depth":
            parser.error("lattice25d sweeps are intended for cell_size, quadtree_capacity, or quadtree_z_variance")
    else:
        base_config = {}

    report = sweep_storage_knob(
        system=args.system,
        knob=args.knob,
        values=values,
        seed=args.seed,
        base_config=base_config,
    )

    out_path = Path(args.output_json) if args.output_json else ARTIFACT_ROOT / f"{report['timestamp_utc']}-{args.system}-{args.knob}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
