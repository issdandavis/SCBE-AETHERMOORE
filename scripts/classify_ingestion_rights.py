#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.ingestion_rights import (  # noqa: E402
    DEFAULT_SOURCE_REGISTRY_PATH,
    classify_ingestion_rights_record,
    get_source_record,
    load_source_registry,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify ingestion rights for a source artifact using the SCBE source registry.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_SOURCE_REGISTRY_PATH)
    parser.add_argument("--list-sources", action="store_true")
    parser.add_argument("--source-id")
    parser.add_argument("--artifact-ref")
    parser.add_argument(
        "--artifact-type",
        choices=[
            "portal_dump",
            "pdf",
            "note",
            "api_result",
            "html_page",
            "chat_trace",
            "proposal_draft",
            "solicitation",
            "award_notice",
            "guidance",
            "paper",
            "dataset",
        ],
    )
    parser.add_argument("--verification-status", default="reviewed", choices=["unreviewed", "reviewed", "verified"])
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--reviewer-notes", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    registry = load_source_registry(args.registry)

    if args.list_sources:
        print(json.dumps(registry, indent=2))
        return

    if not args.source_id or not args.artifact_ref or not args.artifact_type:
        parser.error("--source-id, --artifact-ref, and --artifact-type are required unless --list-sources is used")

    source = get_source_record(args.source_id, registry)
    record = classify_ingestion_rights_record(
        source_record=source,
        artifact_ref=args.artifact_ref,
        artifact_type=args.artifact_type,
        verification_status=args.verification_status,
        reviewed_by=args.reviewed_by,
        reviewer_notes=args.reviewer_notes,
    )

    payload = json.dumps(record, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
