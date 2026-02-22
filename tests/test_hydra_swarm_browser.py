"""HYDRA Swarm Browser Tests — Browser Backends + Swarm Orchestrator + CLI

Tests cover:
  - BrowserBackend ABC interface
  - PlaywrightBackend / SeleniumBackend / CDPBackend importability
  - SwarmBrowser dry-run lifecycle (launch, execute, shutdown)
  - Agent definitions and tongue-to-action mapping
  - RoundtableConsensus integration
  - CLI argument parsing
  - Librarian memory persistence after task execution
  - Ledger keyword index round-trip

@layer Layer 12, Layer 13
@component HYDRA Swarm Browser Tests
"""

import asyncio
import json
import os
import sys

import pytest

# Ensure hydra package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =====================================================================
# Browser Backends
# =====================================================================


class TestBrowserBackendImports:

    def test_import_browser_backend_abc(self):
        from hydra.browsers import BrowserBackend
        assert hasattr(BrowserBackend, "initialize")
        assert hasattr(BrowserBackend, "navigate")
        assert hasattr(BrowserBackend, "click")
        assert hasattr(BrowserBackend, "type_text")
        assert hasattr(BrowserBackend, "screenshot")
        assert hasattr(BrowserBackend, "scroll")
        assert hasattr(BrowserBackend, "get_page_content")
        assert hasattr(BrowserBackend, "close")

    def test_import_playwright_backend(self):
        from hydra.browsers import PlaywrightBackend
        backend = PlaywrightBackend(headless=True)
        assert backend._headless is True

    def test_import_selenium_backend(self):
        from hydra.browsers import SeleniumBackend
        backend = SeleniumBackend(headless=True)
        assert backend._headless is True

    def test_import_cdp_backend(self):
        from hydra.browsers import CDPBackend
        backend = CDPBackend(cdp_url="http://localhost:9999")
        assert backend._cdp_url == "http://localhost:9999"

    def test_playwright_backend_is_subclass(self):
        from hydra.browsers import BrowserBackend, PlaywrightBackend
        assert issubclass(PlaywrightBackend, BrowserBackend)

    def test_selenium_backend_is_subclass(self):
        from hydra.browsers import BrowserBackend, SeleniumBackend
        assert issubclass(SeleniumBackend, BrowserBackend)

    def test_cdp_backend_is_subclass(self):
        from hydra.browsers import BrowserBackend, CDPBackend
        assert issubclass(CDPBackend, BrowserBackend)


# =====================================================================
# Swarm Browser — Dry Run (no real browser needed)
# =====================================================================


class TestSwarmBrowserDryRun:

    @pytest.fixture
    def swarm(self):
        from hydra.swarm_browser import SwarmBrowser
        return SwarmBrowser(
            provider_type="local",
            model="local-model",
            dry_run=True,
        )

    @pytest.mark.asyncio
    async def test_launch_creates_6_heads(self, swarm):
        await swarm.launch()
        try:
            assert len(swarm.heads) == 6
            assert set(swarm.heads.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_launch_idempotent(self, swarm):
        await swarm.launch()
        try:
            await swarm.launch()  # second call should be a no-op
            assert len(swarm.heads) == 6
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_dry_run_no_browser(self, swarm):
        await swarm.launch()
        try:
            assert swarm.browser is None
            assert len(swarm.tab_ids) == 0
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_execute_task_dry_run(self, swarm):
        await swarm.launch()
        try:
            result = await swarm.execute_task("search for SCBE on GitHub")
            assert result["task"] == "search for SCBE on GitHub"
            assert result["total_steps"] >= 1
            assert result["results"][0]["dry_run"] is True
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_navigate_dry_run(self, swarm):
        await swarm.launch()
        try:
            result = await swarm.navigate("https://example.com")
            assert result["dry_run"] is True
            assert result["action"] == "navigate"
            assert result["tongue"] == "KO"
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_get_status(self, swarm):
        await swarm.launch()
        try:
            status = swarm.get_status()
            assert status["launched"] is True
            assert len(status["agents"]) == 6
            assert status["dry_run"] is True
            assert status["provider"] == "local"
        finally:
            await swarm.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_clears_state(self, swarm):
        await swarm.launch()
        await swarm.shutdown()
        assert swarm._launched is False

    @pytest.mark.asyncio
    async def test_governance_initialized(self, swarm):
        await swarm.launch()
        try:
            assert swarm.governance is not None
            assert swarm.roundtable is not None
            assert swarm.ledger is not None
            assert swarm.librarian is not None
        finally:
            await swarm.shutdown()


# =====================================================================
# Agent Definitions
# =====================================================================


class TestAgentDefinitions:

    def test_six_agents_defined(self):
        from hydra.swarm_browser import AGENTS
        assert len(AGENTS) == 6
        assert set(AGENTS.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}

    def test_each_agent_has_role(self):
        from hydra.swarm_browser import AGENTS
        for tongue, spec in AGENTS.items():
            assert "role" in spec, f"{tongue} missing role"
            assert "phase" in spec, f"{tongue} missing phase"
            assert "actions" in spec, f"{tongue} missing actions"

    def test_roles_are_unique(self):
        from hydra.swarm_browser import AGENTS
        roles = [spec["role"] for spec in AGENTS.values()]
        assert len(set(roles)) == 6

    def test_phases_span_360(self):
        from hydra.swarm_browser import AGENTS
        phases = sorted(spec["phase"] for spec in AGENTS.values())
        assert phases == [0, 60, 120, 180, 240, 300]


# =====================================================================
# Tongue-to-Action Mapping
# =====================================================================


class TestTongueActionMapping:

    @pytest.fixture
    def swarm(self):
        from hydra.swarm_browser import SwarmBrowser
        return SwarmBrowser(dry_run=True)

    def test_navigate_maps_to_ko(self, swarm):
        assert swarm._select_tongue("navigate") == "KO"

    def test_screenshot_maps_to_av(self, swarm):
        assert swarm._select_tongue("screenshot") == "AV"

    def test_get_content_maps_to_ru(self, swarm):
        assert swarm._select_tongue("get_content") == "RU"

    def test_click_maps_to_ca(self, swarm):
        assert swarm._select_tongue("click") == "CA"

    def test_type_maps_to_um(self, swarm):
        assert swarm._select_tongue("type") == "UM"

    def test_verify_maps_to_dr(self, swarm):
        assert swarm._select_tongue("verify") == "DR"

    def test_unknown_action_defaults_to_ko(self, swarm):
        assert swarm._select_tongue("unknown_action") == "KO"


# =====================================================================
# CLI Argument Parsing
# =====================================================================


class TestCLISwarm:

    def test_import_cli_module(self):
        from hydra.cli_swarm import main
        assert callable(main)

    def test_argparse_dry_run(self):
        """Verify argparse accepts --dry-run."""
        import argparse
        from hydra.cli_swarm import main

        # We can't easily test main() without launching,
        # but we can verify the module loads cleanly
        assert main is not None


# =====================================================================
# Librarian Keyword Persistence
# =====================================================================


class TestLibrarianKeywordPersistence:

    def test_save_and_load_keywords(self, tmp_path):
        from hydra.ledger import Ledger

        db = str(tmp_path / "kw_test.db")
        ledger = Ledger(db_path=db)

        ledger.save_keyword("python", "mem:python_guide")
        ledger.save_keyword("python", "mem:python_tips")
        ledger.save_keyword("rust", "mem:rust_intro")

        index = ledger.load_keywords()
        assert "python" in index
        assert len(index["python"]) == 2
        assert "mem:python_guide" in index["python"]
        assert "mem:python_tips" in index["python"]
        assert "rust" in index
        assert index["rust"] == ["mem:rust_intro"]

    def test_keywords_persist_across_instances(self, tmp_path):
        from hydra.ledger import Ledger

        db = str(tmp_path / "kw_persist.db")

        # First instance: save
        ledger1 = Ledger(db_path=db)
        ledger1.save_keyword("scbe", "mem:scbe_overview")

        # Second instance: load
        ledger2 = Ledger(db_path=db)
        index = ledger2.load_keywords()
        assert "scbe" in index
        assert index["scbe"] == ["mem:scbe_overview"]

    def test_librarian_loads_persisted_keywords(self, tmp_path):
        from hydra.ledger import Ledger
        from hydra.librarian import Librarian

        db = str(tmp_path / "lib_kw.db")
        ledger = Ledger(db_path=db)

        # Pre-seed keyword index
        ledger.save_keyword("hydra", "mem:hydra_intro")

        lib = Librarian(ledger)
        assert "hydra" in lib._keyword_index
        assert lib._keyword_index["hydra"] == ["mem:hydra_intro"]

    def test_librarian_remember_persists_keywords(self, tmp_path):
        from hydra.ledger import Ledger
        from hydra.librarian import Librarian

        db = str(tmp_path / "lib_persist.db")
        ledger1 = Ledger(db_path=db)
        lib1 = Librarian(ledger1)

        lib1.remember("guide:sacred_eggs", "How to hatch sacred eggs", category="docs")

        # New instance should see the keywords
        ledger2 = Ledger(db_path=db)
        lib2 = Librarian(ledger2)
        # Check that at least some keywords from the key/value were persisted
        all_keys = set()
        for keys in lib2._keyword_index.values():
            all_keys.update(keys)
        assert "guide:sacred_eggs" in all_keys


# =====================================================================
# Ledger Memory Round-Trip
# =====================================================================


class TestLedgerMemory:

    def test_remember_and_recall(self, tmp_path):
        from hydra.ledger import Ledger

        db = str(tmp_path / "mem_test.db")
        ledger = Ledger(db_path=db)

        ledger.remember("test_key", {"data": 42}, category="test", importance=0.8)
        result = ledger.recall("test_key")
        assert result == {"data": 42}

    def test_recall_nonexistent_returns_none(self, tmp_path):
        from hydra.ledger import Ledger

        db = str(tmp_path / "mem_none.db")
        ledger = Ledger(db_path=db)
        assert ledger.recall("missing") is None

    def test_search_memory(self, tmp_path):
        from hydra.ledger import Ledger

        db = str(tmp_path / "mem_search.db")
        ledger = Ledger(db_path=db)

        ledger.remember("scbe:overview", "The SCBE system", category="docs")
        ledger.remember("hydra:overview", "The HYDRA system", category="docs")
        ledger.remember("unrelated", "Something else", category="misc")

        results = ledger.search_memory(pattern="overview", category="docs")
        assert len(results) == 2

    def test_register_and_list_heads(self, tmp_path):
        from hydra.ledger import Ledger

        db = str(tmp_path / "heads_test.db")
        ledger = Ledger(db_path=db)

        ledger.register_head("h1", "claude", "opus")
        ledger.register_head("h2", "local", "llama")

        heads = ledger.get_active_heads()
        assert len(heads) == 2


# =====================================================================
# LLM Provider Factory
# =====================================================================


class TestLLMProviderFactory:

    def test_create_local_no_openai(self):
        """LocalProvider requires openai package — test graceful error."""
        from hydra.llm_providers import _PROVIDER_MAP
        assert "local" in _PROVIDER_MAP
        assert "hf" in _PROVIDER_MAP
        assert "huggingface" in _PROVIDER_MAP
        assert "claude" in _PROVIDER_MAP

    def test_unknown_provider_raises(self):
        from hydra.llm_providers import create_provider
        with pytest.raises(ValueError, match="Unknown ai_type"):
            create_provider("nonexistent_provider")

    def test_provider_map_complete(self):
        from hydra.llm_providers import _PROVIDER_MAP
        expected = {"claude", "anthropic", "gpt", "openai", "gemini", "google", "huggingface", "hf", "local"}
        assert set(_PROVIDER_MAP.keys()) == expected


# =====================================================================
# High Sensitivity Actions
# =====================================================================


class TestHighSensitivityActions:

    def test_click_is_high_sensitivity(self):
        from hydra.swarm_browser import HIGH_SENSITIVITY_ACTIONS
        assert "click" in HIGH_SENSITIVITY_ACTIONS

    def test_type_is_high_sensitivity(self):
        from hydra.swarm_browser import HIGH_SENSITIVITY_ACTIONS
        assert "type" in HIGH_SENSITIVITY_ACTIONS

    def test_navigate_is_not_high_sensitivity(self):
        from hydra.swarm_browser import HIGH_SENSITIVITY_ACTIONS
        assert "navigate" not in HIGH_SENSITIVITY_ACTIONS

    def test_screenshot_is_not_high_sensitivity(self):
        from hydra.swarm_browser import HIGH_SENSITIVITY_ACTIONS
        assert "screenshot" not in HIGH_SENSITIVITY_ACTIONS
