#!/usr/bin/env python3
"""Null battery for the tether grip-and-lift rectifier proxy.

This is a research harness, not a flight model. It asks one narrow question:
does the continuous non-reciprocal rectifier respond to coherent traveling
wave shear more strongly than phase-scrambled waves with the same amplitude
scale?
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sim_tether_rectifier import (
    electrodynamic_tether_terms,
    nonreciprocal_grip_lift_torque,
)  # noqa: E402

DEFAULT_OUT = REPO_ROOT / "artifacts" / "research" / "tether_rectifier_null"


@dataclass(frozen=True)
class HarnessParams:
    nodes: int = 96
    length_m: float = 1.0
    steps: int = 640
    dt_s: float = 0.002
    amplitude_m: float = 0.002
    frequency_hz: float = 3.0
    spatial_mode: int = 3
    gain: float = 0.35
    null_trials: int = 200
    seed: int = 1729
    edt_tether_length_m: float = 1000.0
    edt_line_density_kg_m: float = 0.5
    edt_orbital_speed_m_s: float = 7672.598648
    edt_current_a: float = 10.0
    edt_b_field_t: float = 25e-6
    piston_coils: int = 64
    piston_steps: int = 480
    piston_current_a: float = 10.0
    piston_coupling_length_m: float = 0.05
    piston_b_field_t: float = 0.08


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be between 0 and 1")
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def traveling_wave_rectifier_output(
    params: HarnessParams,
    *,
    phase_offset: float = 0.0,
    amplitude_sign: float = 1.0,
    velocity_sign: float = 1.0,
    orientation_sign: float = 1.0,
) -> float:
    """Average signed rectifier output over a traveling wave sequence."""
    if params.nodes < 3:
        raise ValueError("nodes must be at least 3")
    if params.length_m <= 0:
        raise ValueError("length_m must be positive")

    dx = params.length_m / (params.nodes - 1)
    k = 2.0 * math.pi * params.spatial_mode / params.length_m
    omega = 2.0 * math.pi * params.frequency_hz
    total = 0.0
    for step in range(params.steps):
        t = step * params.dt_s
        y: list[float] = []
        v: list[float] = []
        for i in range(params.nodes):
            x = i * dx
            phase = k * x + omega * t + phase_offset
            y.append(amplitude_sign * params.amplitude_m * math.sin(phase))
            v.append(
                velocity_sign
                * amplitude_sign
                * params.amplitude_m
                * omega
                * math.cos(phase)
            )
        total += nonreciprocal_grip_lift_torque(
            y,
            v,
            dx=dx,
            gain=params.gain,
            orientation_sign=orientation_sign,
        )
    return total / params.steps


def balanced_counterwave_rectifier_output(
    params: HarnessParams, *, phase_a: float, phase_b: float
) -> float:
    """Smooth null: same mode/frequency scale, but balanced opposite wave directions."""
    if params.nodes < 3:
        raise ValueError("nodes must be at least 3")
    if params.length_m <= 0:
        raise ValueError("length_m must be positive")

    dx = params.length_m / (params.nodes - 1)
    k = 2.0 * math.pi * params.spatial_mode / params.length_m
    omega = 2.0 * math.pi * params.frequency_hz
    component_amp = params.amplitude_m / math.sqrt(2.0)
    total = 0.0
    for step in range(params.steps):
        t = step * params.dt_s
        y: list[float] = []
        v: list[float] = []
        for i in range(params.nodes):
            x = i * dx
            forward = k * x + omega * t + phase_a
            backward = k * x - omega * t + phase_b
            y.append(component_amp * (math.sin(forward) + math.sin(backward)))
            v.append(component_amp * omega * (math.cos(forward) - math.cos(backward)))
        total += nonreciprocal_grip_lift_torque(
            y, v, dx=dx, gain=params.gain, orientation_sign=1.0
        )
    return total / params.steps


def run_mechanical_channel(params: HarnessParams) -> dict[str, object]:
    """Mechanical momentum-flux proxy: field independent, amplitude-even."""
    real = traveling_wave_rectifier_output(params)
    amplitude_flip = traveling_wave_rectifier_output(params, amplitude_sign=-1.0)
    orientation_flip = traveling_wave_rectifier_output(params, orientation_sign=-1.0)
    time_reverse = traveling_wave_rectifier_output(params, velocity_sign=-1.0)

    rng = random.Random(params.seed)
    phase_nulls = []
    for _ in range(params.null_trials):
        phase_a = rng.uniform(0.0, 2.0 * math.pi)
        phase_b = rng.uniform(0.0, 2.0 * math.pi)
        phase_nulls.append(
            balanced_counterwave_rectifier_output(
                params, phase_a=phase_a, phase_b=phase_b
            )
        )

    null_abs_p95 = percentile([abs(value) for value in phase_nulls], 0.95)
    effect_ratio = abs(real) / max(null_abs_p95, 1e-18)
    amplitude_flip_ratio = amplitude_flip / real if real else float("nan")
    orientation_flip_ratio = orientation_flip / (-real) if real else float("nan")
    time_reverse_ratio = time_reverse / (-real) if real else float("nan")
    survives = effect_ratio > 1.0
    controls_match = (
        0.8 <= amplitude_flip_ratio <= 1.2
        and 0.8 <= orientation_flip_ratio <= 1.2
        and 0.8 <= time_reverse_ratio <= 1.2
    )
    verdict = (
        "MECHANICAL_FLUX_SURVIVES_PHASE_NULL"
        if survives and controls_match
        else "MECHANICAL_FLUX_NOT_VALIDATED"
    )
    return {
        "verdict": verdict,
        "real_signed_output": real,
        "amplitude_flip_signed_output": amplitude_flip,
        "orientation_flip_signed_output": orientation_flip,
        "time_reverse_signed_output": time_reverse,
        "phase_null_abs_p95": null_abs_p95,
        "effect_ratio_abs_vs_null95": effect_ratio,
        "amplitude_flip_same_ratio": amplitude_flip_ratio,
        "orientation_flip_opposite_ratio": orientation_flip_ratio,
        "time_reverse_opposite_ratio": time_reverse_ratio,
        "phase_null_mean": sum(phase_nulls) / len(phase_nulls),
        "phase_null_min": min(phase_nulls),
        "phase_null_max": max(phase_nulls),
        "phase_null_model": "balanced_counterpropagating_same_mode_same_frequency_random_phase",
        "physics_scope": (
            "Mechanical grip-and-lift momentum flux. It is amplitude-even under y,v -> -y,-v, odd under "
            "time reversal and linkage orientation reversal, and independent of B-field sign."
        ),
    }


def run_electrodynamic_channel(params: HarnessParams) -> dict[str, object]:
    """B-linear EDT channel: signed EMF and Lorentz force flip with B."""
    tether_mass_kg = params.edt_tether_length_m * params.edt_line_density_kg_m
    positive_b = electrodynamic_tether_terms(
        orbital_speed_m_s=params.edt_orbital_speed_m_s,
        b_field_t=params.edt_b_field_t,
        tether_length_m=params.edt_tether_length_m,
        current_a=params.edt_current_a,
        tether_mass_kg=tether_mass_kg,
    )
    negative_b = electrodynamic_tether_terms(
        orbital_speed_m_s=params.edt_orbital_speed_m_s,
        b_field_t=-params.edt_b_field_t,
        tether_length_m=params.edt_tether_length_m,
        current_a=params.edt_current_a,
        tether_mass_kg=tether_mass_kg,
    )
    emf_flip_ratio = negative_b["motional_emf_signed_v"] / (
        -positive_b["motional_emf_signed_v"]
    )
    force_flip_ratio = negative_b["lorentz_force_signed_n"] / (
        -positive_b["lorentz_force_signed_n"]
    )
    controls_flip = (
        0.999 <= emf_flip_ratio <= 1.001 and 0.999 <= force_flip_ratio <= 1.001
    )
    verdict = (
        "EDT_SIGNED_TERMS_FIELD_ODD"
        if controls_flip
        else "EDT_SIGNED_TERMS_NOT_FIELD_ODD"
    )
    return {
        "verdict": verdict,
        "positive_b": positive_b,
        "negative_b": negative_b,
        "emf_field_flip_opposite_ratio": emf_flip_ratio,
        "force_field_flip_opposite_ratio": force_flip_ratio,
        "physics_scope": (
            "Electrodynamic tether channel in the simplified perpendicular case. Signed EMF and Lorentz force "
            "are linear in B; magnitudes remain positive for reporting."
        ),
    }


def _mean_signed_piston_force(
    params: HarnessParams,
    *,
    mode: str,
    b_sign: float = 1.0,
    random_signs: Sequence[int] | None = None,
    phase_errors: Sequence[float] | None = None,
) -> float:
    """Reduced electromagnetic-piston force: F = sum(B * Lc * I_i).

    Modes:
    - naive: traveling sinusoidal current in a uniform field; mean force goes to zero.
    - commutated: current is switched with the local stroke so every engaged coil pushes the same way.
    - mistimed: commutated current with per-coil switching phase errors.
    - random_commutated: same absolute current inventory as commutated, random signs as the null.
    """
    if params.piston_coils < 1:
        raise ValueError("piston_coils must be positive")
    if params.piston_steps < 1:
        raise ValueError("piston_steps must be positive")
    if b_sign == 0.0:
        return 0.0
    if phase_errors is not None and len(phase_errors) != params.piston_coils:
        raise ValueError("phase_errors length must match piston_coils")

    b_field = math.copysign(abs(params.piston_b_field_t), b_sign)
    total = 0.0
    for step in range(params.piston_steps):
        time_phase = 2.0 * math.pi * step / params.piston_steps
        force = 0.0
        for coil in range(params.piston_coils):
            local_phase = time_phase - 2.0 * math.pi * coil / params.piston_coils
            stroke = math.sin(local_phase)
            if mode == "naive":
                current = params.piston_current_a * stroke
            elif mode == "commutated":
                current = params.piston_current_a * stroke * math.copysign(1.0, stroke)
            elif mode == "mistimed":
                if phase_errors is None:
                    raise ValueError("phase_errors are required for mistimed mode")
                switch = math.sin(local_phase + phase_errors[coil])
                current = params.piston_current_a * stroke * math.copysign(1.0, switch)
            elif mode == "random_commutated":
                if random_signs is None:
                    raise ValueError(
                        "random_signs are required for random_commutated mode"
                    )
                current = params.piston_current_a * abs(stroke) * random_signs[coil]
            else:
                raise ValueError(f"unknown piston mode: {mode}")
            force += b_field * params.piston_coupling_length_m * current
        total += force
    return total / params.piston_steps


def _piston_timing_sweep(
    params: HarnessParams, offsets: Sequence[float]
) -> dict[str, object]:
    forces = {
        f"{offset:.12g}": _mean_signed_piston_force(
            params,
            mode="mistimed",
            phase_errors=[offset] * params.piston_coils,
        )
        for offset in offsets
    }
    reference = forces[f"{0.0:.12g}"]
    residuals = {
        key: value - reference * math.cos(float(key)) for key, value in forces.items()
    }
    return {
        "offsets_rad": list(offsets),
        "forces_n": forces,
        "cos_fit_max_abs_resid_n": max(abs(value) for value in residuals.values()),
    }


def run_electromagnetic_piston_channel(params: HarnessParams) -> dict[str, object]:
    """Commutated linear-motor proxy: synchronized current rectifies force."""
    naive = _mean_signed_piston_force(params, mode="naive")
    commutated = _mean_signed_piston_force(params, mode="commutated")
    commutated_b_reversed = _mean_signed_piston_force(
        params, mode="commutated", b_sign=-1.0
    )

    rng = random.Random(params.seed + 991)
    nulls = []
    for _ in range(params.null_trials):
        signs = [1 if rng.random() >= 0.5 else -1 for _ in range(params.piston_coils)]
        nulls.append(
            _mean_signed_piston_force(
                params, mode="random_commutated", random_signs=signs
            )
        )

    timing_nulls = []
    for _ in range(params.null_trials):
        phase_errors = [
            rng.uniform(-math.pi, math.pi) for _ in range(params.piston_coils)
        ]
        timing_nulls.append(
            _mean_signed_piston_force(
                params, mode="mistimed", phase_errors=phase_errors
            )
        )

    null_abs_p95 = percentile([abs(value) for value in nulls], 0.95)
    timing_jitter_null_abs_p95 = percentile(
        [abs(value) for value in timing_nulls], 0.95
    )
    mistimed_mean_force = sum(timing_nulls) / len(timing_nulls)
    commutated_ratio = abs(commutated) / max(null_abs_p95, 1e-18)
    naive_ratio = abs(naive) / max(null_abs_p95, 1e-18)
    mistimed_ratio = abs(mistimed_mean_force) / max(timing_jitter_null_abs_p95, 1e-18)
    field_flip_ratio = (
        commutated_b_reversed / (-commutated) if commutated else float("nan")
    )
    timing_sweep = _piston_timing_sweep(
        params, (0.0, math.pi / 4.0, math.pi / 2.0, 3.0 * math.pi / 4.0, math.pi)
    )
    validated = (
        commutated_ratio > 1.0
        and naive_ratio < 1.0
        and 0.999 <= field_flip_ratio <= 1.001
        and abs(mistimed_mean_force) < timing_jitter_null_abs_p95
        and abs(mistimed_mean_force) < 0.25 * abs(commutated)
    )
    verdict = (
        "COMMUTATED_PISTON_BEATS_NULL_AND_IS_FIELD_ODD"
        if validated
        else "COMMUTATED_PISTON_NOT_VALIDATED"
    )
    return {
        "verdict": verdict,
        "naive_traveling_current_mean_force_n": naive,
        "commutated_mean_force_n": commutated,
        "commutated_b_reversed_mean_force_n": commutated_b_reversed,
        "random_sign_null_abs_p95_n": null_abs_p95,
        "mistimed_mean_force_n": mistimed_mean_force,
        "timing_jitter_null_abs_p95_n": timing_jitter_null_abs_p95,
        "mistimed_ratio_abs_vs_jitter_null": mistimed_ratio,
        "timing_sweep_cos_fit_max_abs_resid_n": timing_sweep["cos_fit_max_abs_resid_n"],
        "timing_sweep": timing_sweep,
        "commutated_ratio_abs_vs_null95": commutated_ratio,
        "naive_ratio_abs_vs_null95": naive_ratio,
        "field_flip_opposite_ratio": field_flip_ratio,
        "random_sign_null_mean_n": sum(nulls) / len(nulls),
        "random_sign_null_min_n": min(nulls),
        "random_sign_null_max_n": max(nulls),
        "timing_jitter_null_mean_n": mistimed_mean_force,
        "timing_jitter_null_min_n": min(timing_nulls),
        "timing_jitter_null_max_n": max(timing_nulls),
        "physics_scope": (
            "Electromagnetic piston proxy. A naive sinusoidal current in a uniform field averages near zero; "
            "commutated current switches with local stroke so every engaged coil pushes the same way. The "
            "commutation benefit requires correct switch timing and collapses under random per-coil phase error. "
            "This is a kinematic linear-motor control law, not a hardware efficiency, switching-loss, or "
            "propulsion claim."
        ),
    }


def run_null_battery(params: HarnessParams) -> dict[str, object]:
    mechanical = run_mechanical_channel(params)
    electrodynamic = run_electrodynamic_channel(params)
    electromagnetic_piston = run_electromagnetic_piston_channel(params)
    validated = mechanical["verdict"] == "MECHANICAL_FLUX_SURVIVES_PHASE_NULL" and (
        electrodynamic["verdict"] == "EDT_SIGNED_TERMS_FIELD_ODD"
        and electromagnetic_piston["verdict"]
        == "COMMUTATED_PISTON_BEATS_NULL_AND_IS_FIELD_ODD"
    )
    verdict = (
        "TETHER_THREE_CHANNEL_MODEL_VALIDATED_FOR_PROXY"
        if validated
        else "TETHER_THREE_CHANNEL_MODEL_NOT_VALIDATED_FOR_PROXY"
    )

    return {
        "schema_version": "tether_rectifier_null_harness_v3",
        "verdict": verdict,
        "params": asdict(params),
        "mechanical_channel": mechanical,
        "electrodynamic_channel": electrodynamic,
        "electromagnetic_piston_channel": electromagnetic_piston,
        "claim_scope": (
            "Pass means the harness keeps three reduced channels separate: mechanical momentum-flux rectification "
            "survives its smooth phase null, signed EDT terms flip under B reversal, and commutated current beats "
            "timing/sign nulls while naive traveling current does not. It does not validate hardware, contactors, "
            "ionospheric current collection, finite-rate switching, eddy losses, or net mission performance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=HarnessParams.nodes)
    parser.add_argument("--steps", type=int, default=HarnessParams.steps)
    parser.add_argument("--null-trials", type=int, default=HarnessParams.null_trials)
    parser.add_argument("--seed", type=int, default=HarnessParams.seed)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--json", action="store_true", help="Only print JSON; do not write artifacts"
    )
    parser.add_argument(
        "--no-write", action="store_true", help="Do not write artifacts"
    )
    args = parser.parse_args()

    params = HarnessParams(
        nodes=args.nodes, steps=args.steps, null_trials=args.null_trials, seed=args.seed
    )
    report = run_null_battery(params)
    report_path = args.out_dir / "report.json"
    if not args.json and not args.no_write:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Tether rectifier null harness v3")
        print(f"verdict={report['verdict']}")
        mechanical = report["mechanical_channel"]
        electrodynamic = report["electrodynamic_channel"]
        piston = report["electromagnetic_piston_channel"]
        print(f"mechanical_verdict={mechanical['verdict']}")
        print(f"mechanical_real_signed_output={mechanical['real_signed_output']:.12g}")
        print(f"mechanical_phase_null_abs_p95={mechanical['phase_null_abs_p95']:.12g}")
        print(
            f"mechanical_effect_ratio_abs_vs_null95={mechanical['effect_ratio_abs_vs_null95']:.3f}"
        )
        print(
            f"mechanical_amplitude_flip_same_ratio={mechanical['amplitude_flip_same_ratio']:.3f}"
        )
        print(
            f"mechanical_time_reverse_opposite_ratio={mechanical['time_reverse_opposite_ratio']:.3f}"
        )
        print(f"edt_verdict={electrodynamic['verdict']}")
        print(
            f"edt_emf_field_flip_opposite_ratio={electrodynamic['emf_field_flip_opposite_ratio']:.3f}"
        )
        print(
            f"edt_force_field_flip_opposite_ratio={electrodynamic['force_field_flip_opposite_ratio']:.3f}"
        )
        print(f"piston_verdict={piston['verdict']}")
        print(
            f"piston_naive_ratio_abs_vs_null95={piston['naive_ratio_abs_vs_null95']:.3f}"
        )
        print(
            f"piston_commutated_ratio_abs_vs_null95={piston['commutated_ratio_abs_vs_null95']:.3f}"
        )
        print(
            f"piston_mistimed_ratio_abs_vs_jitter_null={piston['mistimed_ratio_abs_vs_jitter_null']:.3f}"
        )
        print(
            f"piston_timing_sweep_cos_fit_max_abs_resid_n={piston['timing_sweep_cos_fit_max_abs_resid_n']:.3g}"
        )
        print(
            f"piston_field_flip_opposite_ratio={piston['field_flip_opposite_ratio']:.3f}"
        )
        if args.no_write:
            print("wrote=<disabled>")
        else:
            print(f"wrote={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
