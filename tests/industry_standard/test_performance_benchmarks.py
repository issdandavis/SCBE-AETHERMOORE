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
"""

import pytest
import sys
import os
import time
import statistics
import numpy as np
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Try to import modules
try:
    from symphonic_cipher.scbe_aethermoore.pqc import pqc_core
    from scbe_14layer_reference import (
        layer_1_context_encoding,
        layer_4_poincare_embedding,
        layer_5_hyperbolic_distance,
        layer_14_topological_cfi
    )
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class TestCryptographicPerformance:
    """
    Cryptographic Operation Performance Tests
    
    Industry requirements:
    - Key generation: <100ms
    - Encryption: <10ms for 1KB
    - Decryption: <10ms for 1KB
    - Signing: <50ms
    - Verification: <20ms
    
    These tests verify REAL performance.
    """
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_mlkem768_keygen_performance(self):
        """
        ML-KEM-768 Key Generation Performance Test
        
        Target: <100ms per keypair
        Industry standard for acceptable key generation time.
        
        This test WILL FAIL if key generation is too slow.
        """
        if not hasattr(pqc_core, 'generate_mlkem768_keypair'):
            pytest.skip("ML-KEM-768 not available")
        
        n_trials = 100
        times = []
        
        for _ in range(n_trials):
            start = time.perf_counter()
            pk, sk = pqc_core.generate_mlkem768_keypair()
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)  # Convert to ms
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        assert mean_time < 100.0, f"ML-KEM-768 keygen mean time {mean_time:.2f}ms exceeds 100ms"
        assert p95_time < 150.0, f"ML-KEM-768 keygen p95 time {p95_time:.2f}ms exceeds 150ms"
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_mlkem768_encap_decap_performance(self):
        """
        ML-KEM-768 Encapsulation/Decapsulation Performance Test
        
        Target: <10ms for encap+decap
        Critical for TLS handshake performance.
        
        This test WILL FAIL if KEM operations are too slow.
        """
        if not hasattr(pqc_core, 'mlkem768_encapsulate'):
            pytest.skip("ML-KEM-768 not available")
        
        # Generate keypair once
        pk, sk = pqc_core.generate_mlkem768_keypair()
        
        n_trials = 1000
        encap_times = []
        decap_times = []
        
        for _ in range(n_trials):
            # Measure encapsulation
            start = time.perf_counter()
            ct, ss1 = pqc_core.mlkem768_encapsulate(pk)
            encap_times.append((time.perf_counter() - start) * 1000)
            
            # Measure decapsulation
            start = time.perf_counter()
            ss2 = pqc_core.mlkem768_decapsulate(ct, sk)
            decap_times.append((time.perf_counter() - start) * 1000)
        
        mean_encap = statistics.mean(encap_times)
        mean_decap = statistics.mean(decap_times)
        mean_total = mean_encap + mean_decap
        
        assert mean_encap < 5.0, f"ML-KEM-768 encap mean time {mean_encap:.2f}ms exceeds 5ms"
        assert mean_decap < 5.0, f"ML-KEM-768 decap mean time {mean_decap:.2f}ms exceeds 5ms"
        assert mean_total < 10.0, f"ML-KEM-768 total time {mean_total:.2f}ms exceeds 10ms"
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_mldsa65_sign_verify_performance(self):
        """
        ML-DSA-65 Sign/Verify Performance Test
        
        Target: <50ms for signing, <20ms for verification
        Critical for certificate validation and code signing.
        
        This test WILL FAIL if signature operations are too slow.
        """
        if not hasattr(pqc_core, 'mldsa65_sign'):
            pytest.skip("ML-DSA-65 not available")
        
        # Generate keypair once
        pk, sk = pqc_core.generate_mldsa65_keypair()
        message = b"Performance test message" * 10  # 240 bytes
        
        n_trials = 500
        sign_times = []
        verify_times = []
        
        for _ in range(n_trials):
            # Measure signing
            start = time.perf_counter()
            signature = pqc_core.mldsa65_sign(message, sk)
            sign_times.append((time.perf_counter() - start) * 1000)
            
            # Measure verification
            start = time.perf_counter()
            valid = pqc_core.mldsa65_verify(message, signature, pk)
            verify_times.append((time.perf_counter() - start) * 1000)
        
        mean_sign = statistics.mean(sign_times)
        mean_verify = statistics.mean(verify_times)
        
        assert mean_sign < 50.0, f"ML-DSA-65 signing mean time {mean_sign:.2f}ms exceeds 50ms"
        assert mean_verify < 20.0, f"ML-DSA-65 verification mean time {mean_verify:.2f}ms exceeds 20ms"


class TestSCBELayerPerformance:
    """
    SCBE 14-Layer Performance Tests
    
    Each layer must meet performance requirements:
    - Layer processing: <1ms per layer
    - Full pipeline: <20ms for 1KB
    - Throughput: >50 MB/s
    
    These tests verify REAL layer performance.
    """
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_context_encoding_performance(self):
        """
        Layer 1: Context Encoding Performance Test
        
        Target: <1ms for 1KB input
        Context encoding is the entry point.
        
        This test WILL FAIL if context encoding is too slow.
        """
        data = np.random.randn(1024)  # 1KB of data
        
        n_trials = 1000
        times = []
        
        for _ in range(n_trials):
            start = time.perf_counter()
            encoded = layer_1_context_encoding(data)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        assert mean_time < 1.0, f"Context encoding mean time {mean_time:.3f}ms exceeds 1ms"
        assert p95_time < 2.0, f"Context encoding p95 time {p95_time:.3f}ms exceeds 2ms"
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_poincare_embedding_performance(self):
        """
        Layer 4: Poincaré Embedding Performance Test
        
        Target: <1ms for typical input
        Hyperbolic embedding is computationally intensive.
        
        This test WILL FAIL if embedding is too slow.
        """
        n_trials = 1000
        times = []
        
        for _ in range(n_trials):
            x_G = np.random.randn(8)
            
            start = time.perf_counter()
            u = layer_4_poincare_embedding(x_G)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        assert mean_time < 1.0, f"Poincaré embedding mean time {mean_time:.3f}ms exceeds 1ms"
        assert p95_time < 2.0, f"Poincaré embedding p95 time {p95_time:.3f}ms exceeds 2ms"
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_hyperbolic_distance_performance(self):
        """
        Layer 5: Hyperbolic Distance Performance Test
        
        Target: <0.1ms per distance computation
        Distance is computed frequently.
        
        This test WILL FAIL if distance computation is too slow.
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
            d = layer_5_hyperbolic_distance(u, v)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        assert mean_time < 0.1, f"Hyperbolic distance mean time {mean_time:.4f}ms exceeds 0.1ms"
        assert p95_time < 0.2, f"Hyperbolic distance p95 time {p95_time:.4f}ms exceeds 0.2ms"
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_topological_cfi_performance(self):
        """
        Layer 14: Topological CFI Performance Test
        
        Target: <2ms for CFI verification
        CFI is the final security layer.
        
        This test WILL FAIL if CFI is too slow.
        """
        if not hasattr(layer_14_topological_cfi, '__call__'):
            pytest.skip("Topological CFI not callable")
        
        data = np.random.randn(512)
        
        n_trials = 500
        times = []
        
        for _ in range(n_trials):
            start = time.perf_counter()
            result = layer_14_topological_cfi(data)
            times.append((time.perf_counter() - start) * 1000)
        
        mean_time = statistics.mean(times)
        p95_time = np.percentile(times, 95)
        
        assert mean_time < 2.0, f"Topological CFI mean time {mean_time:.2f}ms exceeds 2ms"
        assert p95_time < 5.0, f"Topological CFI p95 time {p95_time:.2f}ms exceeds 5ms"


class TestThroughputPerformance:
    """
    Throughput Performance Tests
    
    Industry requirements:
    - Encryption throughput: >100 MB/s
    - Decryption throughput: >100 MB/s
    - Hashing throughput: >500 MB/s
    
    These tests verify REAL throughput.
    """
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_encryption_throughput(self):
        """
        Encryption Throughput Test
        
        Target: >100 MB/s
        Critical for bulk data encryption.
        
        This test WILL FAIL if throughput is too low.
        """
        if not hasattr(pqc_core, 'encrypt_bulk'):
            pytest.skip("Bulk encryption not available")
        
        # Test with 10MB of data
        data_size = 10 * 1024 * 1024  # 10 MB
        data = os.urandom(data_size)
        key = os.urandom(32)
        
        start = time.perf_counter()
        encrypted = pqc_core.encrypt_bulk(data, key)
        elapsed = time.perf_counter() - start
        
        throughput = data_size / elapsed / (1024 * 1024)  # MB/s
        
        assert throughput > 100.0, f"Encryption throughput {throughput:.1f} MB/s below 100 MB/s"
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_hashing_throughput(self):
        """
        Hashing Throughput Test
        
        Target: >500 MB/s
        Hashing is used extensively.
        
        This test WILL FAIL if hashing is too slow.
        """
        import hashlib
        
        # Test with 100MB of data
        data_size = 100 * 1024 * 1024  # 100 MB
        data = os.urandom(data_size)
        
        start = time.perf_counter()
        hash_result = hashlib.sha256(data).digest()
        elapsed = time.perf_counter() - start
        
        throughput = data_size / elapsed / (1024 * 1024)  # MB/s
        
        assert throughput > 500.0, f"Hashing throughput {throughput:.1f} MB/s below 500 MB/s"


class TestLatencyPerformance:
    """
    Latency Performance Tests
    
    Industry requirements:
    - p50 latency: <10ms
    - p95 latency: <50ms
    - p99 latency: <100ms
    
    These tests verify REAL latency distribution.
    """
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_end_to_end_latency(self):
        """
        End-to-End Latency Test
        
        Measures full encryption pipeline latency.
        
        This test WILL FAIL if latency exceeds targets.
        """
        if not hasattr(pqc_core, 'encrypt'):
            pytest.skip("Encryption not available")
        
        data = b"Test message" * 100  # 1.2 KB
        key = os.urandom(32)
        
        n_trials = 10000
        latencies = []
        
        for _ in range(n_trials):
            start = time.perf_counter()
            encrypted = pqc_core.encrypt(data, key)
            latencies.append((time.perf_counter() - start) * 1000)
        
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        
        assert p50 < 10.0, f"p50 latency {p50:.2f}ms exceeds 10ms"
        assert p95 < 50.0, f"p95 latency {p95:.2f}ms exceeds 50ms"
        assert p99 < 100.0, f"p99 latency {p99:.2f}ms exceeds 100ms"


class TestScalabilityPerformance:
    """
    Scalability Performance Tests
    
    Tests performance under load:
    - Concurrent operations
    - Large data sizes
    - High request rates
    
    These tests verify system scales properly.
    """
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_concurrent_operations(self):
        """
        Concurrent Operations Test
        
        System must handle concurrent operations efficiently.
        Target: Linear scaling up to CPU cores.
        
        This test WILL FAIL if concurrency causes significant overhead.
        """
        import concurrent.futures
        
        if not hasattr(pqc_core, 'encrypt'):
            pytest.skip("Encryption not available")
        
        def encrypt_task():
            data = os.urandom(1024)
            key = os.urandom(32)
            return pqc_core.encrypt(data, key)
        
        # Test with different concurrency levels
        n_tasks = 100
        
        # Sequential
        start = time.perf_counter()
        for _ in range(n_tasks):
            encrypt_task()
        sequential_time = time.perf_counter() - start
        
        # Concurrent (4 workers)
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(encrypt_task) for _ in range(n_tasks)]
            concurrent.futures.wait(futures)
        concurrent_time = time.perf_counter() - start
        
        speedup = sequential_time / concurrent_time
        
        # Should see at least 2x speedup with 4 workers
        assert speedup > 2.0, f"Concurrent speedup {speedup:.2f}x below 2.0x"
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_large_data_performance(self):
        """
        Large Data Performance Test
        
        Performance must scale linearly with data size.
        
        This test WILL FAIL if performance degrades non-linearly.
        """
        if not hasattr(pqc_core, 'encrypt'):
            pytest.skip("Encryption not available")
        
        key = os.urandom(32)
        
        # Test different data sizes
        sizes = [1024, 10240, 102400, 1024000]  # 1KB, 10KB, 100KB, 1MB
        times = []
        
        for size in sizes:
            data = os.urandom(size)
            
            start = time.perf_counter()
            encrypted = pqc_core.encrypt(data, key)
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
        
        # Check linearity: time should scale roughly linearly with size
        # Calculate throughput for each size
        throughputs = [sizes[i] / times[i] for i in range(len(sizes))]
        
        # Throughput should be relatively consistent (within 50%)
        min_throughput = min(throughputs)
        max_throughput = max(throughputs)
        
        variation = (max_throughput - min_throughput) / min_throughput
        
        assert variation < 0.5, f"Throughput variation {variation:.2%} exceeds 50% - non-linear scaling"


class TestMemoryPerformance:
    """
    Memory Performance Tests
    
    Tests memory usage and efficiency:
    - Memory footprint
    - Memory allocation rate
    - Memory leaks
    
    These tests verify memory efficiency.
    """
    
    @pytest.mark.skipif(not MODULES_AVAILABLE, reason="Modules not available")
    def test_memory_footprint(self):
        """
        Memory Footprint Test
        
        System must have reasonable memory footprint.
        Target: <100MB for typical operations.
        
        This test WILL FAIL if memory usage is excessive.
        """
        import psutil
        import gc
        
        if not hasattr(pqc_core, 'encrypt'):
            pytest.skip("Encryption not available")
        
        # Force garbage collection
        gc.collect()
        
        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Perform operations
        key = os.urandom(32)
        for _ in range(1000):
            data = os.urandom(1024)
            encrypted = pqc_core.encrypt(data, key)
        
        # Measure final memory
        final_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 100.0, f"Memory increase {memory_increase:.1f}MB exceeds 100MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
