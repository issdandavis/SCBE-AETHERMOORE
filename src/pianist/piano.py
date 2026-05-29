"""Mechanical piano: 88 keys + 3 pedals + 10 fingers across two hands.

The Pianist enforces real-world constraints (one finger per key, hand-span
limits, finger reuse latency, 10-finger ceiling) so any operator -- human,
local model, or cloud model -- has to play within human physical bounds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

# MIDI key range for an 88-key piano: A0 (21) .. C8 (108).
MIN_KEY = 21
MAX_KEY = 108

# Hand layout: 5 fingers per hand, thumb = 1, pinky = 5.
LEFT_FINGERS = ("L1", "L2", "L3", "L4", "L5")
RIGHT_FINGERS = ("R1", "R2", "R3", "R4", "R5")
ALL_FINGERS = LEFT_FINGERS + RIGHT_FINGERS

# Maximum span between the lowest and highest key held by a single hand,
# in semitones. A real adult hand reaches a 9th to a 10th; we allow 14.
MAX_HAND_SPAN = 14

# Minimum time, in milliseconds, a finger must rest before being reused.
MIN_FINGER_REUSE_MS = 15

PedalName = Literal["sustain", "sostenuto", "soft"]
PEDALS: Tuple[PedalName, ...] = ("sustain", "sostenuto", "soft")


class PhysicalError(ValueError):
    """Raised when an operator requests an action a real pianist cannot do."""


@dataclass
class Action:
    """A single mechanical command issued by an operator."""

    kind: Literal["press", "release", "pedal", "wait"]
    finger: Optional[str] = None
    key: Optional[int] = None
    velocity: int = 80
    pedal: Optional[PedalName] = None
    pedal_value: float = 0.0
    duration_ms: int = 0


@dataclass
class _HeldNote:
    finger: str
    key: int
    velocity: int
    pressed_at_ms: int


@dataclass
class PianoState:
    """Public, read-only view of the piano at a moment in time."""

    now_ms: int
    held: Dict[str, Tuple[int, int]]  # finger -> (key, velocity)
    pedals: Dict[PedalName, float]


@dataclass
class Pianist:
    """Two hands, 10 fingers, 3 pedals, one piano."""

    now_ms: int = 0
    _held: Dict[str, _HeldNote] = field(default_factory=dict)
    _last_release_ms: Dict[str, int] = field(default_factory=dict)
    _pedals: Dict[PedalName, float] = field(default_factory=lambda: {p: 0.0 for p in PEDALS})
    events: List[Tuple[int, Action]] = field(default_factory=list)

    # --- queries --------------------------------------------------------

    def state(self) -> PianoState:
        return PianoState(
            now_ms=self.now_ms,
            held={f: (n.key, n.velocity) for f, n in self._held.items()},
            pedals=dict(self._pedals),
        )

    def held_keys(self) -> List[int]:
        return sorted(n.key for n in self._held.values())

    # --- execution ------------------------------------------------------

    def execute(self, action: Action) -> None:
        """Apply ``action`` or raise :class:`PhysicalError` if impossible."""
        if action.kind == "wait":
            if action.duration_ms < 0:
                raise PhysicalError("wait duration must be non-negative")
            self.now_ms += action.duration_ms
            self.events.append((self.now_ms, action))
            return

        if action.kind == "press":
            self._press(action)
        elif action.kind == "release":
            self._release(action)
        elif action.kind == "pedal":
            self._pedal(action)
        else:  # pragma: no cover - dataclass Literal enforces this
            raise PhysicalError(f"unknown action kind: {action.kind!r}")
        self.events.append((self.now_ms, action))

    # --- internal -------------------------------------------------------

    def _press(self, action: Action) -> None:
        finger = action.finger
        key = action.key
        if finger not in ALL_FINGERS:
            raise PhysicalError(f"unknown finger {finger!r}")
        if key is None or not (MIN_KEY <= key <= MAX_KEY):
            raise PhysicalError(f"key {key} outside piano range {MIN_KEY}-{MAX_KEY}")
        if not (1 <= action.velocity <= 127):
            raise PhysicalError(f"velocity {action.velocity} outside MIDI range 1-127")
        if finger in self._held:
            raise PhysicalError(f"finger {finger} is already pressing a key")
        if len(self._held) >= 10:
            raise PhysicalError("all 10 fingers are already pressing keys")
        last_release = self._last_release_ms.get(finger)
        if last_release is not None and self.now_ms - last_release < MIN_FINGER_REUSE_MS:
            raise PhysicalError(
                f"finger {finger} needs {MIN_FINGER_REUSE_MS} ms rest before reuse "
                f"(only {self.now_ms - last_release} ms since release)"
            )

        # Hand-span check: pretend the press has happened, then verify the
        # owning hand's keys still fit inside MAX_HAND_SPAN.
        owning_hand = LEFT_FINGERS if finger in LEFT_FINGERS else RIGHT_FINGERS
        hand_keys = [n.key for f, n in self._held.items() if f in owning_hand] + [key]
        if max(hand_keys) - min(hand_keys) > MAX_HAND_SPAN:
            raise PhysicalError(
                f"{('left' if finger in LEFT_FINGERS else 'right')} hand span "
                f"{max(hand_keys) - min(hand_keys)} > {MAX_HAND_SPAN} semitones"
            )

        self._held[finger] = _HeldNote(finger=finger, key=key, velocity=action.velocity, pressed_at_ms=self.now_ms)

    def _release(self, action: Action) -> None:
        finger = action.finger
        if finger not in ALL_FINGERS:
            raise PhysicalError(f"unknown finger {finger!r}")
        if finger not in self._held:
            raise PhysicalError(f"finger {finger} is not pressing any key")
        del self._held[finger]
        self._last_release_ms[finger] = self.now_ms

    def _pedal(self, action: Action) -> None:
        if action.pedal not in PEDALS:
            raise PhysicalError(f"unknown pedal {action.pedal!r}")
        if not (0.0 <= action.pedal_value <= 1.0):
            raise PhysicalError(f"pedal value {action.pedal_value} outside 0.0-1.0")
        self._pedals[action.pedal] = action.pedal_value
