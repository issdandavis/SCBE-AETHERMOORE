from __future__ import annotations

import json
from pathlib import Path

from scripts.extract_model_trace_records import extract_records


def test_extract_records_from_jsonl_is_deterministic(tmp_path: Path) -> None:
    input_path = tmp_path / "grok_trace.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "title": "Route schema",
                "source_model": "grok",
                "messages": [
                    {"role": "user", "content": "Turn this conversation into a schema and builder."},
                    {
                        "role": "assistant",
                        "content": "The route-consistency object should preserve intent and execution.\n\n1. Add schema\n2. Add builder for scripts/build_route_consistency_records.py\n\n```python\nprint('ok')\n```\n\nALLOW once verified.",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    first = extract_records([input_path])
    second = extract_records([input_path])

    assert len(first) == 1
    assert first == second
    record = first[0]
    assert record["source_model"] == "grok"
    assert record["verification"]["human_verified"] is False
    assert record["extracted_structured_record"]["proposed_artifacts"]
    assert record["extracted_structured_record"]["governance_claims"][0]["status"] == "ALLOW"


def test_extract_records_links_shared_intents(tmp_path: Path) -> None:
    input_path = tmp_path / "paired_traces.jsonl"
    rows = [
        {
            "title": "Trace A",
            "source_model": "grok",
            "messages": [
                {"role": "user", "content": "Build the route consistency schema."},
                {"role": "assistant", "content": "Add the schema file and tests."},
            ],
        },
        {
            "title": "Trace B",
            "source_model": "claude",
            "messages": [
                {"role": "user", "content": "Build the route consistency schema."},
                {"role": "assistant", "content": "Implement the builder and validate outputs."},
            ],
        },
    ]
    input_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    records = extract_records([input_path])
    assert len(records) == 2
    assert (
        records[0]["extracted_structured_record"]["intent_id"] == records[1]["extracted_structured_record"]["intent_id"]
    )
    assert records[0]["extracted_structured_record"]["triangulation_links"][0]["linked_ids"] == [records[1]["trace_id"]]
    assert records[1]["extracted_structured_record"]["triangulation_links"][0]["linked_ids"] == [records[0]["trace_id"]]
