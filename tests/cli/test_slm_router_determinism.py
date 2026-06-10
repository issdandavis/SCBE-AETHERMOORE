"""Tests that OllamaAdapter passes temperature + seed to Ollama.

Without these the gate is non-deterministic across runs of the same
prompt (Petri Result E, 2026-05-08). These tests pin the contract so
we can detect any future regression that drops the options block.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.cli.slm_router import OllamaAdapter


def _has_httpx() -> bool:
    try:
        import httpx  # noqa: F401, PLC0415

        return True
    except ImportError:
        return False


def _captured_body_response_pair(captured: dict, response_text: str = '{"choice":"A","confidence":0.9}'):
    """httpx.post mock side effect that records the JSON body and returns OK."""

    def _side_effect(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        fake = MagicMock()
        fake.raise_for_status.return_value = None
        fake.json.return_value = {"response": response_text}
        return fake

    return _side_effect


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_default_sends_temperature_zero_and_seed() -> None:
    adapter = OllamaAdapter()
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_body_response_pair(captured)):
        adapter.classify("test prompt", ["A", "B"])

    body = captured["json"]
    assert "options" in body, "default OllamaAdapter must send an options block"
    assert body["options"]["temperature"] == 0.0
    assert body["options"]["seed"] == 42


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_custom_temperature_and_seed_round_trip() -> None:
    adapter = OllamaAdapter(temperature=0.7, seed=1234)
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_body_response_pair(captured)):
        adapter.classify("test", ["A", "B"])

    assert captured["json"]["options"]["temperature"] == 0.7
    assert captured["json"]["options"]["seed"] == 1234


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_omits_options_when_both_disabled() -> None:
    """Setting both to None disables the options block entirely so
    Ollama uses its model defaults — useful for benchmarking what the
    model does without our pinning."""
    adapter = OllamaAdapter(temperature=None, seed=None)
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_body_response_pair(captured)):
        adapter.classify("test", ["A", "B"])

    assert "options" not in captured["json"]


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_partial_options_when_only_one_set() -> None:
    """If only temperature is pinned and seed is None, the options
    block carries just temperature (and vice versa)."""
    adapter = OllamaAdapter(temperature=0.0, seed=None)
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_body_response_pair(captured)):
        adapter.classify("test", ["A", "B"])

    assert "options" in captured["json"]
    assert captured["json"]["options"] == {"temperature": 0.0}


@pytest.mark.skipif(not _has_httpx(), reason="httpx not installed")
def test_ollama_adapter_post_url_unchanged() -> None:
    """The options change must not move the endpoint."""
    adapter = OllamaAdapter(host="http://example:9999")
    captured: dict = {}
    with patch("httpx.post", side_effect=_captured_body_response_pair(captured)):
        adapter.classify("test", ["A", "B"])

    assert captured["url"] == "http://example:9999/api/generate"
