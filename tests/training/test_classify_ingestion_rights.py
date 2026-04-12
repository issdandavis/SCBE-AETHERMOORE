from __future__ import annotations

from python.scbe.ingestion_rights import classify_ingestion_rights_record, get_source_record, load_source_registry


def test_classify_public_source_allows_public_training() -> None:
    registry = load_source_registry()
    source = get_source_record("sam_gov_public_api", registry)

    record = classify_ingestion_rights_record(
        source_record=source,
        artifact_ref="artifacts/sam_gov/query.json",
        artifact_type="api_result",
        reviewed_by="issdandavis",
    )

    assert record["training_status"] == "allowed_public_training"
    assert "public_training" in record["allowed_uses"]
    assert "public_republication" not in record["prohibited_uses"]


def test_classify_authorized_portal_is_retrieval_only() -> None:
    registry = load_source_registry()
    source = get_source_record("darpa_submission_portal", registry)

    record = classify_ingestion_rights_record(
        source_record=source,
        artifact_ref="notes/darpa/open_solicitations_2026-04-09.md",
        artifact_type="portal_dump",
        reviewed_by="issdandavis",
    )

    assert record["training_status"] == "retrieval_only"
    assert "public_training" in record["prohibited_uses"]
    assert any("internal" in rule.lower() or "portal" in rule.lower() for rule in record["handling_rules"])
