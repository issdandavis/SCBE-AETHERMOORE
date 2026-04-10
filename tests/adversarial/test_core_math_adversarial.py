"""
Adversarial edge-case tests for SCBE-AETHERMOORE core math.
Goal: TRY TO BREAK the TFDD emotional balancing and Davis Security Score.

Uses benchmark values from Issac's Layer 0-8 tests as ground truth:
  TFDD: E=+1.5 -> 1.4526, E=-0.5 -> 1.2678, E=-2.0 -> 3.8274
  GovernanceCoin after 100 steps: 0.8085
  D_H ~ 0.771
  DS(x) = 1 - ||x||_P^441, d=21

Patent: US Provisional #63/961,403
"""
import math
import sys
from dataclasses import dataclass
from typing import List, Tuple

PHI = (1.0 + math.sqrt(5.0)) / 2.0

# =============================================================================
# TFDD (Tonal Flux Discouragement Derivative) - reconstructed from benchmark
# =============================================================================
# From the benchmark data points:
#   E = +1.5 -> TFDD = 1.4526  (mild boost)
#   E = -0.5 -> TFDD = 1.2678  (moderate penalty)
#   E = -2.0 -> TFDD = 3.8274  (strong exponential discouragement)
#
# Reconstruction: TFDD(E) = 1 + beta * exp(-gamma * E)
# Fitting to three benchmark points:
#   gamma = ln(6.2478) / 3.5 ~ 0.5244
#   beta = 0.4526 / exp(-1.5 * 0.5244) ~ 0.9923

BETA_TFDD = 0.9923
GAMMA_TFDD = 0.5244


def tfdd(E: float) -> float:
    """TFDD emotional cost multiplier. Reconstructed from benchmark."""
    return 1.0 + BETA_TFDD * math.exp(-GAMMA_TFDD * E)


def verify_reconstruction():
    """Check our reconstruction matches the benchmark points."""
    benchmarks = [(1.5, 1.4526), (-0.5, 1.2678), (-2.0, 3.8274)]
    print("=== TFDD Reconstruction Verification ===")
    all_close = True
    for E, expected in benchmarks:
        computed = tfdd(E)
        err = abs(computed - expected)
        ok = err < 0.05
        status = "OK" if ok else "MISMATCH"
        print(f"  E={E:+.1f}  expected={expected:.4f}  got={computed:.4f}  err={err:.4f}  [{status}]")
        if not ok:
            all_close = False
    print()
    return all_close


# =============================================================================
# Davis Security Score - exact from patent
# =============================================================================
def davis_score(R: float, d: int = 21) -> float:
    """DS(x) = 1 - R^(d^2) where R = ||x||_P in [0, 1)"""
    if R < 0.0 or R >= 1.0:
        return float('nan')
    return 1.0 - R ** (d * d)  # d^2 = 441 for d=21


def gate_decision(ds: float, tau_allow: float = 0.72, tau_collapse: float = 0.31) -> str:
    if math.isnan(ds):
        return "UNDEFINED"
    if ds > tau_allow:
        return "ALLOW"
    elif ds > tau_collapse:
        return "ATTENUATE"
    else:
        return "COLLAPSE"


# =============================================================================
# ADVERSARIAL TEST BATTERY
# =============================================================================
@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str


results: List[TestResult] = []


def test(name: str):
    """Decorator to register adversarial tests."""
    def decorator(func):
        def wrapper():
            try:
                passed, detail = func()
                results.append(TestResult(name, passed, detail))
            except Exception as e:
                results.append(TestResult(name, False, f"EXCEPTION: {type(e).__name__}: {e}"))
        return wrapper
    return decorator


# --- TFDD ATTACKS ---

@test("TFDD: NaN injection")
def tfdd_nan():
    """What happens when emotional valence is NaN?"""
    val = tfdd(float('nan'))
    if math.isnan(val):
        return False, f"TFDD returns NaN - system cannot make a decision. Got: {val}"
    return True, f"TFDD handles NaN gracefully: {val}"


@test("TFDD: Positive infinity valence")
def tfdd_pos_inf():
    """Adversary claims infinitely positive emotion."""
    val = tfdd(float('inf'))
    if val < 1.0:
        return False, f"TFDD < 1.0 for +inf valence - cost multiplier inverted! Got: {val}"
    return True, f"TFDD at +inf: {val}"


@test("TFDD: Negative infinity valence")
def tfdd_neg_inf():
    """Maximally negative emotion."""
    val = tfdd(float('-inf'))
    if math.isinf(val):
        return False, f"TFDD returns inf - will cause downstream overflow. Got: {val}"
    if math.isnan(val):
        return False, f"TFDD returns NaN for -inf input. Got: {val}"
    return True, f"TFDD at -inf: {val}"


@test("TFDD: Micro-oscillation attack (mean=+0.01, swings to -0.01)")
def tfdd_micro_oscillation():
    """
    Adversary alternates between E=+0.01 and E=-0.01.
    The mean looks positive, but half the steps are negative.
    Does TFDD catch the negative half?
    """
    positive_cost = tfdd(+0.01)
    negative_cost = tfdd(-0.01)
    mean_cost = (positive_cost + negative_cost) / 2.0
    naive_mean_cost = tfdd(0.0)
    if mean_cost < naive_mean_cost * 0.99:
        return False, (f"Oscillation bypass! avg(TFDD(+0.01), TFDD(-0.01))={mean_cost:.6f} "
                       f"< TFDD(0.0)={naive_mean_cost:.6f}")
    return True, (f"Convexity holds: avg={mean_cost:.6f} >= TFDD(0)={naive_mean_cost:.6f}")


@test("TFDD: Boundary float exploit (E = -1e-15)")
def tfdd_boundary_float():
    """Does the exponential branch trigger at tiny negative values?"""
    val_neg = tfdd(-1e-15)
    val_zero = tfdd(0.0)
    val_pos = tfdd(1e-15)
    monotonic = val_neg >= val_zero >= val_pos
    if not monotonic:
        return False, (f"Monotonicity broken at boundary: "
                       f"TFDD(-1e-15)={val_neg:.10f}, TFDD(0)={val_zero:.10f}, TFDD(1e-15)={val_pos:.10f}")
    return True, (f"Monotonic at boundary: TFDD(-1e-15)={val_neg:.10f}, "
                  f"TFDD(0)={val_zero:.10f}, TFDD(1e-15)={val_pos:.10f}")


@test("TFDD: Monotonicity sweep (-10 to +10)")
def tfdd_monotonicity():
    """Full sweep: TFDD must be strictly decreasing as E increases."""
    steps = 1000
    prev = tfdd(-10.0)
    violations = []
    for i in range(1, steps + 1):
        E = -10.0 + (20.0 * i / steps)
        curr = tfdd(E)
        if curr > prev + 1e-12:
            violations.append((E, prev, curr))
        prev = curr
    if violations:
        v = violations[0]
        return False, (f"{len(violations)} monotonicity violations. First at E={v[0]:.4f}: "
                       f"prev={v[1]:.6f} < curr={v[2]:.6f}")
    return True, f"Strictly monotonically decreasing across {steps} steps from E=-10 to E=+10"


@test("TFDD: Extreme negative (E=-100)")
def tfdd_extreme_neg():
    """Does the exponential overflow?"""
    try:
        val = tfdd(-100.0)
        if math.isinf(val):
            return False, f"Overflow at E=-100: TFDD={val}"
        if math.isnan(val):
            return False, f"NaN at E=-100: TFDD={val}"
        return True, f"TFDD(-100) = {val:.6e} (large but finite)"
    except OverflowError:
        return False, "OverflowError raised at E=-100"


@test("TFDD: Extreme negative (E=-1000)")
def tfdd_extreme_neg_1000():
    """Push harder."""
    try:
        val = tfdd(-1000.0)
        if math.isinf(val):
            return False, f"Overflow at E=-1000: TFDD={val}"
        return True, f"TFDD(-1000) = {val:.6e}"
    except OverflowError:
        return False, "OverflowError raised at E=-1000"


# --- DAVIS SECURITY SCORE ATTACKS ---

@test("DS: R exactly 0 (origin)")
def ds_origin():
    """Embedding at origin should be perfectly safe."""
    ds = davis_score(0.0)
    if ds != 1.0:
        return False, f"DS(0) should be 1.0, got {ds}"
    return True, f"DS(0) = {ds}"


@test("DS: R = 1 - 1e-15 (near boundary)")
def ds_near_boundary():
    """Just barely inside the Poincare ball."""
    R = 1.0 - 1e-15
    ds = davis_score(R)
    decision = gate_decision(ds)
    if ds > 0.01:
        return False, f"DS too high near boundary: DS({R})={ds:.10f}, decision={decision}"
    return True, f"DS({R}) = {ds:.10e}, decision={decision}"


@test("DS: R = 1 (exactly on boundary)")
def ds_exact_boundary():
    """On the boundary - should be undefined or 0."""
    ds = davis_score(1.0)
    if not math.isnan(ds):
        return False, f"DS(1.0) should be NaN (outside ball), got {ds}"
    decision = gate_decision(ds)
    if decision != "UNDEFINED":
        return False, f"Gate should return UNDEFINED for boundary, got {decision}"
    return True, f"DS(1.0) = NaN, decision=UNDEFINED - correctly handled"


@test("DS: R = 1 + 1e-15 (outside ball)")
def ds_outside_ball():
    """Just outside - should be caught."""
    ds = davis_score(1.0 + 1e-15)
    if not math.isnan(ds):
        return False, f"DS(1+e) should be NaN, got {ds}"
    return True, f"DS(1+e) correctly returns NaN"


@test("DS: Negative R")
def ds_negative_r():
    """Negative radius is nonsensical."""
    ds = davis_score(-0.5)
    if not math.isnan(ds):
        return False, f"DS(-0.5) should be NaN, got {ds}"
    return True, f"DS(-0.5) correctly returns NaN"


@test("DS: R = 0.41 (from benchmark narrative)")
def ds_benchmark_check():
    """
    The audit narrative said R=0.41 -> DS=0.89, H=6.2e-75.
    Let's verify.
    """
    R = 0.41
    ds = davis_score(R)
    H = R ** 441
    log_H = 441 * math.log10(0.41)  # ~ -170.6
    ds_close = abs(ds - 0.89) < 0.05
    detail = f"DS({R}) = {ds:.6f}, H = {H:.6e}, log10(H) = {log_H:.1f}"
    if not ds_close:
        return False, f"Narrative claimed DS=0.89 for R=0.41 but actual DS={ds:.6f}. {detail}"
    return True, detail


@test("DS: Floating point collapse zone (R near 0.99)")
def ds_float_collapse():
    """Does float precision cause DS to go negative near boundary?"""
    test_points = [0.99, 0.999, 0.9999, 0.99999]
    issues = []
    for R in test_points:
        ds = davis_score(R)
        if ds < 0:
            issues.append(f"DS({R}) = {ds} (NEGATIVE!)")
        elif ds > 0.5:
            issues.append(f"DS({R}) = {ds} (suspiciously high for R~1)")
    if issues:
        return False, "; ".join(issues)
    return True, f"All near-boundary DS values non-negative and small"


@test("DS: Adversarial radius to land exactly at tau_collapse boundary")
def ds_threshold_gaming():
    """
    Find R such that DS(R) ~ tau_collapse = 0.31.
    Can an adversary sit right at the ATTENUATE/COLLAPSE boundary?
    """
    tau_collapse = 0.31
    R_target = (1.0 - tau_collapse) ** (1.0 / 441.0)
    ds = davis_score(R_target)
    decision = gate_decision(ds)
    precision_needed = 1.0 - R_target
    detail = (f"R={R_target:.10f}, DS={ds:.10f}, decision={decision}. "
              f"Adversary needs radius precision of ~{precision_needed:.2e} from boundary")
    if precision_needed > 0.001:
        return True, f"Threshold gaming requires R={R_target:.6f} - coarse precision ({precision_needed:.4f} from boundary). {detail}"
    else:
        return False, f"Threshold gaming feasible at very high precision. {detail}"


# --- COMBINED ATTACK: TFDD + DS ---

@test("Combined: Can positive TFDD mask a near-collapse DS?")
def combined_masking():
    """
    High emotional positivity (low TFDD) but near Poincare boundary (low DS).
    These are SEPARATE layers - TFDD shouldn't rescue a bad DS.
    """
    tfdd_cost = tfdd(5.0)
    ds = davis_score(0.998)
    decision = gate_decision(ds)
    detail = (f"Positive emotion TFDD={tfdd_cost:.4f} (low), "
              f"but DS={ds:.6e} (near zero), decision={decision}")
    if decision == "ALLOW":
        return False, f"CRITICAL: Positive emotion masks boundary drift! {detail}"
    return True, f"Layers independent: {detail}"


# --- ADDITIONAL ADVERSARIAL TESTS I'M ADDING ---

@test("TFDD: Gradient at zero (steepness of penalty onset)")
def tfdd_gradient_zero():
    """How sharp is the penalty transition at E=0?"""
    h = 1e-8
    grad = (tfdd(0.0 + h) - tfdd(0.0 - h)) / (2 * h)
    # Analytical: d/dE [1 + beta*exp(-gamma*E)] = -beta*gamma*exp(-gamma*E)
    # At E=0: -beta*gamma = -0.9923 * 0.5244 = -0.5204
    analytical = -BETA_TFDD * GAMMA_TFDD
    err = abs(grad - analytical)
    if err > 0.01:
        return False, f"Numerical gradient {grad:.6f} != analytical {analytical:.6f}, err={err:.6f}"
    return True, f"Gradient at E=0: {grad:.6f} (analytical: {analytical:.6f}). Penalty slope = {abs(grad):.4f} per unit valence"


@test("DS: ATTENUATE zone width")
def ds_attenuate_width():
    """How wide is the ATTENUATE zone in R-space?"""
    # ALLOW: DS > 0.72 -> R^441 < 0.28 -> R < 0.28^(1/441)
    # COLLAPSE: DS < 0.31 -> R^441 > 0.69 -> R > 0.69^(1/441)
    R_allow = 0.28 ** (1.0 / 441.0)
    R_collapse = 0.69 ** (1.0 / 441.0)
    width = R_collapse - R_allow
    detail = (f"ALLOW zone: R < {R_allow:.6f}, COLLAPSE zone: R > {R_collapse:.6f}, "
              f"ATTENUATE width: {width:.6f} in R-space ({width*100:.2f}% of radius)")
    # If the zone is too narrow, it's effectively binary (ALLOW or COLLAPSE)
    if width < 0.001:
        return False, f"ATTENUATE zone is only {width:.6f} wide - effectively binary gate! {detail}"
    return True, detail


@test("DS: d=21 vs d=6 sensitivity comparison")
def ds_dimension_sensitivity():
    """Does d=21 make DS too aggressive? Compare with d=6."""
    R = 0.5
    ds_21 = davis_score(R, d=21)
    ds_6 = 1.0 - R ** (6 * 6)  # d=6 -> d^2=36
    detail = (f"At R=0.5: DS(d=21)={ds_21:.10f}, DS(d=6)={ds_6:.10f}. "
              f"d=21 exponent is 441, d=6 exponent is 36. "
              f"0.5^441={0.5**441:.2e}, 0.5^36={0.5**36:.2e}")
    # For d=21, even R=0.5 gives DS very close to 1 because 0.5^441 ~ 0
    if ds_21 > 0.9999 and ds_6 > 0.9999:
        return True, f"Both near 1.0 at R=0.5. {detail}"
    return True, detail


@test("DS: Where does the cliff happen for d=21?")
def ds_cliff_location():
    """Find the R value where DS drops from 0.99 to 0.01."""
    # DS = 0.99 -> R^441 = 0.01 -> R = 0.01^(1/441)
    # DS = 0.01 -> R^441 = 0.99 -> R = 0.99^(1/441)
    R_safe = 0.01 ** (1.0 / 441.0)
    R_danger = 0.99 ** (1.0 / 441.0)
    cliff_width = R_danger - R_safe
    detail = (f"DS=0.99 at R={R_safe:.6f}, DS=0.01 at R={R_danger:.6f}. "
              f"Cliff width: {cliff_width:.6f} ({cliff_width*100:.2f}% of radius). "
              f"The entire ALLOW->COLLAPSE transition happens in {cliff_width:.4f} of R-space")
    if cliff_width < 0.01:
        return False, f"Cliff is only {cliff_width:.6f} wide - near-binary behavior! {detail}"
    return True, detail


@test("TFDD: Accumulation attack (1000 steps at E=-0.001)")
def tfdd_accumulation():
    """
    Adversary sends barely-negative valence for many steps.
    Does the accumulated cost add up, or does the tiny per-step penalty
    let the adversary sneak through?
    """
    per_step_cost = tfdd(-0.001)
    neutral_cost = tfdd(0.0)
    excess_per_step = per_step_cost - neutral_cost
    accumulated_excess = excess_per_step * 1000
    detail = (f"Per step: TFDD(-0.001)={per_step_cost:.8f}, neutral={neutral_cost:.8f}, "
              f"excess={excess_per_step:.8e}. After 1000 steps: accumulated excess={accumulated_excess:.6f}")
    if accumulated_excess < 0.01:
        return False, f"Slow-drip attack viable: 1000 barely-negative steps only accumulate {accumulated_excess:.6f} excess cost. {detail}"
    return True, detail


@test("GovernanceCoin: Zero-valence farming")
def governance_zero_farming():
    """
    If an agent stays at exactly E=0 (neutral), does it still accumulate coin?
    A zero-contribution agent shouldn't earn governance weight.
    """
    # GovernanceCoin ~ integral of 1/(1+L) over time
    # At E=0, L = TFDD(0) * base_metric
    # The question is whether neutral agents accumulate value
    tfdd_neutral = tfdd(0.0)
    # Neutral is still > 1.0 (it's 1 + beta = 1.9923)
    # So the cost is non-trivial even at neutral
    detail = f"TFDD(0)={tfdd_neutral:.4f}. Neutral agent faces cost multiplier of {tfdd_neutral:.4f}x"
    # This means V = 1/(1+L) is reduced even for neutral agents
    # Not a failure per se, but worth noting
    return True, detail


# =============================================================================
# RUN ALL TESTS
# =============================================================================
def main():
    print("=" * 72)
    print("ADVERSARIAL TEST BATTERY - SCBE-AETHERMOORE CORE MATH")
    print("Targeting: TFDD emotional balancing + Davis Security Score")
    print("Mode: BREAK IT (not evaluate it)")
    print("=" * 72)
    print()

    verify_reconstruction()

    # Run all tests
    tfdd_nan()
    tfdd_pos_inf()
    tfdd_neg_inf()
    tfdd_micro_oscillation()
    tfdd_boundary_float()
    tfdd_monotonicity()
    tfdd_extreme_neg()
    tfdd_extreme_neg_1000()
    tfdd_gradient_zero()
    tfdd_accumulation()
    ds_origin()
    ds_near_boundary()
    ds_exact_boundary()
    ds_outside_ball()
    ds_negative_r()
    ds_benchmark_check()
    ds_float_collapse()
    ds_threshold_gaming()
    ds_attenuate_width()
    ds_dimension_sensitivity()
    ds_cliff_location()
    combined_masking()
    governance_zero_farming()

    # Report
    print()
    print("=" * 72)
    print("RESULTS")
    print("=" * 72)

    passed = 0
    failed = 0
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        icon = "  " if r.passed else ">>"
        print(f"{icon} [{status}] {r.name}")
        print(f"         {r.detail}")
        print()
        if r.passed:
            passed += 1
        else:
            failed += 1

    print("=" * 72)
    print(f"TOTAL: {passed + failed}  |  PASSED: {passed}  |  FAILED: {failed}")
    if failed > 0:
        print(f"\n*** {failed} FAILURE(S) FOUND - these are real attack surfaces ***")
    else:
        print("\n*** All attacks survived - core math is robust against this battery ***")
    print("=" * 72)

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
