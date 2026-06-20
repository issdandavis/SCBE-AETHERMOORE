"""offload_measure.model_proposer: the live-model adapter that maps a free-text reply to one legal
option. A review found two real defects this locks shut: (1) naive substring matching mapped a correct
'prime-power' reply to the shorter 'prime' (since 'prime' is a substring of 'prime-power'), fabricating
fake rescues; (2) a dead endpoint was returned as a sentinel string and silently counted as a model
ceiling the oracle then 'rescued'. The fix: exact-match-first, then longest-option-first substring; and
raise on a transport failure so it can never masquerade as a lift.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.helm import offload_measure as om  # noqa: E402

_LABELS = ["unit", "prime", "prime-power", "composite"]


def _proposer_with_reply(monkeypatch, reply):
    monkeypatch.setattr(om, "_chat", lambda *a, **k: reply)
    return om.model_proposer("base", "key", "model")


def test_prime_power_reply_is_not_swallowed_by_prime(monkeypatch):
    # the headline bug: 'prime' is a substring of 'prime-power'; a correct reply must map to prime-power
    p = _proposer_with_reply(monkeypatch, "prime-power")
    assert p("ctx", _LABELS) == "prime-power"


def test_prime_power_reply_with_extra_text_still_maps_correctly(monkeypatch):
    p = _proposer_with_reply(monkeypatch, "The answer is prime-power (2^3).")
    assert p("ctx", _LABELS) == "prime-power"


def test_composite_reply_mentioning_prime_maps_to_composite(monkeypatch):
    # 'composite, not prime' must map to composite, not get captured by the substring 'prime'
    p = _proposer_with_reply(monkeypatch, "composite, not prime")
    assert p("ctx", _LABELS) == "composite"


def test_exact_label_reply_maps_to_that_label(monkeypatch):
    p = _proposer_with_reply(monkeypatch, "prime")
    assert p("ctx", _LABELS) == "prime"


def test_off_menu_reply_is_returned_as_a_misstep(monkeypatch):
    # a reply matching no option is returned verbatim so the harness records a legitimate misstep
    p = _proposer_with_reply(monkeypatch, "banana")
    assert p("ctx", _LABELS) == "banana"


def test_endpoint_failure_raises_not_returns(monkeypatch):
    # a transport failure must fail loud, never be counted as a model ceiling the oracle rescues
    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(om, "_chat", boom)
    p = om.model_proposer("base", "key", "model")
    with pytest.raises(ConnectionError):
        p("ctx", _LABELS)
