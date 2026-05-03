from __future__ import annotations

from scripts.benchmark.harness_provider_matrix import build_provider_matrix
from scripts.terminal.geoseal_control_panel_brain import classify_intent, recommend_turn


def test_classify_intent_maps_training_and_design() -> None:
    assert classify_intent("set up the next training eval run") == "training_eval"
    assert classify_intent("design a tokenizer braid for the fleet") == "design"
    assert classify_intent("rotate API key safely") == "security"


def test_recommend_turn_prefers_nvidia_for_coding_eval_when_available(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    matrix = build_provider_matrix(
        [
            "ollama:local-coder",
            "nvidia:qwen/qwen3-coder-480b-a35b-instruct",
        ]
    )

    turn = recommend_turn(goal="benchmark coding eval and repair quality", matrix=matrix)

    assert turn.intent == "training_eval"
    assert turn.recommended_provider == "nvidia"
    assert turn.verdict == "HOLD"
    assert turn.action_id == "verify-evidence"
    assert turn.lane_signal == "provider-pair:local->nvidia:training_eval"


def test_recommend_turn_keeps_secret_tasks_local(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    matrix = build_provider_matrix(
        [
            "ollama:local-coder",
            "nvidia:qwen/qwen3-coder-480b-a35b-instruct",
        ]
    )

    turn = recommend_turn(goal="inspect secret env key handling", matrix=matrix)

    assert turn.intent == "security"
    assert turn.recommended_provider == "ollama"
    assert turn.lane_signal == ""
    assert "local" in turn.reason
