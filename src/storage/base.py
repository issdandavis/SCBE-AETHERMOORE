"""Storage interfaces for sealed memory blobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


class BlobNotFoundError(FileNotFoundError):
    """Raised when a sealed blob is missing from storage."""


@dataclass(frozen=True)
class SealedBlobRecord:
    position: List[int]
    agent: str
    topic: str
    sealed_blob: bytes


class SealedBlobStorage(ABC):
    """Abstract storage interface for sealed blobs."""

    @abstractmethod
    def save(self, record: SealedBlobRecord) -> None:
        """Persist a sealed blob record."""

    @abstractmethod
    def load(self, position: List[int]) -> SealedBlobRecord:
        """Load a sealed blob record by its 6D position."""
