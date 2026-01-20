#!/usr/bin/env python3
"""
Performance Benchmark Tests
============================
Based on industry-standard performance requirements for cryptographic systems.

These tests verify REAL performance metrics, not estimates.
Failing tests indicate performance below acceptable thresholds.

References:
- NIST Performance Requirements for PQC
- TLS 1.3 Performance Benchmarks
- Industry Standard Latency Requirements
- Cloud Provider SLAs

Last Updated: January 19, 2026

USAGE:
  Run with: pytest tests/industry_standard/test_performance_benchmarks.py -v -m perf
  Or set: SCBE_RUN_PERF=1 pytest tests/industry_standard/test_performance_benchmarks.py -v
"""

import pytest
import sys
import os
import time
import statistics
import numpy as np
import json
import platform
import tracemalloc
from typing import List, Dict, Tuple
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Mark all tests in this file as performance tests (opt-in)
pytestmark = pytest.mark.perf

# Try to import modules
MODULES_AVAILABLE = False
IMPORT_ERRORS = []

try:
    from scbe_14layer_reference import (
        layer_1_complex_state,
        layer_4_poincare_embedding,
        layer_5_hyperbolic_distance,
        layer_6_breathing_transform,
        layer_14_audio_axis
    )
    MODULES_AVAILABLE = True
except ImportError as e:
    IMPORT_ERRORS.append(f"scbe_14layer_reference: {str(e)}")

# Try to import PQC modules (optional)
PQC_AVAILABLE = False
try:
    from symphonic_cipher.scbe_aethermoore.pqc import pqc_core
    PQC_AVAILABLE = True
except ImportError as e:
    IMPORT_ERRORS.append(f"pqc_core: {str(e)}")

# Evidence directory
EVIDENCE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'evidence')
os.makedirs(EVIDENCE_DIR, exist_ok=True)


# =============================================================================
# HARD-FAIL TEST: Prevent False Green
# =============================================================================
def test_perf_suite_modules_loaded():
    """
    CRITICAL: Module Load Verification Test
    
    This test MUST FAIL if required modules don't load.
    Prevents "false green" where all tests skip silently.
    
    This is NOT optional - it ensures the test suite is actually testing something.
    """
    if not MODULES_AVAILABLE:
        error_msg = "CRITICAL: SCBE modules failed to load!\n"
        error_msg += "This means the performance test suite cannot run.\n"
        error_msg += "Import errors:\n"
        for err in IMPORT_ERRORS:
            error_msg += f"  - {err}\n"
        pytest.fail(error_msg)
    
    # Verify we can actually call the functions
    try:
        test_data = np.array([1.0, 0.5, 0.3, 0.2, 0.1, 0.0] * 2)
        _ = layer_1_complex_state(test_data, D=6)
        _ = layer_4_poincare_embedding(np.random.randn(12))
        _ = layer_5_hyperbolic_distance(np.zeros(6), np.ones(6) * 0.1)
    except Exception as e:
        pytest.fail(f"CRITICAL: SCBE functions not callable: {e}")


def get_system_info() -> dict:
    """Collect system information for evidence reports."""
    return {
        'timestamp': datetime.now().isoformat(),
        'platform': platform.platform(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'numpy_version': np.__version__,
        'cpu_count': os.cpu_count(),
        'modules_available': MODULES_AVAILABLE,
        'pqc_available': PQC_AVAILABLE,
    }


def save_evidence(test_name: str, data: dict):
    """Save test evidence to JSON file."""
    evidence_file = os.path.join(EVIDENCE_DIR, f"{test_name}.json")
    
    evidence = {
        'test_name': test_name,
        'system_info': get_system_info(),
        'results': data
    }
    
    with open(evidence_file, 'w') as f:
        json.dump(evidence, f, indent=2)
    
    print(f"\n[Evidence saved: {evidence_file}]")


# =============================================================================
# PRIMITIVE BENCHMARKS: Individual Layer Performance
# =============================================================================
class TestPrimitiveBenchmarks:
    """
    Primitive Layer Performance Tests
    
    Tests individual SCBE layer functions in isolation.
    These are the building blocks of the system.
    
    Industry requirements:
    - Layer processing: <1ms per layer
    - Hyperbolic distance: <0.1ms
    - Embedding: <1ms
    """
    
    def test_layer1_complex_state_performance(self):
        """
        Layer 1: Complex State Construction Performance
        
        Target: <0.5ms for typical input
        """
        data = np.random.randn(12)
        n_trials = 1000
        times = []
        
        for _ in range(n_trials):
            start = time.perf_counter()
            _ = layer_1_complex_state(data, D=6)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        evidence = {
            'mean_ms': mean_time,
            'p95_ms': p95_time,
            'p99_ms': np.percentile(times, 99),
            'min_ms': min(times),
            'max_ms': max(times),
            'n_trials': n_trials
        }
        save_evidence('layer1_complex_state', evidence)
        
        assert mean_time < 0.5, f"Layer 1 mean time {mean_time:.3f}ms exceeds 0.5ms"
        assert p95_time < 1.0, f"Layer 1 p95 time {p95_time:.3f}ms exceeds 1ms"
    
    def test_layer4_poincare_embedding_performance(self):
        """
        Layer 4: Poincaré Embedding Performance
        
        Target: <1ms for typical input
        """
        n_trials = 1000
        times = []
        
        for _ in range(n_trials):
            x = np.random.randn(12)
            
            start = time.perf_counter()
            _ = layer_4_poincare_embedding(x)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        evidence = {
            'mean_ms': mean_time,
            'p95_ms': p95_time,
            'p99_ms': np.percentile(times, 99),
            'n_trials': n_trials
        }
        save_evidence('layer4_poincare_embedding', evidence)
        
        assert mean_time < 1.0, f"Poincaré embedding mean time {mean_time:.3f}ms exceeds 1ms"
        assert p95_time < 2.0, f"Poincaré embedding p95 time {p95_time:.3f}ms exceeds 2ms"
    
    def test_layer5_hyperbolic_distance_performance(self):
        """
        Layer 5: Hyperbolic Distance Performance
        
        Target: <0.1ms per distance computation
        """
        # Pre-generate points
        points = [np.random.randn(6) * 0.5 for _ in range(1000)]
        points = [p / (np.linalg.norm(p) + 1.1) for p in points]
        
        n_trials = 1000
        times = []
        
        for i in range(n_trials):
            u = points[i % len(points)]
            v = points[(i + 1) % len(points)]
            
            start = time.perf_counter()
            _ = layer_5_hyperbolic_distance(u, v)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        evidence = {
            'mean_ms': mean_time,
            'p95_ms': p95_time,
            'p99_ms': np.percentile(times, 99),
            'n_trials': n_trials
        }
        save_evidence('layer5_hyperbolic_distance', evidence)
        
        assert mean_time < 0.1, f"Hyperbolic distance mean time {mean_time:.4f}ms exceeds 0.1ms"
        assert p95_time < 0.2, f"Hyperbolic distance p95 time {p95_time:.4f}ms exceeds 0.2ms"
    
    def test_layer6_breathing_transform_performance(self):
        """
        Layer 6: Breathing Transform Performance
        
        Target: <1ms for typical input
        """
        n_trials = 1000
        times = []
        
        for _ in range(n_trials):
            u = np.random.randn(8) * 0.5
            u = u / (np.linalg.norm(u) + 1.1)
            
            start = time.perf_counter()
            _ = layer_6_breathing_transform(u, b=1.2)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        evidence = {
            'mean_ms': mean_time,
            'p95_ms': p95_time,
            'n_trials': n_trials
        }
        save_evidence('layer6_breathing_transform', evidence)
        
        assert mean_time < 1.0, f"Breathing transform mean time {mean_time:.3f}ms exceeds 1ms"
    
    def test_layer14_audio_axis_performance(self):
        """
        Layer 14: Audio Axis Performance
        
        Target: <2ms for typical audio frame
        """
        n_trials = 500
        times = []
        
        for _ in range(n_trials):
            audio = np.random.randn(512)
            
            start = time.perf_counter()
            _ = layer_14_audio_axis(audio)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        evidence = {
            'mean_ms': mean_time,
            'p95_ms': p95_time,
            'n_trials': n_trials
        }
        save_evidence('layer14_audio_axis', evidence)
        
        assert mean_time < 2.0, f"Audio axis mean time {mean_time:.2f}ms exceeds 2ms"
        assert p95_time < 5.0, f"Audio axis p95 time {p95_time:.2f}ms exceeds 5ms"


# =============================================================================
# SYSTEM BENCHMARKS: End-to-End Performance
# =============================================================================
class TestSystemBenchmarks:
    """
    System-Level Performance Tests
    
    Tests complete workflows and pipelines.
    These measure real-world performance.
    
    Industry requirements:
    - Full pipeline: <20ms for 1KB
    - Throughput: >50 MB/s
    - Latency: p95 < 50ms
    """
    
    def test_memory_footprint_tracemalloc(self):
        """
        Memory Footprint Test (using tracemalloc)
        
        Target: <50MB memory increase for 1000 operations
        """
        # Start tracing
        tracemalloc.start()
        
        # Get baseline
        baseline = tracemalloc.get_traced_memory()[0]
        
        # Perform operations
        for _ in range(1000):
            data = np.random.randn(12)
            c = layer_1_complex_state(data, D=6)
            u = layer_4_poincare_embedding(np.concatenate([np.real(c), np.imag(c)]))
            _ = layer_5_hyperbolic_distance(u, np.zeros(12))
        
        # Get peak memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_increase_mb = (peak - baseline) / (1024 * 1024)
        
        evidence = {
            'baseline_mb': baseline / (1024 * 1024),
            'peak_mb': peak / (1024 * 1024),
            'increase_mb': memory_increase_mb,
            'operations': 1000
        }
        save_evidence('memory_footprint', evidence)
        
        assert memory_increase_mb < 50.0, f"Memory increase {memory_increase_mb:.1f}MB exceeds 50MB"
    
    def test_concurrent_operations_process_pool(self):
        """
        Concurrent Operations Test (using ProcessPoolExecutor)
        
        Reports speedup metrics instead of asserting specific values.
        Python GIL makes thread-based speedup unreliable.
        """
        from concurrent.futures import ProcessPoolExecutor
        
        def compute_task(seed):
            np.random.seed(seed)
            data = np.random.randn(12)
            c = layer_1_complex_state(data, D=6)
            x = np.concatenate([np.real(c), np.imag(c)])
            u = layer_4_poincare_embedding(x)
            return layer_5_hyperbolic_distance(u, np.zeros(12))
        
        n_tasks = 100
        
        # Sequential
        start = time.perf_counter()
        for i in range(n_tasks):
            compute_task(i)
        sequential_time = time.perf_counter() - start
        
        # Concurrent (4 workers)
        start = time.perf_counter()
        with ProcessPoolExecutor(max_workers=4) as executor:
            list(executor.map(compute_task, range(n_tasks)))
        concurrent_time = time.perf_counter() - start
        
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0
        
        evidence = {
            'sequential_time_s': sequential_time,
            'concurrent_time_s': concurrent_time,
            'speedup': speedup,
            'n_tasks': n_tasks,
            'workers': 4
        }
        save_evidence('concurrent_operations', evidence)
        
        # Report metrics, don't assert (hardware-dependent)
        print(f"\n[Concurrency] Sequential: {sequential_time:.2f}s, Concurrent: {concurrent_time:.2f}s, Speedup: {speedup:.2f}x")


# =============================================================================
# PQC BENCHMARKS: Post-Quantum Cryptography (Optional)
# =============================================================================
@pytest.mark.skipif(not PQC_AVAILABLE, reason="PQC modules not available")
class TestPQCBenchmarks:
    """
    Post-Quantum Cryptography Performance Tests
    
    Tests ML-KEM and ML-DSA performance (if available).
    These are optional - system works without PQC.
    
    Industry requirements:
    - Key generation: <100ms
    - Encapsulation: <5ms
    - Signing: <50ms
    """
    
    def test_mlkem768_keygen_performance(self):
        """
        ML-KEM-768 Key Generation Performance Test
        
        Target: <100ms per keypair
        """
        if not hasattr(pqc_core, 'generate_mlkem768_keypair'):
            pytest.skip("ML-KEM-768 not available")
        
        n_trials = 100
        times = []
        
        for _ in range(n_trials):
            start = time.perf_counter()
            pk, sk = pqc_core.generate_mlkem768_keypair()
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        evidence = {
            'mean_ms': mean_time,
            'p95_ms': p95_time,
            'n_trials': n_trials
        }
        save_evidence('mlkem768_keygen', evidence)
        
        assert mean_time < 100.0, f"ML-KEM-768 keygen mean time {mean_time:.2f}ms exceeds 100ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
