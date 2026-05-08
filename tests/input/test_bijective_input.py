"""Tests for bijective input telemetry (mouse + key event transport).

The transport rides the Sacred Tongues tokenizer, which is mechanically
bijective per its construction. These tests cover the layer above that:
that struct-packed mouse/key frames round-trip bit-perfect, that the
self-describing kind byte routes correctly across heterogeneous traces,
and that `verify_trace` / `replay_trace` behave on the hot path.
"""

from __future__ import annotations

import math
from typing import List

import pytest

from src.input import (
    KeyAction,
    KeyEvent,
    MouseAction,
    MouseButton,
    MouseEvent,
    cartesian_to_polar,
    decode_key_event,
    decode_mouse_event,
    decode_trace,
    encode_key_event,
    encode_mouse_event,
    encode_trace,
    polar_to_cartesian,
    replay_trace,
    verify_trace,
)
from src.input.bijective_input import (
    KEY_FRAME_SIZE,
    KIND_KEY,
    KIND_MOUSE,
    MOD_ALT,
    MOD_CTRL,
    MOD_META,
    MOD_SHIFT,
    MOUSE_FRAME_SIZE,
)

# ---------------------------------------------------------------------------
#  Mouse event round-trips
# ---------------------------------------------------------------------------


def test_mouse_move_round_trip() -> None:
    ev = MouseEvent(timestamp_us=1_700_000_000_000_000, x=512, y=384)
    tokens = encode_mouse_event(ev)
    assert (
        isinstance(tokens, list) and tokens
    ), "encoder must return non-empty token list"
    decoded = decode_mouse_event(tokens)
    assert decoded == ev


def test_mouse_click_round_trip_all_buttons() -> None:
    """Every button enum value must survive a click round-trip."""
    for btn in MouseButton:
        ev = MouseEvent(
            timestamp_us=42,
            x=100,
            y=200,
            button=btn,
            action=MouseAction.DOWN,
        )
        decoded = decode_mouse_event(encode_mouse_event(ev))
        assert decoded == ev, f"round-trip failed for button {btn}"


def test_mouse_scroll_with_negative_delta() -> None:
    """Negative scroll deltas (wheel-up on most systems) must survive
    the signed↔unsigned wire conversion."""
    ev = MouseEvent(
        timestamp_us=99,
        x=0,
        y=0,
        action=MouseAction.SCROLL,
        scroll_delta=-3,
    )
    decoded = decode_mouse_event(encode_mouse_event(ev))
    assert decoded == ev
    assert decoded.scroll_delta == -3


def test_mouse_negative_coordinates_survive() -> None:
    ev = MouseEvent(timestamp_us=1, x=-1024, y=-2048)
    decoded = decode_mouse_event(encode_mouse_event(ev))
    assert decoded.x == -1024
    assert decoded.y == -2048


def test_mouse_extreme_int32_values() -> None:
    ev = MouseEvent(
        timestamp_us=2**63,
        x=2**31 - 1,
        y=-(2**31),
        scroll_delta=-(2**31),
    )
    decoded = decode_mouse_event(encode_mouse_event(ev))
    assert decoded == ev


def test_mouse_validation_rejects_oversize_coords() -> None:
    with pytest.raises(ValueError, match="x out of int32 range"):
        MouseEvent(timestamp_us=0, x=2**31, y=0)
    with pytest.raises(ValueError, match="y out of int32 range"):
        MouseEvent(timestamp_us=0, x=0, y=-(2**31) - 1)


def test_mouse_validation_rejects_oversize_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp_us"):
        MouseEvent(timestamp_us=-1, x=0, y=0)


# ---------------------------------------------------------------------------
#  Key event round-trips
# ---------------------------------------------------------------------------


def test_key_event_round_trip_minimal() -> None:
    ev = KeyEvent(timestamp_us=1, keycode=0x41)  # 'A'
    decoded = decode_key_event(encode_key_event(ev))
    assert decoded == ev


def test_key_event_with_full_modifier_stack() -> None:
    """Ctrl+Shift+Alt+Meta together must round-trip."""
    mods = MOD_SHIFT | MOD_CTRL | MOD_ALT | MOD_META
    ev = KeyEvent(timestamp_us=7, keycode=0x53, modifiers=mods, action=KeyAction.DOWN)
    decoded = decode_key_event(encode_key_event(ev))
    assert decoded.modifiers == mods
    assert decoded == ev


def test_key_event_action_repeat() -> None:
    ev = KeyEvent(timestamp_us=10, keycode=0x20, action=KeyAction.REPEAT)
    decoded = decode_key_event(encode_key_event(ev))
    assert decoded.action == KeyAction.REPEAT


def test_key_event_max_keycode() -> None:
    ev = KeyEvent(timestamp_us=0, keycode=2**16 - 1)
    decoded = decode_key_event(encode_key_event(ev))
    assert decoded.keycode == 2**16 - 1


def test_key_event_validation_rejects_oversize_keycode() -> None:
    with pytest.raises(ValueError, match="keycode"):
        KeyEvent(timestamp_us=0, keycode=2**16)


def test_key_event_validation_rejects_oversize_modifiers() -> None:
    with pytest.raises(ValueError, match="modifiers"):
        KeyEvent(timestamp_us=0, keycode=0, modifiers=2**8)


# ---------------------------------------------------------------------------
#  Cross-channel: decoder rejects wrong kind byte
# ---------------------------------------------------------------------------


def test_decode_mouse_rejects_key_payload() -> None:
    ev = KeyEvent(timestamp_us=1, keycode=0x41)
    tokens = encode_key_event(ev)
    # Decode with the *key* tongue but as a mouse — kind byte must mismatch.
    with pytest.raises(ValueError, match="not a mouse frame"):
        decode_mouse_event(tokens, tongue="av")


def test_decode_key_rejects_mouse_payload() -> None:
    ev = MouseEvent(timestamp_us=1, x=0, y=0)
    tokens = encode_mouse_event(ev)
    with pytest.raises(ValueError, match="not a key frame"):
        decode_key_event(tokens, tongue="ca")


# ---------------------------------------------------------------------------
#  Frame size invariants (catches schema drift)
# ---------------------------------------------------------------------------


def test_mouse_frame_size_is_25_bytes() -> None:
    """If this changes you've reshaped the wire format — bump a version
    constant explicitly."""
    from src.input.bijective_input import _pack_mouse  # noqa: PLC0415

    raw = _pack_mouse(MouseEvent(timestamp_us=0, x=0, y=0))
    assert len(raw) == MOUSE_FRAME_SIZE == 25


def test_key_frame_size_is_17_bytes() -> None:
    from src.input.bijective_input import _pack_key  # noqa: PLC0415

    raw = _pack_key(KeyEvent(timestamp_us=0, keycode=0))
    assert len(raw) == KEY_FRAME_SIZE == 17


def test_kind_marker_bytes() -> None:
    from src.input.bijective_input import _pack_key, _pack_mouse  # noqa: PLC0415

    assert _pack_mouse(MouseEvent(timestamp_us=0, x=0, y=0))[0] == KIND_MOUSE == 0x01
    assert _pack_key(KeyEvent(timestamp_us=0, keycode=0))[0] == KIND_KEY == 0x02


# ---------------------------------------------------------------------------
#  Polar / cartesian helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "x, y",
    [
        (1.0, 0.0),
        (0.0, 1.0),
        (3.0, 4.0),
        (-7.5, 12.25),
        (1e-3, 1e-3),
        (-100.0, -100.0),
    ],
)
def test_cartesian_polar_round_trip(x: float, y: float) -> None:
    r, theta = cartesian_to_polar(x, y)
    x2, y2 = polar_to_cartesian(r, theta)
    assert math.isclose(x2, x, abs_tol=1e-9)
    assert math.isclose(y2, y, abs_tol=1e-9)


def test_polar_radius_matches_hypot() -> None:
    r, _ = cartesian_to_polar(3.0, 4.0)
    assert math.isclose(r, 5.0)


def test_polar_zero_origin_returns_zero_radius() -> None:
    r, _ = cartesian_to_polar(0.0, 0.0)
    assert r == 0.0


# ---------------------------------------------------------------------------
#  Heterogeneous trace
# ---------------------------------------------------------------------------


def _sample_trace() -> List[object]:
    return [
        MouseEvent(timestamp_us=10, x=100, y=100, action=MouseAction.MOVE),
        KeyEvent(
            timestamp_us=20, keycode=0x41, modifiers=MOD_SHIFT, action=KeyAction.DOWN
        ),
        MouseEvent(
            timestamp_us=30,
            x=200,
            y=150,
            button=MouseButton.LEFT,
            action=MouseAction.DOWN,
        ),
        KeyEvent(timestamp_us=40, keycode=0x41, action=KeyAction.UP),
        MouseEvent(
            timestamp_us=50,
            x=200,
            y=150,
            action=MouseAction.SCROLL,
            scroll_delta=120,
        ),
    ]


def test_encode_decode_trace_round_trip() -> None:
    events = _sample_trace()
    packets = encode_trace(events)
    assert len(packets) == len(events)
    # Each pair is (tongue, tokens).
    for tongue, tokens in packets:
        assert tongue in ("ca", "av")
        assert isinstance(tokens, list) and tokens

    decoded = decode_trace(packets)
    assert decoded == events


def test_encode_trace_routes_channels_correctly() -> None:
    """Mouse → CA, Key → AV by default."""
    events = _sample_trace()
    packets = encode_trace(events)
    expected = ["ca", "av", "ca", "av", "ca"]
    assert [t for t, _ in packets] == expected


def test_encode_trace_custom_tongue_routing() -> None:
    """The caller can override channel routing."""
    events = [
        MouseEvent(timestamp_us=1, x=0, y=0),
        KeyEvent(timestamp_us=2, keycode=0x41),
    ]
    packets = encode_trace(events, mouse_tongue="ru", key_tongue="ko")
    assert packets[0][0] == "ru"
    assert packets[1][0] == "ko"
    # Decode with the SAME custom tongues - matching tongue is the contract.
    assert decode_trace(packets) == events


def test_encode_trace_rejects_unknown_event_type() -> None:
    with pytest.raises(TypeError, match="unknown event type"):
        encode_trace([object()])


# ---------------------------------------------------------------------------
#  verify_trace
# ---------------------------------------------------------------------------


def test_verify_trace_ok_for_round_tripped_packets() -> None:
    packets = encode_trace(_sample_trace())
    report = verify_trace(packets)
    assert report["ok"] is True
    assert report["count"] == 5
    assert report["kinds"] == [KIND_MOUSE, KIND_KEY, KIND_MOUSE, KIND_KEY, KIND_MOUSE]
    # 3 mouse * 25B + 2 key * 17B = 75 + 34 = 109
    assert report["total_bytes"] == 3 * MOUSE_FRAME_SIZE + 2 * KEY_FRAME_SIZE
    assert report["failure"] is None


def test_verify_trace_with_expected_count() -> None:
    packets = encode_trace(_sample_trace())
    bad = verify_trace(packets, expected_count=999)
    assert bad["ok"] is False
    assert "expected_count=999" in bad["failure"]


def test_verify_trace_with_expected_kinds() -> None:
    packets = encode_trace(_sample_trace())
    good = verify_trace(
        packets, expected_kinds=[KIND_MOUSE, KIND_KEY, KIND_MOUSE, KIND_KEY, KIND_MOUSE]
    )
    assert good["ok"] is True

    wrong = verify_trace(packets, expected_kinds=[KIND_KEY] * 5)
    assert wrong["ok"] is False
    assert "expected_kinds" in wrong["failure"]


def test_verify_trace_unknown_tongue_marks_failure() -> None:
    packets = [("zz_not_a_tongue", ["x"])]
    report = verify_trace(packets)
    assert report["ok"] is False
    assert "unknown tongue" in report["failure"]


# ---------------------------------------------------------------------------
#  replay_trace
# ---------------------------------------------------------------------------


def test_replay_trace_returns_decoded_events_no_sink() -> None:
    events = _sample_trace()
    packets = encode_trace(events)
    assert replay_trace(packets) == events


def test_replay_trace_invokes_sink_in_order() -> None:
    events = _sample_trace()
    packets = encode_trace(events)
    received: List[object] = []

    def sink(ev: object) -> None:
        received.append(ev)

    out = replay_trace(packets, sink=sink)
    assert out == events
    assert received == events


def test_replay_trace_sink_is_optional() -> None:
    """Passing sink=None must not raise."""
    packets = encode_trace([MouseEvent(timestamp_us=1, x=0, y=0)])
    replay_trace(packets, sink=None)


# ---------------------------------------------------------------------------
#  Bijection sanity: byte-identical token stream for byte-identical events
# ---------------------------------------------------------------------------


def test_same_event_yields_same_tokens() -> None:
    """Determinism is the whole point — same event, byte-equal tokens."""
    ev = MouseEvent(
        timestamp_us=12345, x=10, y=20, action=MouseAction.DOWN, button=MouseButton.LEFT
    )
    a = encode_mouse_event(ev)
    b = encode_mouse_event(ev)
    assert a == b


def test_distinct_events_yield_distinct_tokens() -> None:
    a = encode_mouse_event(MouseEvent(timestamp_us=1, x=0, y=0))
    b = encode_mouse_event(MouseEvent(timestamp_us=2, x=0, y=0))
    assert a != b
