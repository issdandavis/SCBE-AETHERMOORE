"""
@file exp_decimal_drift_discrimination.py
@module experiments
@layer Layer 1-14
@component Decimal Drift Discrimination Experiment
@version 1.0.0

Tests whether the 14-layer pipeline produces a distinguishable floating-point
fingerprint ("drift profile") that can discriminate organic pipeline-processed
data from synthetic data that skips the pipeline.

Hypothesis: Data that traverses all 14 layers accumulates a specific pattern
of IEEE 754 rounding errors. Synthetic data (even if it produces similar
final values) will lack this pattern because it skips intermediate layers.

Three attack scenarios:
    Type A: Attacker directly computes final values (no pipeline)
    Type B: Attacker runs partial pipeline (skips some layers)
    Type C: Attacker adds random noise to mimic drift

Metrics:
    - Drift profile vector (per-layer drift magnitudes)
    - AUC: Can drift profile separate organic from synthetic?
    - Fractional entropy: Do decimal tails differ?

Author: Issac Davis
"""

import sys
import math
import time
import json
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional

import numpy as np

# Add the project root to path so we can import the real pipeline
sys.path.insert(0, "/home/user/SCBE-AETHERMOORE")

from src.symphonic_cipher.scbe_aethermoore.production_v2_1 import (
    # Constants
    PHI, R, EPSILON, TAU_COH, ETA_TARGET, D,
    TONGUE_WEIGHTS, CONLANG,
    CARRIER_FREQ, SAMPLE_RATE, DURATION,
    # Layer functions
    realify,
    apply_spd_weights,
    poincare_embed,
    hyperbolic_distance,
    mobius_add,
    phase_transform,
    breathing_transform,
    realm_distance,
    clamp_ball,
    QuasicrystalLattice,
    QUASICRYSTAL,
    spectral_stability,
    spin_coherence,
    audio_envelope_coherence,
    triadic_distance,
    harmonic_scaling,
    risk_base,
    risk_prime,
    # State
    State9D,
    generate_9d_state,
    generate_context,
    compute_entropy,
    phase_modulated_intent,
    # Governance
    Polyhedron,
    governance_pipeline,
)


# ============================================================================
# Drift Profile Extraction
# ============================================================================

def extract_drift_profile(state: State9D, intent: float) -> np.ndarray:
    """
    Run full pipeline and extract per-layer drift measurements.

    Returns a 16-element vector capturing the floating-point characteristics
    at each layer transition. This IS the pipeline fingerprint.
    """
    profile = np.zeros(16)

    # L1-L2: Realification
    c_complex = state.to_complex_context()
    x = realify(c_complex)
    norm_c = np.sqrt(np.sum(np.abs(c_complex) ** 2))
    norm_x = np.linalg.norm(x)
    profile[0] = abs(norm_x - norm_c)  # Realification drift

    # L3: SPD weighting
    g = np.array(TONGUE_WEIGHTS[:len(x)] + TONGUE_WEIGHTS[:len(x)])[:len(x)]
    x_G = apply_spd_weights(x, g)
    profile[1] = np.linalg.norm(x_G) / max(np.linalg.norm(x), 1e-30)

    # L3.5: Quasicrystal
    gate_vector = [
        float(v) if isinstance(v, (int, float))
        else abs(v) if isinstance(v, complex) else 0.0
        for v in state.context[:6]
    ]
    _, r_perp, _ = QUASICRYSTAL.map_gates_to_lattice(gate_vector)
    c_qc = QUASICRYSTAL.e_perp_coherence(gate_vector)
    profile[2] = c_qc
    profile[3] = float(np.linalg.norm(r_perp))

    # L4: Poincare embedding
    u = poincare_embed(x_G)
    profile[4] = np.linalg.norm(u)

    # L5: Hyperbolic distance
    v_ref = clamp_ball(np.zeros_like(u))
    d = hyperbolic_distance(u, v_ref)
    profile[5] = d

    # L6: Mobius addition
    a = clamp_ball(np.ones_like(u) * 0.05)
    m = mobius_add(a, u)
    profile[6] = np.linalg.norm(m)

    # L7: Phase transform
    p = phase_transform(u, a)
    profile[7] = np.linalg.norm(p)

    # L8: Breathing
    breathing_factor = 1.0 + 0.1 * np.sin(state.t * 2 * np.pi / 60)
    breath = breathing_transform(u, breathing_factor)
    profile[8] = np.linalg.norm(breath)

    # L9: Realm distance
    centers = np.zeros((1, len(u)))
    rd = realm_distance(u, centers)
    profile[9] = rd

    # L10: Spectral + spin coherence
    wave = phase_modulated_intent(intent)
    s_spec = spectral_stability(wave)
    profile[10] = s_spec

    phasors = np.exp(1j * np.array([
        float(v) if isinstance(v, (int, float))
        else np.angle(v) if isinstance(v, complex) else 0.0
        for v in state.context
    ]))
    s_spin = spin_coherence(phasors)
    profile[11] = s_spin

    # L11: Triadic
    d_auth = abs(intent - 0.75)
    d_cfg = abs(state.eta - ETA_TARGET) / ETA_TARGET
    d_tri = triadic_distance(rd, d_auth, d_cfg)
    profile[12] = d_tri

    # L12: Harmonic scaling
    H, _ = harmonic_scaling(rd, PHI)
    profile[13] = min(H, 1e10)

    # L13: Risk
    rb = risk_base(min(1.0, d_tri / (EPSILON + 1e-9)), s_spin, s_spec, 0.9, 0.9, c_qc)
    profile[14] = rb

    # L14: Audio
    s_audio = audio_envelope_coherence(wave)
    profile[15] = s_audio

    return profile


def extract_fractional_entropy(profile: np.ndarray) -> float:
    """
    Compute entropy of fractional components of a drift profile.
    Strips integer part, analyzes decimal tails only.
    """
    fractions = np.array([abs(v) - int(abs(v)) for v in profile if np.isfinite(v)])
    if len(fractions) < 2:
        return 0.0

    # Histogram of fractional parts
    n_bins = min(10, len(fractions))
    hist, _ = np.histogram(fractions, bins=n_bins, range=(0, 1))
    hist = hist[hist > 0]
    total = hist.sum()
    if total == 0:
        return 0.0
    probs = hist / total
    return float(-np.sum(probs * np.log2(probs)))


# ============================================================================
# Attack Simulators
# ============================================================================

def generate_organic_sample(seed: int) -> Tuple[np.ndarray, float]:
    """Generate an organic sample by running the full 14-layer pipeline."""
    np.random.seed(seed)
    t = float(seed) * 0.1
    state = generate_9d_state(t)
    intent = 0.3 + 0.4 * (seed % 10) / 10
    profile = extract_drift_profile(state, intent)
    frac_ent = extract_fractional_entropy(profile)
    return profile, frac_ent


def generate_type_a_attack(seed: int) -> Tuple[np.ndarray, float]:
    """
    Type A: Direct computation attack.
    Attacker computes "reasonable" final values without any pipeline.
    Uses analytics to guess what the pipeline would output.
    """
    np.random.seed(seed + 10000)

    # Attacker knows the approximate ranges but not the exact drift
    profile = np.zeros(16)
    profile[0] = np.random.uniform(0.0, 0.01)       # Realification drift ~small
    profile[1] = np.random.uniform(1.0, 5.0)         # Weight ratio
    profile[2] = np.random.uniform(0.5, 1.0)         # QC coherence
    profile[3] = np.random.uniform(0.5, 3.0)         # E_perp norm
    profile[4] = np.random.uniform(0.3, 0.95)        # Poincare norm
    profile[5] = np.random.uniform(0.5, 3.0)         # Hyperbolic distance
    profile[6] = np.random.uniform(0.3, 0.95)        # Mobius norm
    profile[7] = np.random.uniform(0.3, 0.95)        # Phase norm
    profile[8] = np.random.uniform(0.3, 0.95)        # Breathing norm
    profile[9] = np.random.uniform(0.5, 3.0)         # Realm distance
    profile[10] = np.random.uniform(0.5, 1.0)        # Spectral stability
    profile[11] = np.random.uniform(0.5, 1.0)        # Spin coherence
    profile[12] = np.random.uniform(0.0, 2.0)        # Triadic distance
    profile[13] = np.random.uniform(1.0, 10.0)       # Harmonic scaling
    profile[14] = np.random.uniform(0.0, 1.0)        # Risk
    profile[15] = np.random.uniform(0.5, 1.0)        # Audio coherence

    frac_ent = extract_fractional_entropy(profile)
    return profile, frac_ent


def generate_type_b_attack(seed: int) -> Tuple[np.ndarray, float]:
    """
    Type B: Partial pipeline attack.
    Attacker runs L1-L4 correctly but fakes L5-L14.
    This is a more sophisticated attacker who has access to early layers.
    """
    np.random.seed(seed)
    t = float(seed) * 0.1
    state = generate_9d_state(t)
    intent = 0.3 + 0.4 * (seed % 10) / 10

    profile = np.zeros(16)

    # REAL: L1-L4 (attacker runs these correctly)
    c_complex = state.to_complex_context()
    x = realify(c_complex)
    norm_c = np.sqrt(np.sum(np.abs(c_complex) ** 2))
    norm_x = np.linalg.norm(x)
    profile[0] = abs(norm_x - norm_c)

    g = np.array(TONGUE_WEIGHTS[:len(x)] + TONGUE_WEIGHTS[:len(x)])[:len(x)]
    x_G = apply_spd_weights(x, g)
    profile[1] = np.linalg.norm(x_G) / max(np.linalg.norm(x), 1e-30)

    gate_vector = [
        float(v) if isinstance(v, (int, float))
        else abs(v) if isinstance(v, complex) else 0.0
        for v in state.context[:6]
    ]
    _, r_perp, _ = QUASICRYSTAL.map_gates_to_lattice(gate_vector)
    c_qc = QUASICRYSTAL.e_perp_coherence(gate_vector)
    profile[2] = c_qc
    profile[3] = float(np.linalg.norm(r_perp))

    u = poincare_embed(x_G)
    profile[4] = np.linalg.norm(u)

    # FAKE: L5-L14 (attacker computes analytically, skipping real operations)
    np.random.seed(seed + 20000)
    profile[5] = float(2 * np.arctanh(np.linalg.norm(u)))  # "Correct" formula, wrong numerics
    profile[6] = np.linalg.norm(u) * 0.95  # Approximation
    profile[7] = np.linalg.norm(u) * 0.97  # Approximation
    profile[8] = np.linalg.norm(u) * (1.0 + 0.05)  # Approximation
    profile[9] = float(2 * np.arctanh(np.linalg.norm(u)))  # Same formula
    wave = phase_modulated_intent(intent)
    profile[10] = 0.85  # Fixed guess
    profile[11] = 0.9   # Fixed guess
    profile[12] = np.random.uniform(0.1, 0.5)
    profile[13] = PHI ** (profile[9] ** 2) if profile[9] < 3 else 10.0
    profile[14] = np.random.uniform(0.1, 0.4)
    profile[15] = 0.88  # Fixed guess

    frac_ent = extract_fractional_entropy(profile)
    return profile, frac_ent


def generate_type_c_attack(seed: int) -> Tuple[np.ndarray, float]:
    """
    Type C: Noise injection attack.
    Attacker runs full pipeline but adds small noise to each layer
    to try to mask their modifications. Most sophisticated attack.
    """
    np.random.seed(seed)
    t = float(seed) * 0.1
    state = generate_9d_state(t)
    intent = 0.3 + 0.4 * (seed % 10) / 10

    # Get organic profile
    profile = extract_drift_profile(state, intent)

    # Add attacker noise to each element
    np.random.seed(seed + 30000)
    noise = np.random.normal(0, 0.01, size=len(profile))
    profile = profile + noise

    frac_ent = extract_fractional_entropy(profile)
    return profile, frac_ent


# ============================================================================
# Discrimination Metrics
# ============================================================================

def compute_auc(scores_positive: List[float], scores_negative: List[float]) -> float:
    """Compute AUC using Mann-Whitney U statistic."""
    n_pos = len(scores_positive)
    n_neg = len(scores_negative)
    if n_pos == 0 or n_neg == 0:
        return 0.5

    correct = sum(1 for p in scores_positive for n in scores_negative if p > n)
    ties = sum(1 for p in scores_positive for n in scores_negative if p == n)
    return (correct + 0.5 * ties) / (n_pos * n_neg)


def drift_distance(profile: np.ndarray, reference_mean: np.ndarray) -> float:
    """
    Compute L2 distance between a profile and the organic mean profile.
    This is the simplest possible classifier: how far is this from "normal"?
    """
    return float(np.linalg.norm(profile - reference_mean))


def layer_correlation(profile: np.ndarray, reference_mean: np.ndarray) -> float:
    """
    Compute correlation between a profile and the organic mean.
    High correlation = looks organic. Low = suspicious.
    """
    p = profile - np.mean(profile)
    r = reference_mean - np.mean(reference_mean)
    denom = np.linalg.norm(p) * np.linalg.norm(r)
    if denom < 1e-30:
        return 0.0
    return float(np.dot(p, r) / denom)


def combined_score(
    profile: np.ndarray,
    frac_ent: float,
    ref_mean: np.ndarray,
    ref_frac_ent_mean: float,
) -> float:
    """
    Combined discriminator: drift distance + fractional entropy deviation.

    Lower = more organic. Higher = more suspicious.
    """
    dist = drift_distance(profile, ref_mean)
    ent_dev = abs(frac_ent - ref_frac_ent_mean)
    # Weight distance more heavily
    return dist + 2.0 * ent_dev


# ============================================================================
# Experiment Runner
# ============================================================================

def run_experiment() -> Dict[str, Any]:
    """Run the full decimal drift discrimination experiment."""
    start_time = time.time()

    print("\n" + "=" * 70)
    print("  EXPERIMENT: Decimal Drift Pipeline Fingerprint")
    print("  Testing: Can IEEE 754 drift discriminate organic from synthetic?")
    print("=" * 70)

    n_samples = 200
    results = {}

    # Phase 1: Generate organic baseline
    print(f"\n  Phase 1: Generating {n_samples} organic samples (full pipeline)...")
    organic_profiles = []
    organic_frac_ents = []
    for i in range(n_samples):
        profile, frac_ent = generate_organic_sample(seed=i)
        organic_profiles.append(profile)
        organic_frac_ents.append(frac_ent)

    organic_mean = np.mean(organic_profiles, axis=0)
    organic_std = np.std(organic_profiles, axis=0)
    organic_frac_ent_mean = np.mean(organic_frac_ents)

    print(f"    Organic mean profile (first 8 layers):")
    layer_names = [
        "L1-2_realify", "L3_weight", "L3.5_qc", "L3.5_eperp",
        "L4_poinc", "L5_hyp", "L6_mob", "L7_phase",
        "L8_breath", "L9_realm", "L10_spec", "L10_spin",
        "L11_tri", "L12_harm", "L13_risk", "L14_audio"
    ]
    for j in range(8):
        print(f"      {layer_names[j]:15s}: {organic_mean[j]:.8f} +/- {organic_std[j]:.8f}")
    print(f"    Organic fractional entropy: {organic_frac_ent_mean:.4f}")

    # Phase 2: Generate attack samples
    attack_types = {
        "Type A (no pipeline)": generate_type_a_attack,
        "Type B (partial pipeline)": generate_type_b_attack,
        "Type C (noise injection)": generate_type_c_attack,
    }

    for attack_name, attack_fn in attack_types.items():
        print(f"\n  Phase 2: Testing {attack_name} ({n_samples} samples)...")

        attack_profiles = []
        attack_frac_ents = []
        for i in range(n_samples):
            profile, frac_ent = attack_fn(seed=i)
            attack_profiles.append(profile)
            attack_frac_ents.append(frac_ent)

        attack_mean = np.mean(attack_profiles, axis=0)

        # Compute organic scores (lower = more organic)
        organic_distances = [drift_distance(p, organic_mean) for p in organic_profiles]
        attack_distances = [drift_distance(p, organic_mean) for p in attack_profiles]

        organic_correlations = [layer_correlation(p, organic_mean) for p in organic_profiles]
        attack_correlations = [layer_correlation(p, organic_mean) for p in attack_profiles]

        organic_combined = [
            combined_score(p, e, organic_mean, organic_frac_ent_mean)
            for p, e in zip(organic_profiles, organic_frac_ents)
        ]
        attack_combined = [
            combined_score(p, e, organic_mean, organic_frac_ent_mean)
            for p, e in zip(attack_profiles, attack_frac_ents)
        ]

        # For AUC: organic should have LOWER distance (so negate for "positive = organic")
        auc_distance = compute_auc(attack_distances, organic_distances)
        # For correlation: organic should have HIGHER correlation
        auc_correlation = compute_auc(organic_correlations, attack_correlations)
        # For combined: attack should have HIGHER score
        auc_combined = compute_auc(attack_combined, organic_combined)

        # Layer-by-layer difference
        print(f"\n    Layer-by-layer mean difference (organic - attack):")
        significant_layers = []
        for j in range(16):
            diff = organic_mean[j] - attack_mean[j]
            rel_diff = abs(diff) / max(abs(organic_mean[j]), 1e-10)
            marker = " ***" if rel_diff > 0.1 else ""
            print(f"      {layer_names[j]:15s}: organic={organic_mean[j]:.6f}  "
                  f"attack={attack_mean[j]:.6f}  diff={diff:+.6f} ({rel_diff:.1%}){marker}")
            if rel_diff > 0.1:
                significant_layers.append(layer_names[j])

        print(f"\n    Discrimination metrics:")
        print(f"      Drift distance AUC:  {auc_distance:.4f}")
        print(f"      Correlation AUC:     {auc_correlation:.4f}")
        print(f"      Combined AUC:        {auc_combined:.4f}")
        print(f"      Frac entropy (organic): {organic_frac_ent_mean:.4f} "
              f"(attack): {np.mean(attack_frac_ents):.4f}")

        best_auc = max(auc_distance, auc_correlation, auc_combined)
        best_method = ["distance", "correlation", "combined"][
            [auc_distance, auc_correlation, auc_combined].index(best_auc)
        ]

        results[attack_name] = {
            "auc_distance": auc_distance,
            "auc_correlation": auc_correlation,
            "auc_combined": auc_combined,
            "best_auc": best_auc,
            "best_method": best_method,
            "organic_mean_distance": float(np.mean(organic_distances)),
            "attack_mean_distance": float(np.mean(attack_distances)),
            "organic_frac_entropy": float(organic_frac_ent_mean),
            "attack_frac_entropy": float(np.mean(attack_frac_ents)),
            "significant_layers": significant_layers,
        }

        status = "PROVEN" if best_auc > 0.8 else "MARGINAL" if best_auc > 0.6 else "FAILED"
        print(f"\n    Verdict: {status} (best AUC = {best_auc:.4f} via {best_method})")

    # Phase 3: Combined scoring (phase + drift)
    print("\n" + "=" * 70)
    print("  Phase 3: Phase+Distance+Drift Combined Scoring")
    print("=" * 70)

    # Phase scoring from experiments/exp_flux_tiering_and_trust_cones.py
    # Simulate: organic has matching phase, attacks don't
    from experiments.exp_flux_tiering_and_trust_cones import (
        TONGUE_PHASES, trust_cone_score, create_tongue_cones,
    )

    cones = create_tongue_cones(dim=16, base_angle=30.0, confidence=1.0)
    tongues_list = list(TONGUE_PHASES.keys())

    np.random.seed(42)
    organic_combined_scores = []
    for i in range(n_samples):
        profile, frac_ent = generate_organic_sample(seed=i)
        dist = drift_distance(profile, organic_mean)
        # Organic agents are aligned with a tongue
        tongue = tongues_list[i % 6]
        phase = TONGUE_PHASES[tongue]
        point = np.zeros(16)
        r = 0.3 + 0.3 * (i % 10) / 10
        point[0] = r * math.cos(phase)
        point[1] = r * math.sin(phase)
        cone_score = trust_cone_score(point, tongue, cones)

        # Combined: higher = more organic
        # Invert drift distance (lower dist = more organic)
        drift_score = 1.0 / (1.0 + dist)
        combined = 0.5 * cone_score + 0.5 * drift_score
        organic_combined_scores.append(combined)

    attack_combined_scores = []
    for i in range(n_samples):
        profile, frac_ent = generate_type_a_attack(seed=i)
        dist = drift_distance(profile, organic_mean)
        # Attack agents have no tongue assignment
        point = np.zeros(16)
        r = np.random.uniform(0.3, 0.7)
        angle = np.random.uniform(0, 2 * math.pi)
        point[0] = r * math.cos(angle)
        point[1] = r * math.sin(angle)
        cone_score = trust_cone_score(point, None, cones)

        drift_score = 1.0 / (1.0 + dist)
        combined = 0.5 * cone_score + 0.5 * drift_score
        attack_combined_scores.append(combined)

    auc_phase_drift = compute_auc(organic_combined_scores, attack_combined_scores)

    print(f"\n  Phase+Drift combined AUC: {auc_phase_drift:.4f}")
    print(f"  (vs Phase alone: ~0.6913, Drift alone: {results['Type A (no pipeline)']['best_auc']:.4f})")

    results["phase_plus_drift_combined"] = {
        "auc": auc_phase_drift,
        "organic_mean": float(np.mean(organic_combined_scores)),
        "attack_mean": float(np.mean(attack_combined_scores)),
    }

    improvement = auc_phase_drift > max(0.6913, results["Type A (no pipeline)"]["best_auc"])
    status = "PROVEN" if improvement else "NO IMPROVEMENT"
    print(f"  Combined improves over either alone: {status}")

    # Summary
    duration_ms = (time.time() - start_time) * 1000

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    for name, res in results.items():
        if name == "phase_plus_drift_combined":
            print(f"  Phase+Drift Combined:  AUC = {res['auc']:.4f}")
        else:
            print(f"  {name:30s}: Best AUC = {res['best_auc']:.4f} ({res['best_method']})")

    print(f"\n  Duration: {duration_ms:.1f}ms")

    # Save telemetry
    telemetry = {
        "experiment": "decimal_drift_discrimination",
        "n_samples": n_samples,
        "duration_ms": duration_ms,
        "results": results,
        "organic_profile_mean": organic_mean.tolist(),
        "organic_profile_std": organic_std.tolist(),
        "layer_names": layer_names,
    }

    return telemetry


if __name__ == "__main__":
    telemetry = run_experiment()
    print(f"\n  Experiment complete.")
