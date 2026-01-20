#!/usr/bin/env python3
"""
Demo: Advanced Mathematics Test Suite with Built-in Telemetry
==============================================================

This demonstrates the telemetry system tracking test execution metrics.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import time
import json
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List

# Import SCBE functions
from scbe_14layer_reference import (
    layer_4_poincare_embedding,
    layer_5_hyperbolic_distance,
    layer_2_realification,
    layer_12_harmonic_scaling,
    layer_9_spectral_coherence,
    layer_10_spin_coherence,
    layer_14_audio_axis
)


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
    
    def export_json(self, filepath: str = "test_telemetry_advanced_math.json"):
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


def test_poincare_ball_containment(collector: TelemetryCollector):
    """Property: All embedded points must satisfy ||u|| < 1"""
    telem = collector.start_test(
        "Poincaré Ball Containment",
        "Hyperbolic Geometry"
    )
    
    iterations = 100
    max_norm = 0.0
    violations = 0
    
    for i in range(iterations):
        x_G = np.random.randn(12) * np.random.uniform(0.1, 100)
        u = layer_4_poincare_embedding(x_G)
        norm = np.linalg.norm(u)
        max_norm = max(max_norm, norm)
        
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
    
    print(f"✓ {telem.test_name}: {'PASS' if passed else 'FAIL'} "
          f"({telem.duration_ms:.2f}ms, {iterations} iterations)")
    return passed


def test_triangle_inequality(collector: TelemetryCollector):
    """Property: d(u,w) ≤ d(u,v) + d(v,w)"""
    telem = collector.start_test(
        "Triangle Inequality",
        "Hyperbolic Geometry"
    )
    
    iterations = 100
    violations = 0
    
    for i in range(iterations):
        u = np.random.rand(12) * 0.7
        v = np.random.rand(12) * 0.7
        w = np.random.rand(12) * 0.7
        
        d_uw = layer_5_hyperbolic_distance(u, w)
        d_uv = layer_5_hyperbolic_distance(u, v)
        d_vw = layer_5_hyperbolic_distance(v, w)
        
        if d_uw > (d_uv + d_vw + 1e-10):
            violations += 1
    
    telem.iterations = iterations
    telem.metrics = {"violations": violations}
    
    passed = violations == 0
    telem.complete(passed)
    
    print(f"✓ {telem.test_name}: {'PASS' if passed else 'FAIL'} "
          f"({telem.duration_ms:.2f}ms, {iterations} iterations)")
    return passed


def test_harmonic_scaling_monotonicity(collector: TelemetryCollector):
    """Property: H(d) is strictly increasing"""
    telem = collector.start_test(
        "Harmonic Scaling Monotonicity",
        "Harmonic Scaling"
    )
    
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
    
    print(f"✓ {telem.test_name}: {'PASS' if passed else 'FAIL'} "
          f"({telem.duration_ms:.2f}ms, {iterations} iterations)")
    return passed


def test_coherence_bounds(collector: TelemetryCollector):
    """Property: All coherence measures ∈ [0, 1]"""
    telem = collector.start_test(
        "Coherence Bounds",
        "Coherence Measures"
    )
    
    iterations = 50
    violations = 0
    
    for i in range(iterations):
        signal = np.random.randn(256)
        phases = np.random.rand(6) * 2 * np.pi
        audio = np.random.randn(512)
        
        S_spec = layer_9_spectral_coherence(signal)
        C_spin = layer_10_spin_coherence(phases)
        S_audio = layer_14_audio_axis(audio)
        
        if not (0 <= S_spec <= 1):
            violations += 1
        if not (0 <= C_spin <= 1):
            violations += 1
        if not (0 <= S_audio <= 1):
            violations += 1
    
    telem.iterations = iterations * 3
    telem.metrics = {"violations": violations}
    
    passed = violations == 0
    telem.complete(passed)
    
    print(f"✓ {telem.test_name}: {'PASS' if passed else 'FAIL'} "
          f"({telem.duration_ms:.2f}ms, {iterations*3} checks)")
    return passed


def test_euler_characteristic(collector: TelemetryCollector):
    """Property: χ = V - E + F = 2 for Platonic solids"""
    telem = collector.start_test(
        "Euler Characteristic",
        "Topological Invariants"
    )
    
    platonic_solids = [
        {"name": "Tetrahedron", "V": 4, "E": 6, "F": 4},
        {"name": "Cube", "V": 8, "E": 12, "F": 6},
        {"name": "Octahedron", "V": 6, "E": 12, "F": 8},
        {"name": "Dodecahedron", "V": 20, "E": 30, "F": 12},
        {"name": "Icosahedron", "V": 12, "E": 30, "F": 20},
    ]
    
    violations = 0
    for solid in platonic_solids:
        chi = solid["V"] - solid["E"] + solid["F"]
        if chi != 2:
            violations += 1
    
    telem.iterations = len(platonic_solids)
    telem.metrics = {"violations": violations}
    
    passed = violations == 0
    telem.complete(passed)
    
    print(f"✓ {telem.test_name}: {'PASS' if passed else 'FAIL'} "
          f"({telem.duration_ms:.2f}ms, {len(platonic_solids)} solids)")
    return passed


def main():
    """Run all tests with telemetry"""
    print("\n" + "=" * 80)
    print("ADVANCED MATHEMATICS TEST SUITE WITH TELEMETRY")
    print("=" * 80)
    print()
    
    collector = TelemetryCollector()
    
    # Run tests
    results = []
    results.append(test_poincare_ball_containment(collector))
    results.append(test_triangle_inequality(collector))
    results.append(test_harmonic_scaling_monotonicity(collector))
    results.append(test_coherence_bounds(collector))
    results.append(test_euler_characteristic(collector))
    
    # Print summary
    collector.print_summary()
    
    # Export telemetry
    data = collector.export_json("test_telemetry_advanced_math.json")
    print(f"\n✓ Telemetry exported to test_telemetry_advanced_math.json")
    print(f"  Session duration: {data['session_duration_ms']:.2f}ms")
    print(f"  Total tests: {data['total_tests']}")
    print(f"  Pass rate: {100*data['passed_tests']/data['total_tests']:.1f}%")
    
    # Return exit code
    return 0 if all(results) else 1


if __name__ == "__main__":
    exit(main())
