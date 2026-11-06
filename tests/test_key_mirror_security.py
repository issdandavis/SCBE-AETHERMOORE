from __future__ import annotations

import hashlib
import importlib.util
import platform
import sys
from pathlib import Path

import pytest

if platform.system() != "Windows":
    pytest.skip("Windows-only tests (requires ctypes.windll / DPAPI)", allow_module_level=True)


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
    "scripts/security/key_mirror.py",
)


def test_key_mirror_sensitive_fingerprint_uses_pbkdf2(monkeypatch) -> None:
    monkeypatch.setenv("SCBE_METADATA_HASH_KEY", "unit-test-key-mirror-salt")

    fingerprint = key_mirror.sensitive_fingerprint("super-secret-value")
    legacy = hashlib.sha256(b"super-secret-value").hexdigest()

    assert len(fingerprint) == 64
    assert fingerprint != legacy


def test_key_mirror_real_dpapi_roundtrip_is_ciphertext_only(tmp_path, monkeypatch):
    monkeypatch.setenv("SCBE_METADATA_HASH_KEY", "unit-test-key-mirror-salt")
    mirror = key_mirror.KeyMirror(tmp_path / "fixture-vault")
    value = "dummy-value-for-dpapi-roundtrip-only"
    result = mirror.store("fixture-service", value, "unit-test")
    ciphertext = Path(result["stored_blob"]).read_bytes()
    assert ciphertext and value.encode() not in ciphertext
    assert value not in mirror.index_file.read_text(encoding="utf-8")
    assert value not in str(mirror.list_services())
    resolved = mirror.resolve("fixture-service")
    assert resolved["value"] == value
    assert resolved["token_id"] == result["token_id"]


def test_key_mirror_real_dpapi_rejects_wrong_entropy():
    ciphertext = key_mirror.dpapi_protect(b"dummy-value", b"fixture-service-a", "unit-test")
    assert key_mirror.dpapi_unprotect(ciphertext, b"fixture-service-a") == b"dummy-value"
    with pytest.raises(OSError):
        key_mirror.dpapi_unprotect(ciphertext, b"fixture-service-b")
