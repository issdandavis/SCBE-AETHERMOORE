"""Tests for browser_map -- the layered, StarCraft-style map viewer.

The tiling/fog/cursor/hybrid-view logic is pure (synthetic feed, no browser) and locked deterministically.
The hover (hover-not-click, separate from scroll) is a browser test that skips if no Chrome is launchable.
"""

from __future__ import annotations

import pytest

from python.scbe.browser_map import FogOfWar, MapTiling, MapView

SYNTHETIC = {
    "viewport": {"w": 900, "h": 900},
    "elements": [
        {"ref": "r0", "x": 20, "y": 20, "w": 60, "h": 60, "name": "top-left"},  # center (50,50)   -> A1
        {"ref": "r1", "x": 220, "y": 220, "w": 60, "h": 60, "name": "mid"},  # center (250,250) -> C3
        {"ref": "r2", "x": 820, "y": 820, "w": 60, "h": 60, "name": "corner"},  # center (850,850) -> I9
    ],
}


def test_tiling_square_diamond_and_triangle_quadrant():
    t = MapTiling(900, 900, 9, 9)
    assert t.square(50, 50) == (0, 0) and t.label((0, 0)) == "A1"
    assert t.square(850, 850) == (8, 8) and t.label((8, 8)) == "I9"
    assert t.square(-5, 5) is None  # off the viewport
    loc = t.locate(205, 205)
    assert loc["label"] == "C3"  # the square (image cell)
    assert loc["diamond"] == (2, 2)  # nearest lattice corner = diamond center
    assert loc["triangle"] == "ES"  # which corner-square the point falls in


def test_neighbors_are_the_four_reaches_clamped():
    t = MapTiling(900, 900, 9, 9)
    assert set(t.neighbors((0, 0))) == {"E", "S"}  # top-left corner: only east + south exist
    assert set(t.neighbors((4, 4))) == {"N", "S", "E", "W"}  # interior: all four


def test_fog_reveal_persists():
    fog = FogOfWar()
    fog.reveal((0, 0))
    fog.reveal((1, 0))
    assert fog.visible((0, 0)) and fog.visible((1, 0)) and not fog.visible((5, 5))
    assert fog.panorama() == ["A1", "B1"]


def test_mapview_pan_reveals_and_hybrid_view():
    mv = MapView(SYNTHETIC, cols=9, rows=9)
    assert mv.look()["cursor"] == "A1"
    assert [e["name"] for e in mv.look()["focus"]["elements"]] == ["top-left"]
    assert mv.look()["focus"]["image_region"] == {"x": 0, "y": 0, "w": 100, "h": 100}
    mv.pan("E")
    look = mv.pan("S")
    assert look["cursor"] == "B2"
    assert set(look["revealed"]) == {"A1", "B1", "B2"}  # fog persists across pans
    # neighbors are returned as TEXT (the triangle reaches), focus is the image cell
    assert set(look["context"]) <= {"N", "S", "E", "W"}


def test_pan_rejects_bad_direction():
    mv = MapView(SYNTHETIC)
    with pytest.raises(ValueError):
        mv.pan("UP-LEFT")


# SC2-style observation: minimap (overview) + screen (detail) + available_actions (legal this frame)
OBS_FEED = {
    "viewport": {"w": 900, "h": 900},
    "elements": [
        {"ref": "r0", "x": 20, "y": 20, "w": 60, "h": 60, "name": "Login", "editable": False, "role": "button"},
        {"ref": "r1", "x": 220, "y": 220, "w": 60, "h": 60, "name": "search", "editable": True, "role": "input"},
    ],
}


def test_available_actions_reflects_edges_and_editability():
    mv = MapView(OBS_FEED, cols=9, rows=9)  # cursor starts at A1 (top-left corner, non-editable button)
    a = mv.available_actions()
    assert set(a) == {"read", "pan:S", "pan:E", "hover", "activate"}  # no off-board N/W, no type
    mv.cursor = (2, 2)  # the editable input cell (interior)
    b = mv.available_actions()
    assert {"pan:N", "pan:S", "pan:E", "pan:W", "hover", "activate", "type"} <= set(b)


def test_minimap_overview_and_screen_detail():
    mv = MapView(OBS_FEED, cols=9, rows=9)
    obs = mv.observe()
    assert set(obs) == {"minimap", "screen", "available_actions"}
    mm = obs["minimap"]
    assert mm["cursor"] == "A1" and mm["revealed"] == ["A1"]  # minimap = sparse overview + fog
    assert mm["occupied"]["A1"] == {"n": 1, "seen": True, "kinds": ["button"]}
    assert mm["occupied"]["C3"]["seen"] is False  # not visited yet -> fogged in the overview
    assert [e["name"] for e in obs["screen"]["focus"]["elements"]] == ["Login"]  # screen = local detail


# --- browser-backed: hover fires onmouseover WITHOUT a click ---
pytest.importorskip("playwright")
from python.scbe.ai_browser import AIBrowser  # noqa: E402

HOVER_FIX = (
    "data:text/html,<style>body{margin:0}</style>"
    "<button style='position:absolute;left:30px;top:30px' "
    "onmouseover=\"document.getElementById('o').innerText='HOVERED'\">btn</button>"
    "<p id=o style='position:absolute;left:30px;top:200px'>idle</p>"
)


def test_hover_focuses_without_click():
    try:
        br = AIBrowser(headless=True).__enter__()
    except Exception as exc:
        pytest.skip("no launchable browser: %s" % type(exc).__name__)
    try:
        page = br.open(HOVER_FIX)
        page.set_viewport_size({"width": 1280, "height": 800})
        mv = MapView(br.read(page))
        res = mv.hover(br, page)
        assert res["hovered"] == "r0"
        assert "HOVERED" in br.read(page)["text"]  # mouseover fired -> hover, not click
    finally:
        br.__exit__(None, None, None)
