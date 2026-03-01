"""
SCBE Security Module

Contains security patches and hardening utilities.
"""

from . import protobuf_patch
from .secret_store import (
    get_api_key_map,
    get_secret,
    list_secret_names,
    pick_secret,
    remove_secret,
    set_secret,
    store_path,
)

__all__ = [
    "protobuf_patch",
    "get_api_key_map",
    "get_secret",
    "list_secret_names",
    "pick_secret",
    "remove_secret",
    "set_secret",
    "store_path",
]
