from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

try:
    from cryptography.fernet import Fernet  # noqa: F401
except BaseException:
    pytest.skip("cryptography package not functional (cffi backend missing)", allow_module_level=True)


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


secret_store = _load_module("test_secret_store_real", "src/security/secret_store.py")
sys.modules["src.security.secret_store"] = secret_store
colab_bridge = _load_module(
    "test_colab_n8n_bridge",
    "external/codex-skills-live/scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py",
)


def test_secret_store_persists_ciphertext_only(tmp_path: Path, monkeypatch) -> None:
    store_path = tmp_path / ".secrets.json"
    monkeypatch.setenv(secret_store.SECRET_STORE_KEY_ENV, "unit-test-passphrase")
    monkeypatch.setattr(secret_store, "_SECRETS_DIR", tmp_path)
    monkeypatch.setattr(secret_store, "_STORE_PATH", store_path)
    monkeypatch.delenv("SCBE_UNIT_SECRET", raising=False)

    secret_store.set_secret("SCBE_UNIT_SECRET", "super-secret-value", note="unit-test")
    monkeypatch.delenv("SCBE_UNIT_SECRET", raising=False)

    payload = json.loads(store_path.read_text(encoding="utf-8"))
    entry = payload["SCBE_UNIT_SECRET"]

    assert entry["scheme"] == "fernet"
    assert "ciphertext" in entry
    assert "value" not in entry
    assert "super-secret-value" not in store_path.read_text(encoding="utf-8")
    assert secret_store.get_secret("SCBE_UNIT_SECRET", "") == "super-secret-value"
    assert secret_store.has_secret("SCBE_UNIT_SECRET") is True


def test_secret_store_migrates_legacy_plaintext_entries(tmp_path: Path, monkeypatch) -> None:
    store_path = tmp_path / ".secrets.json"
    monkeypatch.setenv(secret_store.SECRET_STORE_KEY_ENV, "unit-test-passphrase")
    monkeypatch.setattr(secret_store, "_SECRETS_DIR", tmp_path)
    monkeypatch.setattr(secret_store, "_STORE_PATH", store_path)
    monkeypatch.delenv("SCBE_LEGACY_SECRET", raising=False)

    store_path.write_text(
        json.dumps({"SCBE_LEGACY_SECRET": {"value": "legacy-secret", "note": "legacy"}}, indent=2),
        encoding="utf-8",
    )

    resolved = secret_store.get_secret("SCBE_LEGACY_SECRET", "")
    migrated = json.loads(store_path.read_text(encoding="utf-8"))["SCBE_LEGACY_SECRET"]

    assert resolved == "legacy-secret"
    assert migrated["scheme"] == "fernet"
    assert "ciphertext" in migrated
    assert "value" not in migrated
    assert "legacy-secret" not in store_path.read_text(encoding="utf-8")


def test_env_profile_emits_secret_names_without_secret_values(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "colab_n8n_bridge.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "pivot": {
                        "backend_secret_name": "SCBE_COLAB_BACKEND_URL_PIVOT",
                        "token_secret_name": "SCBE_COLAB_TOKEN_PIVOT",
                        "n8n_webhook": "https://example.com/hook",
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(colab_bridge, "CONFIG_PATH", config_path)
    monkeypatch.setattr(
        colab_bridge,
        "has_secret",
        lambda key: key
        in {
            "SCBE_COLAB_BACKEND_URL_PIVOT": "http://127.0.0.1:8888",
            "SCBE_COLAB_TOKEN_PIVOT": "secret-token-123",
        },
    )

    result = colab_bridge.env_profile(argparse.Namespace(name="pivot"))
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert result == 0
    assert "secret-token-123" not in output
    assert payload["token_secret_name"] == "SCBE_COLAB_TOKEN_PIVOT"
    assert payload["backend_secret_name"] == "SCBE_COLAB_BACKEND_URL_PIVOT"
    assert "resolve secrets locally" in payload["resolution"].lower()


def test_status_profile_omits_backend_value_and_token_value(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "colab_n8n_bridge.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "pivot": {
                        "backend_secret_name": "SCBE_COLAB_BACKEND_URL_PIVOT",
                        "token_secret_name": "SCBE_COLAB_TOKEN_PIVOT",
                        "n8n_webhook": "https://example.com/hook",
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(colab_bridge, "CONFIG_PATH", config_path)
    monkeypatch.setattr(colab_bridge, "has_secret", lambda key: key.endswith("_PIVOT"))
    monkeypatch.setattr(colab_bridge, "get_secret", lambda key, default="": "secret-token-123")

    result = colab_bridge.status_profile(argparse.Namespace(name="pivot"))
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert result == 0
    assert "secret-token-123" not in output
    assert "http://127.0.0.1:8888" not in output
    assert payload["backend_configured"] is True
    assert payload["token_configured"] is True


def test_probe_profile_omits_preview_and_secret_text(tmp_path: Path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "colab_n8n_bridge.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "pivot": {
                        "backend_secret_name": "SCBE_COLAB_BACKEND_URL_PIVOT",
                        "token_secret_name": "SCBE_COLAB_TOKEN_PIVOT",
                    }
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(colab_bridge, "CONFIG_PATH", config_path)
    monkeypatch.setattr(
        colab_bridge,
        "get_secret",
        lambda key, default="": {
            "SCBE_COLAB_BACKEND_URL_PIVOT": "http://127.0.0.1:8888",
            "SCBE_COLAB_TOKEN_PIVOT": "secret-token-123",
        }.get(key, default),
    )
    monkeypatch.setattr(
        colab_bridge,
        "probe_backend",
        lambda base, token: {
            "ok": True,
            "status": 200,
            "api_root": f"{base}/api",
            "preview": f"token={token}",
        },
    )

    result = colab_bridge.probe_profile(argparse.Namespace(name="pivot"))
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert result == 0
    assert payload["ok"] is True
    assert payload["status"] == 200
    assert payload["api_root"] == "http://127.0.0.1:8888/api"
    assert "preview" not in payload
    assert "secret-token-123" not in output
