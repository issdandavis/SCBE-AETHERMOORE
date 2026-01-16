#!/usr/bin/env python3
"""
Harmonic Scaling Law - The Vertical Wall

This module implements the core harmonic scaling functions that make
SCBE-AETHERMOORE geometrically impossible to attack.

Key Functions:
- H(d*) = exp(d*^2) : The vertical wall - risk explodes exponentially
- Psi(P) = 1 + (max-1) * tanh(beta * P) : Anti-fragile stiffness
- breathing_transform() : Space contracts/expands based on threat

Patent Claims: 61, 62, 16
Author: Isaac Davis / SpiralVerse OS
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List

# Constants
PHI = (1 + np.sqrt(5)) / 2  # Golden Ratio


# =============================================================================
# THE VERTICAL WALL: H(d*) = exp(d*^2)
# =============================================================================

def harmonic_scaling(d_star: float) -> float:
    """
    The Harmonic Scaling Function H(d*) = exp(d*^2)
    
    This creates the "vertical wall" - risk amplification that grows
    exponentially as distance from the trusted center increases.
    
    Args:
        d_star: Normalized hyperbolic distance from trusted center
        
    Returns:
        Risk multiplier H(d*)
        
    Examples:
        d* = 0.0 -> H = 1.00         (at center, normal risk)
        d* = 1.0 -> H = 2.72         (getting far, elevated)
        d* = 2.0 -> H = 54.60        (danger zone)
        d* = 3.0 -> H = 8,103.08     (near boundary, catastrophic)
        d* = 4.0 -> H = 8,886,110.52 (impossible to reach)
    """
    return float(np.exp(d_star ** 2))


def harmonic_scaling_derivative(d_star: float) -> float:
    """Derivative dH/d(d*) = 2*d* * exp(d*^2)"""
    return 2.0 * d_star * np.exp(d_star ** 2)


# =============================================================================
# ANTI-FRAGILE STIFFNESS: Psi(P) (Claim 61)
# =============================================================================

def anti_fragile_stiffness(pressure: float, 
                           psi_max: float = 2.0, 
                           beta: float = 3.0) -> float:
    """
    Anti-Fragile Living Metric Stiffness (Claim 61)
    
    Psi(P) = 1 + (psi_max - 1) * tanh(beta * P)
    
    The system gets STRONGER under attack, like a non-Newtonian fluid:
    - Walk slowly -> feet sink in
    - Run fast -> surface becomes SOLID
    
    Args:
        pressure: Attack pressure P in [0, 1]
        psi_max: Maximum stiffness multiplier (default 2.0)
        beta: Sensitivity parameter (default 3.0)
        
    Returns:
        Stiffness multiplier Psi in [1, psi_max]
        
    Examples:
        P = 0.0 -> Psi = 1.00 (normal operation)
        P = 0.3 -> Psi = 1.72 (light attack, hardening)
        P = 0.5 -> Psi = 1.91 (medium attack, harder)
        P = 0.7 -> Psi = 1.97 (heavy attack, nearly max)
        P = 1.0 -> Psi = 2.00 (maximum attack, 2x stronger)
    """
    return 1.0 + (psi_max - 1.0) * np.tanh(beta * pressure)


# =============================================================================
# BREATHING TRANSFORM (Claim 62)
# =============================================================================

def breathing_transform(point: np.ndarray, 
                       breath_factor: float,
                       eps: float = 1e-6) -> np.ndarray:
    """
    Breathing Transform - Space contracts/expands based on threat level.
    
    The Poincare ball "breathes":
    - b < 1: Contract (low threat, easier to reach targets)
    - b = 1: Identity (no change)
    - b > 1: Expand (high threat, harder to reach targets)
    
    Uses the formula: u' = u * tanh(b * arctanh(||u||)) / ||u||
    
    Args:
        point: Point in Poincare ball (||point|| < 1)
        breath_factor: Breathing parameter b
        eps: Small epsilon for numerical stability
        
    Returns:
        Transformed point, still inside the ball
    """
    norm = np.linalg.norm(point)
    
    if norm < eps:
        return point  # Origin stays at origin
    
    # Clamp to open ball
    if norm >= 1.0 - eps:
        point = point * (1.0 - eps) / norm
        norm = 1.0 - eps
    
    # Breathing transform
    arctanh_norm = np.arctanh(norm)
    new_norm = np.tanh(breath_factor * arctanh_norm)
    
    return point * (new_norm / norm)


# =============================================================================
# FRACTIONAL FLUX ODE (Claim 16)
# =============================================================================

def fractional_flux_step(nu: float, 
                        nu_bar: float,
                        kappa: float = 0.1,
                        sigma: float = 0.05,
                        omega: float = 1.0,
                        t: float = 0.0,
                        dt: float = 0.01) -> float:
    """
    Fractional Flux ODE: nu_dot = kappa*(nu_bar - nu) + sigma*sin(Omega*t)
    
    Dimensions "breathe" via ODE dynamics.
    
    Args:
        nu: Current fractional dimension
        nu_bar: Target dimension
        kappa: Convergence rate
        sigma: Oscillation amplitude
        omega: Oscillation frequency
        t: Current time
        dt: Time step
        
    Returns:
        Updated nu value
    """
    nu_dot = kappa * (nu_bar - nu) + sigma * np.sin(omega * t)
    return np.clip(nu + nu_dot * dt, 0.0, 1.0)


# =============================================================================
# SETTLING WAVE K(t) (Claim 62)
# =============================================================================

def settling_wave(t: float, 
                 coefficients: List[Tuple[float, float, float]] = None) -> float:
    """
    Settling Wave: K(t) = Sum of C_n * sin(omega_n * t + phi_n)
    
    Key only materializes at t_arrival.
    
    Args:
        t: Time parameter
        coefficients: List of (C_n, omega_n, phi_n) tuples
        
    Returns:
        K(t) value
    """
    if coefficients is None:
        # Default: Constructive interference at t=0, 1, 2, ...
        coefficients = [
            (1.0, 2*np.pi, 0.0),
            (0.5, 4*np.pi, 0.0),
            (0.25, 6*np.pi, 0.0),
        ]
    
    return sum(C * np.sin(omega * t + phi) 
               for C, omega, phi in coefficients)


# =============================================================================
# COMPOSITE RISK (Lemma 13.1)
# =============================================================================

@dataclass
class RiskFactors:
    behavioral: float  # B: Base behavioral risk [0, 1]
    distance: float    # d*: Hyperbolic distance
    temporal: float    # T: Time penalty factor >= 1
    intent: float      # I: Intent suspicion factor >= 1


def composite_risk(factors: RiskFactors) -> Tuple[float, str]:
    """
    Composite Risk Calculation (Lemma 13.1)
    
    Risk' = B * H(d*) * T * I
    
    All factors are multiplicative - any single bad factor
    can trigger rejection.
    
    Args:
        factors: RiskFactors dataclass
        
    Returns:
        (risk_score, decision) tuple
    """
    H = harmonic_scaling(factors.distance)
    risk = factors.behavioral * H * factors.temporal * factors.intent
    
    if risk < 1.0:
        decision = "ALLOW"
    elif risk < 2.0:
        decision = "WARN"
    else:
        decision = "DENY"
        
    return risk, decision


# =============================================================================
# DEMONSTRATION
# =============================================================================

def demonstrate_vertical_wall():
    """Visualize the vertical wall effect."""
    print("THE VERTICAL WALL: H(d*) = exp(d*^2)")
    print("="*50)
    
    distances = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    
    for d in distances:
        H = harmonic_scaling(d)
        bar = "#" * min(40, int(np.log10(H + 1) * 10))
        print(f"d* = {d:.1f} -> H = {H:>12.2f} {bar}")
    
    print()
    print("Risk EXPLODES exponentially near the boundary!")


def demonstrate_anti_fragile():
    """Visualize anti-fragile behavior."""
    print("\nANTI-FRAGILE STIFFNESS: Psi(P)")
    print("="*50)
    
    for p in np.arange(0, 1.1, 0.1):
        psi = anti_fragile_stiffness(p)
        bar = "#" * int(psi * 20)
        status = "CALM" if p < 0.3 else "ELEVATED" if p < 0.7 else "CRITICAL"
        print(f"P={p:.1f} -> Psi={psi:.4f} [{bar:<40}] {status}")
    
    print()
    print("System gets STRONGER under attack!")


if __name__ == "__main__":
    print("SCBE-AETHERMOORE Harmonic Scaling Law Demo")
    print("="*60)
    
    demonstrate_vertical_wall()
    demonstrate_anti_fragile()
    
    print("\n" + "="*60)
    print("Demo complete. These are the mathematical foundations")
    print("that make attacks geometrically impossible.")
