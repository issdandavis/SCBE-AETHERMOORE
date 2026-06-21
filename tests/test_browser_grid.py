"""Tests for browser_grid -- the per-site coordinate-grid viewer.

cell_label math is pure (no browser). The grid mapping + overlay render are locked by EXECUTION against a
POSITIONED data: fixture (fixed viewport so cells are deterministic): elements land in the expected cells,
off-viewport elements map to 'off', the gridded screenshot renders and the overlay is removed after.
"""

from __future__ import annotations

import os

import pytest

from python.scbe.browser_grid import cell_label, grid_map

pytest.importorskip("playwright")

from python.scbe.ai_browser import AIBrowser  # noqa: E402
from python.scbe.browser_grid import render_grid  # noqa: E402

POSITIONED = (
    "data:text/html,<style>body{margin:0}</style>"
    "<button style='position:absolute;left:40px;top:30px'>Login</button>"
    "<input style='position:absolute;left:600px;top:380px' placeholder='search'>"
    "<a style='position:absolute;left:1120px;top:720px' href='https://x.org'>help</a>"
)
OFFSCREEN = (
    "data:text/html,<style>body{margin:0}</style>"
    "<button style='position:absolute;left:40px;top:5000px'>way down</button>"
)


def test_cell_label_is_spreadsheet_coordinate():
    assert cell_label(0, 0) == "A1"
    assert cell_label(2, 3) == "C4"
    assert cell_label(7, 7) == "H8"
    assert cell_label(25, 0) == "Z1"
    assert cell_label(26, 0) == "AA1"  # wraps past Z like spreadsheet columns
    assert cell_label(27, 9) == "AB10"


def test_exact_right_edge_pixel_is_off():
    # viewport is [0, vw) x [0, vh): a center exactly at cx==vw is OFF-screen, not the last column
    edge = {"viewport": {"w": 1000, "h": 800}, "elements": [{"ref": "r0", "x": 1000, "y": 400, "w": 0, "h": 0}]}
    assert grid_map(edge)["by_ref"]["r0"] == "off"
    inside = {"viewport": {"w": 1000, "h": 800}, "elements": [{"ref": "r0", "x": 999, "y": 400, "w": 0, "h": 0}]}
    assert grid_map(inside)["by_ref"]["r0"] != "off"  # one pixel inside is on-grid


def test_grid_map_pure_on_synthetic_feed():
    feed = {
        "viewport": {"w": 900, "h": 900},
        "elements": [
            {"ref": "r0", "x": 0, "y": 0, "w": 10, "h": 10, "name": "tl"},  # top-left -> A1
            {"ref": "r1", "x": 890, "y": 890, "w": 5, "h": 5, "name": "br"},  # bottom-right -> last cell
        ],
    }
    g = grid_map(feed, cols=9, rows=9)
    assert g["by_ref"]["r0"] == "A1"
    assert g["by_ref"]["r1"] == "I9"  # 9th col (I), 9th row
    assert g["by_cell"]["A1"] == ["r0"] and g["legend"]["A1"] == ["tl"]


@pytest.fixture(scope="module")
def br():
    try:
        b = AIBrowser(headless=True).__enter__()
    except Exception as exc:
        pytest.skip("no launchable browser: %s" % type(exc).__name__)
    try:
        yield b
    finally:
        b.__exit__(None, None, None)


def test_positioned_elements_land_in_distinct_cells(br):
    page = br.open(POSITIONED)
    page.set_viewport_size({"width": 1280, "height": 800})
    g = grid_map(br.read(page), cols=9, rows=9)
    assert g["by_ref"]["r0"] == "A1"  # top-left Login
    cells = [c for c in g["by_ref"].values() if c != "off"]
    assert len(cells) == 3 and len(set(cells)) == 3  # all on-grid, all distinct


def test_offscreen_element_maps_off(br):
    page = br.open(OFFSCREEN)
    page.set_viewport_size({"width": 1280, "height": 800})
    g = grid_map(br.read(page))
    assert g["by_ref"]["r0"] == "off"


def test_render_grid_makes_screenshot_and_removes_overlay(br):
    page = br.open(POSITIONED)
    page.set_viewport_size({"width": 1280, "height": 800})
    out = os.path.join(os.environ.get("TEMP", "/tmp"), "aib_grid_test.png")
    res = render_grid(br, page, out)
    assert os.path.exists(res["path"]) and os.path.getsize(res["path"]) > 0
    assert res["occupied_cells"] and "A1" in res["occupied_cells"]
    assert page.query_selector("#aibgrid") is None  # overlay cleaned up after the shot
