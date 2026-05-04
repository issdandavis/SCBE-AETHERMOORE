from __future__ import annotations

from pathlib import Path

from scripts.build_topological_canaries import CANARY_SCHEMA, build_canaries
from scripts.smoke_topological_receipt import run_smoke


def test_build_topological_canaries_has_expected_coverage() -> None:
    payload = build_canaries()

    assert payload["schema_version"] == CANARY_SCHEMA
    assert payload["n"] >= 30
    assert {"coding", "adversarial", "security_pqc", "scbe_lore"}.issubset(payload["coverage"]["categories"])
    assert {"ALLOW", "QUARANTINE"}.issubset(payload["coverage"]["decisions"])
    assert {"KO", "AV", "RU", "CA", "UM", "DR"} == set(payload["coverage"]["tongues"])
    assert payload["canaries"]
    assert all(item["expected"]["binary_packet_sha256"] for item in payload["canaries"])


def test_topological_receipt_canary_file_replays_cleanly() -> None:
    result = run_smoke(Path("tests/canary/topological_receipt_canaries.json"))

    assert result["schema_version"] == CANARY_SCHEMA
    assert result["failed"] == 0
    assert result["passed"] == result["n"]
