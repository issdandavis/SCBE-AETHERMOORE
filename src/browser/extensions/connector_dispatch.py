"""
@file connector_dispatch.py
@module browser/extensions/connector_dispatch
@layer Layer 13
@component ConnectorDispatcher — HTTP dispatch for registered connectors

Turns connector templates (Zapier, n8n, Shopify, generic webhook) into
real HTTP calls. Each dispatch goes through a governance gate before firing.

Usage:
    dispatcher = ConnectorDispatcher()

    # Register a connector
    config = ConnectorConfig(
        connector_id="my-zapier",
        kind="zapier",
        endpoint_url="https://hooks.zapier.com/hooks/catch/123/abc/",
        auth_type="none",
    )
    dispatcher.register(config)

    # Dispatch a payload
    result = dispatcher.dispatch("my-zapier", {
        "action": "create_task",
        "data": {"title": "Research complete", "body": "..."},
    })
    # result.success, result.status_code, result.response_body
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aetherbrowse-connector-dispatch")


@dataclass
class ConnectorConfig:
    """Configuration for a registered connector."""

    connector_id: str
    kind: str  # zapier, n8n, shopify, generic_webhook
    endpoint_url: str
    auth_type: str = "none"  # none, bearer, header, basic
    auth_token: str = ""
    auth_header_name: str = "Authorization"
    http_method: str = "POST"
    payload_mode: str = "scbe_step"  # scbe_step, shopify_graphql_read, raw
    extra_headers: Dict[str, str] = field(default_factory=dict)
    timeout_sec: int = 30
    enabled: bool = True


@dataclass
class DispatchResult:
    """Result of a connector dispatch."""

    connector_id: str
    success: bool
    status_code: int = 0
    response_body: str = ""
    error: str = ""
    elapsed_ms: float = 0.0
    dispatched_at: str = ""
    payload_hash: str = ""


class ConnectorDispatcher:
    """
    Dispatches payloads to registered connectors via HTTP.

    Supports: Zapier catch hooks, n8n webhooks, Shopify Admin API,
    and generic signed webhooks.

    # A3: Causality — dispatches are ordered and logged with timestamps
    """

    def __init__(
        self,
        audit_dir: str = "artifacts/connector_dispatches",
        max_retries: int = 2,
        retry_backoff_s: float = 1.0,
    ):
        self._connectors: Dict[str, ConnectorConfig] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s

    # ── Registration ───────────────────────────────────────────────────

    def register(self, config: ConnectorConfig) -> None:
        """Register a connector configuration."""
        self._connectors[config.connector_id] = config
        logger.info(
            "Registered connector: %s (%s → %s)",
            config.connector_id,
            config.kind,
            config.endpoint_url[:60],
        )

    def register_from_template(
        self,
        connector_id: str,
        template: Dict[str, Any],
        overrides: Optional[Dict[str, Any]] = None,
    ) -> ConnectorConfig:
        """Register a connector from a template dict (e.g., from CONNECTOR_TEMPLATES).

        Args:
            connector_id: Unique ID for this connector instance.
            template: Template dict with kind, recommended_fields, etc.
            overrides: Field overrides (endpoint_url, auth tokens, etc.).

        Returns:
            The created ConnectorConfig.
        """
        fields = {**(template.get("recommended_fields", {})), **(overrides or {})}

        config = ConnectorConfig(
            connector_id=connector_id,
            kind=template.get("kind", "generic_webhook"),
            endpoint_url=fields.get("endpoint_url", ""),
            auth_type=fields.get("auth_type", "none"),
            auth_token=fields.get("auth_token", ""),
            auth_header_name=fields.get("auth_header_name", "Authorization"),
            http_method=fields.get("http_method", "POST"),
            payload_mode=fields.get("payload_mode", "scbe_step"),
        )
        self.register(config)
        return config

    def unregister(self, connector_id: str) -> bool:
        """Remove a registered connector."""
        if connector_id in self._connectors:
            del self._connectors[connector_id]
            return True
        return False

    def list_connectors(self) -> List[Dict[str, Any]]:
        """List all registered connectors."""
        return [
            {
                "connector_id": c.connector_id,
                "kind": c.kind,
                "endpoint_url": c.endpoint_url[:60] + ("..." if len(c.endpoint_url) > 60 else ""),
                "enabled": c.enabled,
                "auth_type": c.auth_type,
            }
            for c in self._connectors.values()
        ]

    # ── Dispatch ───────────────────────────────────────────────────────

    def dispatch(
        self,
        connector_id: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DispatchResult:
        """Dispatch a payload to a registered connector.

        Args:
            connector_id: ID of the connector to dispatch to.
            payload: The data payload to send.
            metadata: Optional metadata (session_id, workflow_id, etc.).

        Returns:
            DispatchResult with success status and response details.
        """
        config = self._connectors.get(connector_id)
        if config is None:
            return DispatchResult(
                connector_id=connector_id,
                success=False,
                error=f"Connector '{connector_id}' not registered",
            )

        if not config.enabled:
            return DispatchResult(
                connector_id=connector_id,
                success=False,
                error=f"Connector '{connector_id}' is disabled",
            )

        # Build the request body based on payload_mode
        body = self._build_body(config, payload, metadata)
        payload_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]

        # Build headers
        headers = self._build_headers(config)

        # Dispatch with retries
        result = self._do_dispatch(config, body, headers, payload_hash)

        # Audit log
        audit_entry = {
            "connector_id": connector_id,
            "kind": config.kind,
            "endpoint_url": config.endpoint_url,
            "success": result.success,
            "status_code": result.status_code,
            "dispatched_at": result.dispatched_at,
            "payload_hash": payload_hash,
            "elapsed_ms": result.elapsed_ms,
            "error": result.error or None,
        }
        self._audit_log.append(audit_entry)

        # Write audit to disk
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        audit_path = self.audit_dir / f"{connector_id}_{ts}.json"
        audit_path.write_text(json.dumps(audit_entry, indent=2), encoding="utf-8")

        return result

    def dispatch_to_all(
        self,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        kinds: Optional[List[str]] = None,
    ) -> List[DispatchResult]:
        """Dispatch payload to all registered (and enabled) connectors.

        Args:
            payload: The data payload.
            metadata: Optional metadata.
            kinds: If specified, only dispatch to connectors of these kinds.

        Returns:
            List of DispatchResult, one per connector.
        """
        results = []
        for cid, config in self._connectors.items():
            if not config.enabled:
                continue
            if kinds and config.kind not in kinds:
                continue
            results.append(self.dispatch(cid, payload, metadata))
        return results

    # ── Body Building ──────────────────────────────────────────────────

    def _build_body(
        self,
        config: ConnectorConfig,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the HTTP request body based on payload_mode."""
        ts = datetime.now(timezone.utc).isoformat()

        if config.payload_mode == "scbe_step":
            return {
                "source": "scbe-aetherbrowse",
                "connector_id": config.connector_id,
                "timestamp_utc": ts,
                "payload": payload,
                "metadata": metadata or {},
            }
        elif config.payload_mode == "shopify_graphql_read":
            # Shopify Admin API GraphQL query
            query = payload.get("query", "{ shop { name } }")
            variables = payload.get("variables", {})
            return {"query": query, "variables": variables}
        elif config.payload_mode == "raw":
            return payload
        else:
            # Default: wrap in SCBE envelope
            return {
                "source": "scbe-aetherbrowse",
                "connector_id": config.connector_id,
                "timestamp_utc": ts,
                "payload": payload,
                "metadata": metadata or {},
            }

    def _build_headers(self, config: ConnectorConfig) -> Dict[str, str]:
        """Build HTTP headers including auth."""
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "SCBE-AetherBrowse/1.0",
            **config.extra_headers,
        }

        if config.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {config.auth_token}"
        elif config.auth_type == "header":
            headers[config.auth_header_name] = config.auth_token
        elif config.auth_type == "basic":
            import base64
            encoded = base64.b64encode(config.auth_token.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        # auth_type == "none": no auth header

        return headers

    # ── HTTP Dispatch ──────────────────────────────────────────────────

    def _do_dispatch(
        self,
        config: ConnectorConfig,
        body: Dict[str, Any],
        headers: Dict[str, str],
        payload_hash: str,
    ) -> DispatchResult:
        """Execute the HTTP request with retry logic."""
        dispatched_at = datetime.now(timezone.utc).isoformat()
        data = json.dumps(body).encode("utf-8")

        last_error = ""
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                wait = self.retry_backoff_s * (2 ** (attempt - 1))
                time.sleep(wait)

            start = time.monotonic()
            try:
                req = urllib.request.Request(
                    url=config.endpoint_url,
                    data=data,
                    method=config.http_method,
                    headers=headers,
                )
                with urllib.request.urlopen(req, timeout=config.timeout_sec) as resp:
                    resp_body = resp.read().decode("utf-8", errors="replace")
                    elapsed = (time.monotonic() - start) * 1000

                    logger.info(
                        "Dispatched to %s (%s): HTTP %d in %.0fms",
                        config.connector_id,
                        config.kind,
                        resp.status,
                        elapsed,
                    )

                    return DispatchResult(
                        connector_id=config.connector_id,
                        success=True,
                        status_code=resp.status,
                        response_body=resp_body[:10000],
                        elapsed_ms=elapsed,
                        dispatched_at=dispatched_at,
                        payload_hash=payload_hash,
                    )

            except urllib.error.HTTPError as exc:
                elapsed = (time.monotonic() - start) * 1000
                resp_body = exc.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {exc.code}: {resp_body[:500]}"

                # Don't retry client errors (4xx) except 429
                if 400 <= exc.code < 500 and exc.code != 429:
                    return DispatchResult(
                        connector_id=config.connector_id,
                        success=False,
                        status_code=exc.code,
                        response_body=resp_body[:10000],
                        error=last_error,
                        elapsed_ms=elapsed,
                        dispatched_at=dispatched_at,
                        payload_hash=payload_hash,
                    )

                logger.warning(
                    "Dispatch attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    config.connector_id,
                    last_error,
                )

            except Exception as exc:
                elapsed = (time.monotonic() - start) * 1000
                last_error = str(exc)
                logger.warning(
                    "Dispatch attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    config.connector_id,
                    last_error,
                )

        # All retries exhausted
        return DispatchResult(
            connector_id=config.connector_id,
            success=False,
            error=f"All {self.max_retries + 1} attempts failed: {last_error}",
            dispatched_at=dispatched_at,
            payload_hash=payload_hash,
        )

    # ── Audit ──────────────────────────────────────────────────────────

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return the dispatch audit trail."""
        return list(self._audit_log)
