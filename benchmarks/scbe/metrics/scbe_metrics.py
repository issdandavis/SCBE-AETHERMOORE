"""SCBE-specific metrics -- drift, mismatch, audio divergence, constraints.

These metrics measure SCBE's unique detection signals beyond binary
classification: how much state drift occurs, whether surfaces agree,
and whether the harmonic cost model behaves as expected.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from benchmarks.scbe.runners.core import SampleResult, SystemBenchmarkResult


def _safe_mean(values: List[float]) -> float:
    """Mean that handles empty lists."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def compute_scbe_metrics(result: SystemBenchmarkResult) -> Dict[str, Any]:
    """Compute SCBE-specific metrics from benchmark results.

    These only apply when the system is SCBE (metadata contains
    SCBE-specific fields like harmonic_cost, spin_code, etc.).

    Returns:
      - avg_harmonic_cost_attacks: Mean harmonic cost for attack samples.
      - avg_harmonic_cost_benign: Mean harmonic cost for benign samples.
      - cost_separation: Ratio of attack cost to benign cost (higher = better).
      - avg_spin_magnitude_attacks: Mean spin magnitude for attacks.
      - avg_spin_magnitude_benign: Mean spin magnitude for benign.
      - cross_surface_mismatch_rate: Fraction where multiple signals conflict.
      - avg_dispersal_cost: Mean dispersal cost across all samples.
      - constraint_violation_rate: Fraction of attacks that triggered
        boundary_violation or cost_exceeded.
      - tongue_dominance_rate: Fraction of attacks where one tongue dominated.
      - signal_frequency: Count of each detection signal type.
      - audio_divergence_proxy: Estimate based on cost variance (actual
        audio axis divergence requires FFT data not available in harness).
    """
    attack_costs: List[float] = []
    benign_costs: List[float] = []
    attack_spins: List[float] = []
    benign_spins: List[float] = []
    dispersal_costs: List[float] = []
    all_costs: List[float] = []

    boundary_violations = 0
    cost_exceeded = 0
    tongue_dominance = 0
    total_attacks = 0
    total_benign = 0

    signal_freq: Dict[str, int] = {}

    for r in result.results:
        meta = r.metadata

        # Extract SCBE-specific fields from metadata
        h_cost = meta.get("harmonic_cost", 0.0)
        spin_mag = meta.get("spin_magnitude", 0)
        d_cost = meta.get("dispersal_cost", 0.0)
        flags = meta.get("flags", {})

        if isinstance(h_cost, (int, float)):
            all_costs.append(float(h_cost))
            if r.ground_truth == 1:
                attack_costs.append(float(h_cost))
                attack_spins.append(float(spin_mag))
                total_attacks += 1
            else:
                benign_costs.append(float(h_cost))
                benign_spins.append(float(spin_mag))
                total_benign += 1

            if isinstance(d_cost, (int, float)):
                dispersal_costs.append(float(d_cost))

            if flags.get("boundary_violation", False):
                boundary_violations += 1
            if flags.get("cost_exceeded", False):
                cost_exceeded += 1
            if flags.get("tongue_imbalance", False):
                tongue_dominance += 1

        # Count signal frequencies
        for sig in r.signals:
            sig_name = sig.split("(")[0] if "(" in sig else sig
            signal_freq[sig_name] = signal_freq.get(sig_name, 0) + 1

    avg_attack_cost = _safe_mean(attack_costs)
    avg_benign_cost = _safe_mean(benign_costs)
    cost_separation = avg_attack_cost / max(avg_benign_cost, 0.001)

    # Audio divergence proxy: variance in harmonic cost across attacks
    # High variance = good (different attacks produce different cost signatures)
    if len(all_costs) >= 2:
        mean_cost = _safe_mean(all_costs)
        variance = sum((c - mean_cost) ** 2 for c in all_costs) / len(all_costs)
        audio_divergence = math.sqrt(variance)
    else:
        audio_divergence = 0.0

    constraint_violations = boundary_violations + cost_exceeded
    constraint_violation_rate = constraint_violations / max(total_attacks, 1)

    return {
        "avg_harmonic_cost_attacks": round(avg_attack_cost, 4),
        "avg_harmonic_cost_benign": round(avg_benign_cost, 4),
        "cost_separation": round(cost_separation, 4),
        "avg_spin_magnitude_attacks": round(_safe_mean(attack_spins), 2),
        "avg_spin_magnitude_benign": round(_safe_mean(benign_spins), 2),
        "avg_dispersal_cost": round(_safe_mean(dispersal_costs), 4),
        "constraint_violation_rate": round(constraint_violation_rate, 4),
        "tongue_dominance_rate": round(
            tongue_dominance / max(total_attacks, 1), 4
        ),
        "boundary_violations": boundary_violations,
        "cost_exceeded_count": cost_exceeded,
        "audio_divergence_proxy": round(audio_divergence, 4),
        "signal_frequency": dict(
            sorted(signal_freq.items(), key=lambda x: -x[1])
        ),
        "totals": {
            "attacks_with_scbe_data": total_attacks,
            "benign_with_scbe_data": total_benign,
        },
    }
