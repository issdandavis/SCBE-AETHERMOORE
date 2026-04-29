from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_agent_task_run_builds_trajectory_scaling():
    module = load_module(REPO_ROOT / "scripts" / "agents" / "run_agent_task.py", "_run_agent_task_test")
    payload = module.build_task_run(
        goal="improve agentic coding harness",
        workers=4,
        sandbox="auto",
        max_attempts=3,
        critic=True,
        rerank=True,
    )
    assert payload["trajectory_scaling"]["max_attempts"] == 3
    assert len(payload["packets"]) == 4
    assert any(step["role"] == "critic" for step in payload["packets"][0]["trajectory"])
    assert any(step["role"] == "reranker" for step in payload["packets"][0]["trajectory"])
    module.attach_build_bijection(payload)
    assert payload["build_bijection"]["ok"] is True
    assert set(payload["build_bijection"]["tongues"]) == {"ko", "av", "ru", "ca", "um", "dr"}


def test_agent_task_run_write_emits_tool_bridge(tmp_path):
    module = load_module(REPO_ROOT / "scripts" / "agents" / "run_agent_task.py", "_run_agent_task_write")
    payload = module.build_task_run(
        goal="wire geoseal harness",
        workers=1,
        sandbox="auto",
        max_attempts=1,
        critic=False,
        rerank=False,
    )
    module.write_task_run(payload, tmp_path, attach_bijection=False)
    json_paths = [p for p in tmp_path.glob("**/agent_task_run.json") if p.parent.name != "latest"]
    assert len(json_paths) == 1
    saved = json.loads(json_paths[0].read_text(encoding="utf-8"))
    bridge = saved["tool_bridge"]
    assert bridge["schema_version"] == "scbe_agent_tool_bridge_v1"
    assert "explain_route_json" in bridge["geoseal_cli"]
    intent_files = list(tmp_path.glob("**/task_intent.txt"))
    assert len(intent_files) == 1
    assert "wire geoseal harness" in intent_files[0].read_text(encoding="utf-8")


def test_agent_tool_bridge_requires_exactly_one_intent_source():
    from src.coding_spine.agent_tool_bridge import build_agent_tool_bridge_v1

    with pytest.raises(ValueError):
        build_agent_tool_bridge_v1()
    with pytest.raises(ValueError):
        build_agent_tool_bridge_v1(intent_relative_posix="a.txt", inline_goal="b")


def test_geoseal_service_tool_bridge_endpoint():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post("/v1/harness/tool-bridge", json={"goal": "smoke harness"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["schema_version"] == "scbe_agent_tool_bridge_v1"
    assert "geoseal_cli" in body["data"]


def test_external_eval_manifest_validates():
    module = load_module(
        REPO_ROOT / "scripts" / "benchmark" / "external_agentic_eval_driver.py",
        "_external_agentic_eval_driver_test",
    )
    tasks = module.load_manifest(REPO_ROOT / "config" / "eval" / "external_agentic_eval_tasks.sample.json")
    validation = module.validate_tasks(tasks)
    assert validation["ok"], validation
    assert {task.suite for task in tasks} >= {"repo_native", "terminal_bench", "swe_bench"}


def test_external_eval_report_includes_sacred_tongue_bijection(tmp_path):
    module = load_module(
        REPO_ROOT / "scripts" / "benchmark" / "external_agentic_eval_driver.py",
        "_external_agentic_eval_driver_bijection_test",
    )
    tasks = module.load_manifest(REPO_ROOT / "config" / "eval" / "external_agentic_eval_tasks.sample.json")
    out = module.write_report(tasks, tmp_path, execute=False)
    assert out["payload"]["sacred_tongue_bijection"]["ok"] is True
    assert out["payload"]["sacred_tongue_bijection"]["schema_version"] == "scbe_sacred_tongue_payload_bijection_v1"


def test_external_eval_validate_subcommand():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/external_agentic_eval_driver.py",
            "--validate-only",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
