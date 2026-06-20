"""Tests for the mechanical pianist: physical constraints and operators."""

from __future__ import annotations

import io

import pytest

from pianist import (
    Action,
    CloudOperator,
    HumanOperator,
    MarkovOperator,
    PhysicalError,
    Pianist,
)
from pianist.__main__ import run

# ---------------------------------------------------------------------------
# Physical constraints
# ---------------------------------------------------------------------------


def test_press_and_release_round_trip():
    p = Pianist()
    p.execute(Action(kind="press", finger="R3", key=60, velocity=80))
    assert p.held_keys() == [60]
    p.execute(Action(kind="release", finger="R3"))
    assert p.held_keys() == []


def test_finger_cannot_press_twice():
    p = Pianist()
    p.execute(Action(kind="press", finger="R3", key=60))
    with pytest.raises(PhysicalError, match="already pressing"):
        p.execute(Action(kind="press", finger="R3", key=64))


def test_release_unpressed_finger_rejected():
    p = Pianist()
    with pytest.raises(PhysicalError, match="not pressing"):
        p.execute(Action(kind="release", finger="L1"))


def test_eleventh_finger_rejected():
    p = Pianist()
    for i, finger in enumerate(("L1", "L2", "L3", "L4", "L5", "R1", "R2", "R3", "R4", "R5")):
        p.execute(Action(kind="press", finger=finger, key=40 + i))
    with pytest.raises(PhysicalError, match="unknown finger"):
        p.execute(Action(kind="press", finger="X1", key=80))


def test_hand_span_rejected_when_too_wide():
    p = Pianist()
    p.execute(Action(kind="press", finger="R1", key=60))
    with pytest.raises(PhysicalError, match="hand span"):
        p.execute(Action(kind="press", finger="R5", key=80))  # span 20 > 14


def test_hand_span_allows_octave_plus():
    p = Pianist()
    p.execute(Action(kind="press", finger="R1", key=60))
    # Span 14 (C4 to D5) is the documented allowed maximum.
    p.execute(Action(kind="press", finger="R5", key=74))
    assert p.held_keys() == [60, 74]


def test_finger_reuse_requires_rest():
    p = Pianist()
    p.execute(Action(kind="press", finger="R3", key=60))
    p.execute(Action(kind="release", finger="R3"))
    # Same tick: must reject reuse.
    with pytest.raises(PhysicalError, match="rest before reuse"):
        p.execute(Action(kind="press", finger="R3", key=62))


def test_finger_reuse_after_wait_succeeds():
    p = Pianist()
    p.execute(Action(kind="press", finger="R3", key=60))
    p.execute(Action(kind="release", finger="R3"))
    p.execute(Action(kind="wait", duration_ms=20))
    p.execute(Action(kind="press", finger="R3", key=62))
    assert p.held_keys() == [62]


def test_key_outside_range_rejected():
    p = Pianist()
    with pytest.raises(PhysicalError, match="outside piano range"):
        p.execute(Action(kind="press", finger="R3", key=200))


def test_velocity_bounds_enforced():
    p = Pianist()
    with pytest.raises(PhysicalError, match="velocity"):
        p.execute(Action(kind="press", finger="R3", key=60, velocity=0))


def test_pedal_value_bounds_enforced():
    p = Pianist()
    with pytest.raises(PhysicalError, match="pedal value"):
        p.execute(Action(kind="pedal", pedal="sustain", pedal_value=2.0))


def test_wait_advances_clock():
    p = Pianist()
    p.execute(Action(kind="wait", duration_ms=500))
    assert p.now_ms == 500


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------


def test_human_operator_parses_press_release_pedal_wait():
    commands = io.StringIO("press R3 60 90\nwait 100\nrelease R3\npedal sustain 1.0\nstop\n")
    op = HumanOperator(lines=iter(commands))
    p = Pianist()
    run(op, p, out_stream=None)
    # Expect: press, wait, release, pedal -> 4 events recorded (stop ends loop).
    kinds = [a.kind for _, a in p.events]
    assert kinds == ["press", "wait", "release", "pedal"]
    assert p.now_ms == 100
    assert p.state().pedals["sustain"] == 1.0


def test_human_operator_skips_blank_and_comment_lines():
    commands = io.StringIO("\n# this is a comment\npress L3 40\nstop\n")
    op = HumanOperator(lines=iter(commands))
    p = Pianist()
    run(op, p, out_stream=None)
    assert [a.kind for _, a in p.events] == ["press"]


def test_markov_operator_plays_within_constraints():
    op = MarkovOperator(seed=42, bars=2, bar_ms=800)
    p = Pianist()
    run(op, p, out_stream=None)
    assert p.events, "markov operator should produce events"
    assert p.now_ms > 0
    # By the end of a bar all fingers should be released.
    assert p.held_keys() == []


def test_markov_operator_deterministic_with_seed():
    p1 = Pianist()
    p2 = Pianist()
    run(MarkovOperator(seed=7, bars=1), p1, out_stream=None)
    run(MarkovOperator(seed=7, bars=1), p2, out_stream=None)
    assert [a.kind for _, a in p1.events] == [a.kind for _, a in p2.events]
    assert p1.now_ms == p2.now_ms


def test_cloud_operator_falls_back_to_markov_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    op = CloudOperator()
    p = Pianist()
    run(op, p, out_stream=None)
    assert p.events, "cloud operator should fall back to Markov when no key is set"


def test_cloud_operator_uses_custom_responder():
    replies = iter(["press R3 60 80", "wait 50", "release R3", "stop"])

    def responder(prompt, state):
        return next(replies, None)

    op = CloudOperator(responder=responder)
    p = Pianist()
    run(op, p, out_stream=None)
    assert [a.kind for _, a in p.events] == ["press", "wait", "release"]
