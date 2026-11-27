from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"


def _run_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_doctor_json_reports_tooling_and_paths() -> None:
    result = _run_cli("doctor", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_doctor_v1"
    assert "tooling" in payload
    assert "paths" in payload
    assert payload["paths"]["github_workflow_count"] >= 1


def test_use_and_config_round_trip(tmp_path: Path) -> None:
    config_path = tmp_path / "cli-context.json"
    use_result = _run_cli(
        "--config-path",
        str(config_path),
        "use",
        "studio",
        "--firebase-project",
        "scbe-dev",
        "--github-repo",
        "issdandavis/SCBE-AETHERMOORE",
        "--workflow-dir",
        ".github/workflows/custom",
        "--json",
    )
    assert use_result.returncode == 0, use_result.stderr
    use_payload = json.loads(use_result.stdout)
    assert use_payload["active_context"] == "studio"
    assert use_payload["context"]["firebase_project"] == "scbe-dev"

    get_result = _run_cli(
        "--config-path",
        str(config_path),
        "config",
        "get",
        "contexts.studio.github_repo",
        "--json",
    )
    assert get_result.returncode == 0, get_result.stderr
    get_payload = json.loads(get_result.stdout)
    assert get_payload["value"] == "issdandavis/SCBE-AETHERMOORE"


def test_parent_runtime_flags_survive_nested_parser_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "parent-flags.json"
    result = _run_cli(
        "--json",
        "--config-path",
        str(config_path),
        "config",
        "list",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["config_path"] == str(config_path)
    assert payload["config"]["defaults"]["pipeline_dir"] == "workflows/pipelines"


def test_workflow_styleize_writes_github_and_n8n_assets(tmp_path: Path) -> None:
    live_config_path = ROOT / ".scbe" / "cli-context.json"
    live_config_before = live_config_path.read_bytes() if live_config_path.exists() else None
    status_before = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    config_path = tmp_path / "cli-context.json"
    pipeline_dir = tmp_path / "pipelines"
    workflow_dir = tmp_path / "gh-workflows"
    queue_dir = tmp_path / "n8n"

    use_result = _run_cli(
        "--config-path",
        str(config_path),
        "use",
        "ops",
        "--workflow-dir",
        str(workflow_dir),
        "--n8n-dir",
        str(queue_dir),
        "--pipeline-dir",
        str(pipeline_dir),
    )
    assert use_result.returncode == 0, use_result.stderr

    result = _run_cli(
        "--config-path",
        str(config_path),
        "workflow",
        "styleize",
        "--name",
        "nightly-ops",
        "--trigger",
        "workflow_dispatch",
        "--trigger",
        "push",
        "--step",
        "Smoke::python scbe.py selftest",
        "--step",
        "Packetize::python scbe.py flow packetize --plan artifacts/flow_plans/demo.json",
        "--env",
        "SCBE_MODE=ci",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    pipeline_path = ROOT / payload["pipeline_path"]
    workflow_path = ROOT / payload["workflow_path"]
    queue_path = ROOT / payload["queue_path"]
    assert pipeline_path.parent == pipeline_dir
    assert workflow_path.parent == workflow_dir
    assert queue_path.parent == queue_dir
    assert pipeline_path.exists()
    assert workflow_path.exists()
    assert queue_path.exists()

    pipeline_payload = json.loads(pipeline_path.read_text(encoding="utf-8"))
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow_payload = yaml.safe_load(workflow_text)
    queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))

    assert "workflow_dispatch:" in workflow_text
    assert "scripts/system/scbe_cube_pipeline.py run-step" in workflow_text
    assert "python scbe.py selftest" not in workflow_text
    assert payload["schema_version"] == "scbe_workflow_styleize_v2"
    assert payload["solved"] is True
    assert pipeline_payload["schema_version"] == "scbe_cube_pipeline_v1"
    assert len(pipeline_payload["faces"]) == 6
    assert pipeline_payload["steps"][0]["argv"] == ["python", "scbe.py", "selftest"]
    assert workflow_payload["permissions"] == {"contents": "read"}
    job = workflow_payload["jobs"]["orchestrate"]
    assert job["env"] == {"SCBE_MODE": "ci"}
    assert [step["uses"] for step in job["steps"] if "uses" in step] == [
        "actions/checkout@v6",
        "actions/setup-node@v6",
        "actions/setup-python@v6",
    ]
    assert [step["id"] for step in job["steps"] if "id" in step] == [
        "step_01_smoke",
        "step_02_packetize",
    ]
    assert queue_payload["schema_version"] == "scbe_n8_style_queue_v2"
    assert queue_payload["pipeline_sha256"] == pipeline_payload["pipeline_sha256"]
    assert len(queue_payload["items"]) == 2
    assert queue_payload["items"][1]["depends_on"] == [queue_payload["items"][0]["id"]]
    assert [item["command_sha256"] for item in queue_payload["items"]] == [
        step["command_sha256"] for step in pipeline_payload["steps"]
    ]
    saved_config = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved_config["active_context"] == "ops"
    assert saved_config["contexts"]["ops"]["pipeline_dir"] == str(pipeline_dir)
    live_config_after = live_config_path.read_bytes() if live_config_path.exists() else None
    assert live_config_after == live_config_before
    status_after = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert status_after == status_before


def test_workflow_styleize_accepts_yaml_file_and_auto_selects_windows_shell(tmp_path: Path) -> None:
    pipeline_path = tmp_path / "windows.pipeline.json"
    workflow_path = tmp_path / "windows.yaml"
    queue_path = tmp_path / "windows.queue.json"
    result = _run_cli(
        "workflow",
        "styleize",
        "--name",
        "windows-cube",
        "--runs-on",
        "windows-latest",
        "--pipeline-path",
        str(pipeline_path),
        "--workflow-path",
        str(workflow_path),
        "--queue-path",
        str(queue_path),
        "--step",
        "Smoke::python scbe.py selftest",
        "--json",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert workflow_path.is_file()
    assert not (workflow_path / "windows-cube.yml").exists()
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    generated_steps = [step for step in workflow["jobs"]["orchestrate"]["steps"] if "id" in step]
    assert workflow["jobs"]["orchestrate"]["runs-on"] == "windows-latest"
    assert generated_steps[0]["shell"] == "pwsh"


def test_workflow_styleize_rejects_shell_field_injection(tmp_path: Path) -> None:
    result = _run_cli(
        "workflow",
        "styleize",
        "--name",
        "unsafe-cube",
        "--pipeline-path",
        str(tmp_path / "unsafe.pipeline.json"),
        "--workflow-path",
        str(tmp_path / "unsafe.yml"),
        "--queue-path",
        str(tmp_path / "unsafe.queue.json"),
        "--shell",
        "pwsh\ncontinue-on-error: true",
        "--step",
        "Smoke::python scbe.py selftest",
    )

    assert result.returncode == 2
    assert "single line" in result.stdout
    assert not (tmp_path / "unsafe.yml").exists()


def test_colab_status_reports_bridge_and_notebooks() -> None:
    result = _run_cli("colab", "status", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_colab_status_v1"
    assert payload["notebook_count"] >= 1
    assert payload["bridge"]["terminal_method_preferred"] is True


def test_colab_url_resolves_catalog_alias() -> None:
    result = _run_cli("colab", "url", "finetune", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_colab_url_v1"
    assert payload["name"] == "scbe-finetune-free"
    assert "colab.research.google.com" in payload["colab_url"]


def test_colab_review_reports_readiness_and_warnings() -> None:
    result = _run_cli("colab", "review", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_colab_review_v1"
    assert payload["notebook_count"] >= 10
    reviews = {row["name"]: row for row in payload["reviews"]}
    assert "aethermoor-datagen" in reviews
    assert any("demo repo" in warning for warning in reviews["aethermoor-datagen"]["warnings"])
