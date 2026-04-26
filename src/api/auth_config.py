"""
Shared API key configuration for SCBE API routes.

Loads API keys from the SCBE_API_KEYS environment variable. JSON object format
is canonical, with legacy support for comma-separated key:user pairs and a
single raw key for local owner setups.

Environment variable format:
    SCBE_API_KEYS='{"my_key": "user_id", "other_key": "other_user"}'
    SCBE_API_KEYS='my_key:user_id,other_key:other_user'
    SCBE_API_KEYS='my_single_key'
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

_DEMO_KEYS: Dict[str, str] = {
    "demo_key_12345": "demo_user",
    "pilot_key_67890": "pilot_customer",
}


def _env_flag(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_api_keys(raw: str) -> Dict[str, str]:
    """Parse SCBE_API_KEYS without logging or exposing key material."""
    value = raw.strip()
    if not value:
        return {}

    try:
        keys = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        keys = None
    if isinstance(keys, dict) and keys:
        return {str(key): str(owner) for key, owner in keys.items() if str(key).strip()}

    if ":" in value:
        parsed: Dict[str, str] = {}
        for part in value.split(","):
            if not part.strip() or ":" not in part:
                continue
            key, owner = part.split(":", 1)
            key = key.strip()
            owner = owner.strip() or "scbe_user"
            if key:
                parsed[key] = owner
        if parsed:
            return parsed

    # Legacy single-key setup. The key itself remains the credential; only the
    # owner label is synthesized for downstream audit records.
    return {value: "scbe_owner"}


def load_api_keys() -> Dict[str, str]:
    """Load API keys from environment or explicit demo keys for local/test use."""
    env_keys = os.environ.get("SCBE_API_KEYS")
    if env_keys:
        keys = _parse_api_keys(env_keys)
        if keys:
            return keys

    scbe_env = os.environ.get("SCBE_ENV", os.environ.get("NODE_ENV", "production"))
    if _env_flag("SCBE_ALLOW_DEMO_KEYS"):
        logger.warning("Using explicit demo API keys (SCBE_ENV=%s)", scbe_env)
        return dict(_DEMO_KEYS)

    logger.warning(
        "No SCBE_API_KEYS configured and SCBE_ENV=%s; "
        "API authentication will reject all requests. "
        "Set SCBE_API_KEYS or SCBE_ALLOW_DEMO_KEYS=1 for local demo keys.",
        scbe_env,
    )
    return {}


VALID_API_KEYS: Dict[str, str] = load_api_keys()
