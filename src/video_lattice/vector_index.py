"""Local multimodal vector index for text-to-frame retrieval.

This is the backend-neutral bridge for CLIP/SigLIP-style embeddings. Real
encoders can provide the vectors; this module normalizes them, stores frame
metadata, and performs cosine search. For the first local harness we use exact
search because it is deterministic and dependency-free. The API is shaped so an
ANN backend such as Qdrant, Milvus, or FAISS can replace it later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

_EPS = 1e-12


@dataclass(frozen=True)
class VectorRecord:
    record_id: str
    vector: np.ndarray
    modality: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "vector": self.vector.astype(float).tolist(),
            "modality": self.modality,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "VectorRecord":
        return cls(
            record_id=str(data["record_id"]),
            vector=np.asarray(data["vector"], dtype=np.float64),
            modality=str(data["modality"]),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class SearchResult:
    record_id: str
    score: float
    modality: str
    metadata: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "score": self.score,
            "modality": self.modality,
            "metadata": self.metadata,
        }


class LocalVectorIndex:
    """Exact cosine vector index for local video retrieval experiments."""

    def __init__(self, *, dim: int | None = None) -> None:
        self.dim = dim
        self._records: list[VectorRecord] = []

    def add(
        self,
        record_id: str,
        vector: Sequence[float] | np.ndarray,
        *,
        modality: str = "frame",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        normalized = normalize_vector(vector)
        if self.dim is None:
            self.dim = int(normalized.shape[0])
        if int(normalized.shape[0]) != self.dim:
            raise ValueError(f"vector dimension {normalized.shape[0]} does not match index dimension {self.dim}")
        self._records.append(
            VectorRecord(
                record_id=record_id,
                vector=normalized,
                modality=modality,
                metadata=metadata or {},
            )
        )

    def extend(self, records: Iterable[VectorRecord]) -> None:
        for record in records:
            self.add(record.record_id, record.vector, modality=record.modality, metadata=record.metadata)

    def search(
        self,
        query_vector: Sequence[float] | np.ndarray,
        *,
        top_k: int = 5,
        modality: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        if top_k <= 0:
            return []
        query = normalize_vector(query_vector)
        if self.dim is not None and int(query.shape[0]) != self.dim:
            raise ValueError(f"query dimension {query.shape[0]} does not match index dimension {self.dim}")

        results: list[SearchResult] = []
        for record in self._records:
            if modality is not None and record.modality != modality:
                continue
            if metadata_filter and not _metadata_matches(record.metadata, metadata_filter):
                continue
            score = cosine_similarity(query, record.vector)
            results.append(
                SearchResult(
                    record_id=record.record_id,
                    score=score,
                    modality=record.modality,
                    metadata=record.metadata,
                )
            )
        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scbe_local_vector_index_v1",
            "dim": self.dim,
            "records": [record.to_json() for record in self._records],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "LocalVectorIndex":
        index = cls(dim=data.get("dim"))
        index.extend(VectorRecord.from_json(record) for record in data.get("records", []))
        return index

    def save(self, path: Path | str) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_json(), indent=2, sort_keys=True), encoding="utf-8")
        return out

    @classmethod
    def load(cls, path: Path | str) -> "LocalVectorIndex":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_json(data)

    @property
    def records(self) -> list[VectorRecord]:
        return list(self._records)


def normalize_vector(vector: Sequence[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(vector, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("vector must be one-dimensional")
    norm = float(np.linalg.norm(arr))
    if norm <= _EPS:
        raise ValueError("zero vector cannot be normalized")
    return arr / norm


def cosine_similarity(a: Sequence[float] | np.ndarray, b: Sequence[float] | np.ndarray) -> float:
    return float(np.dot(normalize_vector(a), normalize_vector(b)))


def _metadata_matches(metadata: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(metadata.get(key) == value for key, value in expected.items())
