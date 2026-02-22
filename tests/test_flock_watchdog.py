"""
Tests for Flock Shepherd v2.0 — Watchdog, Error Handling, Health Report, Event Log
==================================================================================

Covers:
    - FlockWatchdog auto-isolation of low-coherence sheep
    - FlockWatchdog auto-retirement of stuck isolated sheep
    - Task rebalancing on sheep failure
    - flock_health_report() generation and content
    - FlockEventLog recording and querying (by type, time, sheep)
    - Retry logic (assign_task_with_retry)
    - Graceful BFT degradation when quorum is lost
"""

import os
import sys
import time

import pytest

# Ensure src/ is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.symphonic_cipher.scbe_aethermoore.flock_shepherd import (
    COHERENCE_HEALTHY,
    COHERENCE_ISOLATE,
    COHERENCE_WARN,
    Flock,
    FlockEvent,
    FlockEventLog,
    FlockTask,
    FlockWatchdog,
    Sheep,
    SheepRole,
    SheepState,
    TrainingTrack,
    _retry_with_backoff,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def flock():
    """Fresh flock with no agents."""
    return Flock()


@pytest.fixture
def populated_flock():
    """Flock with 7 agents across all tracks/roles for BFT f=2."""
    f = Flock()
    f.spawn("Alpha", TrainingTrack.SYSTEM, SheepRole.LEADER)
    f.spawn("Bravo", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)
    f.spawn("Charlie", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)
    f.spawn("Delta", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)
    f.spawn("Echo", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)
    f.spawn("Foxtrot", TrainingTrack.FUNCTIONS, SheepRole.EXECUTOR)
    f.spawn("Golf", TrainingTrack.FUNCTIONS, SheepRole.EXECUTOR)
    return f


@pytest.fixture
def event_log():
    """Fresh FlockEventLog."""
    return FlockEventLog()


# ===========================================================================
# 1. FlockWatchdog — Auto-isolate low-coherence sheep
# ===========================================================================


class TestWatchdogAutoIsolate:
    """Watchdog should auto-isolate sheep whose coherence drops below threshold."""

    def test_isolate_low_coherence(self, flock):
        """Sheep with coherence below threshold gets isolated on tick."""
        sheep = flock.spawn("WeakAgent", TrainingTrack.SYSTEM)
        sheep.coherence = 0.20  # Below COHERENCE_ISOLATE (0.30)

        wd = FlockWatchdog(flock, coherence_threshold=0.30)
        result = wd.tick()

        assert sheep.sheep_id in result["isolated"]
        assert sheep.state == SheepState.ISOLATED

    def test_healthy_sheep_not_isolated(self, flock):
        """Sheep with coherence above threshold remains untouched."""
        sheep = flock.spawn("StrongAgent", TrainingTrack.SYSTEM)
        sheep.coherence = 0.90

        wd = FlockWatchdog(flock, coherence_threshold=0.30)
        result = wd.tick()

        assert result["isolated"] == []
        assert sheep.state == SheepState.ACTIVE

    def test_already_isolated_not_doubled(self, flock):
        """Sheep already ISOLATED is not re-isolated."""
        sheep = flock.spawn("AlreadyIso", TrainingTrack.SYSTEM)
        sheep.coherence = 0.10
        sheep.state = SheepState.ISOLATED

        wd = FlockWatchdog(flock, coherence_threshold=0.30)
        result = wd.tick()

        # Should not appear in newly isolated list
        assert sheep.sheep_id not in result["isolated"]

    def test_frozen_sheep_not_isolated(self, flock):
        """FROZEN sheep is not also isolated by watchdog."""
        sheep = flock.spawn("FrozenAgent", TrainingTrack.SYSTEM)
        sheep.coherence = 0.10
        sheep.state = SheepState.FROZEN

        wd = FlockWatchdog(flock, coherence_threshold=0.30)
        result = wd.tick()

        assert result["isolated"] == []
        assert sheep.state == SheepState.FROZEN

    def test_multiple_sheep_isolated(self, flock):
        """Multiple low-coherence sheep are all isolated in one tick."""
        s1 = flock.spawn("Weak1", TrainingTrack.SYSTEM)
        s2 = flock.spawn("Weak2", TrainingTrack.GOVERNANCE)
        s3 = flock.spawn("Healthy", TrainingTrack.FUNCTIONS)
        s1.coherence = 0.15
        s2.coherence = 0.25
        s3.coherence = 0.80

        wd = FlockWatchdog(flock, coherence_threshold=0.30)
        result = wd.tick()

        assert s1.sheep_id in result["isolated"]
        assert s2.sheep_id in result["isolated"]
        assert s3.sheep_id not in result["isolated"]

    def test_custom_threshold(self, flock):
        """Custom coherence threshold is respected."""
        sheep = flock.spawn("Marginal", TrainingTrack.SYSTEM)
        sheep.coherence = 0.45

        wd = FlockWatchdog(flock, coherence_threshold=0.50)
        result = wd.tick()

        assert sheep.sheep_id in result["isolated"]

    def test_watchdog_logs_isolation_event(self, flock):
        """Watchdog records event log entry for auto-isolation."""
        sheep = flock.spawn("LogTest", TrainingTrack.SYSTEM)
        sheep.coherence = 0.10

        wd = FlockWatchdog(flock, coherence_threshold=0.30)
        wd.tick()

        watchdog_events = flock.events.by_type("watchdog_action")
        isolation_events = [
            e for e in watchdog_events
            if e.details.get("action") == "auto_isolate"
        ]
        assert len(isolation_events) >= 1
        assert isolation_events[0].sheep_id == sheep.sheep_id


# ===========================================================================
# 2. FlockWatchdog — Auto-retire stuck sheep
# ===========================================================================


class TestWatchdogAutoRetire:
    """Watchdog should auto-retire sheep stuck in ISOLATED state too long."""

    def test_retire_after_timeout(self, flock):
        """Sheep isolated beyond timeout gets auto-retired."""
        sheep = flock.spawn("StuckAgent", TrainingTrack.SYSTEM)
        sheep.coherence = 0.10
        sheep.state = SheepState.ISOLATED
        sheep_id = sheep.sheep_id

        wd = FlockWatchdog(flock, isolation_timeout=60.0)
        # First tick at t=0
        wd.tick(now=1000.0)
        assert sheep_id in flock.sheep  # Still present

        # Second tick at t=61 (past timeout)
        wd.tick(now=1061.0)
        assert sheep_id not in flock.sheep  # Retired

    def test_not_retired_before_timeout(self, flock):
        """Sheep is NOT retired before timeout expires."""
        sheep = flock.spawn("PendingAgent", TrainingTrack.SYSTEM)
        sheep.coherence = 0.10
        sheep.state = SheepState.ISOLATED
        sheep_id = sheep.sheep_id

        wd = FlockWatchdog(flock, isolation_timeout=300.0)
        wd.tick(now=1000.0)
        wd.tick(now=1100.0)  # 100s < 300s

        assert sheep_id in flock.sheep

    def test_recovered_sheep_not_retired(self, flock):
        """Sheep that recovers from ISOLATED state is not retired."""
        sheep = flock.spawn("RecoverAgent", TrainingTrack.SYSTEM)
        sheep.coherence = 0.10
        sheep.state = SheepState.ISOLATED
        sheep_id = sheep.sheep_id

        wd = FlockWatchdog(flock, isolation_timeout=60.0)
        wd.tick(now=1000.0)

        # Sheep recovers
        sheep.coherence = 0.80
        sheep.state = SheepState.ACTIVE

        wd.tick(now=1100.0)  # Past timeout, but sheep recovered
        assert sheep_id in flock.sheep
        assert sheep.state == SheepState.ACTIVE

    def test_retire_logs_event(self, flock):
        """Auto-retirement logs a watchdog_action event."""
        sheep = flock.spawn("RetireLog", TrainingTrack.SYSTEM)
        sheep.coherence = 0.10
        sheep.state = SheepState.ISOLATED
        sheep_id = sheep.sheep_id

        wd = FlockWatchdog(flock, isolation_timeout=10.0)
        wd.tick(now=1000.0)
        wd.tick(now=1011.0)

        watchdog_events = flock.events.by_type("watchdog_action")
        retire_events = [
            e for e in watchdog_events
            if e.details.get("action") == "auto_retire"
        ]
        assert len(retire_events) >= 1
        assert retire_events[0].sheep_id == sheep_id


# ===========================================================================
# 3. Task Rebalancing on Sheep Failure
# ===========================================================================


class TestTaskRebalancing:
    """Tasks from failed sheep should be rebalanced to healthy sheep."""

    def test_rebalance_from_failed_sheep(self, flock):
        """Tasks owned by a failed sheep are reassigned to healthy ones."""
        sick = flock.spawn("SickExec", TrainingTrack.FUNCTIONS, SheepRole.EXECUTOR)
        healthy = flock.spawn("HealthyExec", TrainingTrack.FUNCTIONS, SheepRole.EXECUTOR)

        task = flock.add_task("Process data", TrainingTrack.FUNCTIONS)
        flock.assign_task(task.task_id, sick.sheep_id)
        assert task.status == "active"
        assert task.owner == sick.sheep_id

        # Sick sheep fails
        sick.state = SheepState.ISOLATED
        reassigned = flock.rebalance_from_failed(sick.sheep_id)

        assert reassigned == 1
        assert task.owner == healthy.sheep_id
        assert task.status == "active"

    def test_rebalance_no_healthy_sheep(self, flock):
        """Rebalancing with no healthy sheep leaves tasks orphaned."""
        sole = flock.spawn("OnlyAgent", TrainingTrack.FUNCTIONS, SheepRole.EXECUTOR)
        task = flock.add_task("Lonely task", TrainingTrack.FUNCTIONS)
        flock.assign_task(task.task_id, sole.sheep_id)

        sole.state = SheepState.ISOLATED
        reassigned = flock.rebalance_from_failed(sole.sheep_id)

        assert reassigned == 0
        # Task should be orphaned since no one can take it
        assert task.status in ("pending", "orphaned")

    def test_watchdog_rebalances_on_retire(self, flock):
        """Watchdog auto-retire also rebalances tasks."""
        sick = flock.spawn("SickW", TrainingTrack.FUNCTIONS, SheepRole.EXECUTOR)
        healthy = flock.spawn("HealthyW", TrainingTrack.FUNCTIONS, SheepRole.EXECUTOR)

        task = flock.add_task("Rebalance me", TrainingTrack.FUNCTIONS)
        flock.assign_task(task.task_id, sick.sheep_id)

        sick.coherence = 0.05
        sick.state = SheepState.ISOLATED

        wd = FlockWatchdog(flock, isolation_timeout=10.0)
        wd.tick(now=1000.0)
        result = wd.tick(now=1011.0)

        assert sick.sheep_id in result["retired"]
        assert result["rebalanced"] >= 1


# ===========================================================================
# 4. Health Report Generation
# ===========================================================================


class TestHealthReport:
    """flock_health_report() should return structured health data."""

    def test_empty_flock_report(self, flock):
        """Empty flock produces a valid report with score=0."""
        report = flock.flock_health_report()

        assert report["flock_health_score"] == 0.0
        assert report["per_sheep"] == []
        assert "Flock is empty" in report["recommendations"][0]

    def test_healthy_flock_score(self, populated_flock):
        """A fully healthy flock should have score close to 1.0."""
        report = populated_flock.flock_health_report()

        assert report["flock_health_score"] > 0.9
        assert len(report["per_sheep"]) == 7

    def test_degraded_flock_score(self, flock):
        """Degraded sheep lowers flock health score."""
        for i in range(4):
            s = flock.spawn(f"Agent{i}", TrainingTrack.SYSTEM)
            s.coherence = 0.40  # Below HEALTHY

        report = flock.flock_health_report()
        assert report["flock_health_score"] < 0.7

    def test_per_sheep_detail(self, flock):
        """Per-sheep data includes all expected fields."""
        sheep = flock.spawn("DetailAgent", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)

        report = flock.flock_health_report()
        detail = report["per_sheep"][0]

        assert detail["sheep_id"] == sheep.sheep_id
        assert detail["name"] == "DetailAgent"
        assert detail["role"] == "validator"
        assert detail["state"] == "active"
        assert "coherence" in detail
        assert "health_label" in detail
        assert "error_rate" in detail

    def test_task_stats(self, flock):
        """Task stats correctly count completed/failed/pending."""
        agent = flock.spawn("Worker", TrainingTrack.SYSTEM)

        t1 = flock.add_task("Task A")
        t2 = flock.add_task("Task B")
        t3 = flock.add_task("Task C")

        flock.assign_task(t1.task_id)
        flock.complete_task(t1.task_id, success=True)
        flock.assign_task(t2.task_id)
        flock.complete_task(t2.task_id, success=False)
        # t3 remains pending

        report = flock.flock_health_report()
        ts = report["task_stats"]

        assert ts["completed"] == 1
        assert ts["failed"] == 1
        assert ts["pending"] == 1
        assert 0.0 <= ts["success_rate"] <= 1.0

    def test_bft_status(self, populated_flock):
        """BFT section of health report shows quorum and tolerance."""
        report = populated_flock.flock_health_report()
        bft = report["bft"]

        assert "quorum_met" in bft
        assert "tolerance" in bft
        assert "active_non_frozen" in bft
        assert bft["active_non_frozen"] == 7
        assert bft["tolerance"] == 2  # (7-1)//3 = 2

    def test_bft_quorum_recommendation(self, flock):
        """Report recommends more sheep when BFT quorum not met."""
        # Only 3 sheep -> f=(3-1)//3=0
        for i in range(3):
            flock.spawn(f"Small{i}", TrainingTrack.SYSTEM)

        report = flock.flock_health_report()
        assert any("Spawn" in r for r in report["recommendations"])

    def test_isolated_sheep_recommendation(self, flock):
        """Report recommends action when sheep are isolated."""
        sheep = flock.spawn("IsoAgent", TrainingTrack.SYSTEM)
        sheep.state = SheepState.ISOLATED

        report = flock.flock_health_report()
        assert any("isolated" in r.lower() for r in report["recommendations"])


# ===========================================================================
# 5. FlockEventLog — Recording and Querying
# ===========================================================================


class TestFlockEventLog:
    """FlockEventLog should record and query events correctly."""

    def test_record_event(self, event_log):
        """Record creates an event with correct fields."""
        evt = event_log.record("spawn", "sheep-abc", {"name": "TestAgent"})

        assert evt.event_type == "spawn"
        assert evt.sheep_id == "sheep-abc"
        assert evt.details["name"] == "TestAgent"
        assert evt.timestamp > 0
        assert evt.event_id.startswith("evt-")

    def test_all_events(self, event_log):
        """all() returns all recorded events."""
        event_log.record("spawn", "s1")
        event_log.record("retire", "s2")
        event_log.record("spawn", "s3")

        assert len(event_log.all()) == 3

    def test_by_type(self, event_log):
        """by_type() filters correctly."""
        event_log.record("spawn", "s1")
        event_log.record("retire", "s2")
        event_log.record("spawn", "s3")
        event_log.record("isolate", "s1")

        spawns = event_log.by_type("spawn")
        assert len(spawns) == 2
        assert all(e.event_type == "spawn" for e in spawns)

    def test_by_sheep(self, event_log):
        """by_sheep() filters correctly."""
        event_log.record("spawn", "sheep-a")
        event_log.record("isolate", "sheep-a")
        event_log.record("spawn", "sheep-b")

        a_events = event_log.by_sheep("sheep-a")
        assert len(a_events) == 2
        assert all(e.sheep_id == "sheep-a" for e in a_events)

    def test_by_time_range(self, event_log):
        """by_time_range() filters events within time bounds."""
        now = time.time()
        e1 = event_log.record("spawn", "s1")
        e1.timestamp = now - 100
        e2 = event_log.record("retire", "s2")
        e2.timestamp = now - 50
        e3 = event_log.record("spawn", "s3")
        e3.timestamp = now - 10

        result = event_log.by_time_range(now - 60, now - 5)
        assert len(result) == 2

    def test_count(self, event_log):
        """count() returns correct totals."""
        event_log.record("spawn", "s1")
        event_log.record("spawn", "s2")
        event_log.record("retire", "s1")

        assert event_log.count() == 3
        assert event_log.count("spawn") == 2
        assert event_log.count("retire") == 1
        assert event_log.count("nonexistent") == 0

    def test_latest(self, event_log):
        """latest() returns the most recent N events."""
        for i in range(20):
            event_log.record("tick", f"s{i}")

        latest = event_log.latest(5)
        assert len(latest) == 5

    def test_len(self, event_log):
        """__len__ works."""
        assert len(event_log) == 0
        event_log.record("test", "s1")
        assert len(event_log) == 1

    def test_flock_integration(self, flock):
        """Flock operations record events in the FlockEventLog."""
        s1 = flock.spawn("EventAgent", TrainingTrack.SYSTEM)
        flock.isolate(s1.sheep_id)
        flock.retire(s1.sheep_id)

        assert flock.events.count("spawn") >= 1
        assert flock.events.count("isolate") >= 1
        assert flock.events.count("retire") >= 1

    def test_task_events_recorded(self, flock):
        """Task creation and assignment record events."""
        agent = flock.spawn("TaskEvtAgent", TrainingTrack.SYSTEM)
        task = flock.add_task("Event task")
        flock.assign_task(task.task_id)

        assert flock.events.count("task_create") >= 1
        assert flock.events.count("task_assign") >= 1


# ===========================================================================
# 6. Retry Logic
# ===========================================================================


class TestRetryLogic:
    """Retry with exponential backoff for task assignment."""

    def test_retry_with_backoff_success(self):
        """_retry_with_backoff succeeds when function works on first try."""
        result = _retry_with_backoff(lambda: 42, max_retries=3, base_delay=0.01)
        assert result == 42

    def test_retry_with_backoff_eventual_success(self):
        """_retry_with_backoff retries until success."""
        attempts = {"count": 0}

        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("Not yet")
            return "success"

        result = _retry_with_backoff(flaky, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert attempts["count"] == 3

    def test_retry_with_backoff_exhausted(self):
        """_retry_with_backoff raises after max retries."""
        def always_fail():
            raise ValueError("permanent failure")

        with pytest.raises(ValueError, match="permanent failure"):
            _retry_with_backoff(always_fail, max_retries=3, base_delay=0.01)

    def test_retry_logs_events(self):
        """_retry_with_backoff records retry events in event log."""
        log = FlockEventLog()
        attempts = {"count": 0}

        def fail_twice():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("Transient")
            return "ok"

        _retry_with_backoff(
            fail_twice,
            max_retries=3,
            base_delay=0.01,
            event_log=log,
            context="test_retry",
        )
        retry_events = log.by_type("retry")
        assert len(retry_events) == 2  # Failed twice before succeeding

    def test_assign_task_with_retry_success(self, flock):
        """assign_task_with_retry succeeds when agent is available."""
        agent = flock.spawn("RetryAgent", TrainingTrack.SYSTEM)
        task = flock.add_task("Retry task")

        result = flock.assign_task_with_retry(
            task.task_id, max_retries=3, base_delay=0.01
        )
        assert result is True
        assert task.status == "active"

    def test_assign_task_with_retry_no_agents(self, flock):
        """assign_task_with_retry returns False when no agents available."""
        task = flock.add_task("Lonely task")

        result = flock.assign_task_with_retry(
            task.task_id, max_retries=2, base_delay=0.01
        )
        assert result is False

    def test_assign_task_with_retry_fallback(self, flock):
        """assign_task_with_retry falls back to auto-select on bad sheep_id."""
        bad_id = "sheep-nonexistent"
        agent = flock.spawn("FallbackAgent", TrainingTrack.SYSTEM)
        task = flock.add_task("Fallback task")

        result = flock.assign_task_with_retry(
            task.task_id,
            sheep_id=bad_id,
            max_retries=3,
            base_delay=0.01,
        )
        # Should eventually auto-select the available agent
        assert result is True
        assert task.owner == agent.sheep_id


# ===========================================================================
# 7. Graceful BFT Degradation
# ===========================================================================


class TestBFTDegradation:
    """BFT quorum loss should degrade gracefully, not crash."""

    def test_vote_no_validators(self, flock):
        """Voting with no validators returns QUARANTINE and bft_degraded flag."""
        flock.spawn("Leader", TrainingTrack.SYSTEM, SheepRole.LEADER)

        result = flock.vote_on_action("deploy_model")
        assert result["consensus"] == "QUARANTINE"
        assert result.get("bft_degraded") is True

    def test_vote_insufficient_validators(self, flock):
        """Voting with <4 validators sets bft_degraded flag."""
        # Only 2 validators -> f=0, degraded
        flock.spawn("V1", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)
        flock.spawn("V2", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)

        result = flock.vote_on_action("process_data")
        assert result.get("bft_degraded") is True
        # Should still produce a consensus (not crash)
        assert result["consensus"] in ("ALLOW", "QUARANTINE", "DENY")

    def test_vote_with_quorum(self, populated_flock):
        """Voting with sufficient validators reports bft_degraded=False."""
        result = populated_flock.vote_on_action("safe_action")
        assert result.get("bft_degraded") is False
        assert result["consensus"] in ("ALLOW", "QUARANTINE", "DENY")

    def test_bft_quorum_met_property(self, populated_flock):
        """bft_quorum_met property correctly reports quorum status."""
        assert populated_flock.bft_quorum_met is True

    def test_bft_quorum_not_met(self, flock):
        """Small flock does not meet BFT quorum."""
        flock.spawn("Solo", TrainingTrack.SYSTEM)
        assert flock.bft_quorum_met is False

    def test_bft_degradation_logs_warning(self, flock):
        """BFT degradation records a bft_warning event."""
        flock.spawn("V1", TrainingTrack.GOVERNANCE, SheepRole.VALIDATOR)
        flock.vote_on_action("risky_action")

        warnings = flock.events.by_type("bft_warning")
        assert len(warnings) >= 1

    def test_vote_records_event(self, populated_flock):
        """Voting records a vote event in the event log."""
        populated_flock.vote_on_action("test_vote")
        vote_events = populated_flock.events.by_type("vote")
        assert len(vote_events) >= 1


# ===========================================================================
# 8. Complete Task Method
# ===========================================================================


class TestCompleteTask:
    """Flock.complete_task() should update task and sheep state."""

    def test_complete_task_success(self, flock):
        """Successful completion updates task and sheep."""
        agent = flock.spawn("CompAgent", TrainingTrack.SYSTEM)
        task = flock.add_task("Complete me")
        flock.assign_task(task.task_id)

        result = flock.complete_task(task.task_id, success=True)
        assert result is True
        assert task.status == "completed"
        assert agent.tasks_completed == 1

    def test_complete_task_failure(self, flock):
        """Failed completion updates task and sheep."""
        agent = flock.spawn("FailAgent", TrainingTrack.SYSTEM)
        task = flock.add_task("Fail me")
        flock.assign_task(task.task_id)

        result = flock.complete_task(task.task_id, success=False)
        assert result is True
        assert task.status == "failed"
        assert agent.tasks_failed == 1

    def test_complete_nonexistent_task(self, flock):
        """Completing a nonexistent task returns False."""
        assert flock.complete_task("task-nonexistent") is False

    def test_complete_logs_event(self, flock):
        """Task completion records a task_complete event."""
        agent = flock.spawn("LogComp", TrainingTrack.SYSTEM)
        task = flock.add_task("Log task")
        flock.assign_task(task.task_id)
        flock.complete_task(task.task_id)

        complete_events = flock.events.by_type("task_complete")
        assert len(complete_events) >= 1


# ===========================================================================
# 9. Backward Compatibility
# ===========================================================================


class TestBackwardCompatibility:
    """Existing Flock API should continue to work unchanged."""

    def test_spawn_and_retire(self, flock):
        sheep = flock.spawn("Compat", TrainingTrack.SYSTEM)
        assert sheep.sheep_id in flock.sheep
        assert flock.retire(sheep.sheep_id) is True
        assert sheep.sheep_id not in flock.sheep

    def test_isolate(self, flock):
        sheep = flock.spawn("IsoCompat", TrainingTrack.SYSTEM)
        assert flock.isolate(sheep.sheep_id) is True
        assert sheep.state == SheepState.ISOLATED

    def test_add_and_assign_task(self, flock):
        flock.spawn("Worker", TrainingTrack.SYSTEM)
        task = flock.add_task("Test task")
        assert flock.assign_task(task.task_id) is True
        assert task.status == "active"

    def test_health_check(self, flock):
        flock.spawn("HC", TrainingTrack.SYSTEM)
        hc = flock.health_check()
        assert "total" in hc
        assert "avg_coherence" in hc
        assert "bft_tolerance" in hc

    def test_status_dashboard(self, flock):
        flock.spawn("Dash", TrainingTrack.SYSTEM)
        dash = flock.status_dashboard()
        assert "FLOCK STATUS" in dash

    def test_event_log_legacy(self, flock):
        flock.spawn("Legacy", TrainingTrack.SYSTEM)
        assert len(flock.event_log) >= 1

    def test_vote_on_action(self, populated_flock):
        result = populated_flock.vote_on_action("compat_test")
        assert "consensus" in result
        assert "votes" in result

    def test_bft_tolerance(self, populated_flock):
        assert populated_flock.bft_tolerance == 2


# ===========================================================================
# 10. Watchdog Background Thread
# ===========================================================================


class TestWatchdogThread:
    """Watchdog background thread starts and stops cleanly."""

    def test_start_stop(self, flock):
        """Watchdog thread can be started and stopped."""
        wd = FlockWatchdog(flock, scan_interval=0.1)
        wd.start()
        assert wd.is_running is True
        time.sleep(0.15)
        wd.stop()
        assert wd.is_running is False

    def test_double_start(self, flock):
        """Calling start() twice does not create duplicate threads."""
        wd = FlockWatchdog(flock, scan_interval=0.1)
        wd.start()
        wd.start()  # Should be a no-op
        assert wd.is_running is True
        wd.stop()
