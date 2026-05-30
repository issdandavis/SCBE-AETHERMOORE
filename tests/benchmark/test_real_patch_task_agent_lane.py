"""Agent lane tests for the real-patch benchmark.

All tests use a monkeypatched _call_agent stub so they run in CI without
any API keys. The stub delegates to scbe_repair (the known-good reference)
to produce correct responses for each task.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "real_patch_task_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("real_patch_task_benchmark_agent", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_stub_call_agent(module: Any):
    """Return a _call_agent stub that returns scbe_repair output without hitting any API."""
    import tempfile

    def _stub(prompt: str, *, provider: str = "cerebras", timeout: int = 90) -> str:
        # Find which task this prompt is for by matching the source filename
        for task in module.TASKS:
            src_file = next(iter(task.files))
            if src_file in prompt:
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    module._write_fixture(root, task)
                    module.scbe_repair(root, task)
                    return (root / src_file).read_text(encoding="utf-8")
        return ""

    return _stub


def test_agent_lane_structure_with_mocked_api(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_call_agent", _make_stub_call_agent(module))

    report = module.build_report(out_dir=tmp_path, run_id="pytest-agent", agent_provider="cerebras")

    # Existing summary keys must be present and unaffected
    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["baseline_test_passes"] == 0
    assert report["summary"]["scbe_test_passes"] == report["summary"]["task_count"]

    # Agent lane keys must be present
    assert "agent_summary" in report
    assert "agent_scores" in report
    assert "agent_meta" in report

    ag = report["agent_summary"]
    assert ag["provider"] == "cerebras"
    assert ag["model"] == "gpt-oss-120b"
    assert "agent_test_passes" in ag
    assert "agent_avg" in ag
    assert "agent_wins" in ag

    # Each agent score must have expected fields
    for score in report["agent_scores"]:
        assert "task_id" in score
        assert "checks" in score
        assert "score" in score

    # Agent meta must include task_id and provider info
    for meta in report["agent_meta"]:
        assert "task_id" in meta
        assert "provider" in meta

    # Claim boundary must include the agent note
    assert any("agent lane" in item.lower() for item in report["claim_boundary"])


def test_agent_lane_skipped_when_provider_none(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(out_dir=tmp_path, run_id="pytest-no-agent")

    # Without --provider, agent keys must NOT appear
    assert "agent_scores" not in report
    assert "agent_summary" not in report
    assert "agent_meta" not in report


def test_agent_lane_passes_all_tasks_with_correct_stub(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "_call_agent", _make_stub_call_agent(module))

    report = module.build_report(out_dir=tmp_path, run_id="pytest-agent-pass", agent_provider="cerebras")

    ag = report["agent_summary"]
    assert ag["agent_test_passes"] == report["summary"]["task_count"]
    for score in report["agent_scores"]:
        assert score["checks"]["tests_passed"] is True
        assert score["checks"]["edit_scope_clean"] is True
        assert score["checks"]["patch_captured"] is True


def test_build_repair_prompt_covers_issue_and_source() -> None:
    module = _load_module()
    task = module.TASKS[0]
    prompt = module._build_repair_prompt(task)

    assert task.issue[:30] in prompt
    src_file = next(iter(task.files))
    assert src_file in prompt
    # Broken source must appear in the prompt
    for line in list(task.files.values())[0].splitlines()[:3]:
        assert line in prompt


def test_strip_fences_handles_all_variants() -> None:
    module = _load_module()

    assert module._strip_fences("```python\nprint('hi')\n```").strip() == "print('hi')"
    assert module._strip_fences("```\nprint('hi')\n```").strip() == "print('hi')"
    assert module._strip_fences("print('hi')") == "print('hi')"


def test_providers_have_required_keys() -> None:
    module = _load_module()

    for name, cfg in module.PROVIDERS.items():
        assert "base_url" in cfg, f"{name} missing base_url"
        assert "model" in cfg, f"{name} missing model"
        assert "env_var" in cfg, f"{name} missing env_var"

    assert module.PROVIDERS["cerebras"]["model"] == "gpt-oss-120b"
    assert module.PROVIDERS["groq"]["model"] == "llama-3.3-70b-versatile"
