"""Bridge HTTP bodies to ``src.geoseal_cli`` handlers for GeoSeal local service."""

from __future__ import annotations

import argparse
import io
import json
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any


def _geoseal_body_requests_execute(command: str, body: dict[str, Any]) -> bool:
    c = (command or "").strip().lower()
    if c in ("loop-dispatch", "testing-cli", "code-roundtrip"):
        return bool(body.get("execute"))
    return False


def _capture_cli(handler: Any, namespace: argparse.Namespace) -> tuple[int, str, str]:
    """Run a geoseal_cli command handler; capture stdout/stderr."""

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = int(handler(namespace))
    return rc, out_buf.getvalue(), err_buf.getvalue()


def dispatch_geoseal_command(command: str, body: dict[str, Any]) -> dict[str, Any]:
    """Dispatch JSON body to the matching CLI handler; return API envelope dict."""

    from src.coding_spine.agent_tool_policy import (
        evaluate_harness_tool_policy,
        geoseal_command_to_tool_class,
    )

    if os.environ.get("SCBE_SKIP_AGENT_TOOL_POLICY", "").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        permission_mode = (
            str(body.get("permission_mode") or "").strip()
            or os.environ.get("SCBE_AGENT_PERMISSION_MODE", "").strip()
            or "observe"
        )
        wants_exec = _geoseal_body_requests_execute(command, body)
        tc = geoseal_command_to_tool_class(command, execute=wants_exec)
        pol = evaluate_harness_tool_policy(permission_mode=permission_mode, tool_class=tc)
        if not pol.get("ok"):
            return {"exit_code": 2, "data": pol, "stderr": pol.get("reason")}

    from src import geoseal_cli

    if command == "skill-tools":
        from pathlib import Path

        from src.coding_spine.skill_harness_tools import build_harness_skill_tools_v1

        root = Path(__file__).resolve().parents[2]
        data = build_harness_skill_tools_v1(repo_root=root)
        return {"exit_code": 0, "data": data, "stderr": None}

    if command == "code-packet":
        ns = argparse.Namespace(
            content=body.get("content") or "",
            source_file=body.get("source_file"),
            source_name=body.get("source_name"),
            language=body.get("language") or "python",
            backend=body.get("backend"),
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_code_packet, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "backend-registry":
        ns = argparse.Namespace(json=True)
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_backend_registry, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "agent-harness":
        ns = argparse.Namespace(
            goal=body.get("goal") or "",
            language=body.get("language") or "python",
            permission_mode=body.get("permission_mode") or "observe",
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_agent_harness, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "hydra-bridge":
        ns = argparse.Namespace(
            goal=body.get("goal") or "",
            language=body.get("language") or "python",
            permission_mode=body.get("permission_mode") or "observe",
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_hydra_bridge, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "agentic-training-loop":
        ns = argparse.Namespace(
            goal=body.get("goal") or "",
            provider=body.get("provider") or "both",
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_agentic_training_loop, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "loop-dispatch":
        ns = argparse.Namespace(
            provider=body.get("provider") or "",
            task=body.get("task") or "",
            query=body.get("query") or "",
            branch=body.get("branch") or "",
            run_id=body.get("run_id") or body.get("run-id") or "",
            hf_model=body.get("hf_model") or body.get("hf-model") or "",
            hf_dataset=body.get("hf_dataset") or body.get("hf-dataset") or "",
            execute=bool(body.get("execute")),
            permission_mode=str(
                body.get("permission_mode")
                or os.environ.get("SCBE_AGENT_PERMISSION_MODE", "")
                or "observe"
            ),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_loop_dispatch, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "explain-route":
        forbid = body.get("forbid_provider")
        if isinstance(forbid, str):
            forbid = [forbid]
        if not isinstance(forbid, list):
            forbid = []
        ns = argparse.Namespace(
            content=body.get("content") or "",
            source_file=body.get("source_file"),
            source_name=body.get("source_name"),
            language=body.get("language") or "python",
            tongue=body.get("tongue"),
            provider=body.get("provider"),
            forbid_provider=forbid,
            small_first=bool(body.get("small_first")),
            governance_tier=body.get("governance_tier") or "ALLOW",
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_explain_route, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "history":
        ns = argparse.Namespace(
            ledger=body.get("ledger") or str(geoseal_cli.DEFAULT_LEDGER),
            limit=int(body.get("limit") or 20),
            type=body.get("type"),
            op=body.get("op"),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_history, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "replay":
        ns = argparse.Namespace(
            ledger=body.get("ledger") or str(geoseal_cli.DEFAULT_LEDGER),
            index=body.get("index"),
            timeout=float(body.get("timeout") or 10.0),
            no_ledger=bool(body.get("no_ledger")),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_replay, ns)
        data = _parse_json_stdout(stdout, stderr, rc) if stdout.strip() else None
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "testing-cli":
        ns = argparse.Namespace(
            content=body.get("content") or "",
            source_file=body.get("source_file"),
            language=body.get("language") or "python",
            execute=bool(body.get("execute")),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_testing_cli, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "project-scaffold":
        if not body.get("content"):
            raise ValueError("content is required for project-scaffold")
        if not body.get("output_dir"):
            raise ValueError("output_dir is required for project-scaffold")
        ns = argparse.Namespace(
            content=body.get("content") or "",
            language=body.get("language") or "python",
            output_dir=body.get("output_dir"),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_project_scaffold, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "code-roundtrip":
        content = body.get("content")
        source = body.get("source")
        temp_path: Path | None = None
        try:
            if content is not None and str(content).strip() != "":
                stem = body.get("source_name") or "geoseal_roundtrip"
                suffix = Path(stem).suffix or ".rs"
                fd, path_str = tempfile.mkstemp(suffix=suffix, prefix="geoseal_rt_")

                with os.fdopen(fd, "wb") as f:
                    f.write(str(content).encode("utf-8", errors="replace"))
                temp_path = Path(path_str)
                source = str(temp_path)
            if not source:
                raise ValueError("source or content is required for code-roundtrip")
            ns = argparse.Namespace(
                source=source,
                lang=body.get("lang") or "rust",
                tongue=body.get("tongue") or "RU",
                execute=bool(body.get("execute")),
                json=True,
            )
            rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_code_roundtrip, ns)
            data = _parse_json_stdout(stdout, stderr, rc)
            return {"exit_code": rc, "data": data, "stderr": stderr or None}
        finally:
            if temp_path is not None and temp_path.exists():
                try:
                    decoded = temp_path.with_name(temp_path.stem + ".decoded" + temp_path.suffix)
                    if decoded.exists():
                        decoded.unlink(missing_ok=True)
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    raise ValueError(f"unsupported GeoSeal bridge command: {command}")


def _parse_json_stdout(stdout: str, stderr: str, rc: int) -> Any:
    raw = stdout.strip()
    if not raw:
        return {"parse_error": "empty_stdout", "stderr": stderr, "exit_code": rc}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_stdout": raw, "stderr": stderr, "exit_code": rc}
