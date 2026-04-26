from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "agentbus_rehearsal_gate.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("agentbus_rehearsal_gate", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _round_packet(**overrides):
    packet = {
        "version": "mirror-room-agent-bus-round-v1",
        "privacy": "local_only",
        "task": {"sha256": "abc", "chars": 40, "type": "coding"},
        "selected_provider": "offline",
        "primary_bus": [{"provider": "offline", "role": "play", "score": 8.0}],
        "secondary_bus": [{"provider": "ollama", "role": "watch", "score": 7.0}],
        "tertiary_bus": [],
        "mirror_room": {"anti_amplification": "watchers do not respond unless promoted"},
        "budget": {"per_round_cents": 0.0, "selected_estimated_cents": 0.0},
        "operation_shape": {
            "floating_point_policy": "forbidden for consensus signatures",
            "signature_binary": "1010",
            "signature_hex": "a",
        },
    }
    packet.update(overrides)
    return packet


def test_local_round_passes_rehearsal_gate() -> None:
    module = _load_module()

    report = module.evaluate_rehearsal_gate(_round_packet())

    assert report["schema_version"] == "scbe_agentbus_rehearsal_gate_v1"
    assert report["status"] == "pass"
    assert report["failure_count"] == 0
    assert report["advantage"]["dataset_value"].startswith("turns each bus round")


def test_local_only_rejects_known_remote_provider() -> None:
    module = _load_module()

    report = module.evaluate_rehearsal_gate(
        _round_packet(
            selected_provider="openai",
            primary_bus=[{"provider": "openai", "role": "play", "score": 5.0}],
        )
    )

    failed = {row["name"] for row in report["checks"] if not row["ok"]}
    assert report["status"] == "fail"
    assert "local_only_blocks_remote_provider" in failed


def test_strict_gate_requires_telemetry_and_abort_condition() -> None:
    module = _load_module()

    report = module.evaluate_rehearsal_gate(_round_packet(privacy="remote_ok"), strict=True)

    failed = {row["name"] for row in report["checks"] if not row["ok"]}
    assert report["status"] == "fail"
    assert "telemetry_sink_present" in failed
    assert "abort_condition_present" in failed


def test_remote_round_with_envelope_passes_strict_gate() -> None:
    module = _load_module()

    report = module.evaluate_rehearsal_gate(
        _round_packet(
            privacy="remote_ok",
            selected_provider="huggingface",
            primary_bus=[{"provider": "huggingface", "role": "play", "score": 5.0}],
            budget={"per_round_cents": 2.0, "selected_estimated_cents": 0.2},
            telemetry={"path": "artifacts/agent_bus/telemetry/run.jsonl"},
            abort_condition="stop if provider returns unsafe or empty output",
        ),
        strict=True,
    )

    assert report["status"] == "pass"
    assert report["failure_count"] == 0
