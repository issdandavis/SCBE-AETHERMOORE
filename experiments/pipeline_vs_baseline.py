#!/usr/bin/env python3
"""
End-to-End Pipeline vs Baseline Experiment
===========================================

HYPOTHESIS: The full 14-layer SCBE pipeline produces better detection results
than a simple 2-layer baseline (embedding + threshold).

WHY THIS MATTERS:
If the integrated system doesn't outperform a simple alternative,
the complexity isn't justified.

SYSTEMS COMPARED:
1. BASELINE (2-layer): Euclidean distance from origin + threshold
2. SIMPLE (3-layer): Poincaré embedding + hyperbolic distance + threshold
3. MEDIUM (6-layer): Embedding + breathing + phase + harmonic scaling
4. FULL (14-layer simulation): All SCBE layers including spectral/spin coherence

Author: SCBE-AETHERMOORE Experiments
Date: February 2026
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import json
from pathlib import Path
import time


@dataclass
class PipelineConfig:
    """Configuration for experiment"""
    num_agents: int = 30
    num_malicious: int = 8
    num_steps: int = 50
    dim: int = 6
    num_runs: int = 100
    # Attack sophistication levels
    attack_levels: List[str] = None

    def __post_init__(self):
        if self.attack_levels is None:
            self.attack_levels = ["random", "subtle", "adaptive"]


# =============================================================================
# LAYER IMPLEMENTATIONS
# =============================================================================

def layer_1_complex_context(features: np.ndarray) -> np.ndarray:
    """Layer 1: Convert features to complex representation"""
    # Split into amplitude and phase
    mid = len(features) // 2
    amplitude = np.abs(features[:mid]) if mid > 0 else np.abs(features)
    phase = features[mid:] if mid > 0 else np.zeros_like(features)

    # Create complex vector
    return amplitude * np.exp(1j * phase * np.pi)


def layer_2_realification(complex_vec: np.ndarray) -> np.ndarray:
    """Layer 2: Map complex to real (isometric)"""
    return np.concatenate([np.real(complex_vec), np.imag(complex_vec)])


def layer_3_weighted_transform(real_vec: np.ndarray) -> np.ndarray:
    """Layer 3: Apply golden ratio weights"""
    phi = (1 + np.sqrt(5)) / 2
    weights = np.array([phi ** i for i in range(len(real_vec))])
    weights = weights / np.sum(weights)  # Normalize
    return real_vec * weights


def layer_4_poincare_embed(vec: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """Layer 4: Project to Poincaré ball"""
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return np.tanh(alpha * norm) * vec / norm


def layer_5_hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-10) -> float:
    """Layer 5: Compute hyperbolic distance"""
    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)

    if norm_u >= 1.0:
        u = u * 0.999 / norm_u
        norm_u = 0.999
    if norm_v >= 1.0:
        v = v * 0.999 / norm_v
        norm_v = 0.999

    diff_sq = np.linalg.norm(u - v) ** 2
    denom = (1 - norm_u**2) * (1 - norm_v**2) + eps

    return float(np.arccosh(max(1.0, 1 + 2 * diff_sq / denom)))


def layer_6_breathing(u: np.ndarray, b: float = 1.0, eps: float = 1e-10) -> np.ndarray:
    """Layer 6: Breathing transform"""
    norm = np.linalg.norm(u)
    if norm < eps:
        return u
    if norm >= 1.0:
        norm = 0.999

    artanh_norm = np.arctanh(norm)
    new_norm = np.tanh(b * artanh_norm)
    return new_norm * u / norm


def layer_7_phase_rotation(u: np.ndarray, theta: float = 0.1) -> np.ndarray:
    """Layer 7: Möbius-like phase rotation"""
    # Simple rotation in first two dimensions
    if len(u) < 2:
        return u

    result = u.copy()
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    result[0] = cos_t * u[0] - sin_t * u[1]
    result[1] = sin_t * u[0] + cos_t * u[1]
    return result


def layer_8_realm_distance(u: np.ndarray, realm_centers: List[np.ndarray]) -> float:
    """Layer 8: Distance to nearest realm center"""
    if not realm_centers:
        return layer_5_hyperbolic_distance(u, np.zeros_like(u))

    return min(layer_5_hyperbolic_distance(u, c) for c in realm_centers)


def layer_9_spectral_coherence(trajectory: np.ndarray) -> float:
    """Layer 9: FFT-based spectral coherence"""
    if len(trajectory) < 4:
        return 1.0

    # Compute FFT along trajectory
    fft_result = np.fft.fft(trajectory, axis=0)
    power = np.abs(fft_result) ** 2

    # Low-frequency energy ratio (coherence indicator)
    total_energy = np.sum(power) + 1e-10
    low_freq_energy = np.sum(power[:len(power)//4])

    return float(low_freq_energy / total_energy)


def layer_10_spin_coherence(trajectory: np.ndarray) -> float:
    """Layer 10: Phase alignment coherence"""
    if len(trajectory) < 2:
        return 1.0

    # Compute velocity vectors
    velocities = np.diff(trajectory, axis=0)
    norms = np.linalg.norm(velocities, axis=1)
    valid = norms > 1e-10

    if not np.any(valid):
        return 1.0

    # Normalize velocities
    unit_vels = velocities[valid] / norms[valid, np.newaxis]

    # Coherence = magnitude of mean unit vector
    mean_vel = np.mean(unit_vels, axis=0)
    return float(np.linalg.norm(mean_vel))


def layer_11_triadic_distance(d_immediate: float, d_memory: float, d_governance: float) -> float:
    """Layer 11: Weighted combination of three timescales"""
    weights = [0.5, 0.3, 0.2]  # Immediate, memory, governance
    return np.sqrt(sum(w * d**2 for w, d in zip(weights, [d_immediate, d_memory, d_governance])))


def layer_12_harmonic_scaling(distance: float, phase_deviation: float = 0.0) -> float:
    """Layer 12: Bounded harmonic scaling H(d) = 1/(1 + d + 2*pd)"""
    return 1.0 / (1.0 + distance + 2.0 * phase_deviation)


def layer_13_risk_decision(risk_score: float) -> str:
    """Layer 13: Decision gate"""
    if risk_score < 0.3:
        return "ALLOW"
    elif risk_score < 0.7:
        return "QUARANTINE"
    else:
        return "DENY"


def layer_14_audio_features(trajectory: np.ndarray) -> float:
    """Layer 14: Audio axis (simplified spectral feature)"""
    # Compute energy variation
    energies = np.linalg.norm(trajectory, axis=1)
    return float(np.std(energies))


# =============================================================================
# PIPELINE IMPLEMENTATIONS
# =============================================================================

def baseline_2layer(trajectory: np.ndarray) -> float:
    """
    BASELINE: 2-layer system
    Just Euclidean distance from origin
    """
    final_pos = trajectory[-1]
    return float(np.linalg.norm(final_pos))


def simple_3layer(trajectory: np.ndarray) -> float:
    """
    SIMPLE: 3-layer system
    Poincaré embedding + hyperbolic distance
    """
    final_pos = trajectory[-1]
    embedded = layer_4_poincare_embed(final_pos)
    origin = np.zeros_like(embedded)
    return layer_5_hyperbolic_distance(embedded, origin)


def medium_6layer(trajectory: np.ndarray) -> float:
    """
    MEDIUM: 6-layer system
    Complex → Real → Weighted → Poincaré → Hyperbolic → Harmonic
    """
    final_pos = trajectory[-1]

    # Layers 1-4
    complex_ctx = layer_1_complex_context(final_pos)
    real_ctx = layer_2_realification(complex_ctx)
    weighted = layer_3_weighted_transform(real_ctx)
    embedded = layer_4_poincare_embed(weighted)

    # Layer 5
    origin = np.zeros_like(embedded)
    distance = layer_5_hyperbolic_distance(embedded, origin)

    # Layer 12 (harmonic scaling)
    return layer_12_harmonic_scaling(distance)


def full_14layer(trajectory: np.ndarray) -> float:
    """
    FULL: 14-layer pipeline simulation
    All layers including spectral/spin coherence
    """
    # Process final position through layers 1-7
    final_pos = trajectory[-1]

    complex_ctx = layer_1_complex_context(final_pos)
    real_ctx = layer_2_realification(complex_ctx)
    weighted = layer_3_weighted_transform(real_ctx)
    embedded = layer_4_poincare_embed(weighted)

    # Layer 5: Base distance
    origin = np.zeros_like(embedded)
    base_distance = layer_5_hyperbolic_distance(embedded, origin)

    # Layer 6-7: Breathing and phase
    breathed = layer_6_breathing(embedded, b=1.1)
    phased = layer_7_phase_rotation(breathed, theta=0.05)

    # Layer 8: Realm distance (use origin as single realm center)
    realm_dist = layer_8_realm_distance(phased, [origin])

    # Layers 9-10: Spectral and spin coherence
    spectral = layer_9_spectral_coherence(trajectory)
    spin = layer_10_spin_coherence(trajectory)

    # Layer 11: Triadic distance
    # Use base distance as "immediate", average over trajectory as "memory"
    memory_dist = np.mean([layer_5_hyperbolic_distance(
        layer_4_poincare_embed(layer_3_weighted_transform(layer_2_realification(layer_1_complex_context(p)))),
        origin
    ) for p in trajectory[::5]])  # Sample every 5th point

    governance_dist = base_distance  # Simplified
    triadic = layer_11_triadic_distance(base_distance, memory_dist, governance_dist)

    # Layer 12: Harmonic scaling
    harmonic = layer_12_harmonic_scaling(triadic)

    # Layer 14: Audio features (adds variance penalty)
    audio = layer_14_audio_features(trajectory)

    # Combine all factors
    # Incoherence (low spectral/spin) increases risk
    coherence_penalty = 2.0 - (spectral + spin)  # Higher when incoherent

    return harmonic * (1 + coherence_penalty * 0.1) + audio * 0.1


# =============================================================================
# EXPERIMENT INFRASTRUCTURE
# =============================================================================

def generate_trajectories(config: PipelineConfig, attack_type: str, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    """Generate agent trajectories with specified attack type"""
    rng = np.random.default_rng(seed)

    trajectories = []
    labels = []  # 1 = malicious, 0 = honest

    for i in range(config.num_agents):
        is_malicious = i < config.num_malicious

        # Start near origin
        start = rng.normal(0, 0.1, size=config.dim)
        trajectory = np.zeros((config.num_steps, config.dim))
        trajectory[0] = start

        for t in range(1, config.num_steps):
            prev = trajectory[t-1]

            if is_malicious:
                if attack_type == "random":
                    # Random drift outward
                    drift = rng.normal(0, 0.03, size=config.dim)
                    drift += 0.02 * prev / (np.linalg.norm(prev) + 1e-10)
                elif attack_type == "subtle":
                    # Slow, steady drift
                    drift = 0.01 * prev / (np.linalg.norm(prev) + 1e-10)
                    drift += rng.normal(0, 0.005, size=config.dim)
                elif attack_type == "adaptive":
                    # Mimics honest behavior but with bias
                    honest_drift = -0.01 * prev  # Mean reversion
                    attack_bias = 0.015 * rng.normal(0, 1, size=config.dim)
                    drift = honest_drift + attack_bias
                else:
                    drift = rng.normal(0, 0.02, size=config.dim)
            else:
                # Honest: mean-reverting with small noise
                drift = -0.02 * prev + rng.normal(0, 0.01, size=config.dim)

            new_pos = prev + drift

            # Clamp to ball
            norm = np.linalg.norm(new_pos)
            if norm >= 0.99:
                new_pos = new_pos * 0.98 / norm

            trajectory[t] = new_pos

        trajectories.append(trajectory)
        labels.append(1 if is_malicious else 0)

    return np.array(trajectories), np.array(labels)


def compute_roc_auc(scores: np.ndarray, labels: np.ndarray, num_thresholds: int = 200) -> Dict:
    """Compute ROC-AUC"""
    min_score, max_score = scores.min(), scores.max()
    if min_score == max_score:
        return {'auc': 0.5}

    thresholds = np.linspace(min_score, max_score, num_thresholds)
    tprs, fprs = [], []

    for thresh in thresholds:
        pred_pos = scores >= thresh
        tp = np.sum(pred_pos & (labels == 1))
        fp = np.sum(pred_pos & (labels == 0))
        fn = np.sum(~pred_pos & (labels == 1))
        tn = np.sum(~pred_pos & (labels == 0))

        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        tprs.append(tpr)
        fprs.append(fpr)

    tprs, fprs = np.array(tprs), np.array(fprs)
    sorted_idx = np.argsort(fprs)
    auc = np.trapezoid(tprs[sorted_idx], fprs[sorted_idx])

    return {'auc': float(auc)}


def run_experiment(config: PipelineConfig) -> Dict:
    """Run full experiment"""
    print(f"\nRunning Pipeline vs Baseline Experiment...")
    print(f"({config.num_runs} runs, {config.num_agents} agents, {len(config.attack_levels)} attack types)")

    pipelines = {
        'baseline_2layer': baseline_2layer,
        'simple_3layer': simple_3layer,
        'medium_6layer': medium_6layer,
        'full_14layer': full_14layer,
    }

    results = {attack: {name: [] for name in pipelines} for attack in config.attack_levels}
    timings = {name: [] for name in pipelines}

    for attack_type in config.attack_levels:
        print(f"  Testing attack type: {attack_type}")

        for run in range(config.num_runs):
            trajectories, labels = generate_trajectories(config, attack_type, seed=run * 42)

            for pipe_name, pipe_func in pipelines.items():
                start_time = time.perf_counter()
                scores = np.array([pipe_func(traj) for traj in trajectories])
                elapsed = time.perf_counter() - start_time
                timings[pipe_name].append(elapsed * 1000 / len(trajectories))  # ms per agent

                roc = compute_roc_auc(scores, labels)
                results[attack_type][pipe_name].append(roc['auc'])

    # Aggregate
    summary = {}
    for attack in config.attack_levels:
        summary[attack] = {}
        for pipe_name in pipelines:
            aucs = results[attack][pipe_name]
            summary[attack][pipe_name] = {
                'auc_mean': float(np.mean(aucs)),
                'auc_std': float(np.std(aucs)),
                'auc_min': float(np.min(aucs)),
                'auc_max': float(np.max(aucs)),
            }

    # Timing summary
    timing_summary = {}
    for pipe_name in pipelines:
        timing_summary[pipe_name] = {
            'ms_per_agent_mean': float(np.mean(timings[pipe_name])),
            'ms_per_agent_std': float(np.std(timings[pipe_name])),
        }

    return {
        'config': config.__dict__,
        'results': summary,
        'timing': timing_summary,
    }


def print_results(results: Dict):
    """Print formatted results"""
    print("\n" + "=" * 90)
    print("  PIPELINE vs BASELINE: END-TO-END COMPARISON")
    print("=" * 90)

    config = results['config']
    print(f"\n  Config: {config['num_agents']} agents, {config['num_malicious']} malicious")
    print(f"          {config['num_steps']} steps, {config['num_runs']} runs")

    # Results by attack type
    for attack in config['attack_levels']:
        print(f"\n  Attack Type: {attack.upper()}")
        print("-" * 90)
        print(f"  {'Pipeline':<20} {'AUC':<25} {'Time (ms/agent)':<20}")
        print("-" * 90)

        attack_results = results['results'][attack]
        timing = results['timing']

        best_auc = 0
        best_pipe = None

        for pipe_name in ['baseline_2layer', 'simple_3layer', 'medium_6layer', 'full_14layer']:
            data = attack_results[pipe_name]
            time_data = timing[pipe_name]

            auc_str = f"{data['auc_mean']:.4f} ± {data['auc_std']:.4f}"
            time_str = f"{time_data['ms_per_agent_mean']:.4f}"

            print(f"  {pipe_name:<20} {auc_str:<25} {time_str:<20}")

            if data['auc_mean'] > best_auc:
                best_auc = data['auc_mean']
                best_pipe = pipe_name

        print(f"\n  Best for {attack}: {best_pipe} (AUC: {best_auc:.4f})")

    print("\n" + "=" * 90)

    # Overall verdict
    all_aucs = {pipe: [] for pipe in ['baseline_2layer', 'simple_3layer', 'medium_6layer', 'full_14layer']}
    for attack in config['attack_levels']:
        for pipe in all_aucs:
            all_aucs[pipe].append(results['results'][attack][pipe]['auc_mean'])

    avg_aucs = {pipe: np.mean(aucs) for pipe, aucs in all_aucs.items()}
    overall_best = max(avg_aucs, key=avg_aucs.get)

    baseline_avg = avg_aucs['baseline_2layer']
    full_avg = avg_aucs['full_14layer']
    improvement = (full_avg - baseline_avg) / baseline_avg * 100 if baseline_avg > 0 else 0

    print(f"\n  OVERALL RESULTS:")
    print(f"  - Baseline (2-layer) average AUC: {baseline_avg:.4f}")
    print(f"  - Full (14-layer) average AUC: {full_avg:.4f}")
    print(f"  - Improvement: {improvement:+.1f}%")

    if full_avg > baseline_avg + 0.02:
        print(f"\n  VERDICT: 14-layer pipeline OUTPERFORMS baseline")
        print(f"           Complexity is JUSTIFIED")
    elif full_avg < baseline_avg - 0.02:
        print(f"\n  VERDICT: Baseline OUTPERFORMS 14-layer pipeline")
        print(f"           Complexity is NOT justified")
    else:
        print(f"\n  VERDICT: No significant difference between pipelines")
        print(f"           Consider simpler approach")

    print("=" * 90)


def main():
    config = PipelineConfig(
        num_agents=30,
        num_malicious=8,
        num_steps=50,
        dim=6,
        num_runs=100,
        attack_levels=["random", "subtle", "adaptive"],
    )

    results = run_experiment(config)
    print_results(results)

    # Save results
    output_path = Path(__file__).parent / "pipeline_vs_baseline_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nFull results saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
