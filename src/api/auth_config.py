"""
Shared API key configuration for SCBE API routes.

Loads API keys from the SCBE_API_KEYS environment variable (JSON format).
Falls back to demo keys only when SCBE_ENV is 'development' or 'test'.

Environment variable format:
    SCBE_API_KEYS='{"my_key": "user_id", "other_key": "other_user"}'
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


def load_api_keys() -> Dict[str, str]:
    """Load API keys from environment or explicit demo keys for local/test use."""
    env_keys = os.environ.get("SCBE_API_KEYS")
    if env_keys:
        try:
            keys = json.loads(env_keys)
            if isinstance(keys, dict) and keys:
                return keys
        except (json.JSONDecodeError, TypeError):
            logger.warning("SCBE_API_KEYS is set but not valid JSON; ignoring")

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
