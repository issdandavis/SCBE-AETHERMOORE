"""Storage backends for sealed memory blobs."""

from __future__ import annotations

import os
from typing import Optional

from .base import BlobNotFoundError, SealedBlobRecord, SealedBlobStorage
from .filesystem import FileSystemSealedBlobStorage


def get_storage_backend(
    backend: Optional[str] = None,
    storage_path: Optional[str] = None,
) -> SealedBlobStorage:
    selected_backend = (backend or os.getenv("SCBE_STORAGE_BACKEND") or "filesystem").lower()
    if selected_backend != "filesystem":
        raise ValueError(
            f"Unsupported storage backend '{selected_backend}'. "
            "Set SCBE_STORAGE_BACKEND=filesystem or implement a custom backend."
        )

    base_path = storage_path or os.getenv("SCBE_STORAGE_PATH") or "./sealed_blobs"
    return FileSystemSealedBlobStorage(base_path)


__all__ = [
    "BlobNotFoundError",
    "SealedBlobRecord",
    "SealedBlobStorage",
    "get_storage_backend",
]
