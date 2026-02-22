"""Tests for the Flock Shepherd — multi-AI fleet orchestrator."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from symphonic_cipher.scbe_aethermoore.flock_shepherd import (
    Flock,
    Sheep,
    SheepRole,
    SheepState,
    TrainingTrack,
    FlockTask,
    COHERENCE_ISOLATE,
    COHERENCE_WARN,
    COHERENCE_HEALTHY,
)


# ═══════════════════════════════════════════════════
#  Spawn & Lifecycle
# ═══════════════════════════════════════════════════

class TestSpawn:
    def test_spawn_agent(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        assert sheep.name == "Alpha"
        assert sheep.role == SheepRole.LEADER  # system -> leader
        assert sheep.state == SheepState.ACTIVE
        assert sheep.track == TrainingTrack.SYSTEM
        assert sheep.sheep_id in flock.sheep

    def test_spawn_governance_agent(self):
        flock = Flock()
        sheep = flock.spawn("Beta", TrainingTrack.GOVERNANCE)
        assert sheep.role == SheepRole.VALIDATOR

    def test_spawn_functions_agent(self):
        flock = Flock()
        sheep = flock.spawn("Gamma", TrainingTrack.FUNCTIONS)
        assert sheep.role == SheepRole.EXECUTOR

    def test_spawn_custom_role(self):
        flock = Flock()
        sheep = flock.spawn("Delta", TrainingTrack.SYSTEM, role=SheepRole.OBSERVER)
        assert sheep.role == SheepRole.OBSERVER

    def test_spawn_multiple(self):
        flock = Flock()
        for i in range(10):
            flock.spawn(f"Agent-{i}", TrainingTrack.SYSTEM)
        assert len(flock.sheep) == 10

    def test_retire_agent(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        assert flock.retire(sheep.sheep_id) is True
        assert sheep.sheep_id not in flock.sheep

    def test_retire_nonexistent(self):
        flock = Flock()
        assert flock.retire("sheep-nonexistent") is False

    def test_retire_orphans_tasks(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        task = flock.add_task("Do something", TrainingTrack.SYSTEM)
        flock.assign_task(task.task_id, sheep.sheep_id)
        assert task.status == "active"
        flock.retire(sheep.sheep_id)
        assert task.status == "orphaned"


# ═══════════════════════════════════════════════════
#  Health & Coherence
# ═══════════════════════════════════════════════════

class TestHealth:
    def test_initial_coherence(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        assert sheep.coherence == 1.0
        assert sheep.is_healthy is True

    def test_degrade(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        sheep.degrade(0.6)
        assert sheep.coherence == 0.4
        assert sheep.health_label == "WARNING"

    def test_degrade_to_isolation(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        sheep.degrade(0.8)  # drops to 0.2, below COHERENCE_ISOLATE
        assert sheep.state == SheepState.ISOLATED
        assert sheep.health_label == "CRITICAL"

    def test_recover(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        sheep.degrade(0.6)  # drops to 0.4
        sheep.recover(0.3)  # recovers to 0.7
        assert sheep.coherence == 0.7

    def test_recover_from_isolation(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        sheep.degrade(0.9)  # drops to 0.1 -> isolated
        assert sheep.state == SheepState.ISOLATED
        sheep.recover(0.5)  # recovers to 0.6 -> above WARN threshold
        assert sheep.state == SheepState.ACTIVE

    def test_coherence_bounded(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        sheep.recover(10.0)  # try to exceed 1.0
        assert sheep.coherence == 1.0
        sheep.degrade(10.0)  # try to go below 0.0
        assert sheep.coherence == 0.0

    def test_tongue_mapping(self):
        flock = Flock()
        leader = flock.spawn("L", TrainingTrack.SYSTEM)
        validator = flock.spawn("V", TrainingTrack.GOVERNANCE)
        executor = flock.spawn("E", TrainingTrack.FUNCTIONS)
        observer = flock.spawn("O", TrainingTrack.SYSTEM, role=SheepRole.OBSERVER)
        assert leader.tongue == "KO"
        assert validator.tongue == "AV"
        assert executor.tongue == "RU"
        assert observer.tongue == "UM"


# ═══════════════════════════════════════════════════
#  Task Distribution
# ═══════════════════════════════════════════════════

class TestTaskDistribution:
    def test_add_task(self):
        flock = Flock()
        task = flock.add_task("Build feature X", TrainingTrack.FUNCTIONS)
        assert task.status == "pending"
        assert task.track == TrainingTrack.FUNCTIONS

    def test_assign_task(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.FUNCTIONS)
        task = flock.add_task("Build feature X", TrainingTrack.FUNCTIONS)
        assert flock.assign_task(task.task_id, sheep.sheep_id) is True
        assert task.status == "active"
        assert task.owner == sheep.sheep_id
        assert sheep.current_task == task.task_id
        assert sheep.state == SheepState.BUSY

    def test_auto_assign(self):
        flock = Flock()
        flock.spawn("Alpha", TrainingTrack.FUNCTIONS)
        task = flock.add_task("Build feature X", TrainingTrack.FUNCTIONS)
        assert flock.assign_task(task.task_id) is True
        assert task.status == "active"

    def test_auto_assign_best_coherence(self):
        flock = Flock()
        low = flock.spawn("Low", TrainingTrack.FUNCTIONS)
        low.coherence = 0.5
        high = flock.spawn("High", TrainingTrack.FUNCTIONS)
        high.coherence = 0.9
        task = flock.add_task("Build feature X", TrainingTrack.FUNCTIONS)
        flock.assign_task(task.task_id)
        assert task.owner == high.sheep_id  # picks highest coherence

    def test_no_available_agent(self):
        flock = Flock()
        task = flock.add_task("Build feature X", TrainingTrack.FUNCTIONS)
        assert flock.assign_task(task.task_id) is False

    def test_complete_task_success(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.FUNCTIONS)
        task = flock.add_task("Build feature X", TrainingTrack.FUNCTIONS)
        flock.assign_task(task.task_id, sheep.sheep_id)
        sheep.complete_task(success=True)
        assert sheep.tasks_completed == 1
        assert sheep.current_task is None

    def test_complete_task_failure(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.FUNCTIONS)
        task = flock.add_task("Build feature X", TrainingTrack.FUNCTIONS)
        flock.assign_task(task.task_id, sheep.sheep_id)
        sheep.complete_task(success=False)
        assert sheep.tasks_failed == 1
        assert sheep.coherence < 1.0  # degraded

    def test_redistribute_orphans(self):
        flock = Flock()
        sheep1 = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        sheep2 = flock.spawn("Beta", TrainingTrack.SYSTEM)
        task = flock.add_task("Important work", TrainingTrack.SYSTEM)
        flock.assign_task(task.task_id, sheep1.sheep_id)
        flock.retire(sheep1.sheep_id)  # orphans the task
        assert task.status == "orphaned"
        reassigned = flock.redistribute_orphans()
        assert reassigned == 1
        assert task.status == "active"
        assert task.owner == sheep2.sheep_id


# ═══════════════════════════════════════════════════
#  Governance Voting
# ═══════════════════════════════════════════════════

class TestGovernanceVoting:
    def test_vote_all_healthy(self):
        flock = Flock()
        for i in range(5):
            flock.spawn(f"V-{i}", TrainingTrack.GOVERNANCE)
        result = flock.vote_on_action("Deploy v2.0")
        assert result["consensus"] == "ALLOW"
        assert len(result["votes"]) == 5
        assert all(v == "ALLOW" for v in result["votes"])

    def test_vote_mixed_health(self):
        flock = Flock()
        healthy = flock.spawn("Healthy", TrainingTrack.GOVERNANCE)
        warn = flock.spawn("Warn", TrainingTrack.GOVERNANCE)
        warn.coherence = 0.6  # below HEALTHY, above WARN
        sick = flock.spawn("Sick", TrainingTrack.GOVERNANCE)
        sick.coherence = 0.2  # below WARN
        result = flock.vote_on_action("Risky action")
        # 1 ALLOW + 1 QUARANTINE + 1 DENY = net 0 -> QUARANTINE
        assert result["consensus"] == "QUARANTINE"

    def test_vote_no_validators(self):
        flock = Flock()
        flock.spawn("Leader", TrainingTrack.SYSTEM)  # not a validator
        result = flock.vote_on_action("Something")
        assert result["consensus"] == "QUARANTINE"
        assert result["reason"] == "No active validators"

    def test_vote_balanced_ternary_packing(self):
        flock = Flock()
        for i in range(3):
            flock.spawn(f"V-{i}", TrainingTrack.GOVERNANCE)
        result = flock.vote_on_action("Test")
        assert "packed_bt" in result
        assert len(result["packed_bt"]) > 0


# ═══════════════════════════════════════════════════
#  BFT Tolerance
# ═══════════════════════════════════════════════════

class TestBFTTolerance:
    def test_bft_empty(self):
        flock = Flock()
        assert flock.bft_tolerance == 0

    def test_bft_single(self):
        flock = Flock()
        flock.spawn("A", TrainingTrack.SYSTEM)
        assert flock.bft_tolerance == 0  # (1-1)//3 = 0

    def test_bft_four_agents(self):
        flock = Flock()
        for i in range(4):
            flock.spawn(f"A-{i}", TrainingTrack.SYSTEM)
        assert flock.bft_tolerance == 1  # (4-1)//3 = 1

    def test_bft_seven_agents(self):
        flock = Flock()
        for i in range(7):
            flock.spawn(f"A-{i}", TrainingTrack.SYSTEM)
        assert flock.bft_tolerance == 2  # (7-1)//3 = 2

    def test_bft_excludes_frozen(self):
        flock = Flock()
        for i in range(7):
            flock.spawn(f"A-{i}", TrainingTrack.SYSTEM)
        # Freeze 3 agents
        agents = list(flock.sheep.values())
        for i in range(3):
            agents[i].state = SheepState.FROZEN
        assert flock.bft_tolerance == 1  # (4-1)//3 = 1


# ═══════════════════════════════════════════════════
#  Status Dashboard
# ═══════════════════════════════════════════════════

class TestStatusDashboard:
    def test_empty_flock(self):
        flock = Flock()
        dashboard = flock.status_dashboard()
        assert "Total Agents: 0" in dashboard

    def test_populated_flock(self):
        flock = Flock()
        flock.spawn("Alpha", TrainingTrack.SYSTEM)
        flock.spawn("Beta", TrainingTrack.GOVERNANCE)
        flock.spawn("Gamma", TrainingTrack.FUNCTIONS)
        dashboard = flock.status_dashboard()
        assert "Total Agents: 3" in dashboard
        assert "Alpha" in dashboard
        assert "Beta" in dashboard
        assert "Gamma" in dashboard

    def test_health_check(self):
        flock = Flock()
        flock.spawn("Alpha", TrainingTrack.SYSTEM)
        flock.spawn("Beta", TrainingTrack.GOVERNANCE)
        health = flock.health_check()
        assert health["total"] == 2
        assert health["avg_coherence"] == 1.0
        assert health["bft_tolerance"] == 0


# ═══════════════════════════════════════════════════
#  Event Log
# ═══════════════════════════════════════════════════

class TestEventLog:
    def test_spawn_logged(self):
        flock = Flock()
        flock.spawn("Alpha", TrainingTrack.SYSTEM)
        assert len(flock.event_log) == 1
        assert flock.event_log[0]["event"] == "spawn"

    def test_multiple_events(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        task = flock.add_task("Work", TrainingTrack.SYSTEM)
        flock.assign_task(task.task_id, sheep.sheep_id)
        flock.retire(sheep.sheep_id)
        assert len(flock.event_log) >= 3  # spawn + assign + retire
