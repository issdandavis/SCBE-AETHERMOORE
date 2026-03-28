import json
from pathlib import Path

import pytest

from scripts.system.aetherbrowser_model_cli import (
    append_jsonl_record,
    build_logged_input,
    execute_request,
    render_weighted_context,
    resolve_provider,
)
from src.aetherbrowser.provider_executor import ProviderExecutionResult
from src.aetherbrowser.router import ModelProvider, OctoArmorRouter


class StubExecutor:
    async def execute(self, plan):
        return ProviderExecutionResult(
            provider=plan.provider,
            model_id="stub-model",
            text="stub result",
            attempted=[plan.provider],
            fallback_used=False,
        )


def test_resolve_provider_accepts_hf_alias() -> None:
    assert resolve_provider("hf") == ModelProvider.HUGGINGFACE


def test_render_weighted_context_contains_label_and_weight() -> None:
    rendered = render_weighted_context("vault note", label="vault", weight=1.75)
    assert "label=vault" in rendered
    assert "weight=1.75" in rendered
    assert "vault note" in rendered


def test_build_logged_input_appends_context_block() -> None:
    combined = build_logged_input(
        "Summarize this", "[weighted-context]\nctx\n[/weighted-context]"
    )
    assert combined.startswith("Summarize this")
    assert "[weighted-context]" in combined


def test_append_jsonl_record_writes_one_line(tmp_path: Path) -> None:
    path = tmp_path / "runs.jsonl"
    append_jsonl_record(path, {"ok": True})
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"ok": True}


@pytest.mark.asyncio
async def test_execute_request_respects_requested_provider() -> None:
    router = OctoArmorRouter(
        enabled_providers={p: True for p in ModelProvider},
    )
    record = await execute_request(
        text="Summarize this page",
        provider=ModelProvider.HUGGINGFACE,
        model_id="issdandavis/scbe-pivot-qwen-0.5b",
        auto_cascade=False,
        context_text="This page is about browser routing.",
        context_label="page",
        context_weight=1.25,
        metadata={"origin": "test"},
        executor=StubExecutor(),
        router=router,
    )

    assert record["requested_provider"] == "huggingface"
    assert record["requested_model_id"] == "issdandavis/scbe-pivot-qwen-0.5b"
    assert record["execution"]["provider"] == "huggingface"
    assert record["metadata"]["origin"] == "test"
    assert record["context"]["weight"] == 1.25
