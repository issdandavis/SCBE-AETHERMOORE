"""
Read a composite_harmonic_wall rho_i log and print a per-axis summary.

Usage (PowerShell):
    python scripts/analyze_rho_log.py
    python scripts/analyze_rho_log.py --path artifacts/rho_logging/composite_wall_rho.jsonl
    python scripts/analyze_rho_log.py --path <file> --json
    python scripts/analyze_rho_log.py --hint
    python scripts/analyze_rho_log.py --hint-only

Synthetic capture (no live traffic): see scripts/rho_logging/generate_sample_rho_log.py or
scripts/windows/capture_rho_log_smoke.ps1 for a one-shot table.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_PATH = Path("artifacts") / "rho_logging" / "composite_wall_rho.jsonl"
RHO_LOG_WINDOW = 256
RHO_LOG_MIN_SAMPLES = 32


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = min(len(xs), len(ys))
    if n < 2:
        return None
    x = xs[-n:]
    y = ys[-n:]
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0.0 or dy == 0.0:
        return 0.0
    return float(num / (dx * dy))


def _rolling_rhos(xs: List[float], ys: List[float]) -> List[float]:
    out: List[float] = []
    n = min(len(xs), len(ys))
    for end in range(RHO_LOG_MIN_SAMPLES, n + 1):
        start = max(0, end - RHO_LOG_WINDOW)
        rho = _pearson(xs[start:end], ys[start:end])
        if rho is not None and math.isfinite(rho):
            out.append(float(rho))
    return out


def _summarize(records: List[dict]) -> Dict[str, dict]:
    distances_by_axis: Dict[str, List[float]] = defaultdict(list)
    h_by_axis: Dict[str, List[float]] = defaultdict(list)
    tiers: Dict[str, int] = defaultdict(int)

    for rec in records:
        tiers[rec.get("tier", "?")] += 1
        dists = rec.get("distances", {}) or {}
        if not dists and rec.get("axis_distances"):
            labels = rec.get("axis_labels") or [f"axis_{i}" for i in range(len(rec["axis_distances"]))]
            dists = dict(zip(labels, rec["axis_distances"]))
        h = float(rec.get("h_composite", float("nan")))
        for axis, dval in dists.items():
            distances_by_axis[axis].append(float(dval))
            h_by_axis[axis].append(h)

    summary: Dict[str, dict] = {}
    for axis, d_vals in distances_by_axis.items():
        h_vals = h_by_axis.get(axis, [])
        finite = _rolling_rhos(d_vals, h_vals)
        latest = finite[-1] if finite else None
        summary[axis] = {
            "samples": len(d_vals),
            "warm_samples": len(finite),
            "rho_latest": latest,
            "rho_mean": (sum(finite) / len(finite)) if finite else None,
            "rho_min": min(finite) if finite else None,
            "rho_max": max(finite) if finite else None,
            "d_mean": (sum(d_vals) / len(d_vals)) if d_vals else None,
            "d_min": min(d_vals) if d_vals else None,
            "d_max": max(d_vals) if d_vals else None,
        }

    return {
        "total_records": len(records),
        "tier_counts": dict(tiers),
        "per_axis": summary,
    }


def _fmt(v: Optional[float], width: int = 7) -> str:
    if v is None:
        return f"{'--':>{width}}"
    return f"{v:>{width}.4f}"


def _decision_hint(summary: Dict[str, dict]) -> Dict[str, object]:
    """Empirical gate: structured rho_latest spread -> prototype dynamic radii; flat -> keep static phi^n."""
    per = summary.get("per_axis") or {}
    latest: Dict[str, float] = {}
    for axis, s in per.items():
        v = s.get("rho_latest")
        if v is not None and math.isfinite(float(v)):
            latest[str(axis)] = float(v)

    if summary.get("total_records", 0) < 10:
        return {
            "verdict": "INSUFFICIENT_RECORDS",
            "detail": "Need more JSONL rows (try >= 32 calls per warm Pearson window).",
            "rho_span": None,
            "axes_ordered_by_rho_latest": [],
            "rho_latest": {},
        }

    if len(latest) < 3:
        return {
            "verdict": "INSUFFICIENT_WARM_AXES",
            "detail": f"Only {len(latest)} axes have finite rho_latest; need >= 3 for a spread read.",
            "rho_span": None,
            "axes_ordered_by_rho_latest": sorted(latest.keys(), key=lambda k: latest[k], reverse=True),
            "rho_latest": latest,
        }

    vals = list(latest.values())
    span = max(vals) - min(vals)
    mean_abs = sum(abs(v) for v in vals) / len(vals)
    m_abs = max(abs(v) for v in vals)
    ordered = sorted(latest.keys(), key=lambda k: latest[k], reverse=True)

    if span < 0.05 and mean_abs < 0.08:
        verdict = "LOW_SIGNAL"
        detail = "rho_latest is flat / small; static phi^n baseline is likely enough unless prod traffic disagrees."
    elif span >= 0.12 or m_abs >= 0.25:
        verdict = "STRUCTURED"
        detail = "Clear spread in rho_latest; worth a dynamic per-tongue radii experiment."
    else:
        verdict = "MARGINAL"
        detail = "Some structure but weak; extend capture window or stress more tongues before building controller."

    return {
        "verdict": verdict,
        "detail": detail,
        "rho_span": span,
        "mean_abs_rho": mean_abs,
        "max_abs_rho": m_abs,
        "axes_ordered_by_rho_latest": ordered,
        "rho_latest": latest,
    }


def _print_hint(h: Dict[str, object]) -> None:
    print()
    print("--- decision hint (empirical) ---")
    print(f"verdict: {h['verdict']}")
    print(f"detail:  {h['detail']}")
    if h.get("rho_span") is not None:
        print(f"rho_span: {float(h['rho_span']):.4f}   mean|rho|: {float(h['mean_abs_rho']):.4f}")
    if h.get("axes_ordered_by_rho_latest"):
        order = h["axes_ordered_by_rho_latest"]
        rho = h.get("rho_latest") or {}
        seq = ", ".join(f"{a}={rho.get(a, float('nan')):.4f}" for a in order)
        print(f"order (high -> low rho_latest): {seq}")


def _print_table(summary: Dict[str, dict]) -> None:
    print(f"records: {summary['total_records']}    tiers: {summary['tier_counts']}")
    print()
    header = f"{'axis':>10} {'samples':>8} {'warm':>6} {'rho_latest':>11} {'rho_mean':>10} {'rho_min':>8} {'rho_max':>8} {'d_mean':>8}"
    print(header)
    print("-" * len(header))
    rows = sorted(
        summary["per_axis"].items(),
        key=lambda kv: (-(abs(kv[1]["rho_latest"]) if kv[1]["rho_latest"] is not None else -1.0), kv[0]),
    )
    for axis, s in rows:
        print(
            f"{axis:>10} {s['samples']:>8} {s['warm_samples']:>6} "
            f"{_fmt(s['rho_latest'], 11)} {_fmt(s['rho_mean'], 10)} "
            f"{_fmt(s['rho_min'], 8)} {_fmt(s['rho_max'], 8)} "
            f"{_fmt(s['d_mean'], 8)}"
        )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--path", type=Path, default=DEFAULT_PATH)
    p.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    p.add_argument(
        "--hint",
        action="store_true",
        help="Append empirical verdict (dynamic radii vs static baseline)",
    )
    p.add_argument(
        "--hint-only",
        action="store_true",
        help="Print only the hint block (implies --hint)",
    )
    args = p.parse_args(argv)
    if args.hint_only:
        args.hint = True

    if not args.path.exists():
        print(f"no log file at {args.path}", file=sys.stderr)
        print("(set SCBE_RHO_LOG=1 in your shell and call composite_harmonic_wall to generate one)", file=sys.stderr)
        return 1

    records: List[dict] = []
    with args.path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    summary = _summarize(records)
    hint_payload = _decision_hint(summary) if args.hint else None

    if args.json:
        out: Dict[str, object] = dict(summary)
        if hint_payload is not None:
            out["decision_hint"] = hint_payload
        print(json.dumps(out, indent=2, default=str))
    elif args.hint_only and hint_payload is not None:
        _print_hint(hint_payload)
    else:
        _print_table(summary)
        if hint_payload is not None:
            _print_hint(hint_payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
