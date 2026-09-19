#!/usr/bin/env python3
"""Measure the dual-trit commitment against its direct SHAKE256 control."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.crypto.dual_trit_polarity_commitment import (  # noqa: E402
    commit_dual_trit_field,
    direct_shake256_commitment,
    dual_trit_root,
    encode_dual_trit_field,
    polarity_cell,
)

DEFAULT_REPORT = (
    ROOT / "reports" / "security" / "dual_trit_hash_benchmark_20260919.json"
)
DEFAULT_SEEDS = (11, 29, 47)


def _bit_distance(left: bytes, right: bytes) -> int:
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def _summary(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def _time_batch(function: Callable[[bytes], bytes], payloads: Sequence[bytes]) -> float:
    started = time.perf_counter_ns()
    for payload in payloads:
        function(payload)
    return (time.perf_counter_ns() - started) / len(payloads) / 1_000.0


def _seed_run(seed: int, *, cases: int, payload_bytes: int) -> dict[str, Any]:
    # Reproducible benchmark samples; this generator creates no keying material.
    rng = random.Random(seed)  # nosec B311
    payloads = [rng.randbytes(payload_bytes) for _ in range(cases)]
    direct_avalanche: list[float] = []
    dual_root_avalanche: list[float] = []
    radial_root_avalanche: list[float] = []
    output_bits = 512

    direct_outputs: set[bytes] = set()
    dual_root_outputs: set[bytes] = set()
    radial_root_outputs: set[bytes] = set()
    for payload in payloads:
        changed = bytearray(payload)
        changed[rng.randrange(payload_bytes)] ^= 1 << rng.randrange(8)
        changed_bytes = bytes(changed)

        direct = direct_shake256_commitment(payload)
        direct_changed = direct_shake256_commitment(changed_bytes)
        dual_root = dual_trit_root(payload)
        dual_root_changed = dual_trit_root(changed_bytes)
        radial_root = commit_dual_trit_field(payload).root
        radial_root_changed = commit_dual_trit_field(changed_bytes).root
        direct_outputs.add(direct)
        dual_root_outputs.add(dual_root)
        radial_root_outputs.add(radial_root)
        direct_avalanche.append(_bit_distance(direct, direct_changed) / output_bits)
        dual_root_avalanche.append(
            _bit_distance(dual_root, dual_root_changed) / output_bits
        )
        radial_root_avalanche.append(
            _bit_distance(radial_root, radial_root_changed) / output_bits
        )

    # Warm both paths before measuring. The direct control and the dual root use
    # identical output lengths and domain framing; the dual path intentionally
    # pays for six directional receipts plus its center and root.
    for payload in payloads[:8]:
        direct_shake256_commitment(payload)
        dual_trit_root(payload)
        commit_dual_trit_field(payload)
    direct_us = _time_batch(direct_shake256_commitment, payloads)
    dual_root_us = _time_batch(dual_trit_root, payloads)
    radial_root_us = _time_batch(
        lambda value: commit_dual_trit_field(value).root,
        payloads,
    )

    return {
        "seed": seed,
        "cases": cases,
        "payload_bytes": payload_bytes,
        "direct_avalanche": _summary(direct_avalanche),
        "dual_root_avalanche": _summary(dual_root_avalanche),
        "radial_root_avalanche": _summary(radial_root_avalanche),
        "direct_observed_collisions": cases - len(direct_outputs),
        "dual_root_observed_collisions": cases - len(dual_root_outputs),
        "radial_root_observed_collisions": cases - len(radial_root_outputs),
        "direct_mean_us": direct_us,
        "dual_root_mean_us": dual_root_us,
        "radial_root_mean_us": radial_root_us,
        "dual_root_over_direct_time_ratio": dual_root_us / direct_us,
        "radial_root_over_direct_time_ratio": radial_root_us / direct_us,
    }


def run_benchmark(
    *,
    seeds: Sequence[int] = DEFAULT_SEEDS,
    cases: int = 512,
    payload_bytes: int = 64,
) -> dict[str, Any]:
    if not seeds or cases < 2 or payload_bytes < 1:
        raise ValueError(
            "benchmark needs seeds, at least two cases, and nonempty payloads"
        )
    runs = [_seed_run(seed, cases=cases, payload_bytes=payload_bytes) for seed in seeds]

    direct_means = [run["direct_avalanche"]["mean"] for run in runs]
    dual_root_means = [run["dual_root_avalanche"]["mean"] for run in runs]
    radial_root_means = [run["radial_root_avalanche"]["mean"] for run in runs]
    direct_summary = _summary(direct_means)
    dual_root_summary = _summary(dual_root_means)
    radial_root_summary = _summary(radial_root_means)
    root_pooled_sd = math.sqrt(
        (direct_summary["sample_sd"] ** 2 + dual_root_summary["sample_sd"] ** 2) / 2.0
    )
    radial_pooled_sd = math.sqrt(
        (direct_summary["sample_sd"] ** 2 + radial_root_summary["sample_sd"] ** 2) / 2.0
    )
    root_avalanche_delta = dual_root_summary["mean"] - direct_summary["mean"]
    radial_avalanche_delta = radial_root_summary["mean"] - direct_summary["mean"]

    byte_cells = [polarity_cell(byte) for byte in range(256)]
    sample_field = encode_dual_trit_field(bytes(payload_bytes))
    return {
        "schema": "scbe.dual-trit-hash-benchmark.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "construction": {
            "security_primitive": "SHAKE256",
            "output_bits": 512,
            "field": "six fixed balanced trits plus exact inverse rail per byte",
            "centered_byte_map": "2*b-255",
            "shells": 128,
            "directions": 6,
            "security_boundary": (
                "Dual-trit geometry is a canonical encoding and receipt layout. "
                "It contributes no independent entropy or hardness."
            ),
        },
        "theoretical_generic_bounds": {
            "classical_collision_bits": 256,
            "quantum_collision_query_bits_bht_idealized": 512 / 3,
            "quantum_preimage_query_bits_grover_idealized": 256,
            "note": "Idealized generic-query exponents are not implementation certifications.",
        },
        "invariants": {
            "unique_byte_cells": len({cell.positive_rail for cell in byte_cells}),
            "negative_cells": sum(cell.polarity < 0 for cell in byte_cells),
            "positive_cells": sum(cell.polarity > 0 for cell in byte_cells),
            "shell_count": len({cell.shell for cell in byte_cells}),
            "complement_is_exact_inversion": all(
                polarity_cell(255 - byte).positive_rail
                == polarity_cell(byte).negative_rail
                for byte in range(256)
            ),
            "encoded_bytes_for_sample": len(sample_field),
            "sample_payload_bytes": payload_bytes,
            "representation_expansion_ratio": len(sample_field) / payload_bytes,
        },
        "runs": runs,
        "summary": {
            "direct_avalanche": direct_summary,
            "dual_root_avalanche": dual_root_summary,
            "radial_root_avalanche": radial_root_summary,
            "dual_root_minus_direct_avalanche": root_avalanche_delta,
            "radial_root_minus_direct_avalanche": radial_avalanche_delta,
            "dual_root_pooled_seed_sd": root_pooled_sd,
            "radial_root_pooled_seed_sd": radial_pooled_sd,
            "dual_root_within_two_pooled_sd": (
                abs(root_avalanche_delta) <= 2.0 * root_pooled_sd
            ),
            "radial_root_within_two_pooled_sd": (
                abs(radial_avalanche_delta) <= 2.0 * radial_pooled_sd
            ),
            "direct_total_observed_collisions": sum(
                run["direct_observed_collisions"] for run in runs
            ),
            "dual_root_total_observed_collisions": sum(
                run["dual_root_observed_collisions"] for run in runs
            ),
            "radial_root_total_observed_collisions": sum(
                run["radial_root_observed_collisions"] for run in runs
            ),
            "dual_root_over_direct_time_ratio": _summary(
                [run["dual_root_over_direct_time_ratio"] for run in runs]
            ),
            "radial_root_over_direct_time_ratio": _summary(
                [run["radial_root_over_direct_time_ratio"] for run in runs]
            ),
        },
        "claim_status": {
            "functional": "PASS",
            "cryptographic": "UNPROVEN_CUSTOM_COMPOSITION",
            "reason": (
                "Round trips, avalanche measurements, and no observed small-sample collisions "
                "do not constitute cryptanalysis. Security remains the SHAKE256 assumption."
            ),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--seeds", default=",".join(map(str, DEFAULT_SEEDS)))
    parser.add_argument("--cases", type=int, default=512)
    parser.add_argument("--payload-bytes", type=int, default=64)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    seeds = tuple(
        int(value.strip()) for value in args.seeds.split(",") if value.strip()
    )
    report = run_benchmark(
        seeds=seeds,
        cases=args.cases,
        payload_bytes=args.payload_bytes,
    )
    if not args.no_write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
