"""Regression tests for the URL-attack hardening + crash-guard in the SCBE layer.

These assert what is ACTUALLY true (verified), not aspirational -- e.g. IP-literal
hosts reach QUARANTINE (not necessarily DENY, which the risk-blend caps).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import scbe_security_layer as S  # noqa: E402

SIG = {"claimed_type": "text/html", "actual_type": "text/html"}


def _decision(url):
    return str(S.SCBESecurityLayer().classify_request(url, content_signals=SIG)).split(".")[-1]


def test_malformed_port_does_not_crash():
    # regression: parsed.port raised ValueError on a bad port and crashed classify_request
    for url in ("http://shop.example:notaport/", "https://h.example:99999/x"):
        assert _decision(url) in {"ALLOW", "QUARANTINE", "DENY"}  # must not raise


def test_ip_literal_encodings_flagged():
    # hex / IPv6 / decimal-int IP hosts (SSRF/loopback) must not be ALLOW
    for url in ("http://0x7f000001/", "http://[::1]/", "http://2130706433/"):
        assert _decision(url) != "ALLOW", url


def test_phishing_name_flagged():
    assert _decision("http://login-verify-account.tk") != "ALLOW"


def test_legit_sites_still_allowed():
    # no false positives on these mainstream sites
    for url in ("https://google.com", "https://github.com", "https://apple.com", "https://amazon.com"):
        assert _decision(url) == "ALLOW", url
