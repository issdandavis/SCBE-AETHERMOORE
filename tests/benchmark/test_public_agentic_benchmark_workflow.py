from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "public-agentic-benchmarks.yml"


def test_scored_aider_workflow_exports_visible_diagnostics() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "GeoSeal Aider adapter preflight" in workflow
    assert "aider_polyglot_preflight" in workflow
    assert "aider_polyglot_scored/diagnostics" in workflow
    assert 'find "${latest_dir}" -name ".aider.results.json"' in workflow
    assert ".chat.history.md" in workflow
    assert "${safe_name}.results.json" in workflow


def test_scored_aider_workflow_patches_flaky_deadsnakes_dockerfile() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "FROM buildpack-deps:noble" in workflow
    assert "deadsnakes/ppa" in workflow
    assert "Aider benchmark Dockerfile changed; refusing silent patch" in workflow
    assert "Ubuntu noble's native Python" in workflow


def test_scored_aider_workflow_uses_venv_for_noble_pep668() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "python3 -m venv /opt/aider-venv" in workflow
    assert 'ENV PATH="/opt/aider-venv/bin:$PATH"' in workflow
    assert "RUN pip install --no-cache-dir --upgrade pip uv" in workflow
    assert "RUN uv pip install --no-cache-dir -e /aider[dev]" in workflow
    assert "--system --no-cache-dir -e /aider[dev]" in workflow
    assert "Aider benchmark Dockerfile pip install block changed; refusing silent patch" in workflow


def test_scored_aider_workflow_can_select_openai_compatible_provider() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "api_provider:" in workflow
    assert "AIDER_API_PROVIDER" in workflow
    assert "HF_TOKEN" in workflow
    assert "NVIDIA_API_KEY" in workflow
    assert "https://router.huggingface.co/v1" in workflow
    assert "https://integrate.api.nvidia.com/v1" in workflow
    assert "AIDER_OPENAI_API_BASE" in workflow
    assert '"${api_env_args[@]}"' in workflow


def test_scored_aider_workflow_defaults_to_low_cost_guard() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'default: "huggingface"' in workflow
    assert 'default: "openai/Qwen/Qwen2.5-Coder-32B-Instruct"' in workflow
    assert "cost_mode:" in workflow
    assert 'default: "free_remote"' in workflow
    assert "BENCHMARK_COST_MODE" in workflow
    assert "local_artifact_only forbids live scored model calls" in workflow
    assert "free_remote scored runs only allow api_provider=huggingface" in workflow
    assert "num_tests must be a positive integer under free_remote" in workflow
    assert "free_remote scored runs are capped at num_tests=1" in workflow
    assert "paid_allowed set explicitly" in workflow
