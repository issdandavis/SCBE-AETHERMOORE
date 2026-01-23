"""
SCBE Test Configuration
=======================

Shared fixtures and configuration for all test tiers.
"""

import pytest
import numpy as np
import sys
import os
from typing import Dict, Any, List
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# =============================================================================
# MATHEMATICAL CONSTANTS
# =============================================================================

PHI = (1 + np.sqrt(5)) / 2  # Golden ratio
R_FIFTH = 1.5  # Perfect fifth harmonic ratio


# =============================================================================
# TEST DATA FACTORIES
# =============================================================================

@dataclass
class TestVector:
    """Standard test vector for SCBE operations."""
    position: List[int]
    agent: str
    topic: str
    context: str
    expected_decision: str
    description: str


@pytest.fixture
def golden_ratio():
    """Golden ratio constant."""
    return PHI


@pytest.fixture
def harmonic_ratio():
    """Perfect fifth harmonic ratio."""
    return R_FIFTH


@pytest.fixture
def legitimate_request():
    """Fixture for legitimate (ALLOW) request."""
    return TestVector(
        position=[1, 2, 3, 5, 8, 13],  # Fibonacci - harmonic
        agent="trusted_agent",
        topic="memory",
        context="internal",
        expected_decision="ALLOW",
        description="Trusted internal agent with harmonic position"
    )


@pytest.fixture
def suspicious_request():
    """Fixture for suspicious (QUARANTINE) request."""
    return TestVector(
        position=[99, 99, 99, 99, 99, 99],  # Edge position
        agent="external_agent",
        topic="secrets",
        context="external",
        expected_decision="QUARANTINE",
        description="External agent at edge position"
    )


@pytest.fixture
def malicious_request():
    """Fixture for malicious (DENY) request."""
    return TestVector(
        position=[0, 0, 0, 0, 0, 0],  # Origin attack
        agent="malicious_bot",
        topic="admin",
        context="untrusted",
        expected_decision="DENY",
        description="Untrusted bot targeting admin"
    )


@pytest.fixture
def valid_api_key():
    """Valid API key for authenticated endpoints."""
    return "demo_key_12345"


@pytest.fixture
def invalid_api_key():
    """Invalid API key for rejection tests."""
    return "invalid_key_00000"


# =============================================================================
# MOCK OBJECTS
# =============================================================================

@pytest.fixture
def mock_scbe_result():
    """Mock SCBE pipeline result."""
    return {
        "decision": "ALLOW",
        "risk_base": 0.15,
        "risk_prime": 0.23,
        "H": 1.53,
        "d_star": 0.42,
        "coherence": {
            "spectral": 0.92,
            "spin": 0.88,
            "temporal": 0.95
        },
        "geometry": {
            "hyperbolic_dist": 0.42,
            "poincare_norm": 0.38
        }
    }


@pytest.fixture
def sacred_tongue_tokens():
    """Sacred Tongue token mappings."""
    return {
        "KO": "kor_nonce_token",
        "AV": "ava_aad_token",
        "RU": "run_salt_token",
        "CA": "cas_cipher_token",
        "UM": "umb_redact_token",
        "DR": "dra_tag_token"
    }


# =============================================================================
# MATHEMATICAL HELPERS
# =============================================================================

@pytest.fixture
def hyperbolic_distance():
    """Hyperbolic distance function."""
    def _hyperbolic_distance(u: np.ndarray, v: np.ndarray) -> float:
        """Calculate hyperbolic distance in Poincaré ball."""
        u_norm_sq = np.sum(u ** 2)
        v_norm_sq = np.sum(v ** 2)
        diff_norm_sq = np.sum((u - v) ** 2)

        # Clamp to avoid numerical issues
        u_norm_sq = min(u_norm_sq, 0.9999)
        v_norm_sq = min(v_norm_sq, 0.9999)

        numerator = 2 * diff_norm_sq
        denominator = (1 - u_norm_sq) * (1 - v_norm_sq)

        if denominator <= 0:
            return float('inf')

        arg = 1 + numerator / denominator
        return np.arccosh(max(arg, 1.0))

    return _hyperbolic_distance


@pytest.fixture
def harmonic_scaling():
    """Harmonic scaling function H(d, R) = R^(d²)."""
    def _harmonic_scaling(d: float, R: float = R_FIFTH) -> float:
        return R ** (d ** 2)

    return _harmonic_scaling


# =============================================================================
# PERFORMANCE HELPERS
# =============================================================================

@pytest.fixture
def performance_timer():
    """Context manager for timing operations."""
    import time

    class Timer:
        def __init__(self):
            self.elapsed = 0.0

        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.elapsed = time.perf_counter() - self.start

    return Timer


# =============================================================================
# TEST MARKERS
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "enterprise: Enterprise-grade tests (compliance, security)")
    config.addinivalue_line("markers", "professional: Professional/industry standard tests")
    config.addinivalue_line("markers", "homebrew: Quick developer feedback tests")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "crypto: Cryptographic tests")
    config.addinivalue_line("markers", "math: Mathematical verification tests")
    config.addinivalue_line("markers", "governance: Governance decision tests")
    config.addinivalue_line("markers", "pqc: Post-quantum cryptography tests")
