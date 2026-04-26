from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config" / "security" / "ai_red_team_scenario_catalog_v1.json"


def test_ai_red_team_scenario_catalog_is_valid_and_source_backed() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    sources = set(catalog["source_index"])

    assert catalog["schema_version"] == "scbe_ai_red_team_scenario_catalog_v1"
    assert len(catalog["single_scenarios"]) >= 12
    assert len(catalog["nested_chains"]) >= 5

    for scenario in catalog["single_scenarios"]:
        assert scenario["id"]
        assert scenario["surface"]
        assert scenario["ingestion_path"]
        assert scenario["expected_decision"] in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
        assert scenario["source_ids"]
        assert set(scenario["source_ids"]).issubset(sources)
        assert "payload" not in scenario

    for chain in catalog["nested_chains"]:
        assert len(chain["steps"]) >= 4
        assert chain["expected_final_decision"] in {"ALLOW", "QUARANTINE", "ESCALATE", "DENY"}
        assert set(chain["source_ids"]).issubset(sources)


def test_catalog_keeps_untrusted_content_as_data_not_authority() -> None:
    catalog_text = CATALOG.read_text(encoding="utf-8").lower()
    assert "untrusted" in catalog_text
    assert "authority" in catalog_text
    assert "operational jailbreak payloads" in catalog_text
