"""Tests that GemmaClient passes temperature + seed to Ollama /api/chat.

Same contract as OllamaAdapter, different endpoint. Without these the
LLM response varies across runs even when the gate verdict is fixed,
which makes the demo transcripts non-reproducible.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from demos.gemma4_scbe_governance.lib import GemmaClient


def _has_httpx() -> bool:
    try:
        import httpx  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


def _captured_chat_response(captured: dict, content: str = "ok"):
    def _side_effect(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        fake = MagicMock()
        fake.raise_for_status.return_value = None
        fake.json.return_value = {"message": {"content": content}}
        return fake

    return _side_effect


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_gemma_client_default_sends_temperature_zero_and_seed() -> None:
    client = GemmaClient()
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_chat_response(captured)):
        client.chat("hello")

    body = captured["json"]
    assert "options" in body
    assert body["options"]["temperature"] == 0.0
    assert body["options"]["seed"] == 42


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_gemma_client_custom_options_round_trip() -> None:
    client = GemmaClient(temperature=0.5, seed=99)
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_chat_response(captured)):
        client.chat("hello")

    assert captured["json"]["options"] == {"temperature": 0.5, "seed": 99}


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_gemma_client_omits_options_when_both_none() -> None:
    client = GemmaClient(temperature=None, seed=None)
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_chat_response(captured)):
        client.chat("hello")

    assert "options" not in captured["json"]


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_gemma_client_endpoint_unchanged() -> None:
    client = GemmaClient(host="http://example:9999")
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_chat_response(captured)):
        client.chat("hello")

    assert captured["url"] == "http://example:9999/api/chat"
