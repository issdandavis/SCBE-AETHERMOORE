"""Outbound webhook relay for SCBE governance events.

When a governance decision returns DENY or ESCALATE, SCBE can push a signed
JSON event to a configured endpoint (PagerDuty, Slack, custom SIEM, etc.).

Configuration (env vars):
    SCBE_WEBHOOK_URL       — target URL (required to enable relay)
    SCBE_WEBHOOK_SECRET    — HMAC-SHA256 signing secret for X-SCBE-Signature header
    SCBE_WEBHOOK_TIMEOUT   — HTTP timeout in seconds (default: 5)
    SCBE_WEBHOOK_DECISIONS — comma-separated decisions to relay (default: DENY,ESCALATE)

Payload schema:
    {
        "schema": "scbe.webhook.governance_event.v1",
        "ts": "2026-05-14T...",
        "decision": "DENY",
        "score": 0.12,
        "agent": "my_agent",
        "topic": "finance",
        "reason": "adversarial intent detected",
        "sha256": "..."   // sha256 of this payload (excluding the sha256 field)
    }

Signature: X-SCBE-Signature: sha256=<hmac-hex>
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("scbe.webhook_relay")


def _relay_url() -> str:
    return os.environ.get("SCBE_WEBHOOK_URL", "").strip()


def _relay_secret() -> str:
    return os.environ.get("SCBE_WEBHOOK_SECRET", "").strip()


def _relay_timeout() -> float:
    try:
        return float(os.environ.get("SCBE_WEBHOOK_TIMEOUT", "5"))
    except ValueError:
        return 5.0


def _relay_decisions() -> frozenset:
    raw = os.environ.get("SCBE_WEBHOOK_DECISIONS", "DENY,ESCALATE")
    return frozenset(d.strip().upper() for d in raw.split(",") if d.strip())


def _sign(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def _build_payload(
    decision: str,
    score: float,
    agent: str,
    topic: str = "",
    reason: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> dict:
    body: Dict[str, Any] = {
        "schema": "scbe.webhook.governance_event.v1",
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "decision": decision,
        "score": round(float(score), 6),
        "agent": agent,
        "topic": topic,
        "reason": reason,
    }
    if extra:
        body.update(extra)
    # stable sha256 of the body (excluding the sha256 field itself)
    body_bytes = json.dumps(body, sort_keys=True).encode()
    body["sha256"] = hashlib.sha256(body_bytes).hexdigest()
    return body


def _fire(url: str, payload: dict, secret: str, timeout: float) -> None:
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-SCBE-Signature"] = f"sha256={_sign(payload_bytes, secret)}"
    req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            logger.debug("webhook relay %s → %d", url, resp.status)
    except urllib.error.HTTPError as exc:
        logger.warning("webhook relay HTTP %d from %s: %s", exc.code, url, exc.reason)
    except Exception as exc:
        logger.warning("webhook relay failed (%s): %s", url, exc)


def relay_governance_event(
    decision: str,
    score: float,
    agent: str,
    topic: str = "",
    reason: str = "",
    extra: Optional[Dict[str, Any]] = None,
    *,
    blocking: bool = False,
) -> None:
    """Fire an outbound webhook for a governance decision.

    By default runs in a daemon thread (non-blocking). Pass ``blocking=True``
    for tests or cases where the caller needs confirmation before continuing.

    No-ops when SCBE_WEBHOOK_URL is not set or the decision is not in
    SCBE_WEBHOOK_DECISIONS.
    """
    url = _relay_url()
    if not url:
        return
    if decision.upper() not in _relay_decisions():
        return

    payload = _build_payload(decision, score, agent, topic, reason, extra)
    secret = _relay_secret()
    timeout = _relay_timeout()

    if blocking:
        _fire(url, payload, secret, timeout)
    else:
        t = threading.Thread(target=_fire, args=(url, payload, secret, timeout), daemon=True)
        t.start()
