from __future__ import annotations

import importlib
import os


def _reload_auth_config():
    import src.api.auth_config as auth_config

    return importlib.reload(auth_config)


def test_load_api_keys_returns_empty_without_env(monkeypatch) -> None:
    monkeypatch.delenv("SCBE_API_KEYS", raising=False)
    monkeypatch.delenv("SCBE_ALLOW_DEMO_KEYS", raising=False)
    monkeypatch.delenv("SCBE_ENV", raising=False)
    monkeypatch.delenv("NODE_ENV", raising=False)

    auth_config = _reload_auth_config()
    assert auth_config.load_api_keys() == {}


def test_load_api_keys_uses_explicit_demo_flag(monkeypatch) -> None:
    monkeypatch.delenv("SCBE_API_KEYS", raising=False)
    monkeypatch.setenv("SCBE_ALLOW_DEMO_KEYS", "1")
    monkeypatch.setenv("SCBE_ENV", "test")

    auth_config = _reload_auth_config()
    keys = auth_config.load_api_keys()
    assert keys["demo_key_12345"] == "demo_user"
    assert keys["pilot_key_67890"] == "pilot_customer"


def test_load_api_keys_prefers_explicit_json(monkeypatch) -> None:
    monkeypatch.setenv("SCBE_API_KEYS", '{"ship-key":"captain"}')
    monkeypatch.setenv("SCBE_ALLOW_DEMO_KEYS", "1")

    auth_config = _reload_auth_config()
    assert auth_config.load_api_keys() == {"ship-key": "captain"}

