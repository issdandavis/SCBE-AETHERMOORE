"""
Tests for src/kernel/agentic_sphere_grid.py
===========================================

Covers:
- SkillNode, AgentState, NeedPressure data structures
- AgenticSphereGrid engine: registration, AP economy, skill manifestation
- Governance checks, computational necessity, propagation
- Teaching, specialization analysis
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kernel.agentic_sphere_grid import (
    SkillDomain,
    ActivationTier,
    ARCHETYPES,
    AP_REWARDS,
    NEED_PRESSURE_PER_FAILURE,
    NEED_PRESSURE_TRIGGER,
    SkillNode,
    NeedPressure,
    AgentState,
    HODGE_PAIRS,
    SKILL_CATALOG,
    AgenticSphereGrid,
)
from kernel.scattered_sphere import TONGUE_WEIGHTS, TONGUE_KEYS

# ============================================================
# Enums and Constants
# ============================================================


@pytest.mark.unit
class TestEnumsAndConstants:
    def test_skill_domains_map_to_tongues(self):
        tongues = {d.value for d in SkillDomain}
        assert tongues == set(TONGUE_KEYS)

    def test_activation_tiers_ordered(self):
        assert ActivationTier.DORMANT < ActivationTier.LATENT
        assert ActivationTier.LATENT < ActivationTier.PARTIAL
        assert ActivationTier.PARTIAL < ActivationTier.CAPABLE
        assert ActivationTier.CAPABLE < ActivationTier.MASTERED

    def test_archetypes_include_blank(self):
        assert "blank" in ARCHETYPES
        assert ARCHETYPES["blank"] == {}

    def test_archetypes_include_researcher(self):
        assert "researcher" in ARCHETYPES
        assert "web_search" in ARCHETYPES["researcher"]

    def test_ap_rewards(self):
        assert AP_REWARDS["success"] > AP_REWARDS["partial"]
        assert AP_REWARDS["failure"] == 0.0

    def test_hodge_pairs_count(self):
        assert len(HODGE_PAIRS) == 6


# ============================================================
# SkillNode
# ============================================================


@pytest.mark.unit
class TestSkillNode:
    def test_effective_cost(self):
        node = SkillNode(id="test", name="Test", tongue="KO", base_cost=10.0)
        cost = node.effective_cost()
        assert cost == 10.0 * 1.0 * TONGUE_WEIGHTS["KO"]

    def test_effective_cost_with_governance(self):
        node = SkillNode(id="test", name="Test", tongue="KO", base_cost=10.0, governance_multiplier=2.0)
        cost = node.effective_cost()
        assert cost == 20.0 * TONGUE_WEIGHTS["KO"]

    def test_effective_cost_scales_with_tongue(self):
        node_ko = SkillNode(id="t1", name="T", tongue="KO", base_cost=10.0)
        node_dr = SkillNode(id="t2", name="T", tongue="DR", base_cost=10.0)
        assert node_dr.effective_cost() > node_ko.effective_cost()

    def test_tier_radius(self):
        node = SkillNode(id="test", name="Test", tongue="KO", tier=1)
        assert node.tier_radius() == 1.0
        node4 = SkillNode(id="test", name="Test", tongue="KO", tier=4)
        assert node4.tier_radius() == 0.4


# ============================================================
# NeedPressure
# ============================================================


@pytest.mark.unit
class TestNeedPressure:
    def test_initial_state(self):
        np_ = NeedPressure(skill_id="web_search")
        assert np_.pressure == 0.0
        assert np_.failure_count == 0

    def test_apply_failure(self):
        np_ = NeedPressure(skill_id="web_search")
        new_pressure = np_.apply_failure("test_task")
        assert new_pressure == NEED_PRESSURE_PER_FAILURE
        assert np_.failure_count == 1
        assert np_.context == "test_task"

    def test_cumulative_pressure(self):
        np_ = NeedPressure(skill_id="web_search")
        np_.apply_failure()
        np_.apply_failure()
        np_.apply_failure()
        assert np_.pressure == NEED_PRESSURE_PER_FAILURE * 3
        assert np_.failure_count == 3

    def test_should_trigger_review(self):
        np_ = NeedPressure(skill_id="web_search")
        assert np_.should_trigger_review() is False
        # Push past threshold
        while not np_.should_trigger_review():
            np_.apply_failure()
        assert np_.pressure >= NEED_PRESSURE_TRIGGER


# ============================================================
# AgentState
# ============================================================


@pytest.mark.unit
class TestAgentState:
    def test_activation_tier_dormant(self):
        state = AgentState(agent_id="a1")
        assert state.activation_tier("nonexistent") == ActivationTier.DORMANT

    def test_activation_tier_levels(self):
        state = AgentState(agent_id="a1", activations={"s1": 0.0, "s2": 0.15, "s3": 0.45, "s4": 0.75, "s5": 0.95})
        assert state.activation_tier("s1") == ActivationTier.DORMANT
        assert state.activation_tier("s2") == ActivationTier.LATENT
        assert state.activation_tier("s3") == ActivationTier.PARTIAL
        assert state.activation_tier("s4") == ActivationTier.CAPABLE
        assert state.activation_tier("s5") == ActivationTier.MASTERED

    def test_can_use(self):
        state = AgentState(agent_id="a1", activations={"s1": 0.29, "s2": 0.30})
        assert state.can_use("s1") is False
        assert state.can_use("s2") is True

    def test_performance_factor_below_threshold(self):
        state = AgentState(agent_id="a1", activations={"s1": 0.2})
        assert state.performance_factor("s1") == 0.0

    def test_performance_factor_at_threshold(self):
        state = AgentState(agent_id="a1", activations={"s1": 0.3})
        assert abs(state.performance_factor("s1") - 0.5) < 1e-10

    def test_performance_factor_at_mastery(self):
        state = AgentState(agent_id="a1", activations={"s1": 1.0})
        assert abs(state.performance_factor("s1") - 1.0) < 1e-10

    def test_performance_factor_midrange(self):
        state = AgentState(agent_id="a1", activations={"s1": 0.65})
        pf = state.performance_factor("s1")
        assert 0.5 < pf < 1.0


# ============================================================
# Skill Catalog
# ============================================================


@pytest.mark.unit
class TestSkillCatalog:
    def test_catalog_has_skills(self):
        assert len(SKILL_CATALOG) >= 24  # 4 tiers * 6 tongues

    def test_catalog_has_hodge_combos(self):
        hodge_skills = [s for s in SKILL_CATALOG if s.id.startswith("hodge_")]
        assert len(hodge_skills) == 6

    def test_all_skills_have_tongues(self):
        for skill in SKILL_CATALOG:
            assert skill.tongue in TONGUE_KEYS

    def test_prerequisites_are_valid_ids(self):
        all_ids = {s.id for s in SKILL_CATALOG}
        for skill in SKILL_CATALOG:
            for prereq in skill.prerequisites:
                assert prereq in all_ids, f"Prerequisite '{prereq}' not found for skill '{skill.id}'"


# ============================================================
# AgenticSphereGrid Engine
# ============================================================


@pytest.mark.integration
class TestAgenticSphereGrid:
    def test_construction(self):
        grid = AgenticSphereGrid()
        assert len(grid.nodes) > 0
        assert len(grid.agents) == 0

    def test_register_blank_agent(self):
        grid = AgenticSphereGrid()
        state = grid.register_agent("agent-1")
        assert state.agent_id == "agent-1"
        assert state.archetype == "blank"
        assert len(state.activations) == 0

    def test_register_researcher_agent(self):
        grid = AgenticSphereGrid()
        state = grid.register_agent("agent-2", archetype="researcher")
        assert state.archetype == "researcher"
        assert state.dominant_tongue == "RU"
        assert "web_search" in state.activations
        assert state.activations["web_search"] == 0.6

    def test_invalid_archetype_defaults_to_blank(self):
        grid = AgenticSphereGrid()
        state = grid.register_agent("agent-3", archetype="INVALID")
        assert state.archetype == "blank"

    def test_earn_ap(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        bank = grid.earn_ap("a1", 10.0, "test")
        assert bank == 10.0

    def test_earn_ap_unknown_agent(self):
        grid = AgenticSphereGrid()
        result = grid.earn_ap("nonexistent", 10.0, "test")
        assert result == 0.0

    def test_earn_ap_with_skill_context(self):
        grid = AgenticSphereGrid()
        state = grid.register_agent("a1", "builder")
        initial = state.activations["code_gen"]
        grid.earn_ap("a1", 10.0, "test", skill_context="code_gen")
        assert state.activations["code_gen"] > initial

    def test_spend_ap(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        grid.earn_ap("a1", 20.0, "test")
        assert grid.spend_ap("a1", 10.0) is True
        assert grid.agents["a1"].ap_bank == 10.0

    def test_spend_ap_insufficient(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        assert grid.spend_ap("a1", 10.0) is False


@pytest.mark.integration
class TestSkillManifestation:
    def test_manifest_tier1_skill(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        grid.earn_ap("a1", 100.0, "test")
        success, level, msg = grid.manifest_skill("a1", "task_dispatch", ap_investment=20.0)
        assert success is True
        assert level > 0.0

    def test_manifest_requires_prerequisites(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        grid.earn_ap("a1", 100.0, "test")
        # Tier 2 skill requires tier 1
        success, level, msg = grid.manifest_skill("a1", "formation_swap", ap_investment=20.0)
        assert success is False
        assert "Prerequisite" in msg

    def test_manifest_invalid_skill(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        success, level, msg = grid.manifest_skill("a1", "NONEXISTENT")
        assert success is False

    def test_manifest_caps_at_one(self):
        grid = AgenticSphereGrid()
        state = grid.register_agent("a1")
        state.activations["task_dispatch"] = 0.99
        grid.earn_ap("a1", 1000.0, "test")
        success, level, msg = grid.manifest_skill("a1", "task_dispatch", ap_investment=500.0)
        assert level <= 1.0


@pytest.mark.integration
class TestComputationalNecessity:
    def test_success_earns_ap(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        result = grid.computational_necessity("a1", "web_search", "success")
        assert result["ap_earned"] == AP_REWARDS["success"]

    def test_failure_earns_nothing(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        result = grid.computational_necessity("a1", "web_search", "failure")
        assert result["ap_earned"] == 0.0

    def test_failure_builds_need_pressure(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        result = grid.computational_necessity("a1", "governance_scan", "failure", needed_skills=["governance_scan"])
        assert len(result["need_pressure_applied"]) > 0

    def test_unknown_agent(self):
        grid = AgenticSphereGrid()
        result = grid.computational_necessity("nonexistent", "test", "success")
        assert "error" in result


@pytest.mark.integration
class TestTeaching:
    def test_teach_successful(self):
        grid = AgenticSphereGrid()
        teacher = grid.register_agent("teacher", "builder")
        student = grid.register_agent("student")
        teacher.activations["code_gen"] = 0.95  # mastered

        result = grid.teach("teacher", "student", "code_gen")
        assert result["success"] is True
        assert result["student_after"] > result["student_before"]

    def test_teach_requires_mastery(self):
        grid = AgenticSphereGrid()
        grid.register_agent("teacher")
        grid.register_agent("student")
        grid.agents["teacher"].activations["code_gen"] = 0.5  # not mastered

        result = grid.teach("teacher", "student", "code_gen")
        assert result["success"] is False

    def test_teach_invalid_agents(self):
        grid = AgenticSphereGrid()
        result = grid.teach("nobody", "nobody2", "code_gen")
        assert result["success"] is False


@pytest.mark.integration
class TestPropagation:
    def test_propagate_increments_tick(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        initial = grid.tick_count
        grid.propagate()
        assert grid.tick_count == initial + 1

    def test_propagate_returns_result(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1")
        result = grid.propagate()
        assert hasattr(result, "tick")
        assert hasattr(result, "fleet_coverage")


@pytest.mark.integration
class TestSpecialization:
    def test_agent_specialization(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1", "researcher")
        spec = grid.agent_specialization("a1")
        assert spec["archetype"] == "researcher"
        assert spec["dominant_tongue"] is not None

    def test_specialization_unknown_agent(self):
        grid = AgenticSphereGrid()
        result = grid.agent_specialization("nonexistent")
        assert "error" in result


@pytest.mark.integration
class TestGridSnapshot:
    def test_snapshot_structure(self):
        grid = AgenticSphereGrid()
        grid.register_agent("a1", "builder")
        grid.register_agent("a2", "guardian")
        snap = grid.grid_snapshot()
        assert snap["total_nodes"] == len(grid.nodes)
        assert snap["total_agents"] == 2
        assert "a1" in snap["agents"]
        assert "a2" in snap["agents"]
