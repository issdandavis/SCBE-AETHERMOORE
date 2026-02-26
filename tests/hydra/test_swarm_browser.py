"""
Tests for HYDRA Swarm Browser -- 6-Agent Sacred Tongue Orchestrator.
=====================================================================

Covers:
- SwarmBrowser construction and defaults
- Agent definitions (6 tongues, correct roles/phases)
- Dry-run launch and shutdown lifecycle
- execute_task in dry-run mode
- _select_tongue action routing
- get_status returns expected keys
- Convenience methods (navigate, screenshot, get_content)
- Consensus check for high-sensitivity actions
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.swarm_browser import SwarmBrowser, AGENTS, HIGH_SENSITIVITY_ACTIONS


# =========================================================================
# Agent definitions
# =========================================================================


class TestAgentDefinitions:
    """The 6 Sacred Tongue agents are correctly defined."""

    def test_six_agents_defined(self):
        assert len(AGENTS) == 6

    def test_all_tongues_present(self):
        expected = {"KO", "AV", "RU", "CA", "UM", "DR"}
        assert set(AGENTS.keys()) == expected

    def test_each_agent_has_role(self):
        for tongue, spec in AGENTS.items():
            assert "role" in spec, f"{tongue} missing 'role'"
            assert isinstance(spec["role"], str)

    def test_each_agent_has_phase(self):
        for tongue, spec in AGENTS.items():
            assert "phase" in spec, f"{tongue} missing 'phase'"
            assert isinstance(spec["phase"], (int, float))

    def test_each_agent_has_actions(self):
        for tongue, spec in AGENTS.items():
            assert "actions" in spec, f"{tongue} missing 'actions'"
            assert isinstance(spec["actions"], list)
            assert len(spec["actions"]) > 0

    def test_role_assignments(self):
        assert AGENTS["KO"]["role"] == "scout"
        assert AGENTS["AV"]["role"] == "vision"
        assert AGENTS["RU"]["role"] == "reader"
        assert AGENTS["CA"]["role"] == "clicker"
        assert AGENTS["UM"]["role"] == "typer"
        assert AGENTS["DR"]["role"] == "judge"

    def test_phases_are_60_degree_steps(self):
        """Phases should be 0, 60, 120, 180, 240, 300."""
        phases = sorted(spec["phase"] for spec in AGENTS.values())
        assert phases == [0, 60, 120, 180, 240, 300]


# =========================================================================
# High-sensitivity action set
# =========================================================================


class TestHighSensitivityActions:
    """Actions that require Roundtable consensus."""

    def test_click_is_high_sensitivity(self):
        assert "click" in HIGH_SENSITIVITY_ACTIONS

    def test_type_is_high_sensitivity(self):
        assert "type" in HIGH_SENSITIVITY_ACTIONS

    def test_submit_is_high_sensitivity(self):
        assert "submit" in HIGH_SENSITIVITY_ACTIONS

    def test_navigate_is_not_high_sensitivity(self):
        assert "navigate" not in HIGH_SENSITIVITY_ACTIONS

    def test_screenshot_is_not_high_sensitivity(self):
        assert "screenshot" not in HIGH_SENSITIVITY_ACTIONS


# =========================================================================
# Constructor
# =========================================================================


class TestSwarmBrowserConstructor:
    """SwarmBrowser initialization and defaults."""

    def test_defaults(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm.provider_type == "local"
        assert swarm.model == "local-model"
        assert swarm.backend_type == "playwright"
        assert swarm.headless is True
        assert swarm.dry_run is True
        assert swarm._launched is False

    def test_custom_provider(self):
        swarm = SwarmBrowser(provider_type="hf", model="my-model", dry_run=True)
        assert swarm.provider_type == "hf"
        assert swarm.model == "my-model"

    def test_initial_state_empty(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm.heads == {}
        assert swarm.tab_ids == {}
        assert swarm.governance is None
        assert swarm.roundtable is None


# =========================================================================
# Dry-run lifecycle
# =========================================================================


class TestDryRunLifecycle:
    """Launch and shutdown in dry-run mode (no real browser)."""

    @pytest.mark.asyncio
    async def test_launch_creates_six_heads(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        try:
            assert swarm._launched is True
            assert len(swarm.heads) == 6
            assert set(swarm.heads.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_launch_initializes_governance(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        try:
            assert swarm.governance is not None
            assert swarm.roundtable is not None
            assert swarm.ledger is not None
            assert swarm.librarian is not None
            assert swarm.spine is not None
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_launch_is_idempotent(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        head_ids_1 = {t: h.head_id for t, h in swarm.heads.items()}
        await swarm.launch()  # second call should be a no-op
        head_ids_2 = {t: h.head_id for t, h in swarm.heads.items()}
        assert head_ids_1 == head_ids_2
        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_clears_launched_flag(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        assert swarm._launched is True
        await swarm.shutdown()
        assert swarm._launched is False

    @pytest.mark.asyncio
    async def test_dry_run_no_browser(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        assert swarm.browser is None
        assert swarm.tab_ids == {}
        await swarm.shutdown()


# =========================================================================
# _select_tongue routing
# =========================================================================


class TestSelectTongue:
    """Action-to-tongue routing."""

    def test_navigate_routes_to_ko(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("navigate") == "KO"

    def test_screenshot_routes_to_av(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("screenshot") == "AV"

    def test_get_content_routes_to_ru(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("get_content") == "RU"

    def test_click_routes_to_ca(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("click") == "CA"

    def test_type_routes_to_um(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("type") == "UM"

    def test_verify_routes_to_dr(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("verify") == "DR"

    def test_scroll_routes_to_ko(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("scroll") == "KO"

    def test_unknown_defaults_to_ko(self):
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._select_tongue("unknown_action") == "KO"


# =========================================================================
# Dry-run dispatch
# =========================================================================


class TestDryRunDispatch:
    """Actions dispatched in dry-run mode return mock results."""

    @pytest.mark.asyncio
    async def test_dispatch_returns_dry_run_result(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        result = await swarm._dispatch("KO", "navigate", "https://example.com", {})
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["action"] == "navigate"
        assert result["target"] == "https://example.com"
        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_dispatch_all_tongues_work(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        for tongue in AGENTS:
            result = await swarm._dispatch(tongue, "test_action", "target", {})
            assert result["success"] is True
            assert result["tongue"] == tongue
        await swarm.shutdown()


# =========================================================================
# execute_task (dry-run)
# =========================================================================


class TestExecuteTask:
    """Task execution in dry-run mode."""

    @pytest.mark.asyncio
    async def test_execute_task_basic(self):
        swarm = SwarmBrowser(dry_run=True)
        result = await swarm.execute_task("search for SCBE on GitHub")
        assert "task" in result
        assert result["task"] == "search for SCBE on GitHub"
        assert "total_steps" in result
        assert result["total_steps"] >= 1
        assert "results" in result
        assert isinstance(result["results"], list)
        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_execute_task_auto_launches(self):
        """execute_task should auto-launch if not yet launched."""
        swarm = SwarmBrowser(dry_run=True)
        assert swarm._launched is False
        await swarm.execute_task("test")
        assert swarm._launched is True
        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_execute_task_fallback_plan(self):
        """Without an LLM, plan falls back to single navigate action."""
        swarm = SwarmBrowser(dry_run=True)
        result = await swarm.execute_task("navigate to example.com")
        # Should have at least 1 step (the fallback navigate)
        assert result["total_steps"] >= 1
        steps = result["results"]
        assert steps[0]["action"] == "navigate"
        await swarm.shutdown()


# =========================================================================
# get_status
# =========================================================================


class TestGetStatus:
    """Swarm status reporting."""

    @pytest.mark.asyncio
    async def test_status_keys(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        status = swarm.get_status()
        assert "launched" in status
        assert "agents" in status
        assert "tabs" in status
        assert "provider" in status
        assert "model" in status
        assert "dry_run" in status
        assert "governance" in status
        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_status_agents_list(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        status = swarm.get_status()
        assert set(status["agents"]) == {"KO", "AV", "RU", "CA", "UM", "DR"}
        assert status["launched"] is True
        assert status["dry_run"] is True
        await swarm.shutdown()

    def test_status_before_launch(self):
        swarm = SwarmBrowser(dry_run=True)
        status = swarm.get_status()
        assert status["launched"] is False
        assert status["agents"] == []


# =========================================================================
# Convenience methods (dry-run)
# =========================================================================


class TestConvenienceMethods:
    """Quick-access methods in dry-run mode."""

    @pytest.mark.asyncio
    async def test_navigate_convenience(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        result = await swarm.navigate("https://example.com")
        assert result["success"] is True
        assert result["action"] == "navigate"
        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_screenshot_convenience(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        result = await swarm.screenshot()
        assert result["success"] is True
        assert result["action"] == "screenshot"
        await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_get_content_convenience(self):
        swarm = SwarmBrowser(dry_run=True)
        await swarm.launch()
        result = await swarm.get_content()
        assert result["success"] is True
        assert result["action"] == "get_content"
        await swarm.shutdown()
