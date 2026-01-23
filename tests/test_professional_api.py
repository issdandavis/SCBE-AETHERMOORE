"""
SCBE Professional API Test Suite
================================

Industry-standard tests for:
- API endpoint functionality
- Request/response validation
- Error handling
- Rate limiting
- Authentication flows

Run: pytest tests/test_professional_api.py -v -m professional
"""

import pytest
import numpy as np
import json
import time
import sys
import os
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try to import FastAPI test client
try:
    from fastapi.testclient import TestClient
    from src.api.main import app, RateLimiter, MetricsStore
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.api
class TestAPIEndpoints:
    """Test all API endpoints for correct behavior."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, valid_api_key):
        """Headers with valid API key."""
        return {"X-API-Key": valid_api_key}

    def test_health_endpoint(self, client):
        """Test /health returns correct status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data

    def test_seal_memory_success(self, client, auth_headers):
        """Test successful memory sealing."""
        payload = {
            "plaintext": "Test secret data",
            "agent": "test_agent",
            "topic": "memory",
            "position": [1, 2, 3, 5, 8, 13]
        }

        response = client.post(
            "/seal-memory",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sealed"
        assert "sealed_blob" in data["data"]
        assert "risk_score" in data["data"]
        assert "governance_result" in data["data"]

    def test_seal_memory_without_auth(self, client):
        """Test seal-memory rejects unauthenticated requests."""
        payload = {
            "plaintext": "Test",
            "agent": "test",
            "topic": "test",
            "position": [1, 2, 3, 4, 5, 6]
        }

        response = client.post("/seal-memory", json=payload)
        assert response.status_code == 422  # Missing header

    def test_seal_memory_invalid_position(self, client, auth_headers):
        """Test seal-memory rejects invalid position vectors."""
        payload = {
            "plaintext": "Test",
            "agent": "test",
            "topic": "test",
            "position": [1, 2, 3]  # Only 3 elements, need 6
        }

        response = client.post(
            "/seal-memory",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    def test_retrieve_memory_contexts(self, client, auth_headers):
        """Test retrieve-memory with different contexts."""
        contexts = ["internal", "external", "untrusted"]

        for context in contexts:
            payload = {
                "position": [1, 2, 3, 5, 8, 13],
                "agent": "test_agent",
                "context": context
            }

            response = client.post(
                "/retrieve-memory",
                json=payload,
                headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["retrieved", "quarantined", "denied"]

    def test_governance_check_public(self, client):
        """Test governance-check is publicly accessible."""
        response = client.get(
            "/governance-check",
            params={
                "agent": "test_agent",
                "topic": "memory",
                "context": "internal"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "decision" in data["data"]
        assert data["data"]["decision"] in ["ALLOW", "QUARANTINE", "DENY"]

    def test_simulate_attack_endpoint(self, client):
        """Test attack simulation endpoint."""
        payload = {
            "position": [99, 99, 99, 99, 99, 99],
            "agent": "malicious_bot",
            "context": "untrusted"
        }

        response = client.post("/simulate-attack", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "simulated"
        assert "fail_to_noise_example" in data["data"]
        assert "detection_layers" in data["data"]

    def test_metrics_requires_auth(self, client, auth_headers):
        """Test /metrics requires authentication."""
        # Without auth
        response = client.get("/metrics")
        assert response.status_code == 422

        # With auth
        response = client.get("/metrics", headers=auth_headers)
        assert response.status_code == 200


# =============================================================================
# RATE LIMITING TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.api
class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiter_allows_under_limit(self):
        """Test rate limiter allows requests under limit."""
        limiter = RateLimiter(max_requests=10, window_seconds=60) if FASTAPI_AVAILABLE else Mock()

        if not FASTAPI_AVAILABLE:
            limiter.is_allowed = Mock(return_value=True)

        for _ in range(9):
            assert limiter.is_allowed("test_key")

    def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        limiter = RateLimiter(max_requests=5, window_seconds=60)

        # Use up the limit
        for _ in range(5):
            assert limiter.is_allowed("test_key")

        # Next request should be blocked
        assert not limiter.is_allowed("test_key")

    def test_rate_limiter_resets_after_window(self):
        """Test rate limiter resets after time window."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        limiter = RateLimiter(max_requests=2, window_seconds=1)

        # Use up limit
        assert limiter.is_allowed("test_key")
        assert limiter.is_allowed("test_key")
        assert not limiter.is_allowed("test_key")

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        assert limiter.is_allowed("test_key")

    def test_rate_limiter_per_key_isolation(self):
        """Test rate limiter tracks keys independently."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        limiter = RateLimiter(max_requests=2, window_seconds=60)

        # Key A uses its limit
        assert limiter.is_allowed("key_a")
        assert limiter.is_allowed("key_a")
        assert not limiter.is_allowed("key_a")

        # Key B should still be allowed
        assert limiter.is_allowed("key_b")
        assert limiter.is_allowed("key_b")


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.api
class TestAuthentication:
    """Test authentication mechanisms."""

    @pytest.fixture
    def client(self):
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")
        return TestClient(app)

    def test_valid_api_key_accepted(self, client):
        """Test valid API keys are accepted."""
        response = client.get(
            "/metrics",
            headers={"X-API-Key": "demo_key_12345"}
        )
        assert response.status_code == 200

    def test_invalid_api_key_rejected(self, client):
        """Test invalid API keys are rejected."""
        response = client.get(
            "/metrics",
            headers={"X-API-Key": "invalid_key"}
        )
        assert response.status_code == 401

    def test_missing_api_key_rejected(self, client):
        """Test missing API key is rejected."""
        response = client.get("/metrics")
        assert response.status_code == 422  # Missing required header


# =============================================================================
# METRICS TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.api
class TestMetrics:
    """Test metrics collection and reporting."""

    def test_metrics_store_initialization(self):
        """Test MetricsStore initializes correctly."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        store = MetricsStore()
        assert store.total_seals == 0
        assert store.total_retrievals == 0
        assert store.total_denials == 0

    def test_metrics_store_records_seals(self):
        """Test MetricsStore records seal operations."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        store = MetricsStore()
        store.record_seal("agent_1", 0.15)
        store.record_seal("agent_2", 0.25)

        assert store.total_seals == 2
        assert len(store.risk_scores) == 2
        assert store.agent_requests["agent_1"] == 1
        assert store.agent_requests["agent_2"] == 1

    def test_metrics_store_records_retrievals(self):
        """Test MetricsStore records retrieval operations."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        store = MetricsStore()
        store.record_retrieval("agent_1", denied=False)
        store.record_retrieval("agent_1", denied=True)

        assert store.total_retrievals == 2
        assert store.total_denials == 1

    def test_metrics_aggregation(self):
        """Test metrics aggregation."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        store = MetricsStore()
        store.record_seal("agent_1", 0.10)
        store.record_seal("agent_1", 0.20)
        store.record_seal("agent_2", 0.30)

        metrics = store.get_metrics()

        assert metrics["total_seals"] == 3
        assert 0.19 < metrics["avg_risk_score"] < 0.21  # ~0.20
        assert len(metrics["top_agents"]) > 0


# =============================================================================
# REQUEST VALIDATION TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.api
class TestRequestValidation:
    """Test request payload validation."""

    @pytest.fixture
    def client(self):
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, valid_api_key):
        return {"X-API-Key": valid_api_key}

    def test_plaintext_max_length(self, client, auth_headers):
        """Test plaintext maximum length is enforced."""
        payload = {
            "plaintext": "x" * 5000,  # Over 4096 limit
            "agent": "test",
            "topic": "test",
            "position": [1, 2, 3, 4, 5, 6]
        }

        response = client.post(
            "/seal-memory",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_position_exactly_6_elements(self, client, auth_headers):
        """Test position must have exactly 6 elements."""
        for length in [5, 7]:
            payload = {
                "plaintext": "test",
                "agent": "test",
                "topic": "test",
                "position": list(range(length))
            }

            response = client.post(
                "/seal-memory",
                json=payload,
                headers=auth_headers
            )

            assert response.status_code == 422

    def test_context_enum_validation(self, client, auth_headers):
        """Test context must be valid enum value."""
        payload = {
            "position": [1, 2, 3, 4, 5, 6],
            "agent": "test",
            "context": "invalid_context"
        }

        response = client.post(
            "/retrieve-memory",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_agent_min_length(self, client, auth_headers):
        """Test agent must have minimum length."""
        payload = {
            "plaintext": "test",
            "agent": "",  # Empty
            "topic": "test",
            "position": [1, 2, 3, 4, 5, 6]
        }

        response = client.post(
            "/seal-memory",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 422


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.api
class TestErrorHandling:
    """Test error handling and response formats."""

    @pytest.fixture
    def client(self):
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")
        return TestClient(app)

    def test_error_response_format(self, client):
        """Test error responses have consistent format."""
        response = client.get("/metrics")  # Missing auth

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # FastAPI validation error format

    def test_404_handling(self, client):
        """Test 404 for non-existent endpoints."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test 405 for wrong HTTP method."""
        response = client.put("/health")  # Should be GET
        assert response.status_code == 405


# =============================================================================
# RESPONSE FORMAT TESTS
# =============================================================================

@pytest.mark.professional
@pytest.mark.api
class TestResponseFormats:
    """Test API response formats and structures."""

    @pytest.fixture
    def client(self):
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")
        return TestClient(app)

    def test_seal_response_structure(self, client, valid_api_key):
        """Test seal-memory response has correct structure."""
        payload = {
            "plaintext": "test",
            "agent": "test_agent",
            "topic": "memory",
            "position": [1, 2, 3, 5, 8, 13]
        }

        response = client.post(
            "/seal-memory",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )

        data = response.json()

        # Top-level structure
        assert "status" in data
        assert "data" in data
        assert "trace" in data

        # Data structure
        assert "sealed_blob" in data["data"]
        assert "position" in data["data"]
        assert "risk_score" in data["data"]
        assert "risk_prime" in data["data"]
        assert "governance_result" in data["data"]
        assert "harmonic_factor" in data["data"]

    def test_governance_response_structure(self, client):
        """Test governance-check response has correct structure."""
        response = client.get(
            "/governance-check",
            params={
                "agent": "test",
                "topic": "test",
                "context": "internal"
            }
        )

        data = response.json()

        assert "status" in data
        assert "data" in data
        assert "decision" in data["data"]
        assert "risk_score" in data["data"]
        assert "coherence_metrics" in data["data"]
        assert "geometry" in data["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "professional"])
