from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_model_trace_schema_accepts_minimal_record() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    schema = json.loads((repo_root / "schemas" / "model_trace_record.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    record = {
        "schema_version": "scbe_model_trace_record_v1",
        "trace_id": "trace_12345678",
        "source_model": "grok",
        "interaction_type": "agentic_dialogue",
        "raw_model_trace": {
            "title": "Route expansion",
            "source_corpus": "training-data/grok_trace.jsonl",
            "messages": [
                {"role": "user", "content": "Plan the route consistency schema."},
                {"role": "assistant", "content": "1. Add schema\n2. Add builder\n3. Add tests"}
            ]
        },
        "extracted_structured_record": {
            "intent_id": "intent_12345678",
            "route_id": "trace_route_12345678",
            "route_family": "agentic_dialogue",
            "target_cluster": "trace_cluster_12345678",
            "source_model": "grok",
            "concept_view": "Build a shared schema.",
            "process_view": "1. Add schema\n2. Add builder",
            "execution_view": "scripts/build_route_consistency_records.py",
            "proposed_artifacts": ["schemas/model_trace_record.schema.json"],
            "governance_claims": [{"claim": "verification pending", "status": "UNSPECIFIED"}],
            "triangulation_links": [],
            "confidence": 0.42
        },
        "verification": {
            "human_verified": False,
            "trust_level": "raw_model_trace"
        }
    }
    validator.validate(record)
