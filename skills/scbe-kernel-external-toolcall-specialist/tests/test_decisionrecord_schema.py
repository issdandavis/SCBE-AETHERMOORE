from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "decisionrecord.schema.json"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_decisionrecord_valid() -> None:
    schema = load_schema()
    payload = {
        "action": "HOLD",
        "signature": "node-x:task-1:1700000000",
        "timestamp": "2026-02-18T04:09:00Z",
        "reason": "human review required",
        "confidence": 0.78,
    }
    jsonschema.validate(payload, schema)


def test_decisionrecord_invalid_confidence() -> None:
    schema = load_schema()
    payload = {
        "action": "HOLD",
        "signature": "node-x:task-1:1700000000",
        "timestamp": "2026-02-18T04:09:00Z",
        "reason": "human review required",
        "confidence": 1.2,
    }
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("expected validation to fail for out-of-range confidence")
