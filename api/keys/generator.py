"""
Secure API key generation.

Generates cryptographically secure API keys with proper formatting.
"""

import secrets
import hashlib
from typing import Tuple

from ..billing.database import ApiKey


def generate_api_key(
    customer_id: str,
    name: str = "Default",
    permissions: str = "full",
) -> Tuple[str, ApiKey]:
    """
    Generate a new API key for a customer.

    Returns tuple of (raw_key, ApiKey record).
    The raw key is only available at generation time.
    """
    # Generate 32 random bytes (256 bits of entropy)
    random_part = secrets.token_urlsafe(32)

    # Format: scbe_<random>
    raw_key = f"scbe_{random_part}"

    # Hash for storage
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Prefix for display (first 12 chars)
    key_prefix = raw_key[:12]

    # Create record (don't store raw key)
    key_record = ApiKey(
        customer_id=customer_id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        permissions=permissions,
        is_active=True,
    )

    return raw_key, key_record


def mask_api_key(key_prefix: str) -> str:
    """
    Create a masked display version of an API key.

    Example: scbe_abc123... -> scbe_abc1****
    """
    if len(key_prefix) > 8:
        return key_prefix[:8] + "****"
    return key_prefix + "****"


def rotate_api_key(
    customer_id: str,
    old_key_record: ApiKey,
) -> Tuple[str, ApiKey]:
    """
    Generate a new key to replace an old one.

    Returns tuple of (new_raw_key, new_ApiKey record).
    The old key should be revoked after this.
    """
    return generate_api_key(
        customer_id=customer_id,
        name=f"{old_key_record.name} (rotated)",
        permissions=old_key_record.permissions,
    )
