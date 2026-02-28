"""Workflow Trigger -- n8n bridge automation integration.

Provides governed automation: each workflow trigger goes through
the encoder before execution.

@layer Layer 13
@component AetherIDE.Workflow
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


class WorkflowTrigger:
    """Trigger n8n workflows through the bridge API."""

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:8001",
        api_key: str = "scbe-dev-key",
    ):
        self._bridge_url = bridge_url.rstrip("/")
        self._api_key = api_key

    def governance_scan(self, content: str) -> Dict[str, Any]:
        """Call /v1/governance/scan on the bridge."""
        return self._post("/v1/governance/scan", {"content": content})

    def tongue_encode(self, text: str) -> Dict[str, Any]:
        """Call /v1/tongue/encode on the bridge."""
        return self._post("/v1/tongue/encode", {"text": text})

    def submit_task(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call /v1/agent/task on the bridge."""
        return self._post("/v1/agent/task", {"type": task_type, **payload})

    def health_check(self) -> bool:
        """Check bridge health via /health."""
        try:
            result = self._get("/health")
            return result.get("status") == "ok" or result.get("status") == "healthy"
        except Exception:
            return False

    def _post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP POST helper."""
        url = f"{self._bridge_url}{path}"
        body = json.dumps(data).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self._api_key,
        }
        req = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (URLError, json.JSONDecodeError, OSError):
            return {"error": "bridge_unreachable"}

    def _get(self, path: str) -> Dict[str, Any]:
        """HTTP GET helper."""
        url = f"{self._bridge_url}{path}"
        headers = {"X-API-Key": self._api_key}
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except (URLError, json.JSONDecodeError, OSError):
            return {"error": "bridge_unreachable"}
