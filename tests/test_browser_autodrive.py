"""Tests for browser_autodrive -- the autonomous on_step macro->micro loop.

Deterministic, against a local fixture (no network): intents resolve to elements by name and act; a
nonexistent target FAILS honestly (no faked success); an assertion reflects the real page. Skips if no
launchable Chrome.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright")

from python.scbe.ai_browser import AIBrowser  # noqa: E402
from python.scbe.browser_autodrive import AutoDriver, assert_title, click, fill  # noqa: E402

FORM = (
    "data:text/html,<title>drivetest</title><input placeholder='search box'>"
    "<button onclick=\"document.getElementById('o').innerText='WENT'\">go</button><p id=o>idle</p>"
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


def test_intents_resolve_by_name_and_act(br):
    drv = AutoDriver(br, br.open(FORM))
    res = drv.run([fill("search", "hello"), click("go"), assert_title("drivetest")])
    assert res["success"] is True
    assert [s["status"] for s in res["trace"]] == ["ok", "ok", "ok"]
    assert "WENT" in br.read(drv.page)["text"]  # the click really fired


def test_nonexistent_target_fails_honestly(br):
    drv = AutoDriver(br, br.open(FORM))
    res = drv.run([click("no-such-control-zzz")])
    assert res["success"] is False
    assert res["trace"][0]["status"] == "fail"
    assert "no element matching" in res["trace"][0]["detail"]


def test_assertion_reflects_the_real_page(br):
    drv = AutoDriver(br, br.open(FORM))
    res = drv.run([assert_title("this-is-not-the-title")])
    assert res["success"] is False  # the page title is 'drivetest', so this assertion must fail


def test_stops_at_first_failure(br):
    drv = AutoDriver(br, br.open(FORM))
    # second intent fails -> third must never run
    res = drv.run([fill("search", "x"), click("missing-zzz"), click("go")])
    assert res["success"] is False
    assert len(res["trace"]) == 2  # stopped after the failing step
