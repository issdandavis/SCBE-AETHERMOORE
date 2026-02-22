"""
Tests for the SCBE-AETHERMOORE Integration Hub.

Tests cross-LLM routing, service discovery, health checking,
and the unified AI completion API.
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# ---------------------------------------------------------------------------
#  Path setup
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.api.integrations import IntegrationHub, ServiceConfig


# ===========================================================================
#  Fixtures
# ===========================================================================

@pytest.fixture
def hub_with_keys():
    """Hub with all services configured."""
    with patch.dict(os.environ, {
        "BROWSERBASE_API_KEY": "bb_test_key",
        "BROWSERBASE_PROJECT_ID": "proj-123",
        "VERCEL_AI_GATEWAY_KEY": "vck_test_key",
        "HF_TOKEN": "hf_test_token",
    }):
        return IntegrationHub()


@pytest.fixture
def hub_no_keys():
    """Hub with no service keys configured."""
    with patch.dict(os.environ, {
        "BROWSERBASE_API_KEY": "",
        "BROWSERBASE_PROJECT_ID": "",
        "VERCEL_AI_GATEWAY_KEY": "",
        "HF_TOKEN": "",
    }, clear=False):
        return IntegrationHub()


@pytest.fixture
def hub_vercel_only():
    """Hub with only Vercel configured."""
    with patch.dict(os.environ, {
        "BROWSERBASE_API_KEY": "",
        "VERCEL_AI_GATEWAY_KEY": "vck_test",
        "HF_TOKEN": "",
    }, clear=False):
        return IntegrationHub()


# ===========================================================================
#  Service Discovery Tests
# ===========================================================================

class TestServiceDiscovery:
    """Test service detection and configuration."""

    def test_all_keys_detected(self, hub_with_keys: IntegrationHub):
        active = hub_with_keys.active_services()
        names = [s.name for s in active]
        assert "Browserbase" in names
        assert "Vercel AI Gateway" in names
        assert "HuggingFace Inference" in names
        assert len(active) == 3

    def test_no_keys_detected(self, hub_no_keys: IntegrationHub):
        active = hub_no_keys.active_services()
        assert len(active) == 0

    def test_partial_keys(self, hub_vercel_only: IntegrationHub):
        active = hub_vercel_only.active_services()
        assert len(active) == 1
        assert active[0].name == "Vercel AI Gateway"

    def test_available_models(self, hub_with_keys: IntegrationHub):
        models = hub_with_keys.available_models()
        assert "Browserbase" in models
        assert "Vercel AI Gateway" in models
        assert "HuggingFace Inference" in models
        # Vercel should have multiple models
        assert len(models["Vercel AI Gateway"]) >= 3

    def test_status_summary(self, hub_with_keys: IntegrationHub):
        status = hub_with_keys.status_summary()
        assert "services" in status
        assert "active" in status
        assert "total_models" in status
        assert "cross_llm_ready" in status
        assert status["cross_llm_ready"] is True  # Vercel + HF

    def test_cross_llm_not_ready_single_provider(self, hub_vercel_only: IntegrationHub):
        status = hub_vercel_only.status_summary()
        assert status["cross_llm_ready"] is False

    def test_get_service(self, hub_with_keys: IntegrationHub):
        svc = hub_with_keys.get_service("browserbase")
        assert svc is not None
        assert svc.name == "Browserbase"
        assert svc.enabled is True

    def test_get_nonexistent_service(self, hub_with_keys: IntegrationHub):
        svc = hub_with_keys.get_service("nonexistent")
        assert svc is None


# ===========================================================================
#  Cross-LLM Routing Tests
# ===========================================================================

class TestCrossLLMRouting:
    """Test the intelligent task-to-provider routing."""

    def test_route_code_prefers_vercel(self, hub_with_keys: IntegrationHub):
        route = hub_with_keys.route_task("code")
        assert route["provider_key"] == "vercel_ai"
        assert route["has_key"] is True

    def test_route_extract_prefers_huggingface(self, hub_with_keys: IntegrationHub):
        route = hub_with_keys.route_task("extract")
        assert route["provider_key"] == "huggingface"

    def test_route_safety_prefers_vercel(self, hub_with_keys: IntegrationHub):
        route = hub_with_keys.route_task("safety")
        assert route["provider_key"] == "vercel_ai"

    def test_route_general_prefers_huggingface(self, hub_with_keys: IntegrationHub):
        route = hub_with_keys.route_task("general")
        assert route["provider_key"] == "huggingface"

    def test_route_with_preferred_provider(self, hub_with_keys: IntegrationHub):
        route = hub_with_keys.route_task("code", prefer_provider="huggingface")
        assert route["provider_key"] == "huggingface"

    def test_route_no_providers(self, hub_no_keys: IntegrationHub):
        route = hub_no_keys.route_task("general")
        assert route["provider"] is None
        assert "error" in route

    def test_route_fallback_on_missing_provider(self, hub_vercel_only: IntegrationHub):
        # extract prefers HF, but only Vercel is available -> should fallback
        route = hub_vercel_only.route_task("extract")
        assert route["provider_key"] == "vercel_ai"
        assert route["has_key"] is True

    def test_route_unknown_task_type(self, hub_with_keys: IntegrationHub):
        route = hub_with_keys.route_task("unknown_type")
        # Should fall back to "general" routing
        assert route["provider_key"] is not None


# ===========================================================================
#  Unified Completion Tests
# ===========================================================================

class TestUnifiedCompletion:
    """Test the unified AI completion API."""

    @pytest.mark.asyncio
    async def test_complete_vercel(self, hub_with_keys: IntegrationHub):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello from GPT"}}],
            "usage": {"total_tokens": 10},
        }
        mock_resp.elapsed = MagicMock()
        mock_resp.elapsed.total_seconds.return_value = 0.5

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        hub_with_keys._http_client = mock_client

        result = await hub_with_keys.complete(
            prompt="Say hello",
            provider="vercel_ai",
        )
        assert result["response"] == "Hello from GPT"
        assert result["provider"] == "Vercel AI Gateway"

    @pytest.mark.asyncio
    async def test_complete_huggingface(self, hub_with_keys: IntegrationHub):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"generated_text": "Hello from Llama"}]
        mock_resp.elapsed = MagicMock()
        mock_resp.elapsed.total_seconds.return_value = 0.3

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        hub_with_keys._http_client = mock_client

        result = await hub_with_keys.complete(
            prompt="Say hello",
            provider="huggingface",
        )
        assert result["response"] == "Hello from Llama"
        assert result["provider"] == "HuggingFace Inference"

    @pytest.mark.asyncio
    async def test_complete_error_handling(self, hub_with_keys: IntegrationHub):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal server error"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        hub_with_keys._http_client = mock_client

        result = await hub_with_keys.complete(prompt="Say hello", provider="vercel_ai")
        assert result.get("error") is not None
        assert result["response"] is None

    @pytest.mark.asyncio
    async def test_complete_no_provider(self, hub_no_keys: IntegrationHub):
        result = await hub_no_keys.complete(prompt="Say hello")
        assert result.get("error") is not None


# ===========================================================================
#  Cross-LLM Exchange Tests
# ===========================================================================

class TestCrossLLMExchange:
    """Test sending to multiple LLMs and aggregating."""

    @pytest.mark.asyncio
    async def test_cross_llm_multiple_responses(self, hub_with_keys: IntegrationHub):
        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.elapsed = MagicMock()
            resp.elapsed.total_seconds.return_value = 0.2
            if "vercel" in url or "chat/completions" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "choices": [{"message": {"content": f"Vercel response"}}],
                    "usage": {},
                }
            else:
                resp.status_code = 200
                resp.json.return_value = [{"generated_text": f"HF response"}]
            return resp

        mock_client = AsyncMock()
        mock_client.post = mock_post
        hub_with_keys._http_client = mock_client

        result = await hub_with_keys.cross_llm_exchange(
            prompt="What is 2+2?",
            providers=["Vercel AI Gateway", "HuggingFace Inference"],
        )
        assert result["response_count"] == 2
        assert result["providers_queried"] == 2
        assert result["consensus"] == "multiple_responses"

    @pytest.mark.asyncio
    async def test_cross_llm_partial_failure(self, hub_with_keys: IntegrationHub):
        async def mock_post(url, **kwargs):
            resp = MagicMock()
            resp.elapsed = MagicMock()
            resp.elapsed.total_seconds.return_value = 0.1
            if "chat/completions" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "choices": [{"message": {"content": "Works"}}],
                    "usage": {},
                }
            else:
                resp.status_code = 503
                resp.text = "Service unavailable"
            return resp

        mock_client = AsyncMock()
        mock_client.post = mock_post
        hub_with_keys._http_client = mock_client

        result = await hub_with_keys.cross_llm_exchange(prompt="Test")
        assert result["response_count"] >= 1


# ===========================================================================
#  ServiceConfig Tests
# ===========================================================================

class TestServiceConfig:
    """Test ServiceConfig dataclass."""

    def test_to_dict_hides_key(self):
        cfg = ServiceConfig(
            name="Test",
            enabled=True,
            api_key="secret_key_123",
            base_url="https://api.test.com",
        )
        d = cfg.to_dict()
        assert d["has_key"] is True
        assert "secret" not in str(d)  # Key should not appear
        assert d["name"] == "Test"

    def test_disabled_by_default(self):
        cfg = ServiceConfig(name="Test")
        assert cfg.enabled is False
        assert cfg.healthy is False


# ===========================================================================
#  Health Check Tests
# ===========================================================================

class TestHealthCheck:

    @pytest.mark.asyncio
    async def test_health_all_disabled(self, hub_no_keys: IntegrationHub):
        report = await hub_no_keys.health_check()
        assert report["active_count"] == 0
        for key, status in report["services"].items():
            assert status["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_health_with_keys(self, hub_with_keys: IntegrationHub):
        # Mock httpx client
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        hub_with_keys._http_client = mock_client

        # Patch browserbase import
        with patch("src.api.integrations.Browserbase", create=True):
            report = await hub_with_keys.health_check()

        assert report["active_count"] == 3
        assert "checked_at" in report
