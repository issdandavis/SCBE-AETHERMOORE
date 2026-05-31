"""Temporal frame tracker over the video multi-lattice.

Callers provide per-axis feature vectors; the tracker records centroid drift
and emits correction events when aggregate drift crosses the threshold.

Intent anchor — closes the trijective audit triangle (human intent / machine
representation / physical output).  Call set_intent_anchor() to declare the
reference state (e.g. "closed fist", "neutral pose").  Every subsequent
observe() computes per-axis hyperbolic distance from the anchor embedding to
the current embedding.  Drift above intent_threshold sets
FrameState.intent_violated = True.  Any loss is declared and routed —
no claim of perfect invertibility is made.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .multi_lattice import LatticeAxis, MultiLattice, MultiLatticeFrame


@dataclass
class IntentAnchor:
    """Declared human-intent reference for the trijective audit loop."""

    axis_vectors: Dict[LatticeAxis, np.ndarray]
    description: str = ""


@dataclass
class FrameState:
    """Tracked state for one observed frame."""

    frame_index: int
    aggregate_drift: float
    correction_triggered: bool
    max_drift_axis: Optional[LatticeAxis]
    drift_by_axis: Dict[LatticeAxis, float] = field(default_factory=dict)
    # Trijective audit: distance from declared intent anchor (empty if no anchor set)
    intent_drift_by_axis: Dict[LatticeAxis, float] = field(default_factory=dict)
    intent_violated: bool = False

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "aggregate_drift": self.aggregate_drift,
            "correction_triggered": self.correction_triggered,
            "max_drift_axis": self.max_drift_axis.value if self.max_drift_axis else None,
            "drift_by_axis": {axis.value: drift for axis, drift in self.drift_by_axis.items()},
            "intent_drift_by_axis": {axis.value: drift for axis, drift in self.intent_drift_by_axis.items()},
            "intent_violated": self.intent_violated,
        }


class TemporalTracker:
    """Stateful video-frame drift tracker.

    Args:
        lattice: optional preconfigured multi-lattice.
        correction_threshold: aggregate drift threshold when creating a default
            multi-lattice.
        intent_threshold: per-axis intent drift above this marks the frame as
            intent_violated in the trijective audit triangle.
    """

    def __init__(
        self,
        lattice: Optional[MultiLattice] = None,
        *,
        correction_threshold: float = 2.0,
        dim: int = 64,
        intent_threshold: float = 1.0,
    ) -> None:
        self.lattice = lattice or MultiLattice(dim=dim, correction_threshold=correction_threshold)
        self._history: List[FrameState] = []
        self._intent_threshold = intent_threshold
        self._intent_anchor: Optional[IntentAnchor] = None

    # ------------------------------------------------------------------
    # Intent anchor — human-intent vertex of the audit triangle
    # ------------------------------------------------------------------

    @property
    def intent_anchor(self) -> Optional[IntentAnchor]:
        return self._intent_anchor

    def set_intent_anchor(
        self,
        axis_vectors: Dict[LatticeAxis, np.ndarray],
        description: str = "",
    ) -> None:
        """Declare the human-intent reference state.

        Args:
            axis_vectors: per-axis vectors representing the target pose/scene
                state (e.g. "closed fist", "neutral pose").
            description: human-readable label for provenance logging.
        """
        self._intent_anchor = IntentAnchor(
            axis_vectors={ax: np.asarray(v, dtype=np.float64) for ax, v in axis_vectors.items()},
            description=description,
        )

    def clear_intent_anchor(self) -> None:
        """Remove the intent anchor; subsequent frames report no intent drift."""
        self._intent_anchor = None

    # ------------------------------------------------------------------
    # Core observe
    # ------------------------------------------------------------------

    def observe(self, axis_vectors: Dict[LatticeAxis, np.ndarray]) -> FrameState:
        """Observe one frame and return its temporal coherence state."""
        frame: MultiLatticeFrame = self.lattice.observe(axis_vectors)

        # Intent drift: hyperbolic distance from declared anchor to current embedding
        intent_drift_by_axis: Dict[LatticeAxis, float] = {}
        intent_violated = False
        if self._intent_anchor is not None:
            for ax, anchor_vec in self._intent_anchor.axis_vectors.items():
                if ax in frame.observations:
                    per_ax = self.lattice.lattice(ax)
                    p_anchor = per_ax.embed(anchor_vec)
                    p_current = frame.observations[ax].embedding
                    intent_drift_by_axis[ax] = per_ax.distance(p_anchor, p_current)
            if intent_drift_by_axis:
                intent_violated = max(intent_drift_by_axis.values()) > self._intent_threshold

        state = FrameState(
            frame_index=frame.frame_index,
            aggregate_drift=frame.aggregate_drift,
            correction_triggered=frame.correction_triggered,
            max_drift_axis=frame.max_drift_axis,
            drift_by_axis={axis: obs.drift for axis, obs in frame.observations.items()},
            intent_drift_by_axis=intent_drift_by_axis,
            intent_violated=intent_violated,
        )
        self._history.append(state)
        return state

    # ------------------------------------------------------------------
    # History queries
    # ------------------------------------------------------------------

    @property
    def history(self) -> List[FrameState]:
        return list(self._history)

    def recent(self, n: int = 5) -> List[FrameState]:
        if n <= 0:
            return []
        return self._history[-n:]

    def correction_events(self) -> List[FrameState]:
        return [state for state in self._history if state.correction_triggered]

    def intent_violations(self) -> List[FrameState]:
        """Frames where the observed state exceeded the intent drift threshold."""
        return [state for state in self._history if state.intent_violated]

    def summary(self) -> dict:
        return {
            "frame_count": len(self._history),
            "correction_events": len(self.correction_events()),
            "intent_violations": len(self.intent_violations()),
            "intent_anchor": self._intent_anchor.description if self._intent_anchor else None,
            "lattice_summary": self.lattice.summary(),
        }

    def reset(self) -> None:
        self.lattice.reset()
        self._history = []
