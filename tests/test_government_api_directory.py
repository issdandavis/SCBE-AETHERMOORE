from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "src" / "knowledge" / "storage" / "government_api_directory.json"


def test_government_api_directory_free_buckets_are_routeable() -> None:
    payload = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    buckets = payload["connector_buckets"]

    assert payload["source_url"] == "https://open.gsa.gov/api/"
    assert buckets["free_public_no_key"]
    assert buckets["free_public_key_required"]

    connectors = {connector["id"]: connector for connector in payload["connectors"]}
    free_ids = set(payload["free_public_connector_ids"])
    partner_ids = set(buckets["partner_gated"])

    assert free_ids
    assert not (free_ids & partner_ids)

    for connector_id in buckets["free_public_no_key"]:
        connector = connectors[connector_id]
        assert connector["free_to_add"] is True
        assert connector["deployment_safe"] is True
        assert connector["requires_api_key"] is False

    for connector_id in buckets["free_public_key_required"]:
        connector = connectors[connector_id]
        assert connector["free_to_add"] is True
        assert connector["deployment_safe"] is True
        assert connector["requires_api_key"] is True
        assert connector["required_env"]

    for connector_id in buckets["partner_gated"]:
        connector = connectors[connector_id]
        assert connector["free_to_add"] is False
        assert connector["deployment_safe"] is False
