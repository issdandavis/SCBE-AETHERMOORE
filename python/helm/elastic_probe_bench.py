"""elastic_probe_bench: the PROBE-LENGTH DISTRIBUTION of the bijective double-hash map, not just the mean.

elastic_bijective_hash._bench_at reports the AVERAGE probes/op. The average is reassuring and misleading:
for an open-addressing double-hash map the mean stays modest under load while the TAIL explodes -- most
lookups are 1-2 probes (p50) but a few are catastrophic (max). This measures the full per-key lookup
distribution (p50/p90/p99/p999/max) across loads, so the worst-case cost is visible, not hidden in the mean.

    run([0.5, 0.9, 0.99, 0.999]) -> for each load, the probe-length percentiles + tail/mean ratio.

Deterministic (seeded). HONEST SCOPE: this characterizes THIS reversible splitmix64 DOUBLE-HASH map (the
module's own docstring notes it is a double-hash map, NOT the Bender-Kuszmaul "elastic hashing" of the
2024/25 result). It is a probe-distribution measurement, no asymptotic claim about either."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from python.scbe.elastic_bijective_hash import BijectiveDoubleHashMap  # noqa: E402


def _percentile(sorted_xs: List[int], p: float) -> int:
    if not sorted_xs:
        return 0
    return sorted_xs[min(len(sorted_xs) - 1, int(p * len(sorted_xs)))]


def lookup_probe_lengths(bits: int, load: float, seed: int) -> List[int]:
    """Fill a 2**bits-slot map to `load`, then measure the probe count of EACH key's lookup (its displacement
    from the base slot). Deterministic keys. Asserts every key is found (a probe-length only means anything
    on a successful lookup)."""
    h = BijectiveDoubleHashMap(bits=bits, seed=seed)
    n = int(h.size * load)
    rng = random.Random(seed)
    keys = ["k%d-%d" % (i, rng.getrandbits(40)) for i in range(n)]
    for i, k in enumerate(keys):
        h.put(k, i)
    lengths: List[int] = []
    for i, k in enumerate(keys):
        h.total_probes = 0
        assert h.get(k) == i, "lookup must find the key it inserted"
        lengths.append(h.total_probes)
    return lengths


def distribution(bits: int, load: float, seed: int) -> Dict[str, Any]:
    lengths = sorted(lookup_probe_lengths(bits, load, seed))
    n = len(lengths)
    mean = sum(lengths) / n if n else 0.0
    mx = lengths[-1] if lengths else 0
    return {
        "load": load,
        "keys": n,
        "mean": round(mean, 2),
        "p50": _percentile(lengths, 0.50),
        "p90": _percentile(lengths, 0.90),
        "p99": _percentile(lengths, 0.99),
        "p999": _percentile(lengths, 0.999),
        "max": mx,
        "tail_over_mean": round(mx / mean, 1) if mean else 0.0,  # how far the worst case beats the average
    }


def run(bits: int = 14, loads: Sequence[float] = (0.5, 0.9, 0.99, 0.999), seed: int = 7) -> Dict[str, Any]:
    return {"bits": bits, "seed": seed, "rows": [distribution(bits, ld, seed) for ld in loads]}


def render(summary: Dict[str, Any]) -> str:
    lines = [
        "ELASTIC PROBE-TAIL (2^%d slots, seed=%d) -- the mean hides the worst case"
        % (summary["bits"], summary["seed"]),
        "",
        "  %7s | %6s %5s %5s %6s %6s %7s | %s" % ("load", "mean", "p50", "p90", "p99", "p999", "max", "max/mean"),
        "  %s" % ("-" * 64),
    ]
    for r in summary["rows"]:
        lines.append(
            "  %6.1f%% | %6.2f %5d %5d %6d %6d %7d | %6.1fx"
            % (r["load"] * 100, r["mean"], r["p50"], r["p90"], r["p99"], r["p999"], r["max"], r["tail_over_mean"])
        )
    lines.append("")
    lines.append("  => p50 stays ~1-2 (most lookups cheap) while max/p99 explode as load -> 1: the average is")
    lines.append("     not the cost a worst-case operation pays. Probe distribution of a double-hash map (honest).")
    return "\n".join(lines)


def main(argv: Sequence[str] = None) -> int:
    ap = argparse.ArgumentParser(prog="elastic-probe-bench", description="probe-length distribution of the hash map")
    ap.add_argument("--bits", type=int, default=14)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    print(render(run(bits=a.bits, seed=a.seed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
