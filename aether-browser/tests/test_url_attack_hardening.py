# -*- coding: utf-8 -*-
"""Regression tests for the decisive URL-threat model + false-positive fixes.

The redesign (analyze_url_threats + veto) makes impersonation reach DENY and stops
penalising legitimate internationalized / lookalike-but-real domains. These assert
the ACTUAL verified behavior.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import scbe_security_layer as S  # noqa: E402

SIG = {"claimed_type": "text/html", "actual_type": "text/html"}


def _d(url):
    return str(S.SCBESecurityLayer().classify_request(url, content_signals=SIG)).split(".")[-1]


def test_impersonation_is_decisive_deny():
    # brand impersonation must reach DENY (the old blend could only ever QUARANTINE)
    for url in (
        "http://login-verify-account.tk",
        "https://goog1e.com",
        "https://paypa1.com",
        "https://аpple.com",  # cyrillic 'a'
        "https://xn--pypal-4ve.com/",
    ):
        assert _d(url) == "DENY", url


def test_structural_attacks_at_least_quarantine():
    # IP-literals (any encoding), embedded creds, malformed port -> not ALLOW, no crash
    for url in (
        "http://0x7f000001/",
        "http://[::1]/",
        "http://2130706433/",
        "http://admin:pass@evil.com/",
        "https://user:pass@x.com:99999/",
    ):
        assert _d(url) in {"QUARANTINE", "DENY"}, url


def test_javascript_uri_denied():
    assert _d("javascript:fetch('//evil')") == "DENY"


def test_malformed_port_does_not_crash():
    for url in ("http://shop.example:notaport/", "https://h.example:99999/x"):
        assert _d(url) in {"ALLOW", "QUARANTINE", "DENY"}  # must not raise


def test_legit_mainstream_sites_allowed():
    for url in ("https://google.com", "https://github.com", "https://apple.com", "https://amazon.com"):
        assert _d(url) == "ALLOW", url


def test_legit_idn_and_lookalike_companies_allowed():
    # the review's confirmed false positives -- all real, legitimate sites
    for url in (
        "https://xn--bcher-kva.de/",  # bücher.de (real book retailer)
        "https://amazone.de/",  # real agricultural-machinery maker
        "https://apples.com/",
        "https://youtuber.com/",
        "https://account.mail.ru/",  # legit Russian auth portal
        "https://login.yandex.ru/",
        "https://paypal.co.uk/",  # multi-part TLD, the real PayPal UK
        "http://myapp.localhost:3000/",  # local dev server
    ):
        assert _d(url) == "ALLOW", url
