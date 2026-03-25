from __future__ import annotations

import pytest

try:
    from scripts.system import ai_bridge, colab_worker_lease, inspect_uspto_session
except ImportError:
    ai_bridge = colab_worker_lease = inspect_uspto_session = None

pytestmark = pytest.mark.skipif(
    ai_bridge is None, reason="scripts.system modules not importable"
)


def test_inspect_uspto_session_safe_url_strips_query_and_fragment() -> None:
    assert (
        inspect_uspto_session._safe_url("https://auth.uspto.gov/callback?code=secret&state=demo#fragment")
        == "https://auth.uspto.gov/callback"
    )


def test_colab_worker_safe_url_strips_query_and_fragment() -> None:
    assert (
        colab_worker_lease._safe_url("https://colab.research.google.com/drive/123?authuser=1#scroll")
        == "https://colab.research.google.com/drive/123"
    )


def test_ai_bridge_write_log_redacts_sensitive_prompt_and_response(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SCBE_ALLOWED_VAULT_ROOTS", str(tmp_path))
    log_path = ai_bridge.write_log(
        str(tmp_path),
        "hf",
        "demo-model",
        "token=supersecret-value",
        "Authorization: Bearer sk-abc1234567890",
    )
    text = log_path.read_text(encoding="utf-8")
    assert "supersecret-value" not in text
    assert "sk-abc1234567890" not in text
    assert "[redacted]" in text
