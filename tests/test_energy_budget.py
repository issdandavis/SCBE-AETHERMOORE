"""Tests for the Energy-Bounded Agent Lifecycle — optimal foraging in governance space."""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from symphonic_cipher.scbe_aethermoore.energy_budget import (
    EnergyBoundedAgent,
    EnergyLedger,
    EnergyPhase,
    FleetEnergyManager,
    TONGUE_WEIGHTS,
    harmonic_cost,
)
from symphonic_cipher.scbe_aethermoore.flock_shepherd import (
    Flock,
    SheepState,
    TrainingTrack,
)

PHI = (1 + math.sqrt(5)) / 2
PI = math.pi


# ═══════════════════════════════════════════════════
#  Harmonic Cost Function
# ═══════════════════════════════════════════════════


class TestHarmonicCost:
    def test_cost_at_centroid_is_one(self):
        """Action at the safe center should cost ~1.0 (pi^0 = 1)."""
        centroid = [0.4, 0.2, 0.5, 0.1, 0.2, 0.3]
        cost = harmonic_cost(centroid, centroid)
        assert abs(cost - 1.0) < 1e-10

    def test_cost_increases_with_distance(self):
        """Cost should increase as we move away from centroid."""
        centroid = [0.0] * 6
        cost_near = harmonic_cost([0.1] * 6, centroid)
        cost_far = harmonic_cost([0.5] * 6, centroid)
        cost_very_far = harmonic_cost([1.0] * 6, centroid)
        assert cost_near < cost_far < cost_very_far

    def test_cost_exponential_scaling(self):
        """Cost should follow pi^(phi * d*) — exponential in distance."""
        centroid = [0.0] * 6
        # At d*=1.0 (unit distance), cost should be pi^phi
        # We can't easily construct exact d*=1.0 due to phi-weighting,
        # but we can verify the formula shape
        cost = harmonic_cost([0.5] * 6, centroid)
        assert cost > 1.0  # Must be above baseline
        assert cost < PI ** (PHI * 5.0)  # Must be below max clamped value

    def test_cost_clamped_at_d_star_5(self):
        """Distance is clamped at 5.0 to prevent overflow."""
        centroid = [0.0] * 6
        cost_extreme = harmonic_cost([100.0] * 6, centroid)
        cost_clamped = PI ** (PHI * 5.0)
        assert abs(cost_extreme - cost_clamped) < 1e-6

    def test_tongue_weights_are_phi_powers(self):
        """Tongue weights should be phi^k for k in 0..5."""
        for k, w in enumerate(TONGUE_WEIGHTS):
            assert abs(w - PHI**k) < 1e-10

    def test_cost_default_centroid(self):
        """Should work with default centroid when None is passed."""
        cost = harmonic_cost([0.4, 0.2, 0.5, 0.1, 0.2, 0.3])
        assert abs(cost - 1.0) < 1e-10  # At default centroid = cost 1


# ═══════════════════════════════════════════════════
#  Energy Ledger
# ═══════════════════════════════════════════════════


class TestEnergyLedger:
    def test_empty_ledger(self):
        ledger = EnergyLedger()
        assert ledger.total_spent == 0.0
        assert ledger.action_count == 0
        assert ledger.cost_rate() == 0.0

    def test_record_entries(self):
        ledger = EnergyLedger()
        ledger.record(5.0, [0.1] * 6, "action_1")
        ledger.record(10.0, [0.2] * 6, "action_2")
        assert ledger.action_count == 2
        assert ledger.total_spent == 15.0

    def test_cost_rate(self):
        ledger = EnergyLedger()
        for i in range(5):
            ledger.record(10.0, [0.1 * i] * 6)
        assert ledger.cost_rate(window=5) == 10.0

    def test_projected_remaining(self):
        ledger = EnergyLedger()
        for _ in range(10):
            ledger.record(10.0, [0.1] * 6)
        # At rate 10.0 per action, with 100.0 remaining -> 10 actions
        assert abs(ledger.projected_remaining_actions(100.0) - 10.0) < 1e-10

    def test_projected_remaining_zero_rate(self):
        ledger = EnergyLedger()
        assert ledger.projected_remaining_actions(100.0) == float("inf")


# ═══════════════════════════════════════════════════
#  Energy-Bounded Agent
# ═══════════════════════════════════════════════════


class TestEnergyBoundedAgent:
    def test_initial_state(self):
        agent = EnergyBoundedAgent(agent_id="test-1", budget=100.0)
        assert agent.energy_remaining == 100.0
        assert agent.energy_fraction == 1.0
        assert agent.phase == EnergyPhase.PROVISIONED
        assert agent.is_alive is True

    def test_spend_reduces_energy(self):
        agent = EnergyBoundedAgent(agent_id="test-1", budget=2000.0)
        centroid = agent.centroid[:]
        # Spend at centroid — cost should be ~1.0
        receipt = agent.spend(centroid)
        assert receipt["permitted"] is True
        assert receipt["remaining"] < 2000.0
        assert receipt["cost"] > 0

    def test_phase_transitions(self):
        """Agent should transition through phases as energy depletes."""
        agent = EnergyBoundedAgent(agent_id="test-1", budget=100.0)
        assert agent.phase == EnergyPhase.PROVISIONED

        # Spend until below 75%
        far_coords = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
        while agent.energy_fraction > 0.75 and agent.is_alive:
            agent.spend(far_coords)
        if agent.is_alive:
            assert agent.phase == EnergyPhase.FORAGING

    def test_quarantine_on_depletion(self):
        """Agent should be quarantined when energy hits zero."""
        agent = EnergyBoundedAgent(agent_id="test-1", budget=50.0)
        far_coords = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
        # Spend aggressively until quarantined
        for _ in range(1000):
            receipt = agent.spend(far_coords)
            if not receipt["permitted"]:
                break
        assert agent.phase == EnergyPhase.QUARANTINED
        assert agent.is_alive is False

    def test_quarantined_agent_cannot_spend(self):
        """Once quarantined, all further actions are denied."""
        agent = EnergyBoundedAgent(agent_id="test-1", budget=10.0)
        # Drain budget
        far = [5.0] * 6
        while agent.is_alive:
            agent.spend(far)

        receipt = agent.spend([0.0] * 6)
        assert receipt["permitted"] is False
        assert receipt["reason"] == "agent_quarantined_energy_depleted"

    def test_nectar_collection(self):
        agent = EnergyBoundedAgent(agent_id="test-1", budget=2000.0)
        agent.spend(agent.centroid[:])  # one cheap action
        agent.collect_nectar(10.0)
        assert agent._nectar_collected == 10.0
        assert agent.foraging_efficiency > 0

    def test_refuel(self):
        """Governance can refuel an agent."""
        agent = EnergyBoundedAgent(agent_id="test-1", budget=100.0)
        far = [1.0] * 6
        agent.spend(far)
        spent_before = agent._spent
        agent.refuel(spent_before / 2)
        assert agent._spent < spent_before

    def test_status_report(self):
        agent = EnergyBoundedAgent(agent_id="test-1", budget=2000.0)
        agent.spend(agent.centroid[:])
        s = agent.status()
        assert s["agent_id"] == "test-1"
        assert s["budget"] == 2000.0
        assert s["is_alive"] is True
        assert "phase" in s
        assert "foraging_efficiency" in s

    def test_safe_actions_are_cheap(self):
        """Actions near centroid should cost ~1.0 — the core invariant."""
        agent = EnergyBoundedAgent(agent_id="test-1", budget=2000.0)
        # 100 safe actions at centroid should barely dent the budget
        for _ in range(100):
            agent.spend(agent.centroid[:])
        # 100 * ~1.0 = ~100 out of 2000
        assert agent.energy_remaining > 1800.0
        assert agent.phase in (EnergyPhase.PROVISIONED, EnergyPhase.FORAGING)

    def test_adversarial_paths_are_expensive(self):
        """Actions far from centroid should drain budget rapidly."""
        agent = EnergyBoundedAgent(agent_id="test-1", budget=2000.0)
        adversarial = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
        # A few adversarial actions should drain significant energy
        for _ in range(5):
            if agent.is_alive:
                agent.spend(adversarial)
        # Should have spent a LOT more than 5 * 1.0
        assert agent._spent > 50.0


# ═══════════════════════════════════════════════════
#  Fleet Energy Manager
# ═══════════════════════════════════════════════════


class TestFleetEnergyManager:
    def test_provision_agent(self):
        mgr = FleetEnergyManager(default_budget=500.0)
        agent = mgr.provision("agent-1")
        assert agent.budget == 500.0
        assert mgr.get("agent-1") is agent

    def test_provision_custom_budget(self):
        mgr = FleetEnergyManager()
        agent = mgr.provision("agent-1", budget=999.0)
        assert agent.budget == 999.0

    def test_retire_archives(self):
        mgr = FleetEnergyManager()
        mgr.provision("agent-1")
        post_mortem = mgr.retire("agent-1")
        assert post_mortem is not None
        assert post_mortem["agent_id"] == "agent-1"
        assert mgr.get("agent-1") is None

    def test_retire_nonexistent(self):
        mgr = FleetEnergyManager()
        assert mgr.retire("nope") is None

    def test_active_vs_quarantined(self):
        mgr = FleetEnergyManager(default_budget=10.0)
        a1 = mgr.provision("agent-1")
        a2 = mgr.provision("agent-2")
        # Quarantine agent-2
        far = [5.0] * 6
        while a2.is_alive:
            a2.spend(far)
        assert len(mgr.active_agents) == 1
        assert len(mgr.quarantined_agents) == 1

    def test_fleet_status(self):
        mgr = FleetEnergyManager(default_budget=1000.0)
        mgr.provision("agent-1")
        mgr.provision("agent-2")
        status = mgr.fleet_status()
        assert status["total_agents"] == 2
        assert status["active"] == 2
        assert status["total_budget"] == 2000.0

    def test_fleet_dashboard(self):
        mgr = FleetEnergyManager()
        mgr.provision("agent-1")
        mgr.provision("agent-2")
        dashboard = mgr.fleet_dashboard()
        assert "FLEET ENERGY STATUS" in dashboard
        assert "agent-1" in dashboard
        assert "agent-2" in dashboard


# ═══════════════════════════════════════════════════
#  Flock Shepherd Integration
# ═══════════════════════════════════════════════════


class TestFlockEnergyIntegration:
    def test_spawn_provisions_energy(self):
        """Spawning an agent should auto-provision energy."""
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        assert sheep.energy_agent is not None
        assert sheep.energy_agent.budget == 2000.0
        assert sheep.energy_phase == EnergyPhase.PROVISIONED

    def test_spawn_custom_budget(self):
        flock = Flock(energy_budget=500.0)
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        assert sheep.energy_agent.budget == 500.0

    def test_spawn_override_budget(self):
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM, energy_budget=100.0)
        assert sheep.energy_agent.budget == 100.0

    def test_spend_energy_via_flock(self):
        """Flock.spend_energy should deduct from the sheep's budget."""
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        coords = sheep.energy_agent.centroid[:]
        receipt = flock.spend_energy(sheep.sheep_id, coords, "test_action")
        assert receipt is not None
        assert receipt["permitted"] is True
        assert sheep.energy_remaining < 2000.0

    def test_energy_quarantine_isolates_sheep(self):
        """When energy runs out, the sheep should be isolated."""
        flock = Flock(energy_budget=10.0)
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        task = flock.add_task("Work", TrainingTrack.SYSTEM)
        flock.assign_task(task.task_id, sheep.sheep_id)

        far = [5.0] * 6
        for _ in range(100):
            receipt = flock.spend_energy(sheep.sheep_id, far)
            if receipt and not receipt["permitted"]:
                break

        assert sheep.state == SheepState.ISOLATED
        # Task should be orphaned
        assert task.status == "orphaned"

    def test_energy_in_health_check(self):
        """Health check should include energy status."""
        flock = Flock()
        flock.spawn("Alpha", TrainingTrack.SYSTEM)
        health = flock.health_check()
        assert "energy" in health
        assert health["energy"]["total_agents"] == 1

    def test_energy_in_dashboard(self):
        """Dashboard should show energy phase info."""
        flock = Flock()
        flock.spawn("Alpha", TrainingTrack.SYSTEM)
        dashboard = flock.status_dashboard()
        assert "provisioned" in dashboard  # energy phase in dashboard

    def test_complete_task_records_nectar(self):
        """Successful task completion should record nectar."""
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.FUNCTIONS)
        task = flock.add_task("Build feature", TrainingTrack.FUNCTIONS)
        flock.assign_task(task.task_id, sheep.sheep_id)
        sheep.complete_task(success=True, nectar_value=5.0)
        assert sheep.energy_agent._nectar_collected == 5.0

    def test_retire_archives_energy(self):
        """Retiring a sheep should archive its energy data."""
        flock = Flock()
        sheep = flock.spawn("Alpha", TrainingTrack.SYSTEM)
        sid = sheep.sheep_id
        flock.retire(sid)
        # Energy manager should have archived the record
        assert flock.energy_manager.get(sid) is None
        assert len(flock.energy_manager._retired) == 1

    def test_nonexistent_sheep_energy(self):
        """Spending energy on nonexistent sheep returns None."""
        flock = Flock()
        assert flock.spend_energy("fake-id", [0.0] * 6) is None

    def test_safe_foraging_loop(self):
        """An agent doing safe work should last a long time (many actions)."""
        flock = Flock(energy_budget=2000.0)
        sheep = flock.spawn("Worker", TrainingTrack.FUNCTIONS)
        centroid = sheep.energy_agent.centroid[:]

        actions = 0
        for _ in range(500):
            receipt = flock.spend_energy(sheep.sheep_id, centroid, "safe_work")
            if not receipt["permitted"]:
                break
            actions += 1

        # Safe actions cost ~1.0 each, so 500 actions < 2000 budget
        assert actions == 500
        assert sheep.energy_agent.is_alive is True

    def test_adversarial_agent_quarantined_fast(self):
        """An agent doing adversarial work should be quarantined quickly."""
        flock = Flock(energy_budget=2000.0)
        sheep = flock.spawn("Attacker", TrainingTrack.SYSTEM)
        adversarial = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]

        actions = 0
        for _ in range(500):
            receipt = flock.spend_energy(sheep.sheep_id, adversarial)
            if not receipt["permitted"]:
                break
            actions += 1

        # Adversarial actions are expensive — should be quarantined well before 500
        assert actions < 100
        assert sheep.state == SheepState.ISOLATED


# ═══════════════════════════════════════════════════
#  Optimal Foraging Invariants
# ═══════════════════════════════════════════════════


class TestForagingInvariants:
    """Tests that verify the biological foraging analogy holds mathematically."""

    def test_energy_conservation(self):
        """Total energy = spent + remaining (conservation law)."""
        agent = EnergyBoundedAgent(agent_id="bee-1", budget=1000.0)
        coords = [0.3, 0.4, 0.2, 0.5, 0.1, 0.6]
        for _ in range(50):
            if agent.is_alive:
                agent.spend(coords)
        assert abs(agent._spent + agent.energy_remaining - agent.budget) < 1e-10

    def test_efficient_forager_high_ratio(self):
        """An agent that collects lots of nectar cheaply has high efficiency."""
        agent = EnergyBoundedAgent(agent_id="bee-1", budget=2000.0)
        centroid = agent.centroid[:]
        for _ in range(10):
            agent.spend(centroid)
            agent.collect_nectar(10.0)
        eff = agent.foraging_efficiency
        assert eff > 1.0  # Collecting more value than energy spent

    def test_inefficient_forager_low_ratio(self):
        """An agent doing expensive work with little nectar has low efficiency."""
        agent = EnergyBoundedAgent(agent_id="bee-2", budget=2000.0)
        far = [2.0] * 6
        for _ in range(10):
            if agent.is_alive:
                agent.spend(far)
                agent.collect_nectar(0.1)
        eff = agent.foraging_efficiency
        assert eff < 0.01  # Spending lots of energy for little value

    def test_six_basis_vectors_span_space(self):
        """Each Sacred Tongue axis is independent — 6 basis vectors span R^6."""
        # Verify that moving along each axis independently changes cost
        centroid = [0.0] * 6
        costs = []
        for axis in range(6):
            coords = [0.0] * 6
            coords[axis] = 1.0
            costs.append(harmonic_cost(coords, centroid))
        # Each axis should give a different cost (due to phi-weighting)
        for i in range(len(costs) - 1):
            assert costs[i] != costs[i + 1], f"Axes {i} and {i+1} gave same cost"
        # Higher-indexed axes should cost more (phi^k weighting)
        for i in range(len(costs) - 1):
            assert costs[i] < costs[i + 1], f"Axis {i} should cost less than {i+1}"

    def test_lifespan_bounded_by_budget(self):
        """integral_0^T cost(t) dt <= E_total must hold."""
        agent = EnergyBoundedAgent(agent_id="bee-3", budget=500.0)
        coords = [0.5, 0.3, 0.7, 0.2, 0.4, 0.6]
        total_cost = 0.0
        while agent.is_alive:
            receipt = agent.spend(coords)
            if receipt["permitted"]:
                total_cost += receipt["cost"]
            else:
                break
        # Total cost should not exceed budget (within floating point)
        assert total_cost <= agent.budget + 1e-6
