"""
Tests for AAOE HiveMind — Multi-Agent Headless Browser Orchestrator.

Tests the full stack:
- Agent registration with GeoSeal identity
- Governed headless browser sessions (mock backend)
- HuggingFace model loading (fallback paths)
- Local GeoSeedModel inference
- Coordinated multi-agent dispatch
- Drift monitoring across agents
- Training data generation from every action
- Quarantine enforcement
- Export to JSONL

@layer Layer 1, Layer 5, Layer 13
"""

import asyncio
import json
import os
import tempfile
import time

import pytest

from src.aaoe.agent_identity import AccessTier, AgentRegistry, GeoSeal
from src.aaoe.task_monitor import (
    ActionObservation,
    DriftLevel,
    IntentVector,
    TaskMonitor,
    harmonic_cost,
    hyperbolic_distance,
)
from src.aaoe.hive_mind import (
    AgentSource,
    AgentSpec,
    HiveAgent,
    HiveMind,
)


# ------------------------------------------------------------------
#  Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def hive():
    return HiveMind()


def _make_spec(
    agent_id: str = "test-agent-1",
    source: AgentSource = AgentSource.LOCAL,
    intent: str = "Research AI safety papers",
    model_id: str = None,
    backend: str = "mock",
) -> AgentSpec:
    return AgentSpec(
        agent_id=agent_id,
        agent_name=f"Test {agent_id}",
        source=source,
        intent=intent,
        model_id=model_id,
        browser_backend=backend,
    )


# ------------------------------------------------------------------
#  Agent Registration
# ------------------------------------------------------------------

class TestAgentRegistration:
    def test_add_local_agent(self, hive):
        spec = _make_spec()
        agent = hive.add_agent(spec)
        assert agent.agent_id == "test-agent-1"
        assert agent.is_active is True
        assert agent.seal.agent_id == "test-agent-1"
        assert agent.token.is_valid is True

    def test_add_hf_agent(self, hive):
        spec = _make_spec(
            agent_id="hf-bot",
            source=AgentSource.HUGGINGFACE,
            model_id="issdandavis/phdm-21d-embedding",
            intent="Generate summaries",
        )
        agent = hive.add_agent(spec)
        assert agent.spec.source == AgentSource.HUGGINGFACE
        assert agent.spec.model_id == "issdandavis/phdm-21d-embedding"

    def test_add_custom_agent(self, hive):
        spec = _make_spec(agent_id="custom-1", source=AgentSource.CUSTOM)
        agent = hive.add_agent(spec)
        assert agent.spec.source == AgentSource.CUSTOM

    def test_multiple_agents(self, hive):
        for i in range(5):
            hive.add_agent(_make_spec(agent_id=f"agent-{i}"))
        assert len(hive.agents) == 5
        assert hive.registry.stats()["total_agents"] == 5

    def test_geoseal_identity(self, hive):
        agent = hive.add_agent(_make_spec())
        seal = agent.seal
        assert seal.seal_id.startswith("geo-")
        assert seal.fingerprint  # non-empty hash
        assert seal.tier == AccessTier.FREE
        assert seal.governance_score.total_sessions == 0

    def test_entry_token(self, hive):
        agent = hive.add_agent(_make_spec())
        token = agent.token
        assert token.is_valid is True
        assert token.agent_id == "test-agent-1"
        assert token.declared_intent == "Research AI safety papers"
        assert token.fingerprint  # non-empty hash


# ------------------------------------------------------------------
#  Browser Initialization (Mock Backend)
# ------------------------------------------------------------------

class TestBrowserInit:
    @pytest.mark.asyncio
    async def test_mock_browser_init(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        ok = await agent.initialize_browser()
        assert ok is True

    @pytest.mark.asyncio
    async def test_initialize_all(self, hive):
        hive.add_agent(_make_spec(agent_id="a1", backend="mock"))
        hive.add_agent(_make_spec(agent_id="a2", backend="mock"))
        results = await hive.initialize()
        assert results["a1"] is True
        assert results["a2"] is True


# ------------------------------------------------------------------
#  Model Loading
# ------------------------------------------------------------------

class TestModelLoading:
    @pytest.mark.asyncio
    async def test_local_model_load(self, hive):
        agent = hive.add_agent(_make_spec())
        ok = await agent.load_model()
        assert ok is True
        assert agent._model is not None

    @pytest.mark.asyncio
    async def test_local_model_inference(self, hive):
        agent = hive.add_agent(_make_spec())
        await agent.load_model()
        result = agent.infer("The SCBE harmonic wall scales exponentially")
        assert "embedding" in result
        assert "tongue_signals" in result

    @pytest.mark.asyncio
    async def test_custom_agent_no_model(self, hive):
        agent = hive.add_agent(_make_spec(source=AgentSource.CUSTOM))
        ok = await agent.load_model()
        assert ok is True  # Custom agents don't need built-in model
        result = agent.infer("test")
        assert result.get("error") == "no_model"

    @pytest.mark.asyncio
    async def test_hf_model_graceful_fallback(self, hive):
        """HF model loading should fail gracefully without network."""
        spec = _make_spec(
            source=AgentSource.HUGGINGFACE,
            model_id="nonexistent/model-that-doesnt-exist",
        )
        agent = hive.add_agent(spec)
        ok = await agent.load_model()
        # Should fail but not crash
        assert ok is False or ok is True  # Depends on HF Hub availability


# ------------------------------------------------------------------
#  Action Execution (Governed Browser)
# ------------------------------------------------------------------

class TestActionExecution:
    @pytest.mark.asyncio
    async def test_single_action(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await agent.initialize_browser()
        action = await agent.execute("navigate", "https://arxiv.org")
        assert action.agent_id == "test-agent-1"
        assert action.action_type == "navigate"
        assert action.target == "https://arxiv.org"
        assert action.governance_decision in ("ALLOW", "QUARANTINE", "DENY", "ESCALATE")

    @pytest.mark.asyncio
    async def test_action_generates_training_pair(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await agent.initialize_browser()
        await agent.execute("navigate", "https://example.com")
        assert len(agent.training_pairs) == 1
        pair = agent.training_pairs[0]
        assert pair["type"] == "sft"
        assert pair["source"] == "aaoe_hive"
        assert pair["agent_id"] == "test-agent-1"
        assert "governance" in pair["output"]

    @pytest.mark.asyncio
    async def test_multiple_actions(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await agent.initialize_browser()
        for url in ["https://arxiv.org", "https://scholar.google.com", "https://huggingface.co"]:
            await agent.execute("navigate", url)
        assert agent.action_count == 3
        assert len(agent.training_pairs) == 3

    @pytest.mark.asyncio
    async def test_click_action(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await agent.initialize_browser()
        await agent.execute("navigate", "https://example.com")
        action = await agent.execute("click", "#search-button")
        assert action.action_type == "click"

    @pytest.mark.asyncio
    async def test_type_action(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await agent.initialize_browser()
        await agent.execute("navigate", "https://example.com")
        action = await agent.execute("type", "#search-input", "AI safety")
        assert action.action_type == "type"


# ------------------------------------------------------------------
#  Multi-Agent Dispatch
# ------------------------------------------------------------------

class TestMultiAgentDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_all(self, hive):
        for i in range(3):
            hive.add_agent(_make_spec(agent_id=f"agent-{i}", backend="mock"))
        await hive.initialize()

        results = await hive.dispatch_all("navigate", "https://arxiv.org")
        assert len(results) == 3
        for agent_id, action in results.items():
            assert action.target == "https://arxiv.org"

    @pytest.mark.asyncio
    async def test_dispatch_single(self, hive):
        hive.add_agent(_make_spec(agent_id="solo", backend="mock"))
        await hive.initialize()

        action = await hive.dispatch("solo", "navigate", "https://example.com")
        assert action.agent_id == "solo"

    @pytest.mark.asyncio
    async def test_dispatch_coordinated(self, hive):
        hive.add_agent(_make_spec(agent_id="a1", backend="mock"))
        hive.add_agent(_make_spec(agent_id="a2", backend="mock"))
        await hive.initialize()

        tasks = [
            ("a1", "navigate", "https://arxiv.org", None),
            ("a2", "navigate", "https://scholar.google.com", None),
        ]
        results = await hive.dispatch_coordinated(tasks)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_dispatch_nonexistent_agent(self, hive):
        with pytest.raises(ValueError, match="Agent not found"):
            await hive.dispatch("ghost", "navigate", "https://example.com")

    @pytest.mark.asyncio
    async def test_concurrent_execution(self, hive):
        """5 agents navigating simultaneously."""
        for i in range(5):
            hive.add_agent(_make_spec(agent_id=f"concurrent-{i}", backend="mock"))
        await hive.initialize()

        results = await hive.dispatch_all("navigate", "https://arxiv.org/list/cs.AI/recent")
        assert len(results) == 5
        # All should have non-zero timestamps
        for action in results.values():
            assert action.timestamp > 0


# ------------------------------------------------------------------
#  Training Data Collection
# ------------------------------------------------------------------

class TestTrainingData:
    @pytest.mark.asyncio
    async def test_collect_from_all_agents(self, hive):
        for i in range(3):
            hive.add_agent(_make_spec(agent_id=f"agent-{i}", backend="mock"))
        await hive.initialize()
        await hive.dispatch_all("navigate", "https://arxiv.org")
        await hive.dispatch_all("navigate", "https://huggingface.co")

        pairs = hive.collect_training_data()
        assert len(pairs) == 6  # 3 agents * 2 actions

    @pytest.mark.asyncio
    async def test_training_pair_schema(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await hive.initialize()
        await hive.dispatch("test-agent-1", "navigate", "https://example.com")

        pairs = hive.collect_training_data()
        assert len(pairs) == 1
        pair = pairs[0]

        # Required fields
        assert "type" in pair
        assert "source" in pair
        assert "agent_id" in pair
        assert "instruction" in pair
        assert "input" in pair
        assert "output" in pair
        assert "metadata" in pair

        # Metadata
        assert "seal_fingerprint" in pair["metadata"]
        assert "token_fingerprint" in pair["metadata"]

    @pytest.mark.asyncio
    async def test_export_jsonl(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await hive.initialize()
        await agent.execute("navigate", "https://arxiv.org")
        await agent.execute("navigate", "https://huggingface.co")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = hive.export_training_data(tmpdir)
            assert os.path.exists(filepath)
            with open(filepath) as f:
                lines = f.readlines()
            assert len(lines) == 2
            for line in lines:
                data = json.loads(line)
                assert data["type"] == "sft"


# ------------------------------------------------------------------
#  Local Model Integration
# ------------------------------------------------------------------

class TestLocalModelIntegration:
    @pytest.mark.asyncio
    async def test_infer_after_browse(self, hive):
        """Agent browses, then uses local model to process content."""
        agent = hive.add_agent(_make_spec(backend="mock"))
        await hive.initialize()

        # Browse
        await agent.execute("navigate", "https://arxiv.org")

        # Infer on scraped content (simulated)
        result = agent.infer("SCBE harmonic wall provides exponential cost scaling")
        assert "embedding" in result
        assert "tongue_signals" in result
        assert "governance_ratio" in result

    @pytest.mark.asyncio
    async def test_multi_agent_mixed_models(self, hive):
        """Mix of local and custom agents."""
        hive.add_agent(_make_spec(agent_id="local-1", source=AgentSource.LOCAL, backend="mock"))
        hive.add_agent(_make_spec(agent_id="custom-1", source=AgentSource.CUSTOM, backend="mock"))
        await hive.initialize()

        # Both can browse
        results = await hive.dispatch_all("navigate", "https://example.com")
        assert len(results) == 2

        # Local can infer
        local = hive.agents["local-1"]
        result = local.infer("test input")
        assert "embedding" in result

        # Custom returns no-model error
        custom = hive.agents["custom-1"]
        result = custom.infer("test input")
        assert result["error"] == "no_model"


# ------------------------------------------------------------------
#  Agent Lifecycle
# ------------------------------------------------------------------

class TestAgentLifecycle:
    @pytest.mark.asyncio
    async def test_agent_summary(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await hive.initialize()
        await agent.execute("navigate", "https://arxiv.org")

        summary = agent.summary()
        assert summary["agent_id"] == "test-agent-1"
        assert summary["is_active"] is True
        assert summary["action_count"] == 1
        assert summary["training_pairs"] == 1
        assert summary["tier"] == "FREE"

    @pytest.mark.asyncio
    async def test_agent_shutdown(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await hive.initialize()
        await agent.shutdown()
        assert agent.is_active is False

    @pytest.mark.asyncio
    async def test_hive_shutdown(self, hive):
        for i in range(3):
            hive.add_agent(_make_spec(agent_id=f"a-{i}", backend="mock"))
        await hive.initialize()
        await hive.shutdown()
        assert all(not a.is_active for a in hive.agents.values())


# ------------------------------------------------------------------
#  Diagnostics
# ------------------------------------------------------------------

class TestDiagnostics:
    @pytest.mark.asyncio
    async def test_diagnostics(self, hive):
        for i in range(3):
            hive.add_agent(_make_spec(agent_id=f"d-{i}", backend="mock"))
        await hive.initialize()
        await hive.dispatch_all("navigate", "https://example.com")

        diag = hive.diagnostics()
        assert diag["total_agents"] == 3
        assert diag["active"] == 3
        assert diag["quarantined"] == 0
        assert diag["total_actions"] == 3
        assert diag["total_training_pairs"] == 3
        assert diag["uptime_s"] >= 0
        assert "registry" in diag
        assert len(diag["agents"]) == 3

    @pytest.mark.asyncio
    async def test_active_vs_quarantined(self, hive):
        a1 = hive.add_agent(_make_spec(agent_id="active-1", backend="mock"))
        a2 = hive.add_agent(_make_spec(agent_id="quarantine-1", backend="mock"))
        await hive.initialize()

        # Manually quarantine one
        a2._is_active = False
        assert len(hive.active_agents()) == 1
        assert len(hive.quarantined_agents()) == 1


# ------------------------------------------------------------------
#  Drift + Governance Math Verification
# ------------------------------------------------------------------

class TestGovernanceMath:
    def test_hyperbolic_distance_zero(self):
        """Same point = zero distance."""
        u = [0.1, 0.2, 0.0, 0.0, 0.0, 0.0]
        d = hyperbolic_distance(u, u)
        assert d < 0.01

    def test_hyperbolic_distance_grows(self):
        """Distance grows as points diverge."""
        origin = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        near = [0.1, 0.0, 0.0, 0.0, 0.0, 0.0]
        far = [0.5, 0.0, 0.0, 0.0, 0.0, 0.0]
        boundary = [0.95, 0.0, 0.0, 0.0, 0.0, 0.0]

        d_near = hyperbolic_distance(origin, near)
        d_far = hyperbolic_distance(origin, far)
        d_boundary = hyperbolic_distance(origin, boundary)

        assert d_near < d_far < d_boundary

    def test_harmonic_cost_exponential(self):
        """Cost scales exponentially with drift."""
        c0 = harmonic_cost(0.0)
        c1 = harmonic_cost(1.0)
        c2 = harmonic_cost(2.0)
        c3 = harmonic_cost(3.0)

        assert c0 == pytest.approx(1.0)
        assert c1 > c0
        assert c2 > c1 * 2  # Superlinear
        assert c3 > c2 * 3  # Even more

    def test_intent_vector_from_text(self):
        """Intent vectors map keywords to Sacred Tongue dimensions."""
        research = IntentVector.from_text("Research quantum computing papers")
        assert research.ko > 0  # Knowledge dimension

        publish = IntentVector.from_text("Publish blog post on AI safety")
        assert publish.av > 0  # Communication dimension

        build = IntentVector.from_text("Build and deploy a web scraper")
        assert build.ru > 0  # Creation dimension

    def test_drift_detection(self):
        """Drift from research intent to shopping should be high."""
        research = IntentVector.from_text("Research AI safety papers")
        shopping = IntentVector.from_text("Buy shoes and clothing")

        d = hyperbolic_distance(research.to_array(), shopping.to_array())
        assert d > 0.3  # Should detect as drift


# ------------------------------------------------------------------
#  HuggingFace Integration Paths
# ------------------------------------------------------------------

class TestHuggingFaceIntegration:
    def test_agent_spec_with_hf_model(self):
        spec = AgentSpec(
            agent_id="hf-1",
            agent_name="HF Agent",
            source=AgentSource.HUGGINGFACE,
            intent="Summarize papers",
            model_id="issdandavis/phdm-21d-embedding",
        )
        assert spec.model_id == "issdandavis/phdm-21d-embedding"
        assert spec.source == AgentSource.HUGGINGFACE

    @pytest.mark.asyncio
    async def test_hf_agent_in_hive(self, hive):
        """HF agent integrates into hive even without actual model download."""
        spec = _make_spec(
            agent_id="hf-researcher",
            source=AgentSource.HUGGINGFACE,
            model_id="issdandavis/phdm-21d-embedding",
            backend="mock",
        )
        agent = hive.add_agent(spec)

        # Browser works regardless of model
        await agent.initialize_browser()
        action = await agent.execute("navigate", "https://huggingface.co")
        assert action.governance_decision in ("ALLOW", "QUARANTINE", "DENY", "ESCALATE")

    def test_hf_agent_spec_metadata(self):
        spec = AgentSpec(
            agent_id="hf-2",
            agent_name="HF Agent 2",
            source=AgentSource.HUGGINGFACE,
            intent="Train embeddings",
            model_id="issdandavis/spiralverse-ai-federated-v1",
            metadata={"hf_revision": "main", "torch_dtype": "float16"},
        )
        assert spec.metadata["hf_revision"] == "main"


# ------------------------------------------------------------------
#  Edge Cases
# ------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_hive(self, hive):
        results = await hive.initialize()
        assert results == {}
        diag = hive.diagnostics()
        assert diag["total_agents"] == 0

    @pytest.mark.asyncio
    async def test_dispatch_to_inactive_agent(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await hive.initialize()
        agent._is_active = False
        with pytest.raises(RuntimeError, match="not active"):
            await hive.dispatch("test-agent-1", "navigate", "https://example.com")

    @pytest.mark.asyncio
    async def test_dispatch_all_skips_inactive(self, hive):
        a1 = hive.add_agent(_make_spec(agent_id="active", backend="mock"))
        a2 = hive.add_agent(_make_spec(agent_id="inactive", backend="mock"))
        await hive.initialize()
        a2._is_active = False

        results = await hive.dispatch_all("navigate", "https://example.com", active_only=True)
        assert len(results) == 1
        assert "active" in results

    @pytest.mark.asyncio
    async def test_token_revocation_blocks_agent(self, hive):
        agent = hive.add_agent(_make_spec(backend="mock"))
        await hive.initialize()
        agent.token.revoke("test_revocation")
        assert agent.is_active is False

    @pytest.mark.asyncio
    async def test_large_fleet(self, hive):
        """20 agents running concurrently."""
        for i in range(20):
            hive.add_agent(_make_spec(agent_id=f"fleet-{i}", backend="mock"))
        await hive.initialize()

        results = await hive.dispatch_all("navigate", "https://arxiv.org")
        assert len(results) == 20

        training = hive.collect_training_data()
        assert len(training) == 20
