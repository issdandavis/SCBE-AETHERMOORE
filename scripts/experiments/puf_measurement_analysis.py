#!/usr/bin/env python3
"""AetherFab PUF measurement analysis harness.

This is the first empirical gate for crypto-seeded topology research. It does
not assume the material works. It asks the only question that matters first:

    does knowing the seed help an attacker clone the physical response?

Input CSV format (wide):

    device_id,seed_id,read_id,f_1hz,f_10hz,f_100hz,...
    seed-a-print-0,seed-a,0,0.11,0.20,0.33,...
    seed-a-print-0,seed-a,1,0.10,0.21,0.32,...
    seed-a-print-1,seed-a,0,0.28,0.41,0.51,...

Numeric feature columns are quantized to bits by global feature medians unless
explicit thresholds are provided in a JSON file.

Distance regimes:
- intra: same physical device, repeated reads; this is the noise floor.
- clone: same seed, different physical device/fabrication; attacker knows seed.
- inter: different seed; random baseline pair.

Status: parked diagnostic harness, not a claim that seeded topology is a good
PUF design. The v2 surrogate simulation found the original seeded-topology
architecture structurally weak at realistic printer tolerances: same-seed clone
pairs were much closer than random inter-device pairs. Preserve this harness for
negative-result documentation and for exotic fabrication regimes where clone
measurements may actually clear the noise floor. Future PUF work should pivot to
the challenge-selector model: uniform geometry, per-device challenge-response
database, and public seed selecting which measurement challenge to apply.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import random
from statistics import mean
from typing import Sequence

SCHEMA_VERSION = "aetherfab_puf_measurement_analysis_v1"
ARCHITECTURE_STATUS = "RAW_SEEDED_TOPOLOGY_PUF_DISCONFIRMED_STANDALONE_2026_05"
NEGATIVE_FINDING_NOTE = (
    "Parked raw seeded-topology diagnostic. Prior v2 surrogate simulation found realistic "
    "SLA/SLS/FDM printer tolerances likely make same-seed clones too close to originals "
    "when geometry alone is treated as the PUF. This does not evaluate Sacred Eggs, "
    "GeoSeal context, batch offsets, enrollment, or challenge-routing layers."
)
CLI_NEGATIVE_FINDING_WARNING = (
    "NOTE: This harness validates raw seeded topology as a standalone PUF. "
    "Simulation (puf_sim_v2.py, 2026-05-09) showed that narrow model is "
    "structurally weak at printer tolerances sigma=0.025-0.10. This warning "
    "does not evaluate Sacred Eggs, GeoSeal, batch offsets, enrollment, or "
    "challenge-selector layers."
)
RECOMMENDED_PIVOT = (
    "challenge-selector CRP-PUF: uniform geometry, per-device response database, "
    "public seed selects fresh measurement challenge"
)


@dataclass(frozen=True)
class Measurement:
    device_id: str
    read_id: str
    values: tuple[float, ...]
    seed_id: str | None = None
    fabrication_id: str | None = None


@dataclass(frozen=True)
class DistanceSummary:
    count: int
    mean: float
    minimum: float
    maximum: float


@dataclass(frozen=True)
class PufMetrics:
    schema_version: str
    measurement_count: int
    device_count: int
    feature_count: int
    quantization: str
    intra: DistanceSummary
    clone: DistanceSummary
    inter: DistanceSummary
    reliability: float
    clone_gap: float
    uniqueness: float
    separation_margin: float
    works_for_fuzzy_extractor: bool
    works_against_seed_clone: bool
    estimated_t_bits: int
    estimated_clone_delta_bits: int
    estimated_delta_bits: int
    clone_vs_intra_ratio: float
    clone_vs_inter_ratio: float
    mean_min_entropy_per_bit: float
    estimated_total_min_entropy_bits: float


def load_measurements(path: Path) -> tuple[list[Measurement], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        required = {"device_id", "read_id"}
        missing = sorted(required.difference(reader.fieldnames))
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")
        metadata = required.union({"seed_id", "fabrication_id"})
        feature_names = [name for name in reader.fieldnames if name not in metadata]
        if not feature_names:
            raise ValueError("CSV must include at least one numeric feature column")
        rows: list[Measurement] = []
        for line_number, row in enumerate(reader, start=2):
            device_id = str(row.get("device_id") or "").strip()
            read_id = str(row.get("read_id") or "").strip()
            if not device_id or not read_id:
                raise ValueError(f"line {line_number}: device_id/read_id required")
            try:
                values = tuple(float(row[name]) for name in feature_names)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"line {line_number}: non-numeric feature value"
                ) from exc
            seed_id = str(row.get("seed_id") or "").strip() or None
            fabrication_id = str(row.get("fabrication_id") or "").strip() or None
            rows.append(
                Measurement(
                    device_id=device_id,
                    read_id=read_id,
                    values=values,
                    seed_id=seed_id,
                    fabrication_id=fabrication_id,
                )
            )
    return rows, feature_names


def median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("median requires at least one value")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def median_thresholds(measurements: Sequence[Measurement]) -> tuple[float, ...]:
    width = len(measurements[0].values)
    return tuple(median([row.values[i] for row in measurements]) for i in range(width))


def load_thresholds(path: Path, feature_names: Sequence[str]) -> tuple[float, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        if len(data) != len(feature_names):
            raise ValueError("threshold list length must equal feature count")
        return tuple(float(value) for value in data)
    if isinstance(data, dict):
        missing = [name for name in feature_names if name not in data]
        if missing:
            raise ValueError(f"threshold JSON missing features: {missing}")
        return tuple(float(data[name]) for name in feature_names)
    raise ValueError("threshold JSON must be a list or object")


def quantize(values: Sequence[float], thresholds: Sequence[float]) -> tuple[int, ...]:
    if len(values) != len(thresholds):
        raise ValueError("values and thresholds length mismatch")
    return tuple(
        1 if value >= threshold else 0 for value, threshold in zip(values, thresholds)
    )


def hamming_fraction(left: Sequence[int], right: Sequence[int]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("bit vectors must be non-empty and equal length")
    return sum(1 for a, b in zip(left, right) if a != b) / len(left)


def summarize_distances(values: Sequence[float]) -> DistanceSummary:
    if not values:
        return DistanceSummary(count=0, mean=0.0, minimum=0.0, maximum=0.0)
    return DistanceSummary(
        count=len(values),
        mean=float(mean(values)),
        minimum=float(min(values)),
        maximum=float(max(values)),
    )


def _seed_key(row: Measurement) -> str:
    return row.seed_id or row.device_id


def pairwise_distances(
    bit_rows: Sequence[tuple[Measurement, tuple[int, ...]]],
) -> tuple[list[float], list[float], list[float]]:
    intra: list[float] = []
    clone: list[float] = []
    inter: list[float] = []
    for i, (row_a, bits_a) in enumerate(bit_rows):
        for row_b, bits_b in bit_rows[i + 1 :]:
            distance = hamming_fraction(bits_a, bits_b)
            if row_a.device_id == row_b.device_id:
                intra.append(distance)
            elif _seed_key(row_a) == _seed_key(row_b):
                clone.append(distance)
            else:
                inter.append(distance)
    return intra, clone, inter


def bit_min_entropy(bit_rows: Sequence[tuple[int, ...]]) -> tuple[float, float]:
    if not bit_rows:
        return 0.0, 0.0
    width = len(bit_rows[0])
    per_bit: list[float] = []
    for i in range(width):
        ones = sum(row[i] for row in bit_rows)
        p_one = ones / len(bit_rows)
        p_max = max(p_one, 1.0 - p_one)
        per_bit.append(-math.log2(max(p_max, 1e-12)))
    return float(mean(per_bit)), float(sum(per_bit))


def analyze_measurements(
    measurements: Sequence[Measurement],
    *,
    thresholds: Sequence[float] | None = None,
    quantization: str = "global_median",
) -> PufMetrics:
    if len(measurements) < 2:
        raise ValueError("need at least two measurements")
    feature_count = len(measurements[0].values)
    if any(len(row.values) != feature_count for row in measurements):
        raise ValueError("all measurements must have the same feature count")
    thresholds = (
        tuple(thresholds) if thresholds is not None else median_thresholds(measurements)
    )
    bit_rows = [(row, quantize(row.values, thresholds)) for row in measurements]
    intra_values, clone_values, inter_values = pairwise_distances(bit_rows)
    intra = summarize_distances(intra_values)
    clone = summarize_distances(clone_values)
    inter = summarize_distances(inter_values)
    bit_vectors = [bits for _, bits in bit_rows]
    mean_entropy, total_entropy = bit_min_entropy(bit_vectors)
    estimated_t_bits = math.ceil(intra.maximum * feature_count)
    estimated_clone_delta_bits = (
        math.floor(clone.minimum * feature_count) if clone.count else 0
    )
    estimated_delta_bits = (
        math.floor(inter.minimum * feature_count) if inter.count else 0
    )
    fuzzy_vs_inter = bool(
        intra.count and inter.count and estimated_t_bits < estimated_delta_bits / 2
    )
    fuzzy_vs_clone = bool(
        intra.count
        and clone.count
        and estimated_t_bits < estimated_clone_delta_bits / 2
    )
    clone_gap = clone.minimum - intra.maximum if intra.count and clone.count else 0.0
    clone_vs_intra_ratio = clone.mean / max(intra.mean, 1e-12) if clone.count else 0.0
    clone_vs_inter_ratio = (
        clone.mean / max(inter.mean, 1e-12) if clone.count and inter.count else 0.0
    )
    return PufMetrics(
        schema_version=SCHEMA_VERSION,
        measurement_count=len(measurements),
        device_count=len({row.device_id for row in measurements}),
        feature_count=feature_count,
        quantization=quantization,
        intra=intra,
        clone=clone,
        inter=inter,
        reliability=1.0 - intra.mean,
        clone_gap=clone_gap,
        uniqueness=inter.mean,
        separation_margin=(
            inter.minimum - intra.maximum if intra.count and inter.count else 0.0
        ),
        works_for_fuzzy_extractor=fuzzy_vs_inter,
        works_against_seed_clone=fuzzy_vs_clone,
        estimated_t_bits=estimated_t_bits,
        estimated_clone_delta_bits=estimated_clone_delta_bits,
        estimated_delta_bits=estimated_delta_bits,
        clone_vs_intra_ratio=clone_vs_intra_ratio,
        clone_vs_inter_ratio=clone_vs_inter_ratio,
        mean_min_entropy_per_bit=mean_entropy,
        estimated_total_min_entropy_bits=total_entropy,
    )


def bootstrap_gap_ci(
    measurements: Sequence[Measurement],
    *,
    iterations: int = 300,
    seed: int = 1337,
) -> tuple[float, float]:
    """Bootstrap separation margin CI by resampling measurements with replacement."""

    if iterations <= 0:
        raise ValueError("iterations must be positive")
    rng = random.Random(seed)
    margins: list[float] = []
    rows = list(measurements)
    for _ in range(iterations):
        sample = [rng.choice(rows) for _ in rows]
        try:
            margins.append(analyze_measurements(sample).separation_margin)
        except ValueError:
            continue
    if not margins:
        return 0.0, 0.0
    margins.sort()
    low = margins[int(0.025 * (len(margins) - 1))]
    high = margins[int(0.975 * (len(margins) - 1))]
    return float(low), float(high)


def metrics_to_report(
    metrics: PufMetrics, *, feature_names: Sequence[str], gap_ci: tuple[float, float]
) -> dict:
    report = asdict(metrics)
    report["architecture_status"] = ARCHITECTURE_STATUS
    report["status_note"] = NEGATIVE_FINDING_NOTE
    report["recommended_pivot"] = RECOMMENDED_PIVOT
    report["feature_names"] = list(feature_names)
    report["separation_margin_ci95"] = {"low": gap_ci[0], "high": gap_ci[1]}
    if metrics.clone.count:
        report["verdict"] = (
            "clone_resistant_candidate"
            if metrics.clone_gap > 0
            else "clone_overlap_or_barcode"
        )
    else:
        report["verdict"] = (
            "separated" if metrics.separation_margin > 0 else "overlap_or_unproven"
        )
    report["recommended_next"] = (
        "choose ECC parameters from estimated_t_bits and estimated_clone_delta_bits"
        if metrics.works_against_seed_clone
        else (
            "print same-seed clones and estimate clone distribution"
            if not metrics.clone.count
            else "increase fabrication-sensitive feature size or try another measurement modality"
        )
    )
    return report


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze PUF measurement CSVs for uniqueness/reliability."
    )
    parser.add_argument(
        "csv",
        type=Path,
        help="Wide CSV with device_id, read_id, numeric feature columns",
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        help="Optional JSON thresholds list or feature-name mapping",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("artifacts/aetherfab/puf_measurement_report.json"),
        help="Output JSON report path",
    )
    parser.add_argument(
        "--bootstrap",
        type=int,
        default=300,
        help="Bootstrap iterations for separation CI",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    measurements, feature_names = load_measurements(args.csv)
    thresholds = (
        load_thresholds(args.thresholds, feature_names) if args.thresholds else None
    )
    metrics = analyze_measurements(
        measurements,
        thresholds=thresholds,
        quantization="provided_thresholds" if thresholds else "global_median",
    )
    gap_ci = bootstrap_gap_ci(measurements, iterations=args.bootstrap)
    report = metrics_to_report(metrics, feature_names=feature_names, gap_ci=gap_ci)
    write_report(report, args.report)
    print(
        "AetherFab PUF analysis: "
        f"reliability={metrics.reliability:.4f} "
        f"clone_gap={metrics.clone_gap:.4f} "
        f"uniqueness={metrics.uniqueness:.4f} "
        f"separation_margin={metrics.separation_margin:.4f} "
        f"seed_clone_resistant={metrics.works_against_seed_clone}"
    )
    print(CLI_NEGATIVE_FINDING_WARNING)
    print(f"report={args.report}")
    return (
        0
        if (
            metrics.works_against_seed_clone
            or (not metrics.clone.count and metrics.separation_margin > 0)
        )
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
