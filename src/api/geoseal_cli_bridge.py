"""Bridge HTTP bodies to ``src.geoseal_cli`` handlers for GeoSeal local service."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

_SAFE_SUFFIX_RE = re.compile(r"^\.[A-Za-z0-9][A-Za-z0-9_.-]{0,15}$")


def _capture_cli(handler: Any, namespace: argparse.Namespace) -> tuple[int, str, str]:
    """Run a geoseal_cli command handler; capture stdout/stderr."""

    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = int(handler(namespace))
    return rc, out_buf.getvalue(), err_buf.getvalue()


def _safe_temp_suffix(source_name: object, default: str = ".rs") -> str:
    suffix = Path(str(source_name or "")).suffix or default
    return suffix if _SAFE_SUFFIX_RE.fullmatch(suffix) else default


def _trusted_temp_path(path_str: str) -> Path:
    path = Path(path_str).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if path.parent != temp_root and temp_root not in path.parents:
        raise ValueError(f"temp path outside system temp dir: {path}")
    return path


def _unlink_trusted_temp(path: Path) -> None:
    _trusted_temp_path(str(path)).unlink(missing_ok=True)


def dispatch_geoseal_command(command: str, body: dict[str, Any]) -> dict[str, Any]:
    """Dispatch JSON body to the matching CLI handler; return API envelope dict."""

    from src import geoseal_cli

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
                suffix = _safe_temp_suffix(body.get("source_name"), ".rs")
                fd, path_str = tempfile.mkstemp(suffix=suffix, prefix="geoseal_rt_")
                with os.fdopen(fd, "wb") as f:
                    f.write(str(content).encode("utf-8", errors="replace"))
                temp_path = _trusted_temp_path(path_str)
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
                    decoded = _trusted_temp_path(
                        str(
                            temp_path.with_name(
                                temp_path.stem + ".decoded" + temp_path.suffix
                            )
                        )
                    )
                    if decoded.exists():
                        _unlink_trusted_temp(decoded)
                    _unlink_trusted_temp(temp_path)
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
