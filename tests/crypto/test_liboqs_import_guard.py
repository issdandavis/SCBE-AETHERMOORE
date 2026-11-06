"""Regression tests for side-effect-free optional liboqs discovery."""

from __future__ import annotations

import builtins

from src.crypto import pqc_liboqs


def test_missing_native_library_does_not_import_oqs(monkeypatch) -> None:
    """A missing DLL must select the fallback without invoking auto-install."""
    monkeypatch.setattr(pqc_liboqs, "_native_liboqs_present", lambda: False)
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "oqs":
            raise AssertionError("oqs import would trigger liboqs-python auto-install")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    assert pqc_liboqs._load_oqs_module() is None


def test_explicit_install_path_is_detected_without_import(monkeypatch, tmp_path) -> None:
    """An explicitly managed native install remains eligible for Tier 1."""
    install_root = tmp_path / "managed-oqs"
    dll_path = install_root / "bin" / "oqs.dll"
    dll_path.parent.mkdir(parents=True)
    dll_path.touch()

    monkeypatch.setenv("OQS_INSTALL_PATH", str(install_root))
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr(pqc_liboqs, "find_library", lambda _name: None)

    assert pqc_liboqs._native_liboqs_present() is True
