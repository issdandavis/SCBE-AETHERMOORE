from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


autosync = _load_module("test_local_cloud_autosync_security", "scripts/local_cloud_autosync.py")


def test_detect_github_repo_rejects_non_github_substring(monkeypatch) -> None:
    class _FakeProc:
        stdout = "https://evil.example.com/github.com/owner/repo.git\n"

    monkeypatch.setattr(autosync.shutil, "which", lambda name: "git")
    monkeypatch.setattr(autosync.subprocess, "run", lambda *args, **kwargs: _FakeProc())

    assert autosync.detect_github_repo() == ""


def test_detect_github_repo_accepts_https_origin(monkeypatch) -> None:
    class _FakeProc:
        stdout = "https://github.com/issdandavis/SCBE-AETHERMOORE.git\n"

    monkeypatch.setattr(autosync.shutil, "which", lambda name: "git")
    monkeypatch.setattr(autosync.subprocess, "run", lambda *args, **kwargs: _FakeProc())

    assert autosync.detect_github_repo() == "issdandavis/SCBE-AETHERMOORE"
