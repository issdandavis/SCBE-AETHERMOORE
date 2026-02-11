"""Filesystem-backed sealed blob storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .base import BlobNotFoundError, SealedBlobRecord, SealedBlobStorage


class FileSystemSealedBlobStorage(SealedBlobStorage):
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, record: SealedBlobRecord) -> None:
        payload = {
            "position": record.position,
            "agent": record.agent,
            "topic": record.topic,
            "sealed_blob": record.sealed_blob.hex(),
        }
        blob_path = self._blob_path(record.position)
        blob_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, position: List[int]) -> SealedBlobRecord:
        blob_path = self._blob_path(position)
        if not blob_path.exists():
            raise BlobNotFoundError(f"No sealed blob found at position {position}")
        payload = json.loads(blob_path.read_text(encoding="utf-8"))
        return SealedBlobRecord(
            position=payload["position"],
            agent=payload["agent"],
            topic=payload["topic"],
            sealed_blob=bytes.fromhex(payload["sealed_blob"]),
        )

    def _blob_path(self, position: List[int]) -> Path:
        key = "_".join(str(value) for value in position)
        return self.base_path / f"{key}.json"
