#!/usr/bin/env python3
"""Deterministic, cross-platform SCBE pipeline projections and runner.

The canonical pipeline spec is the fixed cube center. GitHub Actions, the
n8-style queue, Windows/POSIX execution, validation, and run receipts are
projections (faces) of that same state. A rotation may change a projection;
it may not rewrite the canonical commands or dependency graph.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SCHEMA = "scbe_cube_pipeline_v1"
QUEUE_SCHEMA = "scbe_n8_style_queue_v2"
DEFAULT_TIMEOUT_SECONDS = 900
MAX_TIMEOUT_SECONDS = 3600
STEP_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,127}$")
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHELL_CONTROL_TOKENS = frozenset({"&&", "||", "|", ";", ">", ">>", "<", "<<"})
ALLOWED_TRIGGERS = frozenset({"workflow_dispatch", "push", "pull_request", "schedule"})
ALLOWED_SHELLS = frozenset({"bash", "pwsh", "powershell"})
ACTION_REFS = (
    "actions/checkout@v6",
    "actions/setup-node@v6",
    "actions/setup-python@v6",
)
FACES = (
    {"id": "canonical", "role": "fixed-center", "surface": "pipeline-spec"},
    {"id": "github", "role": "projection", "surface": "github-actions"},
    {"id": "n8", "role": "projection", "surface": "n8-style-queue"},
    {"id": "windows", "role": "execution", "surface": "direct-python-pwsh"},
    {"id": "posix", "role": "execution", "surface": "direct-python-bash"},
    {"id": "receipt", "role": "verification", "surface": "hashed-run-receipts"},
)


class PipelineError(ValueError):
    """Raised when a cube pipeline cannot be validated or executed safely."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    # Text projections may be checked out as CRLF on Windows and LF on Linux.
    # Universal-newline reads preserve semantic drift detection without making
    # the host's Git line-ending policy part of the pipeline state.
    normalized = path.read_text(encoding="utf-8")
    return _sha256_bytes(normalized.encode("utf-8"))


def command_sha256(argv: list[str]) -> str:
    return _sha256_bytes(_canonical_bytes(argv))


def pipeline_sha256(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "pipeline_sha256"}
    return _sha256_bytes(_canonical_bytes(unsigned))


def _single_line(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise PipelineError(f"{field} is required")
    if any(marker in text for marker in ("\r", "\n", "\x00")):
        raise PipelineError(f"{field} must be a single line")
    return text


def _yaml_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def resolve_shell(runs_on: str, shell: str) -> str:
    runs_on_value = _single_line(runs_on, "runs_on")
    shell_value = _single_line(shell, "shell").lower()
    if shell_value == "auto":
        shell_value = "pwsh" if "windows" in runs_on_value.lower() else "bash"
    if shell_value not in ALLOWED_SHELLS:
        allowed = ", ".join(sorted(ALLOWED_SHELLS | {"auto"}))
        raise PipelineError(f"shell must be one of: {allowed}")
    return shell_value


def parse_command(command: str) -> list[str]:
    command_value = str(command or "").strip()
    if not command_value:
        raise PipelineError("workflow command is required")
    try:
        argv = shlex.split(command_value, posix=True)
    except ValueError as exc:
        raise PipelineError(f"workflow command could not be parsed: {exc}") from exc
    if not argv:
        raise PipelineError("workflow command is required")
    controls = [token for token in argv if token in SHELL_CONTROL_TOKENS]
    if controls:
        raise PipelineError(
            "workflow commands must be direct argv, not shell programs; " f"unsupported token: {controls[0]}"
        )
    if any("\x00" in token for token in argv):
        raise PipelineError("workflow command contains a null byte")
    return argv


def _validate_artifact_ref(value: object, field: str) -> str:
    text = _single_line(value, field).replace("\\", "/")
    if PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute():
        raise PipelineError(f"{field} must be portable and relative to its declared path base")
    return text


def _validate_run_id(value: str) -> str:
    run_id = str(value or "").strip()
    if not RUN_ID_RE.fullmatch(run_id) or run_id in {".", ".."}:
        raise PipelineError("run_id must be a portable path component")
    return run_id


def build_pipeline_spec(
    *,
    name: str,
    steps: list[dict[str, Any]],
    triggers: list[str],
    cron: str,
    runs_on: str,
    shell: str,
    node_version: str,
    python_version: str,
    env: dict[str, str],
    artifacts: dict[str, str],
    path_base: str = "repo-root",
) -> dict[str, Any]:
    name_value = _single_line(name, "name")
    runs_on_value = _single_line(runs_on, "runs_on")
    shell_value = resolve_shell(runs_on_value, shell)
    node_value = _single_line(node_version, "node_version")
    python_value = _single_line(python_version, "python_version")
    cron_value = _single_line(cron or "0 9 * * *", "cron")
    trigger_values = _ordered_unique(triggers or ["workflow_dispatch"])
    unknown_triggers = sorted(set(trigger_values) - ALLOWED_TRIGGERS)
    if unknown_triggers:
        raise PipelineError(f"unsupported workflow trigger: {unknown_triggers[0]}")
    if path_base not in {"repo-root", "spec-dir"}:
        raise PipelineError("path_base must be repo-root or spec-dir")

    clean_env: dict[str, str] = {}
    for key, value in sorted(env.items()):
        key_value = _single_line(key, "environment key")
        if not ENV_KEY_RE.fullmatch(key_value):
            raise PipelineError(f"invalid environment key: {key_value}")
        clean_env[key_value] = _single_line(value, f"environment value for {key_value}")

    clean_artifacts = {
        key: _validate_artifact_ref(artifacts[key], f"artifacts.{key}")
        for key in ("spec", "github_workflow", "n8_queue")
    }
    if path_base == "repo-root":
        for key, reference in clean_artifacts.items():
            if ".." in PurePosixPath(reference).parts:
                raise PipelineError(f"artifacts.{key} cannot escape the repository root")

    clean_steps: list[dict[str, Any]] = []
    previous_id = ""
    for raw_step in steps:
        step_id = _single_line(raw_step.get("id"), "step id")
        if not STEP_ID_RE.fullmatch(step_id):
            raise PipelineError(f"invalid step id: {step_id}")
        label = _single_line(raw_step.get("name") or raw_step.get("label"), f"step {step_id} label")
        raw_argv = raw_step.get("argv")
        argv = (
            [str(token) for token in raw_argv]
            if isinstance(raw_argv, list)
            else parse_command(raw_step.get("command", ""))
        )
        depends_on = raw_step.get("depends_on")
        if depends_on is None:
            dependencies = [previous_id] if previous_id else []
        elif isinstance(depends_on, list):
            dependencies = [str(value) for value in depends_on]
        else:
            raise PipelineError(f"step {step_id} depends_on must be a list")
        timeout_seconds = int(raw_step.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
        clean_steps.append(
            {
                "id": step_id,
                "label": label,
                "argv": argv,
                "depends_on": dependencies,
                "timeout_seconds": timeout_seconds,
                "command_sha256": command_sha256(argv),
            }
        )
        previous_id = step_id

    payload: dict[str, Any] = {
        "schema_version": PIPELINE_SCHEMA,
        "name": name_value,
        "path_base": path_base,
        "faces": [dict(face) for face in FACES],
        "workflow": {
            "triggers": trigger_values,
            "cron": cron_value,
            "runs_on": runs_on_value,
            "shell": shell_value,
            "node_version": node_value,
            "python_version": python_value,
            "env": clean_env,
        },
        "artifacts": clean_artifacts,
        "steps": clean_steps,
    }
    payload["pipeline_sha256"] = pipeline_sha256(payload)
    errors = validate_pipeline_spec(payload)
    if errors:
        raise PipelineError("; ".join(errors))
    return payload


def validate_pipeline_spec(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["pipeline spec must be an object"]
    errors: list[str] = []
    if payload.get("schema_version") != PIPELINE_SCHEMA:
        errors.append(f"schema_version must be {PIPELINE_SCHEMA}")
    try:
        _single_line(payload.get("name"), "name")
    except PipelineError as exc:
        errors.append(str(exc))
    if payload.get("path_base") not in {"repo-root", "spec-dir"}:
        errors.append("path_base must be repo-root or spec-dir")

    workflow = payload.get("workflow")
    if not isinstance(workflow, dict):
        errors.append("workflow must be an object")
        workflow = {}
    triggers = workflow.get("triggers")
    if not isinstance(triggers, list) or not triggers:
        errors.append("workflow.triggers must be a non-empty list")
    elif len(triggers) != len(set(str(value) for value in triggers)):
        errors.append("workflow.triggers contains duplicates")
    elif set(str(value) for value in triggers) - ALLOWED_TRIGGERS:
        errors.append("workflow.triggers contains an unsupported trigger")
    try:
        resolve_shell(str(workflow.get("runs_on") or ""), str(workflow.get("shell") or ""))
    except PipelineError as exc:
        errors.append(str(exc))
    env = workflow.get("env")
    if not isinstance(env, dict):
        errors.append("workflow.env must be an object")
    else:
        for key in env:
            if not ENV_KEY_RE.fullmatch(str(key)):
                errors.append(f"invalid environment key: {key}")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be an object")
    else:
        for key in ("spec", "github_workflow", "n8_queue"):
            try:
                reference = _validate_artifact_ref(artifacts.get(key), f"artifacts.{key}")
                if payload.get("path_base") == "repo-root" and ".." in PurePosixPath(reference).parts:
                    errors.append(f"artifacts.{key} cannot escape the repository root")
            except PipelineError as exc:
                errors.append(str(exc))

    steps = payload.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty list")
        steps = []
    ids: list[str] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"steps[{index}] must be an object")
            continue
        step_id = str(step.get("id") or "")
        if not STEP_ID_RE.fullmatch(step_id):
            errors.append(f"invalid step id: {step_id or '<empty>'}")
        if step_id in ids:
            errors.append(f"duplicate step id: {step_id}")
        dependencies = step.get("depends_on")
        if not isinstance(dependencies, list):
            errors.append(f"step {step_id} depends_on must be a list")
            dependencies = []
        for dependency in dependencies:
            dependency_id = str(dependency)
            if dependency_id not in ids:
                errors.append(f"step {step_id} dependency must name an earlier step: {dependency_id}")
        argv = step.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(token, str) and token for token in argv):
            errors.append(f"step {step_id} argv must be a non-empty string list")
        elif any(token in SHELL_CONTROL_TOKENS or "\x00" in token for token in argv):
            errors.append(f"step {step_id} argv contains a shell control token")
        elif step.get("command_sha256") != command_sha256(argv):
            errors.append(f"step {step_id} command_sha256 mismatch")
        try:
            timeout_seconds = int(step.get("timeout_seconds", 0))
            if not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"step {step_id} timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")
        ids.append(step_id)

    expected_digest = pipeline_sha256(payload)
    if payload.get("pipeline_sha256") != expected_digest:
        errors.append("pipeline_sha256 mismatch")
    return errors


def _runner_spec_ref(spec_path: Path, payload: dict[str, Any]) -> str:
    if payload.get("path_base") == "repo-root":
        return str(payload["artifacts"]["spec"]).replace("\\", "/")
    return str(spec_path.resolve()).replace("\\", "/")


def _runner_argv(spec_ref: str, step_id: str) -> list[str]:
    return [
        "python",
        "scripts/system/scbe_cube_pipeline.py",
        "run-step",
        "--spec",
        spec_ref,
        "--step",
        step_id,
    ]


def _shell_join(argv: list[str], shell: str) -> str:
    if shell in {"pwsh", "powershell", "bash"}:
        return shlex.join(argv)
    raise PipelineError(f"unsupported shell: {shell}")


def render_github_workflow(payload: dict[str, Any], spec_path: Path) -> str:
    errors = validate_pipeline_spec(payload)
    if errors:
        raise PipelineError("; ".join(errors))
    workflow = payload["workflow"]
    lines = [f"name: {_yaml_quote(payload['name'])}", "on:"]
    for trigger in workflow["triggers"]:
        if trigger == "workflow_dispatch":
            lines.append("  workflow_dispatch:")
        elif trigger == "push":
            lines.extend(["  push:", "    branches: [main]"])
        elif trigger == "pull_request":
            lines.extend(["  pull_request:", "    branches: [main]"])
        elif trigger == "schedule":
            lines.extend(["  schedule:", f"    - cron: {_yaml_quote(workflow['cron'])}"])
    lines.extend(
        [
            "permissions:",
            "  contents: read",
            "",
            "jobs:",
            "  orchestrate:",
            f"    runs-on: {_yaml_quote(workflow['runs_on'])}",
        ]
    )
    if workflow["env"]:
        lines.append("    env:")
        for key, value in sorted(workflow["env"].items()):
            lines.append(f"      {_yaml_quote(key)}: {_yaml_quote(value)}")
    lines.extend(
        [
            "    steps:",
            "      - name: Checkout",
            f"        uses: {ACTION_REFS[0]}",
            "      - name: Setup Node",
            f"        uses: {ACTION_REFS[1]}",
            "        with:",
            f"          node-version: {_yaml_quote(workflow['node_version'])}",
            "      - name: Setup Python",
            f"        uses: {ACTION_REFS[2]}",
            "        with:",
            f"          python-version: {_yaml_quote(workflow['python_version'])}",
        ]
    )
    spec_ref = _runner_spec_ref(spec_path, payload)
    for step in payload["steps"]:
        command = _shell_join(_runner_argv(spec_ref, step["id"]), workflow["shell"])
        lines.extend(
            [
                f"      - name: {_yaml_quote(step['label'])}",
                f"        id: {step['id']}",
                f"        shell: {_yaml_quote(workflow['shell'])}",
                "        run: |",
                f"          {command}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_n8_queue(payload: dict[str, Any], spec_path: Path) -> dict[str, Any]:
    errors = validate_pipeline_spec(payload)
    if errors:
        raise PipelineError("; ".join(errors))
    spec_ref = _runner_spec_ref(spec_path, payload)
    items: list[dict[str, Any]] = []
    for index, step in enumerate(payload["steps"], start=1):
        argv = _runner_argv(spec_ref, step["id"])
        items.append(
            {
                "id": step["id"],
                "action": "scbe_cube_step",
                "label": step["label"],
                "argv": argv,
                "command": _shell_join(argv, payload["workflow"]["shell"]),
                "depends_on": list(step["depends_on"]),
                "command_sha256": step["command_sha256"],
                "metadata": {
                    "order": index,
                    "source": "scbe cube pipeline",
                    "pipeline_sha256": payload["pipeline_sha256"],
                    "github_workflow": payload["artifacts"]["github_workflow"],
                },
            }
        )
    return {
        "schema_version": QUEUE_SCHEMA,
        "workflow_name": payload["name"],
        "pipeline_sha256": payload["pipeline_sha256"],
        "triggers": list(payload["workflow"]["triggers"]),
        "runtime": {
            "executor": "python-direct",
            "shell": payload["workflow"]["shell"],
            "working_directory": "repo-root",
            "requires_run_id_env": "SCBE_CUBE_RUN_ID",
        },
        "env": dict(payload["workflow"]["env"]),
        "items": items,
    }


def _json_text(payload: object) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def write_bundle(
    spec_path: Path,
    workflow_path: Path,
    queue_path: Path,
    payload: dict[str, Any],
) -> None:
    atomic_write(spec_path, _json_text(payload))
    atomic_write(workflow_path, render_github_workflow(payload, spec_path))
    atomic_write(queue_path, _json_text(render_n8_queue(payload, spec_path)))


def load_pipeline_spec(spec_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PipelineError(f"pipeline spec not found: {spec_path}") from exc
    except json.JSONDecodeError as exc:
        raise PipelineError(f"pipeline spec is not valid JSON: {exc}") from exc
    errors = validate_pipeline_spec(payload)
    if errors:
        raise PipelineError("; ".join(errors))
    return payload


def resolve_artifact_path(spec_path: Path, payload: dict[str, Any], artifact: str) -> Path:
    reference = Path(str(payload["artifacts"][artifact]))
    if payload.get("path_base") == "repo-root":
        base = REPO_ROOT.resolve()
        allowed_root = base
    else:
        base = spec_path.resolve().parent
        allowed_root = base.parent
    resolved = (base / reference).resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise PipelineError(f"artifact path escapes its pipeline boundary: {artifact}") from exc
    return resolved


def audit_surfaces(spec_path: Path) -> dict[str, Any]:
    payload = load_pipeline_spec(spec_path)
    workflow_path = resolve_artifact_path(spec_path, payload, "github_workflow")
    queue_path = resolve_artifact_path(spec_path, payload, "n8_queue")
    expected_workflow = render_github_workflow(payload, spec_path)
    expected_queue = _json_text(render_n8_queue(payload, spec_path))
    expected = {workflow_path: expected_workflow, queue_path: expected_queue}
    issues: list[dict[str, str]] = []
    surfaces: list[dict[str, Any]] = []
    for path, expected_text in expected.items():
        expected_sha = _sha256_bytes(expected_text.encode("utf-8"))
        actual_sha = _sha256_file(path)
        if not path.exists():
            issues.append({"code": "missing_projection", "path": str(path)})
        elif actual_sha != expected_sha:
            issues.append({"code": "projection_drift", "path": str(path)})
        surfaces.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "actual_sha256": actual_sha,
                "expected_sha256": expected_sha,
            }
        )
    return {
        "schema_version": "scbe_cube_pipeline_audit_v1",
        "pipeline": payload["name"],
        "pipeline_sha256": payload["pipeline_sha256"],
        "solved": not issues,
        "issues": issues,
        "surfaces": surfaces,
    }


def rotate_surfaces(spec_path: Path, *, apply: bool) -> dict[str, Any]:
    before = audit_surfaces(spec_path)
    if apply and before["issues"]:
        payload = load_pipeline_spec(spec_path)
        workflow_path = resolve_artifact_path(spec_path, payload, "github_workflow")
        queue_path = resolve_artifact_path(spec_path, payload, "n8_queue")
        atomic_write(workflow_path, render_github_workflow(payload, spec_path))
        atomic_write(queue_path, _json_text(render_n8_queue(payload, spec_path)))
    after = audit_surfaces(spec_path)
    return {
        "schema_version": "scbe_cube_pipeline_rotation_v1",
        "applied": bool(apply),
        "changed": bool(before["issues"] and apply),
        "before": before,
        "after": after,
    }


def _resolve_executable(argv: list[str]) -> list[str]:
    resolved = list(argv)
    if resolved[0].lower() in {"python", "python3", "py"}:
        resolved[0] = sys.executable
    elif not Path(resolved[0]).is_file():
        executable = shutil.which(resolved[0])
        if executable:
            resolved[0] = executable
    return resolved


def _default_run_id() -> str:
    github_run = str(os.environ.get("GITHUB_RUN_ID") or "").strip()
    if github_run:
        attempt = str(os.environ.get("GITHUB_RUN_ATTEMPT") or "1").strip()
        return f"github-{github_run}-{attempt}"
    explicit = str(os.environ.get("SCBE_CUBE_RUN_ID") or "").strip()
    if explicit:
        return explicit
    return ""


def _receipt_directory(payload: dict[str, Any], run_id: str, requested: str = "") -> Path:
    if requested:
        return Path(requested).expanduser().resolve()
    runner_temp = str(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir())
    pipeline_dir = re.sub(r"[^A-Za-z0-9._-]+", "-", str(payload["name"])).strip("-.") or "pipeline"
    return (Path(runner_temp) / "scbe-cube" / pipeline_dir / run_id).resolve()


def _load_receipt(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def execute_step(
    spec_path: Path,
    step_id: str,
    *,
    run_id: str = "",
    receipt_dir: str = "",
) -> dict[str, Any]:
    payload = load_pipeline_spec(spec_path)
    step = next((item for item in payload["steps"] if item["id"] == step_id), None)
    if step is None:
        raise PipelineError(f"unknown pipeline step: {step_id}")
    effective_run_id = run_id or _default_run_id()
    if not effective_run_id:
        if step["depends_on"]:
            raise PipelineError("run_id is required for a dependent step; use the full run command locally")
        effective_run_id = f"manual-{uuid.uuid4().hex[:12]}"
    effective_run_id = _validate_run_id(effective_run_id)
    receipts = _receipt_directory(payload, effective_run_id, receipt_dir)
    receipts.mkdir(parents=True, exist_ok=True)
    receipt_path = receipts / f"{step_id}.json"

    blocked_by: list[str] = []
    for dependency in step["depends_on"]:
        dependency_receipt = _load_receipt(receipts / f"{dependency}.json")
        if (
            dependency_receipt.get("status") != "success"
            or dependency_receipt.get("pipeline_sha256") != payload["pipeline_sha256"]
            or dependency_receipt.get("run_id") != effective_run_id
        ):
            blocked_by.append(dependency)
    if blocked_by:
        receipt = {
            "schema_version": "scbe_cube_step_receipt_v1",
            "pipeline": payload["name"],
            "pipeline_sha256": payload["pipeline_sha256"],
            "run_id": effective_run_id,
            "step_id": step_id,
            "command_sha256": step["command_sha256"],
            "status": "blocked",
            "blocked_by": blocked_by,
            "returncode": 3,
        }
        atomic_write(receipt_path, _json_text(receipt))
        return receipt

    argv = _resolve_executable(step["argv"])
    env = os.environ.copy()
    env.update({str(key): str(value) for key, value in payload["workflow"]["env"].items()})
    started = time.monotonic()
    stdout = ""
    stderr = ""
    status = "failure"
    returncode = 1
    try:
        completed = subprocess.run(
            argv,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(step["timeout_seconds"]),
            check=False,
            shell=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        returncode = int(completed.returncode)
        status = "success" if returncode == 0 else "failure"
    except subprocess.TimeoutExpired as exc:
        stdout = str(exc.stdout or "")
        stderr = str(exc.stderr or "")
        status = "timeout"
        returncode = 124
    except FileNotFoundError as exc:
        stderr = str(exc)
        status = "missing_executable"
        returncode = 127
    duration_ms = round((time.monotonic() - started) * 1000)
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if stderr:
        print(stderr, file=sys.stderr, end="" if stderr.endswith("\n") else "\n")
    receipt = {
        "schema_version": "scbe_cube_step_receipt_v1",
        "pipeline": payload["name"],
        "pipeline_sha256": payload["pipeline_sha256"],
        "run_id": effective_run_id,
        "step_id": step_id,
        "command_sha256": step["command_sha256"],
        "status": status,
        "returncode": returncode,
        "duration_ms": duration_ms,
        "stdout_sha256": _sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": _sha256_bytes(stderr.encode("utf-8")),
    }
    atomic_write(receipt_path, _json_text(receipt))
    return receipt


def execute_pipeline(
    spec_path: Path,
    *,
    run_id: str = "",
    receipt_dir: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    payload = load_pipeline_spec(spec_path)
    effective_run_id = _validate_run_id(run_id or _default_run_id() or f"local-{uuid.uuid4().hex[:12]}")
    if dry_run:
        return {
            "schema_version": "scbe_cube_pipeline_run_v1",
            "pipeline": payload["name"],
            "pipeline_sha256": payload["pipeline_sha256"],
            "run_id": effective_run_id,
            "dry_run": True,
            "steps": [
                {"id": step["id"], "argv": step["argv"], "depends_on": step["depends_on"]} for step in payload["steps"]
            ],
            "ok": True,
        }
    receipts: list[dict[str, Any]] = []
    for step in payload["steps"]:
        receipts.append(
            execute_step(
                spec_path,
                step["id"],
                run_id=effective_run_id,
                receipt_dir=receipt_dir,
            )
        )
    return {
        "schema_version": "scbe_cube_pipeline_run_v1",
        "pipeline": payload["name"],
        "pipeline_sha256": payload["pipeline_sha256"],
        "run_id": effective_run_id,
        "dry_run": False,
        "steps": receipts,
        "ok": all(receipt["status"] == "success" for receipt in receipts),
    }


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SCBE cube pipeline projector, repairer, and direct runner")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate the canonical spec and every generated face")
    validate.add_argument("--spec", required=True)

    rotate = sub.add_parser("rotate", help="Check or deterministically repair generated faces")
    rotate.add_argument("--spec", required=True)
    rotate.add_argument("--apply", action="store_true")

    run = sub.add_parser("run", help="Run every step directly without a shell")
    run.add_argument("--spec", required=True)
    run.add_argument("--run-id", default="")
    run.add_argument("--receipt-dir", default="")
    run.add_argument("--dry-run", action="store_true")

    run_step = sub.add_parser("run-step", help="Run one step and enforce dependency receipts")
    run_step.add_argument("--spec", required=True)
    run_step.add_argument("--step", required=True)
    run_step.add_argument("--run-id", default="")
    run_step.add_argument("--receipt-dir", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        spec_path = Path(args.spec).expanduser().resolve()
        if args.command == "validate":
            report = audit_surfaces(spec_path)
            _print_json(report)
            return 0 if report["solved"] else 1
        if args.command == "rotate":
            report = rotate_surfaces(spec_path, apply=args.apply)
            _print_json(report)
            return 0 if report["after"]["solved"] else 1
        if args.command == "run":
            report = execute_pipeline(
                spec_path,
                run_id=args.run_id,
                receipt_dir=args.receipt_dir,
                dry_run=args.dry_run,
            )
            _print_json(report)
            return 0 if report["ok"] else 1
        if args.command == "run-step":
            receipt = execute_step(
                spec_path,
                args.step,
                run_id=args.run_id,
                receipt_dir=args.receipt_dir,
            )
            _print_json(receipt)
            return 0 if receipt["status"] == "success" else int(receipt["returncode"] or 1)
    except PipelineError as exc:
        _print_json({"ok": False, "error": str(exc)})
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
