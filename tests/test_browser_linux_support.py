"""Tests for Linux Chrome support in browser backends."""

import importlib
import importlib.util
import sys
from pathlib import Path


def _load_module_from_path(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec for {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_chrome_binary_uses_env_override(monkeypatch):
    module = importlib.import_module("agents.browsers.cdp_backend")
    monkeypatch.setenv("SCBE_CHROME_PATH", "/opt/google/chrome/chrome")

    path = module.resolve_chrome_binary(system="Linux")

    assert path == "/opt/google/chrome/chrome"


def test_resolve_chrome_binary_linux_checks_common_names(monkeypatch):
    module = importlib.import_module("agents.browsers.cdp_backend")

    monkeypatch.delenv("SCBE_CHROME_PATH", raising=False)

    def fake_which(name):
        if name == "google-chrome-stable":
            return "/usr/bin/google-chrome-stable"
        return None

    monkeypatch.setattr(module.shutil, "which", fake_which)

    path = module.resolve_chrome_binary(system="Linux")

    assert path == "/usr/bin/google-chrome-stable"


def test_get_chrome_launch_command_quotes_linux_path(monkeypatch):
    module = importlib.import_module("agents.browsers.cdp_backend")

    monkeypatch.setattr(module, "resolve_chrome_binary", lambda system=None: "/opt/Google Chrome/chrome")

    cmd = module.get_chrome_launch_command(port=9333, user_data_dir="/tmp/scbe profile")

    assert cmd.startswith('"/opt/Google Chrome/chrome" --remote-debugging-port=9333')
    assert '--user-data-dir="/tmp/scbe profile"' in cmd


def test_playwright_wrapper_prefers_linux_executable(monkeypatch):
    module = _load_module_from_path(
        "playwright_wrapper_under_test",
        str(Path("agents/browser/playwright_wrapper.py")),
    )

    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.shutil, "which", lambda name: "/usr/bin/chromium" if name == "chromium" else None)

    wrapper = module.PlaywrightWrapper(module.BrowserConfig(headless=True))
    options = wrapper._build_launch_options()

    assert options["headless"] is True
    assert options["executable_path"] == "/usr/bin/chromium"


def test_playwright_wrapper_respects_explicit_channel_over_linux_detection(monkeypatch):
    module = _load_module_from_path(
        "playwright_wrapper_under_test_2",
        str(Path("agents/browser/playwright_wrapper.py")),
    )

    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.shutil, "which", lambda _name: "/usr/bin/google-chrome")

    wrapper = module.PlaywrightWrapper(
        module.BrowserConfig(headless=False, browser_channel="chrome")
    )
    options = wrapper._build_launch_options()

    assert options == {"headless": False, "channel": "chrome"}
