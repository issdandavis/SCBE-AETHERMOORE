from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "statevector.schema.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_statevector_valid() -> None:
    schema = load_schema()
    payload = {
        "worker_id": "node-1",
        "task_id": "task-abc",
        "role": "coder",
        "status": "done",
        "timestamp": "2026-02-18T04:09:00Z",
        "turnstile_action": "ALLOW",
        "attempts": 1,
    }
    jsonschema.validate(payload, schema)


def test_statevector_invalid_missing_required() -> None:
    schema = load_schema()
    payload = {
        "worker_id": "node-1",
        "task_id": "task-abc",
        "status": "done",
        "timestamp": "2026-02-18T04:09:00Z",
    }
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("expected validation to fail for missing required fields")
