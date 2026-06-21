"""Tests for BrowserController -- the fixed-geometry steering surface over ai_browser.

Locks by EXECUTION (local data: fixture, no network): a fixed button vocabulary drives any page via a
cursor; typing only lands on editable elements (legal-moves-only); every geometry skin (gamepad/cube/
sphere/wheel) maps all nine buttons; the per-step frame has a fixed shape. Skips if no launchable Chrome.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright")

from python.scbe.ai_browser import AIBrowser  # noqa: E402
from python.scbe.browser_controller import BUTTONS, LAYOUTS, BrowserController  # noqa: E402

FIXTURE = (
    "data:text/html,<h1>Demo</h1>"
    "<button onclick=\"document.getElementById('o').innerText='CLICKED'\">Press me</button>"
    "<input placeholder='your name'><a href='https://example.org'>link</a><p id=o>idle</p>"
)


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


def test_every_layout_maps_all_buttons():
    for name, mapping in LAYOUTS.items():
        assert set(mapping) == set(BUTTONS), "layout %s missing buttons" % name
        assert len(set(mapping.values())) == len(BUTTONS), "layout %s has duplicate skins" % name


def test_cursor_steers_and_actions_change_state(br):
    ctl = BrowserController(br, br.open(FIXTURE), layout="cube")
    assert ctl.frame()["n_elements"] == 3
    assert ctl.frame()["focused"].startswith("r0")  # button first
    ctl.press("next")
    assert ctl.frame()["focused_editable"] is True  # the input
    ctl.press("type", "Issac")
    ctl.press("prev")
    ctl.press("activate")
    assert ctl.page.eval_on_selector("[data-aibref='r1']", "e=>e.value") == "Issac"
    assert "CLICKED" in br.read(ctl.page)["text"]


def test_type_on_non_editable_is_rejected(br):
    ctl = BrowserController(br, br.open(FIXTURE), layout="gamepad")
    ctl.cursor = 0  # the button (not editable)
    res = ctl.press("type", "xx")
    assert res.get("rejected") == "focused element is not editable"


def test_frame_shape_is_fixed_across_layouts(br):
    keys = None
    for layout in LAYOUTS:
        ctl = BrowserController(br, br.open(FIXTURE), layout=layout)
        fr = ctl.frame()
        assert set(fr["buttons"]) == set(BUTTONS)
        if keys is None:
            keys = set(fr)
        assert set(fr) == keys  # identical frame shape no matter the geometry


def test_invalid_layout_and_button_rejected(br):
    with pytest.raises(ValueError):
        BrowserController(br, br.open(FIXTURE), layout="hyperbolic-banana")
    ctl = BrowserController(br, br.open(FIXTURE))
    with pytest.raises(ValueError):
        ctl.press("teleport")
