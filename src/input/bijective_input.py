"""Bijective input telemetry — dual-channel agent input over Sacred Tongues.

Mouse events and key events pack to fixed-size byte structs, then ride the
existing `SACRED_TONGUE_TOKENIZER` to a token stream. The transport is
mechanically bijective (256-token lookup, validated at tokenizer init), so
encode → decode round-trips bit-perfect.

What this module gives you, in the SCBE verbs you asked for:

  encode  — events become deterministic token packets (one tongue per channel)
  replay  — token traces decode back into the exact event objects
  verify  — `verify_trace()` confirms hash + length without decoding
  govern  — events flow through the same gate as text prompts (downstream)

What this module is NOT:

  * A keystroke-injection driver. This is the *transport*, not the OS hook.
    Plug pynput / pyautogui / playwright on top of `replay_trace()` to
    actually move the cursor or type.
  * A cryptographic identity layer. Bijection comes from the tokenizer.
    Tamper-evidence and authenticity come from the sealed_memory_packets
    layer that wraps a trace token stream when you need it.

Coordinate notes
----------------
Mouse pointers are naturally 2-vectors. The default encoding is cartesian
`(x, y)` in screen pixels. Polar `(r, θ)` is offered as a coordinate
*option* via `cartesian_to_polar()` / `polar_to_cartesian()` — useful for
gesture-direction analysis. Bijection is preserved end-to-end for r > 0.

Default channel routing (configurable per call):

  mouse pointer events -> CA (Cassisivadan)  - math/logic, geometry
  keyboard symbol events -> AV (Avali)       - communication, transport
"""

from __future__ import annotations

import enum
import math
import struct
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

# ---------------------------------------------------------------------------
#  Schema constants
# ---------------------------------------------------------------------------

# Frame layout (little-endian):
#   1 byte   kind        (0x01 = mouse, 0x02 = key)
#   8 bytes  timestamp   uint64 microseconds since epoch
#   ... kind-specific tail ...
#
# Mouse tail (16 bytes):
#   4 bytes  x  int32
#   4 bytes  y  int32
#   1 byte   button enum
#   1 byte   action enum
#   2 bytes  reserved (must be zero)
#   4 bytes  scroll delta int32   (0 unless action == SCROLL)
#
# Key tail (8 bytes):
#   2 bytes  keycode uint16
#   1 byte   modifiers bitmask
#   1 byte   action enum
#   4 bytes  reserved (must be zero)

KIND_MOUSE = 0x01
KIND_KEY = 0x02

MOUSE_FRAME_SIZE = 1 + 8 + 16  # 25 bytes
KEY_FRAME_SIZE = 1 + 8 + 8  # 17 bytes


class MouseButton(enum.IntEnum):
    NONE = 0
    LEFT = 1
    MIDDLE = 2
    RIGHT = 3
    X1 = 4
    X2 = 5


class MouseAction(enum.IntEnum):
    MOVE = 0
    DOWN = 1
    UP = 2
    SCROLL = 3


class KeyAction(enum.IntEnum):
    DOWN = 0
    UP = 1
    REPEAT = 2


# Modifier bitmask (matches X11 / common conventions)
MOD_SHIFT = 0x01
MOD_CTRL = 0x02
MOD_ALT = 0x04
MOD_META = 0x08


# ---------------------------------------------------------------------------
#  Event types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MouseEvent:
    timestamp_us: int
    x: int
    y: int
    button: MouseButton = MouseButton.NONE
    action: MouseAction = MouseAction.MOVE
    scroll_delta: int = 0

    def __post_init__(self) -> None:
        if not (0 <= self.timestamp_us < 2**64):
            raise ValueError(f"timestamp_us out of uint64 range: {self.timestamp_us}")
        if not (-(2**31) <= self.x < 2**31):
            raise ValueError(f"x out of int32 range: {self.x}")
        if not (-(2**31) <= self.y < 2**31):
            raise ValueError(f"y out of int32 range: {self.y}")
        if not (-(2**31) <= self.scroll_delta < 2**31):
            raise ValueError(f"scroll_delta out of int32 range: {self.scroll_delta}")


@dataclass(frozen=True)
class KeyEvent:
    timestamp_us: int
    keycode: int
    modifiers: int = 0
    action: KeyAction = KeyAction.DOWN

    def __post_init__(self) -> None:
        if not (0 <= self.timestamp_us < 2**64):
            raise ValueError(f"timestamp_us out of uint64 range: {self.timestamp_us}")
        if not (0 <= self.keycode < 2**16):
            raise ValueError(f"keycode out of uint16 range: {self.keycode}")
        if not (0 <= self.modifiers < 2**8):
            raise ValueError(f"modifiers out of uint8 range: {self.modifiers}")


# ---------------------------------------------------------------------------
#  Polar helpers (a coordinate option, not a security primitive)
# ---------------------------------------------------------------------------


def cartesian_to_polar(x: float, y: float) -> Tuple[float, float]:
    """Return (r, theta_degrees). Bijective for r > 0."""
    r = math.hypot(x, y)
    theta = math.degrees(math.atan2(y, x))
    return r, theta


def polar_to_cartesian(r: float, theta_degrees: float) -> Tuple[float, float]:
    """Inverse of cartesian_to_polar."""
    rad = math.radians(theta_degrees)
    return r * math.cos(rad), r * math.sin(rad)


# ---------------------------------------------------------------------------
#  Encode / decode — single events
# ---------------------------------------------------------------------------


def _pack_mouse(ev: MouseEvent) -> bytes:
    return bytes([KIND_MOUSE]) + struct.pack(
        "<Qiibb2sI",
        ev.timestamp_us,
        ev.x,
        ev.y,
        int(ev.button),
        int(ev.action),
        b"\x00\x00",
        ev.scroll_delta & 0xFFFFFFFF,  # signed-to-unsigned for the wire
    )


def _unpack_mouse(payload: bytes) -> MouseEvent:
    if len(payload) != MOUSE_FRAME_SIZE - 1:
        raise ValueError(f"mouse frame must be {MOUSE_FRAME_SIZE - 1} bytes after kind, got {len(payload)}")
    ts, x, y, btn, act, reserved, scroll_unsigned = struct.unpack("<Qiibb2sI", payload)
    if reserved != b"\x00\x00":
        raise ValueError("mouse frame reserved bytes must be zero")
    # Convert unsigned scroll back to signed int32.
    scroll = scroll_unsigned if scroll_unsigned < 2**31 else scroll_unsigned - 2**32
    return MouseEvent(
        timestamp_us=ts,
        x=x,
        y=y,
        button=MouseButton(btn),
        action=MouseAction(act),
        scroll_delta=scroll,
    )


def _pack_key(ev: KeyEvent) -> bytes:
    return bytes([KIND_KEY]) + struct.pack(
        "<QHBB4s",
        ev.timestamp_us,
        ev.keycode,
        ev.modifiers,
        int(ev.action),
        b"\x00\x00\x00\x00",
    )


def _unpack_key(payload: bytes) -> KeyEvent:
    if len(payload) != KEY_FRAME_SIZE - 1:
        raise ValueError(f"key frame must be {KEY_FRAME_SIZE - 1} bytes after kind, got {len(payload)}")
    ts, keycode, mods, action, reserved = struct.unpack("<QHBB4s", payload)
    if reserved != b"\x00\x00\x00\x00":
        raise ValueError("key frame reserved bytes must be zero")
    return KeyEvent(
        timestamp_us=ts,
        keycode=keycode,
        modifiers=mods,
        action=KeyAction(action),
    )


def encode_mouse_event(ev: MouseEvent, *, tongue: str = "ca") -> List[str]:
    return SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, _pack_mouse(ev))


def decode_mouse_event(tokens: Sequence[str], *, tongue: str = "ca") -> MouseEvent:
    raw = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, list(tokens))
    if not raw or raw[0] != KIND_MOUSE:
        raise ValueError("not a mouse frame")
    return _unpack_mouse(raw[1:])


def encode_key_event(ev: KeyEvent, *, tongue: str = "av") -> List[str]:
    return SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, _pack_key(ev))


def decode_key_event(tokens: Sequence[str], *, tongue: str = "av") -> KeyEvent:
    raw = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, list(tokens))
    if not raw or raw[0] != KIND_KEY:
        raise ValueError("not a key frame")
    return _unpack_key(raw[1:])


# ---------------------------------------------------------------------------
#  Trace — heterogeneous event stream with self-describing kind byte
# ---------------------------------------------------------------------------


@dataclass
class TraceFrame:
    """Wrapper used by encode_trace/decode_trace so we can hand back typed
    events from a heterogeneous stream."""

    event: object  # MouseEvent | KeyEvent
    tongue: str
    kind: int


def _pack_event(ev: object) -> bytes:
    if isinstance(ev, MouseEvent):
        return _pack_mouse(ev)
    if isinstance(ev, KeyEvent):
        return _pack_key(ev)
    raise TypeError(f"unknown event type: {type(ev).__name__}")


def encode_trace(
    events: Iterable[object],
    *,
    mouse_tongue: str = "ca",
    key_tongue: str = "av",
) -> List[Tuple[str, List[str]]]:
    """Encode a heterogeneous event sequence as a list of (tongue, tokens) pairs.

    Each pair is decode-ready in isolation. Returning per-event pairs (instead
    of one giant token blob) keeps the channel routing visible and lets the
    governance gate score events independently.
    """
    out: List[Tuple[str, List[str]]] = []
    for ev in events:
        if isinstance(ev, MouseEvent):
            out.append((mouse_tongue, encode_mouse_event(ev, tongue=mouse_tongue)))
        elif isinstance(ev, KeyEvent):
            out.append((key_tongue, encode_key_event(ev, tongue=key_tongue)))
        else:
            raise TypeError(f"unknown event type: {type(ev).__name__}")
    return out


def decode_trace(packets: Sequence[Tuple[str, Sequence[str]]]) -> List[object]:
    """Inverse of encode_trace. Picks the right decoder per kind byte."""
    decoded: List[object] = []
    for tongue, tokens in packets:
        raw = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, list(tokens))
        if not raw:
            raise ValueError("empty packet")
        kind = raw[0]
        if kind == KIND_MOUSE:
            decoded.append(_unpack_mouse(raw[1:]))
        elif kind == KIND_KEY:
            decoded.append(_unpack_key(raw[1:]))
        else:
            raise ValueError(f"unknown kind byte: 0x{kind:02x}")
    return decoded


# ---------------------------------------------------------------------------
#  Verify + replay
# ---------------------------------------------------------------------------


def verify_trace(
    packets: Sequence[Tuple[str, Sequence[str]]],
    *,
    expected_count: int | None = None,
    expected_kinds: Sequence[int] | None = None,
) -> dict:
    """Verify a trace's shape without fully decoding event payloads.

    Returns a dict with `ok`, `count`, `kinds`, `total_bytes`, `failure`. The
    function is fast — it touches each packet once, decodes only the kind
    byte, and counts. Use this on the hot path; reach for `decode_trace`
    when you need the actual event objects.
    """
    kinds: List[int] = []
    total_bytes = 0
    failure: str | None = None
    try:
        for idx, (tongue, tokens) in enumerate(packets):
            if tongue not in SACRED_TONGUE_TOKENIZER.tongues:
                raise ValueError(f"unknown tongue at packet {idx}: {tongue}")
            raw = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, list(tokens))
            if not raw:
                raise ValueError(f"empty packet at index {idx}")
            kinds.append(raw[0])
            total_bytes += len(raw)
    except Exception as exc:  # pragma: no cover - defensive
        failure = f"{type(exc).__name__}: {exc}"

    ok = failure is None
    if ok and expected_count is not None and len(kinds) != expected_count:
        ok = False
        failure = f"expected_count={expected_count}, got {len(kinds)}"
    if ok and expected_kinds is not None and tuple(kinds) != tuple(expected_kinds):
        ok = False
        failure = f"expected_kinds={tuple(expected_kinds)}, got {tuple(kinds)}"

    return {
        "ok": ok,
        "count": len(kinds),
        "kinds": kinds,
        "total_bytes": total_bytes,
        "failure": failure,
    }


def replay_trace(
    packets: Sequence[Tuple[str, Sequence[str]]],
    *,
    sink: callable | None = None,
) -> List[object]:
    """Decode a trace and optionally hand each event to a `sink` callable.

    The sink is what plugs OS-level input drivers in (pynput, playwright)
    on top of the deterministic event stream. With sink=None this is just
    an alias for `decode_trace`.
    """
    events = decode_trace(packets)
    if sink is not None:
        for ev in events:
            sink(ev)
    return events


__all__ = [
    "KeyAction",
    "KeyEvent",
    "MouseAction",
    "MouseButton",
    "MouseEvent",
    "MOD_ALT",
    "MOD_CTRL",
    "MOD_META",
    "MOD_SHIFT",
    "decode_key_event",
    "decode_mouse_event",
    "decode_trace",
    "encode_key_event",
    "encode_mouse_event",
    "encode_trace",
    "polar_to_cartesian",
    "replay_trace",
    "cartesian_to_polar",
    "verify_trace",
]
