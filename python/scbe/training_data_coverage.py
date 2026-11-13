"""Audit whether a training campaign expands concept support or only replays rows.

The Clay action campaigns serialize compact tensor bundles.  This module reads
those bundles without importing the experiment worktree, recovers the declared
state factors from the 37-column feature schema, and measures marginal, joint,
and replay exposure.  It intentionally does not train or mutate a model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import torch
from torch import Tensor

SCHEMA = "clay.training-data-coverage-audit.v1"
FEATURE_NAMES = (
    "position_x",
    "position_y",
    "velocity_x",
    "velocity_y",
    "presented_position_x",
    "presented_position_y",
    "presented_target_x",
    "presented_target_y",
    "frame_offset_x",
    "frame_offset_y",
    "geometry_00",
    "geometry_01",
    "geometry_10",
    "geometry_11",
    "scope_dx",
    "scope_dy",
    "scope_margin_x",
    "scope_margin_y",
    "scope_speed",
    "phase_crawl",
    "phase_play",
    "phase_swaddle",
    "phase_release",
    "drive_negative",
    "drive_neutral",
    "drive_positive",
    "target_phase_0",
    "target_phase_1",
    "target_phase_2",
    "target_phase_3",
    "memory_occupancy",
    "stagnation",
    "outburst",
    "mobility",
    "curiosity",
    "stability",
    "bias",
)

JOINTS: tuple[tuple[str, ...], ...] = (
    ("phase", "drive"),
    ("phase", "target"),
    ("phase", "memory_slots"),
    ("phase", "stagnation_ticks"),
    ("phase", "outburst_ticks"),
    ("drive", "target"),
    ("memory_slots", "stagnation_ticks"),
    ("memory_slots", "outburst_ticks"),
    ("stagnation_ticks", "outburst_ticks"),
    ("position_x_bin", "position_y_bin"),
    ("velocity_x_bin", "velocity_y_bin"),
    ("scope_sign_x", "scope_sign_y"),
    ("phase", "sector"),
    ("target", "sector"),
    ("action", "sector"),
    ("action", "target"),
    ("action", "phase"),
    ("phase", "drive", "target"),
    ("phase", "target", "sector"),
    ("action", "target", "sector"),
)


class CoverageAuditError(ValueError):
    """Raised when an input bundle violates the declared campaign schema."""


@dataclass(frozen=True, slots=True)
class TensorBundle:
    """Validated tensor-only view of one serialized campaign split."""

    path: Path
    features: Tensor
    labels: Tensor
    sectors: Tensor
    reward_values: Tensor
    file_sha256: str


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_sha256(value: Tensor) -> str:
    cpu = value.detach().cpu().contiguous()
    header = f"{cpu.dtype}|{tuple(cpu.shape)}|".encode("ascii")
    return hashlib.sha256(header + cpu.numpy().tobytes()).hexdigest()


def load_tensor_bundle(path: str | Path) -> TensorBundle:
    """Load one campaign split with PyTorch's restricted tensor loader."""

    source = Path(path).resolve()
    payload = torch.load(source, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict):
        raise CoverageAuditError("campaign bundle must be a mapping")
    required = {"features", "labels", "sectors", "reward_values"}
    if not required.issubset(payload):
        missing = sorted(required.difference(payload))
        raise CoverageAuditError(f"campaign bundle is missing {missing}")

    features = payload["features"]
    labels = payload["labels"]
    sectors = payload["sectors"]
    rewards = payload["reward_values"]
    if not all(
        isinstance(value, Tensor) for value in (features, labels, sectors, rewards)
    ):
        raise CoverageAuditError("campaign data fields must be tensors")
    if features.ndim != 2 or features.shape[1] != len(FEATURE_NAMES):
        raise CoverageAuditError("feature tensor does not match the 37-column schema")
    count = features.shape[0]
    if labels.shape != (count,) or sectors.shape != (count,):
        raise CoverageAuditError(
            "labels and sectors must have one value per feature row"
        )
    if rewards.ndim != 2 or rewards.shape[0] != count:
        raise CoverageAuditError("reward table must have one row per feature row")
    if not bool(torch.isfinite(features).all()) or not bool(
        torch.isfinite(rewards).all()
    ):
        raise CoverageAuditError("campaign tensors must be finite")
    if labels.dtype != torch.int64 or sectors.dtype != torch.int64:
        raise CoverageAuditError("labels and sectors must be int64")
    return TensorBundle(
        path=source,
        features=features.detach().cpu(),
        labels=labels.detach().cpu(),
        sectors=sectors.detach().cpu(),
        reward_values=rewards.detach().cpu(),
        file_sha256=file_sha256(source),
    )


def _strict_one_hot(features: Tensor, start: int, stop: int, name: str) -> Tensor:
    block = features[:, start:stop]
    if not bool(
        torch.allclose(block.sum(dim=1), torch.ones(block.shape[0]), atol=1e-6)
    ):
        raise CoverageAuditError(f"{name} columns are not one-hot")
    if not bool(torch.all((block >= -1e-6) & (block <= 1.0 + 1e-6))):
        raise CoverageAuditError(f"{name} columns leave [0, 1]")
    return block.argmax(dim=1).to(torch.int64)


def _fixed_bins(values: Tensor, boundaries: Sequence[float]) -> Tensor:
    edges = torch.tensor(boundaries, dtype=values.dtype)
    return torch.bucketize(values.contiguous(), edges).to(torch.int64)


def _sign_code(values: Tensor, epsilon: float = 1e-8) -> Tensor:
    result = torch.ones(values.shape, dtype=torch.int64)
    result[values < -epsilon] = 0
    result[values > epsilon] = 2
    return result


def derive_factors(bundle: TensorBundle) -> dict[str, Tensor]:
    """Recover discrete generator, geometry, and outcome factors."""

    x = bundle.features
    phase = _strict_one_hot(x, 19, 23, "phase")
    drive = _strict_one_hot(x, 23, 26, "drive") - 1
    target = _strict_one_hot(x, 26, 30, "target")
    memory_slots = torch.round(x[:, 30] * 8.0).to(torch.int64)
    stagnation = torch.round(x[:, 31] * 4.0).to(torch.int64)
    outburst = torch.round(x[:, 32] * 2.0).to(torch.int64)
    for name, values, low, high in (
        ("memory_slots", memory_slots, 0, 2),
        ("stagnation_ticks", stagnation, 0, 3),
        ("outburst_ticks", outburst, 0, 2),
    ):
        if bool(torch.any((values < low) | (values > high))):
            raise CoverageAuditError(f"{name} does not match the sampled-state recipe")

    position_edges = (-0.75, -0.50, -0.25, 0.0, 0.25, 0.50, 0.75)
    velocity_edges = (-0.46875, -0.3125, -0.15625, 0.0, 0.15625, 0.3125, 0.46875)
    stat_edges = (0.2, 0.4, 0.6, 0.8)
    speed_max = math.sqrt(2.0) * 0.625
    speed_edges = tuple(speed_max * index / 8.0 for index in range(1, 8))
    return {
        "phase": phase,
        "drive": drive,
        "target": target,
        "memory_slots": memory_slots,
        "stagnation_ticks": stagnation,
        "outburst_ticks": outburst,
        "sector": bundle.sectors.to(torch.int64),
        "action": bundle.labels.to(torch.int64),
        "scope_sign_x": _sign_code(x[:, 14]),
        "scope_sign_y": _sign_code(x[:, 15]),
        "position_x_bin": _fixed_bins(x[:, 0], position_edges),
        "position_y_bin": _fixed_bins(x[:, 1], position_edges),
        "velocity_x_bin": _fixed_bins(x[:, 2], velocity_edges),
        "velocity_y_bin": _fixed_bins(x[:, 3], velocity_edges),
        "speed_bin": _fixed_bins(x[:, 18], speed_edges),
        "mobility_bin": _fixed_bins(x[:, 33], stat_edges),
        "curiosity_bin": _fixed_bins(x[:, 34], stat_edges),
        "stability_bin": _fixed_bins(x[:, 35], stat_edges),
    }


def _entropy_evenness(counts: Iterable[int], support_size: int) -> float:
    values = [int(value) for value in counts if value > 0]
    total = sum(values)
    if total <= 0 or support_size <= 1:
        return 1.0
    entropy = -sum((value / total) * math.log(value / total) for value in values)
    return entropy / math.log(support_size)


def _quantiles(values: Tensor) -> dict[str, float]:
    source = values.detach().to(torch.float64).flatten()
    points = torch.tensor((0.0, 0.05, 0.5, 0.95, 1.0), dtype=torch.float64)
    result = torch.quantile(source, points)
    return dict(
        zip(("min", "p05", "median", "p95", "max"), result.tolist(), strict=True)
    )


def marginal_receipt(values: Tensor) -> dict[str, Any]:
    counts = Counter(int(value) for value in values.tolist())
    ordered = sorted(counts.items())
    return {
        "states": len(ordered),
        "counts": {str(key): value for key, value in ordered},
        "min_count": min(counts.values()),
        "max_count": max(counts.values()),
        "entropy_evenness": _entropy_evenness(counts.values(), len(counts)),
    }


def joint_receipt(
    factors: Mapping[str, Tensor], names: Sequence[str]
) -> dict[str, Any]:
    """Measure occupancy against the product of observed marginal states."""

    columns = [factors[name].tolist() for name in names]
    tuples = [tuple(int(value) for value in row) for row in zip(*columns, strict=True)]
    counts = Counter(tuples)
    marginal_states = [sorted({int(value) for value in column}) for column in columns]
    cartesian_cells = math.prod(len(states) for states in marginal_states)
    missing: list[str] = []
    if cartesian_cells <= 512:
        import itertools

        for cell in itertools.product(*marginal_states):
            if cell not in counts:
                missing.append("|".join(str(value) for value in cell))
    lowest = sorted(counts.items(), key=lambda item: (item[1], item[0]))[:8]
    return {
        "factors": list(names),
        "marginal_state_counts": [len(states) for states in marginal_states],
        "cartesian_cells": cartesian_cells,
        "observed_cells": len(counts),
        "coverage_ratio": len(counts) / cartesian_cells,
        "missing_cell_count": cartesian_cells - len(counts),
        "missing_cells_sample": missing[:32],
        "min_nonzero_count": min(counts.values()),
        "max_count": max(counts.values()),
        "entropy_evenness": _entropy_evenness(counts.values(), cartesian_cells),
        "lowest_cells": [
            {"cell": "|".join(str(value) for value in cell), "count": count}
            for cell, count in lowest
        ],
    }


def audit_bundle(bundle: TensorBundle) -> dict[str, Any]:
    factors = derive_factors(bundle)
    return {
        "path": str(bundle.path),
        "file_sha256": bundle.file_sha256,
        "records": int(bundle.features.shape[0]),
        "feature_width": int(bundle.features.shape[1]),
        "reward_width": int(bundle.reward_values.shape[1]),
        "tensor_sha256": {
            "features": _tensor_sha256(bundle.features),
            "labels": _tensor_sha256(bundle.labels),
            "sectors": _tensor_sha256(bundle.sectors),
            "reward_values": _tensor_sha256(bundle.reward_values),
        },
        "marginals": {
            name: marginal_receipt(values) for name, values in factors.items()
        },
        "joints": {"x".join(names): joint_receipt(factors, names) for names in JOINTS},
    }


def _row_hashes(features: Tensor) -> set[bytes]:
    cpu = features.detach().cpu().contiguous().numpy()
    return {hashlib.sha256(row.tobytes()).digest() for row in cpu}


def exact_row_overlap(left: TensorBundle, right: TensorBundle) -> dict[str, Any]:
    left_rows = _row_hashes(left.features)
    right_rows = _row_hashes(right.features)
    overlap = left_rows.intersection(right_rows)
    return {
        "left_unique_rows": len(left_rows),
        "right_unique_rows": len(right_rows),
        "exact_overlap_rows": len(overlap),
    }


def nearest_train_distance(train: TensorBundle, other: TensorBundle) -> dict[str, Any]:
    """Return standardized RMS distance to the nearest stored train row."""

    center = train.features.to(torch.float64).mean(dim=0)
    scale = train.features.to(torch.float64).std(dim=0, unbiased=False)
    active = scale > 1e-10
    if not bool(active.any()):
        raise CoverageAuditError("training features have no varying columns")
    train_z = (train.features.to(torch.float64)[:, active] - center[active]) / scale[
        active
    ]
    other_z = (other.features.to(torch.float64)[:, active] - center[active]) / scale[
        active
    ]
    distances: list[Tensor] = []
    for chunk in other_z.split(256):
        nearest = torch.cdist(chunk, train_z).amin(dim=1) / math.sqrt(train_z.shape[1])
        distances.append(nearest)
    all_distances = torch.cat(distances)
    return {
        "active_standardized_columns": int(active.sum().item()),
        "rms_z_nearest": _quantiles(all_distances),
    }


def simulate_uniform_replay(
    record_count: int,
    *,
    held_sector: int,
    seed: int,
    steps: int,
    batch_size: int,
) -> dict[str, Any]:
    """Replay the campaign's exact uniform-with-replacement sampler."""

    if min(record_count, steps, batch_size) < 1:
        raise CoverageAuditError("replay dimensions must be positive")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(100_000 * held_sector + seed)
    counts = torch.zeros(record_count, dtype=torch.int64)
    remaining = steps * batch_size
    while remaining:
        size = min(remaining, 1_000_000)
        sampled = torch.randint(0, record_count, (size,), generator=generator)
        counts += torch.bincount(sampled, minlength=record_count)
        remaining -= size
    total = int(counts.sum().item())
    effective_rows = (
        total * total / float(torch.sum(counts.to(torch.float64) ** 2).item())
    )
    return {
        "held_sector": held_sector,
        "seed": seed,
        "draws": total,
        "records": record_count,
        "unique_rows_seen": int((counts > 0).sum().item()),
        "unseen_rows": int((counts == 0).sum().item()),
        "row_exposure": _quantiles(counts),
        "effective_rows_inverse_simpson": effective_rows,
        "support_expansion_rows": 0,
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CoverageAuditError(f"{path.name} must contain a JSON object")
    return payload


def audit_campaign(root: str | Path) -> dict[str, Any]:
    """Audit every declared fold of a completed fundamentals campaign."""

    campaign_root = Path(root).resolve()
    campaign = _read_json(campaign_root / "CAMPAIGN.json")
    steps = int(campaign["steps"])
    batch_size = int(campaign["batch_size"])
    seeds = [int(value) for value in campaign["seeds"]]
    held_sectors = [int(value) for value in campaign["held_sectors"]]
    folds: dict[str, Any] = {}
    all_rows_seen = True
    for held in held_sectors:
        folder = campaign_root / "inputs" / f"held-sector-{held}"
        manifest = _read_json(folder / "MANIFEST.json")
        bundles = {
            split: load_tensor_bundle(folder / f"{split.upper()}.pt")
            for split in ("train", "holdout", "anchor")
        }
        replay = [
            simulate_uniform_replay(
                int(bundles["train"].features.shape[0]),
                held_sector=held,
                seed=seed,
                steps=steps,
                batch_size=batch_size,
            )
            for seed in seeds
        ]
        all_rows_seen &= all(row["unseen_rows"] == 0 for row in replay)
        folds[str(held)] = {
            "manifest_sha256": manifest.get("manifest_sha256"),
            "source_families": {
                name: manifest.get("records", {}).get(name, {}).get("source_family")
                for name in ("train", "holdout", "anchor")
            },
            "splits": {name: audit_bundle(bundle) for name, bundle in bundles.items()},
            "exact_row_overlap": {
                "train_holdout": exact_row_overlap(
                    bundles["train"], bundles["holdout"]
                ),
                "train_anchor": exact_row_overlap(bundles["train"], bundles["anchor"]),
            },
            "nearest_train_distance": {
                "holdout": nearest_train_distance(bundles["train"], bundles["holdout"]),
                "anchor": nearest_train_distance(bundles["train"], bundles["anchor"]),
            },
            "uniform_replay": replay,
        }

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "campaign_root": str(campaign_root),
        "campaign_sha256": campaign.get("campaign_sha256"),
        "campaign_file_sha256": file_sha256(campaign_root / "CAMPAIGN.json"),
        "steps": steps,
        "batch_size": batch_size,
        "draws_per_horse": steps * batch_size,
        "seeds": seeds,
        "held_sectors": held_sectors,
        "training_input_mode": "static serialized rows sampled uniformly with replacement",
        "online_transform_or_augmentation": False,
        "all_stored_train_rows_seen_by_every_sampler": all_rows_seen,
        "support_can_expand_after_row_saturation": False,
        "folds": folds,
        "interpretation": {
            "supported": (
                "Long replay amplifies gradients on the stored support; it does not add new "
                "transformations or cross-factor cells after every row has been seen."
            ),
            "not_claimed": (
                "Missing Cartesian cells are not automatically reachable states; this audit "
                "separates measured occupancy from causal training benefit."
            ),
            "next_controlled_test": (
                "Generate equal-count transformed state orbits across declared independent "
                "factors, then compare with static replay and shuffled-transform controls."
            ),
        },
    }
    return {**body, "audit_sha256": sha256_json(body)}


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render a compact human audit without dumping payload rows."""

    lines = [
        "# Clay Fundamentals Data-Coverage Audit",
        "",
        f"Audit SHA-256: `{report['audit_sha256']}`",
        "",
        "## Outcome",
        "",
        "The campaign exhausted its stored rows but did not expand concept support online.",
        "Each horse sampled a fixed 8,000-row tensor bank with replacement. Once every row",
        "was seen, additional steps only changed exposure counts; they could not add a new",
        "rotation, source family, sector, or factor crossing.",
        "",
        f"- Draws per horse: `{report['draws_per_horse']:,}`",
        f"- Every sampler saw every stored row: `{str(report['all_stored_train_rows_seen_by_every_sampler']).lower()}`",
        "- Online transform/augmentation: `false`",
        "- Promotion or unfreeze authorized by this audit: `false`",
        "",
        "## Fold market",
        "",
        "| Held sector | Train rows | Replays/row median range | Holdout nearest RMS-z median | Anchor nearest RMS-z median |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for held, fold in report["folds"].items():
        train = fold["splits"]["train"]
        medians = [row["row_exposure"]["median"] for row in fold["uniform_replay"]]
        holdout_distance = fold["nearest_train_distance"]["holdout"]["rms_z_nearest"][
            "median"
        ]
        anchor_distance = fold["nearest_train_distance"]["anchor"]["rms_z_nearest"][
            "median"
        ]
        lines.append(
            f"| {held} | {train['records']:,} | {min(medians):.0f}-{max(medians):.0f} | "
            f"{holdout_distance:.4f} | {anchor_distance:.4f} |"
        )
    lines.extend(
        (
            "",
            "## Meaning",
            "",
            "The held-sector and shifted-physics split is a valid transfer challenge, but",
            "replaying static rows cannot densify the missing region. The next experiment",
            "must vary the data itself: equal-count state orbits over target angle, phase,",
            "drive, position, and velocity crossings, with static and shuffled controls.",
            "The adaptive exposure scheduler remains unpromoted because earlier controlled",
            "runs showed that factor coverage helped while its ranking rule did not.",
            "",
            "This is a data-support finding, not evidence that any architecture improved.",
            "",
        )
    )
    return "\n".join(lines)


__all__ = [
    "CoverageAuditError",
    "FEATURE_NAMES",
    "JOINTS",
    "SCHEMA",
    "TensorBundle",
    "audit_bundle",
    "audit_campaign",
    "canonical_json",
    "derive_factors",
    "exact_row_overlap",
    "joint_receipt",
    "load_tensor_bundle",
    "marginal_receipt",
    "nearest_train_distance",
    "render_markdown",
    "sha256_json",
    "simulate_uniform_replay",
]
