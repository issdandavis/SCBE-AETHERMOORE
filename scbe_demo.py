#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Demo - Quantum-Resistant Authorization System

This is a simplified demo of the SCBE-AETHERMOORE 13-layer security stack.
For full implementation, see the main repository.

Author: Isaac Davis / SpiralVerse OS
License: Proprietary - Demo Version
"""

import numpy as np
import hashlib
import hmac
from dataclasses import dataclass
from typing import Tuple

# Golden Ratio - fundamental constant
PHI = (1 + np.sqrt(5)) / 2


def hyperbolic_distance(u: np.ndarray, v: np.ndarray, eps: float = 1e-6) -> float:
    """Poincare ball distance metric - the core invariant."""
    u_norm = np.linalg.norm(u)
    v_norm = np.linalg.norm(v)
    
    if u_norm >= 1.0 - eps:
        u = u * ((1.0 - eps) / u_norm)
    if v_norm >= 1.0 - eps:
        v = v * ((1.0 - eps) / v_norm)
    
    u_norm = np.linalg.norm(u)
    v_norm = np.linalg.norm(v)
    diff_norm_sq = np.linalg.norm(u - v) ** 2
    denom = (1 - u_norm**2) * (1 - v_norm**2)
    
    return float(np.arccosh(max(1.0, 1 + 2 * diff_norm_sq / denom)))


def harmonic_scaling(d_star: float) -> float:
    """H(d*) = exp(d*^2) - The Vertical Wall."""
    return float(np.exp(d_star ** 2))


def anti_fragile_stiffness(pressure: float, psi_max: float = 2.0, beta: float = 3.0) -> float:
    """System gets STRONGER under attack."""
    return 1.0 + (psi_max - 1.0) * np.tanh(beta * pressure)


@dataclass
class AuthorizationResult:
    decision: str  # ALLOW, DENY, THROTTLE
    risk_score: float
    hyperbolic_distance: float
    harmonic_factor: float
    confidence: float


class SCBEDemo:
    """Simplified SCBE-AETHERMOORE verifier for demonstration."""
    
    def __init__(self, key: bytes = b"demo_key"):
        self.key = key
        self.trusted_center = np.array([0.0, 0.0])
        self.risk_threshold = 1.0
        
    def verify(self, identity: str, intent: str, context: dict) -> AuthorizationResult:
        """
        Main verification entry point.
        
        Args:
            identity: User/entity identifier
            intent: Requested action
            context: Additional context (session, timestamp, etc.)
        """
        # Map identity to hyperbolic space
        id_hash = hashlib.sha256(identity.encode()).digest()
        user_point = np.array([
            (id_hash[0] / 255.0) * 0.8 - 0.4,
            (id_hash[1] / 255.0) * 0.8 - 0.4
        ])
        
        # Calculate hyperbolic distance from trusted center
        d_H = hyperbolic_distance(user_point, self.trusted_center)
        
        # Apply harmonic scaling (the vertical wall)
        H = harmonic_scaling(d_H)
        
        # Intent risk factor
        intent_risk = 0.1 if intent in ['read', 'view'] else 0.5
        
        # Composite risk
        risk = intent_risk * H
        
        # Anti-fragile response
        pressure = min(1.0, risk / 10.0)
        stiffness = anti_fragile_stiffness(pressure)
        
        # Final decision
        if risk < self.risk_threshold:
            decision = "ALLOW"
        elif risk < self.risk_threshold * 2:
            decision = "THROTTLE"
        else:
            decision = "DENY"
            
        return AuthorizationResult(
            decision=decision,
            risk_score=risk,
            hyperbolic_distance=d_H,
            harmonic_factor=H,
            confidence=1.0 / (1.0 + risk)
        )


def demo():
    """Run interactive demo."""
    print("="*60)
    print("SCBE-AETHERMOORE Quantum Security Demo")
    print("="*60)
    print()
    
    verifier = SCBEDemo()
    
    # Test cases
    test_cases = [
        ("trusted_user_123", "read", {"session": "valid"}),
        ("unknown_user", "write", {"session": "new"}),
        ("attacker_xyz", "admin_access", {"session": "suspicious"}),
    ]
    
    for identity, intent, context in test_cases:
        result = verifier.verify(identity, intent, context)
        print(f"Identity: {identity}")
        print(f"Intent: {intent}")
        print(f"Decision: {result.decision}")
        print(f"Risk Score: {result.risk_score:.4f}")
        print(f"Hyperbolic Distance: {result.hyperbolic_distance:.4f}")
        print(f"Harmonic Factor H(d*): {result.harmonic_factor:.4f}")
        print(f"Confidence: {result.confidence:.4f}")
        print("-"*40)
    
    print()
    print("Demo complete. See full implementation for all 13 layers.")


if __name__ == "__main__":
    demo()
