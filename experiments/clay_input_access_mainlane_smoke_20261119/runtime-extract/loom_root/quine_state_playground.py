#!/usr/bin/env python3
"""
quine_state_playground.py -- backpropagate_quine_state, fully exposed.

Nothing is hidden here. Edit the INPUTS, flip the knobs, rerun:
    python quine_state_playground.py
The diagnostics just report what the function does. If a result looks wrong,
change a line and watch the number move. That is the point of the playground.
"""

import cmath
import math


PHI = 1.618033988749895
LANGUE_PHASES = [(2 * math.pi * lane) / 6.0 for lane in range(6)]


# =====================================================================
# QUINE-SEEDED KLEIN REGIONS -- finite routes inside an unreachable Absolute
# =====================================================================
def _inside_unit_ball(point, *, name="point"):
    values = tuple(float(value) for value in point)
    if not values:
        raise ValueError(f"{name} must have at least one coordinate")
    radius_squared = sum(value * value for value in values)
    if not math.isfinite(radius_squared) or radius_squared >= 1.0:
        raise ValueError(f"{name} must lie strictly inside the Klein unit ball")
    return values, radius_squared


def klein_lorentz_lift(point):
    """Lift an n-D Klein-ball point to the upper Lorentz hyperboloid.

    The returned tuple is ``(*space, time)`` and has Lorentz norm exactly -1
    up to floating-point error.  The unit sphere is the Cayley--Klein
    Absolute: it is validated, never clipped into a finite point.
    """

    values, radius_squared = _inside_unit_ball(point)
    scale = 1.0 / math.sqrt(1.0 - radius_squared)
    return tuple(value * scale for value in values) + (scale,)


def klein_distance(left, right):
    """Hyperbolic distance between same-dimensional Klein-ball points."""

    left_values, left_radius_squared = _inside_unit_ball(left, name="left")
    right_values, right_radius_squared = _inside_unit_ball(right, name="right")
    if len(left_values) != len(right_values):
        raise ValueError("left and right must have the same dimension")
    dot = sum(a * b for a, b in zip(left_values, right_values))
    cosh_distance = (1.0 - dot) / math.sqrt(
        (1.0 - left_radius_squared) * (1.0 - right_radius_squared)
    )
    # Roundoff can put an identical pair microscopically below cosh(0) == 1.
    return math.acosh(max(1.0, cosh_distance))


def quine_seeded_region(point, seed, region_radius, *, neutral_width=1e-9):
    """Measure one quine route against a finite seed-centered region.

    ``absolute_form`` is negative for every valid point and tends to zero only
    at the unreachable global boundary.  ``region_form`` applies the same
    signed-square construction to a finite hyperbolic radius around ``seed``:
    -1 is inside, 0 is the neutral boundary band, and +1 is outside.  This
    provides a real balanced-trit gate without treating the Absolute as a
    reachable node or silently replacing the existing quine state.
    """

    values, radius_squared = _inside_unit_ball(point)
    seed_values, _ = _inside_unit_ball(seed, name="seed")
    if len(values) != len(seed_values):
        raise ValueError("point and seed must have the same dimension")
    if not math.isfinite(region_radius) or region_radius <= 0:
        raise ValueError("region_radius must be finite and positive")
    if not math.isfinite(neutral_width) or neutral_width < 0:
        raise ValueError("neutral_width must be finite and non-negative")

    distance = klein_distance(values, seed_values)
    region_form = distance * distance - region_radius * region_radius
    if abs(region_form) <= neutral_width:
        trit = 0
    elif region_form < 0:
        trit = -1
    else:
        trit = 1
    euclidean_radius = math.sqrt(radius_squared)
    return {
        "point": values,
        "seed": seed_values,
        "distance": distance,
        "region_radius": float(region_radius),
        "region_form": region_form,
        "trit": trit,
        "absolute_form": radius_squared - 1.0,
        "absolute_margin": 1.0 - radius_squared,
        "origin_distance": math.atanh(euclidean_radius),
    }


# =====================================================================
# USER-SUPPLIED FUNCTION -- preserved as the baseline. Tweak it freely.
# =====================================================================
def backpropagate_quine_state(
    observed_cage,
    target_parameters,
    beta,
    temperature=1.0,
):
    n_parameters = len(target_parameters)
    updated = []
    for index in range(n_parameters):
        target = target_parameters[index]
        observed = observed_cage[index]
        target_magnitude = (PHI**index) * math.exp((beta * target) / temperature)
        observed_magnitude = (PHI**index) * math.exp((beta * observed) / temperature)
        phase = LANGUE_PHASES[index % 6]
        target_state = cmath.rect(target_magnitude, phase)
        observed_state = cmath.rect(observed_magnitude, phase)
        error_rotation = target_state * observed_state.conjugate()
        magnitude = abs(error_rotation)
        step = math.log(magnitude) / beta if magnitude > 0 else 0.0
        # KNOB A: this gives self-agreement a fixed point, but because the final
        # expression becomes target + (observed - target) == observed, it is an
        # identity pass rather than a corrective descent step:
        # step = observed - target
        updated.append(target + step)
    return updated


# =====================================================================
# DIAGNOSTICS
# =====================================================================
def phase_check(target, observed, beta=1.0, temperature=1.0):
    print("== 1. is the complex/phase machinery doing anything? ==")
    all_real = True
    for index in range(len(target)):
        target_value = target[index]
        observed_value = observed[index]
        phase = LANGUE_PHASES[index % 6]
        target_state = cmath.rect(
            (PHI**index) * math.exp(beta * target_value / temperature),
            phase,
        )
        observed_state = cmath.rect(
            (PHI**index) * math.exp(beta * observed_value / temperature),
            phase,
        )
        error_rotation = target_state * observed_state.conjugate()
        if abs(error_rotation.imag) > 1e-9:
            all_real = False
        print(
            f"   i={index}  err={error_rotation.real:10.4f}{error_rotation.imag:+.2e}j"
        )
    verdict = "phase CANCELS" if all_real else "phase SURVIVES"
    print(f"   -> every err real? {all_real}  =>  {verdict}\n")
    return all_real


def convergence_check(target, observed, beta=1.0, temperature=1.0):
    print("== 2. does one call pull observed toward target? ==")
    updated = backpropagate_quine_state(observed, target, beta, temperature)
    contractions = []
    for index in range(len(target)):
        before = abs(observed[index] - target[index])
        after = abs(updated[index] - target[index])
        closer = after < before
        contractions.append(closer)
        arrow = "closer" if closer else "FARTHER"
        print(
            f"   i={index}  tgt={target[index]:+.2f} obs={observed[index]:+.2f} "
            f"-> upd={updated[index]:+7.3f}   gap {before:.2f} -> {after:.2f} "
            f"({arrow})"
        )
    print()
    return updated, contractions


def fixed_point_check(beta=1.0, temperature=1.0):
    print("== 3. fixed point? feed target == observed, should come back unchanged ==")
    values = [0.5, 0.5, 0.5]
    output = backpropagate_quine_state(values, values, beta, temperature)
    returned = all(abs(left - right) < 1e-9 for left, right in zip(values, output))
    print(f"   in : {values}")
    print(f"   out: {[round(value, 4) for value in output]}")
    print(f"   -> input returned? {returned}   (try KNOB A to change this)\n")
    return output, returned


# =====================================================================
# PHASE-CONJUGATE RESIDUAL DESCENT -- separate from the preserved baseline
# =====================================================================
def complex_states(parameters, beta=1.0, temperature=1.0):
    """Map real parameters onto the six fixed tongue phases."""

    if temperature <= 0:
        raise ValueError("temperature must be positive")
    return [
        cmath.rect(
            (PHI**index) * math.exp(beta * value / temperature),
            LANGUE_PHASES[index % 6],
        )
        for index, value in enumerate(parameters)
    ]


def phase_conjugate_loss(
    observed,
    target,
    beta=1.0,
    temperature=1.0,
    anchor=1.0,
):
    """Complex field loss plus a per-coordinate reconstruction anchor.

    The field term permits interference across tongues.  The anchor prevents a
    different parameter vector with the same aggregate amplitude from counting
    as an exact replica.  Both terms are zero at observed == target.
    """

    if len(observed) != len(target):
        raise ValueError("observed and target must have the same length")
    if anchor < 0:
        raise ValueError("anchor must be non-negative")
    observed_states = complex_states(observed, beta, temperature)
    target_states = complex_states(target, beta, temperature)
    residuals = [
        observed_state - target_state
        for observed_state, target_state in zip(observed_states, target_states)
    ]
    aggregate = sum(residuals, 0j)
    return abs(aggregate) ** 2 + anchor * sum(
        abs(residual) ** 2 for residual in residuals
    )


def phase_conjugate_gradient(
    observed,
    target,
    beta=1.0,
    temperature=1.0,
    anchor=1.0,
):
    """Analytic gradient of phase_conjugate_loss with respect to observed."""

    if len(observed) != len(target):
        raise ValueError("observed and target must have the same length")
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    if anchor < 0:
        raise ValueError("anchor must be non-negative")
    observed_states = complex_states(observed, beta, temperature)
    target_states = complex_states(target, beta, temperature)
    residuals = [
        observed_state - target_state
        for observed_state, target_state in zip(observed_states, target_states)
    ]
    aggregate = sum(residuals, 0j)
    gradient = []
    for observed_state, residual in zip(observed_states, residuals):
        state_derivative = (beta / temperature) * observed_state
        coupled = aggregate.conjugate() + anchor * residual.conjugate()
        gradient.append(2.0 * (coupled * state_derivative).real)
    return gradient


def phase_conjugate_descent(
    observed,
    target,
    beta=1.0,
    temperature=1.0,
    learning_rate=1.0,
    anchor=1.0,
    max_backtracks=32,
):
    """Take one accepted gradient step, halving the rate until loss falls."""

    before = phase_conjugate_loss(observed, target, beta, temperature, anchor)
    gradient = phase_conjugate_gradient(
        observed,
        target,
        beta,
        temperature,
        anchor,
    )
    if not any(gradient):
        return list(observed), {
            "loss_before": before,
            "loss_after": before,
            "learning_rate": 0.0,
            "backtracks": 0,
            "accepted": True,
        }

    rate = learning_rate
    for backtracks in range(max_backtracks + 1):
        candidate = [
            value - rate * derivative for value, derivative in zip(observed, gradient)
        ]
        after = phase_conjugate_loss(candidate, target, beta, temperature, anchor)
        if math.isfinite(after) and after < before:
            return candidate, {
                "loss_before": before,
                "loss_after": after,
                "learning_rate": rate,
                "backtracks": backtracks,
                "accepted": True,
            }
        rate *= 0.5

    return list(observed), {
        "loss_before": before,
        "loss_after": before,
        "learning_rate": 0.0,
        "backtracks": max_backtracks + 1,
        "accepted": False,
    }


def phase_descent_check(target, observed, beta=1.0, temperature=1.0):
    print("== 4. phase-conjugate residual: one real gradient step ==")
    updated, report = phase_conjugate_descent(
        observed,
        target,
        beta,
        temperature,
    )
    gap_before = math.dist(observed, target)
    gap_after = math.dist(updated, target)
    print(
        f"   loss {report['loss_before']:.6f} -> {report['loss_after']:.6f}"
        f"   accepted={report['accepted']} rate={report['learning_rate']:.3g}"
        f" backtracks={report['backtracks']}"
    )
    print(f"   parameter gap {gap_before:.6f} -> {gap_after:.6f}\n")
    return updated, report


# =====================================================================
# ADDITIVE FIELD VS. INTERFERENCE FIELD
# =====================================================================
def langue_field(weights, mode="additive"):
    """Measure six tongue weights with additive or complex interference rules."""

    if mode == "additive":
        return sum(
            (PHI**lane) * math.exp(weight) for lane, weight in enumerate(weights)
        )
    amplitude = sum(
        (PHI**lane) * math.exp(weight) * cmath.exp(1j * (2 * math.pi * lane) / 6.0)
        for lane, weight in enumerate(weights)
    )
    return abs(amplitude) ** 2


def interference_demo():
    print("== 5. interference idea, runnable ==")
    weights = [0.0] * 6
    additive = langue_field(weights, "additive")
    interference = langue_field(weights, "interference")
    print(f"   additive field (phi^l weights)     : {additive:12.4f}  strictly +")
    print(
        f"   interference field (phi^l weights) : {interference:12.4f}  partial cancel"
    )
    equal = sum(cmath.exp(1j * (2 * math.pi * lane) / 6.0) for lane in range(6))
    pair = abs(cmath.exp(0j) + cmath.exp(1j * math.pi)) ** 2
    print(
        f"   equal-magnitude all six tongues    : |{equal:.1e}|  "
        "-> numerical zero (6th roots of unity)"
    )
    print(
        f"   equal-magnitude pair l=0 vs l=3    : {pair:.1e}  "
        "-> numerical zero (antiphase)"
    )
    print(
        "   (with phi^l weights the pairs differ in size, so cancellation is only "
        "partial;\n    equalize the antiphase pairs if you want true nulls.)\n"
    )
    return {
        "additive": additive,
        "interference": interference,
        "equal_six_amplitude": abs(equal),
        "equal_antiphase_pair_intensity": pair,
    }


def main():
    target = [0.5, 1.0, -0.3, 0.8, 0.2, -0.5, 0.7]
    observed = [0.4, 1.2, -0.1, 0.6, 0.5, -0.2, 0.9]
    beta = 1.0
    temperature = 1.0

    phase_check(target, observed, beta, temperature)
    convergence_check(target, observed, beta, temperature)
    fixed_point_check(beta, temperature)
    phase_descent_check(target, observed, beta, temperature)
    interference_demo()


if __name__ == "__main__":
    main()
