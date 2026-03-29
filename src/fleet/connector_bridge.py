"""
Connector bridge compatibility layer for external service workflows.

This repo currently needs only the NotebookLM lane for tests and HYDRA callers.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import httpx
except ModuleNotFoundError:  # optional runtime dep
    httpx = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKLM_SCRIPT = REPO_ROOT / "scripts" / "system" / "notebooklm_connector.py"
DEFAULT_AUTOMATIONS_URL = "http://127.0.0.1:8001/v1/automations/emit"


@dataclass
class ConnectorResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    platform: str = ""
    elapsed_ms: float = 0.0
    credits_earned: float = 0.0


class ConnectorCapability(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    WEBHOOK = "WEBHOOK"
    SEARCH = "SEARCH"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class ConnectorInfo:
    platform: str
    capabilities: set[ConnectorCapability] = field(default_factory=set)
    configured: bool = False
    description: str = ""


class ConnectorBridge:
    def __init__(self) -> None:
        self._infos: dict[str, ConnectorInfo] = {
            "notebooklm": ConnectorInfo(
                platform="notebooklm",
                capabilities={
                    ConnectorCapability.CREATE,
                    ConnectorCapability.UPDATE,
                    ConnectorCapability.SEARCH,
                    ConnectorCapability.READ,
                },
                configured=NOTEBOOKLM_SCRIPT.exists(),
                description="NotebookLM browser-first connector bridge",
            ),
            "automations": ConnectorInfo(
                platform="automations",
                capabilities={
                    ConnectorCapability.WRITE,
                    ConnectorCapability.WEBHOOK,
                    ConnectorCapability.CREATE,
                    ConnectorCapability.UPDATE,
                },
                configured=True,
                description="Local automation hub bridge",
            )
        }

    def list_connectors(self) -> list[ConnectorInfo]:
        return list(self._infos.values())

    def is_configured(self, platform: str) -> bool:
        info = self._infos.get(platform.lower())
        return bool(info and info.configured)

    async def _run_notebooklm_connector(self, args: list[str]) -> dict[str, Any]:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(NOTEBOOKLM_SCRIPT),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_ROOT),
        )
        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        try:
            parsed = json.loads(stdout_text) if stdout_text else {}
        except json.JSONDecodeError:
            parsed = {"ok": process.returncode == 0, "stdout": stdout_text, "stderr": stderr_text}
        if stderr_text and "stderr" not in parsed:
            parsed["stderr"] = stderr_text
        if "ok" not in parsed:
            parsed["ok"] = process.returncode == 0
        return parsed

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
        content_type = response.headers.get("content-type", "")
        parsed: Any
        if "application/json" in content_type.lower():
            parsed = response.json()
        else:
            parsed = response.text
        return {"status_code": response.status_code, "response": parsed}

    async def execute(self, platform: str, action: str, payload: dict[str, Any] | None = None) -> ConnectorResult:
        platform = platform.lower()
        payload = payload or {}
        started = time.perf_counter()
        try:
            if platform == "notebooklm":
                result = await self._execute_notebooklm(action, payload)
            elif platform == "automations":
                result = await self._execute_automations(action, payload)
            else:
                return ConnectorResult(
                    success=False, error=f"Unknown platform: {platform}", platform=platform
                )
        except Exception as exc:  # noqa: BLE001
            result = ConnectorResult(success=False, error=str(exc), platform=platform)
        result.platform = platform
        result.elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        return result

    async def _execute_notebooklm(self, action: str, payload: dict[str, Any]) -> ConnectorResult:
        action_map = {
            "create_notebook": "create-notebook",
            "resolve_notebook": "resolve-notebook",
            "add_source_url": "add-source-url",
            "seed_notebooks": "seed-notebooks",
            "profile": "profile",
        }
        cli_action = action_map.get(action)
        if not cli_action:
            return ConnectorResult(success=False, error=f"Unknown notebooklm action: {action}")

        args: list[str] = ["--action", cli_action]
        session_id = str(payload.get("session_id", "1")).strip() or "1"
        args.extend(["--session", session_id])

        workspace_url = str(payload.get("workspace_url", "")).strip()
        if workspace_url:
            args.extend(["--workspace-url", workspace_url])

        timeout_ms = payload.get("timeout_ms")
        if timeout_ms is not None:
            args.extend(["--timeout-ms", str(int(timeout_ms))])

        title = str(payload.get("title", "")).strip()
        if title:
            args.extend(["--title", title])

        notebook_url = str(payload.get("notebook_url", "")).strip()
        if notebook_url:
            args.extend(["--notebook-url", notebook_url])

        notebook_id = str(payload.get("notebook_id", "")).strip()
        if notebook_id:
            args.extend(["--notebook-id", notebook_id])

        name_prefix = str(payload.get("name_prefix", "")).strip()
        if name_prefix:
            args.extend(["--name-prefix", name_prefix])

        count = payload.get("count")
        if count is not None:
            args.extend(["--count", str(int(count))])

        source_url = str(payload.get("source_url", "")).strip()
        source_urls = payload.get("source_urls") or []
        if source_url:
            source_urls = [source_url, *list(source_urls)]

        if cli_action == "add-source-url" and not source_url and not source_urls:
            return ConnectorResult(success=False, error="source_url is required")

        for url in source_urls:
            if str(url).strip():
                args.extend(["--source-url", str(url).strip()])

        raw = await self._run_notebooklm_connector(args)
        ok = bool(raw.get("ok", False))
        return ConnectorResult(
            success=ok,
            data=raw if ok else {},
            error="" if ok else str(raw.get("error") or raw.get("stderr") or "NotebookLM connector failed"),
        )

    async def _execute_automations(self, action: str, payload: dict[str, Any]) -> ConnectorResult:
        if action != "trigger":
            return ConnectorResult(success=False, error=f"Unknown automations action: {action}")

        event = str(payload.get("event", "")).strip()
        if not event:
            return ConnectorResult(success=False, error="event is required")

        target_url = str(os.getenv("SCBE_AUTOMATIONS_URL", DEFAULT_AUTOMATIONS_URL)).strip()
        parsed = urlparse(target_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ConnectorResult(success=False, error="SCBE_AUTOMATIONS_URL must be a valid http(s) URL")

        body = {"event": event, "payload": payload.get("payload", {})}
        raw = await self._post_json(target_url, body)
        status_code = int(raw.get("status_code", 0))
        ok = 200 <= status_code < 300
        return ConnectorResult(
            success=ok,
            data=raw if ok else {},
            error="" if ok else f"automation hub returned status {status_code}",
        )
