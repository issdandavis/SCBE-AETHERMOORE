#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Mathematics and Geometry Test Suite with Telemetry
============================================================

Tests advanced mathematical properties, geometric invariants, and topological
constraints of the SCBE system with comprehensive telemetry tracking.

Feature: Advanced Mathematical Validation
Properties: Geometric Invariants, Topological Constraints, Metric Properties
"""

import sys
import os
import time
import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pytest

# Telemetry tracking
@dataclass
class TestTelemetry:
    """Telemetry data for test execution"""
    test_name: str
    category: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    iterations: int = 0
    passed: bool = False
    metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
    
    def complete(self, passed: bool):
        """Mark test as complete and calculate duration"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.passed = passed

class TelemetryCollector:
    """Collects and exports test telemetry"""
    
    def __init__(self):
        self.telemetry: List[TestTelemetry] = []
        self.session_start = time.time()
    
    def start_test(self, name: str, category: str) -> TestTelemetry:
        """Start tracking a test"""
        telem = TestTelemetry(
            test_name=name,
            category=category,
            start_time=time.time()
        )
        self.telemetry.append(telem)
        return telem
    
    def export_json(self, filepath: str = "test_telemetry.json"):
        """Export telemetry to JSON"""
        session_duration = time.time() - self.session_start
        
        # Convert telemetry to JSON-serializable format
        tests_data = []
        for t in self.telemetry:
            test_dict = asdict(t)
            # Ensure all values are JSON-serializable
            test_dict['passed'] = bool(test_dict['passed'])
            test_dict['metrics'] = {k: float(v) for k, v in test_dict['metrics'].items()}
            tests_data.append(test_dict)
        
        data = {
            "session_start": float(self.session_start),
            "session_duration_ms": float(session_duration * 1000),
            "total_tests": int(len(self.telemetry)),
            "passed_tests": int(sum(1 for t in self.telemetry if t.passed)),
            "failed_tests": int(sum(1 for t in self.telemetry if not t.passed)),
            "tests": tests_data
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return data
    
    def print_summary(self):
        """Print telemetry summary"""
        total = len(self.telemetry)
        passed = sum(1 for t in self.telemetry if t.passed)
        failed = total - passed
        
        print("\n" + "=" * 80)
        print("ADVANCED MATHEMATICS TEST TELEMETRY SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ({100*passed/total:.1f}%)")
        print(f"Failed: {failed} ({100*failed/total:.1f}%)")
        print(f"\nBy Category:")
        
        categories = {}
        for t in self.telemetry:
            if t.category not in categories:
                categories[t.category] = {"passed": 0, "failed": 0, "total_ms": 0}
            categories[t.category]["passed" if t.passed else "failed"] += 1
            categories[t.category]["total_ms"] += t.duration_ms
        
        for cat, stats in categories.items():
            total_cat = stats["passed"] + stats["failed"]
            print(f"  {cat}: {stats['passed']}/{total_cat} passed "
                  f"({stats['total_ms']:.2f}ms total)")
        
        print("=" * 80)

# Global telemetry collector
TELEMETRY = TelemetryCollector()


class TestHyperbolicGeometry:
    """Test hyperbolic geometry properties with telemetry"""
    
    def test_poincare_ball_containment(self):
        """Property: All embedded points must satisfy ||u|| < 1"""
        telem = TELEMETRY.start_test(
            "Poincaré Ball Containment",
            "Hyperbolic Geometry"
        )
        
        from scbe_14layer_reference import layer_4_poincare_embedding
        
        iterations = 100
        max_norm = 0.0
        violations = 0
        
        for i in range(iterations):
            # Random input
            x_G = np.random.randn(12) * np.random.uniform(0.1, 100)
            
            # Embed
            u = layer_4_poincare_embedding(x_G)
            norm = np.linalg.norm(u)
            
            max_norm = max(max_norm, norm)
            
            # Check containment
            if norm >= 1.0:
                violations += 1
        
        telem.iterations = iterations
        telem.metrics = {
            "max_norm": float(max_norm),
            "violations": violations,
            "containment_margin": float(1.0 - max_norm)
        }
        
        passed = violations == 0 and max_norm < 1.0
        telem.complete(passed)
        
        assert passed, f"Ball containment violated: {violations} violations, max_norm={max_norm}"
    
    def test_hyperbolic_distance_triangle_inequality(self):
        """Property: d(u,w) ≤ d(u,v) + d(v,w) (triangle inequality)"""
        telem = TELEMETRY.start_test(
            "Triangle Inequality",
            "Hyperbolic Geometry"
        )
        
        from scbe_14layer_reference import layer_5_hyperbolic_distance
        
        iterations = 100
        max_violation = 0.0
        violations = 0
        
        for i in range(iterations):
            # Random points in ball
            u = np.random.rand(12) * 0.7
            v = np.random.rand(12) * 0.7
            w = np.random.rand(12) * 0.7
            
            # Distances
            d_uw = layer_5_hyperbolic_distance(u, w)
            d_uv = layer_5_hyperbolic_distance(u, v)
            d_vw = layer_5_hyperbolic_distance(v, w)
            
            # Check triangle inequality
            violation = d_uw - (d_uv + d_vw)
            if violation > 1e-10:  # Allow numerical tolerance
                violations += 1
                max_violation = max(max_violation, violation)
        
        telem.iterations = iterations
        telem.metrics = {
            "max_violation": float(max_violation),
            "violations": violations
        }
        
        passed = violations == 0
        telem.complete(passed)
        
        assert passed, f"Triangle inequality violated {violations} times, max={max_violation}"
    
    def test_hyperbolic_distance_symmetry(self):
        """Property: d(u,v) = d(v,u) (symmetry)"""
        telem = TELEMETRY.start_test(
            "Distance Symmetry",
            "Hyperbolic Geometry"
        )
        
        from scbe_14layer_reference import layer_5_hyperbolic_distance
        
        iterations = 100
        max_asymmetry = 0.0
        
        for i in range(iterations):
            u = np.random.rand(12) * 0.8
            v = np.random.rand(12) * 0.8
            
            d_uv = layer_5_hyperbolic_distance(u, v)
            d_vu = layer_5_hyperbolic_distance(v, u)
            
            asymmetry = abs(d_uv - d_vu)
            max_asymmetry = max(max_asymmetry, asymmetry)
        
        telem.iterations = iterations
        telem.metrics = {"max_asymmetry": float(max_asymmetry)}
        
        passed = max_asymmetry < 1e-10
        telem.complete(passed)
        
        assert passed, f"Symmetry violated: max asymmetry={max_asymmetry}"
    
    def test_mobius_addition_identity(self):
        """Property: u ⊕ 0 = u (identity element)"""
        telem = TELEMETRY.start_test(
            "Möbius Addition Identity",
            "Hyperbolic Geometry"
        )
        
        # Möbius addition implementation
        def mobius_add(u: np.ndarray, v: np.ndarray) -> np.ndarray:
            uv = np.dot(u, v)
            u_norm_sq = np.dot(u, u)
            v_norm_sq = np.dot(v, v)
            
            num_coeff_u = 1 + 2 * uv + v_norm_sq
            num_coeff_v = 1 - u_norm_sq
            denom = 1 + 2 * uv + u_norm_sq * v_norm_sq
            
            return (num_coeff_u * u + num_coeff_v * v) / denom
        
        iterations = 100
        max_error = 0.0
        
        for i in range(iterations):
            u = np.random.rand(12) * 0.7
            zero = np.zeros(12)
            
            result = mobius_add(u, zero)
            error = np.linalg.norm(result - u)
            max_error = max(max_error, error)
        
        telem.iterations = iterations
        telem.metrics = {"max_identity_error": float(max_error)}
        
        passed = max_error < 1e-10
        telem.complete(passed)
        
        assert passed, f"Identity property violated: max error={max_error}"


class TestIsometryPreservation:
    """Test isometry preservation properties"""
    
    def test_phase_transform_distance_preservation(self):
        """Property: Phase transform preserves hyperbolic distances (isometry)"""
        telem = TELEMETRY.start_test(
            "Phase Transform Isometry",
            "Isometry Preservation"
        )
        
        from scbe_14layer_reference import (
            layer_5_hyperbolic_distance,
            layer_7_phase_transform
        )
        
        iterations = 50
        max_distance_change = 0.0
        
        for i in range(iterations):
            # Random points
            u = np.random.rand(12) * 0.6
            v = np.random.rand(12) * 0.6
            
            # Random rotation (orthogonal matrix)
            Q, _ = np.linalg.qr(np.random.randn(12, 12))
            a = np.zeros(12)
            
            # Distance before transform
            d_before = layer_5_hyperbolic_distance(u, v)
            
            # Apply phase transform
            u_transformed = layer_7_phase_transform(u, a, Q)
            v_transformed = layer_7_phase_transform(v, a, Q)
            
            # Distance after transform
            d_after = layer_5_hyperbolic_distance(u_transformed, v_transformed)
            
            distance_change = abs(d_after - d_before)
            max_distance_change = max(max_distance_change, distance_change)
        
        telem.iterations = iterations
        telem.metrics = {"max_distance_change": float(max_distance_change)}
        
        # Allow small numerical error
        passed = max_distance_change < 0.01
        telem.complete(passed)
        
        assert passed, f"Isometry violated: max distance change={max_distance_change}"
    
    def test_realification_norm_preservation(self):
        """Property: Realification preserves norm (isometry from ℂ^D to ℝ^{2D})"""
        telem = TELEMETRY.start_test(
            "Realification Norm Preservation",
            "Isometry Preservation"
        )
        
        from scbe_14layer_reference import layer_2_realification
        
        iterations = 100
        max_norm_error = 0.0
        
        for i in range(iterations):
            # Random complex vector
            c = np.random.randn(6) + 1j * np.random.randn(6)
            
            # Realify
            x = layer_2_realification(c)
            
            # Check norm preservation
            c_norm = np.linalg.norm(c)
            x_norm = np.linalg.norm(x)
            
            norm_error = abs(c_norm - x_norm)
            max_norm_error = max(max_norm_error, norm_error)
        
        telem.iterations = iterations
        telem.metrics = {"max_norm_error": float(max_norm_error)}
        
        passed = max_norm_error < 1e-10
        telem.complete(passed)
        
        assert passed, f"Norm preservation violated: max error={max_norm_error}"


class TestHarmonicScaling:
    """Test harmonic scaling properties"""
    
    def test_harmonic_scaling_monotonicity(self):
        """Property: H(d) is strictly increasing in d"""
        telem = TELEMETRY.start_test(
            "Harmonic Scaling Monotonicity",
            "Harmonic Scaling"
        )
        
        from scbe_14layer_reference import layer_12_harmonic_scaling
        
        iterations = 100
        violations = 0
        
        for i in range(iterations):
            d1 = np.random.uniform(0, 3)
            d2 = d1 + np.random.uniform(0.01, 0.5)
            
            H1 = layer_12_harmonic_scaling(d1)
            H2 = layer_12_harmonic_scaling(d2)
            
            if H2 <= H1:
                violations += 1
        
        telem.iterations = iterations
        telem.metrics = {"violations": violations}
        
        passed = violations == 0
        telem.complete(passed)
        
        assert passed, f"Monotonicity violated {violations} times"
    
    def test_harmonic_scaling_identity(self):
        """Property: H(0, R) = 1 for all R > 1"""
        telem = TELEMETRY.start_test(
            "Harmonic Scaling Identity",
            "Harmonic Scaling"
        )
        
        from scbe_14layer_reference import layer_12_harmonic_scaling
        
        R_values = [1.5, 2.0, np.e, 3.0, 5.0]
        max_error = 0.0
        
        for R in R_values:
            H_zero = layer_12_harmonic_scaling(0.0, R)
            error = abs(H_zero - 1.0)
            max_error = max(max_error, error)
        
        telem.iterations = len(R_values)
        telem.metrics = {"max_identity_error": float(max_error)}
        
        passed = max_error < 1e-10
        telem.complete(passed)
        
        assert passed, f"Identity H(0)=1 violated: max error={max_error}"
    
    def test_harmonic_scaling_superexponential(self):
        """Property: H(2d) >> 2·H(d) (super-exponential growth)"""
        telem = TELEMETRY.start_test(
            "Harmonic Scaling Super-Exponential",
            "Harmonic Scaling"
        )
        
        from scbe_14layer_reference import layer_12_harmonic_scaling
        
        test_points = [0.5, 1.0, 1.5, 2.0]
        min_ratio = float('inf')
        
        for d in test_points:
            H_d = layer_12_harmonic_scaling(d)
            H_2d = layer_12_harmonic_scaling(2 * d)
            
            # H(2d) should be much greater than 2*H(d)
            ratio = H_2d / (2 * H_d)
            min_ratio = min(min_ratio, ratio)
        
        telem.iterations = len(test_points)
        telem.metrics = {"min_superexp_ratio": float(min_ratio)}
        
        # For super-exponential, ratio should be >> 1
        passed = min_ratio > 2.0
        telem.complete(passed)
        
        assert passed, f"Super-exponential property weak: min ratio={min_ratio}"


class TestTopologicalInvariants:
    """Test topological invariants"""
    
    def test_euler_characteristic_platonic_solids(self):
        """Property: χ = V - E + F = 2 for all Platonic solids"""
        telem = TELEMETRY.start_test(
            "Euler Characteristic (Platonic)",
            "Topological Invariants"
        )
        
        platonic_solids = [
            {"name": "Tetrahedron", "V": 4, "E": 6, "F": 4},
            {"name": "Cube", "V": 8, "E": 12, "F": 6},
            {"name": "Octahedron", "V": 6, "E": 12, "F": 8},
            {"name": "Dodecahedron", "V": 20, "E": 30, "F": 12},
            {"name": "Icosahedron", "V": 12, "E": 30, "F": 20},
        ]
        
        violations = []
        
        for solid in platonic_solids:
            chi = solid["V"] - solid["E"] + solid["F"]
            if chi != 2:
                violations.append(f"{solid['name']}: χ={chi}")
        
        telem.iterations = len(platonic_solids)
        telem.metrics = {"violations": len(violations)}
        
        passed = len(violations) == 0
        telem.complete(passed)
        
        assert passed, f"Euler characteristic violated: {violations}"
    
    def test_genus_euler_relation(self):
        """Property: χ = 2(1 - g) for surfaces of genus g"""
        telem = TELEMETRY.start_test(
            "Genus-Euler Relation",
            "Topological Invariants"
        )
        
        surfaces = [
            {"name": "Sphere", "V": 8, "E": 12, "F": 6, "g": 0},  # Cube
            {"name": "Torus (Szilassi)", "V": 7, "E": 21, "F": 14, "g": 1},
            {"name": "Star (genus 4)", "V": 12, "E": 30, "F": 12, "g": 4},
        ]
        
        violations = []
        
        for surf in surfaces:
            chi = surf["V"] - surf["E"] + surf["F"]
            expected_chi = 2 * (1 - surf["g"])
            if chi != expected_chi:
                violations.append(f"{surf['name']}: χ={chi}, expected={expected_chi}")
        
        telem.iterations = len(surfaces)
        telem.metrics = {"violations": len(violations)}
        
        passed = len(violations) == 0
        telem.complete(passed)
        
        assert passed, f"Genus-Euler relation violated: {violations}"


class TestCoherenceBounds:
    """Test coherence measure bounds"""
    
    def test_coherence_bounds(self):
        """Property: All coherence measures ∈ [0, 1]"""
        telem = TELEMETRY.start_test(
            "Coherence Bounds",
            "Coherence Measures"
        )
        
        from scbe_14layer_reference import (
            layer_9_spectral_coherence,
            layer_10_spin_coherence,
            layer_14_audio_axis
        )
        
        iterations = 50
        violations = []
        
        for i in range(iterations):
            # Random signals
            signal = np.random.randn(256)
            phases = np.random.rand(6) * 2 * np.pi
            audio = np.random.randn(512)
            
            S_spec = layer_9_spectral_coherence(signal)
            C_spin = layer_10_spin_coherence(phases)
            S_audio = layer_14_audio_axis(audio)
            
            if not (0 <= S_spec <= 1):
                violations.append(f"S_spec={S_spec}")
            if not (0 <= C_spin <= 1):
                violations.append(f"C_spin={C_spin}")
            if not (0 <= S_audio <= 1):
                violations.append(f"S_audio={S_audio}")
        
        telem.iterations = iterations * 3
        telem.metrics = {"violations": len(violations)}
        
        passed = len(violations) == 0
        telem.complete(passed)
        
        assert passed, f"Coherence bounds violated: {violations[:5]}"


class TestRiskMonotonicity:
    """Test risk decision monotonicity"""
    
    def test_risk_amplification_monotonicity(self):
        """Property: Risk' increases monotonically with d*"""
        telem = TELEMETRY.start_test(
            "Risk Amplification Monotonicity",
            "Risk Logic"
        )
        
        from scbe_14layer_reference import layer_12_harmonic_scaling
        
        iterations = 50
        violations = 0
        
        Risk_base = 0.3  # Fixed base risk
        
        for i in range(iterations):
            d1 = np.random.uniform(0, 2)
            d2 = d1 + np.random.uniform(0.1, 0.5)
            
            H1 = layer_12_harmonic_scaling(d1)
            H2 = layer_12_harmonic_scaling(d2)
            
            Risk1 = Risk_base * H1
            Risk2 = Risk_base * H2
            
            if Risk2 <= Risk1:
                violations += 1
        
        telem.iterations = iterations
        telem.metrics = {"violations": violations}
        
        passed = violations == 0
        telem.complete(passed)
        
        assert passed, f"Risk monotonicity violated {violations} times"


# Pytest fixtures for telemetry
@pytest.fixture(scope="session", autouse=True)
def export_telemetry(request):
    """Export telemetry at end of session"""
    def finalizer():
        TELEMETRY.print_summary()
        data = TELEMETRY.export_json("tests/test_telemetry_advanced_math.json")
        print(f"\n✓ Telemetry exported to test_telemetry_advanced_math.json")
        print(f"  Total duration: {data['session_duration_ms']:.2f}ms")
    
    request.addfinalizer(finalizer)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
