from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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


def test_workflow_styleize_writes_github_and_n8n_assets(tmp_path: Path) -> None:
    config_path = tmp_path / "cli-context.json"
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

    workflow_path = ROOT / payload["workflow_path"]
    queue_path = ROOT / payload["queue_path"]
    assert workflow_path.exists()
    assert queue_path.exists()

    workflow_text = workflow_path.read_text(encoding="utf-8")
    queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))

    assert "workflow_dispatch:" in workflow_text
    assert "python scbe.py selftest" in workflow_text
    assert queue_payload["schema_version"] == "scbe_n8_style_queue_v1"
    assert len(queue_payload["items"]) == 2
    assert queue_payload["items"][1]["depends_on"] == [queue_payload["items"][0]["id"]]


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
