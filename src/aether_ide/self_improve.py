"""Self-Improvement Loop -- coherence monitoring and task generation.

Watches the stream of IDE events.  When coherence degrades below
threshold, generates improvement task records.

@layer Layer 11, Layer 13
@component AetherIDE.SelfImprove
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.aether_ide.types import IDEEvent


@dataclass
class ImprovementTask:
    """A self-improvement task generated from coherence degradation."""
    metric: str
    current_value: float
    threshold: float
    suggested_action: str
    tongue: str = "RU"
    priority: int = 5


class SelfImproveLoop:
    """Monitor IDE coherence and generate improvement tasks."""

    def __init__(self, coherence_threshold: float = 0.55, window_size: int = 20):
        self._threshold = coherence_threshold
        self._window_size = window_size
        self._recent_events: List[IDEEvent] = []
        self._tasks: List[ImprovementTask] = []

    def observe(self, event: IDEEvent) -> Optional[ImprovementTask]:
        """Observe an IDE event and check for coherence degradation.

        Returns an ImprovementTask if coherence has dropped below
        threshold, None otherwise.
        """
        self._recent_events.append(event)
        if len(self._recent_events) > self._window_size:
            self._recent_events = self._recent_events[-self._window_size:]

        coherence = self._compute_coherence()
        if coherence < self._threshold and len(self._recent_events) >= 5:
            evidence = self._build_evidence()
            task = self._generate_task(coherence, evidence)
            self._tasks.append(task)
            return task
        return None

    def _compute_coherence(self) -> float:
        """Compute rolling coherence from recent events.

        Coherence = 1.0 - (deny_rate * 0.5 + quarantine_rate * 0.3 + threat_avg * 0.2)
        """
        if not self._recent_events:
            return 1.0

        n = len(self._recent_events)
        deny_count = sum(1 for e in self._recent_events if e.decision == "DENY")
        quarantine_count = sum(1 for e in self._recent_events if e.decision == "QUARANTINE")

        threat_sum = 0.0
        for e in self._recent_events:
            if hasattr(e.encoder_result, "threat_score"):
                threat_sum += e.encoder_result.threat_score
        threat_avg = threat_sum / n if n > 0 else 0.0

        deny_rate = deny_count / n
        quarantine_rate = quarantine_count / n

        return max(0.0, 1.0 - (deny_rate * 0.5 + quarantine_rate * 0.3 + threat_avg * 0.2))

    def _build_evidence(self) -> Dict[str, Any]:
        """Collect evidence from recent events for the improvement task."""
        deny_count = sum(1 for e in self._recent_events if e.decision == "DENY")
        quarantine_count = sum(1 for e in self._recent_events if e.decision == "QUARANTINE")
        return {
            "window_size": len(self._recent_events),
            "deny_count": deny_count,
            "quarantine_count": quarantine_count,
            "deny_rate": deny_count / max(1, len(self._recent_events)),
        }

    def _generate_task(self, coherence: float, evidence: Dict[str, Any]) -> ImprovementTask:
        """Generate an ImprovementTask for the failing metric."""
        if evidence.get("deny_rate", 0) > 0.3:
            return ImprovementTask(
                metric="deny_rate",
                current_value=evidence["deny_rate"],
                threshold=0.3,
                suggested_action="Review recent DENY events for false positives; "
                                 "consider adjusting chemistry_threat_level",
                tongue="RU",
                priority=8,
            )
        return ImprovementTask(
            metric="coherence",
            current_value=coherence,
            threshold=self._threshold,
            suggested_action="Review recent QUARANTINE events; "
                             "consider narrowing input patterns",
            tongue="UM",
            priority=5,
        )

    @property
    def pending_tasks(self) -> List[ImprovementTask]:
        return list(self._tasks)

    @property
    def current_coherence(self) -> float:
        return self._compute_coherence()

    def clear_tasks(self) -> None:
        self._tasks.clear()
