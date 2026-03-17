"""
SCBE Security Module

Contains security patches, hardening utilities, and shared secret store.
"""

from . import protobuf_patch
from . import secret_store

__all__ = ["protobuf_patch", "secret_store"]
