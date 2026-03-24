"""Tests for provider-backed command execution."""

import pytest

from src.aetherbrowser.command_planner import CommandPlan, RankedAction
from src.aetherbrowser.provider_executor import ProviderExecutionResult, ProviderExecutor
from src.aetherbrowser.router import ModelProvider, TaskComplexity


def _plan(**overrides):
    base = CommandPlan(
        text="Research hyperbolic competitors",
        task_type="research",
        intent="research",
        complexity=TaskComplexity.HIGH,
        provider="sonnet",
        selection_reason="preferred_provider",
        fallback_chain=["haiku", "local"],
        browser_action_required=False,
        escalation_ready=True,
        preferred_engine="playwright",
        targets=["github.com"],
        risk_tier="low",
        review_zone=None,
        approval_required=False,
        required_approvals=[],
        auto_cascade=True,
        next_actions=[RankedAction(label="Inspect target repo", reason="best next step", risk_tier="low")],
        assignments=[{"role": "KO", "task": "Orchestrate the research"}],
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


class TestProviderExecutor:
    def test_runtime_status_marks_missing_env_for_cloud_lane(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        executor = ProviderExecutor()

        snapshot = executor.runtime_status_snapshot()

        assert snapshot["haiku"]["available"] is False
        assert snapshot["haiku"]["reason"] == "missing_env:ANTHROPIC_API_KEY"
        assert snapshot["haiku"]["model_id"] == "claude-3-5-haiku-20241022"

    def test_runtime_status_marks_ready_when_env_and_package_exist(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        executor = ProviderExecutor()

        snapshot = executor.runtime_status_snapshot()

        assert snapshot["flash"]["available"] is True
        assert snapshot["flash"]["reason"] == "ready"
        assert snapshot["flash"]["family"] == "openai"
        assert snapshot["flash"]["packages"] == ["openai"]

    def test_runtime_status_marks_huggingface_missing_env(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        executor = ProviderExecutor()

        snapshot = executor.runtime_status_snapshot()

        assert snapshot["huggingface"]["available"] is False
        assert snapshot["huggingface"]["reason"] == "missing_env:HF_TOKEN"
        assert snapshot["huggingface"]["family"] == "huggingface"

    @pytest.mark.asyncio
    async def test_local_executor_returns_deterministic_summary(self):
        executor = ProviderExecutor()

        result = await executor.execute(_plan(provider="local", fallback_chain=["local"]))

        assert isinstance(result, ProviderExecutionResult)
        assert result.provider == "local"
        assert result.fallback_used is False
        assert "Local execution lane active" in result.text

    @pytest.mark.asyncio
    async def test_falls_back_when_primary_provider_fails(self):
        async def fail_adapter(_model_id: str, _prompt: str) -> str:
            raise RuntimeError("primary failed")

        async def win_adapter(_model_id: str, _prompt: str) -> str:
            return "fallback answer"

        executor = ProviderExecutor(
            adapters={
                ModelProvider.SONNET: fail_adapter,
                ModelProvider.HAIKU: fail_adapter,
                ModelProvider.LOCAL: win_adapter,
            }
        )
        result = await executor.execute(_plan())

        assert result.provider == "local"
        assert result.fallback_used is True
        assert result.attempted == ["sonnet", "haiku", "local"]
        assert result.text == "fallback answer"

    @pytest.mark.asyncio
    async def test_no_cascade_raises_primary_failure(self):
        async def fail_adapter(_model_id: str, _prompt: str) -> str:
            raise RuntimeError("primary failed")

        executor = ProviderExecutor(adapters={ModelProvider.SONNET: fail_adapter})

        with pytest.raises(RuntimeError, match="primary failed"):
            await executor.execute(_plan(auto_cascade=False, fallback_chain=["sonnet"]))

    @pytest.mark.asyncio
    async def test_huggingface_adapter_can_be_stubbed(self):
        async def hf_adapter(_model_id: str, _prompt: str) -> str:
            return "hf answer"

        executor = ProviderExecutor(adapters={ModelProvider.HUGGINGFACE: hf_adapter})
        result = await executor.execute(
            _plan(provider="huggingface", fallback_chain=["huggingface"], auto_cascade=False)
        )

        assert result.provider == "huggingface"
        assert result.text == "hf answer"
