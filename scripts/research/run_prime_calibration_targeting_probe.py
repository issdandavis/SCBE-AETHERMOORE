"""Calibration targeting probe for raw primes and P(P(n)) superprime anchors.

This is the durable version of the "hide-and-recover" reframe:

    known sequence -> hide next value -> predict the corridor from prior values

It intentionally does not use row-cache fields. The tested substrate is only the
exact prime sequence:

    raw        : p_n
    superprime : p_{p_n} for prime n

The metric is not "did we solve primes"; it is whether local geometry narrows
the targeting cone below the honest wheel + PNT / baseline residue structure.
"""

from __future__ import annotations

import argparse
import bisect
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from prime_truth_oracle import prime_stream
except ModuleNotFoundError:  # pragma: no cover - package import path for tests
    from scripts.research.prime_truth_oracle import prime_stream


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "prime_calibration_targeting_probe"
WHEEL_210_ALLOWED = tuple(r for r in range(210) if math.gcd(r, 210) == 1)


@dataclass(frozen=True)
class WindowMetrics:
    label: str
    sequence: str
    lower_value: int
    upper_value: int
    sample_count: int
    mean_gap: float
    median_gap: float
    stdev_gap: float
    pnt_half_log2_window: int
    pnt_wheel_candidates_mid: int
    pnt_target_inside_rate: float
    empirical_window: int
    empirical_wheel_candidates_mid: int
    empirical_target_inside_rate: float
    rolling_global_rmse: float
    local_last3_rmse: float
    local_minus_global_rmse: float
    lag1_gap_corr: float
    same_mod6_rate: float
    same_mod30_rate: float
    transition_count: int


@dataclass(frozen=True)
class ModelResult:
    model: str
    rmse: float
    delta_vs_density: float | None
    feature_count: int
    coefficients: dict[str, float]


def simple_sieve(limit: int) -> list[int]:
    if limit < 2:
        return []
    flags = bytearray(b"\x01") * (limit + 1)
    flags[0:2] = b"\x00\x00"
    root = math.isqrt(limit)
    for value in range(2, root + 1):
        if flags[value]:
            start = value * value
            flags[start : limit + 1 : value] = b"\x00" * (
                ((limit - start) // value) + 1
            )
    return [index for index, flag in enumerate(flags) if flag]


def p_p_n_for_prime_n_sequence(limit: int) -> list[int]:
    """Return p_{p_n} for every prime n that can be resolved by primes <= limit."""
    primes = simple_sieve(limit)
    rows: list[int] = []
    prime_count = len(primes)
    for n in primes:
        if n > prime_count:
            break
        p_n = primes[n - 1]
        if p_n > prime_count:
            break
        rows.append(primes[p_n - 1])
    return rows


def nth_prime_upper_bound(n: int) -> int:
    if n < 1:
        raise ValueError("n must be positive")
    small = (2, 3, 5, 7, 11)
    if n <= len(small):
        return small[n - 1]
    x = float(n)
    return int(math.ceil(x * (math.log(x) + math.log(math.log(x))) + 32.0))


def p_p_n_for_prime_n_by_index_limit(index_limit: int) -> list[int]:
    """Return p_{p_n} for prime n while p_n <= index_limit.

    This is the "superprime anchors <= index limit" interpretation used by the
    density-control steelman: the inner index p_n is bounded, while the outer
    anchor value p_{p_n} can be much larger.
    """
    upper = nth_prime_upper_bound(index_limit)
    primes = simple_sieve(upper)
    while len(primes) < index_limit:
        upper = int(upper * 1.25) + 1024
        primes = simple_sieve(upper)

    rows: list[int] = []
    for n in primes:
        if n > len(primes):
            break
        p_n = primes[n - 1]
        if p_n > index_limit:
            break
        rows.append(primes[p_n - 1])
    return rows


def raw_prime_sequence_around(start: int, count: int) -> list[int]:
    return prime_stream(start, count)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def stdev(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    mu = mean([float(value) for value in values])
    return math.sqrt(sum((value - mu) ** 2 for value in values) / (len(values) - 1))


def rmse(errors: list[float]) -> float:
    if not errors:
        return 0.0
    return math.sqrt(sum(error * error for error in errors) / len(errors))


def _solve_linear_system(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Small dense Gaussian solver for ridge normal equations."""
    n = len(values)
    aug = [row[:] + [values[index]] for index, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1e-12:
            continue
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [value / scale for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if abs(factor) < 1e-12:
                continue
            aug[row] = [
                current - factor * pivot_value
                for current, pivot_value in zip(aug[row], aug[col])
            ]
    return [aug[row][-1] for row in range(n)]


def _ridge_fit_predict(
    train_x: list[list[float]],
    train_y: list[float],
    test_x: list[list[float]],
    alpha: float = 1.0,
) -> tuple[list[float], list[float], list[float], list[float]]:
    """Fit ridge with train-only standardization and an unpenalized intercept."""
    if not train_x:
        return [], [], [], []
    feature_count = len(train_x[0])
    means: list[float] = []
    scales: list[float] = []
    for col in range(feature_count):
        values = [row[col] for row in train_x]
        mu = mean(values)
        var = sum((value - mu) ** 2 for value in values) / max(1, len(values) - 1)
        scale = math.sqrt(var) or 1.0
        means.append(mu)
        scales.append(scale)

    def transform(rows: list[list[float]]) -> list[list[float]]:
        return [
            [1.0]
            + [(row[col] - means[col]) / scales[col] for col in range(feature_count)]
            for row in rows
        ]

    tx = transform(train_x)
    vx = transform(test_x)
    width = feature_count + 1
    xtx = [[0.0 for _ in range(width)] for _ in range(width)]
    xty = [0.0 for _ in range(width)]
    for row, target in zip(tx, train_y):
        for i in range(width):
            xty[i] += row[i] * target
            for j in range(width):
                xtx[i][j] += row[i] * row[j]
    for i in range(1, width):
        xtx[i][i] += alpha
    beta = _solve_linear_system(xtx, xty)
    preds = [sum(coef * value for coef, value in zip(beta, row)) for row in vx]
    return preds, beta, means, scales


def pearson(left: list[int], right: list[int]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    l_mu = mean([float(value) for value in left])
    r_mu = mean([float(value) for value in right])
    numerator = sum((a - l_mu) * (b - r_mu) for a, b in zip(left, right))
    l_den = math.sqrt(sum((a - l_mu) ** 2 for a in left))
    r_den = math.sqrt(sum((b - r_mu) ** 2 for b in right))
    denom = l_den * r_den
    return numerator / denom if denom else 0.0


def superprime_sequence_up_to(max_value: int) -> list[int]:
    return [
        value for value in p_p_n_for_prime_n_sequence(max_value) if value <= max_value
    ]


def _phase_features(value: int, modulus: int) -> tuple[float, float]:
    angle = 2.0 * math.pi * (value % modulus) / modulus
    return math.sin(angle), math.cos(angle)


def density_control_rows(seq: list[int]) -> tuple[list[dict[str, float]], list[float]]:
    """Build next-gap rows from prior-only features.

    Row i predicts gap(seq[i], seq[i+1]) using seq[i] and earlier gaps only.
    """
    gaps = [right - left for left, right in zip(seq, seq[1:])]
    rows: list[dict[str, float]] = []
    targets: list[float] = []
    for index in range(3, len(gaps)):
        p = seq[index]
        g1 = float(gaps[index - 1])
        g2 = float(gaps[index - 2])
        g3 = float(gaps[index - 3])
        s30, c30 = _phase_features(p, 30)
        s210, c210 = _phase_features(p, 210)
        rows.append(
            {
                "log_p": math.log(p),
                "g1": g1,
                "g2": g2,
                "g3": g3,
                "rollmean3": (g1 + g2 + g3) / 3.0,
                "curv12": g1 - g2,
                "curv23": g2 - g3,
                "ratio12": g1 / max(1.0, g2),
                "ratio23": g2 / max(1.0, g3),
                "s30": s30,
                "c30": c30,
                "s210": s210,
                "c210": c210,
            }
        )
        targets.append(float(gaps[index]))
    return rows, targets


def _matrix(rows: list[dict[str, float]], features: list[str]) -> list[list[float]]:
    return [[row[name] for name in features] for row in rows]


def run_density_control_steelman(
    max_value: int | None = None,
    index_limit: int | None = None,
    split_fraction: float = 0.70,
) -> dict:
    if index_limit is not None:
        seq = p_p_n_for_prime_n_by_index_limit(index_limit)
        sequence_cutoff = {"kind": "inner_index_limit", "value": index_limit}
    elif max_value is not None:
        seq = superprime_sequence_up_to(max_value)
        sequence_cutoff = {"kind": "outer_value_limit", "value": max_value}
    else:
        raise ValueError("either max_value or index_limit is required")
    rows, targets = density_control_rows(seq)
    split = max(1, min(len(rows) - 1, int(split_fraction * len(rows))))
    train_rows = rows[:split]
    test_rows = rows[split:]
    train_y = targets[:split]
    test_y = targets[split:]
    flat_pred = mean(train_y)
    flat_rmse = rmse([actual - flat_pred for actual in test_y])

    feature_sets = {
        "density_only_logp": ["log_p"],
        "density_plus_all_local": [
            "log_p",
            "g1",
            "g2",
            "g3",
            "rollmean3",
            "curv12",
            "curv23",
            "ratio12",
            "ratio23",
            "s30",
            "c30",
            "s210",
            "c210",
        ],
        "density_plus_local_gaps": [
            "log_p",
            "g1",
            "g2",
            "g3",
            "rollmean3",
            "curv12",
            "curv23",
            "ratio12",
            "ratio23",
        ],
        "density_plus_residue_phase": ["log_p", "s30", "c30", "s210", "c210"],
        "local_geometry_without_density": [
            "g1",
            "g2",
            "g3",
            "rollmean3",
            "curv12",
            "curv23",
            "ratio12",
            "ratio23",
            "s30",
            "c30",
            "s210",
            "c210",
        ],
    }

    results: list[ModelResult] = [
        ModelResult(
            model="flat_global_mean_wrong_baseline",
            rmse=round(flat_rmse, 6),
            delta_vs_density=None,
            feature_count=0,
            coefficients={},
        )
    ]
    density_rmse: float | None = None
    for name, features in feature_sets.items():
        preds, beta, _means, _scales = _ridge_fit_predict(
            _matrix(train_rows, features), train_y, _matrix(test_rows, features)
        )
        model_rmse = rmse([actual - pred for actual, pred in zip(test_y, preds)])
        if name == "density_only_logp":
            density_rmse = model_rmse
        delta = None if density_rmse is None else model_rmse - density_rmse
        coefficients = {"intercept": round(beta[0], 6)}
        coefficients.update(
            {feature: round(coef, 6) for feature, coef in zip(features, beta[1:])}
        )
        results.append(
            ModelResult(
                model=name,
                rmse=round(model_rmse, 6),
                delta_vs_density=round(delta, 6) if delta is not None else None,
                feature_count=len(features),
                coefficients=coefficients,
            )
        )

    return {
        "schema": "prime_calibration_density_control_steelman_v1",
        "sequence": "p_p_n_for_prime_n",
        "sequence_cutoff": sequence_cutoff,
        "max_value": max_value,
        "index_limit": index_limit,
        "first_value": seq[0] if seq else None,
        "last_value": seq[-1] if seq else None,
        "sequence_count": len(seq),
        "row_count": len(rows),
        "train_count": len(train_rows),
        "test_count": len(test_rows),
        "split_fraction": split_fraction,
        "target": "next_gap",
        "results": [asdict(item) for item in results],
    }


def wheel_candidate_count(start: int, width: int, modulus: int = 210) -> int:
    if width <= 0:
        return 0
    end = start + width
    full_cycles, remainder = divmod(width, modulus)
    count = full_cycles * len(WHEEL_210_ALLOWED)
    start_residue = start % modulus
    for offset in range(remainder):
        if (start_residue + offset) % modulus in WHEEL_210_ALLOWED:
            count += 1
    # Include 2, 3, 5, 7 if the interval is very small and crosses them.
    for special in (2, 3, 5, 7):
        if start <= special < end and special % modulus not in WHEEL_210_ALLOWED:
            count += 1
    return count


def target_inside_rate(seq: list[int], window_width: int) -> float:
    if len(seq) < 2 or window_width <= 0:
        return 0.0
    hits = 0
    for cur, nxt in zip(seq, seq[1:]):
        if 0 < nxt - cur <= window_width:
            hits += 1
    return hits / (len(seq) - 1)


def rolling_gap_errors(gaps: list[int], history: int = 3) -> tuple[float, float]:
    global_errors: list[float] = []
    local_errors: list[float] = []
    for index in range(history, len(gaps)):
        actual = float(gaps[index])
        prior = [float(value) for value in gaps[:index]]
        local = [float(value) for value in gaps[index - history : index]]
        global_errors.append(actual - mean(prior))
        local_errors.append(actual - mean(local))
    return rmse(global_errors), rmse(local_errors)


def analyze_window(sequence_name: str, label: str, seq: list[int]) -> WindowMetrics:
    if len(seq) < 5:
        raise ValueError("sequence window must contain at least 5 values")
    gaps = [right - left for left, right in zip(seq, seq[1:])]
    gap_mean = mean([float(value) for value in gaps])
    gap_stdev = stdev(gaps)
    midpoint = seq[len(seq) // 2]
    pnt_width = max(1, int(math.ceil((math.log(midpoint) ** 2) / 2.0)))
    empirical_width = max(1, int(math.ceil(gap_mean + (2.0 * gap_stdev))))
    global_rmse, local_rmse = rolling_gap_errors(gaps)
    transitions = len(seq) - 1

    return WindowMetrics(
        label=label,
        sequence=sequence_name,
        lower_value=seq[0],
        upper_value=seq[-1],
        sample_count=len(seq),
        mean_gap=round(gap_mean, 6),
        median_gap=round(median(gaps), 6),
        stdev_gap=round(gap_stdev, 6),
        pnt_half_log2_window=pnt_width,
        pnt_wheel_candidates_mid=wheel_candidate_count(midpoint + 1, pnt_width),
        pnt_target_inside_rate=round(target_inside_rate(seq, pnt_width), 6),
        empirical_window=empirical_width,
        empirical_wheel_candidates_mid=wheel_candidate_count(
            midpoint + 1, empirical_width
        ),
        empirical_target_inside_rate=round(target_inside_rate(seq, empirical_width), 6),
        rolling_global_rmse=round(global_rmse, 6),
        local_last3_rmse=round(local_rmse, 6),
        local_minus_global_rmse=round(local_rmse - global_rmse, 6),
        lag1_gap_corr=round(pearson(gaps[:-1], gaps[1:]), 6),
        same_mod6_rate=round(
            sum(1 for a, b in zip(seq, seq[1:]) if a % 6 == b % 6) / transitions, 6
        ),
        same_mod30_rate=round(
            sum(1 for a, b in zip(seq, seq[1:]) if a % 30 == b % 30) / transitions, 6
        ),
        transition_count=transitions,
    )


def windows_from_sequence(
    seq: list[int], scales: list[int], counts: list[int]
) -> list[tuple[str, list[int]]]:
    windows: list[tuple[str, list[int]]] = []
    for scale, count in zip(scales, counts):
        start = bisect.bisect_left(seq, scale)
        if start >= len(seq):
            start = max(0, len(seq) - count)
        if start + count > len(seq):
            start = max(0, len(seq) - count)
        window = seq[start : start + count]
        if len(window) >= 5:
            windows.append((f"~{scale:g}", window))
    return windows


def run_raw(scales: list[int], counts: list[int]) -> list[WindowMetrics]:
    metrics: list[WindowMetrics] = []
    for scale, count in zip(scales, counts):
        seq = raw_prime_sequence_around(scale, count)
        metrics.append(analyze_window("raw_primes", f"~{scale:g}", seq))
    return metrics


def run_superprime(
    limit: int, scales: list[int], counts: list[int]
) -> tuple[list[WindowMetrics], int]:
    seq = p_p_n_for_prime_n_sequence(limit)
    return [
        analyze_window("p_p_n_for_prime_n", label, window)
        for label, window in windows_from_sequence(seq, scales, counts)
    ], len(seq)


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Prime Calibration Targeting Probe",
        "",
        f"Mode: `{report['mode']}`",
        f"Generated sequence count: `{report.get('generated_sequence_count', 'n/a')}`",
        "",
        (
            "| Scale | N | Range | Mean gap | Median gap | Gap stdev | PNT wheel candidates | "
            "PNT hit rate | Empirical candidates | Empirical hit rate | Global RMSE | "
            "Local3 RMSE | Local-Global | Gap corr | same mod6 | same mod30 |"
        ),
        (
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: | ---: | ---: | ---: |"
        ),
    ]
    for item in report["windows"]:
        lines.append(
            (
                "| {label} | {sample_count} | {lower_value}-{upper_value} | {mean_gap:.3f} | "
                "{median_gap:.3f} | {stdev_gap:.3f} | {pnt_wheel_candidates_mid} | "
                "{pnt_target_inside_rate:.3f} | {empirical_wheel_candidates_mid} | "
                "{empirical_target_inside_rate:.3f} | {rolling_global_rmse:.3f} | "
                "{local_last3_rmse:.3f} | {local_minus_global_rmse:.3f} | "
                "{lag1_gap_corr:.3f} | {same_mod6_rate:.3f} | {same_mod30_rate:.3f} |"
            ).format(**item)
        )
    lines.extend(
        [
            "",
            "Interpretation guardrails:",
            "",
            "- PNT wheel candidates are the free wheel+PNT cone, not a discovery.",
            "- Empirical candidates use mean + 2 stdev of this sequence window; useful for calibration, not a theorem.",
            "- Local3 beats global only if `Local-Global` is negative.",
            "- Residue rates are descriptive; LO-S is already known for ordinary consecutive primes.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_density_control_markdown(report: dict, path: Path) -> None:
    cutoff = report["sequence_cutoff"]
    lines = [
        "# Superprime Density-Control Steelman",
        "",
        f"Sequence: `{report['sequence']}`",
        f"Cutoff: `{cutoff['kind']}={cutoff['value']}`",
        f"Value range: `{report['first_value']}` to `{report['last_value']}`",
        f"Rows: `{report['row_count']}` (`{report['train_count']}` train / `{report['test_count']}` test)",
        "",
        "| Model | Features | RMSE | Delta vs density |",
        "| --- | ---: | ---: | ---: |",
    ]
    for result in report["results"]:
        delta = result["delta_vs_density"]
        lines.append(
            "| {model} | {feature_count} | {rmse:.3f} | {delta} |".format(
                model=result["model"],
                feature_count=result["feature_count"],
                rmse=result["rmse"],
                delta="" if delta is None else f"{delta:.3f}",
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- `flat_global_mean_wrong_baseline` is intentionally included as the trap.",
            "- `density_only_logp` is the honest density baseline for a time-ordered split.",
            "- Local geometry only counts if it improves materially over `density_only_logp`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_csv_ints(raw: str) -> list[int]:
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("raw", "superprime"), default="superprime")
    parser.add_argument(
        "--density-control-steelman",
        action="store_true",
        help="run superprime ridge steelman against an honest log-density baseline",
    )
    parser.add_argument(
        "--limit", type=int, default=100_000_000, help="sieve limit for superprime mode"
    )
    parser.add_argument("--max-value", type=int, default=1_500_000)
    parser.add_argument(
        "--index-limit",
        type=int,
        default=None,
        help="for --density-control-steelman, bound inner p_n index instead of outer value",
    )
    parser.add_argument("--scales", default="100,100000,100000000")
    parser.add_argument("--counts", default="40,3000,4000")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.density_control_steelman:
        report = run_density_control_steelman(
            max_value=args.max_value if args.index_limit is None else None,
            index_limit=args.index_limit,
        )
        json_path = out_dir / "superprime_density_control_latest.json"
        md_path = out_dir / "superprime_density_control_latest.md"
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        write_density_control_markdown(report, md_path)
        print(f"report -> {json_path}")
        print(f"markdown -> {md_path}")
        density = next(
            item for item in report["results"] if item["model"] == "density_only_logp"
        )
        for item in report["results"]:
            delta = item["delta_vs_density"]
            print(
                "{model}: rmse={rmse:.3f} delta_vs_density={delta}".format(
                    model=item["model"],
                    rmse=item["rmse"],
                    delta="n/a" if delta is None else f"{delta:.3f}",
                )
            )
        print(f"honest density baseline rmse={density['rmse']:.3f}")
        return 0

    scales = parse_csv_ints(args.scales)
    counts = parse_csv_ints(args.counts)
    if len(scales) != len(counts):
        raise ValueError("--scales and --counts must have the same length")

    if args.mode == "raw":
        metrics = run_raw(scales, counts)
        generated_count: int | str = "streamed"
    else:
        metrics, generated_count = run_superprime(args.limit, scales, counts)

    report = {
        "schema": "prime_calibration_targeting_probe_v1",
        "mode": args.mode,
        "limit": args.limit if args.mode == "superprime" else None,
        "scales": scales,
        "counts": counts,
        "generated_sequence_count": generated_count,
        "windows": [asdict(item) for item in metrics],
    }

    json_path = out_dir / f"{args.mode}_latest.json"
    md_path = out_dir / f"{args.mode}_latest.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    print(f"report -> {json_path}")
    print(f"markdown -> {md_path}")
    for item in report["windows"]:
        print(
            "{label}: N={sample_count} mean_gap={mean_gap:.3f} pnt_hit={pnt_target_inside_rate:.3f} "
            "emp_hit={empirical_target_inside_rate:.3f} global_rmse={rolling_global_rmse:.3f} "
            "local3_rmse={local_last3_rmse:.3f} same_mod6={same_mod6_rate:.3f}".format(
                **item
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
