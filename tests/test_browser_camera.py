"""Tests for browser_camera -- the document-level camera (doc minimap + 3-state fog + move_camera).

ThreeStateFog and PageMinimap are pure (synthetic feed with document+scroll). The move_camera scroll is a
browser test against a TALL fixture (doc >> viewport), skipped if no Chrome is launchable.
"""

from __future__ import annotations

import pytest

from python.scbe.browser_camera import HIDDEN, SEEN, VISIBLE, PageMinimap, ThreeStateFog


def test_three_state_fog_hidden_seen_visible_and_snapshot():
    fog = ThreeStateFog()
    fog.update({"A1", "B1"}, {"A1": ["r0"], "B1": ["r1"]})
    assert fog.of("A1") == VISIBLE and fog.name("A1") == "visible"
    assert fog.of("Z9") == HIDDEN  # never seen
    # next frame: A1 scrolled out of view -> SEEN (stale), its snapshot remembered; C1 newly VISIBLE
    fog.update({"B1", "C1"}, {"B1": ["r1"], "C1": ["r2"]})
    assert fog.of("A1") == SEEN and fog.seen_snapshot("A1") == ["r0"]
    assert fog.of("B1") == VISIBLE and fog.of("C1") == VISIBLE


def test_page_minimap_is_document_coords_with_viewport_rectangle():
    feed = {
        "viewport": {"w": 1000, "h": 800},
        "scroll": {"x": 0, "y": 0},
        "document": {"w": 1000, "h": 3000},  # 3000 tall -> much bigger than the 800 viewport
        "elements": [
            {"ref": "r0", "x": 10, "y": 10, "w": 20, "h": 20},  # near top -> in viewport
            {"ref": "r1", "x": 10, "y": 2400, "w": 20, "h": 20},  # far down -> below the fold
        ],
    }
    mm = PageMinimap(feed, cols=10, rows=10)
    vp = mm.viewport_cells()
    top = next(c for c, els in mm.by_cell.items() if els[0]["ref"] == "r0")
    bot = next(c for c, els in mm.by_cell.items() if els[0]["ref"] == "r1")
    assert top in vp  # the top element's doc-cell is within the viewport rectangle
    assert bot not in vp  # the far-down element is OUTSIDE the viewport (needs move_camera)
    assert mm.dh == 3000  # minimap spans the whole document, not just the viewport


# --- browser: move_camera scrolls an off-screen element into view on a TALL page ---
pytest.importorskip("playwright")
from python.scbe.ai_browser import AIBrowser  # noqa: E402
from python.scbe.browser_camera import Camera  # noqa: E402

TALL = (
    "data:text/html,<style>body{margin:0}</style>"
    "<button style='position:absolute;left:10px;top:10px'>top</button>"
    "<button style='position:absolute;left:10px;top:2500px'>bottom</button>"
    "<div style='height:3000px'></div>"
)


def test_move_camera_brings_offscreen_into_view():
    try:
        br = AIBrowser(headless=True).__enter__()
    except Exception as exc:
        pytest.skip("no launchable browser: %s" % type(exc).__name__)
    try:
        page = br.open(TALL)
        page.set_viewport_size({"width": 1000, "height": 800})
        cam = Camera(br, page, cols=10, rows=10)
        assert cam.minimap.dh > 2000  # tall document
        # the 'bottom' button (doc y=2500) is off-screen at scroll 0
        bottom = next(e["ref"] for e in cam.feed["elements"] if not cam.in_viewport(e["ref"]))
        before = cam.observe()["scroll"]["y"]
        cam.move_camera(bottom)
        after = cam.observe()
        assert after["scroll"]["y"] > before  # the camera scrolled
        assert cam.in_viewport(bottom)  # the target is now visible
        assert after["fog"]["visible"] >= 1
    finally:
        br.__exit__(None, None, None)
