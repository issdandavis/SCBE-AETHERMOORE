from __future__ import annotations

from scripts import pypi_build


def test_ensure_build_module_available_when_present(monkeypatch) -> None:
    monkeypatch.setattr(pypi_build.importlib.util, "find_spec", lambda name: object())
    called = {"pip": False}

    def _unexpected_pip(*_args, **_kwargs):
        called["pip"] = True
        raise AssertionError("pip install should not run when module is present")

    monkeypatch.setattr(pypi_build.subprocess, "run", _unexpected_pip)
    assert pypi_build.ensure_build_module_available(auto_bootstrap=True) is True
    assert called["pip"] is False


def test_ensure_build_module_available_without_bootstrap(monkeypatch) -> None:
    monkeypatch.setattr(pypi_build.importlib.util, "find_spec", lambda name: None)
    assert pypi_build.ensure_build_module_available(auto_bootstrap=False) is False


def test_ensure_build_module_available_bootstraps(monkeypatch) -> None:
    state = {"count": 0}

    def _find_spec(_name: str):
        state["count"] += 1
        return None if state["count"] == 1 else object()

    monkeypatch.setattr(pypi_build.importlib.util, "find_spec", _find_spec)

    class _Proc:
        returncode = 0

    calls: list[list[str]] = []

    def _run(cmd, check=False):  # noqa: ARG001
        calls.append(cmd)
        return _Proc()

    monkeypatch.setattr(pypi_build.subprocess, "run", _run)
    assert pypi_build.ensure_build_module_available(auto_bootstrap=True) is True
    assert calls and calls[0][0:3] == [pypi_build.sys.executable, "-m", "pip"]
