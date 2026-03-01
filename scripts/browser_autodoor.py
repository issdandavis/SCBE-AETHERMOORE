#!/usr/bin/env python3
"""Shared auto-authorization helpers for headless/browser tools.

This module computes lightweight "time+intent" headers used by browser clients
for automatic API access doors. It uses an HMAC over request context and a
domain-scoped API key when available.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from src.security.secret_store import get_api_key_map


AUTODOOR_MAX_CLOCK_DRIFT_MS = int(os.environ.get("SCBE_AUTODOOR_MAX_CLOCK_DRIFT_MS", "300000"))
AUTODOOR_ENABLED = os.environ.get("SCBE_AUTODOOR_ENABLED", "1").lower() in {"1", "true", "yes", "on"}
AUTODOOR_INTENT = os.environ.get("SCBE_AUTODOOR_INTENT", "agentic").strip() or "agentic"


@dataclass
class AutoDoorDecision:
    matched_key: bool
    has_secret: bool
    headers: Dict[str, str]
    api_key_hint: str
    context: Dict[str, Any]


def _normalize_domain(url: str) -> str:
    if not url:
        return ""
    normalized = url if ("://" in url) else f"https://{url}"
    parsed = urlparse(normalized)
    return (parsed.hostname or "").lower()


def _domain_matches(pattern: str, domain: str) -> bool:
    pattern = (pattern or "").lower().strip()
    domain = (domain or "").lower().strip()
    if not pattern or not domain:
        return False
    if pattern == "*":
        return True
    if pattern.startswith("*."):
        suffix = pattern[2:]
        return domain == suffix or domain.endswith(f".{suffix}")
    return domain == pattern


def _load_key_map() -> Dict[str, str]:
    mapping = get_api_key_map("SCBE_WEB_KEY_MAP")
    if mapping:
        return mapping

    mapping = get_api_key_map()
    if mapping:
        return mapping

    fallback = os.getenv("SCBE_BROWSER_API_KEY") or os.getenv("SCBE_API_KEY")
    if fallback:
        return {"*": fallback}

    return {}


def _pick_api_key(url: str, key_map: Dict[str, str], fallback_key: Optional[str]) -> tuple[Optional[str], str]:
    domain = _normalize_domain(url)
    for pattern, key in key_map.items():
        if _domain_matches(pattern, domain):
            return key, pattern

    if fallback_key:
        return fallback_key, "*"

    return None, ""


def _signature_payload(context: Dict[str, Any]) -> str:
    return json.dumps(context, sort_keys=True, separators=(",", ":"))


def _hmac_signature(secret: str, payload: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def build_auto_door_headers(
    url: str,
    *,
    action: str,
    intent: str | None = None,
    key_map: Optional[Dict[str, str]] = None,
    now_ms: Optional[int] = None,
) -> AutoDoorDecision:
    """Build request headers for SCBE time-intent authorization."""

    if not AUTODOOR_ENABLED:
        return AutoDoorDecision(
            matched_key=False,
            has_secret=False,
            headers={},
            api_key_hint="",
            context={
                "time_ms": None,
                "intent": intent or AUTODOOR_INTENT,
                "action": action,
                "domain": _normalize_domain(url),
            },
        )

    key_map = key_map or _load_key_map()
    intent_value = (intent or AUTODOOR_INTENT).strip() or AUTODOOR_INTENT
    request_time_ms = int(now_ms or time.time() * 1000)
    domain = _normalize_domain(url)
    fallback_key = os.getenv("SCBE_AUTODOOR_FALLBACK_KEY")
    key, matched_pattern = _pick_api_key(url, key_map, fallback_key)

    context: Dict[str, Any] = {
        "domain": domain,
        "action": action,
        "intent": intent_value,
        "request_time_ms": request_time_ms,
        "version": 1,
    }
    context["clock_drift_ratio"] = 0.0
    token_payload = _signature_payload(context)

    headers = {
        "X-SCBE-Time-Intent": token_payload,
        "X-SCBE-Time": str(request_time_ms),
        "X-SCBE-Time-Intent-Nonce": base64.urlsafe_b64encode(f"{request_time_ms}".encode("utf-8")).decode("utf-8").rstrip("="),
        "X-SCBE-Intent": intent_value,
        "X-SCBE-Domain": domain,
    }

    if key:
        context["secret_ref"] = matched_pattern or "*"
        context["clock_drift_ratio"] = round(
            min(
                1.0,
                abs(int(time.time() * 1000) - request_time_ms)
                / float(max(1, AUTODOOR_MAX_CLOCK_DRIFT_MS)),
            ),
            6,
        )
        signature = _hmac_signature(key, token_payload)
        headers["X-SCBE-Time-Intent-Signature"] = signature
        headers["Authorization"] = key if key.lower().startswith("bearer ") else f"Bearer {key}"
        return AutoDoorDecision(
            matched_key=True,
            has_secret=True,
            headers=headers,
            api_key_hint=f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****",
            context=context,
        )

    return AutoDoorDecision(
        matched_key=False,
        has_secret=False,
        headers=headers,
        api_key_hint="",
        context=context,
    )
