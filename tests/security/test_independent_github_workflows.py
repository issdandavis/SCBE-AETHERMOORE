from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
PIPELINES = ROOT / "workflows" / "pipelines"
N8_QUEUES = ROOT / "workflows" / "n8n"


def _workflow_text(name: str) -> str:
    path = WORKFLOWS / name
    return path.read_text(encoding="utf-8")


def test_claude_workflows_are_local_only_and_do_not_call_external_ai_actions() -> None:
    for name in ("claude.yml", "claude-code-review.yml"):
        text = _workflow_text(name)
        yaml.safe_load(text)

        assert "anthropics/claude-code-action" not in text
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in text
        assert "id-token: write" not in text
        assert "pull-requests: write" not in text
        assert "External AI invoked: no" in text


def test_daily_dependency_audit_uses_one_rolling_issue_not_daily_issue_spam() -> None:
    text = _workflow_text("daily-dep-audit.yml")
    yaml.safe_load(text)

    assert "Dependency Vulnerabilities - rolling" in text
    assert "Dependency Vulnerabilities - ${today}" not in text
    assert "issues.update" in text
    assert "updates one rolling issue" in text


def test_nightly_ops_is_parseable_and_keeps_job_env_outside_steps() -> None:
    workflow_text = _workflow_text("nightly-ops.yml")
    workflow = yaml.safe_load(workflow_text)
    pipeline = json.loads((PIPELINES / "nightly-ops.pipeline.json").read_text(encoding="utf-8"))
    queue = json.loads((N8_QUEUES / "nightly-ops.queue.json").read_text(encoding="utf-8"))
    job = workflow["jobs"]["orchestrate"]
    generated_steps = [step for step in job["steps"] if "id" in step]

    assert workflow["permissions"] == {"contents": "read"}
    assert job["env"] == {"SCBE_MODE": "ci"}
    assert [step["uses"] for step in job["steps"] if "uses" in step] == [
        "actions/checkout@v6",
        "actions/setup-node@v6",
        "actions/setup-python@v6",
    ]
    assert [step["id"] for step in generated_steps] == [
        "step_01_smoke",
        "step_02_plan",
        "step_03_packetize",
    ]
    assert pipeline["schema_version"] == "scbe_cube_pipeline_v1"
    assert queue["schema_version"] == "scbe_n8_style_queue_v2"
    assert queue["pipeline_sha256"] == pipeline["pipeline_sha256"]
    assert [step["id"] for step in generated_steps] == [step["id"] for step in pipeline["steps"]]
    assert [item["id"] for item in queue["items"]] == [step["id"] for step in pipeline["steps"]]
    assert [item["depends_on"] for item in queue["items"]] == [step["depends_on"] for step in pipeline["steps"]]
    assert [item["command_sha256"] for item in queue["items"]] == [step["command_sha256"] for step in pipeline["steps"]]
    assert all("scripts/system/scbe_cube_pipeline.py run-step" in step["run"] for step in generated_steps)
    assert "C:/Users/" not in workflow_text
    assert "C:/Users/" not in json.dumps(queue)


def test_every_cube_pipeline_projection_is_portable_and_synchronized() -> None:
    specs = sorted(PIPELINES.glob("*.pipeline.json"))
    assert specs
    for spec_path in specs:
        pipeline = json.loads(spec_path.read_text(encoding="utf-8"))
        assert pipeline["path_base"] == "repo-root"
        workflow_path = ROOT / pipeline["artifacts"]["github_workflow"]
        queue_path = ROOT / pipeline["artifacts"]["n8_queue"]
        workflow_text = workflow_path.read_text(encoding="utf-8")
        queue_text = queue_path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(workflow_text)
        queue = json.loads(queue_text)
        generated_steps = [step for step in workflow["jobs"]["orchestrate"]["steps"] if "id" in step]

        assert queue["pipeline_sha256"] == pipeline["pipeline_sha256"]
        assert [step["id"] for step in generated_steps] == [step["id"] for step in pipeline["steps"]]
        assert [item["id"] for item in queue["items"]] == [step["id"] for step in pipeline["steps"]]
        assert [item["depends_on"] for item in queue["items"]] == [step["depends_on"] for step in pipeline["steps"]]
        assert [item["command_sha256"] for item in queue["items"]] == [
            step["command_sha256"] for step in pipeline["steps"]
        ]
        assert all("scripts/system/scbe_cube_pipeline.py run-step" in step["run"] for step in generated_steps)
        assert "C:/Users/" not in workflow_text
        assert "C:/Users/" not in queue_text
