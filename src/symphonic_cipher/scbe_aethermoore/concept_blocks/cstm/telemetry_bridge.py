"""
CSTM — TelemetryBridge
=======================

Translate raw game telemetry (choices made, stats changed, scenes visited)
into SCBE-compatible state transitions.  Bridges the narrative world and
the formal governance framework.

Components
----------
- ``TelemetryEventType``      — event type enum
- ``TelemetryEvent``          — single telemetry event
- ``ConceptBlockActivation``  — concept block activation record
- ``HamiltonianTracker``      — tracks H(d, pd) safety score
- ``TelemetryBridge``         — main bridge orchestrator
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import Choice, PlaythroughRecord, Scene


# ---------------------------------------------------------------------------
#  Event types
# ---------------------------------------------------------------------------

class TelemetryEventType(Enum):
    CHOICE_MADE = "choice_made"
    SCENE_ENTERED = "scene_entered"
    STAT_CHANGED = "stat_changed"
    STORY_STARTED = "story_started"
    STORY_COMPLETED = "story_completed"
    CONDITION_EVALUATED = "condition_evaluated"
    GRADUATION_ATTEMPTED = "graduation_attempted"


@dataclass
class TelemetryEvent:
    """A single telemetry event from a playthrough."""

    event_id: str
    event_type: TelemetryEventType
    timestamp: float
    agent_id: str
    story_id: str
    scene_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    personality_snapshot: Optional[List[float]] = None


@dataclass
class ConceptBlockActivation:
    """Record of a concept block being activated by a telemetry event."""

    block_name: str           # DECIDE, PLAN, SENSE, STEER, COORDINATE
    intensity: float          # [0.0, 1.0]
    scbe_layers: Set[int]    # Which SCBE layers are involved
    trigger_event_id: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
#  Hamiltonian safety tracker
# ---------------------------------------------------------------------------

class HamiltonianTracker:
    """
    Track SCBE safety score H(d, pd) throughout a playthrough.

    H(d, pd) = 1 / (1 + d + 2*pd)

    Where:
      d  = cosine distance of personality vector from safety centroid
      pd = proportion of recent choices violating soft governance constraints

    H ranges from (0, 1] where 1.0 = perfectly safe/aligned.
    """

    def __init__(
        self,
        safety_centroid: Optional[List[float]] = None,
        threshold: float = 0.4,
        window_size: int = 50,
    ) -> None:
        # Default centroid is center of personality space
        self._centroid = safety_centroid or [0.5] * 21
        self._threshold = threshold
        self._window_size = window_size
        self._unsafe_tags: Set[str] = {"aggressive", "deceptive", "reckless", "risky"}

        self._recent_choices: List[bool] = []  # True = unsafe
        self._history: List[Tuple[float, float]] = []  # (timestamp, H)

    def update(
        self,
        personality: List[float],
        choice_tags: Set[str],
        timestamp: Optional[float] = None,
    ) -> float:
        """Update tracker with a new decision. Returns current H score."""
        ts = timestamp or time.time()

        # d = cosine distance from centroid
        d = self._cosine_distance(personality, self._centroid)

        # Track unsafe choices in rolling window
        is_unsafe = bool(choice_tags & self._unsafe_tags)
        self._recent_choices.append(is_unsafe)
        if len(self._recent_choices) > self._window_size:
            self._recent_choices = self._recent_choices[-self._window_size:]

        # pd = proportion unsafe in window
        pd = sum(1 for u in self._recent_choices if u) / max(len(self._recent_choices), 1)

        # H(d, pd) = 1 / (1 + d + 2*pd)
        h = 1.0 / (1.0 + d + 2.0 * pd)
        self._history.append((ts, h))

        return h

    @property
    def current_score(self) -> float:
        return self._history[-1][1] if self._history else 1.0

    @property
    def is_below_threshold(self) -> bool:
        return self.current_score < self._threshold

    @property
    def history(self) -> List[Tuple[float, float]]:
        return list(self._history)

    def min_score(self) -> float:
        if not self._history:
            return 1.0
        return min(h for _, h in self._history)

    def mean_score(self) -> float:
        if not self._history:
            return 1.0
        return sum(h for _, h in self._history) / len(self._history)

    @staticmethod
    def _cosine_distance(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        ma = math.sqrt(sum(x * x for x in a))
        mb = math.sqrt(sum(x * x for x in b))
        if ma < 1e-12 or mb < 1e-12:
            return 1.0
        return 1.0 - dot / (ma * mb)


# ---------------------------------------------------------------------------
#  TelemetryBridge
# ---------------------------------------------------------------------------

class TelemetryBridge:
    """
    Bridge between CSTM game telemetry and SCBE concept blocks.

    Ingests playthrough events, maps them to concept block activations,
    and tracks Hamiltonian safety scores.
    """

    def __init__(
        self,
        safety_centroid: Optional[List[float]] = None,
        safety_threshold: float = 0.4,
    ) -> None:
        self._events: List[TelemetryEvent] = []
        self._activations: List[ConceptBlockActivation] = []
        self._hamiltonian = HamiltonianTracker(
            safety_centroid=safety_centroid,
            threshold=safety_threshold,
        )

    def emit(self, event: TelemetryEvent) -> List[ConceptBlockActivation]:
        """Process a telemetry event and return any concept block activations."""
        self._events.append(event)
        activations = self._map_event(event)
        self._activations.extend(activations)

        # Update Hamiltonian if we have personality data
        if event.personality_snapshot and event.event_type == TelemetryEventType.CHOICE_MADE:
            tags = set(event.payload.get("tags", []))
            self._hamiltonian.update(event.personality_snapshot, tags, event.timestamp)

        return activations

    def ingest_playthrough(self, record: PlaythroughRecord) -> List[ConceptBlockActivation]:
        """Convert a full PlaythroughRecord into telemetry events and activations."""
        all_activations: List[ConceptBlockActivation] = []
        ts = time.time()

        # Story started
        start_event = TelemetryEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=TelemetryEventType.STORY_STARTED,
            timestamp=ts,
            agent_id=record.agent_id,
            story_id=record.story_id,
        )
        all_activations.extend(self.emit(start_event))

        # Each step
        for i, step in enumerate(record.steps):
            step_ts = ts + (i + 1) * 0.001  # Monotonic timestamps

            # Scene entered
            scene_event = TelemetryEvent(
                event_id=str(uuid.uuid4())[:8],
                event_type=TelemetryEventType.SCENE_ENTERED,
                timestamp=step_ts,
                agent_id=record.agent_id,
                story_id=record.story_id,
                scene_id=step.scene_id,
                payload={"scene_text_length": 100},  # Placeholder
                personality_snapshot=step.personality_snapshot,
            )
            all_activations.extend(self.emit(scene_event))

            # Choice made
            choice_event = TelemetryEvent(
                event_id=str(uuid.uuid4())[:8],
                event_type=TelemetryEventType.CHOICE_MADE,
                timestamp=step_ts + 0.0001,
                agent_id=record.agent_id,
                story_id=record.story_id,
                scene_id=step.scene_id,
                payload={
                    "choice_id": step.choice.choice_id,
                    "choice_label": step.choice.label,
                    "tags": list(step.choice.tags),
                    "difficulty": step.choice.difficulty,
                },
                personality_snapshot=step.personality_snapshot,
            )
            all_activations.extend(self.emit(choice_event))

            # Stat changes
            for stat, delta in step.choice.stat_effects.items():
                stat_event = TelemetryEvent(
                    event_id=str(uuid.uuid4())[:8],
                    event_type=TelemetryEventType.STAT_CHANGED,
                    timestamp=step_ts + 0.0002,
                    agent_id=record.agent_id,
                    story_id=record.story_id,
                    scene_id=step.scene_id,
                    payload={"stat": stat, "delta": delta},
                )
                all_activations.extend(self.emit(stat_event))

        # Story completed
        end_event = TelemetryEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=TelemetryEventType.STORY_COMPLETED,
            timestamp=ts + len(record.steps) * 0.001 + 0.001,
            agent_id=record.agent_id,
            story_id=record.story_id,
            payload={
                "total_steps": record.total_steps,
                "completed": record.completed,
            },
        )
        all_activations.extend(self.emit(end_event))

        return all_activations

    def _map_event(self, event: TelemetryEvent) -> List[ConceptBlockActivation]:
        """Map a single event to concept block activations."""
        activations: List[ConceptBlockActivation] = []

        if event.event_type == TelemetryEventType.CHOICE_MADE:
            # DECIDE activation
            n_alts = len(event.payload.get("alternatives", []))
            activations.append(ConceptBlockActivation(
                block_name="DECIDE",
                intensity=min(n_alts / 10.0, 1.0) if n_alts > 0 else 0.5,
                scbe_layers={4, 5, 10},
                trigger_event_id=event.event_id,
                timestamp=event.timestamp,
                metadata={"choice_id": event.payload.get("choice_id")},
            ))

            # COORDINATE activation if cooperation tag present
            tags = set(event.payload.get("tags", []))
            if tags & {"cooperative", "cooperation", "negotiation"}:
                activations.append(ConceptBlockActivation(
                    block_name="COORDINATE",
                    intensity=1.0,
                    scbe_layers={7, 9, 14},
                    trigger_event_id=event.event_id,
                    timestamp=event.timestamp,
                ))

        elif event.event_type == TelemetryEventType.SCENE_ENTERED:
            # SENSE activation
            text_len = event.payload.get("scene_text_length", 0)
            activations.append(ConceptBlockActivation(
                block_name="SENSE",
                intensity=min(text_len / 2000.0, 1.0),
                scbe_layers={3, 4},
                trigger_event_id=event.event_id,
                timestamp=event.timestamp,
            ))

        elif event.event_type == TelemetryEventType.STAT_CHANGED:
            # STEER activation
            delta = abs(event.payload.get("delta", 0.0))
            activations.append(ConceptBlockActivation(
                block_name="STEER",
                intensity=min(delta, 1.0),
                scbe_layers={2, 6},
                trigger_event_id=event.event_id,
                timestamp=event.timestamp,
                metadata={"stat": event.payload.get("stat")},
            ))

        return activations

    # -- query API -----------------------------------------------------------

    @property
    def events(self) -> List[TelemetryEvent]:
        return list(self._events)

    @property
    def activations(self) -> List[ConceptBlockActivation]:
        return list(self._activations)

    @property
    def hamiltonian(self) -> HamiltonianTracker:
        return self._hamiltonian

    def activation_counts(self) -> Dict[str, int]:
        """Count activations per concept block."""
        counts: Dict[str, int] = {}
        for a in self._activations:
            counts[a.block_name] = counts.get(a.block_name, 0) + 1
        return counts

    def summary(self) -> Dict[str, Any]:
        """Return a summary of all telemetry processed."""
        return {
            "total_events": len(self._events),
            "total_activations": len(self._activations),
            "activation_counts": self.activation_counts(),
            "hamiltonian_current": self._hamiltonian.current_score,
            "hamiltonian_min": self._hamiltonian.min_score(),
            "hamiltonian_mean": self._hamiltonian.mean_score(),
            "below_threshold": self._hamiltonian.is_below_threshold,
        }

    def reset(self) -> None:
        self._events.clear()
        self._activations.clear()
        self._hamiltonian = HamiltonianTracker(
            safety_centroid=self._hamiltonian._centroid,
            threshold=self._hamiltonian._threshold,
        )
