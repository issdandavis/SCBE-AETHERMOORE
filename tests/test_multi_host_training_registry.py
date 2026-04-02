import json
import subprocess
import sys
from pathlib import Path


SCRIPT = "scripts/system/multi_host_training_registry.py"


def _run(*args: str, cwd: str = "C:/Users/issda/SCBE-AETHERMOORE"):
    return subprocess.run(
        [sys.executable, SCRIPT, *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def test_register_and_list_runs(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"

    result = _run(
        "--registry",
        str(registry),
        "register",
        "--run-id",
        "colab-run-1",
        "--host",
        "colab",
        "--provider",
        "hf",
        "--role",
        "textgen",
        "--base-model",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--dataset-repo",
        "issdandavis/scbe-aethermoore-training-data",
        "--dataset-revision",
        "rev-001",
        "--artifact-id",
        "issdandavis/scbe-colab-run-1",
        "--artifact-uri",
        "hf://issdandavis/scbe-colab-run-1",
        "--quality",
        "0.82",
        "--safety",
        "0.98",
        "--latency-ms-p95",
        "110",
        "--cost-per-1k-tokens",
        "0.75",
    )

    assert result.returncode == 0, result.stderr

    listing = _run("--registry", str(registry), "list")
    assert listing.returncode == 0, listing.stderr
    payload = json.loads(listing.stdout)
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["run_id"] == "colab-run-1"
    assert payload["runs"][0]["host"] == "colab"


def test_promote_replaces_previous_run_for_same_track(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    shared_args = [
        "--registry",
        str(registry),
        "register",
        "--provider",
        "hf",
        "--role",
        "textgen",
        "--base-model",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--dataset-repo",
        "issdandavis/scbe-aethermoore-training-data",
        "--dataset-revision",
        "rev-001",
        "--quality",
        "0.82",
        "--safety",
        "0.98",
        "--latency-ms-p95",
        "110",
        "--cost-per-1k-tokens",
        "0.75",
    ]

    first = _run(
        *shared_args,
        "--run-id",
        "colab-run-1",
        "--host",
        "colab",
        "--artifact-id",
        "issdandavis/scbe-colab-run-1",
        "--artifact-uri",
        "hf://issdandavis/scbe-colab-run-1",
    )
    second = _run(
        *shared_args,
        "--run-id",
        "kaggle-run-1",
        "--host",
        "kaggle",
        "--artifact-id",
        "issdandavis/scbe-kaggle-run-1",
        "--artifact-uri",
        "hf://issdandavis/scbe-kaggle-run-1",
    )
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    promote_first = _run("--registry", str(registry), "promote", "--run-id", "colab-run-1")
    assert promote_first.returncode == 0, promote_first.stderr
    promote_second = _run("--registry", str(registry), "promote", "--run-id", "kaggle-run-1")
    assert promote_second.returncode == 0, promote_second.stderr

    payload = json.loads(registry.read_text(encoding="utf-8"))
    assert payload["promotions"]["textgen"]["run_id"] == "kaggle-run-1"
    statuses = {run["run_id"]: run["status"] for run in payload["runs"]}
    assert statuses["colab-run-1"] == "candidate"
    assert statuses["kaggle-run-1"] == "promoted"


def test_export_provider_manifest_uses_promoted_runs(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    manifest = tmp_path / "hf_manifest.json"

    register = _run(
        "--registry",
        str(registry),
        "register",
        "--run-id",
        "colab-run-1",
        "--host",
        "colab",
        "--provider",
        "hf",
        "--role",
        "textgen",
        "--base-model",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--dataset-repo",
        "issdandavis/scbe-aethermoore-training-data",
        "--dataset-revision",
        "rev-001",
        "--artifact-id",
        "issdandavis/scbe-colab-run-1",
        "--artifact-uri",
        "hf://issdandavis/scbe-colab-run-1",
        "--quality",
        "0.85",
        "--safety",
        "0.99",
        "--latency-ms-p95",
        "95",
        "--cost-per-1k-tokens",
        "0.7",
    )
    assert register.returncode == 0, register.stderr
    promote = _run("--registry", str(registry), "promote", "--run-id", "colab-run-1")
    assert promote.returncode == 0, promote.stderr

    export_result = _run(
        "--registry",
        str(registry),
        "export-provider-manifest",
        "--provider",
        "hf",
        "--output",
        str(manifest),
    )
    assert export_result.returncode == 0, export_result.stderr

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["provider"] == "hf"
    assert len(payload["artifacts"]) == 1
    artifact = payload["artifacts"][0]
    assert artifact["id"] == "issdandavis/scbe-colab-run-1"
    assert artifact["role"] == "textgen"
    assert artifact["metadata"]["host"] == "colab"
