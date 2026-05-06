"""Validation harness for cryptographically seeded MAHSS topology fingerprints.

This is not a finite-element or RF solver. It is a deterministic pre-physical
screen that answers the first engineering question: do seeded topology fields
produce separable, repeatable fingerprints under bounded manufacturing noise?
Real sensor traces can replace ``extract_topology_signature`` later without
changing the report schema.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

SCHEMA_VERSION = "scbe_mahss_topology_validation_v1"
MEASUREMENT_SCHEMA_VERSION = "scbe_mahss_physical_response_validation_v1"
PHI = (1.0 + math.sqrt(5.0)) / 2.0
GOLDEN_ANGLE = 2.0 * math.pi / (PHI * PHI)
DEFAULT_Q = 3329


@dataclass(frozen=True)
class TopologySpec:
    """Bounded geometry controls for the seed-to-topology map."""

    node_count: int = 144
    coefficient_count: int = 256
    radius_mm: float = 25.0
    pitch_mm: float = 0.42
    max_radial_offset_mm: float = 1.2
    min_channel_width_mm: float = 0.65
    max_channel_width_mm: float = 2.35
    max_curvature_gain: float = 0.18
    min_infill_density: float = 0.22
    max_infill_density: float = 0.82


def _seed_bytes(seed: str, index: int) -> bytes:
    return hashlib.sha256(f"{seed}:{index}".encode("utf-8")).digest()


def residue_coefficients(seed: str, count: int, q: int = DEFAULT_Q) -> np.ndarray:
    """Map a seed into centered modular residues in [-1, 1].

    The residues are the topology source. This intentionally avoids decorative
    sine/cosine noise; the geometry is driven by coefficient blocks that can be
    swapped for real ML-KEM/NTT-domain coefficients later.
    """

    values = np.empty(count, dtype=np.float64)
    half = q // 2
    for idx in range(count):
        raw = int.from_bytes(_seed_bytes(seed, idx)[:4], "big") % q
        centered = raw - q if raw > half else raw
        values[idx] = centered / float(half)
    return values


def _resample(values: np.ndarray, count: int) -> np.ndarray:
    source_x = np.linspace(0.0, 1.0, num=len(values), endpoint=True)
    target_x = np.linspace(0.0, 1.0, num=count, endpoint=True)
    return np.interp(target_x, source_x, values)


def generate_topology(seed: str, spec: TopologySpec = TopologySpec()) -> dict[str, object]:
    """Generate a deterministic manufacturable topology field from a seed."""

    if spec.node_count < 16:
        raise ValueError("node_count must be >= 16")
    if spec.coefficient_count < 32:
        raise ValueError("coefficient_count must be >= 32")

    coeffs = residue_coefficients(seed, spec.coefficient_count)
    blocks = np.array_split(coeffs, 4)
    radial = _resample(blocks[0], spec.node_count) * spec.max_radial_offset_mm
    width_unit = (_resample(blocks[1], spec.node_count) + 1.0) / 2.0
    curvature = _resample(blocks[2], spec.node_count) * spec.max_curvature_gain
    infill_unit = (_resample(blocks[3], spec.node_count) + 1.0) / 2.0

    channel_width = spec.min_channel_width_mm + width_unit * (spec.max_channel_width_mm - spec.min_channel_width_mm)
    infill_density = spec.min_infill_density + infill_unit * (spec.max_infill_density - spec.min_infill_density)

    idx = np.arange(spec.node_count, dtype=np.float64)
    theta = idx * GOLDEN_ANGLE + curvature
    radius = spec.radius_mm + radial
    z = idx * spec.pitch_mm
    points = np.column_stack((radius * np.cos(theta), radius * np.sin(theta), z))

    return {
        "seed": seed,
        "spec": spec.__dict__,
        "points": points,
        "channel_width": channel_width,
        "curvature": curvature,
        "infill_density": infill_density,
        "coefficients_sha256": hashlib.sha256(coeffs.tobytes()).hexdigest(),
    }


def apply_manufacturing_noise(
    topology: dict[str, object],
    *,
    noise_seed: str,
    position_sigma_mm: float = 0.035,
    channel_sigma_mm: float = 0.018,
    density_sigma: float = 0.008,
) -> dict[str, object]:
    """Return a bounded noisy measurement copy of a generated topology."""

    rng_seed = int.from_bytes(hashlib.sha256(noise_seed.encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(rng_seed)
    spec = TopologySpec(**topology["spec"])  # type: ignore[arg-type]
    points = np.asarray(topology["points"], dtype=np.float64) + rng.normal(0.0, position_sigma_mm, (spec.node_count, 3))
    channel_width = np.clip(
        np.asarray(topology["channel_width"], dtype=np.float64) + rng.normal(0.0, channel_sigma_mm, spec.node_count),
        spec.min_channel_width_mm,
        spec.max_channel_width_mm,
    )
    infill_density = np.clip(
        np.asarray(topology["infill_density"], dtype=np.float64) + rng.normal(0.0, density_sigma, spec.node_count),
        spec.min_infill_density,
        spec.max_infill_density,
    )
    noisy = dict(topology)
    noisy["points"] = points
    noisy["channel_width"] = channel_width
    noisy["infill_density"] = infill_density
    noisy["measurement_noise"] = {
        "position_sigma_mm": position_sigma_mm,
        "channel_sigma_mm": channel_sigma_mm,
        "density_sigma": density_sigma,
        "noise_seed": noise_seed,
    }
    return noisy


def _stats(values: np.ndarray) -> list[float]:
    return [
        float(np.mean(values)),
        float(np.std(values)),
        float(np.min(values)),
        float(np.max(values)),
        float(np.quantile(values, 0.25)),
        float(np.quantile(values, 0.75)),
    ]


def _fft_magnitudes(values: np.ndarray, count: int = 10) -> list[float]:
    centered = values - float(np.mean(values))
    spectrum = np.abs(np.fft.rfft(centered))
    total = float(np.sum(spectrum)) or 1.0
    return [float(v / total) for v in spectrum[1 : count + 1]]


def extract_topology_signature(topology: dict[str, object]) -> np.ndarray:
    """Extract a sensor-like signature vector from topology fields."""

    points = np.asarray(topology["points"], dtype=np.float64)
    widths = np.asarray(topology["channel_width"], dtype=np.float64)
    curvature = np.asarray(topology["curvature"], dtype=np.float64)
    infill = np.asarray(topology["infill_density"], dtype=np.float64)

    radial = np.linalg.norm(points[:, :2], axis=1)
    strut_lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    bend_angles = np.diff(np.unwrap(np.arctan2(points[:, 1], points[:, 0])))
    inertia = np.linalg.eigvalsh(np.cov(points.T))

    features: list[float] = []
    for series in (radial, strut_lengths, bend_angles, widths, curvature, infill):
        features.extend(_stats(series))
        features.extend(_fft_magnitudes(series))
    features.extend(float(v) for v in inertia)
    vector = np.asarray(features, dtype=np.float64)
    norm = float(np.linalg.norm(vector)) or 1.0
    return vector / norm


def fingerprint(signature: np.ndarray, *, precision: int = 6) -> str:
    quantized = np.round(signature, precision)
    return hashlib.sha256(quantized.tobytes()).hexdigest()


def euclidean_distance(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right))


def pairwise_distances(signatures: Sequence[np.ndarray]) -> list[float]:
    distances: list[float] = []
    for i, left in enumerate(signatures):
        for right in signatures[i + 1 :]:
            distances.append(euclidean_distance(left, right))
    return distances


def extract_measurement_signature(samples: Sequence[float], *, fft_bins: int = 32) -> np.ndarray:
    """Extract a normalized signature from one physical response trace.

    The input can be vibration amplitude, RF response, thermal response, or
    impedance magnitude. The extractor is intentionally sensor-agnostic: it
    keeps time-domain statistics plus normalized spectral energy so the same
    authentication harness can compare different measurement channels.
    """

    values = np.asarray(samples, dtype=np.float64)
    if values.size < 16:
        raise ValueError("measurement trace must contain at least 16 samples")
    values = values - float(np.mean(values))
    amplitude = float(np.max(np.abs(values))) or 1.0
    values = values / amplitude
    spectrum = np.abs(np.fft.rfft(values))
    spectral_total = float(np.sum(spectrum)) or 1.0
    spectral = spectrum / spectral_total
    bins = spectral[1 : fft_bins + 1]
    if bins.size < fft_bins:
        bins = np.pad(bins, (0, fft_bins - bins.size))
    freqs = np.arange(spectral.size, dtype=np.float64)
    centroid = float(np.sum(freqs * spectral) / (np.sum(spectral) or 1.0))
    bandwidth = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * spectral) / (np.sum(spectral) or 1.0)))
    peak_index = float(np.argmax(spectral[1:]) + 1 if spectral.size > 1 else 0)
    features = np.asarray(
        [
            *_stats(values),
            *_fft_magnitudes(values, count=16),
            *[float(v) for v in bins],
            centroid / max(float(spectral.size), 1.0),
            bandwidth / max(float(spectral.size), 1.0),
            peak_index / max(float(spectral.size), 1.0),
        ],
        dtype=np.float64,
    )
    norm = float(np.linalg.norm(features)) or 1.0
    return features / norm


def load_measurement_csv(path: Path) -> dict[str, list[np.ndarray]]:
    """Load sensor traces from CSV grouped by seed and repeat.

    Required columns: ``seed``, ``repeat``, and ``value``. Optional time/frequency
    columns are ignored for now because row order is enough for repeatable
    impulse-response and sweep traces.
    """

    grouped: dict[tuple[str, str], list[float]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"seed", "repeat", "value"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"measurement CSV missing required columns: {sorted(missing)}")
        for row in reader:
            seed = str(row["seed"])
            repeat = str(row["repeat"])
            grouped.setdefault((seed, repeat), []).append(float(row["value"]))

    by_seed: dict[str, list[np.ndarray]] = {}
    for (seed, _repeat), values in sorted(grouped.items()):
        by_seed.setdefault(seed, []).append(np.asarray(values, dtype=np.float64))
    return by_seed


def synthetic_impulse_trace(
    seed: str,
    repeat: int,
    *,
    sample_count: int = 512,
    noise_sigma: float = 0.025,
) -> np.ndarray:
    """Generate a deterministic stand-in for tap-test / impulse-response data."""

    if sample_count < 64:
        raise ValueError("sample_count must be >= 64")
    coeffs = residue_coefficients(seed, 64)
    t = np.linspace(0.0, 1.0, sample_count, endpoint=False)
    trace = np.zeros(sample_count, dtype=np.float64)
    for mode_idx, coeff in enumerate(coeffs[:8]):
        frequency = 18.0 + mode_idx * 13.0 + abs(float(coeff)) * 9.0
        damping = 2.4 + mode_idx * 0.32 + abs(float(coeffs[mode_idx + 8])) * 0.9
        phase = float(coeffs[mode_idx + 16]) * math.pi
        amplitude = 0.45 / (mode_idx + 1.0) + 0.05 * abs(float(coeffs[mode_idx + 24]))
        trace += amplitude * np.exp(-damping * t) * np.sin(2.0 * math.pi * frequency * t + phase)
    rng_seed = int.from_bytes(hashlib.sha256(f"{seed}:synthetic:{repeat}".encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(rng_seed)
    trace += rng.normal(0.0, noise_sigma, sample_count)
    return trace


def write_synthetic_measurement_csv(
    output: Path,
    *,
    seed_count: int = 12,
    repeats_per_seed: int = 4,
    sample_count: int = 512,
    noise_sigma: float = 0.025,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("seed", "repeat", "sample_index", "value"))
        writer.writeheader()
        for seed_idx in range(seed_count):
            seed = f"mahss-physical-{seed_idx:04d}"
            for repeat in range(repeats_per_seed):
                trace = synthetic_impulse_trace(seed, repeat, sample_count=sample_count, noise_sigma=noise_sigma)
                for sample_index, value in enumerate(trace):
                    writer.writerow(
                        {
                            "seed": seed,
                            "repeat": repeat,
                            "sample_index": sample_index,
                            "value": f"{float(value):.12g}",
                        }
                    )


def run_measurement_validation(
    measurements: Mapping[str, Sequence[Sequence[float]]],
    *,
    channel: str = "synthetic_impulse",
    enrollment_repeats: int | None = None,
) -> dict[str, object]:
    """Validate physical-response clustering from measured traces.

    The first ``enrollment_repeats`` traces for each seed are averaged into an
    enrollment centroid; remaining repeats are verification attempts for that
    same seed. Centroid enrollment is the realistic physical protocol because
    single taps are too sensitive to fixture and contact noise.
    """

    if len(measurements) < 2:
        raise ValueError("at least two seeds are required")
    enrolled: dict[str, np.ndarray] = {}
    verification: dict[str, list[np.ndarray]] = {}
    rows: list[dict[str, object]] = []
    for seed, traces in sorted(measurements.items()):
        trace_list = list(traces)
        if len(trace_list) < 2:
            raise ValueError(f"seed {seed!r} must have at least two repeats")
        enroll_count = enrollment_repeats if enrollment_repeats is not None else min(2, len(trace_list) - 1)
        if enroll_count < 1 or enroll_count >= len(trace_list):
            raise ValueError(f"seed {seed!r} has invalid enrollment_repeats={enroll_count}")
        signatures = [extract_measurement_signature(trace) for trace in trace_list]
        centroid = np.mean(np.vstack(signatures[:enroll_count]), axis=0)
        centroid = centroid / (float(np.linalg.norm(centroid)) or 1.0)
        enrolled[seed] = centroid
        verification[seed] = signatures[enroll_count:]
        rows.append(
            {
                "seed": seed,
                "enrollment_fingerprint_sha256": fingerprint(centroid),
                "repeat_count": len(trace_list),
                "enrollment_repeat_count": enroll_count,
            }
        )

    inter_distances = pairwise_distances(list(enrolled.values()))
    intra_distances = [
        euclidean_distance(enrolled[seed], signature)
        for seed, signatures in verification.items()
        for signature in signatures
    ]
    min_inter = min(inter_distances)
    max_intra = max(intra_distances)
    threshold = (min_inter + max_intra) / 2.0
    false_rejects = sum(1 for distance in intra_distances if distance > threshold)
    false_accepts = sum(1 for distance in inter_distances if distance <= threshold)
    collision_count = len(rows) - len({row["enrollment_fingerprint_sha256"] for row in rows})
    margin = min_inter - max_intra
    passed = margin > 0.0 and false_accepts == 0 and false_rejects == 0 and collision_count == 0

    return {
        "schema_version": MEASUREMENT_SCHEMA_VERSION,
        "channel": channel,
        "seed_count": len(measurements),
        "enrollment_repeats": enrollment_repeats,
        "metrics": {
            "min_inter_seed_distance": min_inter,
            "mean_inter_seed_distance": float(np.mean(inter_distances)),
            "max_intra_seed_distance": max_intra,
            "mean_intra_seed_distance": float(np.mean(intra_distances)),
            "separation_margin": margin,
            "auth_threshold": threshold,
            "false_accept_count": false_accepts,
            "false_reject_count": false_rejects,
            "fingerprint_collision_count": collision_count,
        },
        "rows": rows,
        "decision_record": {
            "action": "QUARANTINE",
            "reason": (
                "physical-response channel separates in this run"
                if passed
                else "physical-response channel does not yet separate reliably"
            ),
            "confidence": 0.78 if passed else 0.35,
            "signature": hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()[:32],
        },
        "gate_report": {
            "G0_schema": {"status": "pass", "reason": "seed/repeat/value traces loaded"},
            "G1_uniqueness": {
                "status": "pass" if collision_count == 0 else "fail",
                "reason": f"fingerprint collisions={collision_count}",
            },
            "G2_repeatability": {
                "status": "pass" if margin > 0.0 else "fail",
                "reason": f"min_inter_seed_distance={min_inter:.9f}, max_intra_seed_distance={max_intra:.9f}",
            },
            "G3_authentication": {
                "status": "pass" if false_accepts == 0 and false_rejects == 0 else "fail",
                "reason": f"false_accepts={false_accepts}, false_rejects={false_rejects}, threshold={threshold:.9f}",
            },
            "G4_promotion": {
                "status": "quarantine",
                "reason": "requires repeated real-world sensor sessions before production authentication",
            },
        },
        "rollback_plan": "Drop this channel or strengthen topology perturbations if physical clusters overlap.",
    }


def run_validation(
    *,
    seed_count: int = 24,
    repeats_per_seed: int = 4,
    spec: TopologySpec = TopologySpec(),
    position_sigma_mm: float = 0.035,
    channel_sigma_mm: float = 0.018,
    density_sigma: float = 0.008,
) -> dict[str, object]:
    """Run uniqueness, repeatability, and authentication checks."""

    if seed_count < 2:
        raise ValueError("seed_count must be >= 2")
    if repeats_per_seed < 2:
        raise ValueError("repeats_per_seed must be >= 2")

    seeds = [f"mahss-topology-{idx:04d}" for idx in range(seed_count)]
    enrolled: dict[str, np.ndarray] = {}
    repeated: dict[str, list[np.ndarray]] = {}
    rows: list[dict[str, object]] = []

    for seed in seeds:
        topology = generate_topology(seed, spec)
        base_signature = extract_topology_signature(topology)
        enrolled[seed] = base_signature
        repeated[seed] = []
        rows.append(
            {
                "seed": seed,
                "fingerprint_sha256": fingerprint(base_signature),
                "coefficients_sha256": topology["coefficients_sha256"],
            }
        )
        for repeat_idx in range(repeats_per_seed):
            measured = apply_manufacturing_noise(
                topology,
                noise_seed=f"{seed}:repeat:{repeat_idx}",
                position_sigma_mm=position_sigma_mm,
                channel_sigma_mm=channel_sigma_mm,
                density_sigma=density_sigma,
            )
            repeated[seed].append(extract_topology_signature(measured))

    inter_distances = pairwise_distances(list(enrolled.values()))
    intra_distances = [
        euclidean_distance(enrolled[seed], measured) for seed, measurements in repeated.items() for measured in measurements
    ]
    min_inter = min(inter_distances)
    max_intra = max(intra_distances)
    threshold = (min_inter + max_intra) / 2.0
    false_rejects = sum(1 for distance in intra_distances if distance > threshold)
    false_accepts = sum(1 for distance in inter_distances if distance <= threshold)
    collision_count = len(rows) - len({row["fingerprint_sha256"] for row in rows})
    margin = min_inter - max_intra

    gates = {
        "G0_spec": {
            "status": "pass",
            "reason": "deterministic seed, coefficient source, noise model, and thresholds are explicit",
        },
        "G1_unit": {
            "status": "pass" if collision_count == 0 else "fail",
            "reason": f"fingerprint collisions={collision_count}",
        },
        "G2_repeatability": {
            "status": "pass" if margin > 0.0 else "fail",
            "reason": f"min_inter_seed_distance={min_inter:.9f}, max_intra_seed_distance={max_intra:.9f}",
        },
        "G3_authentication": {
            "status": "pass" if false_accepts == 0 and false_rejects == 0 else "fail",
            "reason": f"false_accepts={false_accepts}, false_rejects={false_rejects}, threshold={threshold:.9f}",
        },
        "G4_promotion": {
            "status": "quarantine",
            "reason": "simulation-only validation; requires physical vibration/RF/thermal/impedance measurements",
        },
    }
    decision = "QUARANTINE" if gates["G4_promotion"]["status"] == "quarantine" else "ALLOW"

    return {
        "schema_version": SCHEMA_VERSION,
        "hypothesis": (
            "Cryptographically seeded coefficient fields produce topology signatures where same-seed "
            "manufacturing measurements cluster tighter than different-seed topologies."
        ),
        "spec": spec.__dict__,
        "seed_count": seed_count,
        "repeats_per_seed": repeats_per_seed,
        "noise_model": {
            "position_sigma_mm": position_sigma_mm,
            "channel_sigma_mm": channel_sigma_mm,
            "density_sigma": density_sigma,
        },
        "metrics": {
            "min_inter_seed_distance": min_inter,
            "mean_inter_seed_distance": float(np.mean(inter_distances)),
            "max_intra_seed_distance": max_intra,
            "mean_intra_seed_distance": float(np.mean(intra_distances)),
            "separation_margin": margin,
            "auth_threshold": threshold,
            "false_accept_count": false_accepts,
            "false_reject_count": false_rejects,
            "fingerprint_collision_count": collision_count,
        },
        "rows": rows,
        "state_vector": [round(v, 6) for v in _state_vector(min_inter, max_intra, margin, false_accepts, false_rejects)],
        "decision_record": {
            "action": decision,
            "reason": "pre-physical topology authentication passes simulation gates but is not manufacturable proof yet",
            "confidence": 0.72 if margin > 0.0 and false_accepts == 0 and false_rejects == 0 else 0.38,
            "signature": hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()[:32],
        },
        "gate_report": gates,
        "rollback_plan": "Keep as experiment-only artifact; do not wire into production authentication until physical clusters separate.",
    }


def _state_vector(
    min_inter: float,
    max_intra: float,
    margin: float,
    false_accepts: int,
    false_rejects: int,
) -> list[float]:
    vector = [0.0] * 21
    vector[0] = 1.0
    vector[1] = min(1.0, max(0.0, margin / max(min_inter, 1e-9)))
    vector[2] = 1.0 if margin > 0.0 else 0.0
    vector[3] = min_inter
    vector[4] = max_intra
    vector[5] = margin
    vector[12] = 1.0 if false_accepts == 0 else 0.0
    vector[13] = 1.0 if false_rejects == 0 else 0.0
    vector[20] = 0.5  # experiment lane, not production promotion
    return vector


def write_report(report: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-count", type=int, default=24)
    parser.add_argument("--repeats-per-seed", type=int, default=4)
    parser.add_argument("--node-count", type=int, default=TopologySpec.node_count)
    parser.add_argument("--coefficient-count", type=int, default=TopologySpec.coefficient_count)
    parser.add_argument("--position-sigma-mm", type=float, default=0.035)
    parser.add_argument("--channel-sigma-mm", type=float, default=0.018)
    parser.add_argument("--density-sigma", type=float, default=0.008)
    parser.add_argument(
        "--measurement-csv",
        type=Path,
        default=None,
        help="Validate physical response traces from CSV columns: seed, repeat, value.",
    )
    parser.add_argument(
        "--make-synthetic-measurements",
        type=Path,
        default=None,
        help="Write a deterministic synthetic impulse-response CSV, then validate it.",
    )
    parser.add_argument("--sample-count", type=int, default=512, help="Samples per synthetic measurement trace.")
    parser.add_argument("--measurement-noise-sigma", type=float, default=0.025)
    parser.add_argument("--measurement-channel", default="synthetic_impulse")
    parser.add_argument(
        "--enrollment-repeats",
        type=int,
        default=None,
        help="Number of traces per seed to average into the enrollment signature.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mahss_topology/topology_validation_v1.json"),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    measurement_csv = args.measurement_csv
    if args.make_synthetic_measurements is not None:
        write_synthetic_measurement_csv(
            args.make_synthetic_measurements,
            seed_count=args.seed_count,
            repeats_per_seed=args.repeats_per_seed,
            sample_count=args.sample_count,
            noise_sigma=args.measurement_noise_sigma,
        )
        measurement_csv = args.make_synthetic_measurements
    if measurement_csv is not None:
        report = run_measurement_validation(
            load_measurement_csv(measurement_csv),
            channel=args.measurement_channel,
            enrollment_repeats=args.enrollment_repeats,
        )
        report["measurement_csv"] = str(measurement_csv)
        write_report(report, args.output)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            metrics = report["metrics"]
            assert isinstance(metrics, dict)
            print(f"wrote {args.output}")
            print(
                "measurement_margin={separation_margin:.9f} min_inter={min_inter_seed_distance:.9f} "
                "max_intra={max_intra_seed_distance:.9f} FAR={false_accept_count} FRR={false_reject_count}".format(
                    **metrics
                )
            )
            print(f"decision={report['decision_record']['action']}")  # type: ignore[index]
        return 0

    spec = TopologySpec(node_count=args.node_count, coefficient_count=args.coefficient_count)
    report = run_validation(
        seed_count=args.seed_count,
        repeats_per_seed=args.repeats_per_seed,
        spec=spec,
        position_sigma_mm=args.position_sigma_mm,
        channel_sigma_mm=args.channel_sigma_mm,
        density_sigma=args.density_sigma,
    )
    write_report(report, args.output)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        metrics = report["metrics"]
        assert isinstance(metrics, dict)
        print(f"wrote {args.output}")
        print(
            "margin={separation_margin:.9f} min_inter={min_inter_seed_distance:.9f} "
            "max_intra={max_intra_seed_distance:.9f} FAR={false_accept_count} FRR={false_reject_count}".format(
                **metrics
            )
        )
        print(f"decision={report['decision_record']['action']}")  # type: ignore[index]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
