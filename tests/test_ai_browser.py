"""Tests for the abstraction-based AI browser core (ai_browser).

Locks the three load-bearing pieces by EXECUTION against a local data: fixture (no network): the data-first
feed, the bounded move control surface (steer by ref, never a selector), and the ephemeral no-over-cache
buffer. Skips cleanly if Playwright or a launchable Chrome is absent (so CI without browsers doesn't hang).
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("playwright")

from python.scbe.ai_browser import AIBrowser, Move  # noqa: E402

FIXTURE = (
    "data:text/html,"
    "<h1>Demo Site</h1>"
    "<button onclick=\"document.getElementById('out').innerText='CLICKED'\">Press me</button>"
    "<input placeholder='your name'>"
    "<a href='https://example.org'>docs link</a>"
    "<p id=out>idle</p>"
)


@pytest.fixture(scope="module")
def browser():
    try:
        br = AIBrowser(headless=True).__enter__()
    except Exception as exc:  # no launchable Chrome in this env -> skip, don't fail
        pytest.skip("no launchable browser: %s" % type(exc).__name__)
    try:
        yield br
    finally:
        br.__exit__(None, None, None)


def test_feed_is_structured_and_bounded(browser):
    page = browser.open(FIXTURE)
    feed = browser.read(page)
    assert feed["url"].startswith("data:text/html")
    refs = {e["ref"] for e in feed["elements"]}
    assert len(refs) == len(feed["elements"]) == 3  # button, input, link -- a small bounded surface
    by_tag = {e["tag"] for e in feed["elements"]}
    assert {"button", "input", "a"} <= by_tag
    assert next(e for e in feed["elements"] if e["tag"] == "input")["editable"] is True


def test_control_surface_is_legal_moves_only(browser):
    page = browser.open(FIXTURE)
    moves = browser.moves(browser.read(page))
    kinds = [m.kind for m in moves]
    assert "read" in kinds and "scroll" in kinds and "back" in kinds
    assert any(m.kind == "click" for m in moves) and any(m.kind == "type" for m in moves)
    # every element-bound move carries a ref (the model steers by ref, never a CSS selector)
    assert all(m.ref for m in moves if m.kind in ("click", "type"))


def test_steer_by_ref_changes_page_state(browser):
    page = browser.open(FIXTURE)
    moves = browser.moves(browser.read(page))
    typ = next(m for m in moves if m.kind == "type")
    typ.value = "Issac"
    browser.act(page, typ)
    browser.act(page, next(m for m in moves if m.kind == "click" and "Press" in m.label))
    assert page.eval_on_selector("[data-aibref='%s']" % typ.ref, "e=>e.value") == "Issac"
    assert "CLICKED" in browser.read(page)["text"]


def test_ephemeral_feed_consume_deletes_local_copy(browser):
    page = browser.open(FIXTURE)
    ef = browser.park(browser.read(page))
    assert ef.cached and os.path.exists(ef.path)
    data = ef.consume()
    assert data["url"].startswith("data:text/html")
    assert not os.path.exists(ef.path)  # ingested -> deleted, no over-cache
    with pytest.raises(RuntimeError):
        ef.consume()  # exactly once


def test_unknown_move_rejected(browser):
    page = browser.open(FIXTURE)
    with pytest.raises(ValueError):
        browser.act(page, Move("teleport"))


def test_submit_acts_on_focus_survives_rerender(browser):
    # submit presses Enter on whatever is FOCUSED -- no ref, so a re-render that detaches the input can't
    # break it (the real-world failure Wikipedia exposed)
    page = browser.open(
        "data:text/html,<input onkeydown=\"if(event.key==='Enter')"
        "document.getElementById('o').innerText='SUBMITTED'\"><p id=o>idle</p>"
    )
    inp = next(e for e in browser.read(page)["elements"] if e["editable"])
    browser.act(page, Move("type", ref=inp["ref"], value="x"))  # type focuses the input
    browser.act(page, Move("submit"))  # Enter on focus
    assert "SUBMITTED" in browser.read(page)["text"]


def test_hover_move_fires_mouseover_without_click(browser):
    page = browser.open(
        "data:text/html,<button onmouseover=\"document.getElementById('o').innerText='HOVERED'\">b</button>"
        "<p id=o>idle</p>"
    )
    btn = next(e for e in browser.read(page)["elements"] if e["tag"] == "button")
    browser.act(page, Move("hover", ref=btn["ref"]))
    assert "HOVERED" in browser.read(page)["text"]
