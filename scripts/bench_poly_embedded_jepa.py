"""Microbenchmark for the poly-embedded JEPA harness.

Reports throughput for build, verify, and (build + verify) round-trip
against fixed thresholds. Exit code is non-zero when any threshold is
missed so CI / wrapper scripts can iterate.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python.scbe.poly_embedded_jepa import build_poly_embedding, verify_poly_embedding  # noqa: E402

THRESHOLDS = {
    "build_ops_per_s": 2000.0,
    "verify_ops_per_s": 1000.0,
    "round_trip_ops_per_s": 600.0,
}

WARMUP = 64


def _concept(i: int) -> str:
    return f"benchmark-concept-{i:08d}"


def _pos(i: int) -> tuple[int, int]:
    return i % 6, (i * 7) % 6


def _stats(n: int, elapsed: float) -> dict[str, float]:
    return {
        "ops": float(n),
        "elapsed_s": elapsed,
        "ops_per_s": n / elapsed if elapsed > 0 else float("inf"),
        "us_per_op": (elapsed * 1e6) / n if n else 0.0,
    }


def bench_build(n: int) -> dict[str, float]:
    for i in range(WARMUP):
        row, col = _pos(i)
        build_poly_embedding(_concept(i), masked_row=row, masked_col=col)
    start = time.perf_counter()
    for i in range(n):
        row, col = _pos(i)
        build_poly_embedding(_concept(i), masked_row=row, masked_col=col)
    elapsed = time.perf_counter() - start
    return _stats(n, elapsed)


def bench_verify(n: int) -> dict[str, float]:
    embeddings = []
    for i in range(n):
        row, col = _pos(i)
        embeddings.append(build_poly_embedding(_concept(i), masked_row=row, masked_col=col))
    for emb in embeddings[:WARMUP]:
        verify_poly_embedding(emb)
    start = time.perf_counter()
    for emb in embeddings:
        verify_poly_embedding(emb)
    elapsed = time.perf_counter() - start
    return _stats(n, elapsed)


def bench_round_trip(n: int) -> dict[str, float]:
    for i in range(WARMUP):
        row, col = _pos(i)
        emb = build_poly_embedding(_concept(i), masked_row=row, masked_col=col)
        verify_poly_embedding(emb)
    start = time.perf_counter()
    for i in range(n):
        row, col = _pos(i)
        emb = build_poly_embedding(_concept(i), masked_row=row, masked_col=col)
        verify_poly_embedding(emb)
    elapsed = time.perf_counter() - start
    return _stats(n, elapsed)


def _format_row(name: str, stat: dict[str, float], threshold: float, ok: bool) -> str:
    status = "PASS" if ok else "FAIL"
    return (
        f"{name:<12} {stat['ops_per_s']:>11.1f} ops/s "
        f"({stat['us_per_op']:>7.1f} us/op)  threshold {threshold:>7.0f}  {status}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=2000, help="ops per phase")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    print(f"poly_embedded_jepa benchmark  n={args.n}  warmup={WARMUP}")
    print("-" * 80)

    build = bench_build(args.n)
    verify = bench_verify(args.n)
    round_trip = bench_round_trip(args.n)

    pass_build = build["ops_per_s"] >= THRESHOLDS["build_ops_per_s"]
    pass_verify = verify["ops_per_s"] >= THRESHOLDS["verify_ops_per_s"]
    pass_round_trip = round_trip["ops_per_s"] >= THRESHOLDS["round_trip_ops_per_s"]

    print(_format_row("build", build, THRESHOLDS["build_ops_per_s"], pass_build))
    print(_format_row("verify", verify, THRESHOLDS["verify_ops_per_s"], pass_verify))
    print(_format_row("round-trip", round_trip, THRESHOLDS["round_trip_ops_per_s"], pass_round_trip))
    print("-" * 80)

    all_pass = pass_build and pass_verify and pass_round_trip
    print("ALL PASS" if all_pass else "FAIL: at least one threshold missed")

    results = {
        "n_ops": args.n,
        "build": build,
        "verify": verify,
        "round_trip": round_trip,
        "thresholds": THRESHOLDS,
        "pass": {
            "build": pass_build,
            "verify": pass_verify,
            "round_trip": pass_round_trip,
            "all": all_pass,
        },
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(results, indent=2))

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
