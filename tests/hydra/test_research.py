"""Tests for HYDRA research orchestration."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from hydra.research import ResearchConfig, ResearchOrchestrator, html_to_text
from hydra.switchboard import Switchboard


class DummyProvider:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[str] = []

    async def complete(self, prompt: str, system=None, max_tokens: int = 4096, temperature: float = 0.7):
        self.calls.append(prompt)
        text = self._responses.pop(0) if self._responses else "fallback"
        return SimpleNamespace(
            text=text,
            model="dummy",
            input_tokens=1,
            output_tokens=1,
            finish_reason="stop",
        )


class DummyMultiTabLimb:
    def __init__(self):
        self.active = False

    async def activate(self):
        self.active = True
        return True

    async def deactivate(self):
        self.active = False

    async def execute_parallel(self, commands):
        if not commands:
            return []
        action = str(commands[0].get("action", ""))
        if action == "navigate":
            return [
                {"success": True, "tab_id": f"tab-{idx}", "data": {"url": cmd.get("target")}}
                for idx, cmd in enumerate(commands)
            ]
        if action == "get_content":
            return [
                {
                    "success": True,
                    "data": {
                        "preview": "<html><body><h1>Aethermoor</h1><p>Multi-agent governance and safety.</p></body></html>",
                    },
                }
                for _ in commands
            ]
        return [{"success": False, "error": "unknown action"} for _ in commands]


def test_html_to_text_compacts_markup():
    raw = "<html><body><script>ignored()</script><p>Hello <b>World</b></p></body></html>"
    text = html_to_text(raw, max_chars=200)
    assert "ignored" not in text
    assert "Hello World" in text


@pytest.mark.asyncio
async def test_research_local_pipeline_with_parallel_browse():
    decompose = json.dumps(
        [
            {
                "title": "Core concepts",
                "search_query": "AI safety governance",
                "urls": ["https://example.com/core"],
            },
            {
                "title": "Recent updates",
                "search_query": "AI safety governance latest",
                "urls": ["https://example.com/latest"],
            },
        ]
    )

    provider = DummyProvider([decompose, "Synthesis: governance trends and operational controls."])
    orchestrator = ResearchOrchestrator(
        config=ResearchConfig(mode="local", provider_order=["claude"]),
        providers={"claude": provider},
        browser_limb=DummyMultiTabLimb(),
    )

    report = await orchestrator.research("latest AI safety research")
    await orchestrator.close()

    assert report.query == "latest AI safety research"
    assert len(report.subtasks) == 2
    assert len(report.sources) == 2
    assert all(source.status == "ok" for source in report.sources)
    assert "Synthesis:" in report.synthesis


@pytest.mark.asyncio
async def test_research_cloud_mode_uses_switchboard(tmp_path: Path):
    decompose = json.dumps(
        [
            {
                "title": "Error correction",
                "search_query": "quantum error correction 2025",
                "urls": ["https://example.com/qec"],
            },
            {
                "title": "Fault tolerance",
                "search_query": "fault tolerant quantum computing",
                "urls": ["https://example.com/ftqc"],
            },
        ]
    )

    provider = DummyProvider([decompose, "Synthesis: cloud worker output merged."])
    db_path = tmp_path / "switchboard.db"
    board = Switchboard(str(db_path))

    orchestrator = ResearchOrchestrator(
        config=ResearchConfig(
            mode="cloud",
            provider_order=["claude"],
            cloud_wait_timeout_sec=10,
            cloud_poll_interval_sec=0.05,
            switchboard_role="researcher",
        ),
        providers={"claude": provider},
        switchboard=board,
    )

    async def worker_sim() -> None:
        processed = 0
        while processed < 2:
            task = board.claim_task("worker-1", ["researcher"], lease_seconds=30)
            if not task:
                await asyncio.sleep(0.01)
                continue
            payload = task.get("payload", {})
            url = str(payload.get("target", ""))
            board.complete_task(
                task["task_id"],
                "worker-1",
                {
                    "success": True,
                    "url": url,
                    "text": f"content from {url}",
                    "chars": len(url) + 13,
                },
            )
            processed += 1

    worker_task = asyncio.create_task(worker_sim())
    report = await orchestrator.research("quantum computing error correction 2025")
    await worker_task
    await orchestrator.close()

    assert len(report.sources) == 2
    assert all(src.provider == "cloud-worker" for src in report.sources)
    assert all(src.status == "ok" for src in report.sources)


@pytest.mark.asyncio
async def test_decompose_fallback_when_model_output_is_not_json():
    provider = DummyProvider(["not-json-response"])
    orchestrator = ResearchOrchestrator(
        config=ResearchConfig(mode="local", provider_order=["claude"]),
        providers={"claude": provider},
        browser_limb=DummyMultiTabLimb(),
    )

    subtasks = await orchestrator._decompose_query("sheaf cohomology for lattices")
    await orchestrator.close()

    assert len(subtasks) >= 2
    assert subtasks[0].search_query
