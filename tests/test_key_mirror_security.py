from __future__ import annotations

import hashlib
import importlib.util
import platform
import sys
from pathlib import Path

import pytest

if platform.system() != "Windows":
    pytest.skip(
        "Windows-only tests (requires ctypes.windll / DPAPI)", allow_module_level=True
    )


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


key_mirror = _load_module(
    "test_key_mirror_security_mod",
    "external/codex-skills-live/scbe-api-key-local-mirror/scripts/key_mirror.py",
)


def test_key_mirror_sensitive_fingerprint_uses_pbkdf2(monkeypatch) -> None:
    monkeypatch.setenv("SCBE_METADATA_HASH_KEY", "unit-test-key-mirror-salt")

    fingerprint = key_mirror.sensitive_fingerprint("super-secret-value")
    legacy = hashlib.sha256(b"super-secret-value").hexdigest()

    assert len(fingerprint) == 64
    assert fingerprint != legacy
