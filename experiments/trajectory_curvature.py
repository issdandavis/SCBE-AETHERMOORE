#!/usr/bin/env python3
"""
Trajectory Curvature Experiment
===============================

HYPOTHESIS: Hyperbolic curvature accumulation over multi-step trajectories
detects adversarial drift better than Euclidean path length.

WHY THIS MIGHT WORK:
- Unlike single-point scoring (disproven in hyperbolic_vs_baselines.py),
  trajectory curvature in hyperbolic space compounds differently
- Paths near the Poincaré boundary curve more sharply
- Adversarial agents that drift toward the boundary accumulate more curvature
- This is the core insight behind the "geometric firewall" concept

METRICS COMPARED:
1. Euclidean path length: sum of ||p[t+1] - p[t]||
2. Hyperbolic path length: sum of d_H(p[t+1], p[t])
3. Hyperbolic curvature: sum of angular change in hyperbolic geodesics
4. Boundary proximity integral: integral of 1/(1-||p||^2) over trajectory

Author: SCBE-AETHERMOORE Experiments
Date: February 2026
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class TrajectoryConfig:
    """Configuration for trajectory generation"""
    num_agents: int = 20
    num_malicious: int = 5
    num_steps: int = 100
    dim: int = 6
    num_runs: int = 100
    # Trajectory dynamics
    honest_drift: float = 0.002  # Honest agents drift slowly
    malicious_drift: float = 0.015  # Malicious agents drift faster
    noise_std: float = 0.01
    # Hyperbolic parameters
    curvature: float = -1.0  # Poincaré ball curvature


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-10) -> float:
    """
    Compute hyperbolic distance in Poincaré ball.
    d_H(u,v) = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))
    """
    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)

    # Clamp to stay inside ball
    if norm_u >= 1.0:
        u = u * 0.999 / norm_u
        norm_u = 0.999
    if norm_v >= 1.0:
        v = v * 0.999 / norm_v
        norm_v = 0.999

    diff_norm_sq = np.linalg.norm(u - v) ** 2
    denom = (1 - norm_u**2) * (1 - norm_v**2) + eps

    arg = 1 + 2 * diff_norm_sq / denom
    return float(np.arccosh(max(1.0, arg)))


def euclidean_path_length(trajectory: np.ndarray) -> float:
    """Sum of Euclidean distances between consecutive points"""
    diffs = np.diff(trajectory, axis=0)
    return float(np.sum(np.linalg.norm(diffs, axis=1)))


def hyperbolic_path_length(trajectory: np.ndarray) -> float:
    """Sum of hyperbolic distances between consecutive points"""
    total = 0.0
    for t in range(len(trajectory) - 1):
        total += hyperbolic_distance(trajectory[t], trajectory[t+1])
    return total


def hyperbolic_curvature(trajectory: np.ndarray, eps: float = 1e-10) -> float:
    """
    Compute accumulated curvature along trajectory in hyperbolic space.

    Curvature is measured as the sum of angular changes between
    consecutive velocity vectors, weighted by hyperbolic metric.
    """
    if len(trajectory) < 3:
        return 0.0

    total_curvature = 0.0

    for t in range(1, len(trajectory) - 1):
        # Velocity vectors (in tangent space)
        v1 = trajectory[t] - trajectory[t-1]
        v2 = trajectory[t+1] - trajectory[t]

        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)

        if norm_v1 < eps or norm_v2 < eps:
            continue

        # Cosine of angle between velocity vectors
        cos_angle = np.dot(v1, v2) / (norm_v1 * norm_v2)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle)

        # Weight by position's proximity to boundary (hyperbolic metric factor)
        pos_norm = np.linalg.norm(trajectory[t])
        if pos_norm >= 1.0:
            pos_norm = 0.999

        # Metric factor: increases as we approach boundary
        metric_weight = 1.0 / (1.0 - pos_norm**2 + eps)

        total_curvature += angle * metric_weight

    return float(total_curvature)


def boundary_proximity_integral(trajectory: np.ndarray, eps: float = 1e-10) -> float:
    """
    Integral of 1/(1-||p||^2) over trajectory.
    Higher values indicate more time spent near the boundary.
    """
    total = 0.0
    for point in trajectory:
        norm = np.linalg.norm(point)
        if norm >= 1.0:
            norm = 0.999
        total += 1.0 / (1.0 - norm**2 + eps)
    return float(total)


def generate_trajectory(
    start: np.ndarray,
    num_steps: int,
    drift_rate: float,
    noise_std: float,
    is_malicious: bool,
    rng: np.random.Generator
) -> np.ndarray:
    """
    Generate a trajectory with specified dynamics.

    Honest agents: Small random walk with mean-reversion toward origin
    Malicious agents: Gradual drift outward (toward boundary)
    """
    trajectory = np.zeros((num_steps, len(start)))
    trajectory[0] = start.copy()

    for t in range(1, num_steps):
        prev = trajectory[t-1]
        noise = rng.normal(0, noise_std, size=len(start))

        if is_malicious:
            # Drift outward (away from origin)
            norm = np.linalg.norm(prev)
            if norm > 0:
                drift_dir = prev / norm
            else:
                drift_dir = rng.normal(0, 1, size=len(start))
                drift_dir /= np.linalg.norm(drift_dir)

            new_pos = prev + drift_rate * drift_dir + noise
        else:
            # Mean-reversion toward origin with small noise
            new_pos = prev * (1 - drift_rate * 0.1) + noise

        # Clamp to ball
        new_norm = np.linalg.norm(new_pos)
        if new_norm >= 0.999:
            new_pos = new_pos * 0.998 / new_norm

        trajectory[t] = new_pos

    return trajectory


def compute_all_metrics(trajectory: np.ndarray) -> Dict[str, float]:
    """Compute all trajectory metrics"""
    return {
        'euclidean_length': euclidean_path_length(trajectory),
        'hyperbolic_length': hyperbolic_path_length(trajectory),
        'hyperbolic_curvature': hyperbolic_curvature(trajectory),
        'boundary_integral': boundary_proximity_integral(trajectory),
    }


def compute_roc_auc(scores: np.ndarray, labels: np.ndarray, num_thresholds: int = 200) -> Dict:
    """
    Compute ROC curve and AUC.
    labels: 1 = malicious, 0 = honest
    Higher score should indicate malicious.
    """
    min_score, max_score = scores.min(), scores.max()
    if min_score == max_score:
        return {'auc': 0.5, 'optimal_threshold': min_score, 'optimal_tpr': 0.5, 'optimal_fpr': 0.5}

    thresholds = np.linspace(min_score, max_score, num_thresholds)

    tprs = []
    fprs = []

    for thresh in thresholds:
        predicted_positive = scores >= thresh

        tp = np.sum(predicted_positive & (labels == 1))
        fp = np.sum(predicted_positive & (labels == 0))
        fn = np.sum(~predicted_positive & (labels == 1))
        tn = np.sum(~predicted_positive & (labels == 0))

        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

        tprs.append(tpr)
        fprs.append(fpr)

    tprs = np.array(tprs)
    fprs = np.array(fprs)

    # Sort by FPR for AUC calculation
    sorted_idx = np.argsort(fprs)
    fprs_sorted = fprs[sorted_idx]
    tprs_sorted = tprs[sorted_idx]

    # Trapezoidal AUC
    auc = np.trapezoid(tprs_sorted, fprs_sorted)

    # Optimal threshold (Youden's J)
    j_scores = tprs - fprs
    optimal_idx = np.argmax(j_scores)

    return {
        'auc': float(auc),
        'optimal_threshold': float(thresholds[optimal_idx]),
        'optimal_tpr': float(tprs[optimal_idx]),
        'optimal_fpr': float(fprs[optimal_idx]),
        'tpr_at_5pct_fpr': float(tprs[np.argmin(np.abs(fprs - 0.05))]) if np.any(fprs <= 0.05) else 0.0
    }


def run_single_trial(config: TrajectoryConfig, seed: int) -> Dict:
    """Run a single trial with the given seed"""
    rng = np.random.default_rng(seed)

    # Generate starting positions (all near origin)
    starts = rng.normal(0, 0.1, size=(config.num_agents, config.dim))
    for i in range(len(starts)):
        norm = np.linalg.norm(starts[i])
        if norm >= 0.5:
            starts[i] = starts[i] * 0.4 / norm

    # Labels: first num_malicious are malicious
    labels = np.array([1] * config.num_malicious + [0] * (config.num_agents - config.num_malicious))

    # Generate trajectories
    trajectories = []
    for i in range(config.num_agents):
        is_mal = i < config.num_malicious
        traj = generate_trajectory(
            start=starts[i],
            num_steps=config.num_steps,
            drift_rate=config.malicious_drift if is_mal else config.honest_drift,
            noise_std=config.noise_std,
            is_malicious=is_mal,
            rng=rng
        )
        trajectories.append(traj)

    # Compute metrics for each trajectory
    all_metrics = {
        'euclidean_length': [],
        'hyperbolic_length': [],
        'hyperbolic_curvature': [],
        'boundary_integral': [],
    }

    for traj in trajectories:
        metrics = compute_all_metrics(traj)
        for key in all_metrics:
            all_metrics[key].append(metrics[key])

    # Convert to arrays
    for key in all_metrics:
        all_metrics[key] = np.array(all_metrics[key])

    # Compute ROC-AUC for each metric
    results = {}
    for metric_name, scores in all_metrics.items():
        roc = compute_roc_auc(scores, labels)
        results[metric_name] = roc

    return results


def run_experiment(config: TrajectoryConfig) -> Dict:
    """Run full experiment with multiple trials"""
    print(f"\nRunning Trajectory Curvature Experiment...")
    print(f"({config.num_runs} independent runs, {config.num_agents} agents, {config.num_steps} steps)")

    all_results = {metric: [] for metric in ['euclidean_length', 'hyperbolic_length',
                                              'hyperbolic_curvature', 'boundary_integral']}

    for run in range(config.num_runs):
        trial_results = run_single_trial(config, seed=run * 42)
        for metric in all_results:
            all_results[metric].append(trial_results[metric])

    # Aggregate results
    summary = {}
    for metric in all_results:
        aucs = [r['auc'] for r in all_results[metric]]
        tprs = [r['optimal_tpr'] for r in all_results[metric]]
        fprs = [r['optimal_fpr'] for r in all_results[metric]]
        tpr_5fpr = [r['tpr_at_5pct_fpr'] for r in all_results[metric]]

        summary[metric] = {
            'auc': {'mean': np.mean(aucs), 'std': np.std(aucs), 'min': np.min(aucs), 'max': np.max(aucs)},
            'optimal_tpr': {'mean': np.mean(tprs), 'std': np.std(tprs)},
            'optimal_fpr': {'mean': np.mean(fprs), 'std': np.std(fprs)},
            'tpr_at_5pct_fpr': {'mean': np.mean(tpr_5fpr), 'std': np.std(tpr_5fpr)},
        }

    return {'config': config.__dict__, 'summary': summary}


def print_results(results: Dict):
    """Print formatted results"""
    print("\n" + "=" * 80)
    print("  TRAJECTORY CURVATURE EXPERIMENT RESULTS")
    print("=" * 80)

    config = results['config']
    print(f"\n  Config: {config['num_agents']} agents ({config['num_malicious']} malicious)")
    print(f"          {config['num_steps']} steps, {config['dim']}D space, {config['num_runs']} runs")

    print("\n" + "-" * 80)
    print(f"  {'Metric':<25} {'AUC':<20} {'TPR@5%FPR':<20}")
    print("-" * 80)

    summary = results['summary']
    best_metric = None
    best_auc = 0

    for metric, data in summary.items():
        auc_mean = data['auc']['mean']
        auc_std = data['auc']['std']
        tpr_mean = data['tpr_at_5pct_fpr']['mean']
        tpr_std = data['tpr_at_5pct_fpr']['std']

        print(f"  {metric:<25} {auc_mean:.4f} ± {auc_std:.4f}    {tpr_mean:.4f} ± {tpr_std:.4f}")

        if auc_mean > best_auc:
            best_auc = auc_mean
            best_metric = metric

    print("-" * 80)

    # Determine winner
    eucl_auc = summary['euclidean_length']['auc']['mean']
    hyp_length_auc = summary['hyperbolic_length']['auc']['mean']
    hyp_curv_auc = summary['hyperbolic_curvature']['auc']['mean']
    boundary_auc = summary['boundary_integral']['auc']['mean']

    # Check if any hyperbolic metric beats Euclidean
    hyp_wins = (hyp_length_auc > eucl_auc + 0.01 or
                hyp_curv_auc > eucl_auc + 0.01 or
                boundary_auc > eucl_auc + 0.01)

    if hyp_wins:
        print(f"\n  RESULT: HYPERBOLIC METRIC WINS! ({best_metric}: {best_auc:.4f})")
        print(f"  Trajectory curvature analysis VALIDATES geometric approach.")
    else:
        print(f"\n  RESULT: No significant hyperbolic advantage (best: {best_metric})")
        print(f"  Euclidean path length: {eucl_auc:.4f}")

    print("=" * 80)


def main():
    config = TrajectoryConfig(
        num_agents=20,
        num_malicious=5,
        num_steps=100,
        dim=6,
        num_runs=100,
    )

    results = run_experiment(config)
    print_results(results)

    # Save results
    output_path = Path(__file__).parent / "trajectory_curvature_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nFull results saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
