#!/usr/bin/env python3
"""Phi-loop benchmark controller.

Runs a benchmark in Fibonacci-sized loops and maps each observed speedup onto
the nearest powers of phi. The next target is not fixed: it moves from the
current observed ratio toward the next phi layer by one phi-weighted step.

This is a controller, not a replacement for the underlying benchmark cards.
Use it to explore convergence; publish the underlying cards for claims.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PHI = (1.0 + math.sqrt(5.0)) / 2.0


def phi_state(speedup: float) -> dict[str, float | int]:
    if speedup <= 0:
        raise ValueError("speedup must be positive")
    layer = math.floor(math.log(speedup, PHI))
    lower = PHI**layer
    upper = PHI ** (layer + 1)
    progress = (speedup - lower) / (upper - lower) if upper != lower else 1.0
    moving_target = speedup + (upper - speedup) / PHI
    return {
        "layer": layer,
        "lower_phi_power": round(lower, 6),
        "upper_phi_power": round(upper, 6),
        "progress_to_next_phi_layer": round(progress, 6),
        "moving_target_speedup_x": round(moving_target, 6),
    }


def run_encoder(loop_index: int, runs: int, warmup: int, pure_runs: int, out_dir: Path) -> dict[str, Any]:
    out = out_dir / f"encoder-phi-loop-{loop_index:02d}.json"
    cmd = [
        sys.executable,
        "scripts/benchmarks/encoder_bench.py",
        "--runs",
        str(runs),
        "--warmup",
        str(warmup),
        "--pure-runs",
        str(pure_runs),
        "--out",
        str(out),
    ]
    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)
    card = json.loads(out.read_text(encoding="utf-8"))
    speedup = float(card["baseline"]["speedup_x"])
    engine_speedup = card.get("pure_encode", {}).get("engine_speedup_x")
    return {
        "loop": loop_index,
        "runs": runs,
        "warmup": warmup,
        "pure_runs": pure_runs,
        "card": str(out.relative_to(ROOT)).replace("\\", "/"),
        "stdout": completed.stdout.strip(),
        "end_to_end_speedup_x": speedup,
        "end_to_end_phi": phi_state(speedup),
        "engine_speedup_x": engine_speedup,
        "engine_phi": phi_state(float(engine_speedup)) if engine_speedup else None,
        "stable": card.get("stable", False),
        "python_cv_pct": card["variants"]["python_reference"]["cv_pct"],
        "rust_cv_pct": card["variants"]["rust"]["cv_pct"],
    }


def fibonacci_pairs(count: int, start_runs: int = 5) -> list[tuple[int, int]]:
    seq = [1, 1]
    while len(seq) < count + 5:
        seq.append(seq[-1] + seq[-2])
    runs = [n for n in seq if n >= start_runs][:count]
    return [(r, max(1, round(r / PHI))) for r in runs]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loops", type=int, default=3)
    parser.add_argument("--out", default="research/benchmarks/results/phi-loop-encoder-local.json")
    parser.add_argument("--pure-runs", type=int, default=3)
    args = parser.parse_args()

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    loop_dir = out_path.parent / "phi-loop-cards"
    loop_dir.mkdir(parents=True, exist_ok=True)

    loops = []
    for i, (runs, warmup) in enumerate(fibonacci_pairs(args.loops), start=1):
        rec = run_encoder(i, runs, warmup, args.pure_runs, loop_dir)
        loops.append(rec)
        print(
            "loop {i}: runs={runs} warmup={warmup} e2e={e2e:.2f}x "
            "target->{target:.2f}x engine={engine}x".format(
                i=i,
                runs=runs,
                warmup=warmup,
                e2e=rec["end_to_end_speedup_x"],
                target=rec["end_to_end_phi"]["moving_target_speedup_x"],
                engine=rec["engine_speedup_x"],
            )
        )

    payload = {
        "schema_version": "scbe_phi_loop_benchmark_v1",
        "benchmark": "ast-cube-encoder",
        "phi": PHI,
        "controller": {
            "loop_sample_sizes": "Fibonacci sequence",
            "target_rule": "next_target = observed + (next_phi_power - observed) / phi",
            "interpretation": "speedup is mapped to phi^n layers; target moves toward the next layer each loop",
        },
        "loops": loops,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"phi card: {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
