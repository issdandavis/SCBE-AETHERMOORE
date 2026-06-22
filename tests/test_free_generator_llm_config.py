import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import free_generator as fg  # noqa: E402


def test_resolve_llm_config_uses_defaults_when_env_absent(monkeypatch):
    monkeypatch.delenv("SCBE_LLM_BASE", raising=False)
    monkeypatch.delenv("SCBE_LLM_KEY", raising=False)
    monkeypatch.delenv("SCBE_LLM_MODEL", raising=False)

    cfg = fg.resolve_llm_config()

    assert cfg.base == fg.DEFAULT_BASE
    assert cfg.key == fg.DEFAULT_KEY
    assert cfg.model == fg.DEFAULT_MODEL


def test_resolve_llm_config_uses_env_and_explicit_overrides(monkeypatch):
    monkeypatch.setenv("SCBE_LLM_BASE", "http://env-base/v1")
    monkeypatch.setenv("SCBE_LLM_KEY", "env-key")
    monkeypatch.setenv("SCBE_LLM_MODEL", "env-model")

    env_cfg = fg.resolve_llm_config()
    explicit_cfg = fg.resolve_llm_config(base="http://arg-base/v1", key="arg-key", model="arg-model")

    assert env_cfg == fg.LLMConfig(base="http://env-base/v1", key="env-key", model="env-model")
    assert explicit_cfg == fg.LLMConfig(base="http://arg-base/v1", key="arg-key", model="arg-model")


def test_chat_with_config_delegates_to_existing_transport(monkeypatch):
    captured = {}

    def fake_chat(messages, *, base, key, model, timeout=120):
        captured.update({"messages": messages, "base": base, "key": key, "model": model, "timeout": timeout})
        return "ok"

    monkeypatch.setattr(fg, "_chat", fake_chat)
    cfg = fg.LLMConfig(base="http://base/v1", key="secret", model="m")

    assert fg.chat_with_config([{"role": "user", "content": "hi"}], cfg, timeout=7) == "ok"
    assert captured == {
        "messages": [{"role": "user", "content": "hi"}],
        "base": "http://base/v1",
        "key": "secret",
        "model": "m",
        "timeout": 7,
    }
