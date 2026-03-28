import sys
from pathlib import Path

import pytest

pytest.importorskip(
    "fastapi", reason="fastapi is required for browser session pool tests"
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.browser import main as browser_main  # noqa: E402


class FakeBrowser:
    def __init__(self, config):
        self.config = config
        self._is_initialized = False
        self.closed = False
        self.reset_calls = 0

    async def initialize(self):
        self._is_initialized = True

    async def close(self):
        self.closed = True
        self._is_initialized = False

    def reset_session(self):
        self.reset_calls += 1


@pytest.fixture(autouse=True)
def _cleanup_browser_pool(monkeypatch):
    original_pool_limit = browser_main._BROWSER_SESSION_POOL_LIMIT
    original_cls = browser_main.PlaywrightWrapper
    browser_main._session_browsers.clear()
    browser_main._browser_lru.clear()
    monkeypatch.setattr(browser_main, "PlaywrightWrapper", FakeBrowser)
    yield
    browser_main._session_browsers.clear()
    browser_main._browser_lru.clear()
    browser_main._BROWSER_SESSION_POOL_LIMIT = original_pool_limit
    monkeypatch.setattr(browser_main, "PlaywrightWrapper", original_cls)


@pytest.mark.asyncio
async def test_ensure_browser_reuses_same_session():
    browser_main._BROWSER_SESSION_POOL_LIMIT = 2
    first = await browser_main.ensure_browser("session-a")
    second = await browser_main.ensure_browser("session-a")
    assert first is second
    assert len(browser_main._session_browsers) == 1


@pytest.mark.asyncio
async def test_ensure_browser_evicts_lru_when_pool_full():
    browser_main._BROWSER_SESSION_POOL_LIMIT = 2
    first = await browser_main.ensure_browser("session-a")
    await browser_main.ensure_browser("session-b")
    await browser_main.ensure_browser("session-c")

    assert "session-a" not in browser_main._session_browsers
    assert first.closed is True
    assert set(browser_main._session_browsers.keys()) == {"session-b", "session-c"}
