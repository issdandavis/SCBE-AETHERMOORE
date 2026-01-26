"""
Lorentz Factor for Threat Response
==================================
Relativistic path dilation for security routing.
Suspicious agents experience "time dilation" - their requests
get exponentially slower as threat level approaches maximum.
"""

import numpy as np
from typing import Tuple


def lorentz_factor(v: float, c: float = 1.0) -> float:
    """
    Calculate Lorentz factor γ = 1/√(1 - v²/c²)

    As v → c, γ → ∞ (infinite time dilation)

    Args:
        v: "Velocity" (threat level, 0 to c)
        c: "Speed of light" (maximum threat, normalized to 1.0)

    Returns:
        Lorentz factor γ
    """
    if v >= c:
        return float('inf')
    if v <= 0:
        return 1.0
    return 1.0 / np.sqrt(1 - (v/c)**2)


def dilated_path_cost(
    base_cost: float,
    threat_level: float,
    max_threat: float = 1.0
) -> float:
    """
    Calculate dilated routing cost based on threat level.

    Args:
        base_cost: Base routing cost (e.g., latency, hops)
        threat_level: Agent's threat score (0 = safe, max = attack)
        max_threat: Maximum threat level (default 1.0)

    Returns:
        Dilated cost (base_cost * γ)

    Example:
        >>> dilated_path_cost(10, 0.0)    # Safe: 10.0
        >>> dilated_path_cost(10, 0.9)    # Suspicious: ~23.0
        >>> dilated_path_cost(10, 0.99)   # Malicious: ~71.0
        >>> dilated_path_cost(10, 0.999)  # Attack: ~224.0
    """
    gamma = lorentz_factor(threat_level, max_threat)
    if gamma == float('inf'):
        return float('inf')
    return base_cost * gamma


def threat_velocity(
    anomaly_score: float,
    behavior_score: float,
    reputation_score: float,
    weights: Tuple[float, float, float] = (0.4, 0.3, 0.3)
) -> float:
    """
    Calculate composite threat "velocity" from multiple signals.

    Args:
        anomaly_score: Statistical anomaly detection (0-1)
        behavior_score: Behavioral analysis score (0-1)
        reputation_score: Historical reputation (0-1, inverted)
        weights: Weights for each component

    Returns:
        Threat velocity (0 = safe, 1 = maximum threat)
    """
    w1, w2, w3 = weights

    # Clamp inputs
    anomaly = np.clip(anomaly_score, 0, 1)
    behavior = np.clip(behavior_score, 0, 1)
    reputation = np.clip(1 - reputation_score, 0, 1)  # Invert: high rep = low threat

    v = w1 * anomaly + w2 * behavior + w3 * reputation
    return np.clip(v, 0, 0.9999)  # Never quite reach c


def threat_classification(v: float) -> str:
    """
    Classify threat level based on velocity.

    Args:
        v: Threat velocity (0-1)

    Returns:
        Human-readable classification
    """
    if v < 0.3:
        return "LEGITIMATE"
    elif v < 0.6:
        return "SUSPICIOUS"
    elif v < 0.9:
        return "MALICIOUS"
    else:
        return "ATTACK"
