#!/usr/bin/env python3
"""
Test Suite: Open Source Integrations
=====================================

Tests for SCBE integrations with:
- geoopt (Hyperbolic geometry)
- liboqs-python (Post-quantum crypto)
- mesa (Agent-based modeling)
- pyswarms (Swarm optimization)

Run: python tests/test_integrations.py
"""

import sys
import os
import time
import numpy as np

# Add prototype to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prototype'))

# ============================================================================
# Test Helpers
# ============================================================================

TESTS_RUN = 0
TESTS_PASSED = 0
TESTS_SKIPPED = 0

def test(name, condition, details=""):
    global TESTS_RUN, TESTS_PASSED
    TESTS_RUN += 1
    start = time.perf_counter()
    try:
        result = condition() if callable(condition) else condition
        elapsed = (time.perf_counter() - start) * 1000
        if result:
            TESTS_PASSED += 1
            print(f"  ✓ PASS | {name} ({elapsed:.1f}ms)")
        else:
            print(f"  ✗ FAIL | {name} ({elapsed:.1f}ms) {details}")
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  ✗ ERROR | {name} ({elapsed:.1f}ms) - {e}")

def skip(name, reason):
    global TESTS_SKIPPED
    TESTS_SKIPPED += 1
    print(f"  ○ SKIP | {name} - {reason}")


# ============================================================================
# Import integrations module
# ============================================================================

try:
    from integrations import (
        check_integrations,
        GEOOPT_AVAILABLE,
        LIBOQS_AVAILABLE,
        MESA_AVAILABLE,
        PYSWARMS_AVAILABLE,
    )
    INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    INTEGRATIONS_AVAILABLE = False
    print(f"Warning: Could not import integrations module: {e}")


# ============================================================================
# Tests: Integration Module
# ============================================================================

def test_integration_module():
    print("\n--- Integration Module Tests ---")

    if not INTEGRATIONS_AVAILABLE:
        skip("Integration module import", "Module not available")
        return

    # Test 1: check_integrations returns dict
    status = check_integrations()
    test("check_integrations returns dict",
         lambda: isinstance(status, dict))

    # Test 2: All expected keys present
    expected_keys = {'geoopt', 'liboqs', 'mesa', 'pyswarms'}
    test("All integration keys present",
         lambda: expected_keys <= set(status.keys()))

    # Test 3: Values are boolean
    test("All values are boolean",
         lambda: all(isinstance(v, bool) for v in status.values()))


# ============================================================================
# Tests: Geoopt Integration
# ============================================================================

def test_geoopt_integration():
    print("\n--- Geoopt Integration Tests ---")

    if not INTEGRATIONS_AVAILABLE or not GEOOPT_AVAILABLE:
        skip("Geoopt tests", "geoopt not installed")
        return

    from integrations import GeooptHyperbolicSpace

    # Test 1: Create space
    space = GeooptHyperbolicSpace(dim=6)
    test("Create 6D Poincaré ball",
         lambda: space.dim == 6)

    # Test 2: Random point generation
    point = space.random_point()
    test("Random point is 6D",
         lambda: len(point) == 6)

    # Test 3: Point is in ball
    test("Random point is in unit ball",
         lambda: np.linalg.norm(point) < 1.0)

    # Test 4: Distance is non-negative
    x = space.random_point()
    y = space.random_point()
    dist = space.distance(x, y)
    test("Distance is non-negative",
         lambda: dist >= 0)

    # Test 5: Self-distance is zero
    test("Self-distance is ~0",
         lambda: space.distance(x, x) < 1e-6)

    # Test 6: Projection keeps point in ball
    wild_point = np.random.randn(6) * 2  # Outside ball
    projected = space.project(wild_point)
    test("Projection keeps point in ball",
         lambda: np.linalg.norm(projected) < 1.0)


# ============================================================================
# Tests: liboqs Integration
# ============================================================================

def test_liboqs_integration():
    print("\n--- liboqs Integration Tests ---")

    if not INTEGRATIONS_AVAILABLE or not LIBOQS_AVAILABLE:
        skip("liboqs tests", "liboqs-python not installed")
        return

    from integrations import PostQuantumSigner, PostQuantumKEM

    # Test 1: Available algorithms
    sig_algs = PostQuantumSigner.available_algorithms()
    test("Signature algorithms available",
         lambda: len(sig_algs) > 0)

    # Test 2: Create signer
    signer = PostQuantumSigner("Dilithium3")
    test("Create Dilithium3 signer",
         lambda: signer.public_key is not None)

    # Test 3: Sign message
    message = b"SCBE governance decision"
    signature = signer.sign(message)
    test("Sign message",
         lambda: len(signature) > 0)

    # Test 4: Verify valid signature
    test("Verify valid signature",
         lambda: signer.verify(message, signature))

    # Test 5: Reject tampered message
    test("Reject tampered message",
         lambda: not signer.verify(b"tampered", signature))

    # Test 6: KEM algorithms
    kem_algs = PostQuantumKEM.available_algorithms()
    test("KEM algorithms available",
         lambda: len(kem_algs) > 0)

    # Test 7: Create KEM
    kem = PostQuantumKEM("Kyber768")
    test("Create Kyber768 KEM",
         lambda: kem.public_key is not None)

    # Test 8: Encapsulate/Decapsulate
    ciphertext, shared_secret = kem.encapsulate()
    recovered = kem.decapsulate(ciphertext)
    test("Key encapsulation roundtrip",
         lambda: shared_secret == recovered)


# ============================================================================
# Tests: Mesa Integration
# ============================================================================

def test_mesa_integration():
    print("\n--- Mesa Integration Tests ---")

    if not INTEGRATIONS_AVAILABLE or not MESA_AVAILABLE:
        skip("Mesa tests", "mesa not installed")
        return

    from integrations import SCBEModel, SCBEAgent

    # Test 1: Create model
    model = SCBEModel(n_agents=6)
    test("Create SCBE model",
         lambda: model is not None)

    # Test 2: Correct number of agents
    test("Model has 6 agents",
         lambda: len(model.schedule.agents) == 6)

    # Test 3: Agents have tongues
    tongues = {a.tongue for a in model.schedule.agents}
    test("Agents have Sacred Tongue assignments",
         lambda: len(tongues) > 0)

    # Test 4: Run simulation step
    initial_trust = np.mean([a.trust_score for a in model.schedule.agents])
    model.step()
    test("Simulation step runs",
         lambda: True)

    # Test 5: Data collector works
    model.step()
    model.step()
    data = model.datacollector.get_model_vars_dataframe()
    test("Data collector captures trust",
         lambda: 'AvgTrust' in data.columns and len(data) > 0)

    # Test 6: Agents have positions
    test("Agents have positions",
         lambda: all(hasattr(a, 'pos') for a in model.schedule.agents))


# ============================================================================
# Tests: PySwarms Integration
# ============================================================================

def test_pyswarms_integration():
    print("\n--- PySwarms Integration Tests ---")

    if not INTEGRATIONS_AVAILABLE or not PYSWARMS_AVAILABLE:
        skip("PySwarms tests", "pyswarms not installed")
        return

    from integrations import SwarmOptimizer

    # Test 1: Create optimizer
    optimizer = SwarmOptimizer(n_particles=10, dimensions=2)
    test("Create swarm optimizer",
         lambda: optimizer is not None)

    # Test 2: Optimizer has options
    test("Optimizer has PSO options",
         lambda: 'c1' in optimizer.options and 'c2' in optimizer.options)


# ============================================================================
# Tests: Fallback Behavior
# ============================================================================

def test_fallback_behavior():
    print("\n--- Fallback Behavior Tests ---")

    if not INTEGRATIONS_AVAILABLE:
        skip("Fallback tests", "Module not available")
        return

    from integrations import check_integrations

    # Test 1: Check returns even when libs missing
    status = check_integrations()
    test("check_integrations works regardless of installed libs",
         lambda: isinstance(status, dict) and len(status) >= 4)

    # Test 2: Missing lib raises ImportError
    if not GEOOPT_AVAILABLE:
        from integrations import GeooptHyperbolicSpace
        try:
            GeooptHyperbolicSpace()
            test("Missing geoopt raises ImportError", False)
        except ImportError:
            test("Missing geoopt raises ImportError", True)
    else:
        skip("Import error test for geoopt", "geoopt is installed")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TEST SUITE: Open Source Integrations")
    print("=" * 70)

    test_integration_module()
    test_geoopt_integration()
    test_liboqs_integration()
    test_mesa_integration()
    test_pyswarms_integration()
    test_fallback_behavior()

    print("\n" + "-" * 70)
    total = TESTS_RUN + TESTS_SKIPPED
    print(f"RESULT: {TESTS_PASSED}/{TESTS_RUN} tests passed, {TESTS_SKIPPED} skipped")
    print("=" * 70)

    # List available integrations
    if INTEGRATIONS_AVAILABLE:
        status = check_integrations()
        available = [k for k, v in status.items() if v]
        if available:
            print(f"Available integrations: {', '.join(available)}")
        else:
            print("No optional integrations installed")
            print("Install with: pip install -r requirements-integrations.txt")

    sys.exit(0 if TESTS_PASSED == TESTS_RUN else 1)
