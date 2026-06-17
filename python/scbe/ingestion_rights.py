from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SCHEMA_PATH = REPO_ROOT / "schemas" / "source_registry_record.schema.json"
RIGHTS_SCHEMA_PATH = REPO_ROOT / "schemas" / "ingestion_rights_record.schema.json"
DEFAULT_SOURCE_REGISTRY_PATH = REPO_ROOT / "config" / "research" / "source_registry.json"


def _load_validator(path: Path) -> Draft202012Validator:
    return Draft202012Validator(json.loads(path.read_text(encoding="utf-8")))


SOURCE_VALIDATOR = _load_validator(SOURCE_SCHEMA_PATH)
RIGHTS_VALIDATOR = _load_validator(RIGHTS_SCHEMA_PATH)


def load_source_registry(path: Path | None = None) -> List[Dict[str, Any]]:
    registry_path = path or DEFAULT_SOURCE_REGISTRY_PATH
    records = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Source registry must be a JSON array of source records")
    for record in records:
        SOURCE_VALIDATOR.validate(record)
    return records


def get_source_record(source_id: str, registry: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    for record in registry:
        if record["source_id"] == source_id:
            return record
    raise KeyError(f"Unknown source_id: {source_id}")


def _stable_hash(*parts: str) -> str:
    joined = "||".join(part.strip() for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _derive_allowed_uses(training_status: str) -> List[str]:
    if training_status == "allowed_public_training":
        return [
            "internal_rag",
            "internal_training",
            "public_training",
            "metadata_extraction",
            "compliance_analysis",
            "citation_only",
        ]
    if training_status == "internal_training_only":
        return [
            "internal_rag",
            "internal_training",
            "metadata_extraction",
            "compliance_analysis",
            "citation_only",
        ]
    if training_status == "retrieval_only":
        return [
            "internal_rag",
            "metadata_extraction",
            "compliance_analysis",
            "citation_only",
        ]
    return ["citation_only"]


def _derive_prohibited_uses(
    redistribution_status: str,
    training_status: str,
) -> List[str]:
    prohibited = {"autonomous_submission", "legal_advice"}

    if redistribution_status != "publishable":
        prohibited.update({"public_republication", "external_sharing"})
    if training_status != "allowed_public_training":
        prohibited.add("public_training")
    if training_status in {"retrieval_only", "blocked"}:
        prohibited.add("external_sharing")
    return sorted(prohibited)


def _derive_handling_rules(
    source: Dict[str, Any],
    artifact_type: str,
) -> List[str]:
    rules = []
    if source["citation_required"]:
        rules.append("Preserve citations and provenance for any downstream synthesis.")
    if source["access_level"] != "public":
        rules.append("Keep raw artifact content in internal storage lanes only.")
    if source["training_status"] == "retrieval_only":
        rules.append("Use for retrieval and metadata extraction only; do not promote into training corpora.")
    if artifact_type in {"portal_dump", "proposal_draft"}:
        rules.append("Do not redistribute raw portal or draft text outside authorized internal workflows.")
    if source["redistribution_status"] == "unclear":
        rules.append("Require human review before any external sharing or public dataset inclusion.")
    if source["redistribution_status"] == "blocked":
        rules.append("Block public redistribution and public training until rights status changes.")
    return rules or ["Default to internal metadata extraction until reviewed."]


def classify_ingestion_rights_record(
    *,
    source_record: Dict[str, Any],
    artifact_ref: str,
    artifact_type: str,
    verification_status: str = "reviewed",
    reviewed_by: str | None = None,
    reviewer_notes: str | None = None,
) -> Dict[str, Any]:
    rights_record = {
        "schema_version": "scbe_ingestion_rights_record_v1",
        "rights_record_id": _stable_hash(source_record["source_id"], artifact_ref, artifact_type),
        "source_id": source_record["source_id"],
        "artifact_ref": artifact_ref,
        "artifact_type": artifact_type,
        "access_level": source_record["access_level"],
        "redistribution_status": source_record["redistribution_status"],
        "training_status": source_record["training_status"],
        "verification_status": verification_status,
        "allowed_uses": _derive_allowed_uses(source_record["training_status"]),
        "prohibited_uses": _derive_prohibited_uses(
            source_record["redistribution_status"],
            source_record["training_status"],
        ),
        "handling_rules": _derive_handling_rules(source_record, artifact_type),
        "reviewed_by": reviewed_by,
        "reviewed_at": datetime.now(UTC).isoformat() if reviewed_by else None,
        "reviewer_notes": reviewer_notes,
    }
    RIGHTS_VALIDATOR.validate(rights_record)
    return rights_record
