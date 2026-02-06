"""
Rigorous Experiment: Hyperbolic vs Euclidean vs Scalar Detection
================================================================

Fair comparison of distance metrics for detecting adversarial agents.

Setup:
- 20 agents (15 honest, 5 malicious)
- 100-step 6D trajectories
- Honest: Mean-reversion to origin + small noise
- Malicious: Outward drift + larger noise
- Same physics for all metrics (no rigging)

Metrics:
- ROC-AUC (proper classification metric)
- Optimal threshold (Youden's J statistic)
- True Positive Rate at fixed False Positive Rate
- Separation score (mean difference / pooled std)

100+ independent runs for statistical significance.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict
import json


@dataclass
class ExperimentConfig:
    """Configuration for the experiment."""
    num_agents: int = 20
    num_malicious: int = 5
    num_steps: int = 100
    dim: int = 6
    num_runs: int = 100

    # Dynamics (identical for all metrics)
    honest_drift_strength: float = 0.05
    honest_noise_scale: float = 0.05
    mal_drift_strength: float = 0.15
    mal_noise_scale: float = 0.20
    ball_radius: float = 0.98


def generate_trajectories(config: ExperimentConfig, seed: int) -> Tuple[List[np.ndarray], np.ndarray]:
    """
    Generate agent trajectories with fair dynamics.

    Honest agents: mean-revert toward origin (trusted center)
    Malicious agents: drift outward (adversarial behavior)

    Same physics applied - metrics compete on equal footing.
    """
    np.random.seed(seed)

    trajectories = []
    labels = []  # 0 = honest, 1 = malicious

    for i in range(config.num_agents):
        is_mal = i >= config.num_agents - config.num_malicious
        pos = np.zeros(config.dim)
        traj = [pos.copy()]

        for _ in range(config.num_steps - 1):
            # Direction: honest pull toward origin, malicious push outward
            norm = np.linalg.norm(pos)
            if norm > 1e-8:
                direction = -pos / norm if not is_mal else pos / norm
            else:
                direction = np.random.randn(config.dim)
                direction /= np.linalg.norm(direction)

            # Drift and noise
            drift_strength = config.honest_drift_strength if not is_mal else config.mal_drift_strength
            noise_scale = config.honest_noise_scale if not is_mal else config.mal_noise_scale

            drift = direction * drift_strength
            noise = np.random.randn(config.dim) * noise_scale
            pos = pos + drift + noise

            # Project to ball interior
            norm = np.linalg.norm(pos)
            if norm > config.ball_radius:
                pos *= config.ball_radius / norm

            traj.append(pos.copy())

        trajectories.append(np.array(traj))
        labels.append(1 if is_mal else 0)

    return trajectories, np.array(labels)


# =============================================================================
# Distance Metrics
# =============================================================================

def euclidean_score(traj: np.ndarray) -> float:
    """Average Euclidean distance from origin over trajectory."""
    norms = np.linalg.norm(traj, axis=1)
    return float(np.mean(norms))


def hyperbolic_score(traj: np.ndarray) -> float:
    """
    Average hyperbolic distance from origin.

    d_H(0, x) = arccosh(1 + 2*||x||^2 / (1 - ||x||^2))

    This captures the exponential growth near the boundary.
    """
    norms = np.linalg.norm(traj, axis=1)
    safe_norms = np.clip(norms, 0, 0.999)  # Avoid division by zero

    # Hyperbolic distance to origin in Poincare ball
    d_h = np.arccosh(1 + 2 * safe_norms**2 / (1 - safe_norms**2 + 1e-10))

    return float(np.mean(d_h))


def scalar_coherence_score(traj: np.ndarray) -> float:
    """
    Simple scalar coherence: inverse of variance + distance.

    Higher coherence = more stable/trusted behavior.
    Returns negative score so higher = more suspicious (for consistent ROC).
    """
    variance = np.var(traj, axis=0).mean()
    mean_dist = np.mean(np.linalg.norm(traj, axis=1))
    coherence = 1 / (1 + variance + mean_dist)

    # Invert so higher score = more suspicious
    return -coherence


# =============================================================================
# ROC Analysis
# =============================================================================

def compute_roc(scores: np.ndarray, labels: np.ndarray, num_thresholds: int = 200) -> Dict:
    """
    Compute ROC curve and AUC.

    Higher score = predicted malicious.
    """
    min_score = np.min(scores)
    max_score = np.max(scores)
    thresholds = np.linspace(min_score - 0.01, max_score + 0.01, num_thresholds)

    tprs = []
    fprs = []

    n_pos = np.sum(labels == 1)
    n_neg = np.sum(labels == 0)

    for thresh in thresholds:
        predictions = (scores >= thresh).astype(int)

        tp = np.sum((predictions == 1) & (labels == 1))
        fp = np.sum((predictions == 1) & (labels == 0))

        tpr = tp / max(1, n_pos)
        fpr = fp / max(1, n_neg)

        tprs.append(tpr)
        fprs.append(fpr)

    tprs = np.array(tprs)
    fprs = np.array(fprs)

    # Sort by FPR for proper AUC calculation
    sorted_idx = np.argsort(fprs)
    fprs_sorted = fprs[sorted_idx]
    tprs_sorted = tprs[sorted_idx]

    # Trapezoidal AUC
    auc = np.trapezoid(tprs_sorted, fprs_sorted)

    # Optimal threshold (Youden's J = TPR - FPR)
    j_scores = tprs - fprs
    optimal_idx = np.argmax(j_scores)
    optimal_threshold = thresholds[optimal_idx]
    optimal_tpr = tprs[optimal_idx]
    optimal_fpr = fprs[optimal_idx]

    # TPR at 5% FPR (practical constraint)
    idx_5pct = np.argmin(np.abs(fprs - 0.05))
    tpr_at_5pct_fpr = tprs[idx_5pct]

    return {
        'auc': float(auc),
        'optimal_threshold': float(optimal_threshold),
        'optimal_tpr': float(optimal_tpr),
        'optimal_fpr': float(optimal_fpr),
        'tpr_at_5pct_fpr': float(tpr_at_5pct_fpr),
        'fprs': fprs.tolist(),
        'tprs': tprs.tolist(),
        'thresholds': thresholds.tolist()
    }


def separation_score(honest_scores: List[float], mal_scores: List[float]) -> float:
    """
    Cohen's d-like separation: (mean_mal - mean_honest) / pooled_std

    Higher positive = better separation.
    """
    mean_h = np.mean(honest_scores)
    mean_m = np.mean(mal_scores)
    std_h = np.std(honest_scores)
    std_m = np.std(mal_scores)
    pooled_std = np.sqrt((std_h**2 + std_m**2) / 2)

    return float((mean_m - mean_h) / (pooled_std + 1e-10))


# =============================================================================
# Experiment Runner
# =============================================================================

def run_single_trial(config: ExperimentConfig, seed: int) -> Dict:
    """Run a single trial and compute all metrics."""
    trajectories, labels = generate_trajectories(config, seed)

    # Compute scores for each metric
    eucl_scores = np.array([euclidean_score(t) for t in trajectories])
    hyper_scores = np.array([hyperbolic_score(t) for t in trajectories])
    scalar_scores = np.array([scalar_coherence_score(t) for t in trajectories])

    # ROC analysis for each
    eucl_roc = compute_roc(eucl_scores, labels)
    hyper_roc = compute_roc(hyper_scores, labels)
    scalar_roc = compute_roc(scalar_scores, labels)

    # Separation scores
    honest_mask = labels == 0
    mal_mask = labels == 1

    eucl_sep = separation_score(
        eucl_scores[honest_mask].tolist(),
        eucl_scores[mal_mask].tolist()
    )
    hyper_sep = separation_score(
        hyper_scores[honest_mask].tolist(),
        hyper_scores[mal_mask].tolist()
    )
    scalar_sep = separation_score(
        scalar_scores[honest_mask].tolist(),
        scalar_scores[mal_mask].tolist()
    )

    return {
        'euclidean': {
            'auc': eucl_roc['auc'],
            'optimal_tpr': eucl_roc['optimal_tpr'],
            'optimal_fpr': eucl_roc['optimal_fpr'],
            'tpr_at_5pct_fpr': eucl_roc['tpr_at_5pct_fpr'],
            'separation': eucl_sep
        },
        'hyperbolic': {
            'auc': hyper_roc['auc'],
            'optimal_tpr': hyper_roc['optimal_tpr'],
            'optimal_fpr': hyper_roc['optimal_fpr'],
            'tpr_at_5pct_fpr': hyper_roc['tpr_at_5pct_fpr'],
            'separation': hyper_sep
        },
        'scalar': {
            'auc': scalar_roc['auc'],
            'optimal_tpr': scalar_roc['optimal_tpr'],
            'optimal_fpr': scalar_roc['optimal_fpr'],
            'tpr_at_5pct_fpr': scalar_roc['tpr_at_5pct_fpr'],
            'separation': scalar_sep
        }
    }


def run_experiment(config: ExperimentConfig = None) -> Dict:
    """Run full experiment with multiple trials."""
    if config is None:
        config = ExperimentConfig()

    results = {
        'euclidean': {'auc': [], 'optimal_tpr': [], 'optimal_fpr': [], 'tpr_at_5pct_fpr': [], 'separation': []},
        'hyperbolic': {'auc': [], 'optimal_tpr': [], 'optimal_fpr': [], 'tpr_at_5pct_fpr': [], 'separation': []},
        'scalar': {'auc': [], 'optimal_tpr': [], 'optimal_fpr': [], 'tpr_at_5pct_fpr': [], 'separation': []}
    }

    for seed in range(config.num_runs):
        trial = run_single_trial(config, seed)

        for metric in ['euclidean', 'hyperbolic', 'scalar']:
            for key in results[metric]:
                results[metric][key].append(trial[metric][key])

    # Compute summary statistics
    summary = {}
    for metric in ['euclidean', 'hyperbolic', 'scalar']:
        summary[metric] = {}
        for key in results[metric]:
            values = results[metric][key]
            summary[metric][key] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values))
            }

    return {
        'config': {
            'num_agents': config.num_agents,
            'num_malicious': config.num_malicious,
            'num_steps': config.num_steps,
            'dim': config.dim,
            'num_runs': config.num_runs
        },
        'raw_results': results,
        'summary': summary
    }


def print_results(results: Dict):
    """Pretty-print experiment results."""
    print("\n" + "=" * 70)
    print("  HYPERBOLIC vs EUCLIDEAN vs SCALAR: ROC Analysis")
    print("=" * 70)

    config = results['config']
    print(f"\n  Config: {config['num_agents']} agents ({config['num_malicious']} malicious)")
    print(f"          {config['num_steps']} steps, {config['dim']}D space, {config['num_runs']} runs")

    print("\n" + "-" * 70)
    print(f"  {'Metric':<15} {'AUC':<18} {'TPR@5%FPR':<18} {'Separation':<18}")
    print("-" * 70)

    for metric in ['hyperbolic', 'euclidean', 'scalar']:
        s = results['summary'][metric]
        auc = f"{s['auc']['mean']:.3f} ± {s['auc']['std']:.3f}"
        tpr = f"{s['tpr_at_5pct_fpr']['mean']:.3f} ± {s['tpr_at_5pct_fpr']['std']:.3f}"
        sep = f"{s['separation']['mean']:.1f} ± {s['separation']['std']:.1f}"

        print(f"  {metric:<15} {auc:<18} {tpr:<18} {sep:<18}")

    print("-" * 70)

    # Winner analysis
    hyper_auc = results['summary']['hyperbolic']['auc']['mean']
    eucl_auc = results['summary']['euclidean']['auc']['mean']
    scalar_auc = results['summary']['scalar']['auc']['mean']

    if hyper_auc > eucl_auc and hyper_auc > scalar_auc:
        improvement_vs_eucl = (hyper_auc - eucl_auc) / eucl_auc * 100
        improvement_vs_scalar = (hyper_auc - scalar_auc) / scalar_auc * 100
        print(f"\n  RESULT: Hyperbolic wins")
        print(f"          +{improvement_vs_eucl:.1f}% vs Euclidean, +{improvement_vs_scalar:.1f}% vs Scalar")
    elif eucl_auc > hyper_auc:
        print(f"\n  RESULT: Euclidean wins (hyperbolic does NOT outperform)")
    else:
        print(f"\n  RESULT: Scalar wins (unexpected)")

    print("=" * 70 + "\n")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\nRunning fair experiment: Hyperbolic vs Baselines...")
    print("(100 independent runs, identical physics for all metrics)\n")

    config = ExperimentConfig(num_runs=100)
    results = run_experiment(config)

    print_results(results)

    # Save full results
    with open('experiments/hyperbolic_experiment_results.json', 'w') as f:
        # Convert numpy arrays to lists for JSON
        json.dump({
            'config': results['config'],
            'summary': results['summary']
        }, f, indent=2)

    print("Full results saved to experiments/hyperbolic_experiment_results.json")
