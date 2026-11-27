from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_zero_job_failure_routes_to_canonical_cube_repair(monkeypatch) -> None:
    detector = _load("detect_failures_cube_test", ROOT / "scripts" / "ci" / "detect_failures.py")
    monkeypatch.setattr(
        detector,
        "run_gh",
        lambda _args: json.dumps(
            {
                "databaseId": 123,
                "name": ".github/workflows/nightly-ops.yml",
                "headBranch": "main",
                "conclusion": "failure",
                "status": "completed",
            }
        ),
    )
    monkeypatch.setattr(detector, "get_failing_jobs", lambda _run_id: [])
    monkeypatch.setattr(detector, "get_run_logs", lambda _run_id: "")

    report = detector.detect(run_id=123)

    assert report is not None
    assert len(report.failures) == 1
    failure = report.failures[0]
    assert failure.pattern_id == "workflow_zero_job"
    assert failure.fix_strategy == "cube_pipeline_repair"
    assert failure.file_path == "workflows/pipelines/nightly-ops.pipeline.json"
    assert report.fix_commands == [
        "python scripts/system/scbe_cube_pipeline.py rotate "
        "--spec workflows/pipelines/nightly-ops.pipeline.json --apply"
    ]


def test_cube_auto_fix_uses_direct_python_subprocess_and_receipt(monkeypatch, tmp_path: Path) -> None:
    fixer = _load("auto_fix_cube_test", ROOT / "scripts" / "ci" / "auto_fix.py")
    repo = tmp_path / "repo"
    spec_path = repo / "workflows" / "pipelines" / "nightly-ops.pipeline.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fixer, "REPO_ROOT", repo)
    seen: dict[str, object] = {}

    def fake_run(command: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        seen["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"changed": True}), stderr="")

    monkeypatch.setattr(fixer, "run", fake_run)

    changed = fixer.apply_cube_pipeline_repair(
        {"file_path": "workflows/pipelines/nightly-ops.pipeline.json"},
        dry_run=False,
    )

    command = seen["command"]
    assert changed is True
    assert command[0] == sys.executable
    assert command[-1] == "--apply"
    assert "rotate" in command
    assert not isinstance(command, str)


def test_cube_auto_fix_refuses_spec_outside_repository(monkeypatch, tmp_path: Path) -> None:
    fixer = _load("auto_fix_cube_boundary_test", ROOT / "scripts" / "ci" / "auto_fix.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.pipeline.json"
    outside.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fixer, "REPO_ROOT", repo)

    changed = fixer.apply_cube_pipeline_repair({"file_path": str(outside)}, dry_run=False)

    assert changed is False
