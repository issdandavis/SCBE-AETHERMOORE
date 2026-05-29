"""Temporal frame tracker over the video multi-lattice.

This module keeps the first version deliberately deterministic: callers provide
per-axis feature vectors, the tracker records drift, and correction events are
emitted when aggregate drift crosses the configured threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .multi_lattice import LatticeAxis, MultiLattice, MultiLatticeFrame


@dataclass
class FrameState:
    """Tracked state for one observed frame."""

    frame_index: int
    aggregate_drift: float
    correction_triggered: bool
    max_drift_axis: Optional[LatticeAxis]
    drift_by_axis: Dict[LatticeAxis, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "aggregate_drift": self.aggregate_drift,
            "correction_triggered": self.correction_triggered,
            "max_drift_axis": self.max_drift_axis.value if self.max_drift_axis else None,
            "drift_by_axis": {axis.value: drift for axis, drift in self.drift_by_axis.items()},
        }


class TemporalTracker:
    """Stateful video-frame drift tracker.

    Args:
        lattice: optional preconfigured multi-lattice.
        correction_threshold: aggregate drift threshold when creating a default
            multi-lattice.
    """

    def __init__(
        self,
        lattice: Optional[MultiLattice] = None,
        *,
        correction_threshold: float = 2.0,
        dim: int = 64,
    ) -> None:
        self.lattice = lattice or MultiLattice(dim=dim, correction_threshold=correction_threshold)
        self._history: List[FrameState] = []

    def observe(self, axis_vectors: Dict[LatticeAxis, np.ndarray]) -> FrameState:
        """Observe one frame and return its temporal coherence state."""

        frame: MultiLatticeFrame = self.lattice.observe(axis_vectors)
        state = FrameState(
            frame_index=frame.frame_index,
            aggregate_drift=frame.aggregate_drift,
            correction_triggered=frame.correction_triggered,
            max_drift_axis=frame.max_drift_axis,
            drift_by_axis={axis: obs.drift for axis, obs in frame.observations.items()},
        )
        self._history.append(state)
        return state

    @property
    def history(self) -> List[FrameState]:
        return list(self._history)

    def recent(self, n: int = 5) -> List[FrameState]:
        if n <= 0:
            return []
        return self._history[-n:]

    def correction_events(self) -> List[FrameState]:
        return [state for state in self._history if state.correction_triggered]

    def reset(self) -> None:
        self.lattice.reset()
        self._history = []
