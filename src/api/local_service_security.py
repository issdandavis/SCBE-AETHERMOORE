"""Shared fail-closed authentication helpers for local HTTP services."""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException


def configured_api_key(env_name: str) -> str:
    """Return a trimmed service key without caching environment state."""
    return os.environ.get(env_name, "").strip()


def require_api_key(env_name: str, supplied_key: str | None, service_name: str) -> None:
    """Reject unconfigured services and invalid keys without leaking key material."""
    configured_key = configured_api_key(env_name)
    if not configured_key:
        raise HTTPException(status_code=503, detail=f"{service_name} authentication is not configured")
    if supplied_key is None or not secrets.compare_digest(supplied_key, configured_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def comma_separated_env(name: str) -> list[str]:
    """Load a trimmed, non-empty comma-separated environment allowlist."""
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]
