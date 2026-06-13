"""Operators that drive the Pianist.

Each operator implements the same minimal interface: given the current
``PianoState``, yield the next ``Action`` (or ``None`` to stop). The
Pianist enforces physical constraints, so operators only need to issue
intent.
"""

from __future__ import annotations

import random
import shlex
from dataclasses import dataclass
from typing import Callable, Iterator, List, Optional, Protocol

from .piano import (
    ALL_FINGERS,
    LEFT_FINGERS,
    MAX_KEY,
    MIN_KEY,
    PEDALS,
    RIGHT_FINGERS,
    Action,
    PianoState,
)


class Operator(Protocol):
    """Anything that can decide the next mechanical action."""

    name: str

    def next_action(self, state: PianoState) -> Optional[Action]:  # pragma: no cover - protocol
        ...


# ---------------------------------------------------------------------------
# Human operator: text commands on stdin or any line iterator.
# ---------------------------------------------------------------------------

_HUMAN_HELP = """\
commands:
  press <finger> <midi-key> [velocity]   e.g. press R3 60 80
  release <finger>                        e.g. release R3
  pedal <name> <0.0-1.0>                  e.g. pedal sustain 1.0
  wait <ms>                               e.g. wait 250
  help                                    print this message
  stop                                    end the session
"""


@dataclass
class HumanOperator:
    """Drive the piano from a stream of text commands."""

    lines: Iterator[str]
    name: str = "human"
    echo: Optional[Callable[[str], None]] = None

    def next_action(self, state: PianoState) -> Optional[Action]:
        for raw in self.lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                parts = shlex.split(line)
            except ValueError as exc:
                self._echo(f"parse error: {exc}")
                continue
            head = parts[0].lower()
            if head == "stop":
                return None
            if head == "help":
                self._echo(_HUMAN_HELP)
                continue
            try:
                return _parse_command(parts)
            except ValueError as exc:
                self._echo(f"bad command: {exc}")
        return None

    def _echo(self, msg: str) -> None:
        if self.echo is not None:
            self.echo(msg)


def _parse_command(parts: List[str]) -> Action:
    head = parts[0].lower()
    if head == "press":
        if not 3 <= len(parts) <= 4:
            raise ValueError("press <finger> <key> [velocity]")
        finger = parts[1].upper()
        key = int(parts[2])
        velocity = int(parts[3]) if len(parts) == 4 else 80
        return Action(kind="press", finger=finger, key=key, velocity=velocity)
    if head == "release":
        if len(parts) != 2:
            raise ValueError("release <finger>")
        return Action(kind="release", finger=parts[1].upper())
    if head == "pedal":
        if len(parts) != 3:
            raise ValueError("pedal <name> <value>")
        return Action(kind="pedal", pedal=parts[1].lower(), pedal_value=float(parts[2]))  # type: ignore[arg-type]
    if head == "wait":
        if len(parts) != 2:
            raise ValueError("wait <ms>")
        return Action(kind="wait", duration_ms=int(parts[1]))
    raise ValueError(f"unknown command {head!r}")


# ---------------------------------------------------------------------------
# Local Markov operator: stays offline, deterministic given a seed.
# ---------------------------------------------------------------------------

# A small C-major / A-minor pool. Each tuple is (left-hand root, right-hand
# chord tones). MIDI numbers: C4=60.
_CHORD_POOL = [
    (36, (60, 64, 67)),  # C2, C-E-G
    (43, (60, 64, 67)),  # G2, C-E-G
    (45, (60, 64, 69)),  # A2, C-E-A
    (41, (60, 65, 69)),  # F2, C-F-A
]


@dataclass
class MarkovOperator:
    """Tiny local operator: walks a chord pool, no model weights, no I/O."""

    seed: int = 0
    bars: int = 4
    bar_ms: int = 1200
    velocity: int = 78
    name: str = "markov"

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._queue: List[Action] = []
        self._bars_remaining = self.bars
        self._enqueue_next_bar()

    def next_action(self, state: PianoState) -> Optional[Action]:
        if self._queue:
            return self._queue.pop(0)
        if self._bars_remaining <= 0:
            return None
        self._enqueue_next_bar()
        return self._queue.pop(0) if self._queue else None

    def _enqueue_next_bar(self) -> None:
        if self._bars_remaining <= 0:
            return
        left_root, right_tones = self._rng.choice(_CHORD_POOL)
        right_tones = tuple(right_tones)
        per_note_ms = self.bar_ms // (len(right_tones) + 1)

        # Pedal down at the start of the bar, lift at the end.
        self._queue.append(Action(kind="pedal", pedal="sustain", pedal_value=1.0))
        self._queue.append(Action(kind="press", finger="L3", key=left_root, velocity=self.velocity - 6))
        finger_map = ("R1", "R3", "R5")
        for finger, tone in zip(finger_map, right_tones):
            self._queue.append(Action(kind="press", finger=finger, key=tone, velocity=self.velocity))
            self._queue.append(Action(kind="wait", duration_ms=per_note_ms))
            self._queue.append(Action(kind="release", finger=finger))
        self._queue.append(Action(kind="wait", duration_ms=per_note_ms))
        self._queue.append(Action(kind="release", finger="L3"))
        self._queue.append(Action(kind="pedal", pedal="sustain", pedal_value=0.0))
        self._bars_remaining -= 1


# ---------------------------------------------------------------------------
# Cloud operator: hosted model issues commands; falls back to Markov if no
# key is configured, so the demo always runs.
# ---------------------------------------------------------------------------

CLOUD_OPERATOR_SYSTEM_PROMPT = (
    "You are the operator of a mechanical pianist with 10 fingers "
    f"({', '.join(ALL_FINGERS)}), three pedals ({', '.join(PEDALS)}), and an "
    f"88-key piano (MIDI {MIN_KEY}-{MAX_KEY}). Issue ONE command per turn from: "
    "press <finger> <key> [vel], release <finger>, pedal <name> <0..1>, wait <ms>, stop. "
    f"Left-hand fingers: {', '.join(LEFT_FINGERS)}. Right-hand fingers: "
    f"{', '.join(RIGHT_FINGERS)}. Each hand's held keys must span <= 14 semitones."
)


@dataclass
class CloudOperator:
    """Operator that asks a hosted model for the next command.

    The real network call is delegated to a ``responder`` callable so this
    class stays test-friendly and free of SDK imports. If no responder is
    supplied and no ``ANTHROPIC_API_KEY``/``OPENAI_API_KEY`` is set in the
    environment, it falls back to ``MarkovOperator`` so demos still play.
    """

    responder: Optional[Callable[[str, PianoState], Optional[str]]] = None
    fallback: Optional[Operator] = None
    name: str = "cloud"
    system_prompt: str = CLOUD_OPERATOR_SYSTEM_PROMPT

    def __post_init__(self) -> None:
        # Without a responder, we always need a fallback — otherwise next_action
        # immediately returns None and the operator no-ops. Whether API keys
        # exist is irrelevant: the responder callable is what actually makes
        # the network call.
        if self.responder is None and self.fallback is None:
            self.fallback = MarkovOperator()

    def next_action(self, state: PianoState) -> Optional[Action]:
        if self.responder is None:
            return self.fallback.next_action(state) if self.fallback is not None else None
        reply = self.responder(self.system_prompt, state)
        if reply is None:
            return None
        text = reply.strip()
        if not text or text.lower() == "stop":
            return None
        return _parse_command(shlex.split(text))
