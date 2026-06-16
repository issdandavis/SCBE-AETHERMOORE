#!/usr/bin/env python3
"""Reproducible benchmark: AST cube encoder, Rust vs Python reference.

Emits a filled score card (see research/benchmarks/score-template.json) so the
encoder speed claim has reproducible evidence instead of a bare number.

Methodology (see research/benchmarks/benchmarking-reference.md):
- warm up, then >= RUNS measured runs
- report mean / median / stddev / min / max / CV% / 95% CI
- one fixed corpus, same inputs to both variants
- record full environment + commit
- speedup only quoted when both variants are stable (CV% < CV_WARN)

Metric (stated exactly): wall time to encode the corpus end-to-end.
- Python: in-process encode_matrix() over each file (interpreter already running;
  startup NOT counted).
- Rust: ONE subprocess invocation over all files, compact binary transport
  (process startup IS counted -- this is the honest end-to-end cost).
This asymmetry favors Python on tiny corpora; it is disclosed, not hidden.

Usage:
    python scripts/benchmarks/encoder_bench.py [--runs N] [--warmup N] [--out PATH]
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from python.scbe import ast_cube_encoder, ast_cube_rust  # noqa: E402

CV_WARN = 5.0  # percent; above this a result is noise, not a measurement


def corpus() -> list[Path]:
    """Deterministic corpus: the encoder's own neighbourhood of real Python files."""
    files = sorted((ROOT / "python" / "scbe").glob("*.py"))
    files = [f for f in files if f.name != "__init__.py"]
    return files[:20]


def run_python(files: list[Path]) -> float:
    start = time.perf_counter()
    for path in files:
        src = path.read_text(encoding="utf-8", errors="surrogatepass")
        ast_cube_encoder.encode_matrix(src)
    return time.perf_counter() - start


def run_rust(files: list[Path]) -> float:
    start = time.perf_counter()
    ast_cube_rust.encode_files_binary_raw(files)  # one invocation, all files
    return time.perf_counter() - start


def measure(fn, files: list[Path], runs: int, warmup: int) -> list[float]:
    for _ in range(warmup):
        fn(files)
    return [fn(files) for _ in range(runs)]


def summarize(times: list[float]) -> dict:
    mean = statistics.fmean(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0.0
    n = len(times)
    half_ci = 1.96 * stdev / math.sqrt(n) if n > 1 else 0.0
    return {
        "runs": n,
        "mean": round(mean, 6),
        "median": round(statistics.median(times), 6),
        "stddev": round(stdev, 6),
        "min": round(min(times), 6),
        "max": round(max(times), 6),
        "cv_pct": round((stdev / mean) * 100.0, 3) if mean else 0.0,
        "ci95": [round(mean - half_ci, 6), round(mean + half_ci, 6)],
        "unit": "s",
    }


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             check=True, capture_output=True, text=True)
        return out.stdout.strip()
    except Exception:
        return ""


def environment() -> dict:
    return {
        "cpu": platform.processor() or platform.machine(),
        "cores": os.cpu_count() or 0,
        "os": f"{platform.system()} {platform.release()}",
        "runtime": f"python {platform.python_version()}",
        "toolchain_versions": {"rust_exe": str(ast_cube_rust.DEFAULT_EXE.name)},
        "commit": git_commit(),
        "date": datetime.date.today().isoformat(),
        "machine_class": "laptop",
        "cpu_governor": "unknown",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    files = corpus()
    if not files:
        print("no corpus files found", file=sys.stderr)
        return 1
    loc = sum(len(p.read_text(encoding="utf-8", errors="surrogatepass").splitlines()) for p in files)

    py = summarize(measure(run_python, files, args.runs, args.warmup))

    rust_built = ast_cube_rust.rust_encoder_available()
    rust = summarize(measure(run_rust, files, args.runs, args.warmup)) if rust_built else None

    speedup = None
    stable = py["cv_pct"] < CV_WARN and (rust is None or rust["cv_pct"] < CV_WARN)
    if rust and rust["median"] > 0:
        speedup = round(py["median"] / rust["median"], 2)

    card = {
        "schema_version": "scbe_benchmark_score_v1",
        "benchmark": "ast-cube-encoder",
        "goal": "comparison",
        "type": {"scope": "macro", "axis": "latency", "state": "warm", "clock": "wall"},
        "metric": {
            "name": "wall_time",
            "unit": "s",
            "lower_is_better": True,
            "definition": "end-to-end encode of the corpus; Python in-process (no interpreter "
                          "startup), Rust one subprocess incl. process startup + binary transport",
        },
        "result": rust if rust else py,
        "variants": {"python_reference": py, "rust": rust},
        "baseline": {
            "name": "python-reference (encode_matrix)",
            "median": py["median"],
            "speedup_x": speedup,
            "speedup_note": "speedup = python.median / rust.median; quote only when both cv_pct < %s" % CV_WARN,
        },
        "input": {
            "description": "python/scbe/*.py (excl __init__)",
            "size": f"{len(files)} files / {loc} LOC",
            "seed": 0,
        },
        "environment": environment(),
        "command": "python scripts/benchmarks/encoder_bench.py --runs %d --warmup %d" % (args.runs, args.warmup),
        "tool": "custom (perf_counter, stdlib statistics)",
        "reproducible": True,
        "modeled_not_measured": False,
        "stable": stable,
        "notes": "Rust path includes subprocess startup; on a small corpus that startup caps the "
                 "observed speedup vs the pure-encode ratio. Not stable => re-run on a quiet machine "
                 "with CPU governor pinned before publishing.",
    }

    default_out = ROOT / "research" / "benchmarks" / "results" / f"encoder-{card['environment']['date']}.json"
    out_path = Path(args.out) if args.out else default_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(card, indent=2), encoding="utf-8")

    print(f"corpus: {len(files)} files / {loc} LOC")
    print(f"python : median {py['median']*1000:.2f} ms  CV {py['cv_pct']}%  (n={py['runs']})")
    if rust:
        print(f"rust   : median {rust['median']*1000:.2f} ms  CV {rust['cv_pct']}%  (n={rust['runs']})")
        verdict = f"{speedup}x faster" if stable else f"{speedup}x (UNSTABLE - re-run)"
        print(f"speedup: {verdict}")
    else:
        print("rust   : NOT BUILT (cargo build --release --manifest-path rust/ast_cube/Cargo.toml)")
    print(f"card   : {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
