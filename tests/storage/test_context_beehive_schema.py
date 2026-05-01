from __future__ import annotations

import sqlite3

import pytest

from src.storage.context_beehive_schema import (
    context_beehive_manifest,
    context_beehive_schema_sql,
    make_context_cell,
    serialize_sqlite_json_fields,
)


def test_context_cell_tracks_reversible_text_and_negative_embedding() -> None:
    cell = make_context_cell(
        source_uri="docs/notion/geoseal.md",
        source_span="L10-L20",
        surface_text="false wall",
        tongue_route="DR",
        semantic_roles=["boundary", "shadow_retrieval"],
        active_role="boundary",
        positive_embedding=[0.2, 0.8],
        negative_embedding=[-0.2, -0.8],
        polarity="double_negative",
        raw_pointer="sha256:raw-doc",
    )
    record = cell.to_record()

    assert record["byte_hex"] == "66.61.6C.73.65.20.77.61.6C.6C"
    assert record["polarity"] == "double_negative"
    assert record["negative_embedding"] == [-0.2, -0.8]
    assert record["source_hash"]


def test_context_cell_rejects_unknown_polarity() -> None:
    with pytest.raises(ValueError):
        make_context_cell(source_uri="x", surface_text="x", polarity="maybe")


def test_sqlite_schema_executes_and_accepts_serialized_cell() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(context_beehive_schema_sql("sqlite"))
    cell = make_context_cell(
        source_uri="local://trace",
        surface_text="buffalo",
        semantic_roles=["noun", "verb", "recursive_grammar"],
        positive_embedding=[1.0, 0.0],
        negative_embedding=[0.0, -1.0],
        polarity="double_positive",
    )
    record = serialize_sqlite_json_fields(cell.to_record())
    conn.execute(
        """
        INSERT INTO scbe_context_cells (
            cell_id, source_hash, source_uri, source_span, surface_text, byte_hex,
            tongue_route, semantic_roles, active_role, positive_embedding,
            negative_embedding, polarity, storage_tier, raw_pointer, metadata
        ) VALUES (
            :cell_id, :source_hash, :source_uri, :source_span, :surface_text, :byte_hex,
            :tongue_route, :semantic_roles, :active_role, :positive_embedding,
            :negative_embedding, :polarity, :storage_tier, :raw_pointer, :metadata
        )
        """,
        record,
    )
    stored = conn.execute("SELECT polarity, byte_hex FROM scbe_context_cells").fetchone()
    assert stored == ("double_positive", "62.75.66.66.61.6C.6F")


def test_postgres_schema_declares_jsonb_and_polarity_index() -> None:
    sql = context_beehive_schema_sql("postgres")
    assert "JSONB" in sql
    assert "idx_scbe_context_cells_polarity" in sql
    assert "double_negative" in sql


def test_manifest_explains_false_wall_boundary_limits() -> None:
    manifest = context_beehive_manifest()
    assert manifest["schema_version"] == "scbe_context_beehive_v1"
    assert "double_negative" in manifest["polarity_modes"]
    assert any("not security boundaries" in rule for rule in manifest["rules"])
