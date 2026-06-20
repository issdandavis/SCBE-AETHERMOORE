"""Prime-Vibration Edge System v3 — corrected-formula experiment.

Executable reference implementation built from the formula verification report
(website vs. spec). Every formula here is the SPEC-CORRECT form, including the
two critical corrections the report found:

1. Nonresonance margin Delta(S, B) uses the l-infinity coefficient bound
   (max_p |b_p| <= B, Baker/Matveev convention), NOT the l1 bound the website
   displayed. The two norms define different optimization problems; this module
   computes both to demonstrate they disagree.
2. Forward encoding and Lane B drift are SEPARATE formulas. The website's
   hybrid `log n = sum k * alpha * log p` asserts log n = alpha * log n (false
   for alpha != 1). Correct pair:
       forward encoding:  log n = sum_{p in S} v_p(n) * log p      (no alpha)
       Lane B drift:      omega_n = alpha * log n

Formula reference (spec notation):
    Lane A lock:        f_p = p * f0                       (prime p)
    GCD repeat:         T_repeat = T / gcd(a, b)
    LCM overtone:       f_common = lcm(a, b) * f0
    Lane B drift:       omega_p = alpha * log p             (omega, not f^(B))
    Factorization:      n = prod_{p in S} p^{v_p(n)}
    Composite drift:    omega_n = alpha * sum v_p(n) log p
    Nonresonance:       Delta(S, B) = min_{0 < max|b_p| <= B} |sum b_p log p|
    Certificate:        Delta(S, B) > eps_num + eps_sensor
    Canary products:    p + q, |p - q|, 2p (2nd order, even bins); 2p +/- q (3rd)
    Fermat lane:        F_k = 2^(2^k) + 1, |(Z/F_k Z)^x| = F_k - 1 = 2^(2^k)
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from dataclasses import asdict, dataclass
from math import gcd, lcm
from typing import Sequence

DEFAULT_SUPPORT: tuple[int, ...] = (2, 3, 5)
DEFAULT_BOUND = 2
F4 = 65537
F4_GROUP_ORDER = 65536


# ---------------------------------------------------------------------------
# Lane A — integer frequency locks
# ---------------------------------------------------------------------------


def lane_a_frequency(p: int, f0: float) -> float:
    """Lane A lock frequency f_p = p * f0 for a prime edge address p."""
    return p * f0


def repeat_period(a: int, b: int, base_period: float) -> float:
    """GCD repeat period T_repeat = T / gcd(a, b) of two locked edges."""
    return base_period / gcd(a, b)


def common_overtone(a: int, b: int, f0: float) -> float:
    """LCM common overtone f_common = lcm(a, b) * f0 of two locked edges."""
    return lcm(a, b) * f0


# ---------------------------------------------------------------------------
# Lane B — logarithmic drift
# ---------------------------------------------------------------------------


def prime_valuations(n: int) -> dict[int, int]:
    """p-adic valuations of n: returns {p: v_p(n)} with n = prod p^v_p(n).

    Args:
        n: Integer >= 2.

    Returns:
        Mapping of each prime factor p to its exponent v_p(n).
    """
    if n < 2:
        raise ValueError(f"n must be >= 2, got {n}")
    valuations: dict[int, int] = {}
    remainder = n
    factor = 2
    while factor * factor <= remainder:
        while remainder % factor == 0:
            valuations[factor] = valuations.get(factor, 0) + 1
            remainder //= factor
        factor += 1
    if remainder > 1:
        valuations[remainder] = valuations.get(remainder, 0) + 1
    return valuations


def lane_b_frequency(p: int, alpha: float) -> float:
    """Lane B drift frequency omega_p = alpha * log p (spec's omega notation)."""
    return alpha * math.log(p)


def forward_encoding(n: int) -> float:
    """Forward encoding log n = sum_{p} v_p(n) * log p — deliberately NO alpha.

    The verification report's critical finding #2: mixing alpha into this
    identity asserts log n = alpha * log n, which is false for alpha != 1.
    """
    return sum(v * math.log(p) for p, v in prime_valuations(n).items())


def lane_b_drift(n: int, alpha: float) -> float:
    """Composite Lane B drift omega_n = alpha * log n = alpha * sum v_p(n) log p."""
    return alpha * forward_encoding(n)


# ---------------------------------------------------------------------------
# Nonresonance certificate Delta(S, B)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeltaResult:
    """Minimum |sum b_p log p| with its arg-min vector and the norm used."""

    value: float
    vector: tuple[int, ...]
    norm: str


def _coefficient_vectors(size: int, bound: int, norm: str) -> "itertools.product":
    if bound < 1:
        raise ValueError(f"bound must be >= 1, got {bound}")
    if norm not in ("linf", "l1"):
        raise ValueError(f"norm must be 'linf' or 'l1', got {norm!r}")
    return itertools.product(range(-bound, bound + 1), repeat=size)


def delta_certificate(support: Sequence[int], bound: int, norm: str = "linf") -> DeltaResult:
    """Compute Delta(S, B) = min over nonzero integer vectors of |sum b_p log p|.

    Args:
        support: Prime support S.
        bound: Coefficient bound B.
        norm: 'linf' (spec-correct: max |b_p| <= B) or 'l1' (the website's
            incorrect sum |b_p| <= B), kept to demonstrate the difference.

    Returns:
        DeltaResult with the minimum value and a vector attaining it.
    """
    logs = [math.log(p) for p in support]
    best_value = math.inf
    best_vector: tuple[int, ...] = ()
    for vector in _coefficient_vectors(len(support), bound, norm):
        if not any(vector):
            continue
        if norm == "l1" and sum(abs(c) for c in vector) > bound:
            continue
        value = abs(sum(c * lg for c, lg in zip(vector, logs)))
        if value < best_value:
            best_value = value
            best_vector = vector
    return DeltaResult(value=best_value, vector=best_vector, norm=norm)


def numerical_epsilon(support: Sequence[int], bound: int) -> float:
    """Conservative roundoff budget for the Delta(S, B) sum in float64."""
    return len(support) * bound * max(math.log(p) for p in support) * 2.0**-50


def certificate_holds(support: Sequence[int], bound: int, eps_sensor: float) -> bool:
    """Certificate inequality Delta(S, B) > eps_num + eps_sensor (l-inf norm)."""
    delta = delta_certificate(support, bound, norm="linf")
    return delta.value > numerical_epsilon(support, bound) + eps_sensor


def recover_coefficients(target: float, support: Sequence[int], bound: int, tol: float) -> tuple[int, ...] | None:
    """Bounded-support recovery: find b with |sum b_p log p - target| < tol.

    Uniqueness is guaranteed when tol < Delta(S, 2B) / 2, since two distinct
    candidates differ by a nonzero vector with max coefficient <= 2B.

    Returns:
        The recovered coefficient vector, or None if nothing lands within tol.
    """
    logs = [math.log(p) for p in support]
    for vector in _coefficient_vectors(len(support), bound, "linf"):
        if abs(sum(c * lg for c, lg in zip(vector, logs)) - target) < tol:
            return vector
    return None


# ---------------------------------------------------------------------------
# Canary distortion products
# ---------------------------------------------------------------------------


def second_order_products(p: int, q: int) -> tuple[int, int, int]:
    """Second-order distortion products (p + q, |p - q|, 2p) — all even bins."""
    return (p + q, abs(p - q), 2 * p)


def third_order_products(p: int, q: int) -> tuple[int, int]:
    """Third-order distortion products (2p + q, 2p - q) — odd bins."""
    return (2 * p + q, 2 * p - q)


# ---------------------------------------------------------------------------
# Fermat / NTT lane
# ---------------------------------------------------------------------------


def fermat_number(k: int) -> int:
    """Fermat number F_k = 2^(2^k) + 1."""
    return 2 ** (2**k) + 1


def multiplicative_group_order(k: int) -> int:
    """Order of (Z/F_k Z)^x = F_k - 1 = 2^(2^k); valid while F_k is prime (k <= 4)."""
    if k > 4:
        raise ValueError("F_k is composite for known k > 4; group order is not F_k - 1")
    return fermat_number(k) - 1


def is_primitive_root_mod_f4(g: int) -> bool:
    """True iff g generates (Z/65537 Z)^x.

    The group order 65536 = 2^16 has the single prime factor 2, so g is a
    generator iff g^(65536/2) != 1 (mod 65537).
    """
    return pow(g, F4_GROUP_ORDER // 2, F4) != 1


# ---------------------------------------------------------------------------
# Self-verifying experiment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ExperimentReport:
    passed: bool
    checks: tuple[Check, ...]


def run_experiment(
    support: Sequence[int] = DEFAULT_SUPPORT,
    bound: int = DEFAULT_BOUND,
    alpha: float = 0.5,
    eps_sensor: float = 1e-6,
) -> ExperimentReport:
    """Run all corrected-formula verifications and return a pass/fail report."""
    checks: list[Check] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append(Check(name=name, passed=passed, detail=detail))

    # Lane A identities.
    check(
        "lane_a_gcd_lcm",
        repeat_period(6, 10, 1.0) == 0.5 and common_overtone(6, 10, 2.0) == 60.0,
        "T/gcd(6,10)=0.5, lcm(6,10)*f0=60",
    )

    # Forward encoding matches log n exactly (fundamental theorem of arithmetic).
    n = 360
    encoding_error = abs(forward_encoding(n) - math.log(n))
    check("forward_encoding_identity", encoding_error < 1e-12, f"|sum v_p log p - log {n}| = {encoding_error:.2e}")

    # The website's conflated formula would force log n = alpha * log n.
    conflated = alpha * forward_encoding(n)
    check(
        "alpha_conflation_bug_demonstrated",
        abs(conflated - math.log(n)) > 0.1 and abs(lane_b_drift(n, alpha) - alpha * math.log(n)) < 1e-12,
        f"alpha*sum = {conflated:.4f} != log n = {math.log(n):.4f}; omega_n = alpha*log n holds",
    )

    # l-inf vs l1 define different Delta(S, B) objects.
    delta_linf = delta_certificate(support, bound, norm="linf")
    delta_l1 = delta_certificate(support, bound, norm="l1")
    check(
        "linf_vs_l1_differ",
        delta_linf.value < delta_l1.value - 1e-9,
        f"Delta_linf={delta_linf.value:.6f} via {delta_linf.vector}, "
        f"Delta_l1={delta_l1.value:.6f} via {delta_l1.vector}",
    )

    # Certificate inequality with explicit numeric budget.
    check(
        "certificate_holds",
        certificate_holds(support, bound, eps_sensor),
        f"Delta(S,B)={delta_linf.value:.6f} > eps_num+eps_sensor",
    )

    # Bounded-support recovery roundtrip.
    true_vector = (2, -1, 1)[: len(support)]
    target = sum(c * math.log(p) for c, p in zip(true_vector, support))
    recovered = recover_coefficients(target, support, bound, tol=1e-9)
    check("reverse_recovery_roundtrip", recovered == true_vector, f"recovered {recovered} == {true_vector}")

    # Canary parity: 2nd-order products land on even bins, 3rd-order on odd.
    p, q = 3, 7
    second = second_order_products(p, q)
    third = third_order_products(p, q)
    check(
        "canary_bin_parity",
        all(x % 2 == 0 for x in second) and all(x % 2 == 1 for x in third),
        f"2nd-order {second} even; 3rd-order {third} odd",
    )

    # Fermat lane: F_4 structure and primitive root.
    check(
        "fermat_f4_structure",
        fermat_number(4) == F4 and multiplicative_group_order(4) == F4_GROUP_ORDER,
        "F_4 = 65537, |(Z/F_4 Z)^x| = 65536 = 2^16",
    )
    check(
        "primitive_root_mod_f4",
        is_primitive_root_mod_f4(3) and not is_primitive_root_mod_f4(2),
        "ord(3) = 65536 (generator); ord(2) = 32 (not a generator)",
    )

    return ExperimentReport(passed=all(c.passed for c in checks), checks=tuple(checks))


def main() -> int:
    """CLI entry: run the experiment and print a human or JSON report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument("--bound", type=int, default=DEFAULT_BOUND, help="coefficient bound B")
    parser.add_argument("--alpha", type=float, default=0.5, help="Lane B drift scale alpha")
    args = parser.parse_args()

    report = run_experiment(bound=args.bound, alpha=args.alpha)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        for c in report.checks:
            print(f"[{'PASS' if c.passed else 'FAIL'}] {c.name}: {c.detail}")
        print(f"\nresult: {'PASS' if report.passed else 'FAIL'} ({len(report.checks)} checks)")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
