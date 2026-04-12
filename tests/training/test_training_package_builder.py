from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.build_training_package import build_training_package


def test_build_training_package_stages_and_merges_lanes(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]

    source_note = tmp_path / "note.md"
    source_note.write_text("# Note\n\nThis becomes reusable training context.\n", encoding="utf-8")

    sft_path = tmp_path / "sft.jsonl"
    sft_path.write_text(
        json.dumps(
            {
                "id": "row_1",
                "instruction": "Summarize the note.",
                "response": "This becomes reusable training context.",
                "metadata": {"source_type": "markdown"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    route_path = tmp_path / "route.jsonl"
    route_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_route_consistency_record_v1",
                "record_id": "route_record_1234",
                "intent_id": "intent_record_1234",
                "route_id": "route_record_5678",
                "route_family": "instruction_projection",
                "target_cluster": "cluster_record_1234",
                "source_corpus": "tmp/route.jsonl",
                "input": {"text": "Summarize the note.", "language": "en"},
                "route_metadata": {
                    "tongue": "RU",
                    "layer": "L3",
                    "view": "instruction_response",
                    "governance": "ALLOW",
                },
                "atomic_features": {
                    "tokens": ["Summarize", "note"],
                    "elements": [
                        {
                            "symbol": "H",
                            "Z": 1,
                            "group": 1,
                            "period": 1,
                            "valence": 1,
                            "electronegativity": 2.2,
                            "witness_stable": True,
                        }
                    ],
                    "trits": [{"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0}],
                },
                "triangulation_links": [],
                "labels": {
                    "target_behavior": "summary",
                    "expected_outcome": "grounded answer",
                    "passes_governance": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    model_trace_path = tmp_path / "model_trace.jsonl"
    model_trace_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_model_trace_record_v1",
                "trace_id": "trace_12345678",
                "source_model": "codex",
                "interaction_type": "agentic_dialogue",
                "raw_model_trace": {
                    "title": "Summarize route",
                    "source_corpus": "tmp/model_trace.jsonl",
                    "messages": [
                        {"role": "user", "content": "Summarize the note."},
                        {"role": "assistant", "content": "This becomes reusable training context."},
                    ],
                },
                "extracted_structured_record": {
                    "intent_id": "intent_12345678",
                    "route_id": "trace_route_12345678",
                    "route_family": "agentic_dialogue",
                    "target_cluster": "trace_cluster_12345678",
                    "source_model": "codex",
                    "concept_view": "Summarize a note.",
                    "process_view": "Read note, emit summary.",
                    "execution_view": "training package builder",
                    "proposed_artifacts": ["normalized/model_traces_merged.jsonl"],
                    "governance_claims": [{"claim": "review pending", "status": "UNSPECIFIED"}],
                    "triangulation_links": [],
                    "confidence": 0.7,
                },
                "verification": {"human_verified": False, "trust_level": "raw_model_trace"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rights_path = tmp_path / "rights.jsonl"
    rights_path.write_text(
        json.dumps(
            {
                "schema_version": "scbe_ingestion_rights_record_v1",
                "rights_record_id": "rights_record_1234",
                "source_id": "sam_gov_public_api",
                "artifact_ref": "tmp/source.json",
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
                    "citation_only",
                ],
                "prohibited_uses": ["autonomous_submission", "legal_advice"],
                "handling_rules": ["Preserve citations and provenance for any downstream synthesis."],
                "reviewed_by": "issdandavis",
                "reviewed_at": "2026-04-09T00:00:00+00:00",
                "reviewer_notes": "Public and trainable.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = build_training_package(
        package_name="demo-training-pack",
        source_inputs=[str(source_note)],
        sft_inputs=[str(sft_path)],
        route_inputs=[str(route_path)],
        model_trace_inputs=[str(model_trace_path)],
        rights_inputs=[str(rights_path)],
        output_root=tmp_path / "out",
        package_stamp="20260409T180000Z",
        notes="Reusable package for training synthesis.",
        create_archive=True,
    )

    assert result["package_id"] == "demo-training-pack-20260409T180000Z"
    assert result["counts"]["source_files"] == 1
    assert result["counts"]["sft_rows"] == 1
    assert result["counts"]["route_consistency_rows"] == 1
    assert result["counts"]["model_trace_rows"] == 1
    assert result["counts"]["rights_rows"] == 1

    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads((repo_root / "schemas" / "training_package_manifest.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)

    assert Path(manifest["outputs"]["merged_sft"]).exists()
    assert Path(manifest["outputs"]["merged_route_consistency"]).exists()
    assert Path(manifest["outputs"]["merged_model_traces"]).exists()
    assert Path(manifest["outputs"]["merged_rights"]).exists()
    assert Path(manifest["outputs"]["report"]).exists()
    assert Path(manifest["outputs"]["archive"]).exists()

    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "SCBE Training Package" in report
    assert "demo-training-pack-20260409T180000Z" in report
