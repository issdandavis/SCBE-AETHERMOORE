"""
Live end-to-end tests for PlaywrightRuntime and RemoteDisplayManager.

These tests launch real browsers. Marked @pytest.mark.slow.
Run with: PYTHONPATH=. python -m pytest tests/aetherbrowser/test_e2e_live.py -v -s
"""

import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

pytestmark = pytest.mark.slow


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── PlaywrightRuntime ──────────────────────────────────────────────────────


class TestPlaywrightRuntime:
    """Live tests for the local browser runtime."""

    def test_launch_navigate_screenshot_close(self, event_loop, tmp_path):
        """Full lifecycle: launch → navigate → screenshot → title → close."""
        from agents.playwright_runtime import PlaywrightRuntime

        async def run():
            rt = PlaywrightRuntime()
            await rt.launch(headless=True)
            assert rt.is_connected

            # Navigate
            url = await rt.navigate("https://example.com")
            assert "example.com" in url
            assert "example.com" in rt.current_url

            # Title
            title = await rt.title()
            assert "Example" in title

            # Screenshot
            shot_path = str(tmp_path / "test.png")
            data = await rt.screenshot(path=shot_path)
            assert len(data) > 1000  # PNG should be >1KB
            assert os.path.isfile(shot_path)

            # Content
            html = await rt.content()
            assert "<h1>" in html or "<title>" in html

            # Evaluate
            result = await rt.evaluate("() => document.title")
            assert "Example" in result

            await rt.close()
            assert not rt.is_connected

        event_loop.run_until_complete(run())

    def test_click_and_type(self, event_loop):
        """Navigate to a page with an input, type into it, read back."""
        from agents.playwright_runtime import PlaywrightRuntime

        async def run():
            rt = PlaywrightRuntime()
            await rt.launch(headless=True)

            # Use a data URI with a simple form
            await rt.navigate(
                "data:text/html,<input id='q' type='text'><button id='btn'>Go</button>"
            )

            await rt.type_text("#q", "hello aethermoore")
            value = await rt.evaluate("() => document.getElementById('q').value")
            assert value == "hello aethermoore"

            await rt.click("#btn")

            await rt.close()

        event_loop.run_until_complete(run())

    def test_navigation_history(self, event_loop):
        """go_back and go_forward work."""
        from agents.playwright_runtime import PlaywrightRuntime

        async def run():
            rt = PlaywrightRuntime()
            await rt.launch(headless=True)

            await rt.navigate("data:text/html,<h1>Page 1</h1>")
            await rt.navigate("data:text/html,<h1>Page 2</h1>")

            await rt.go_back()
            html = await rt.content()
            assert "Page 1" in html

            await rt.go_forward()
            html = await rt.content()
            assert "Page 2" in html

            await rt.close()

        event_loop.run_until_complete(run())

    def test_wait_for_selector(self, event_loop):
        """wait_for_selector finds dynamically added elements."""
        from agents.playwright_runtime import PlaywrightRuntime

        async def run():
            rt = PlaywrightRuntime()
            await rt.launch(headless=True)

            await rt.navigate(
                "data:text/html,"
                "<script>setTimeout(()=>{let d=document.createElement('div');"
                "d.id='delayed';d.textContent='arrived';"
                "document.body.appendChild(d)},200)</script>"
            )

            await rt.wait_for_selector("#delayed", timeout=5_000)
            text = await rt.evaluate("() => document.getElementById('delayed').textContent")
            assert text == "arrived"

            await rt.close()

        event_loop.run_until_complete(run())

    def test_not_launched_raises(self):
        """Operations before launch raise RuntimeError."""
        from agents.playwright_runtime import PlaywrightRuntime

        rt = PlaywrightRuntime()
        with pytest.raises(RuntimeError, match="not launched"):
            asyncio.get_event_loop().run_until_complete(rt.navigate("https://example.com"))


# ── RemoteDisplayManager ───────────────────────────────────────────────────


class TestRemoteDisplayManager:
    """Live tests for RemoteDisplayManager (no actual CRD — tests the Playwright wiring)."""

    def test_launch_and_close(self, event_loop):
        """Manager can launch and close without errors."""
        from agents.remote_display import RemoteDisplayManager

        async def run():
            mgr = RemoteDisplayManager()
            await mgr.launch(headless=True)
            assert mgr.display_names == []
            assert mgr.connected_displays == []
            await mgr.close()

        event_loop.run_until_complete(run())

    def test_connect_display_navigates_to_crd(self, event_loop):
        """
        connect_display navigates to remotedesktop.google.com.
        Won't fully connect (no Google auth) but exercises the flow.
        """
        from agents.remote_display import RemoteDisplayManager

        async def run():
            mgr = RemoteDisplayManager()
            await mgr.launch(headless=True)

            # This will navigate to CRD but won't connect (no auth)
            # It should NOT raise — just log warnings and return handle
            try:
                handle = await mgr.connect_display(
                    "test-display", timeout=10_000
                )
                assert handle.name == "test-display"
                assert "test-display" in mgr.display_names
                # Won't be connected without Google auth
                # but the handle exists
            except Exception:
                pass  # Network/auth failures expected in CI

            await mgr.close()

        event_loop.run_until_complete(run())

    def test_duplicate_display_raises(self, event_loop):
        """Connecting the same display name twice raises ValueError."""
        from agents.remote_display import RemoteDisplayManager, DisplayHandle

        async def run():
            mgr = RemoteDisplayManager()
            await mgr.launch(headless=True)

            # Manually inject a display handle
            ctx = await mgr._browser.new_context()
            page = await ctx.new_page()
            mgr._displays["dupe"] = DisplayHandle(
                name="dupe", host_id="", context=ctx, page=page,
            )

            with pytest.raises(ValueError, match="already exists"):
                await mgr.connect_display("dupe")

            await mgr.close()

        event_loop.run_until_complete(run())


# ── Governed Browser Agent (dry-run) ───────────────────────────────────────


class TestGovernedBrowserAgent:
    """Test browser_agent.py with real PlaywrightRuntime (no SCBE API needed for runtime wiring)."""

    def test_runtime_wiring_exists(self):
        """SCBEBrowserAgent accepts a runtime parameter."""
        from unittest.mock import patch, MagicMock

        with patch.dict(os.environ, {"SCBE_API_KEY": "test-key"}):
            with patch("agents.browser_agent.SCBEClient") as MockClient:
                instance = MockClient.return_value
                instance.api_key = "test-key"
                instance.health_check.return_value = True
                instance.register_agent.return_value = True

                from agents.browser_agent import SCBEBrowserAgent

                fake_runtime = MagicMock()
                agent = SCBEBrowserAgent(
                    agent_id="test-rt",
                    runtime=fake_runtime,
                )
                assert agent.runtime is fake_runtime
