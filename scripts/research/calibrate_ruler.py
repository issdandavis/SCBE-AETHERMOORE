#!/usr/bin/env python3
"""calibrate_ruler.py — fine-tune the offset ruler on hard knowns (primes).

Issac's metrology step: "calibrate on hard knowns, like fine-tuning any device,
and test the prime finder as calibration." Primes are the ideal standard —
exact, self-verifying (segmented sieve), and an infinite ladder at every scale.

Procedure (with the held-out discipline so it's calibration, not overfit):
  1. predictor pred(n) = n(ln n + ln ln n - 1)   [Dusart lower bound -> reads low]
  2. CALIBRATE: fit a 2-knob linear correction  actual ≈ α·pred + β  on a set of
     KNOWN primes (the gauge blocks).
  3. VALIDATE on a DISJOINT, held-out set of known primes. Calibration is only
     real if it improves the held-out numbers — you never test on what you tuned.
  4. Certify the instrument's tolerance = worst held-out error after calibration.

Usage:  python scripts/research/calibrate_ruler.py
"""
from __future__ import annotations

import math

try:
    from scripts.research.nth_prime_baseline_gate import simple_sieve
except ImportError:
    def simple_sieve(limit: int) -> list[int]:
        if limit < 2:
            return []
        f = bytearray([1]) * (limit + 1)
        f[0] = f[1] = 0
        for i in range(2, int(limit**0.5) + 1):
            if f[i]:
                f[i * i :: i] = bytearray(len(f[i * i :: i]))
        return [i for i in range(2, limit + 1) if f[i]]


def pred_base(n: int) -> float:
    return n * (math.log(n) + math.log(math.log(n)) - 1.0)


def linfit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least-squares y = a*x + b."""
    k = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = k * sxx - sx * sx
    a = (k * sxy - sx * sy) / denom
    b = (sy - a * sx) / k
    return a, b


def main() -> int:
    primes = simple_sieve(700)            # covers p_100 = 541, exact + verifiable
    def p(n: int) -> int:                 # the hard known
        return primes[n - 1]

    cal_ns = [10, 20, 30, 40, 50]         # gauge blocks to calibrate on
    val_ns = [60, 70, 80, 90, 100]        # HELD OUT — never tuned on these

    a, b = linfit([pred_base(n) for n in cal_ns], [p(n) for n in cal_ns])

    print("CALIBRATE OFFSET RULER ON HARD KNOWNS (primes from the engine)")
    print(f"  raw predictor:  pred(n) = n(ln n + ln ln n - 1)   [a lower bound -> reads short]")
    print(f"  calibrated on n={cal_ns}:  actual ≈ {a:.4f}·pred + {b:.2f}")
    print(f"\n  HELD-OUT VALIDATION (n never used in the fit):")
    print(f"  {'n':>4} {'pₙ(known)':>10} {'raw':>8} {'rawErr':>7} {'calibrated':>11} {'calErr':>7}")
    unc_errs, cal_errs = [], []
    for n in val_ns:
        actual = p(n)
        raw = pred_base(n)
        cal = a * raw + b
        ue = abs(actual - raw) / actual
        ce = abs(actual - cal) / actual
        unc_errs.append(ue)
        cal_errs.append(ce)
        print(f"  {n:>4} {actual:>10} {raw:>8.1f} {ue*100:>6.1f}% {cal:>11.1f} {ce*100:>6.1f}%")

    tol = max(cal_errs)
    print(f"\n  raw mean held-out error  = {sum(unc_errs)/len(unc_errs)*100:.1f}%")
    print(f"  calibrated mean held-out = {sum(cal_errs)/len(cal_errs)*100:.1f}%")
    print(f"  CERTIFIED TOLERANCE (worst held-out after calibration) = ±{tol*100:.1f}%")
    print(f"  -> the ruler now carries a stated accuracy; any unknown it measures is reported within it.")

    # self-checks: calibration must IMPROVE the held-out numbers (else it's overfit/noise)
    assert sum(cal_errs) < sum(unc_errs), "calibration did not help held-out — not a real calibration"
    assert max(cal_errs) < max(unc_errs), "worst-case held-out error not reduced by calibration"
    # and the standard itself must be exact/verifiable
    assert p(1) == 2 and p(10) == 29 and p(100) == 541, "prime standard mismatch — bad gauge"
    print("  self-checks: calibration improves held-out; prime standard exact (p₁₀=29, p₁₀₀=541)  OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
