"""Tests for the Perplexity Sonar source adapter."""

from __future__ import annotations

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.obsidian_researcher.source_adapter import IngestionResult, SourceType
from agents.obsidian_researcher.sources.perplexity_source import PerplexitySource


# ==========================================================================
# Mock data
# ==========================================================================

MOCK_CHAT_RESPONSE = {
    "id": "chatcmpl-abc123",
    "model": "sonar",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hyperbolic geometry in AI safety uses the Poincaré ball model "
                "to create exponential cost barriers for adversarial behavior. "
                "Key papers include work on trust scaling in multi-agent systems.",
            },
            "finish_reason": "stop",
        }
    ],
    "citations": [
        "https://arxiv.org/abs/2401.12345",
        "https://www.nature.com/articles/s41586-024-1234",
        "https://openreview.net/forum?id=abc123",
    ],
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 120,
        "total_tokens": 170,
    },
}

MOCK_RESEARCH_RESPONSE = {
    "id": "chatcmpl-def456",
    "model": "sonar-pro",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "The AI safety market is projected to reach $8.4B by 2028. "
                "Key players include Anthropic, OpenAI, Google DeepMind. "
                "Governance frameworks are emerging as critical infrastructure.",
            },
            "finish_reason": "stop",
        }
    ],
    "citations": [
        "https://www.grandviewresearch.com/ai-safety-market",
        "https://arxiv.org/abs/2402.67890",
    ],
    "usage": {
        "prompt_tokens": 80,
        "completion_tokens": 200,
        "total_tokens": 280,
    },
}


def _mock_urlopen(response_data: Any):
    """Create a mock urlopen returning JSON."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ==========================================================================
# Tests
# ==========================================================================


class TestPerplexityConfig(unittest.TestCase):
    """Test configuration and initialization."""

    def test_default_config(self):
        source = PerplexitySource({"api_key": "test-key"})
        self.assertEqual(source._model, "sonar")
        self.assertEqual(source._timeout, 30)
        self.assertTrue(source._return_citations)

    def test_custom_model(self):
        source = PerplexitySource({
            "api_key": "test-key",
            "model": "sonar-pro",
            "timeout": 60,
        })
        self.assertEqual(source._model, "sonar-pro")
        self.assertEqual(source._timeout, 60)

    def test_env_api_key(self):
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "env-key"}):
            source = PerplexitySource()
            self.assertEqual(source._api_key, "env-key")

    def test_config_key_overrides_env(self):
        with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "env-key"}):
            source = PerplexitySource({"api_key": "config-key"})
            self.assertEqual(source._api_key, "config-key")


class TestPerplexityFetch(unittest.TestCase):
    """Test the fetch method (search)."""

    def setUp(self):
        self.source = PerplexitySource({"api_key": "test-key"})

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_fetch_returns_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        results = self.source.fetch("hyperbolic AI safety")
        # Main result + 3 citation results
        self.assertEqual(len(results), 4)
        self.assertIn("hyperbolic geometry", results[0].raw_content.lower())

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_fetch_main_result_metadata(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        results = self.source.fetch("hyperbolic AI safety")
        main = results[0]
        self.assertEqual(main.metadata["source"], "perplexity")
        self.assertEqual(main.metadata["model"], "sonar")
        self.assertEqual(main.metadata["citation_count"], 3)
        self.assertIn("perplexity", main.tags)

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_fetch_citation_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        results = self.source.fetch("test")
        citations = [r for r in results if "citation" in r.tags]
        self.assertEqual(len(citations), 3)
        self.assertEqual(citations[0].url, "https://arxiv.org/abs/2401.12345")

    def test_fetch_no_api_key(self):
        source = PerplexitySource({"api_key": ""})
        results = source.fetch("test")
        self.assertEqual(results, [])

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_fetch_api_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://api.perplexity.ai/chat/completions",
            429, "Rate limited", {}, None,
        )
        results = self.source.fetch("test")
        self.assertEqual(results, [])


class TestPerplexityFetchById(unittest.TestCase):
    """Test fetch_by_id (topic/URL analysis)."""

    def setUp(self):
        self.source = PerplexitySource({"api_key": "test-key"})

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_fetch_by_url(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        result = self.source.fetch_by_id("https://arxiv.org/abs/2401.12345")
        self.assertIsNotNone(result)
        self.assertEqual(result.url, "https://arxiv.org/abs/2401.12345")

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_fetch_by_topic(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        result = self.source.fetch_by_id("AI governance frameworks 2026")
        self.assertIsNotNone(result)
        self.assertIn("analysis", result.tags)

    def test_fetch_by_id_no_key(self):
        source = PerplexitySource({"api_key": ""})
        self.assertIsNone(source.fetch_by_id("test"))


class TestPerplexityResearch(unittest.TestCase):
    """Test the extended research methods."""

    def setUp(self):
        self.source = PerplexitySource({"api_key": "test-key"})

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_research_quick(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_RESEARCH_RESPONSE)
        result = self.source.research("AI safety market", depth="quick")
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata["depth"], "quick")
        self.assertIn("depth:quick", result.tags)

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_research_deep(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_RESEARCH_RESPONSE)
        result = self.source.research("post-quantum cryptography", depth="deep")
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata["depth"], "deep")

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_competitive_analysis(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_RESEARCH_RESPONSE)
        result = self.source.competitive_analysis("OpenClaw")
        self.assertIsNotNone(result)
        self.assertIn("focus:competitive intelligence", result.tags)

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_patent_landscape(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_RESEARCH_RESPONSE)
        result = self.source.patent_landscape("AI governance")
        self.assertIsNotNone(result)
        self.assertIn("focus:patent intelligence", result.tags)

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_market_research(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_RESEARCH_RESPONSE)
        result = self.source.market_research("AI safety tools")
        self.assertIsNotNone(result)
        self.assertIn("focus:market intelligence", result.tags)

    def test_research_no_key(self):
        source = PerplexitySource({"api_key": ""})
        self.assertIsNone(source.research("test"))


class TestPerplexityHealth(unittest.TestCase):
    """Test health check."""

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_healthy(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        source = PerplexitySource({"api_key": "test-key"})
        self.assertTrue(source.health_check())

    def test_no_key(self):
        source = PerplexitySource({"api_key": ""})
        self.assertFalse(source.health_check())

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_api_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 401, "Unauthorized", {}, None,
        )
        source = PerplexitySource({"api_key": "bad-key"})
        self.assertFalse(source.health_check())


class TestPerplexityRequestFormat(unittest.TestCase):
    """Test that API requests are properly formatted."""

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_request_includes_auth_header(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        source = PerplexitySource({"api_key": "pplx-test123"})
        source.fetch("test")
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_header("Authorization"), "Bearer pplx-test123")

    @patch("agents.obsidian_researcher.sources.perplexity_source.urllib.request.urlopen")
    def test_request_body_format(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen(MOCK_CHAT_RESPONSE)
        source = PerplexitySource({"api_key": "test-key", "model": "sonar-pro"})
        source.fetch("AI safety")
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data)
        self.assertEqual(body["model"], "sonar-pro")
        self.assertEqual(len(body["messages"]), 2)
        self.assertEqual(body["messages"][1]["content"], "AI safety")
        self.assertTrue(body.get("return_citations", False))


if __name__ == "__main__":
    unittest.main()
