"""Exact C3 radial analysis/synthesis for the Loom multiplex value fiber.

The multiplex address remains ``(shell, carrier, source, target, charge)``.
Every value stored at that address may carry seven ordered C3 tri-folds.  The
result is 7 x 3 = 21 phase-addressed channels, not 21 independent axes and not
21 additional representation nodes.
"""

from __future__ import annotations

import cmath
import math
import random
from collections.abc import Sequence


LAYERS = 7
PHASE_CHANNELS = 3
CHANNELS = LAYERS * PHASE_CHANNELS
INTRINSIC_CONTINUOUS_DOF = 2 * LAYERS
OMEGA = cmath.exp(2j * math.pi / PHASE_CHANNELS)
TOLERANCE = 1e-9


def _three(values: Sequence[object], name: str) -> None:
    if len(values) != PHASE_CHANNELS:
        raise ValueError(f"{name} must contain exactly three phase channels")


def channels_from_mode(mode: complex) -> tuple[complex, complex, complex]:
    """Synthesize one ordered tri-fold ``z_k = u * omega**k``."""
    return tuple(mode * OMEGA**k for k in range(PHASE_CHANNELS))


def mode_from_channels(channels: Sequence[complex]) -> complex:
    """Extract the oriented k=1 C3 Fourier mode from complex channels."""
    _three(channels, "tri-fold")
    return sum(channels[k] * OMEGA ** (-k) for k in range(PHASE_CHANNELS)) / PHASE_CHANNELS


def manifold_residual(channels: Sequence[complex]) -> float:
    """Relative distance from the ordered tri-fold manifold."""
    model = channels_from_mode(mode_from_channels(channels))
    numerator = math.sqrt(sum(abs(left - right) ** 2 for left, right in zip(channels, model)))
    denominator = max(math.sqrt(sum(abs(value) ** 2 for value in channels)), 1e-15)
    return numerator / denominator


def splay_plane_residual(radial: Sequence[float]) -> float:
    """Relative violation of the real C3 plane ``sum(p_k) = 0``."""
    _three(radial, "radial splay")
    denominator = max(math.sqrt(sum(float(value) ** 2 for value in radial)), 1e-15)
    return abs(sum(float(value) for value in radial)) / denominator


def rotate_into_splay(
    channels: Sequence[complex],
    frame: float = 0.0,
    tolerance: float = TOLERANCE,
) -> tuple[float, float, float]:
    """Analyze a legal complex tri-fold as three real radial channels."""
    residual = manifold_residual(channels)
    if residual > tolerance:
        raise ValueError(f"REFUSE off-manifold tri-fold: residual {residual:.6g}")
    rotor = cmath.exp(-1j * frame)
    return tuple(float((rotor * value).real) for value in channels)


def rotate_out_of_splay(
    radial: Sequence[float],
    frame: float = 0.0,
    tolerance: float = TOLERANCE,
) -> tuple[complex, complex, complex]:
    """Synthesize the complex tri-fold from a legal real radial state."""
    residual = splay_plane_residual(radial)
    if residual > tolerance:
        raise ValueError(f"REFUSE off-plane radial state: residual {residual:.6g}")
    mode = (2.0 / 3.0) * cmath.exp(1j * frame) * sum(
        float(radial[k]) * OMEGA ** (-k) for k in range(PHASE_CHANNELS)
    )
    return channels_from_mode(mode)


def rotate_into_canonical_splay(
    channels: Sequence[complex],
    tolerance: float = TOLERANCE,
) -> tuple[float, tuple[float, float, float]]:
    """Use ``arg(u)`` as frame, retaining it as the reversible rotor."""
    residual = manifold_residual(channels)
    if residual > tolerance:
        raise ValueError(f"REFUSE off-manifold tri-fold: residual {residual:.6g}")
    mode = mode_from_channels(channels)
    frame = cmath.phase(mode) if abs(mode) > tolerance else 0.0
    return frame, rotate_into_splay(channels, frame, tolerance)


def wrap_phase(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def connection_holonomy(alpha: Sequence[float], twist: Sequence[int]) -> dict:
    """Keep continuous U(1) phase and discrete C3 twist in the loop verdict."""
    if len(alpha) != len(twist):
        raise ValueError("alpha and twist must address the same edges")
    total_phase = wrap_phase(sum(alpha) + 2 * math.pi * sum(twist) / PHASE_CHANNELS)
    return {
        "discrete_mod3": sum(twist) % PHASE_CHANNELS,
        "continuous_phase": wrap_phase(sum(alpha)),
        "total_phase": total_phase,
        "closure_residual": abs(total_phase),
        "closes": abs(total_phase) <= TOLERANCE,
    }


def transport(
    channels: Sequence[complex],
    alpha: Sequence[float],
    twist: Sequence[int],
) -> tuple[complex, complex, complex]:
    """Apply unitary multiplex-edge transport without changing local geometry."""
    if len(alpha) != len(twist):
        raise ValueError("alpha and twist must address the same edges")
    transported = tuple(channels)
    for phase, step in zip(alpha, twist):
        multiplier = cmath.exp(1j * phase) * OMEGA**step
        transported = tuple(multiplier * value for value in transported)
    return transported


def fiber_record() -> dict:
    """Return the JSON-safe contract embedded in the multiplex scene."""
    root_three_over_two = math.sqrt(3) / 2
    return {
        "schema": "loom.c3-radial-trifold.v1",
        "placement": "value fiber inside every multiplex relation address",
        "not_new_nodes": True,
        "layers": LAYERS,
        "layer_semantics": "unbound; no seventh roster name is invented",
        "phase_channels_per_layer": PHASE_CHANNELS,
        "phase_channel_labels": ["positive", "neutral", "negative"],
        "labels_are_phase_sectors_not_amplitudes": True,
        "phase_channel_angles": [0.0, 2 * math.pi / 3, -2 * math.pi / 3],
        "phase_addressed_channels": CHANNELS,
        "ambient_complex_real_components": 2 * CHANNELS,
        "continuous_intrinsic_dof": INTRINSIC_CONTINUOUS_DOF,
        "splay_real_shape": [LAYERS, PHASE_CHANNELS],
        "splay_constraints": LAYERS,
        "manifold": "z[a,k] = u[a] * omega^k; omega = exp(2*pi*i/3)",
        "invariants": [
            "sum_k z[a,k] = 0",
            "abs(z[a,k]) = rho[a]",
            "abs(z[a,j]-z[a,k]) = sqrt(3)*rho[a] for j != k",
        ],
        "radial_analysis": "p[a,k](psi)=Re(exp(-i*psi[a])*z[a,k])",
        "radial_synthesis": (
            "u[a]=(2/3)*exp(i*psi[a])*sum_k(p[a,k]*omega^(-k)); "
            "z[a,k]=u[a]*omega^k"
        ),
        "canonical_frame": "psi[a]=arg(u[a]); carry psi[a] as the reversible rotor",
        "forced_couplings": {
            "with_cos": [1.0, -0.5, -0.5],
            "through_sin": [0.0, root_three_over_two, -root_three_over_two],
            "for": "directed unitary edge transport exp(i*alpha_ab)*omega^g_ab",
        },
        "legality": {
            "complex_gate": "refuse when relative distance from z_k=u*omega^k exceeds tolerance",
            "radial_gate": "refuse when abs(sum_k p_k)/norm(p) exceeds tolerance",
            "tolerance": TOLERANCE,
            "failure_mode": "REFUSE; never silently project an off-manifold state",
        },
        "counting_rule": "fiber channels are a constrained value shape; do not multiply address-state counts",
        "integration_status": (
            "executable geometry primitive inside the multiplex record; learned model self-use is unproven"
        ),
    }


def verify_radial_trifold(
    seeds: Sequence[int] = (5, 17, 29, 43, 71),
    samples_per_seed: int = 200,
) -> dict:
    """Multi-seed round-trip, equivariance, and refusal controls."""
    exact = equivariant = corrupted_refused = independent_refused = total = 0
    max_error = max_equivariance_error = 0.0
    for seed in seeds:
        rng = random.Random(seed)
        for _ in range(samples_per_seed):
            mode = rng.uniform(0.2, 3.0) * cmath.exp(1j * rng.uniform(-math.pi, math.pi))
            channels = channels_from_mode(mode)
            frame = rng.uniform(-math.pi, math.pi)
            radial = rotate_into_splay(channels, frame)
            recovered = rotate_out_of_splay(radial, frame)
            error = max(abs(left - right) for left, right in zip(channels, recovered))
            max_error = max(max_error, error)
            exact += error <= TOLERANCE

            rotation = rng.uniform(-math.pi, math.pi)
            rotated = tuple(cmath.exp(1j * rotation) * value for value in channels)
            equivariance_error = max(
                abs(left - right)
                for left, right in zip(radial, rotate_into_splay(rotated, frame + rotation))
            )
            max_equivariance_error = max(max_equivariance_error, equivariance_error)
            equivariant += equivariance_error <= TOLERANCE

            corrupted = list(channels)
            corrupted[rng.randrange(PHASE_CHANNELS)] += 1e-4 * complex(
                rng.gauss(0, 1), rng.gauss(0, 1)
            )
            try:
                rotate_into_splay(corrupted)
            except ValueError:
                corrupted_refused += 1

            independent = tuple(
                complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(PHASE_CHANNELS)
            )
            try:
                rotate_into_splay(independent)
            except ValueError:
                independent_refused += 1
            total += 1

    checks = {
        "round_trip": exact == total,
        "rotation_equivariance": equivariant == total,
        "corrupted_refusal": corrupted_refused == total,
        "independent_refusal": independent_refused == total,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "seeds": list(seeds),
        "samples": total,
        "exact": exact,
        "equivariant": equivariant,
        "corrupted_refused": corrupted_refused,
        "independent_refused": independent_refused,
        "max_round_trip_error": max_error,
        "max_equivariance_error": max_equivariance_error,
    }
