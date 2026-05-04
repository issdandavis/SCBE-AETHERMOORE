#!/usr/bin/env python3
"""Benchmark the 9D-integrated space stack helpers."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import timeit

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.physics_sim.space_stack import (
    SwarmVehicle,
    decide_vehicle_governance,
    evaluate_fdir_status,
)


def run_benchmark(iterations: int) -> dict[str, float | int]:
    vehicle = SwarmVehicle(
        vehicle_id="SHEPHERD-01",
        position_m=[0.0, 0.0, 0.0],
        velocity_m_s=[0.0, 0.0, 0.0],
        battery_soc=0.92,
        thermal_margin_c=12.0,
        actuator_health=0.86,
        comm_link_quality=0.8,
    )

    # Warm cache once for stable hot-path measurement.
    evaluate_fdir_status(vehicle, state_time_s=45.0)

    cached_time = timeit.timeit(
        lambda: evaluate_fdir_status(vehicle, state_time_s=45.0),
        number=iterations,
    )
    decide_time = timeit.timeit(
        lambda: decide_vehicle_governance(vehicle, state_time_s=45.0),
        number=iterations,
    )
    decide_payload_time = timeit.timeit(
        lambda: decide_vehicle_governance(
            vehicle,
            state_time_s=45.0,
            include_state9d_payload=True,
        ),
        number=iterations,
    )

    # Vary time to pressure cache misses and represent cold-like behavior.
    start = time.perf_counter()
    for i in range(iterations):
        evaluate_fdir_status(vehicle, state_time_s=45.0 + i * 1e-4)
    varying_dt = time.perf_counter() - start

    return {
        "iterations": iterations,
        "eval_fdir_cached_ms": (cached_time / iterations) * 1000.0,
        "decide_governance_ms": (decide_time / iterations) * 1000.0,
        "decide_governance_with_payload_ms": (decide_payload_time / iterations) * 1000.0,
        "eval_fdir_varying_time_ms": (varying_dt / iterations) * 1000.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SCBE space stack helpers.")
    parser.add_argument(
        "--iterations",
        type=int,
        default=5000,
        help="Number of benchmark iterations per case.",
    )
    args = parser.parse_args()
    result = run_benchmark(args.iterations)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
