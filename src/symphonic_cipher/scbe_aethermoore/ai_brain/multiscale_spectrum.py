"""
Multiscale Spectrum Analysis (Fractal Dimensional Analysis)
==========================================================

@file multiscale_spectrum.py
@module ai_brain/multiscale_spectrum
@layer Layer 9, Layer 10, Layer 14
@component Scale-spectrum analysis for 21D brain state trajectories
@version 1.0.0

Performs "dimensional analysis" on 21D brain state trajectories:
- Multiscale covariance spectra (eigen-scaling signatures)
- Participation ratio as effective dimension measure
- Spectral entropy for complexity estimation
- Anomaly detection via spectrum shape changes

The approach: for each scale s, compute increments X[t+s] - X[t],
build covariance, eigendecompose, then track how the spectrum
changes across scales. Normal behavior has stable scaling;
attacks create rank jumps, heavy tails, or weird slopes.

Integration with SCBE:
- Works on raw 21D state vectors or Poincaré-embedded vectors
- Feeds Layer 9/10 spectral coherence checks
- Provides Layer 14 audio axis diagnostic features
- Detects replay (low rank), chaotic probing (rank explosion),
  slow drift (spectral entropy shift), and mirror compromise
  (asymmetric eigenvalue distribution)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

# 21D brain state dimension layout
BRAIN_DIMENSIONS = 21
SCBE_SLICE = slice(0, 6)       # SCBE Context
NAV_SLICE = slice(6, 12)       # Dual Lattice Navigation
COG_SLICE = slice(12, 15)      # PHDM Cognitive Position
SEM_SLICE = slice(15, 18)      # Sacred Tongues Semantic Phase
SWARM_SLICE = slice(18, 21)    # Swarm Coordination

DEFAULT_SCALES = (1, 2, 4, 8, 16)
EPS = 1e-12


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScaleFeatures:
    """Spectral features at a single scale."""
    scale: int
    participation_ratio: float
    spectral_entropy: float
    top_eigenvalues: List[float]
    effective_rank: float
    condition_number: float


@dataclass(frozen=True)
class MultiscaleReport:
    """Complete multiscale analysis report for a trajectory."""
    scale_features: List[ScaleFeatures]
    anomaly_score: float
    replay_score: float
    chaos_score: float
    drift_score: float
    trajectory_length: int
    dimensions: int


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def compute_increments(
    X: np.ndarray, scale: int
) -> np.ndarray:
    """
    Compute scale-s increments: dX[t] = X[t+s] - X[t].

    Args:
        X: Trajectory matrix (T, D).
        scale: Time scale for differencing.

    Returns:
        Increment matrix (T-s, D).
    """
    if scale <= 0:
        raise ValueError("Scale must be positive.")
    if len(X) <= scale:
        raise ValueError(
            f"Trajectory length {len(X)} too short for scale {scale}."
        )
    return X[scale:] - X[:-scale]


def covariance_spectrum(
    dX: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute eigenvalues and eigenvectors of the covariance matrix.

    Args:
        dX: Centered increment matrix (N, D).

    Returns:
        (eigenvalues descending, eigenvectors as columns).
    """
    dX_centered = dX - dX.mean(axis=0, keepdims=True)
    n = max(len(dX_centered) - 1, 1)
    C = (dX_centered.T @ dX_centered) / n
    evals, evecs = np.linalg.eigh(C)
    # Sort descending
    idx = np.argsort(evals)[::-1]
    return evals[idx], evecs[:, idx]


def participation_ratio(evals: np.ndarray) -> float:
    """
    Participation ratio: (sum(evals))^2 / sum(evals^2).

    High if energy is spread across many modes (complex behavior).
    Low if energy is concentrated in few modes (simple/replay).

    Args:
        evals: Eigenvalues (non-negative).

    Returns:
        Participation ratio in [1, D].
    """
    evals = np.maximum(evals, EPS)
    total = float(evals.sum())
    sq_total = float(np.sum(evals**2))
    return (total**2) / (sq_total + EPS)


def spectral_entropy(evals: np.ndarray) -> float:
    """
    Spectral entropy: -sum(p_i * log(p_i)) where p_i = eval_i / sum(evals).

    Maximum when all eigenvalues are equal (uniform complexity).
    Zero when all energy in one mode.

    Args:
        evals: Eigenvalues (non-negative).

    Returns:
        Spectral entropy in [0, log(D)].
    """
    evals = np.maximum(evals, EPS)
    p = evals / evals.sum()
    return float(-np.sum(p * np.log(p + EPS)))


def effective_rank(evals: np.ndarray) -> float:
    """
    Effective rank: exp(spectral_entropy).

    Continuous generalization of matrix rank.

    Args:
        evals: Eigenvalues (non-negative).

    Returns:
        Effective rank in [1, D].
    """
    return math.exp(spectral_entropy(evals))


def analyze_scale(
    X: np.ndarray, scale: int, top_k: int = 5
) -> ScaleFeatures:
    """
    Compute spectral features at a single scale.

    Args:
        X: Trajectory matrix (T, D).
        scale: Time scale.
        top_k: Number of top eigenvalues to report.

    Returns:
        ScaleFeatures for this scale.
    """
    dX = compute_increments(X, scale)
    evals, _ = covariance_spectrum(dX)
    evals_pos = np.maximum(evals, EPS)

    pr = participation_ratio(evals_pos)
    se = spectral_entropy(evals_pos)
    er = math.exp(se)
    cond = float(evals_pos[0] / evals_pos[-1]) if evals_pos[-1] > EPS else float("inf")

    return ScaleFeatures(
        scale=scale,
        participation_ratio=pr,
        spectral_entropy=se,
        top_eigenvalues=evals_pos[:top_k].tolist(),
        effective_rank=er,
        condition_number=cond,
    )


def multiscale_spectrum_features(
    X: np.ndarray,
    scales: Sequence[int] = DEFAULT_SCALES,
    top_k: int = 5,
) -> List[ScaleFeatures]:
    """
    Compute spectral features across multiple time scales.

    Args:
        X: Trajectory matrix (T, D) — e.g. (T, 21) for brain states.
        scales: Tuple of scales to analyze.
        top_k: Number of top eigenvalues per scale.

    Returns:
        List of ScaleFeatures, one per valid scale.
    """
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError(f"Expected 2D array (T, D), got {X.ndim}D.")

    results = []
    for s in scales:
        if len(X) <= s + 2:
            continue
        results.append(analyze_scale(X, s, top_k))
    return results


# ---------------------------------------------------------------------------
# Anomaly scoring
# ---------------------------------------------------------------------------

def _replay_score(features: List[ScaleFeatures]) -> float:
    """
    Replay/static attack score: low participation ratio across scales.

    Replay attacks produce near-constant trajectories with very low
    effective dimension.

    Returns:
        Score in [0, 1] where 1 = likely replay.
    """
    if not features:
        return 0.0
    prs = [f.participation_ratio for f in features]
    avg_pr = sum(prs) / len(prs)
    D = BRAIN_DIMENSIONS
    # Normalize: PR=1 -> score=1 (pure replay), PR=D -> score=0
    return max(0.0, min(1.0, 1.0 - (avg_pr - 1.0) / max(D - 1.0, 1.0)))


def _chaos_score(features: List[ScaleFeatures]) -> float:
    """
    Chaotic probing score: high effective rank across all scales.

    Random probing attacks produce near-uniform eigenvalue spread
    with effective rank close to D.

    Returns:
        Score in [0, 1] where 1 = likely chaotic probing.
    """
    if not features:
        return 0.0
    ers = [f.effective_rank for f in features]
    avg_er = sum(ers) / len(ers)
    D = BRAIN_DIMENSIONS
    # Normalize: ER close to D -> high chaos score
    return max(0.0, min(1.0, (avg_er - 1.0) / max(D - 1.0, 1.0)))


def _drift_score(features: List[ScaleFeatures]) -> float:
    """
    Slow drift score: spectral entropy changes across scales.

    Normal behavior has roughly consistent spectral entropy.
    Drift attacks show monotonic entropy increase with scale.

    Returns:
        Score in [0, 1] where 1 = significant drift detected.
    """
    if len(features) < 2:
        return 0.0
    entropies = [f.spectral_entropy for f in features]
    # Check for monotonic trend via Spearman-like correlation
    n = len(entropies)
    ranks_x = list(range(n))
    mean_x = (n - 1) / 2.0
    mean_y = sum(entropies) / n
    num = sum((rx - mean_x) * (ey - mean_y) for rx, ey in zip(ranks_x, entropies))
    denom_x = sum((rx - mean_x) ** 2 for rx in ranks_x)
    denom_y = sum((ey - mean_y) ** 2 for ey in entropies)
    denom = math.sqrt(denom_x * denom_y + EPS)
    corr = num / denom if denom > EPS else 0.0
    # Strong positive correlation = drift
    return max(0.0, min(1.0, corr))


def analyze_trajectory(
    X: np.ndarray,
    scales: Sequence[int] = DEFAULT_SCALES,
) -> MultiscaleReport:
    """
    Full multiscale analysis of a 21D brain state trajectory.

    Produces:
    - Per-scale spectral features
    - Anomaly scores for replay, chaos, and drift attack types
    - Combined anomaly score

    Args:
        X: Trajectory matrix (T, 21).
        scales: Time scales to analyze.

    Returns:
        MultiscaleReport with all features and scores.
    """
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError(f"Expected 2D array, got {X.ndim}D.")

    features = multiscale_spectrum_features(X, scales)

    replay = _replay_score(features)
    chaos = _chaos_score(features)
    drift = _drift_score(features)

    # Combined anomaly: max of the three attack scores
    anomaly = max(replay, chaos, drift)

    return MultiscaleReport(
        scale_features=features,
        anomaly_score=anomaly,
        replay_score=replay,
        chaos_score=chaos,
        drift_score=drift,
        trajectory_length=len(X),
        dimensions=X.shape[1] if X.ndim == 2 else 0,
    )


# ---------------------------------------------------------------------------
# Subsystem analysis (analyze specific 21D slices)
# ---------------------------------------------------------------------------

def analyze_subsystem(
    X: np.ndarray,
    subsystem: str,
    scales: Sequence[int] = DEFAULT_SCALES,
) -> MultiscaleReport:
    """
    Analyze a specific subsystem of the 21D brain state.

    Args:
        X: Full 21D trajectory matrix (T, 21).
        subsystem: One of "scbe", "navigation", "cognitive", "semantic", "swarm".
        scales: Time scales.

    Returns:
        MultiscaleReport for the requested subsystem.
    """
    slices = {
        "scbe": SCBE_SLICE,
        "navigation": NAV_SLICE,
        "cognitive": COG_SLICE,
        "semantic": SEM_SLICE,
        "swarm": SWARM_SLICE,
    }
    if subsystem not in slices:
        raise ValueError(
            f"Unknown subsystem '{subsystem}'. "
            f"Choose from: {list(slices.keys())}"
        )
    X = np.asarray(X, dtype=float)
    return analyze_trajectory(X[:, slices[subsystem]], scales)


# ---------------------------------------------------------------------------
# Sliding window analysis (for real-time monitoring)
# ---------------------------------------------------------------------------

def sliding_window_analysis(
    X: np.ndarray,
    window_size: int = 64,
    step: int = 16,
    scales: Sequence[int] = (1, 2, 4, 8),
) -> List[MultiscaleReport]:
    """
    Sliding window multiscale analysis for real-time anomaly detection.

    Args:
        X: Full trajectory (T, D).
        window_size: Number of timesteps per window.
        step: Stride between windows.
        scales: Time scales (should be < window_size).

    Returns:
        List of MultiscaleReports, one per window.
    """
    X = np.asarray(X, dtype=float)
    reports = []
    for start in range(0, len(X) - window_size + 1, step):
        window = X[start : start + window_size]
        reports.append(analyze_trajectory(window, scales))
    return reports
