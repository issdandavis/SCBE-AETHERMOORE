from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "publish" / "post_to_devto.py"
    spec = importlib.util.spec_from_file_location("post_to_devto_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_api_key_ignores_placeholder_from_connector_file(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.delenv("DEVTO_API_KEY", raising=False)
    monkeypatch.delenv("DEV_TO_API_KEY", raising=False)
    monkeypatch.delenv("DEV_API_KEY", raising=False)

    config_dir = tmp_path / "config" / "connector_oauth"
    config_dir.mkdir(parents=True)
    (config_dir / ".env.connector.oauth").write_text("DEVTO_API_KEY=REPLACE_ME\n", encoding="utf-8")

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    assert module._load_api_key() is None


def test_load_api_key_prefers_real_env_value(monkeypatch):
    module = _load_module()
    monkeypatch.setenv("DEVTO_API_KEY", "real-devto-key")
    monkeypatch.delenv("DEV_TO_API_KEY", raising=False)
    monkeypatch.delenv("DEV_API_KEY", raising=False)

    assert module._load_api_key() == "real-devto-key"
