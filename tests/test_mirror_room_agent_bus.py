from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "mirror_room_agent_bus.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("mirror_room_agent_bus", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _router_config(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "providers": {
                    "openai": {
                        "enabled": True,
                        "env_keys": ["OPENAI_API_KEY"],
                        "tiers": {"cheap": {"model": "gpt-test", "estimated_cents": 1.2}},
                    },
                    "anthropic": {
                        "enabled": True,
                        "env_keys": ["ANTHROPIC_API_KEY"],
                        "tiers": {"cheap": {"model": "claude-test", "estimated_cents": 1.6}},
                    },
                    "xai": {
                        "enabled": True,
                        "env_keys": ["XAI_API_KEY"],
                        "tiers": {"cheap": {"model": "grok-test", "estimated_cents": 1.0}},
                    },
                    "huggingface": {
                        "enabled": True,
                        "env_keys": ["HF_TOKEN"],
                        "tiers": {"cheap": {"model": "hf-test", "estimated_cents": 0.2}},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_local_only_match_prefers_local_player(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    config = _router_config(tmp_path / "router.json")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    result = module.schedule_match_round(
        task="write a Python add function",
        task_type="coding",
        series_id="local-only",
        round_index=1,
        privacy="local_only",
        budget_cents=10,
        output_root=tmp_path / "mirror",
        config_path=config,
    )

    assert result["selected_provider"] in {"offline", "ollama"}
    assert all(row["provider"] in {"offline", "ollama"} for row in result["primary_bus"])
    assert "write a Python add function" not in json.dumps(result)
    assert (tmp_path / "mirror" / "local-only" / "mirror_room.jsonl").exists()


def test_remote_ok_research_can_pick_configured_remote_provider(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    config = _router_config(tmp_path / "router.json")
    monkeypatch.setenv("XAI_API_KEY", "test")

    result = module.schedule_match_round(
        task="compare two source-grounded research summaries",
        task_type="research",
        series_id="remote-research",
        round_index=1,
        privacy="remote_ok",
        budget_cents=10,
        output_root=tmp_path / "mirror",
        config_path=config,
    )

    assert result["selected_provider"] in {"xai", "huggingface", "ollama", "offline"}
    assert result["mirror_room"]["anti_amplification"].startswith("watchers do not respond")
    assert result["secondary_bus"]


def test_recent_player_fatigues_and_next_round_can_rotate(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    config = _router_config(tmp_path / "router.json")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    first = module.schedule_match_round(
        task="review code",
        task_type="review",
        series_id="fatigue",
        round_index=1,
        privacy="remote_ok",
        budget_cents=10,
        output_root=tmp_path / "mirror",
        config_path=config,
    )
    second = module.schedule_match_round(
        task="review code again",
        task_type="review",
        series_id="fatigue",
        round_index=2,
        privacy="remote_ok",
        budget_cents=10,
        output_root=tmp_path / "mirror",
        config_path=config,
    )

    assert first["selected_provider"]
    assert second["selected_provider"]
    assert second["mirror_room"]["history_events"] == 1
    if first["selected_provider"] == second["selected_provider"]:
        selected_reason = second["primary_bus"][0]["reason"]
        assert "conserve after" in selected_reason


def test_custom_local_provider_is_discovered(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    config = _router_config(tmp_path / "router.json")
    monkeypatch.setenv(
        "SCBE_FREE_LLM_PROVIDERS",
        json.dumps(
            {
                "local-coder": {
                    "enabled": True,
                    "endpoint": "http://127.0.0.1:9999/v1/chat/completions",
                    "strengths": ["coding", "review"],
                }
            }
        ),
    )

    players = module.discover_players(config)

    local_coder = next(player for player in players if player.provider == "local-coder")
    assert local_coder.privacy == "local"
    assert "coding" in local_coder.strengths


def test_operation_command_braids_topological_shape_into_round(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    config = _router_config(tmp_path / "router.json")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    result = module.schedule_match_round(
        task="run a shaped operation",
        task_type="coding",
        series_id="shape-braid",
        round_index=1,
        privacy="local_only",
        budget_cents=0,
        output_root=tmp_path / "mirror",
        config_path=config,
        operation_command="korah aelin dahru",
    )

    shape = result["operation_shape"]
    assert shape["schema_version"] == "mirror-room-operation-shape-v1"
    assert shape["root_value"] == 12026
    assert shape["floating_point_policy"] == "forbidden for consensus signatures"
    assert len(shape["signature_binary"]) == 64
    assert [token["id"] for token in shape["tokens"]] == [0, 1, 2]
    assert "korah aelin dahru" not in json.dumps(result)
