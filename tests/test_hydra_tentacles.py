"""
Tests for HYDRA Tentacle Registry, Apprentice Provider, and Code Sandbox Limb.

Covers:
  - TentacleRegistry: registration, discovery, dispatch, health
  - ApprenticeProvider: delegation, feedback, SFT generation, stats
  - CodeSandboxLimb: execution, risk assessment, governance, multi-language
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================
# Tentacle Registry Tests
# ============================================================


class TestTentacleRegistry:
    """Tests for hydra.tentacle_registry."""

    def _make_registry(self):
        from hydra.tentacle_registry import TentacleRegistry
        return TentacleRegistry.create_default()

    def test_create_default_registers_all_kinds(self):
        registry = self._make_registry()
        listing = registry.list_all()
        kinds = {t["kind"] for t in listing}
        assert "browser" in kinds
        assert "connector" in kinds
        assert "ide" in kinds
        assert "training" in kinds
        assert "inference" in kinds

    def test_register_and_get(self):
        from hydra.tentacle_registry import (
            TentacleRegistry,
            BrowserTentacle,
            TentacleStatus,
        )

        registry = TentacleRegistry()
        bt = BrowserTentacle(tentacle_id="test-browser")
        tid = registry.register(bt)

        assert tid == "test-browser"
        assert registry.get("test-browser") is bt
        assert bt.spec.status == TentacleStatus.ACTIVE

    def test_unregister(self):
        from hydra.tentacle_registry import TentacleRegistry, ConnectorTentacle

        registry = TentacleRegistry()
        ct = ConnectorTentacle(tentacle_id="test-conn")
        registry.register(ct)

        assert registry.unregister("test-conn") is True
        assert registry.get("test-conn") is None
        assert registry.unregister("nonexistent") is False

    def test_find_by_kind(self):
        registry = self._make_registry()
        browsers = registry.find(kind="browser")
        assert len(browsers) == 1
        assert browsers[0].kind.value == "browser"

    def test_find_by_tongue(self):
        registry = self._make_registry()
        # Browser tentacle has KO, AV, RU, CA, UM tongues
        ko_tentacles = registry.find(tongue="KO")
        assert len(ko_tentacles) >= 1

    def test_find_by_action(self):
        registry = self._make_registry()
        navigators = registry.find(action="navigate")
        assert len(navigators) >= 1

    def test_find_combined_filters(self):
        registry = self._make_registry()
        # Browser kind + navigate action
        results = registry.find(kind="browser", action="navigate")
        assert len(results) == 1

    def test_find_no_match(self):
        registry = self._make_registry()
        results = registry.find(kind="nonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_dispatch_success(self):
        registry = self._make_registry()
        result = await registry.dispatch(
            "browser-fleet", "navigate", {"url": "https://example.com"}
        )
        assert result.success is True
        assert result.tentacle_id == "browser-fleet"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tentacle(self):
        registry = self._make_registry()
        result = await registry.dispatch("nonexistent", "navigate", {})
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_dispatch_unknown_action(self):
        registry = self._make_registry()
        result = await registry.dispatch("browser-fleet", "fly_to_moon", {})
        assert result.success is False
        assert "Unknown action" in result.error

    @pytest.mark.asyncio
    async def test_dispatch_to_kind(self):
        registry = self._make_registry()
        result = await registry.dispatch_to_kind("browser", "navigate", {"url": "test"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dispatch_to_kind_no_match(self):
        registry = self._make_registry()
        result = await registry.dispatch_to_kind("browser", "nonexistent_action", {})
        assert result.success is False

    @pytest.mark.asyncio
    async def test_broadcast(self):
        registry = self._make_registry()
        # extract is available on browser tentacle
        results = await registry.broadcast("extract", {"url": "test"})
        assert len(results) >= 1
        assert all(isinstance(r.success, bool) for r in results)

    def test_health_report(self):
        registry = self._make_registry()
        report = registry.health_report()
        assert report["total_tentacles"] == 5
        assert report["active"] == 5
        assert report["avg_health"] == 1.0
        assert "tentacles" in report

    def test_list_all_structure(self):
        registry = self._make_registry()
        listing = registry.list_all()
        for item in listing:
            assert "tentacle_id" in item
            assert "kind" in item
            assert "name" in item
            assert "status" in item
            assert "capabilities" in item

    @pytest.mark.asyncio
    async def test_dispatch_logs_are_recorded(self):
        registry = self._make_registry()
        await registry.dispatch("browser-fleet", "navigate", {"url": "test"})
        await registry.dispatch("ide-worker", "plan", {"prompt": "hello"})
        report = registry.health_report()
        assert report["recent_dispatches"] == 2


# ============================================================
# Connector / IDE / Training / Inference Tentacle Tests
# ============================================================


class TestConnectorTentacle:
    @pytest.mark.asyncio
    async def test_dispatch_without_backend(self):
        from hydra.tentacle_registry import ConnectorTentacle

        ct = ConnectorTentacle()
        result = await ct.execute("dispatch", {"connector_id": "my-zap", "data": {"key": "val"}})
        assert result.success is True
        assert result.result["status"] == "dispatch_queued"

    @pytest.mark.asyncio
    async def test_list_without_backend(self):
        from hydra.tentacle_registry import ConnectorTentacle

        ct = ConnectorTentacle()
        result = await ct.execute("list", {})
        assert result.success is True
        assert result.result["count"] == 0


class TestIDETentacle:
    @pytest.mark.asyncio
    async def test_run_code_without_backend(self):
        from hydra.tentacle_registry import IDETentacle

        ide = IDETentacle()
        result = await ide.execute("run_code", {"language": "python", "code": "print(1)"})
        assert result.success is True
        assert result.result["language"] == "python"

    @pytest.mark.asyncio
    async def test_plan_without_backend(self):
        from hydra.tentacle_registry import IDETentacle

        ide = IDETentacle()
        result = await ide.execute("plan", {"prompt": "Build a REST API"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_test_action(self):
        from hydra.tentacle_registry import IDETentacle

        ide = IDETentacle()
        result = await ide.execute("test", {"path": "tests/", "framework": "pytest"})
        assert result.success is True
        assert result.result["framework"] == "pytest"


class TestTrainingTentacle:
    @pytest.mark.asyncio
    async def test_stats(self):
        from hydra.tentacle_registry import TrainingTentacle

        tt = TrainingTentacle()
        result = await tt.execute("stats", {})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_merge(self):
        from hydra.tentacle_registry import TrainingTentacle

        tt = TrainingTentacle()
        result = await tt.execute("merge", {"sources": ["training-data/"]})
        assert result.success is True


class TestInferenceTentacle:
    @pytest.mark.asyncio
    async def test_generate_without_backend(self):
        from hydra.tentacle_registry import InferenceTentacle

        it = InferenceTentacle()
        result = await it.execute("generate", {"prompt": "Hello world"})
        assert result.success is True
        assert result.result["status"] == "generation_queued"

    @pytest.mark.asyncio
    async def test_delegate_without_backend(self):
        from hydra.tentacle_registry import InferenceTentacle

        it = InferenceTentacle()
        result = await it.execute("delegate", {"task": "classify risk", "context": {"domain": "banking"}})
        assert result.success is True
        assert result.result["status"] == "delegation_queued"

    def test_health_check(self):
        from hydra.tentacle_registry import InferenceTentacle

        it = InferenceTentacle()
        health = it.health_check()
        assert health["health_score"] == 1.0
        assert health["action_count"] == 0


# ============================================================
# Apprentice Provider Tests
# ============================================================


class TestApprenticeInteraction:
    """Test the ApprenticeInteraction data structure."""

    def test_to_sft_pair_approved(self):
        from hydra.apprentice_provider import ApprenticeInteraction

        interaction = ApprenticeInteraction(
            interaction_id="test-001",
            timestamp="2026-02-27T00:00:00Z",
            mentor_type="claude",
            task_prompt="Classify risk for banking.com",
            apprentice_response="High risk (0.9)",
            context={"domain": "banking"},
            approved=True,
            quality_score=0.85,
            tongue="DR",
            layers=[13],
            model_id="test-model",
        )

        pair = interaction.to_sft_pair()
        assert pair is not None
        assert pair["instruction"] == "Classify risk for banking.com"
        assert pair["output"] == "High risk (0.9)"
        assert pair["metadata"]["approved"] is True
        assert pair["metadata"]["tongue"] == "DR"

    def test_to_sft_pair_corrected(self):
        from hydra.apprentice_provider import ApprenticeInteraction

        interaction = ApprenticeInteraction(
            interaction_id="test-002",
            timestamp="2026-02-27T00:00:00Z",
            mentor_type="claude",
            task_prompt="Assess domain",
            apprentice_response="Low risk",
            context={},
            approved=False,
            correction="High risk — banking domain has elevated sensitivity",
            quality_score=0.4,
            model_id="test-model",
        )

        pair = interaction.to_sft_pair()
        assert pair is not None
        # Should use the correction, not the original response
        assert "High risk" in pair["output"]
        assert pair["metadata"]["corrected"] is True

    def test_to_sft_pair_rejected_no_correction(self):
        from hydra.apprentice_provider import ApprenticeInteraction

        interaction = ApprenticeInteraction(
            interaction_id="test-003",
            timestamp="2026-02-27T00:00:00Z",
            mentor_type="claude",
            task_prompt="Bad task",
            apprentice_response="Bad response",
            context={},
            approved=False,
            correction=None,
            model_id="test-model",
        )

        pair = interaction.to_sft_pair()
        assert pair is None  # No training signal from rejected without correction

    def test_to_sft_pair_pending(self):
        from hydra.apprentice_provider import ApprenticeInteraction

        interaction = ApprenticeInteraction(
            interaction_id="test-004",
            timestamp="2026-02-27T00:00:00Z",
            mentor_type="claude",
            task_prompt="Pending",
            apprentice_response="Response",
            context={},
            model_id="test-model",
        )

        pair = interaction.to_sft_pair()
        assert pair is None  # Not yet reviewed


class TestApprenticeProvider:
    """Test the ApprenticeProvider with mocked HF backend."""

    def _make_provider(self, tmpdir):
        """Create an ApprenticeProvider with mocked HF provider."""
        from hydra.apprentice_provider import ApprenticeProvider

        with patch("hydra.apprentice_provider.HuggingFaceProvider") as MockHF:
            mock_hf = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "This domain has elevated risk (0.85)"
            mock_response.model = "test-model"
            mock_response.input_tokens = 50
            mock_response.output_tokens = 30
            mock_response.finish_reason = "stop"
            mock_hf.complete = AsyncMock(return_value=mock_response)
            MockHF.return_value = mock_hf

            provider = ApprenticeProvider(
                model_id="test/model",
                mentor_type="claude",
                tongue="DR",
                output_dir=str(tmpdir),
                auto_flush_interval=5,
            )
            provider._hf_provider = mock_hf
            return provider

    @pytest.mark.asyncio
    async def test_delegate_records_interaction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)
            result = await provider.delegate(
                task="Classify banking.com risk",
                context={"domain": "banking"},
                tongue="DR",
            )

            assert result.interaction_id.startswith("appr-")
            assert result.response == "This domain has elevated risk (0.85)"
            assert result.confidence > 0
            assert result.latency_ms >= 0

            stats = provider.get_stats()
            assert stats["total_delegations"] == 1
            assert stats["pending_review"] == 1

    @pytest.mark.asyncio
    async def test_mentor_feedback_approved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)
            result = await provider.delegate(task="Test task", context={})

            sft_pair = await provider.mentor_feedback(
                interaction_id=result.interaction_id,
                approved=True,
                quality_score=0.9,
            )

            assert sft_pair is not None
            assert sft_pair["metadata"]["approved"] is True

            stats = provider.get_stats()
            assert stats["approved"] == 1
            assert stats["pending_review"] == 0
            assert stats["total_sft_pairs"] == 1

    @pytest.mark.asyncio
    async def test_mentor_feedback_corrected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)
            result = await provider.delegate(task="Test", context={})

            sft_pair = await provider.mentor_feedback(
                interaction_id=result.interaction_id,
                approved=False,
                correction="Better answer here",
                quality_score=0.5,
            )

            assert sft_pair is not None
            assert sft_pair["output"] == "Better answer here"
            assert sft_pair["metadata"]["corrected"] is True

            stats = provider.get_stats()
            assert stats["corrected"] == 1

    @pytest.mark.asyncio
    async def test_mentor_feedback_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)
            result = await provider.delegate(task="Bad task", context={})

            sft_pair = await provider.mentor_feedback(
                interaction_id=result.interaction_id,
                approved=False,
                quality_score=0.1,
            )

            assert sft_pair is None  # No training signal

            stats = provider.get_stats()
            assert stats["rejected"] == 1
            assert stats["total_sft_pairs"] == 0

    @pytest.mark.asyncio
    async def test_flush_training_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)

            # Create 3 approved interactions
            for i in range(3):
                result = await provider.delegate(task=f"Task {i}", context={})
                await provider.mentor_feedback(
                    result.interaction_id, approved=True, quality_score=0.8
                )

            count = await provider.flush_training_data()
            assert count == 3

            # Verify file was written
            session_file = provider._session_file
            assert session_file.exists()
            lines = session_file.read_text().strip().split("\n")
            assert len(lines) == 3

            # Verify each line is valid JSON
            for line in lines:
                data = json.loads(line)
                assert "instruction" in data
                assert "output" in data
                assert "metadata" in data

    @pytest.mark.asyncio
    async def test_auto_flush_at_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)
            provider._auto_flush_interval = 3  # Flush every 3

            # Create 3 approved interactions (should trigger auto-flush)
            for i in range(3):
                result = await provider.delegate(task=f"Task {i}", context={})
                await provider.mentor_feedback(
                    result.interaction_id, approved=True, quality_score=0.8
                )

            # Buffer should be empty after auto-flush
            assert len(provider._sft_buffer) == 0
            assert provider._session_file.exists()

    @pytest.mark.asyncio
    async def test_get_pending_reviews(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)

            r1 = await provider.delegate(task="Task 1", context={})
            r2 = await provider.delegate(task="Task 2", context={})

            pending = provider.get_pending_reviews()
            assert len(pending) == 2

            await provider.mentor_feedback(r1.interaction_id, approved=True)
            pending = provider.get_pending_reviews()
            assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_delegate_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)

            tasks = [
                {"task": "Classify A", "context": {"domain": "a"}},
                {"task": "Classify B", "context": {"domain": "b"}},
                {"task": "Classify C", "context": {"domain": "c"}},
            ]
            results = await provider.delegate_batch(tasks)
            assert len(results) == 3
            assert all(r.response for r in results)

            stats = provider.get_stats()
            assert stats["total_delegations"] == 3

    @pytest.mark.asyncio
    async def test_delegate_and_auto_approve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)

            result = await provider.delegate_and_auto_approve(
                task="Low risk task",
                min_confidence=0.5,  # Our mock returns ~0.75 confidence
                auto_quality=0.6,
            )

            stats = provider.get_stats()
            # Should be auto-approved since confidence > 0.5
            assert stats["approved"] == 1
            assert stats["pending_review"] == 0

    def test_confidence_estimation(self):
        from hydra.apprentice_provider import ApprenticeProvider

        with patch("hydra.apprentice_provider.HuggingFaceProvider"):
            provider = ApprenticeProvider.__new__(ApprenticeProvider)

            # Good response: long, proper finish
            mock_good = MagicMock()
            mock_good.text = " ".join(["word"] * 200)
            mock_good.finish_reason = "stop"
            mock_good.input_tokens = 100
            mock_good.output_tokens = 200
            conf_good = provider._estimate_confidence(mock_good)

            # Bad response: short, truncated
            mock_bad = MagicMock()
            mock_bad.text = "ok"
            mock_bad.finish_reason = "length"
            mock_bad.input_tokens = 100
            mock_bad.output_tokens = 2
            conf_bad = provider._estimate_confidence(mock_bad)

            assert conf_good > conf_bad

    @pytest.mark.asyncio
    async def test_mentor_feedback_nonexistent_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self._make_provider(tmpdir)
            result = await provider.mentor_feedback("nonexistent", approved=True)
            assert result is None

    def test_tongue_prompts_exist(self):
        from hydra.apprentice_provider import TONGUE_APPRENTICE_PROMPTS

        for tongue in ["KO", "AV", "RU", "CA", "UM", "DR"]:
            assert tongue in TONGUE_APPRENTICE_PROMPTS
            assert len(TONGUE_APPRENTICE_PROMPTS[tongue]) > 20


# ============================================================
# Code Sandbox Limb Tests
# ============================================================


class TestCodeSandboxRiskAssessment:
    """Test the risk assessment without executing code."""

    def _make_sandbox(self, tmpdir=None):
        from hydra.code_sandbox_limb import CodeSandboxLimb, SandboxConfig

        config = SandboxConfig(
            workspace=tmpdir or tempfile.mkdtemp(),
            safe_mode=True,
        )
        return CodeSandboxLimb(config)

    def test_banned_fragment_detected(self):
        sandbox = self._make_sandbox()
        risk, reason = sandbox._assess_risk("rm -rf /", "shell")
        assert risk == 1.0
        assert reason is not None
        assert "Banned" in reason

    def test_fork_bomb_blocked(self):
        sandbox = self._make_sandbox()
        risk, reason = sandbox._assess_risk(":(){ :|:& };:", "shell")
        assert risk == 1.0
        assert reason is not None

    def test_safe_python_low_risk(self):
        sandbox = self._make_sandbox()
        risk, reason = sandbox._assess_risk("print('hello world')", "python")
        assert reason is None
        assert risk < 0.5

    def test_risky_python_patterns(self):
        sandbox = self._make_sandbox()
        code = "import subprocess\nsubprocess.run(['ls'])"
        risk, reason = sandbox._assess_risk(code, "python")
        assert reason is None  # Not banned, but risky
        assert risk > 0.3

    def test_eval_increases_risk(self):
        sandbox = self._make_sandbox()
        code_safe = "print(1 + 1)"
        code_eval = "eval(input())"
        risk_safe, _ = sandbox._assess_risk(code_safe, "python")
        risk_eval, _ = sandbox._assess_risk(code_eval, "python")
        assert risk_eval > risk_safe

    def test_shell_higher_baseline(self):
        sandbox = self._make_sandbox()
        risk_py, _ = sandbox._assess_risk("echo hello", "python")
        risk_sh, _ = sandbox._assess_risk("echo hello", "shell")
        assert risk_sh > risk_py  # Shell has higher baseline risk

    def test_governance_decision_allow(self):
        sandbox = self._make_sandbox()
        assert sandbox._governance_decision(0.2) == "ALLOW"

    def test_governance_decision_quarantine(self):
        sandbox = self._make_sandbox()
        assert sandbox._governance_decision(0.6) == "QUARANTINE"

    def test_governance_decision_deny(self):
        sandbox = self._make_sandbox()
        assert sandbox._governance_decision(0.9) == "DENY"


class TestCodeSandboxExecution:
    """Test actual code execution in the sandbox."""

    def _make_sandbox(self):
        from hydra.code_sandbox_limb import CodeSandboxLimb, SandboxConfig

        config = SandboxConfig(
            workspace=tempfile.mkdtemp(),
            safe_mode=False,  # Relax for testing
        )
        return CodeSandboxLimb(config)

    @pytest.mark.asyncio
    async def test_python_execution(self):
        sandbox = self._make_sandbox()
        result = await sandbox.run_code("python", "print('hello from sandbox')")
        assert result.success is True
        assert "hello from sandbox" in result.stdout
        assert result.exit_code == 0
        assert result.governance_decision in ("ALLOW", "QUARANTINE")

    @pytest.mark.asyncio
    async def test_python_error(self):
        sandbox = self._make_sandbox()
        result = await sandbox.run_code("python", "raise ValueError('test error')")
        assert result.success is False
        assert result.exit_code != 0
        assert "ValueError" in result.stderr

    @pytest.mark.asyncio
    async def test_node_execution(self):
        sandbox = self._make_sandbox()
        result = await sandbox.run_code("node", "console.log(JSON.stringify({ok: true}))")
        assert result.success is True
        assert "ok" in result.stdout

    @pytest.mark.asyncio
    async def test_shell_execution(self):
        sandbox = self._make_sandbox()
        result = await sandbox.run_code("shell", "echo 'shell works'")
        assert result.success is True
        assert "shell works" in result.stdout

    @pytest.mark.asyncio
    async def test_disallowed_language(self):
        sandbox = self._make_sandbox()
        result = await sandbox.run_code("cobol", "DISPLAY 'HELLO'")
        assert result.success is False
        assert "not allowed" in result.stderr

    @pytest.mark.asyncio
    async def test_banned_code_blocked(self):
        sandbox = self._make_sandbox()
        result = await sandbox.run_code("shell", "rm -rf /tmp/something")
        assert result.success is False
        assert result.governance_decision == "DENY"

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self):
        sandbox = self._make_sandbox()
        result = await sandbox.run_code(
            "python",
            "import time; time.sleep(30)",
            timeout=2,
        )
        assert result.success is False
        assert "timed out" in result.stderr

    @pytest.mark.asyncio
    async def test_write_and_run(self):
        sandbox = self._make_sandbox()
        result = await sandbox.write_and_run(
            filename="test_script.py",
            code="import math\nprint(f'pi = {math.pi:.4f}')",
        )
        assert result.success is True
        assert "pi = 3.1416" in result.stdout
        assert result.file_path is not None

    @pytest.mark.asyncio
    async def test_write_and_run_auto_detect_language(self):
        sandbox = self._make_sandbox()
        result = await sandbox.write_and_run(
            filename="test_script.js",
            code="console.log('node auto-detected')",
        )
        assert result.success is True
        assert "node auto-detected" in result.stdout

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        sandbox = self._make_sandbox()
        result = await sandbox.write_and_run(
            filename="../../../etc/passwd",
            code="malicious",
        )
        assert result.success is False
        assert result.governance_decision == "DENY"

    @pytest.mark.asyncio
    async def test_detect_available(self):
        sandbox = self._make_sandbox()
        available = await sandbox.detect_available()
        assert "python" in available
        assert available["python"]["available"] is True
        assert available["python"]["version"] is not None

    def test_stats(self):
        sandbox = self._make_sandbox()
        stats = sandbox.get_stats()
        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_stats_after_executions(self):
        sandbox = self._make_sandbox()
        await sandbox.run_code("python", "print(1)")
        await sandbox.run_code("python", "raise Exception('fail')")
        stats = sandbox.get_stats()
        assert stats["total_executions"] == 2
        assert stats["successes"] == 1
        assert stats["failures"] == 1

    @pytest.mark.asyncio
    async def test_execution_id_unique(self):
        sandbox = self._make_sandbox()
        r1 = await sandbox.run_code("python", "print(1)")
        r2 = await sandbox.run_code("python", "print(2)")
        assert r1.execution_id != r2.execution_id

    @pytest.mark.asyncio
    async def test_output_truncation(self):
        from hydra.code_sandbox_limb import CodeSandboxLimb, SandboxConfig

        config = SandboxConfig(
            workspace=tempfile.mkdtemp(),
            max_output_size=100,
            safe_mode=False,
        )
        sandbox = CodeSandboxLimb(config)
        result = await sandbox.run_code("python", "print('x' * 1000)")
        assert result.truncated is True
        assert len(result.stdout) <= 150  # 100 + truncation message
