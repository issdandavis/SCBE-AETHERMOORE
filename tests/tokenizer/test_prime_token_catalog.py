"""Six-view catalog mechanics, not a learned retrieval claim."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from python.scbe.prime_token_catalog import (
    CATALOG_AUDIT_SCHEMA,
    DEFAULT_TOKENIZER_SHA256,
    InputRecord,
    PrimeTokenCatalogBuilder,
    SOURCE_MANIFEST_SCHEMA,
    VIEW_NAMES,
    audit_catalog_sources,
    search_goal,
    update_probability_lookup,
)


def _catalog(tmp_path: Path) -> tuple[Path, dict]:
    output = tmp_path / "catalog"
    builder = PrimeTokenCatalogBuilder(output, section_chars=512, range_size=128)
    builder.ingest_record(
        InputRecord(
            text=(
                "Alice and the research team measured the sample.\n\n"
                "Because the sensor failed, therefore the evidence explains why the launch stopped.\n"
            ),
            source_uri="local://academic-fixture",
            source_kind="academic",
            license_name="fixture",
        )
    )
    builder.ingest_record(
        InputRecord(
            text=(
                "Bob asks about the launch in conversation.\n\n" "Tomorrow we meet inside the laboratory after noon.\n"
            ),
            source_uri="local://conversation-fixture",
            source_kind="conversation",
            license_name="fixture",
        )
    )
    return output / "catalog.sqlite3", builder.finalize()


def test_build_preserves_canonical_identity_and_six_typed_views(tmp_path):
    database, manifest = _catalog(tmp_path)

    assert manifest["tokenizer"]["sha256"] == DEFAULT_TOKENIZER_SHA256
    assert manifest["canonical_identity"] == "utf8_bytes_and_source_word_span"
    assert manifest["views"] == list(VIEW_NAMES)
    assert manifest["source_count"] == 2
    assert manifest["section_count"] == 4
    assert manifest["occurrence_count"] > 20
    assert manifest["status"] == "MECHANICS_ONLY_NO_PROMOTION"

    connection = sqlite3.connect(database)
    views = {row[0] for row in connection.execute("SELECT DISTINCT view_name FROM section_features")}
    assert views == set(VIEW_NAMES)
    first = connection.execute(
        "SELECT global_ordinal, prime_kind, prime_factors_json FROM occurrences ORDER BY global_ordinal LIMIT 4"
    ).fetchall()
    connection.close()
    assert first[0] == (1, "edge", "[]")
    assert first[1][0:2] == (2, "prime")
    assert json.loads(first[1][2]) == [2]
    assert first[3][0:2] == (4, "composite")
    assert json.loads(first[3][2]) == [2, 2]


def test_goal_surfing_separates_ideas_from_grammar_constraints(tmp_path):
    database, _manifest = _catalog(tmp_path)
    receipt = search_goal(database, "why did the launch stop because the sensor failed", limit=4)

    assert receipt["schema"] == "scbe.prime-token-goal-search.v1"
    assert len(receipt["search_id"]) == 64
    assert len(receipt["catalog_sha256"]) == 64
    assert receipt["views"] == list(VIEW_NAMES)
    assert receipt["view_weights"]["lexical"] > receipt["view_weights"]["speech"]
    assert receipt["results"]
    top = receipt["results"][0]
    assert "sensor failed" in top["preview"]
    assert {row["normalized"] for row in top["content_tokens"]} & {
        "sensor",
        "failed",
        "evidence",
        "launch",
    }
    assert all(row["role"] == "constraint_not_idea_evidence" for row in top["grammar_constraints"])
    assert top["evidence_path"]["lexical"]
    assert 0.0 < sum(row["probability"] for row in receipt["results"]) <= 1.0


def test_size_matched_shuffle_and_ablation_are_explicit_controls(tmp_path):
    database, _manifest = _catalog(tmp_path)
    aligned = search_goal(database, "tomorrow inside the laboratory", limit=4, control="aligned")
    shuffled = search_goal(
        database,
        "tomorrow inside the laboratory",
        limit=4,
        control="shuffled",
        control_seed=17,
    )
    ablated = search_goal(database, "tomorrow inside the laboratory", limit=4, ablate_views=["five_w"])

    assert aligned["control"] == "aligned"
    assert shuffled["control"] == "shuffled"
    assert shuffled["control_seed"] == 17
    assert shuffled["control_offset"] > 0
    assert ablated["ablated_views"] == ["five_w"]
    assert len(aligned["results"]) == len(shuffled["results"])
    aligned_by_id = {row["section_id"]: row["score"] for row in aligned["results"]}
    shuffled_by_id = {row["section_id"]: row["score"] for row in shuffled["results"]}
    shared = set(aligned_by_id) & set(shuffled_by_id)
    assert shared
    assert any(aligned_by_id[key] != shuffled_by_id[key] for key in shared)


def test_probability_lookup_is_append_only_and_weight_anchored(tmp_path):
    database, _manifest = _catalog(tmp_path)
    search = search_goal(database, "evidence explaining why the launch stopped", limit=4)
    anchor = "a" * 64
    first = update_probability_lookup(database, search, model_anchor_sha256=anchor, token_limit=16)
    second = update_probability_lookup(database, search, model_anchor_sha256=anchor, token_limit=16)

    assert first["model_anchor_sha256"] == anchor
    assert abs(first["probability_sum"] - 1.0) < 1e-9
    assert first["events"] and second["events"]
    assert any(event["old_probability"] > 0 for event in second["events"])
    assert first["catalog_sha256"] == second["catalog_sha256"]
    assert Path(first["probability_database"]).name == "probability_lookup.sqlite3"
    connection = sqlite3.connect(first["probability_database"])
    current = connection.execute("SELECT COUNT(*) FROM token_probability_current").fetchone()[0]
    events = connection.execute("SELECT COUNT(*) FROM probability_events").fetchone()[0]
    connection.close()
    assert events == current * 2
    assert all("no neural tensor" in first["boundary"] for _ in [0])


def test_catalog_refuses_to_overwrite_and_bad_anchor(tmp_path):
    database, _manifest = _catalog(tmp_path)
    with pytest.raises(FileExistsError):
        PrimeTokenCatalogBuilder(database.parent)
    search = search_goal(database, "launch evidence", limit=2)
    with pytest.raises(ValueError, match="SHA-256"):
        update_probability_lookup(database, search, model_anchor_sha256="not-a-hash")


def test_source_manifest_binds_hash_and_rights_metadata(tmp_path):
    source = tmp_path / "research.md"
    source.write_text("Measured evidence for a routed research source.\n", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": SOURCE_MANIFEST_SCHEMA,
                "sources": [
                    {
                        "path": "research.md",
                        "sha256": source_hash,
                        "source_kind": "academic",
                        "license": "owner-authored-proprietary",
                        "rights_basis": "owner-authored",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    builder = PrimeTokenCatalogBuilder(tmp_path / "catalog", section_chars=512, range_size=128)
    builder.ingest_source_manifest(manifest_path)
    result = builder.finalize()

    assert result["source_count"] == 1
    assert result["source_manifests"] == [
        {
            "path": str(manifest_path.resolve()),
            "sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "declared_sources": 1,
            "rights_metadata": "explicit_per_source",
        }
    ]
    connection = sqlite3.connect(tmp_path / "catalog" / "catalog.sqlite3")
    assert connection.execute("SELECT source_kind, license_name FROM sources").fetchone() == (
        "academic",
        "owner-authored-proprietary",
    )
    connection.close()


@pytest.mark.parametrize("missing_field", ["license", "rights_basis"])
def test_source_manifest_refuses_missing_commercial_rights(tmp_path, missing_field):
    source = tmp_path / "research.md"
    source.write_text("Bounded source.\n", encoding="utf-8")
    row = {
        "path": str(source),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_kind": "academic",
        "license": "owner-authored-proprietary",
        "rights_basis": "owner-authored",
    }
    row.pop(missing_field)
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(
        json.dumps({"schema": SOURCE_MANIFEST_SCHEMA, "sources": [row]}),
        encoding="utf-8",
    )

    builder = PrimeTokenCatalogBuilder(tmp_path / "catalog", section_chars=512, range_size=128)
    with pytest.raises(ValueError, match=missing_field):
        builder.ingest_source_manifest(manifest_path)


def test_source_manifest_refuses_hash_drift_before_ingest(tmp_path):
    source = tmp_path / "research.md"
    source.write_text("Changed source.\n", encoding="utf-8")
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": SOURCE_MANIFEST_SCHEMA,
                "sources": [
                    {
                        "path": str(source),
                        "sha256": "0" * 64,
                        "source_kind": "academic",
                        "license": "owner-authored-proprietary",
                        "rights_basis": "owner-authored",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    builder = PrimeTokenCatalogBuilder(tmp_path / "catalog", section_chars=512, range_size=128)
    with pytest.raises(ValueError, match="hash mismatch"):
        builder.ingest_source_manifest(manifest_path)
    connection = sqlite3.connect(tmp_path / "catalog" / "catalog.sqlite3")
    assert connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0
    connection.close()


def test_catalog_source_audit_passes_diverse_rights_bound_fixture(tmp_path):
    output = tmp_path / "catalog"
    builder = PrimeTokenCatalogBuilder(output, section_chars=512, range_size=128)
    for index, source_kind in enumerate(("academic", "documentation", "publication") * 2):
        builder.ingest_record(
            InputRecord(
                text=f"Source {index} records evidence about who routed the measured system and why.",
                source_uri=f"local://source-{index}",
                source_kind=source_kind,
                license_name="fixture-license",
            )
        )
    builder.finalize()

    result = audit_catalog_sources(output / "catalog.sqlite3")

    assert result["schema"] == CATALOG_AUDIT_SCHEMA
    assert result["status"] == "STRUCTURAL_GATE_PASS"
    assert result["source_count"] == 6
    assert result["source_kind_counts"] == {
        "academic": 2,
        "documentation": 2,
        "publication": 2,
    }
    assert result["unknown_license_sources"] == 0
    assert all(result["checks"].values())
    assert all(not source_ids for source_ids in result["missing_source_ids_by_view"].values())


def test_catalog_source_audit_fails_unknown_rights_and_concentration(tmp_path):
    output = tmp_path / "catalog"
    builder = PrimeTokenCatalogBuilder(output, section_chars=512, range_size=128)
    builder.ingest_record(
        InputRecord(
            text="One oversized unknown-rights source. " * 200,
            source_uri="local://unknown",
            source_kind="academic",
            license_name="unknown",
        )
    )
    for index in range(5):
        builder.ingest_record(
            InputRecord(
                text=f"Small source {index} records one routed fact.",
                source_uri=f"local://small-{index}",
                source_kind="documentation" if index < 3 else "publication",
                license_name="fixture-license",
            )
        )
    builder.finalize()

    result = audit_catalog_sources(output / "catalog.sqlite3")

    assert result["status"] == "STRUCTURAL_GATE_FAIL"
    assert result["unknown_license_sources"] == 1
    assert not result["checks"]["all_sources_have_explicit_license"]
    assert not result["checks"]["largest_source_section_share_at_most_0_40"]
