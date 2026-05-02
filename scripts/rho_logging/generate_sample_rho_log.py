"""
Generate a JSONL rho log via composite_harmonic_wall (SCBE_RHO_LOG=1).

Use for local smoke / scheduled capture when you do not yet have live traffic.
Real workloads: set SCBE_RHO_LOG in the process that calls the wall and skip this script.

Usage:
    PYTHONPATH=. python scripts/rho_logging/generate_sample_rho_log.py
    PYTHONPATH=. python scripts/rho_logging/generate_sample_rho_log.py --iterations 200 --seed 7
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_path() -> None:
    sys.path.insert(0, str(REPO_ROOT / "src"))


def main(argv: list[str] | None = None) -> int:
    _ensure_path()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--iterations", type=int, default=128, help="Wall calls (>= 32 warms Pearson per axis)")
    p.add_argument("--seed", type=int, default=42, help="RNG seed for reproducible synthetic distances")
    p.add_argument(
        "--path",
        type=Path,
        default=None,
        help="JSONL output (sets SCBE_RHO_LOG_PATH). Default: artifacts/rho_logging/composite_wall_rho.jsonl",
    )
    p.add_argument(
        "--truncate",
        action="store_true",
        help="Delete the log file before writing (clean run)",
    )
    args = p.parse_args(argv)

    if args.iterations < 2:
        p.error("--iterations must be at least 2")

    log_path = args.path
    if log_path is None:
        log_path = REPO_ROOT / "artifacts" / "rho_logging" / "composite_wall_rho.jsonl"
    else:
        log_path = log_path.resolve()

    if args.truncate and log_path.exists():
        log_path.unlink()

    log_path.parent.mkdir(parents=True, exist_ok=True)

    os.environ["SCBE_RHO_LOG"] = "1"
    os.environ["SCBE_RHO_LOG_PATH"] = str(log_path)

    from symphonic_cipher.scbe_aethermoore.axiom_grouped.polyhedral_flow import composite_harmonic_wall

    tongues = ("KO", "AV", "RU", "CA", "UM", "DR")
    rng = random.Random(args.seed)

    for i in range(args.iterations):
        dists = {}
        for t in tongues:
            base = 0.08 + 0.35 * rng.random()
            drift = 0.02 * math.sin(i / 11.0 + ord(t[0]) / 20.0)
            dists[t] = max(0.01, min(0.95, base + drift))
        composite_harmonic_wall(dists, phase_deviation=0.05 * rng.random())

    print(f"wrote {args.iterations} records to {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
