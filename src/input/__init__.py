"""Bijective input telemetry for SCBE-governed agent actions.

Mouse and keyboard events become deterministic Sacred-Tongue packets that
the SCBE pipeline can replay, verify, and govern as input traces. Two
independent channels: pointer events (mouse) and symbolic events
(keyboard).
"""

from .bijective_input import (  # noqa: F401
    KeyAction,
    KeyEvent,
    MouseAction,
    MouseButton,
    MouseEvent,
    decode_key_event,
    decode_mouse_event,
    decode_trace,
    encode_key_event,
    encode_mouse_event,
    encode_trace,
    polar_to_cartesian,
    replay_trace,
    cartesian_to_polar,
    verify_trace,
)
