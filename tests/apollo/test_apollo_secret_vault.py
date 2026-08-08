from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.apollo import apollo_core


def test_scrub_metadata_does_not_retain_secret_derived_identifiers() -> None:
    secret = "password=hunter2"

    clean, items = apollo_core.scrub_text(secret)

    assert "hunter2" not in clean
    assert items
    assert all("fingerprint" not in item for item in items)


def test_vault_persists_only_counts_and_categories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault_path = tmp_path / "vault.json"
    monkeypatch.setattr(apollo_core, "VAULT_PATH", vault_path)
    _, items = apollo_core.scrub_text("token=super-secret-value")

    apollo_core.vault_secrets(items, context="email:private-message-id")

    entry = json.loads(vault_path.read_text(encoding="utf-8"))["entries"][0]
    assert set(entry) == {"timestamp", "source_kind", "count", "types"}
    assert entry["source_kind"] == "email"
    assert entry["count"] == 1
    assert entry["types"] == ["generic"]
    assert "fingerprints" not in entry
    assert "private-message-id" not in vault_path.read_text(encoding="utf-8")
    assert "super-secret-value" not in vault_path.read_text(encoding="utf-8")
