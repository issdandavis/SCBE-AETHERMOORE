from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.system.agentbus_pressure_test import run_pressure


def _router_config(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "providers": {
                    "huggingface": {
                        "enabled": True,
                        "env_keys": ["HF_TOKEN"],
                        "tiers": {"cheap": {"estimated_cents": 0.2}},
                    },
                    "kaggle": {
                        "enabled": True,
                        "env_keys": ["KAGGLE_USERNAME", "KAGGLE_KEY"],
                        "tiers": {"cheap": {"estimated_cents": 0.0}},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_agentbus_pressure_test_blocks_backdoor_and_keeps_game_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setenv("KAGGLE_USERNAME", "test-user")
    monkeypatch.setenv("KAGGLE_KEY", "test-key")
    args = type(
        "Args",
        (),
        {
            "run_id": "pytest-pressure",
            "privacy": "remote_ok",
            "budget_cents": 1.0,
            "max_players": 2,
            "operation_command": "korah aelin dahru",
            "config": str(_router_config(tmp_path / "router.json")),
            "output_root": str(tmp_path / "pressure"),
        },
    )()

    report = run_pressure(args)

    assert report["overall_status"] == "pass"
    assert "huggingface" in report["provider_lanes_seen"]
    assert "kaggle" in report["provider_lanes_seen"]
    by_id = {row["scenario_id"]: row for row in report["scenarios"]}
    assert by_id["S01_BACKDOOR_POLARITY"]["intent"]["decision"] == "DENY"
    assert by_id["S01_BACKDOOR_POLARITY"]["geoseal_agentbus"]["route_tongue"] == "dr"
    assert by_id["S01_BACKDOOR_POLARITY"]["geoseal_agentbus"]["verify_ok"] is True
    assert "mission_rehearsal_gate" in by_id["S01_BACKDOOR_POLARITY"]["geoseal_agentbus"]["hydra_protocols"]
    assert by_id["S02_GAME_NEGABINARY"]["intent"]["decision"] == "ALLOW"
    assert by_id["S02_GAME_NEGABINARY"]["geoseal_agentbus"]["route_tongue"] == "um"
    assert (tmp_path / "pressure" / "pytest-pressure" / "report.json").exists()


def test_agentbus_pressure_test_runs_catalog_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setenv("KAGGLE_USERNAME", "test-user")
    monkeypatch.setenv("KAGGLE_KEY", "test-key")
    args = type(
        "Args",
        (),
        {
            "run_id": "pytest-catalog-pressure",
            "privacy": "remote_ok",
            "budget_cents": 1.0,
            "max_players": 2,
            "operation_command": "korah aelin dahru",
            "config": str(_router_config(tmp_path / "router.json")),
            "output_root": str(tmp_path / "pressure"),
            "use_catalog": True,
            "scenario_catalog": str(ROOT / "config" / "security" / "ai_red_team_scenario_catalog_v1.json"),
            "include_chains": True,
            "scenario_filter": "CHAIN_LOW_PRIV_AGENT_TO_HIGH_PRIV_AGENT",
            "limit": 1,
        },
    )()

    report = run_pressure(args)

    assert report["overall_status"] == "pass"
    assert report["scenarios"][0]["scenario_id"] == "CHAIN_LOW_PRIV_AGENT_TO_HIGH_PRIV_AGENT"
    assert report["scenarios"][0]["intent"]["decision"] == "DENY"
    assert report["scenarios"][0]["geoseal_agentbus"]["verify_ok"] is True
