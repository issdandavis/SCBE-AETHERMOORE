"""Bridge HTTP bodies to ``src.geoseal_cli`` handlers for GeoSeal local service."""

from __future__ import annotations

import argparse
import io
import json
import re
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

_SAFE_SUFFIX_RE = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9._-]{0,15}$")


def _reject_external_file_fields(body: dict[str, Any], *fields: str) -> None:
    """Keep the HTTP bridge content-only unless a command explicitly owns storage.

    The CLI can read local files because it runs in an operator shell. The HTTP
    service is a narrower bridge and should not turn request JSON into arbitrary
    filesystem reads or writes.
    """

    for field in fields:
        if body.get(field):
            raise ValueError(f"{field} is not accepted by the HTTP GeoSeal bridge; send inline content instead")


def _safe_temp_suffix(source_name: Any, default: str = ".rs") -> str:
    suffix = Path(str(source_name or "")).suffix or default
    return suffix if _SAFE_SUFFIX_RE.fullmatch(suffix) else default


def _capture_cli(handler: Any, namespace: argparse.Namespace) -> tuple[int, str, str]:
    """Run a geoseal_cli command handler; capture stdout/stderr."""

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = int(handler(namespace))
    return rc, out_buf.getvalue(), err_buf.getvalue()


def dispatch_geoseal_command(command: str, body: dict[str, Any]) -> dict[str, Any]:
    """Dispatch JSON body to the matching CLI handler; return API envelope dict."""

    from src import geoseal_cli

    if command == "code-packet":
        _reject_external_file_fields(body, "source_file")
        ns = argparse.Namespace(
            content=body.get("content") or "",
            source_file=None,
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

    if command == "call-switchboard":
        ns = argparse.Namespace(
            calls=None,
            inline_calls=json.dumps(body.get("calls") or []),
            request=json.dumps(body.get("request") or {}),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_call_switchboard, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "lightning-indexer":
        _reject_external_file_fields(body, "candidates_file")
        ns = argparse.Namespace(
            goal=body.get("goal") or "",
            inline_candidates=json.dumps(
                body.get("candidates") or body.get("inline_candidates") or []
            ),
            candidates_file=None,
            top_k=int(body.get("top_k") or 8),
            block_size=int(body.get("block_size") or 16),
            channel_budget=int(body.get("channel_budget") or 3),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_lightning_indexer, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "compile":
        intent = body.get("intent") or body.get("goal") or ""
        if isinstance(intent, str):
            intent_parts = intent.split()
        elif isinstance(intent, list):
            intent_parts = [str(part) for part in intent]
        else:
            intent_parts = [str(intent)]
        ns = argparse.Namespace(
            intent=intent_parts,
            permission_mode=body.get("permission_mode") or "observe",
            language=body.get("language") or "python",
            tool=body.get("tool"),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_compile, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "explain-route":
        _reject_external_file_fields(body, "source_file")
        forbid = body.get("forbid_provider")
        if isinstance(forbid, str):
            forbid = [forbid]
        if not isinstance(forbid, list):
            forbid = []
        ns = argparse.Namespace(
            content=body.get("content") or "",
            source_file=None,
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
        _reject_external_file_fields(body, "ledger")
        ns = argparse.Namespace(
            ledger=str(geoseal_cli.DEFAULT_LEDGER),
            limit=int(body.get("limit") or 20),
            type=body.get("type"),
            op=body.get("op"),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_history, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "replay":
        _reject_external_file_fields(body, "ledger")
        ns = argparse.Namespace(
            ledger=str(geoseal_cli.DEFAULT_LEDGER),
            index=body.get("index"),
            timeout=float(body.get("timeout") or 10.0),
            no_ledger=bool(body.get("no_ledger")),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_replay, ns)
        data = _parse_json_stdout(stdout, stderr, rc) if stdout.strip() else None
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "testing-cli":
        _reject_external_file_fields(body, "source_file")
        ns = argparse.Namespace(
            content=body.get("content") or "",
            source_file=None,
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
        _reject_external_file_fields(body, "output_dir")
        ns = argparse.Namespace(
            content=body.get("content") or "",
            language=body.get("language") or "python",
            output_dir=str(Path(tempfile.mkdtemp(prefix="geoseal_scaffold_"))),
            json=True,
        )
        rc, stdout, stderr = _capture_cli(geoseal_cli.cmd_project_scaffold, ns)
        data = _parse_json_stdout(stdout, stderr, rc)
        return {"exit_code": rc, "data": data, "stderr": stderr or None}

    if command == "code-roundtrip":
        content = body.get("content")
        source = body.get("source")
        temp_dir: tempfile.TemporaryDirectory[str] | None = None
        try:
            if content is not None and str(content).strip() != "":
                temp_dir = tempfile.TemporaryDirectory(prefix="geoseal_rt_")
                temp_path = Path(temp_dir.name) / "source.rs"
                temp_path.write_bytes(str(content).encode("utf-8", errors="replace"))
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
            if temp_dir is not None:
                temp_dir.cleanup()

    raise ValueError(f"unsupported GeoSeal bridge command: {command}")


def _parse_json_stdout(stdout: str, stderr: str, rc: int) -> Any:
    raw = stdout.strip()
    if not raw:
        return {"parse_error": "empty_stdout", "stderr": stderr, "exit_code": rc}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_stdout": raw, "stderr": stderr, "exit_code": rc}
