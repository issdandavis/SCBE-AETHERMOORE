from __future__ import annotations

import json
from pathlib import Path

from scripts.obsidian_local_promotion import (
    build_review_queue_markdown,
    load_decisions,
    promote_verified_traces,
    resolve_note_paths,
    write_decision_template,
    write_trace_records,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TRACE_SCHEMA = REPO_ROOT / "schemas" / "model_trace_record.schema.json"
ROUTE_SCHEMA = REPO_ROOT / "schemas" / "route_consistency_record.schema.json"


def test_resolve_note_paths_uses_existing_vault_shapes(tmp_path: Path) -> None:
    (tmp_path / "notes" / ".obsidian").mkdir(parents=True)
    (tmp_path / "notes" / "Messges Dumps_trainging files").mkdir(parents=True)
    inbox = tmp_path / "notes" / "_inbox.md"
    dump = tmp_path / "notes" / "Messges Dumps_trainging files" / "First Dump.md"
    hidden = tmp_path / "notes" / ".obsidian" / "ignore.md"
    inbox.write_text("hello", encoding="utf-8")
    dump.write_text("world", encoding="utf-8")
    hidden.write_text("skip", encoding="utf-8")

    resolved = resolve_note_paths(tmp_path)
    assert inbox.resolve() in resolved
    assert dump.resolve() in resolved
    assert hidden.resolve() not in resolved


def test_extract_and_promote_obsidian_traces(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    agent_memory = notes_dir / "agent-memory"
    agent_memory.mkdir(parents=True)
    note_path = notes_dir / "_inbox.md"
    note_path.write_text(
        """
Use the route consistency builder for local promotion.

1. Extract traces from notes.
2. Verify them locally.

```python
print('verified locally')
```

ALLOW once reviewed.
""".strip(),
        encoding="utf-8",
    )

    trace_output = tmp_path / "training-data" / "model_traces" / "obsidian" / "trace_records.jsonl"
    records = write_trace_records(
        note_paths=[note_path],
        output_jsonl=trace_output,
        schema_path=TRACE_SCHEMA,
        source_model="grok",
    )
    assert len(records) == 1

    decisions_path = agent_memory / "obsidian-trace-decisions.jsonl"
    assert write_decision_template(records, decisions_path, overwrite=True) is True
    queue_markdown = build_review_queue_markdown(records, decisions_path=decisions_path, repo_root=tmp_path)
    assert "Obsidian Trace Review Queue" in queue_markdown
    assert records[0]["trace_id"] in queue_markdown

    promoted_decision = {
        "trace_id": records[0]["trace_id"],
        "decision": "promote",
        "notes": "Verified by local review.",
        "language_override": "python",
        "tongue_override": "CA",
        "layer_override": "L3",
    }
    decisions_path.write_text(json.dumps(promoted_decision) + "\n", encoding="utf-8")

    result = promote_verified_traces(
        trace_records=records,
        decisions=load_decisions(decisions_path),
        verified_output=tmp_path / "verified_traces.jsonl",
        route_seed_output=tmp_path / "route_seed.jsonl",
        route_output=tmp_path / "route_records.jsonl",
        route_manifest=tmp_path / "route_manifest.json",
        repo_root=tmp_path,
        route_schema_path=ROUTE_SCHEMA,
    )

    assert result["promoted_count"] == 1

    verified_rows = [
        json.loads(line)
        for line in (tmp_path / "verified_traces.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert verified_rows[0]["verification"]["human_verified"] is True
    assert verified_rows[0]["verification"]["trust_level"] == "human_verified_record"

    route_rows = [
        json.loads(line) for line in (tmp_path / "route_records.jsonl").read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(route_rows) == 1
    assert route_rows[0]["route_metadata"]["tongue"] == "CA"
    assert route_rows[0]["input"]["language"] == "python"
