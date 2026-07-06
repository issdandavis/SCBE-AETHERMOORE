"""The router's SCBE second gate must fail CLOSED, not fail open."""

import pytest

from src.aetherbrowser.hyperlane_py import HyperLanePy, Zone


def test_bad_port_fails_closed():
    hl = HyperLanePy()
    if hl._scbe is None:
        pytest.skip("SCBE layer not importable in this environment")
    hl.add_domain("login-verify.tk", Zone.GREEN)
    clean = hl.evaluate("https://login-verify.tk/", action="read", agent_id="KO")
    bad = hl.evaluate("https://login-verify.tk:99999/", action="read", agent_id="KO")  # bad port used to fail-OPEN
    assert clean.decision.value != "ALLOW"  # phishing name already escalates
    assert bad.decision.value != "ALLOW"  # and a crashing port must not downgrade it


def test_clean_green_still_allows():
    hl = HyperLanePy()
    hl.add_domain("github.com", Zone.GREEN)
    r = hl.evaluate("https://github.com/", action="read", agent_id="KO")
    assert r.decision.value == "ALLOW"
