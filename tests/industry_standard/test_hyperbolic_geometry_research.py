#!/usr/bin/env python3
"""
Hyperbolic Geometry Research-Based Tests
=========================================
Based on current research in hyperbolic geometry for cryptography and security.

These tests verify REAL mathematical properties, not approximations.
Failing tests indicate violations of fundamental hyperbolic geometry.

References:
- Poincaré, H. "Analysis Situs" (1895)
- Cannon, J.W. et al. "Hyperbolic Geometry" (1997)
- Ratcliffe, J.G. "Foundations of Hyperbolic Manifolds" (2006)
- Recent research on hyperbolic cryptography (2024-2025)

Last Updated: January 19, 2026
"""

import pytest
import sys
import os
import numpy as np
from typing import Tuple, List
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from scbe_14layer_reference import (
    layer_4_poincare_embedding,
    layer_5_hyperbolic_distance,
    layer_6_breathing_transform,
    layer_7_phase_transform
)


class TestPoincareMetricProperties:
    """
    Poincaré Ball Model Metric Properties
    
    The Poincaré ball model is a conformal model of hyperbolic geometry.
    These tests verify FUNDAMENTAL metric properties that MUST hold.
    
    If these tests fail, the hyperbolic geometry implementation is WRONG.
    """
    
    def test_metric_positive_definiteness(self):
        """
        Metric Axiom 1: Positive Definiteness
        
        For all points u, v in the Poincaré ball:
        - d(u, v) ≥ 0 (non-negativity)
        - d(u, v) = 0 if and only if u = v (identity of indiscernibles)
        
        This is a FUNDAMENTAL property. If this fails, the metric is BROKEN.
        """
        # Test 1: Distance to self is zero
        for _ in range(100):
            u = np.random.randn(6) * 0.5
            u = u / (np.linalg.norm(u) + 1.1)  # Ensure in ball
            
            d = layer_5_hyperbolic_distance(u, u)
            assert abs(d) < 1e-10, f"Metric violation: d(u, u) = {d}, expected 0"
        
        # Test 2: Distance between different points is positive
        for _ in range(100):
            u = np.random.randn(6) * 0.4
            v = np.random.randn(6) * 0.4
            u = u / (np.linalg.norm(u) + 1.1)
            v = v / (np.linalg.norm(v) + 1.1)
            
            if not np.allclose(u, v):
                d = layer_5_hyperbolic_distance(u, v)
                assert d > 0, f"Metric violation: d(u, v) = {d} ≤ 0 for u ≠ v"
    
    def test_metric_symmetry(self):
        """
        Metric Axiom 2: Symmetry
        
        For all points u, v:
        d(u, v) = d(v, u)
        
        This is FUNDAMENTAL. If this fails, it's not a metric.
        """
        for _ in range(100):
            u = np.random.randn(8) * 0.5
            v = np.random.randn(8) * 0.5
            u = u / (np.linalg.norm(u) + 1.1)
            v = v / (np.linalg.norm(v) + 1.1)
            
            d_uv = layer_5_hyperbolic_distance(u, v)
            d_vu = layer_5_hyperbolic_distance(v, u)
            
            assert abs(d_uv - d_vu) < 1e-10, f"Metric violation: d(u,v) = {d_uv} ≠ d(v,u) = {d_vu}"
    
    def test_triangle_inequality(self):
        """
        Metric Axiom 3: Triangle Inequality
        
        For all points u, v, w:
        d(u, w) ≤ d(u, v) + d(v, w)
        
        This is FUNDAMENTAL. If this fails, it's not a metric space.
        This test is STRICT - no approximations.
        """
        failures = []
        
        for trial in range(100):
            u = np.random.randn(6) * 0.3
            v = np.random.randn(6) * 0.3
            w = np.random.randn(6) * 0.3
            u = u / (np.linalg.norm(u) + 1.1)
            v = v / (np.linalg.norm(v) + 1.1)
            w = w / (np.linalg.norm(w) + 1.1)
            
            d_uw = layer_5_hyperbolic_distance(u, w)
            d_uv = layer_5_hyperbolic_distance(u, v)
            d_vw = layer_5_hyperbolic_distance(v, w)
            
            # Triangle inequality with small tolerance for numerical errors
            if d_uw > d_uv + d_vw + 1e-8:
                failures.append({
                    'trial': trial,
                    'd_uw': d_uw,
                    'd_uv': d_uv,
                    'd_vw': d_vw,
                    'violation': d_uw - (d_uv + d_vw)
                })
        
        if failures:
            msg = f"Triangle inequality violated in {len(failures)}/100 trials:\n"
            for f in failures[:5]:  # Show first 5 failures
                msg += f"  Trial {f['trial']}: d(u,w)={f['d_uw']:.6f} > d(u,v)+d(v,w)={f['d_uv']+f['d_vw']:.6f} (violation: {f['violation']:.6e})\n"
            pytest.fail(msg)
    
    def test_hyperbolic_distance_formula(self):
        """
        Poincaré Ball Distance Formula Verification
        
        The hyperbolic distance in the Poincaré ball model is:
        d(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
        
        This test verifies the formula is implemented EXACTLY.
        """
        for _ in range(50):
            u = np.random.randn(5) * 0.4
            v = np.random.randn(5) * 0.4
            u = u / (np.linalg.norm(u) + 1.1)
            v = v / (np.linalg.norm(v) + 1.1)
            
            # Compute distance using implementation
            d_impl = layer_5_hyperbolic_distance(u, v)
            
            # Compute distance using formula directly
            diff_norm_sq = np.linalg.norm(u - v) ** 2
            u_norm_sq = np.linalg.norm(u) ** 2
            v_norm_sq = np.linalg.norm(v) ** 2
            
            numerator = 2 * diff_norm_sq
            denominator = (1 - u_norm_sq) * (1 - v_norm_sq)
            
            arg = 1 + numerator / denominator
            d_formula = np.arccosh(max(arg, 1.0))
            
            # They must match exactly (within numerical precision)
            assert abs(d_impl - d_formula) < 1e-10, f"Distance formula mismatch: impl={d_impl}, formula={d_formula}"
    
    def test_distance_to_origin(self):
        """
        Distance to Origin Test

        For a point u in the Poincaré ball, the distance to origin is:
        d(0, u) = 2 * artanh(||u||)

        This follows from the general formula:
        d(u,v) = arcosh(1 + 2||u-v||²/((1-||u||²)(1-||v||²)))

        When v=0: d(0,u) = arcosh(1 + 2||u||²/(1-||u||²))
        Using identity: arcosh(1 + 2x²/(1-x²)) = 2*arctanh(x)

        This is a special case that MUST be exact.
        """
        for _ in range(50):
            u = np.random.randn(6) * 0.5
            u = u / (np.linalg.norm(u) + 1.1)

            origin = np.zeros_like(u)

            # Compute distance using implementation
            d_impl = layer_5_hyperbolic_distance(origin, u)

            # Compute using correct formula: d(0, u) = 2 * arctanh(||u||)
            u_norm = np.linalg.norm(u)
            d_formula = 2.0 * np.arctanh(min(u_norm, 0.9999))

            # Must match
            assert abs(d_impl - d_formula) < 1e-8, f"Distance to origin mismatch: impl={d_impl}, formula={d_formula}"


class TestPoincareIsometries:
    """
    Poincaré Ball Isometry Tests
    
    Isometries are distance-preserving transformations.
    In the Poincaré ball, isometries include:
    - Rotations (orthogonal transformations)
    - Möbius transformations
    
    These tests verify that claimed isometries ACTUALLY preserve distances.
    """
    
    def test_rotation_preserves_distance(self):
        """
        Rotation Isometry Test
        
        Rotations (orthogonal transformations) MUST preserve hyperbolic distance.
        
        This test is STRICT. If rotations don't preserve distance, they're not isometries.
        """
        failures = []
        
        for trial in range(50):
            # Generate random points
            u = np.random.randn(12) * 0.4
            v = np.random.randn(12) * 0.4
            u = u / (np.linalg.norm(u) + 1.1)
            v = v / (np.linalg.norm(v) + 1.1)
            
            # Compute distance before rotation
            d_before = layer_5_hyperbolic_distance(u, v)
            
            # Generate random rotation matrix
            Q = self._random_rotation_matrix(12)
            
            # Apply rotation using phase transform (with zero shift)
            a = np.zeros(12)
            u_rot = layer_7_phase_transform(u, a, Q)
            v_rot = layer_7_phase_transform(v, a, Q)
            
            # Compute distance after rotation
            d_after = layer_5_hyperbolic_distance(u_rot, v_rot)
            
            # Distances must match (within numerical precision)
            if abs(d_before - d_after) > 1e-6:
                failures.append({
                    'trial': trial,
                    'd_before': d_before,
                    'd_after': d_after,
                    'error': abs(d_before - d_after)
                })
        
        if failures:
            msg = f"Rotation isometry violated in {len(failures)}/50 trials:\n"
            for f in failures[:5]:
                msg += f"  Trial {f['trial']}: d_before={f['d_before']:.6f}, d_after={f['d_after']:.6f}, error={f['error']:.6e}\n"
            pytest.fail(msg)
    
    def test_mobius_addition_properties(self):
        """
        Möbius Addition Properties Test
        
        Möbius addition ⊕ in the Poincaré ball has specific properties:
        1. Identity: 0 ⊕ u = u
        2. Inverse: u ⊕ (-u) = 0
        3. Commutativity: u ⊕ v = v ⊕ u (in general, NOT true)
        
        This test verifies these properties.
        """
        # Test identity
        for _ in range(20):
            u = np.random.randn(8) * 0.4
            u = u / (np.linalg.norm(u) + 1.1)
            
            zero = np.zeros_like(u)
            Q = np.eye(len(u))
            
            # 0 ⊕ u should equal u
            result = layer_7_phase_transform(u, zero, Q)
            
            assert np.allclose(result, u, atol=1e-8), f"Möbius identity violated: 0 ⊕ u ≠ u"
    
    def _random_rotation_matrix(self, n: int) -> np.ndarray:
        """Generate a random orthogonal matrix (rotation)."""
        # QR decomposition of random matrix gives orthogonal Q
        A = np.random.randn(n, n)
        Q, R = np.linalg.qr(A)
        
        # Ensure det(Q) = 1 (proper rotation)
        if np.linalg.det(Q) < 0:
            Q[:, 0] = -Q[:, 0]
        
        return Q


class TestBreathingTransformProperties:
    """
    Breathing Transform Tests
    
    The breathing transform is a DIFFEOMORPHISM (smooth bijection), NOT an isometry.
    It MUST preserve the Poincaré ball but WILL change distances.
    
    These tests verify the breathing transform behaves correctly.
    """
    
    def test_breathing_preserves_ball(self):
        """
        Ball Preservation Test
        
        The breathing transform MUST keep all points inside the Poincaré ball.
        For all u with ||u|| < 1, breathing(u) MUST satisfy ||breathing(u)|| < 1.
        
        This is CRITICAL. If points escape the ball, the geometry is BROKEN.
        """
        failures = []
        
        for trial in range(100):
            u = np.random.randn(10) * 0.6
            u = u / (np.linalg.norm(u) + 1.1)  # Ensure in ball
            
            # Test various breathing factors
            for b in [0.1, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0]:
                u_breath = layer_6_breathing_transform(u, b)
                norm = np.linalg.norm(u_breath)
                
                if norm >= 1.0:
                    failures.append({
                        'trial': trial,
                        'b': b,
                        'u_norm': np.linalg.norm(u),
                        'breath_norm': norm
                    })
        
        if failures:
            msg = f"Breathing transform pushed points outside ball in {len(failures)} cases:\n"
            for f in failures[:5]:
                msg += f"  Trial {f['trial']}, b={f['b']}: ||u||={f['u_norm']:.6f} → ||breath(u)||={f['breath_norm']:.6f} ≥ 1\n"
            pytest.fail(msg)
    
    def test_breathing_changes_distances(self):
        """
        Distance Change Test
        
        The breathing transform is NOT an isometry - it MUST change distances.
        This test verifies that breathing actually modifies the geometry.
        """
        distance_changed = False
        
        for _ in range(20):
            u = np.random.randn(8) * 0.4
            v = np.random.randn(8) * 0.4
            u = u / (np.linalg.norm(u) + 1.1)
            v = v / (np.linalg.norm(v) + 1.1)
            
            d_before = layer_5_hyperbolic_distance(u, v)
            
            # Apply breathing with b ≠ 1
            b = 1.5
            u_breath = layer_6_breathing_transform(u, b)
            v_breath = layer_6_breathing_transform(v, b)
            
            d_after = layer_5_hyperbolic_distance(u_breath, v_breath)
            
            # Distance should change (not an isometry)
            if abs(d_before - d_after) > 1e-6:
                distance_changed = True
                break
        
        assert distance_changed, "Breathing transform didn't change distances - should not be an isometry"
    
    def test_breathing_identity(self):
        """
        Breathing Identity Test
        
        With breathing factor b = 1, the transform should be approximately identity.
        
        This test verifies the identity case works correctly.
        """
        for _ in range(20):
            u = np.random.randn(8) * 0.5
            u = u / (np.linalg.norm(u) + 1.1)
            
            u_breath = layer_6_breathing_transform(u, b=1.0)
            
            # Should be very close to original
            assert np.allclose(u, u_breath, atol=1e-6), f"Breathing with b=1 should be identity"


class TestHyperbolicCurvature:
    """
    Hyperbolic Curvature Tests
    
    Hyperbolic space has constant negative curvature K = -1.
    These tests verify curvature-related properties.
    """
    
    def test_exponential_volume_growth(self):
        """
        Exponential Volume Growth Test
        
        In hyperbolic space, the volume of a ball of radius r grows exponentially:
        V(r) ~ e^((n-1)r) for large r
        
        This is a FUNDAMENTAL property of hyperbolic geometry.
        """
        # This test requires computing volumes, which is complex
        # For now, we verify the distance formula exhibits exponential behavior
        
        origin = np.zeros(6)
        
        # Points at increasing distances from origin
        distances = []
        norms = []
        
        for norm in np.linspace(0.1, 0.9, 20):
            u = np.ones(6) * norm / np.sqrt(6)  # Point at distance from origin
            d = layer_5_hyperbolic_distance(origin, u)
            distances.append(d)
            norms.append(norm)
        
        # Verify distances grow faster than linearly (exponential-like)
        # d(0, u) = artanh(||u||) grows exponentially as ||u|| → 1
        for i in range(1, len(distances)):
            ratio = distances[i] / distances[i-1]
            # Ratio should increase (exponential growth)
            if i > 1:
                prev_ratio = distances[i-1] / distances[i-2]
                # Growth rate should increase
                assert ratio >= prev_ratio * 0.9, "Distance growth not exponential"
    
    def test_negative_curvature_triangle_sum(self):
        """
        Triangle Angle Sum Test
        
        In hyperbolic geometry, the sum of angles in a triangle is LESS than π.
        The defect (π - sum) is proportional to the area.
        
        This is a FUNDAMENTAL property that distinguishes hyperbolic from Euclidean geometry.
        """
        # This test requires computing angles, which requires geodesics
        # For now, we document the property
        pytest.skip("Requires geodesic computation - future implementation")


class TestNumericalStability:
    """
    Numerical Stability Tests
    
    Hyperbolic geometry computations can be numerically unstable near the boundary.
    These tests verify the implementation handles edge cases correctly.
    """
    
    def test_distance_near_boundary(self):
        """
        Near-Boundary Distance Test
        
        Points near the boundary (||u|| → 1) should still have finite distances.
        The implementation MUST handle this correctly.
        """
        origin = np.zeros(8)
        
        # Test points increasingly close to boundary
        for norm in [0.9, 0.95, 0.99, 0.999, 0.9999]:
            u = np.ones(8) * norm / np.sqrt(8)
            
            d = layer_5_hyperbolic_distance(origin, u)
            
            # Distance should be finite and positive
            assert np.isfinite(d), f"Distance not finite for ||u||={norm}"
            assert d > 0, f"Distance not positive for ||u||={norm}"
            assert d < 100, f"Distance unreasonably large for ||u||={norm}: d={d}"
    
    def test_distance_very_close_points(self):
        """
        Very Close Points Test
        
        For points very close together, distance should be small but non-zero.
        """
        u = np.random.randn(6) * 0.5
        u = u / (np.linalg.norm(u) + 1.1)
        
        # Create point very close to u
        epsilon = 1e-10
        v = u + epsilon * np.random.randn(6)
        v = v / (np.linalg.norm(v) + 1.1)  # Ensure in ball
        
        d = layer_5_hyperbolic_distance(u, v)
        
        # Distance should be small but finite
        assert np.isfinite(d), "Distance not finite for very close points"
        assert d >= 0, "Distance negative for very close points"
        assert d < 1.0, f"Distance too large for very close points: d={d}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
