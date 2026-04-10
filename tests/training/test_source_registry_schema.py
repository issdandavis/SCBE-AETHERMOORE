from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_source_registry_entries_validate() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    schema = json.loads((repo_root / "schemas" / "source_registry_record.schema.json").read_text(encoding="utf-8"))
    registry = json.loads((repo_root / "config" / "research" / "source_registry.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    assert isinstance(registry, list)
    assert registry

    for record in registry:
        validator.validate(record)
