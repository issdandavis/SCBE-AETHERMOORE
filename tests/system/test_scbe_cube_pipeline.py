from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "scbe_cube_pipeline.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scbe_cube_pipeline_test_runtime", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cube = _load_module()


def _spec(
    tmp_path: Path,
    steps: list[dict] | None = None,
    *,
    runs_on: str = "ubuntu-latest",
    shell: str = "auto",
):
    return cube.build_pipeline_spec(
        name="test-cube",
        steps=steps
        or [
            {"id": "step_01_smoke", "name": "Smoke", "argv": ["python", "-c", "print('ok')"]},
            {"id": "step_02_check", "name": "Check", "argv": ["python", "-c", "print('checked')"]},
        ],
        triggers=["workflow_dispatch", "push"],
        cron="0 9 * * *",
        runs_on=runs_on,
        shell=shell,
        node_version="20",
        python_version="3.11",
        env={"SCBE_MODE": "test"},
        artifacts={
            "spec": "test-cube.pipeline.json",
            "github_workflow": "../gh/test-cube.yaml",
            "n8_queue": "../n8/test-cube.queue.json",
        },
        path_base="spec-dir",
    )


def test_cube_faces_share_ids_dependencies_and_command_digests(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec" / "test-cube.pipeline.json"
    workflow_path = tmp_path / "gh" / "test-cube.yaml"
    queue_path = tmp_path / "n8" / "test-cube.queue.json"
    payload = _spec(tmp_path)

    cube.write_bundle(spec_path, workflow_path, queue_path, payload)

    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    workflow_steps = [step for step in workflow["jobs"]["orchestrate"]["steps"] if "id" in step]

    assert len(payload["faces"]) == 6
    assert payload["workflow"]["shell"] == "bash"
    assert [step["id"] for step in workflow_steps] == [step["id"] for step in payload["steps"]]
    assert [item["id"] for item in queue["items"]] == [step["id"] for step in payload["steps"]]
    assert [item["depends_on"] for item in queue["items"]] == [step["depends_on"] for step in payload["steps"]]
    assert [item["command_sha256"] for item in queue["items"]] == [step["command_sha256"] for step in payload["steps"]]
    assert queue["pipeline_sha256"] == payload["pipeline_sha256"]
    assert queue["runtime"]["executor"] == "python-direct"
    assert queue["runtime"]["requires_run_id_env"] == "SCBE_CUBE_RUN_ID"
    assert cube.audit_surfaces(spec_path)["solved"] is True


def test_rotation_repairs_only_drifted_projections_and_is_idempotent(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec" / "test-cube.pipeline.json"
    workflow_path = tmp_path / "gh" / "test-cube.yaml"
    queue_path = tmp_path / "n8" / "test-cube.queue.json"
    payload = _spec(tmp_path)
    cube.write_bundle(spec_path, workflow_path, queue_path, payload)
    workflow_path.write_text("name: stale\n", encoding="utf-8")

    check = cube.rotate_surfaces(spec_path, apply=False)
    repair = cube.rotate_surfaces(spec_path, apply=True)
    second = cube.rotate_surfaces(spec_path, apply=True)

    assert check["before"]["solved"] is False
    assert check["after"]["solved"] is False
    assert check["before"]["issues"] == [{"code": "projection_drift", "path": str(workflow_path)}]
    assert repair["changed"] is True
    assert repair["after"]["solved"] is True
    assert second["changed"] is False
    assert second["after"]["solved"] is True


def test_projection_audit_accepts_windows_line_endings(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec" / "test-cube.pipeline.json"
    workflow_path = tmp_path / "gh" / "test-cube.yaml"
    queue_path = tmp_path / "n8" / "test-cube.queue.json"
    payload = _spec(tmp_path)
    cube.write_bundle(spec_path, workflow_path, queue_path, payload)
    workflow_path.write_bytes(workflow_path.read_bytes().replace(b"\n", b"\r\n"))
    queue_path.write_bytes(queue_path.read_bytes().replace(b"\n", b"\r\n"))

    report = cube.audit_surfaces(spec_path)

    assert report["solved"] is True
    assert report["issues"] == []


def test_windows_face_selects_pwsh_and_yaml_options_cannot_inject_fields(tmp_path: Path) -> None:
    payload = _spec(tmp_path, runs_on="windows-latest", shell="auto")
    spec_path = tmp_path / "spec" / "test-cube.pipeline.json"
    workflow = yaml.safe_load(cube.render_github_workflow(payload, spec_path))
    step = [item for item in workflow["jobs"]["orchestrate"]["steps"] if "id" in item][0]

    assert payload["workflow"]["shell"] == "pwsh"
    assert step["shell"] == "pwsh"
    assert "continue-on-error" not in step
    with pytest.raises(cube.PipelineError, match="single line"):
        _spec(tmp_path, shell="pwsh\ncontinue-on-error: true")


def test_pipeline_rejects_shell_programs_invalid_env_and_forward_dependencies(tmp_path: Path) -> None:
    with pytest.raises(cube.PipelineError, match="direct argv"):
        cube.parse_command("python scbe.py selftest && echo bypass")
    with pytest.raises(cube.PipelineError, match="invalid environment key"):
        cube.build_pipeline_spec(
            name="bad-env",
            steps=[{"id": "step_one", "name": "One", "argv": ["python", "-V"]}],
            triggers=["workflow_dispatch"],
            cron="0 9 * * *",
            runs_on="ubuntu-latest",
            shell="auto",
            node_version="20",
            python_version="3.11",
            env={"BAD-KEY": "value"},
            artifacts={"spec": "a.json", "github_workflow": "a.yml", "n8_queue": "a.queue.json"},
        )
    with pytest.raises(cube.PipelineError, match="earlier step"):
        cube.build_pipeline_spec(
            name="forward-edge",
            steps=[
                {
                    "id": "step_one",
                    "name": "One",
                    "argv": ["python", "-V"],
                    "depends_on": ["step_two"],
                },
                {"id": "step_two", "name": "Two", "argv": ["python", "-V"], "depends_on": []},
            ],
            triggers=["workflow_dispatch"],
            cron="0 9 * * *",
            runs_on="ubuntu-latest",
            shell="auto",
            node_version="20",
            python_version="3.11",
            env={},
            artifacts={"spec": "a.json", "github_workflow": "a.yml", "n8_queue": "a.queue.json"},
        )
    with pytest.raises(cube.PipelineError, match="cannot escape"):
        cube.build_pipeline_spec(
            name="escaping-artifact",
            steps=[{"id": "step_one", "name": "One", "argv": ["python", "-V"]}],
            triggers=["workflow_dispatch"],
            cron="0 9 * * *",
            runs_on="ubuntu-latest",
            shell="auto",
            node_version="20",
            python_version="3.11",
            env={},
            artifacts={
                "spec": "workflows/pipelines/a.json",
                "github_workflow": "../outside.yml",
                "n8_queue": "workflows/n8n/a.queue.json",
            },
        )


def test_direct_runner_executes_argv_and_emits_hashed_receipts(tmp_path: Path) -> None:
    first_marker = tmp_path / "first.txt"
    second_marker = tmp_path / "second.txt"
    spec_path = tmp_path / "spec" / "test-cube.pipeline.json"
    workflow_path = tmp_path / "gh" / "test-cube.yaml"
    queue_path = tmp_path / "n8" / "test-cube.queue.json"
    payload = _spec(
        tmp_path,
        steps=[
            {
                "id": "step_one",
                "name": "One",
                "argv": [
                    "python",
                    "-c",
                    "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('one')",
                    str(first_marker),
                ],
            },
            {
                "id": "step_two",
                "name": "Two",
                "argv": [
                    "python",
                    "-c",
                    "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('two')",
                    str(second_marker),
                ],
            },
        ],
    )
    cube.write_bundle(spec_path, workflow_path, queue_path, payload)

    result = cube.execute_pipeline(
        spec_path,
        run_id="test-success",
        receipt_dir=str(tmp_path / "receipts"),
    )

    assert result["ok"] is True
    assert first_marker.read_text(encoding="utf-8") == "one"
    assert second_marker.read_text(encoding="utf-8") == "two"
    assert [receipt["status"] for receipt in result["steps"]] == ["success", "success"]
    assert all("stdout" not in receipt for receipt in result["steps"])
    assert all(len(receipt["stdout_sha256"]) == 64 for receipt in result["steps"])


def test_failed_step_blocks_dependent_command(tmp_path: Path) -> None:
    forbidden_marker = tmp_path / "must-not-exist.txt"
    spec_path = tmp_path / "spec" / "test-cube.pipeline.json"
    payload = _spec(
        tmp_path,
        steps=[
            {"id": "step_fail", "name": "Fail", "argv": ["python", "-c", "raise SystemExit(7)"]},
            {
                "id": "step_blocked",
                "name": "Blocked",
                "argv": [
                    "python",
                    "-c",
                    "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('unsafe')",
                    str(forbidden_marker),
                ],
            },
        ],
    )
    cube.write_bundle(
        spec_path,
        tmp_path / "gh" / "test-cube.yaml",
        tmp_path / "n8" / "test-cube.queue.json",
        payload,
    )

    result = cube.execute_pipeline(
        spec_path,
        run_id="test-failure",
        receipt_dir=str(tmp_path / "receipts"),
    )

    assert result["ok"] is False
    assert [receipt["status"] for receipt in result["steps"]] == ["failure", "blocked"]
    assert result["steps"][1]["blocked_by"] == ["step_fail"]
    assert forbidden_marker.exists() is False


def test_runner_rejects_path_traversal_run_id(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec" / "test-cube.pipeline.json"
    payload = _spec(tmp_path)
    cube.write_bundle(
        spec_path,
        tmp_path / "gh" / "test-cube.yaml",
        tmp_path / "n8" / "test-cube.queue.json",
        payload,
    )

    with pytest.raises(cube.PipelineError, match="portable path component"):
        cube.execute_pipeline(spec_path, run_id="../escape")
