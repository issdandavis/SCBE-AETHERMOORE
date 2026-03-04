"""Multi-cloud routing for browser governance.

Primary goals:
- Route stateless validations to Lambda endpoint.
- Route stateful/session actions to Cloud Run endpoint.
- Fail over in <200ms budget when primary is unhealthy.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class CloudEndpoint:
    name: str
    url: str
    kind: str  # stateless | stateful
    timeout_ms: int = 180


@dataclass
class RouteResult:
    selected: str
    fallback_used: bool
    latency_ms: float
    response: Dict[str, Any]


class MultiCloudRouter:
    def __init__(
        self,
        lambda_endpoint: CloudEndpoint,
        cloud_run_endpoint: CloudEndpoint,
        failover_budget_ms: int = 200,
    ):
        self.lambda_endpoint = lambda_endpoint
        self.cloud_run_endpoint = cloud_run_endpoint
        self.failover_budget_ms = failover_budget_ms

    def _post(self, endpoint: CloudEndpoint, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.post(
                endpoint.url,
                json=payload,
                timeout=max(0.05, endpoint.timeout_ms / 1000.0),
            )
            if resp.status_code >= 300:
                return None
            if resp.headers.get("content-type", "").startswith("application/json"):
                return resp.json()
            return {"status": "ok", "raw": resp.text[:200]}
        except Exception:
            return None

    def route(self, action_kind: str, payload: Dict[str, Any]) -> RouteResult:
        """Route request based on action type and health/fallback results."""
        start = time.perf_counter()

        primary = self.lambda_endpoint if action_kind == "stateless" else self.cloud_run_endpoint
        secondary = self.cloud_run_endpoint if primary is self.lambda_endpoint else self.lambda_endpoint

        primary_resp = self._post(primary, payload)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if primary_resp is not None:
            return RouteResult(
                selected=primary.name,
                fallback_used=False,
                latency_ms=elapsed_ms,
                response=primary_resp,
            )

        if elapsed_ms >= self.failover_budget_ms:
            return RouteResult(
                selected=primary.name,
                fallback_used=False,
                latency_ms=elapsed_ms,
                response={"status": "failed", "reason": "primary_failed_budget_exceeded"},
            )

        secondary_resp = self._post(secondary, payload)
        total_ms = (time.perf_counter() - start) * 1000.0
        if secondary_resp is None:
            return RouteResult(
                selected=secondary.name,
                fallback_used=True,
                latency_ms=total_ms,
                response={"status": "failed", "reason": "both_clouds_failed"},
            )

        return RouteResult(
            selected=secondary.name,
            fallback_used=True,
            latency_ms=total_ms,
            response=secondary_resp,
        )
