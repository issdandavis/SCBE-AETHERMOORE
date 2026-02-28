"""Tests for aether_ide.self_improve."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.aether_ide.self_improve import SelfImproveLoop, ImprovementTask
from src.aether_ide.types import IDEAction, IDEEvent


def _make_event(decision: str, threat_score: float = 0.0) -> IDEEvent:
    """Helper to create a test event."""
    class FakeResult:
        def __init__(self, ts):
            self.threat_score = ts
    return IDEEvent(
        action=IDEAction(kind="edit", content="x = 1"),
        decision=decision,
        encoder_result=FakeResult(threat_score),
        timestamp=0.0,
        session_id="test",
    )


def test_coherence_starts_high():
    loop = SelfImproveLoop()
    assert loop.current_coherence == 1.0


def test_coherence_degrades_with_denies():
    loop = SelfImproveLoop(window_size=10)
    for _ in range(10):
        loop.observe(_make_event("DENY"))
    assert loop.current_coherence < 0.55


def test_improvement_task_generated():
    loop = SelfImproveLoop(coherence_threshold=0.9, window_size=5)
    task = None
    for _ in range(6):
        result = loop.observe(_make_event("DENY"))
        if result is not None:
            task = result
    assert task is not None
    assert isinstance(task, ImprovementTask)
    assert task.metric in ("deny_rate", "coherence")


def test_no_task_when_all_allow():
    loop = SelfImproveLoop(window_size=10)
    for _ in range(10):
        result = loop.observe(_make_event("ALLOW"))
        assert result is None


def test_pending_tasks():
    loop = SelfImproveLoop(coherence_threshold=0.9, window_size=5)
    for _ in range(6):
        loop.observe(_make_event("DENY"))
    assert len(loop.pending_tasks) > 0


def test_clear_tasks():
    loop = SelfImproveLoop(coherence_threshold=0.9, window_size=5)
    for _ in range(6):
        loop.observe(_make_event("DENY"))
    loop.clear_tasks()
    assert len(loop.pending_tasks) == 0
