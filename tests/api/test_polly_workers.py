"""Tests for Polly worker / integration surfaces."""

from __future__ import annotations

import pytest

from src.api.polly_workers import (
    VOICE_GREETING_DEFAULT,
    all_statuses,
    call_service_status,
    hf_status,
    kaggle_status,
    ollama_status,
    voice_response_twiml,
)

# ---------------------------------------------------------------------------
# Status reporting
# ---------------------------------------------------------------------------


def test_ollama_status_always_returns_a_status() -> None:
    s = ollama_status()
    assert s.name == "ollama"
    assert isinstance(s.configured, bool)


def test_hf_status_unconfigured_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    s = hf_status()
    assert s.name == "huggingface"
    assert s.configured is False


def test_hf_status_configured_when_token_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    s = hf_status()
    assert s.configured is True
    assert "model=" in s.detail


def test_kaggle_status_returns_structured_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without globally mocking Path, just verify the function returns a sane
    structure regardless of local Kaggle setup."""
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    s = kaggle_status()
    assert s.name == "kaggle"
    assert isinstance(s.configured, bool)
    assert isinstance(s.detail, str)


def test_kaggle_status_configured_when_env_creds_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAGGLE_USERNAME", "testuser")
    monkeypatch.setenv("KAGGLE_KEY", "testkey")
    s = kaggle_status()
    assert s.configured is True
    assert "user=testuser" in s.detail


def test_call_service_unconfigured_without_twilio_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"):
        monkeypatch.delenv(var, raising=False)
    s = call_service_status()
    assert s.name == "twilio_voice"
    assert s.configured is False


def test_call_service_configured_with_all_three(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+13608080876")
    s = call_service_status()
    assert s.configured is True
    assert "+13608080876" in s.detail


def test_all_statuses_returns_four_integrations() -> None:
    statuses = all_statuses()
    names = {s.name for s in statuses}
    assert names == {"ollama", "huggingface", "kaggle", "twilio_voice"}


# ---------------------------------------------------------------------------
# Voice TwiML
# ---------------------------------------------------------------------------


def test_voice_response_uses_default_greeting() -> None:
    xml = voice_response_twiml()
    assert "<?xml" in xml
    assert VOICE_GREETING_DEFAULT.split(",")[0] in xml  # first word of greeting
    assert "<Record" in xml  # falls back to voicemail


def test_voice_response_with_bridge_streams_to_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POLLY_VOICE_AGENT_URL", raising=False)
    xml = voice_response_twiml(voice_agent_url="wss://example.com/agent")
    assert '<Stream url="wss://example.com/agent"/>' in xml
    assert "<Record" not in xml  # bridge mode, no voicemail


def test_voice_response_uses_env_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLLY_VOICE_AGENT_URL", "wss://env.example/stream")
    xml = voice_response_twiml()
    assert "wss://env.example/stream" in xml


def test_voice_response_escapes_xml_specials() -> None:
    """Custom greeting with & and < should not break the XML."""
    xml = voice_response_twiml(greeting="Hi & welcome <here>")
    assert "&amp;" in xml
    assert "&lt;here>" in xml
    # And the result should still be parseable XML structure (no raw <here>).
    assert "<here>" not in xml


# ---------------------------------------------------------------------------
# HF push / Kaggle pull — we don't have credentials in test env, just verify
# the failure path returns structured errors instead of raising.
# ---------------------------------------------------------------------------


def test_push_to_hf_returns_structured_error_without_token(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    from src.api.polly_workers import push_training_corpus_to_hf

    result = push_training_corpus_to_hf(corpus_dir=tmp_path)
    assert result["ok"] is False
    assert "HF_TOKEN" in (result["error"] or "")


def test_pull_kaggle_returns_structured_error_when_unconfigured(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    # Note: this still passes if user has ~/.kaggle/kaggle.json. We only assert
    # the function returns a dict and never raises.
    from src.api.polly_workers import pull_kaggle_dataset

    result = pull_kaggle_dataset(dataset_slug="invalid/does-not-exist", target_dir=tmp_path)
    assert isinstance(result, dict)
    assert "ok" in result
    assert "error" in result


def test_pull_kaggle_rejects_invalid_slug(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("KAGGLE_USERNAME", "x")
    monkeypatch.setenv("KAGGLE_KEY", "y")
    from src.api.polly_workers import pull_kaggle_dataset

    result = pull_kaggle_dataset(dataset_slug="no-slash-here", target_dir=tmp_path)
    assert result["ok"] is False
    assert "invalid slug" in (result["error"] or "")
