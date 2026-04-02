#!/usr/bin/env python3
"""
Compare harmonic exponent families against SCBE drift thresholds.

This script is evidence-gathering only. It does NOT replace the canonical
Layer 12 formula. It compares the retired exponent family

    H_alpha(d, R) = R ** (d ** alpha)

across alpha values that have been proposed in design discussions:
    1.5, phi, sqrt(2), 2, e

The benchmark surface uses the current canonical governance thresholds from
`docs/specs/LAYER_12_CANONICAL_FORMULA.md` as the reference labels, then asks:

    "Which exponent family best separates ALLOW from collapse-style outcomes
     (ESCALATE / DENY) on the same drift inputs?"
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from symphonic_cipher.qasi_core import decision_from_risk as legacy_decision_from_risk


PHI = (1.0 + math.sqrt(5.0)) / 2.0
EXPONENTS: Dict[str, float] = {
    "1.5": 1.5,
    "phi": PHI,
    "sqrt2": math.sqrt(2.0),
    "2": 2.0,
    "e": math.e,
}

CANONICAL_ALLOW = 0.30
CANONICAL_QUARANTINE = 0.70
CANONICAL_ESCALATE = 0.90


@dataclass(frozen=True)
class DriftCase:
    d_h: float
    phase_deviation: float
    behavioral_risk: float
    canonical_decision: str


@dataclass(frozen=True)
class AlphaMetrics:
    alpha_name: str
    alpha_value: float
    pairwise_auc_allow_vs_collapse: float
    quantile_margin_allow_vs_collapse: float
    exact_three_way_accuracy: float
    binary_allow_vs_collapse_accuracy: float
    collapse_recall: float
    allow_precision: float
    sample_count: int
    binary_sample_count: int
    confusion_three_way: Dict[str, Dict[str, int]]


def linspace(start: float, stop: float, steps: int) -> List[float]:
    if steps <= 1:
        return [start]
    width = stop - start
    return [start + width * (idx / (steps - 1)) for idx in range(steps)]


def quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def canonical_h_score(d_h: float, phase_deviation: float) -> float:
    return 1.0 / (1.0 + PHI * d_h + 2.0 * phase_deviation)


def canonical_decision(behavioral_risk: float, d_h: float, phase_deviation: float) -> str:
    adjusted = behavioral_risk / canonical_h_score(d_h, phase_deviation)
    if adjusted < CANONICAL_ALLOW:
        return "ALLOW"
    if adjusted < CANONICAL_QUARANTINE:
        return "QUARANTINE"
    if adjusted < CANONICAL_ESCALATE:
        return "ESCALATE"
    return "DENY"


def to_three_way(label: str) -> str:
    if label == "ALLOW":
        return "ALLOW"
    if label == "QUARANTINE":
        return "QUARANTINE"
    return "DENY"


def to_binary_allow_vs_collapse(label: str) -> str | None:
    if label == "ALLOW":
        return "ALLOW"
    if label in {"ESCALATE", "DENY"}:
        return "COLLAPSE"
    return None


def harmonic_wall_alpha(d_h: float, r_base: float, alpha: float, max_log: float = 700.0) -> float:
    if d_h <= 0.0:
        return 1.0
    log_h = math.log(r_base) * (d_h**alpha)
    return math.exp(min(log_h, max_log))


def risk_prime_alpha(behavioral_risk: float, d_h: float, alpha: float, r_base: float) -> float:
    return behavioral_risk * harmonic_wall_alpha(d_h=d_h, r_base=r_base, alpha=alpha)


def pairwise_auc(allow_scores: Sequence[float], collapse_scores: Sequence[float]) -> float:
    if not allow_scores or not collapse_scores:
        return float("nan")
    wins = 0.0
    total = 0
    for allow_score in allow_scores:
        for collapse_score in collapse_scores:
            total += 1
            if allow_score < collapse_score:
                wins += 1.0
            elif allow_score == collapse_score:
                wins += 0.5
    return wins / total


def build_cases(
    d_steps: int = 31,
    pd_steps: int = 11,
    risk_steps: int = 19,
    d_max: float = 5.0,
    phase_max: float = 0.5,
    risk_min: float = 0.05,
    risk_max: float = 0.95,
) -> List[DriftCase]:
    cases: List[DriftCase] = []
    for d_h in linspace(0.0, d_max, d_steps):
        for phase_deviation in linspace(0.0, phase_max, pd_steps):
            for behavioral_risk in linspace(risk_min, risk_max, risk_steps):
                cases.append(
                    DriftCase(
                        d_h=d_h,
                        phase_deviation=phase_deviation,
                        behavioral_risk=behavioral_risk,
                        canonical_decision=canonical_decision(behavioral_risk, d_h, phase_deviation),
                    )
                )
    return cases


def evaluate_alpha(cases: Iterable[DriftCase], alpha_name: str, alpha_value: float, r_base: float) -> AlphaMetrics:
    confusion: Dict[str, Dict[str, int]] = {
        "ALLOW": {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0},
        "QUARANTINE": {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0},
        "DENY": {"ALLOW": 0, "QUARANTINE": 0, "DENY": 0},
    }

    allow_scores: List[float] = []
    collapse_scores: List[float] = []
    binary_total = 0
    binary_correct = 0
    collapse_true = 0
    collapse_hit = 0
    allow_pred = 0
    allow_precision_hits = 0
    total = 0
    exact = 0

    for case in cases:
        total += 1
        risk_prime = risk_prime_alpha(
            behavioral_risk=case.behavioral_risk,
            d_h=case.d_h,
            alpha=alpha_value,
            r_base=r_base,
        )
        predicted_three = legacy_decision_from_risk(risk_prime)
        canonical_three = to_three_way(case.canonical_decision)
        confusion[canonical_three][predicted_three] += 1
        if predicted_three == canonical_three:
            exact += 1

        binary_truth = to_binary_allow_vs_collapse(case.canonical_decision)
        if binary_truth == "ALLOW":
            allow_scores.append(risk_prime)
        elif binary_truth == "COLLAPSE":
            collapse_scores.append(risk_prime)

        if binary_truth is not None:
            binary_total += 1
            predicted_binary = "ALLOW" if predicted_three == "ALLOW" else "COLLAPSE"
            if predicted_binary == binary_truth:
                binary_correct += 1
            if binary_truth == "COLLAPSE":
                collapse_true += 1
                if predicted_binary == "COLLAPSE":
                    collapse_hit += 1
            if predicted_binary == "ALLOW":
                allow_pred += 1
                if binary_truth == "ALLOW":
                    allow_precision_hits += 1

    collapse_recall = collapse_hit / collapse_true if collapse_true else float("nan")
    allow_precision = allow_precision_hits / allow_pred if allow_pred else float("nan")
    auc = pairwise_auc(allow_scores, collapse_scores)
    margin = quantile(collapse_scores, 0.10) - quantile(allow_scores, 0.90)
    return AlphaMetrics(
        alpha_name=alpha_name,
        alpha_value=alpha_value,
        pairwise_auc_allow_vs_collapse=auc,
        quantile_margin_allow_vs_collapse=margin,
        exact_three_way_accuracy=exact / total if total else float("nan"),
        binary_allow_vs_collapse_accuracy=binary_correct / binary_total if binary_total else float("nan"),
        collapse_recall=collapse_recall,
        allow_precision=allow_precision,
        sample_count=total,
        binary_sample_count=binary_total,
        confusion_three_way=confusion,
    )


def print_human_report(metrics: Sequence[AlphaMetrics], r_base: float, case_count: int) -> None:
    print("Harmonic Exponent Comparison")
    print("===========================")
    print("Mode: evidence-gathering only for retired R^(d^alpha) family")
    print(f"Reference labels: canonical Layer 12 formula with phi coefficient and L13 thresholds")
    print(f"Benchmark cases: {case_count} grid points")
    print(f"Shared base ratio R: {r_base:.6f}")
    print("")
    print(
        f"{'alpha':<8} {'auc':>8} {'margin':>10} {'3way_acc':>10} {'bin_acc':>9} {'collapse_rec':>13} {'allow_prec':>11}"
    )
    for item in metrics:
        print(
            f"{item.alpha_name:<8} "
            f"{item.pairwise_auc_allow_vs_collapse:>8.4f} "
            f"{item.quantile_margin_allow_vs_collapse:>10.4f} "
            f"{item.exact_three_way_accuracy:>10.4f} "
            f"{item.binary_allow_vs_collapse_accuracy:>9.4f} "
            f"{item.collapse_recall:>13.4f} "
            f"{item.allow_precision:>11.4f}"
        )

    best = max(
        metrics,
        key=lambda item: (
            item.pairwise_auc_allow_vs_collapse,
            item.quantile_margin_allow_vs_collapse,
            item.binary_allow_vs_collapse_accuracy,
        ),
    )
    print("")
    print(
        "Best by allow-vs-collapse separation: "
        f"{best.alpha_name} (alpha={best.alpha_value:.6f}, auc={best.pairwise_auc_allow_vs_collapse:.4f})"
    )
    print("")
    print("Note: this does not overrule the canonical formula. It only ranks the exponent family against the")
    print("current drift labels so you can decide whether phi earns a place by measurement instead of analogy.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r-base", type=float, default=1.5, help="Shared R base for the retired exponent family")
    parser.add_argument("--d-steps", type=int, default=31, help="Number of distance grid steps")
    parser.add_argument("--pd-steps", type=int, default=11, help="Number of phase deviation grid steps")
    parser.add_argument("--risk-steps", type=int, default=19, help="Number of behavioral risk grid steps")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a table")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = build_cases(d_steps=args.d_steps, pd_steps=args.pd_steps, risk_steps=args.risk_steps)
    metrics = [evaluate_alpha(cases, name, value, args.r_base) for name, value in EXPONENTS.items()]
    metrics = sorted(
        metrics,
        key=lambda item: (
            item.pairwise_auc_allow_vs_collapse,
            item.quantile_margin_allow_vs_collapse,
            item.binary_allow_vs_collapse_accuracy,
        ),
        reverse=True,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "r_base": args.r_base,
                    "case_count": len(cases),
                    "metrics": [asdict(item) for item in metrics],
                },
                indent=2,
            )
        )
    else:
        print_human_report(metrics, args.r_base, len(cases))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
