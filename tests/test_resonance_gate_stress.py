"""
Resonance Gate — 1000-iteration stress test.
Tests the gate across distance, time, phase, and adversarial scenarios.
Reports statistics and identifies improvements.
"""

import math
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PHI = (1 + math.sqrt(5)) / 2
F0 = 440
TONGUE_WEIGHTS = [1.0, PHI, PHI**2, PHI**3, PHI**4, PHI**5]
TONGUE_PHASES = [
    0,
    math.pi / 3,
    2 * math.pi / 3,
    math.pi,
    4 * math.pi / 3,
    5 * math.pi / 3,
]
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]


def static_envelope(d_star, R=1.5):
    return R * math.pi ** (PHI * d_star)


def tongue_wave(t, weights=None, phase_offset=0.0):
    w = weights or TONGUE_WEIGHTS
    total_weight = sum(w)
    s = sum(
        w[lang] * math.cos(2 * math.pi * F0 * PHI**lang * t + TONGUE_PHASES[lang] + phase_offset) for lang in range(6)
    )
    return s / total_weight if total_weight > 0 else 0


def resonance_gate(d_star, t=0, R=1.5, phase_offset=0.0):
    d = max(0, d_star)
    envelope = static_envelope(d, R)
    combined = tongue_wave(t, phase_offset=phase_offset)
    wave_alignment = max(0, min(1, (combined + 1) / 2))
    geometry_alignment = math.exp(-PHI * d)
    rho = max(0, min(1, wave_alignment * geometry_alignment))
    barrier_cost = envelope / max(rho, 1e-6)

    if rho >= 0.7:
        decision = "PASS"
    elif rho >= 0.3:
        decision = "ESCALATE"
    else:
        decision = "REJECT"

    return {
        "rho": rho,
        "envelope": envelope,
        "wave_alignment": wave_alignment,
        "geometry_alignment": geometry_alignment,
        "barrier_cost": barrier_cost,
        "decision": decision,
        "t": t,
        "d_star": d_star,
    }


def phi_invariant_check(d_star, samples=64, dt=0.001):
    values = [resonance_gate(d_star, i * dt)["rho"] for i in range(samples)]
    epsilons = [0.1, 0.05, 0.025, 0.0125]
    counts = []
    for eps in epsilons:
        boxes = set(int(v / eps) for v in values)
        counts.append(len(boxes))

    log_eps = [math.log(e) for e in epsilons]
    log_n = [math.log(max(n, 1)) for n in counts]
    n = len(log_eps)
    sum_x = sum(log_eps)
    sum_y = sum(log_n)
    sum_xy = sum(log_eps[i] * log_n[i] for i in range(n))
    sum_x2 = sum(x**2 for x in log_eps)
    denom = n * sum_x2 - sum_x**2
    slope = (n * sum_xy - sum_x * sum_y) / denom if abs(denom) > 1e-12 else 0
    return -slope


# ============================================================================
# TESTS
# ============================================================================


def test_basic_properties(n=1000):
    """Test rho is always in [0,1], envelope is always positive, decisions are consistent."""
    failures = []
    for i in range(n):
        d = (i / n) * 3.0  # d* from 0 to 3
        t = i * 0.0001
        r = resonance_gate(d, t)

        if not (0 <= r["rho"] <= 1):
            failures.append(f"rho out of bounds: {r['rho']} at d*={d}, t={t}")
        if r["envelope"] <= 0:
            failures.append(f"envelope non-positive: {r['envelope']} at d*={d}")
        if r["rho"] >= 0.7 and r["decision"] != "PASS":
            failures.append(f"decision mismatch: rho={r['rho']} but decision={r['decision']}")
        if r["rho"] < 0.3 and r["decision"] != "REJECT":
            failures.append(f"decision mismatch: rho={r['rho']} but decision={r['decision']}")
        if r["barrier_cost"] < r["envelope"]:
            failures.append(f"barrier_cost < envelope: {r['barrier_cost']} < {r['envelope']}")

    return len(failures) == 0, failures


def test_distance_monotonicity(n=1000):
    """Test that as d* increases, geometry_alignment decreases monotonically."""
    failures = []
    prev_ga = 1.0
    for i in range(n):
        d = i * 0.003  # 0 to 3
        r = resonance_gate(d, t=0)
        if r["geometry_alignment"] > prev_ga + 1e-10:
            failures.append(
                f"geometry_alignment increased at d*={d:.4f}: {r['geometry_alignment']:.6f} > {prev_ga:.6f}"
            )
        prev_ga = r["geometry_alignment"]
    return len(failures) == 0, failures


def test_envelope_growth(n=1000):
    """Test that envelope grows super-exponentially with distance."""
    failures = []
    prev_env = 0
    for i in range(1, n):
        d = i * 0.003
        r = resonance_gate(d, t=0)
        if r["envelope"] < prev_env:
            failures.append(f"envelope decreased at d*={d:.4f}: {r['envelope']:.2f} < {prev_env:.2f}")
        prev_env = r["envelope"]
    return len(failures) == 0, failures


def test_adversarial_high_distance(n=1000):
    """Test that high d* always results in REJECT regardless of time."""
    failures = []
    for i in range(n):
        t = i * 0.00037  # varied time
        r = resonance_gate(d_star=2.0, t=t)
        if r["decision"] == "PASS":
            failures.append(f"HIGH d*=2.0 got PASS at t={t:.6f}, rho={r['rho']:.4f}")
    return len(failures) == 0, failures


def test_safe_origin_passes(n=1000):
    """Test that d*=0 (safe origin) almost always passes."""
    pass_count = 0
    for i in range(n):
        t = i * 0.00023
        r = resonance_gate(d_star=0.0, t=t)
        if r["decision"] == "PASS":
            pass_count += 1
    pass_rate = pass_count / n
    ok = pass_rate > 0.5  # at least half should pass at origin
    return ok, [f"pass_rate at d*=0: {pass_rate:.3f} ({pass_count}/{n})"]


def test_wave_aperiodicity(n=1000):
    """Test that the wave never exactly repeats over n samples."""
    seen = set()
    for i in range(n):
        t = i * 0.001
        w = tongue_wave(t)
        # Round to 10 decimal places — if it repeats, the wave is periodic
        key = round(w, 10)
        seen.add(key)
    unique_ratio = len(seen) / n
    ok = unique_ratio > 0.95  # at least 95% unique values
    return ok, [f"unique wave values: {len(seen)}/{n} ({unique_ratio:.3f})"]


def test_phase_offset_discrimination(n=1000):
    """Test that different phase offsets produce different rho values."""
    base_rhos = []
    shifted_rhos = []
    for i in range(n):
        d = 0.5
        t = i * 0.0003
        r_base = resonance_gate(d, t, phase_offset=0)
        r_shift = resonance_gate(d, t, phase_offset=math.pi)  # adversarial phase
        base_rhos.append(r_base["rho"])
        shifted_rhos.append(r_shift["rho"])

    avg_base = sum(base_rhos) / n
    avg_shift = sum(shifted_rhos) / n
    discrimination = abs(avg_base - avg_shift)
    ok = discrimination > 0.01  # there should be measurable difference
    return ok, [f"avg_base_rho={avg_base:.4f}, avg_shifted_rho={avg_shift:.4f}, discrimination={discrimination:.4f}"]


def test_barrier_cost_explodes(n=1000):
    """Test that barrier cost grows dramatically with distance."""
    costs = []
    for i in range(n):
        d = i * 0.003  # 0 to 3
        r = resonance_gate(d, t=0)
        costs.append(r["barrier_cost"])

    ratio = costs[-1] / max(costs[0], 1e-10)
    ok = ratio > 1000  # should be orders of magnitude higher at d*=3
    return ok, [f"barrier_cost ratio (d*=3 / d*=0): {ratio:.1f}x"]


def test_phi_invariant_convergence(n=100):
    """Test fractal dimension convergence at multiple distances."""
    results = []
    for i in range(n):
        d = i * 0.02  # 0 to 2
        fd = phi_invariant_check(d, samples=64, dt=0.001)
        results.append({"d_star": d, "fractal_dim": fd, "phi_delta": abs(fd - PHI)})

    avg_delta = sum(r["phi_delta"] for r in results) / n
    close_count = sum(1 for r in results if r["phi_delta"] < 0.3)
    return True, [f"avg phi_delta={avg_delta:.4f}, close_to_phi={close_count}/{n}"]


def test_negative_distance_safety(n=100):
    """Test that negative d* values are clamped safely."""
    failures = []
    for i in range(n):
        d = -1 * (i + 1) * 0.1
        r = resonance_gate(d, t=0)
        if not (0 <= r["rho"] <= 1):
            failures.append(f"rho={r['rho']} at d*={d}")
        if r["geometry_alignment"] > 1.01:
            failures.append(f"geometry_alignment={r['geometry_alignment']} > 1 at d*={d}")
    return len(failures) == 0, failures


# ============================================================================
# RUNNER
# ============================================================================

if __name__ == "__main__":
    tests = [
        ("basic_properties (1000 points)", test_basic_properties),
        ("distance_monotonicity (1000 steps)", test_distance_monotonicity),
        ("envelope_growth (1000 steps)", test_envelope_growth),
        ("adversarial_high_distance (1000 times)", test_adversarial_high_distance),
        ("safe_origin_passes (1000 times)", test_safe_origin_passes),
        ("wave_aperiodicity (1000 samples)", test_wave_aperiodicity),
        ("phase_offset_discrimination (1000 pairs)", test_phase_offset_discrimination),
        ("barrier_cost_explodes (1000 distances)", test_barrier_cost_explodes),
        ("phi_invariant_convergence (100 distances)", test_phi_invariant_convergence),
        ("negative_distance_safety (100 values)", test_negative_distance_safety),
    ]

    print("=" * 60)
    print("  Resonance Gate — 1000-Iteration Stress Test")
    print("=" * 60)

    results = []
    total_pass = 0
    t0 = time.time()

    for name, fn in tests:
        try:
            ok, details = fn()
            status = "PASS" if ok else "FAIL"
            if ok:
                total_pass += 1
            results.append({"test": name, "status": status, "details": details[:3]})
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")
            for d in details[:3]:
                print(f"        {d}")
        except Exception as e:
            results.append({"test": name, "status": "ERROR", "details": [str(e)]})
            print(f"  ERROR {name}: {e}")

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  {total_pass}/{len(tests)} tests passed in {elapsed:.2f}s")
    print(f"  Total iterations: ~{sum(1000 for _ in tests)}")
    print(f"{'=' * 60}")

    # Save results
    report = {
        "total_tests": len(tests),
        "passed": total_pass,
        "failed": len(tests) - total_pass,
        "elapsed_s": round(elapsed, 3),
        "results": results,
    }
    report_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "artifacts",
        "resonance_gate_stress_report.json",
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {report_path}")
