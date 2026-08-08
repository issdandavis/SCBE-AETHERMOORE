"""Filesystem-backed sealed blob storage."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import List

from .base import BlobNotFoundError, SealedBlobRecord, SealedBlobStorage


class FileSystemSealedBlobStorage(SealedBlobStorage):
    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path).expanduser().resolve(strict=False)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, record: SealedBlobRecord) -> None:
        payload = {
            "position": record.position,
            "agent": record.agent,
            "topic": record.topic,
            "sealed_blob": record.sealed_blob.hex(),
        }
        blob_path = self._blob_path(record.position, record.owner, create_owner_dir=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=blob_path.parent,
                prefix=f".{blob_path.stem}-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
                temporary_path = Path(handle.name)
            os.replace(temporary_path, blob_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def load(self, position: List[int], owner: str) -> SealedBlobRecord:
        blob_path = self._blob_path(position, owner)
        if not blob_path.exists():
            raise BlobNotFoundError(f"No sealed blob found at position {position}")
        payload = json.loads(blob_path.read_text(encoding="utf-8"))
        if payload.get("position") != position:
            raise ValueError("Stored sealed blob position does not match its storage key")
        agent = payload.get("agent")
        topic = payload.get("topic")
        sealed_blob = payload.get("sealed_blob")
        if not isinstance(agent, str) or not isinstance(topic, str) or not isinstance(sealed_blob, str):
            raise ValueError("Stored sealed blob record is malformed")
        return SealedBlobRecord(
            owner=owner,
            position=position,
            agent=agent,
            topic=topic,
            sealed_blob=bytes.fromhex(sealed_blob),
        )

    def _blob_path(self, position: List[int], owner: str, *, create_owner_dir: bool = False) -> Path:
        if len(position) != 6:
            raise ValueError("Position must contain exactly 6 integers")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in position):
            raise ValueError("Position must contain integers")
        if any(value < -(2**63) or value > 2**63 - 1 for value in position):
            raise ValueError("Position integers must fit in a signed 64-bit coordinate")
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("Owner must be a non-empty string")

        owner_key = hashlib.sha256(owner.encode("utf-8")).hexdigest()
        position_payload = json.dumps(position, separators=(",", ":")).encode("ascii")
        position_key = hashlib.sha256(position_payload).hexdigest()
        owner_path = (self.base_path / owner_key).resolve(strict=False)
        blob_path = (owner_path / f"{position_key}.json").resolve(strict=False)
        try:
            blob_path.relative_to(self.base_path)
        except ValueError as exc:
            raise ValueError("Position resolved outside the sealed blob storage root") from exc
        if create_owner_dir:
            owner_path.mkdir(parents=True, exist_ok=True)
        return blob_path
