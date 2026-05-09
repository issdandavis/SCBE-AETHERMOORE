#!/usr/bin/env python3
"""Sacred Egg CRP-PUF analysis harness.

This is the forward path after the raw seeded-topology PUF diagnostic:

    uniform/mostly-uniform device -> enrolled challenge-response database
    public seed / Sacred Egg context -> challenge selector
    verifier asks challenge -> device response must match enrollment

CSV input format:

    device_id,challenge_id,read_id,r_0,r_1,r_2,...
    unit-a,c-001,0,0.10,0.90,0.11,...
    unit-a,c-001,1,0.12,0.88,0.10,...
    unit-b,c-001,0,0.91,0.10,0.89,...

Distance regimes:
- genuine: same device, same challenge, repeated reads
- impostor: different device, same challenge
- cross_challenge: same device, different challenge

For production, genuine distances must stay below impostor distances for the
same challenge. That is the challenge-response PUF question Sacred Eggs can
route into: the seed selects the challenge; the enrolled physical device answers.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from statistics import mean
from typing import Sequence

SCHEMA_VERSION = "sacred_egg_crp_puf_analysis_v1"
ARCHITECTURE_STATUS = "CHALLENGE_SELECTOR_CRP_PUF_CANDIDATE_2026_05"


@dataclass(frozen=True)
class CrpMeasurement:
    device_id: str
    challenge_id: str
    read_id: str
    values: tuple[float, ...]


@dataclass(frozen=True)
class DistanceSummary:
    count: int
    mean: float
    minimum: float
    maximum: float


@dataclass(frozen=True)
class CrpMetrics:
    schema_version: str
    architecture_status: str
    measurement_count: int
    device_count: int
    challenge_count: int
    feature_count: int
    genuine: DistanceSummary
    impostor: DistanceSummary
    cross_challenge: DistanceSummary
    reliability: float
    uniqueness: float
    challenge_separation: float
    works_for_authentication: bool
    estimated_t_bits: int
    estimated_impostor_delta_bits: int
    mean_min_entropy_per_bit: float
    estimated_total_min_entropy_bits: float


def load_measurements(path: Path) -> tuple[list[CrpMeasurement], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        required = {"device_id", "challenge_id", "read_id"}
        missing = sorted(required.difference(reader.fieldnames))
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")
        feature_names = [name for name in reader.fieldnames if name not in required]
        if not feature_names:
            raise ValueError("CSV must include at least one numeric response column")
        rows: list[CrpMeasurement] = []
        for line_number, row in enumerate(reader, start=2):
            device_id = str(row.get("device_id") or "").strip()
            challenge_id = str(row.get("challenge_id") or "").strip()
            read_id = str(row.get("read_id") or "").strip()
            if not device_id or not challenge_id or not read_id:
                raise ValueError(f"line {line_number}: device_id/challenge_id/read_id required")
            try:
                values = tuple(float(row[name]) for name in feature_names)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"line {line_number}: non-numeric response value") from exc
            rows.append(CrpMeasurement(device_id, challenge_id, read_id, values))
    return rows, feature_names


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median requires at least one value")
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _thresholds(rows: Sequence[CrpMeasurement]) -> tuple[float, ...]:
    width = len(rows[0].values)
    return tuple(_median([row.values[i] for row in rows]) for i in range(width))


def quantize(values: Sequence[float], thresholds: Sequence[float]) -> tuple[int, ...]:
    if len(values) != len(thresholds):
        raise ValueError("values and thresholds length mismatch")
    return tuple(1 if value >= threshold else 0 for value, threshold in zip(values, thresholds))


def hamming_fraction(left: Sequence[int], right: Sequence[int]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("bit vectors must be non-empty and equal length")
    return sum(1 for a, b in zip(left, right) if a != b) / len(left)


def summarize(values: Sequence[float]) -> DistanceSummary:
    if not values:
        return DistanceSummary(0, 0.0, 0.0, 0.0)
    return DistanceSummary(len(values), float(mean(values)), float(min(values)), float(max(values)))


def bit_min_entropy(bit_rows: Sequence[tuple[int, ...]]) -> tuple[float, float]:
    if not bit_rows:
        return 0.0, 0.0
    per_bit: list[float] = []
    for i in range(len(bit_rows[0])):
        ones = sum(row[i] for row in bit_rows)
        p_one = ones / len(bit_rows)
        p_max = max(p_one, 1.0 - p_one)
        per_bit.append(-math.log2(max(p_max, 1e-12)))
    return float(mean(per_bit)), float(sum(per_bit))


def pairwise_distances(
    bit_rows: Sequence[tuple[CrpMeasurement, tuple[int, ...]]],
) -> tuple[list[float], list[float], list[float]]:
    genuine: list[float] = []
    impostor: list[float] = []
    cross_challenge: list[float] = []
    for i, (row_a, bits_a) in enumerate(bit_rows):
        for row_b, bits_b in bit_rows[i + 1 :]:
            distance = hamming_fraction(bits_a, bits_b)
            same_device = row_a.device_id == row_b.device_id
            same_challenge = row_a.challenge_id == row_b.challenge_id
            if same_device and same_challenge:
                genuine.append(distance)
            elif (not same_device) and same_challenge:
                impostor.append(distance)
            elif same_device and not same_challenge:
                cross_challenge.append(distance)
    return genuine, impostor, cross_challenge


def analyze_measurements(rows: Sequence[CrpMeasurement]) -> CrpMetrics:
    if len(rows) < 2:
        raise ValueError("need at least two measurements")
    feature_count = len(rows[0].values)
    if any(len(row.values) != feature_count for row in rows):
        raise ValueError("all measurements must have the same feature count")
    thresholds = _thresholds(rows)
    bit_rows = [(row, quantize(row.values, thresholds)) for row in rows]
    genuine_values, impostor_values, cross_values = pairwise_distances(bit_rows)
    genuine = summarize(genuine_values)
    impostor = summarize(impostor_values)
    cross_challenge = summarize(cross_values)
    mean_entropy, total_entropy = bit_min_entropy([bits for _, bits in bit_rows])
    estimated_t_bits = math.ceil(genuine.maximum * feature_count)
    estimated_impostor_delta_bits = math.floor(impostor.minimum * feature_count) if impostor.count else 0
    challenge_separation = impostor.minimum - genuine.maximum if genuine.count and impostor.count else 0.0
    return CrpMetrics(
        schema_version=SCHEMA_VERSION,
        architecture_status=ARCHITECTURE_STATUS,
        measurement_count=len(rows),
        device_count=len({row.device_id for row in rows}),
        challenge_count=len({row.challenge_id for row in rows}),
        feature_count=feature_count,
        genuine=genuine,
        impostor=impostor,
        cross_challenge=cross_challenge,
        reliability=1.0 - genuine.mean,
        uniqueness=impostor.mean,
        challenge_separation=challenge_separation,
        works_for_authentication=bool(
            genuine.count and impostor.count and estimated_t_bits < estimated_impostor_delta_bits / 2
        ),
        estimated_t_bits=estimated_t_bits,
        estimated_impostor_delta_bits=estimated_impostor_delta_bits,
        mean_min_entropy_per_bit=mean_entropy,
        estimated_total_min_entropy_bits=total_entropy,
    )


def metrics_to_report(metrics: CrpMetrics, *, feature_names: Sequence[str]) -> dict:
    report = asdict(metrics)
    report["feature_names"] = list(feature_names)
    report["verdict"] = "auth_candidate" if metrics.works_for_authentication else "overlap_or_unproven"
    report["sacred_egg_role"] = (
        "Sacred Egg / GeoSeal context should select challenge_id and bind the response receipt; "
        "this harness only tests whether enrolled CRP responses separate genuine from impostor reads."
    )
    report["recommended_next"] = (
        "bind challenge_id selection to Sacred Egg context and sealed measurement receipts"
        if metrics.works_for_authentication
        else "increase response dimensionality, improve fixture stability, or collect cleaner challenge data"
    )
    return report


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze challenge-response PUF measurement CSVs.")
    parser.add_argument(
        "csv",
        type=Path,
        help="CSV with device_id, challenge_id, read_id, response columns",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("artifacts/aetherfab/sacred_egg_crp_puf_report.json"),
        help="Output JSON report path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows, feature_names = load_measurements(args.csv)
    metrics = analyze_measurements(rows)
    report = metrics_to_report(metrics, feature_names=feature_names)
    write_report(report, args.report)
    print(
        "Sacred Egg CRP-PUF analysis: "
        f"reliability={metrics.reliability:.4f} "
        f"uniqueness={metrics.uniqueness:.4f} "
        f"challenge_separation={metrics.challenge_separation:.4f} "
        f"auth_ready={metrics.works_for_authentication}"
    )
    print(f"report={args.report}")
    return 0 if metrics.works_for_authentication else 2


if __name__ == "__main__":
    raise SystemExit(main())
