from __future__ import annotations

import importlib.util
import json
import os
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
    assert set(payload["build_bijection"]["tongues"]) == {
        "ko",
        "av",
        "ru",
        "ca",
        "um",
        "dr",
    }


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


def test_agent_harness_manifest_routes_all_code_languages():
    from src.coding_spine.agent_tool_bridge import build_agent_harness_manifest_v1

    manifest = build_agent_harness_manifest_v1(
        inline_goal="make agentic coding easier",
        preferred_language="rust",
        permission_mode="workspace-write",
    )
    assert manifest["schema_version"] == "scbe_agent_harness_manifest_v1"
    languages = {row["language"] for row in manifest["language_routes"]}
    assert {
        "python",
        "typescript",
        "rust",
        "c",
        "julia",
        "haskell",
        "go",
        "zig",
    } <= languages
    assert manifest["selected_language"]["language"] == "rust"
    assert manifest["selected_language"]["tongue"] == "RU"
    assert manifest["permission_mode"] == "workspace-write"
    assert any(tool["tool"] == "execute_tests" for tool in manifest["tool_contracts"])
    assert "agent_harness_json" in manifest["geoseal_cli"]
    stack = manifest["agent_execution_stack_v1"]
    assert stack["schema_version"] == "scbe_agent_execution_stack_v1"
    assert "execution_layer" in stack
    assert "temporal_reliance_layer" in stack
    ext = manifest["inbuilt_agentic_training_extensions"]
    assert ext["schema_version"] == "scbe_agentic_training_extensions_v1"
    assert "github" in ext and "huggingface" in ext
    assert "trigger_router_coding" in ext["github"]["commands"]
    assert "dispatch_train_and_gate" in ext["huggingface"]["commands"]
    assert "loop_dispatch_github_coding_json" in manifest["geoseal_cli"]
    assert "agentic_training_loop_json" in manifest["geoseal_cli"]
    hydra = manifest["hydra_tokenizer_bridge_v1"]
    assert hydra["schema_version"] == "geoseal_hydra_tokenizer_bridge_v1"
    assert hydra["selected_language"]["language"] == "rust"
    assert len(hydra["hydra_heads"]) == 6
    assert len(hydra["tokenizer_packet"]["rows"]) == 6
    assert "hydra_bridge_json" in manifest["geoseal_cli"]


def test_geoseal_agent_harness_cli_json():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "agent-harness",
            "--goal",
            "route all mapped code languages",
            "--language",
            "zig",
            "--permission-mode",
            "observe",
            "--json",
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
    assert payload["schema_version"] == "scbe_agent_harness_manifest_v1"
    assert payload["selected_language"]["language"] == "zig"
    assert payload["selected_language"]["parent_tongue"] == "RU"


def test_geoseal_agentic_training_loop_cli_json():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "agentic-training-loop",
            "--goal",
            "run nightly training loop",
            "--provider",
            "both",
            "--json",
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
    assert payload["schema_version"] == "geoseal-agentic-training-loop-v1"
    assert payload["extensions"]["github"] is not None
    assert payload["extensions"]["huggingface"] is not None
    assert "watch_run" in payload["extensions"]["github"]["commands"]


def test_geoseal_hydra_bridge_cli_json():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "hydra-bridge",
            "--goal",
            "route a coding task through hydra and tokenizer",
            "--language",
            "typescript",
            "--permission-mode",
            "observe",
            "--json",
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
    assert payload["schema_version"] == "geoseal_hydra_tokenizer_bridge_v1"
    assert payload["selected_language"]["tongue"] == "AV"
    assert payload["separation_of_concerns"]["hydra"].startswith("multi-agent")
    assert payload["tokenizer_packet"]["transport_boundary"].endswith("not authorization.")
    assert {row["tongue"] for row in payload["tokenizer_packet"]["rows"]} == {
        "KO",
        "AV",
        "RU",
        "CA",
        "UM",
        "DR",
    }


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


def test_geoseal_service_agent_harness_endpoint():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/harness/agent-harness",
        json={"goal": "make free agents useful", "language": "go"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["selected_language"]["language"] == "go"
    assert body["data"]["selected_language"]["parent_tongue"] == "CA"


def test_geoseal_service_cli_bridge_backend_registry():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post("/v1/geoseal/backend-registry", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["exit_code"] == 0
    assert body["data"]["version"] == "geoseal-backend-registry-v1"
    assert isinstance(body["data"]["backends"], list)


def test_geoseal_service_cli_bridge_agent_harness():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/agent-harness",
        json={"goal": "agent tool manifest", "language": "typescript"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["exit_code"] == 0
    assert body["data"]["selected_language"]["tongue"] == "AV"


def test_geoseal_service_cli_bridge_hydra_bridge():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/hydra-bridge",
        json={"goal": "coordinate paired agents", "language": "go"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["exit_code"] == 0
    assert body["data"]["schema_version"] == "geoseal_hydra_tokenizer_bridge_v1"
    assert body["data"]["selected_language"]["parent_tongue"] == "CA"


def test_geoseal_service_cli_bridge_agentic_training_loop():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/agentic-training-loop",
        json={"goal": "nightly loop", "provider": "github"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["exit_code"] == 0
    assert body["data"]["extensions"]["github"] is not None
    assert body["data"]["extensions"]["huggingface"] is None


def test_geoseal_loop_dispatch_cli_json_github_coding():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "loop-dispatch",
            "--provider",
            "github",
            "--task",
            "coding",
            "--branch",
            "feat/test-loop",
            "--query",
            "smoke router",
            "--json",
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
    assert payload["schema_version"] == "geoseal-loop-dispatch-v1"
    assert payload["ok"] is True
    assert payload["provider"] == "github"
    assert payload["task"] == "trigger_router_coding"
    assert "gh" in payload["argv"]
    assert "feat/test-loop" in payload["argv"]
    assert "smoke router" in " ".join(payload["argv"])


def test_geoseal_loop_dispatch_cli_json_hf_bijective():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "loop-dispatch",
            "--provider",
            "huggingface",
            "--task",
            "bijective_gate",
            "--hf-model",
            "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1",
            "--json",
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
    assert payload["execute_env"]["SCBE_GATE_MODEL"] == "issdandavis/scbe-coding-agent-qwen-merged-coding-model-v1"
    assert str(payload["argv"][-1]).endswith("run_bijective_tongue_gate_hf.py")


def test_geoseal_loop_dispatch_execute_refused_without_gate_env():
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "loop-dispatch",
            "--provider",
            "github",
            "--task",
            "list_runs",
            "--permission-mode",
            "cloud-dispatch",
            "--execute",
        ],
        cwd=REPO_ROOT,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "SCBE_AGENTIC_LOOP_EXECUTE"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 2
    assert "SCBE_AGENTIC_LOOP_EXECUTE" in proc.stderr


def test_geoseal_service_cli_bridge_loop_dispatch():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/loop-dispatch",
        json={"provider": "github", "task": "list_runs"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["exit_code"] == 0
    assert body["data"]["ok"] is True
    assert body["data"]["argv"][0] == "gh"


def test_geoseal_service_loop_dispatch_execute_blocked_by_policy():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/loop-dispatch",
        json={
            "provider": "github",
            "task": "list_runs",
            "execute": True,
            "permission_mode": "observe",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["exit_code"] == 2
    assert body["data"]["schema_version"] == "scbe_agent_tool_policy_v1"
    assert body["data"]["ok"] is False


def test_geoseal_service_cli_bridge_code_packet():
    from fastapi.testclient import TestClient

    from src.api.geoseal_service import app

    client = TestClient(app)
    response = client.post(
        "/v1/geoseal/code-packet",
        json={"content": "def add(a, b):\n    return a + b\n", "language": "python"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["exit_code"] == 0
    assert "native_tokenization" in body["data"] or "transport_tokens" in body["data"]


def test_external_eval_manifest_validates():
    module = load_module(
        REPO_ROOT / "scripts" / "benchmark" / "external_agentic_eval_driver.py",
        "_external_agentic_eval_driver_test",
    )
    tasks = module.load_manifest(REPO_ROOT / "config" / "eval" / "external_agentic_eval_tasks.sample.json")
    validation = module.validate_tasks(tasks)
    assert validation["ok"], validation
    assert {task.suite for task in tasks} >= {
        "repo_native",
        "terminal_bench",
        "swe_bench",
    }


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
