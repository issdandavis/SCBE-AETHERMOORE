from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_ingestion_rights_schema_accepts_minimal_record() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    schema = json.loads((repo_root / "schemas" / "ingestion_rights_record.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    record = {
        "schema_version": "scbe_ingestion_rights_record_v1",
        "rights_record_id": "f3a1f494f963f2f6",
        "source_id": "sam_gov_public_api",
        "artifact_ref": "artifacts/sam_gov/example.json",
        "artifact_type": "api_result",
        "access_level": "public",
        "redistribution_status": "publishable",
        "training_status": "allowed_public_training",
        "verification_status": "reviewed",
        "allowed_uses": [
            "internal_rag",
            "internal_training",
            "public_training",
            "metadata_extraction",
            "compliance_analysis",
            "citation_only"
        ],
        "prohibited_uses": [
            "autonomous_submission",
            "legal_advice"
        ],
        "handling_rules": [
            "Preserve citations and provenance for any downstream synthesis."
        ],
        "reviewed_by": "issdandavis",
        "reviewed_at": "2026-04-09T00:00:00+00:00",
        "reviewer_notes": "Public API result."
    }

    validator.validate(record)
