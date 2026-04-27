"""Tests for RemoteDisplayManager (unit-level, no real browser)."""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


def test_import():
    """RemoteDisplayManager can be imported."""
    from agents.remote_display import RemoteDisplayManager
    mgr = RemoteDisplayManager()
    assert mgr.display_names == []
    assert mgr.connected_displays == []


def test_canvas_coord_mapping():
    """Pixel coords map correctly through canvas bounds."""
    from agents.remote_display import RemoteDisplayManager, DisplayHandle

    mgr = RemoteDisplayManager()

    handle = DisplayHandle(
        name="test",
        host_id="abc",
        context=None,
        page=None,
        connected=True,
        resolution=(1920, 1080),
        canvas_bounds={"x": 10, "y": 20, "width": 960, "height": 540},
    )

    # (0, 0) in remote space → top-left of canvas
    cx, cy = mgr._canvas_coords(handle, 0, 0)
    assert cx == 10.0  # canvas x offset
    assert cy == 20.0  # canvas y offset

    # (1920, 1080) → bottom-right of canvas
    cx, cy = mgr._canvas_coords(handle, 1920, 1080)
    assert cx == 10.0 + 960.0  # x + full width
    assert cy == 20.0 + 540.0  # y + full height

    # Midpoint
    cx, cy = mgr._canvas_coords(handle, 960, 540)
    assert cx == pytest.approx(10.0 + 480.0)
    assert cy == pytest.approx(20.0 + 270.0)


def test_canvas_coords_no_bounds():
    """Without canvas bounds, coords pass through unchanged."""
    from agents.remote_display import RemoteDisplayManager, DisplayHandle

    mgr = RemoteDisplayManager()
    handle = DisplayHandle(
        name="test",
        host_id="abc",
        context=None,
        page=None,
        connected=True,
        resolution=(1920, 1080),
        canvas_bounds=None,
    )

    cx, cy = mgr._canvas_coords(handle, 500, 300)
    assert cx == 500.0
    assert cy == 300.0


def test_get_display_not_found():
    """Accessing a nonexistent display raises ValueError."""
    from agents.remote_display import RemoteDisplayManager

    mgr = RemoteDisplayManager()
    with pytest.raises(ValueError, match="not found"):
        mgr._get_display("nonexistent")


def test_require_browser_not_launched():
    """Operations before launch() raise RuntimeError."""
    from agents.remote_display import RemoteDisplayManager

    mgr = RemoteDisplayManager()
    with pytest.raises(RuntimeError, match="not launched"):
        mgr._require_browser()


def test_playwright_runtime_remote_not_open():
    """remote_screenshot before open_remote_display raises RuntimeError."""
    from agents.playwright_runtime import PlaywrightRuntime

    rt = PlaywrightRuntime()
    with pytest.raises(RuntimeError, match="No remote displays"):
        import asyncio
        asyncio.get_event_loop().run_until_complete(rt.remote_screenshot("test"))
