"""SCBE context beehive storage schema.

The beehive is an index over raw truth, not a replacement for raw files. It
stores reversible token evidence, semantic overlays, and positive/negative
embedding pairs so agents can retrieve context through multiple views.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = "scbe_context_beehive_v1"
SUPPORTED_ENGINES = {"postgres", "sqlite"}
POLARITIES = {"neutral", "positive", "negative", "double_positive", "double_negative"}


@dataclass(frozen=True)
class ContextBeehiveCell:
    cell_id: str
    source_hash: str
    source_uri: str
    source_span: str = ""
    surface_text: str = ""
    byte_hex: str = ""
    tongue_route: str = "KO"
    semantic_roles: list[str] = field(default_factory=list)
    active_role: str = ""
    positive_embedding: list[float] = field(default_factory=list)
    negative_embedding: list[float] = field(default_factory=list)
    polarity: str = "neutral"
    storage_tier: str = "hot_index"
    raw_pointer: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "cell_id": self.cell_id,
            "source_hash": self.source_hash,
            "source_uri": self.source_uri,
            "source_span": self.source_span,
            "surface_text": self.surface_text,
            "byte_hex": self.byte_hex,
            "tongue_route": self.tongue_route,
            "semantic_roles": list(self.semantic_roles),
            "active_role": self.active_role,
            "positive_embedding": list(self.positive_embedding),
            "negative_embedding": list(self.negative_embedding),
            "polarity": self.polarity,
            "storage_tier": self.storage_tier,
            "raw_pointer": self.raw_pointer,
            "metadata": dict(self.metadata),
        }


def _sha256_short(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]


def _byte_hex(text: str) -> str:
    return ".".join(f"{byte:02X}" for byte in text.encode("utf-8"))


def make_context_cell(
    *,
    source_uri: str,
    surface_text: str,
    source_span: str = "",
    tongue_route: str = "KO",
    semantic_roles: list[str] | None = None,
    active_role: str = "",
    positive_embedding: list[float] | None = None,
    negative_embedding: list[float] | None = None,
    polarity: str = "neutral",
    storage_tier: str = "hot_index",
    raw_pointer: str = "",
    metadata: dict[str, Any] | None = None,
) -> ContextBeehiveCell:
    """Build a deterministic context cell with reversible byte/hex evidence."""

    if polarity not in POLARITIES:
        raise ValueError(f"unsupported polarity {polarity!r}")
    source_hash = hashlib.sha256(f"{source_uri}\0{source_span}\0{surface_text}".encode("utf-8")).hexdigest()
    cell_id = f"ctx_{_sha256_short(source_hash + tongue_route + polarity)}"
    return ContextBeehiveCell(
        cell_id=cell_id,
        source_hash=source_hash,
        source_uri=source_uri,
        source_span=source_span,
        surface_text=surface_text,
        byte_hex=_byte_hex(surface_text),
        tongue_route=tongue_route,
        semantic_roles=list(semantic_roles or []),
        active_role=active_role,
        positive_embedding=list(positive_embedding or []),
        negative_embedding=list(negative_embedding or []),
        polarity=polarity,
        storage_tier=storage_tier,
        raw_pointer=raw_pointer,
        metadata=dict(metadata or {}),
    )


def context_beehive_schema_sql(engine: Literal["postgres", "sqlite"] = "postgres") -> str:
    """Return DDL for the context beehive lane.

    Postgres uses JSONB and lightweight GIN indexes. SQLite uses TEXT columns
    containing JSON so it can run locally without extensions.
    """

    if engine not in SUPPORTED_ENGINES:
        raise ValueError(f"unsupported engine {engine!r}")

    if engine == "postgres":
        return """
CREATE TABLE IF NOT EXISTS scbe_context_cells (
    cell_id TEXT PRIMARY KEY,
    source_hash TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_span TEXT NOT NULL DEFAULT '',
    surface_text TEXT NOT NULL DEFAULT '',
    byte_hex TEXT NOT NULL DEFAULT '',
    tongue_route TEXT NOT NULL DEFAULT 'KO',
    semantic_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    active_role TEXT NOT NULL DEFAULT '',
    positive_embedding JSONB NOT NULL DEFAULT '[]'::jsonb,
    negative_embedding JSONB NOT NULL DEFAULT '[]'::jsonb,
    polarity TEXT NOT NULL DEFAULT 'neutral',
    storage_tier TEXT NOT NULL DEFAULT 'hot_index',
    raw_pointer TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT scbe_context_cells_polarity_chk
        CHECK (polarity IN ('neutral','positive','negative','double_positive','double_negative'))
);

CREATE TABLE IF NOT EXISTS scbe_context_edges (
    edge_id TEXT PRIMARY KEY,
    from_cell_id TEXT NOT NULL REFERENCES scbe_context_cells(cell_id) ON DELETE CASCADE,
    to_cell_id TEXT NOT NULL REFERENCES scbe_context_cells(cell_id) ON DELETE CASCADE,
    edge_kind TEXT NOT NULL,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_source_hash ON scbe_context_cells(source_hash);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_tongue_route ON scbe_context_cells(tongue_route);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_polarity ON scbe_context_cells(polarity);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_semantic_roles
    ON scbe_context_cells USING GIN (semantic_roles);
""".strip()

    return """
CREATE TABLE IF NOT EXISTS scbe_context_cells (
    cell_id TEXT PRIMARY KEY,
    source_hash TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_span TEXT NOT NULL DEFAULT '',
    surface_text TEXT NOT NULL DEFAULT '',
    byte_hex TEXT NOT NULL DEFAULT '',
    tongue_route TEXT NOT NULL DEFAULT 'KO',
    semantic_roles TEXT NOT NULL DEFAULT '[]',
    active_role TEXT NOT NULL DEFAULT '',
    positive_embedding TEXT NOT NULL DEFAULT '[]',
    negative_embedding TEXT NOT NULL DEFAULT '[]',
    polarity TEXT NOT NULL DEFAULT 'neutral',
    storage_tier TEXT NOT NULL DEFAULT 'hot_index',
    raw_pointer TEXT NOT NULL DEFAULT '',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (polarity IN ('neutral','positive','negative','double_positive','double_negative'))
);

CREATE TABLE IF NOT EXISTS scbe_context_edges (
    edge_id TEXT PRIMARY KEY,
    from_cell_id TEXT NOT NULL,
    to_cell_id TEXT NOT NULL,
    edge_kind TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    evidence TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(from_cell_id) REFERENCES scbe_context_cells(cell_id) ON DELETE CASCADE,
    FOREIGN KEY(to_cell_id) REFERENCES scbe_context_cells(cell_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_source_hash ON scbe_context_cells(source_hash);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_tongue_route ON scbe_context_cells(tongue_route);
CREATE INDEX IF NOT EXISTS idx_scbe_context_cells_polarity ON scbe_context_cells(polarity);
""".strip()


def context_beehive_manifest() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "purpose": "routeable semantic index over raw files, logs, token packets, and agent traces",
        "engines": sorted(SUPPORTED_ENGINES),
        "tables": ["scbe_context_cells", "scbe_context_edges"],
        "polarity_modes": sorted(POLARITIES),
        "rules": [
            "store hashes and pointers, not secrets",
            "raw files remain authoritative",
            "positive and negative embeddings are retrieval partitions, not security boundaries",
            "double_positive and double_negative rows are allowed for paired-wall / false-wall experiments",
        ],
    }


def serialize_sqlite_json_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON-ish fields to strings for SQLite inserts."""

    out = dict(record)
    for key in ("semantic_roles", "positive_embedding", "negative_embedding", "metadata"):
        if not isinstance(out.get(key), str):
            out[key] = json.dumps(out.get(key, [] if key != "metadata" else {}), sort_keys=True)
    return out
