from __future__ import annotations

from src.contracts.geoseal_agent_bus import (
    build_geoseal_agentbus_envelope,
    verify_geoseal_agentbus_envelope,
)


def _summary(task_type: str = "coding") -> dict:
    return {
        "schema_version": "scbe_agentbus_user_run_v1",
        "generated_at": "2026-04-27T00:00:00Z",
        "series_id": "pytest-geoseal-bus",
        "privacy": "local_only",
        "budget_cents": 0,
        "task": {
            "sha256": "a" * 64,
            "chars": 42,
            "type": task_type,
        },
        "operation_shape": {
            "root_value": 12026,
            "signature_hex": "c176ca9a2f3473c6d643c1ef8b000c7a",
            "signature_binary": "1100000101110110110010101001101000101111001101000111001111000110",
            "floating_point_policy": "forbidden for consensus signatures",
        },
        "selected_provider": "offline",
        "primary_bus": [{"provider": "offline", "role": "play"}],
        "secondary_bus": [{"provider": "ollama", "role": "watch"}],
        "tertiary_bus_count": 1,
        "dispatch": {
            "enabled": True,
            "provider": "offline",
            "event_id": "event-1",
            "route": {"privacy": "local", "kind": "offline"},
            "result": {"finish_reason": "offline_deterministic", "text": "accepted"},
        },
        "rehearsal_gate": {"status": "pass", "failure_count": 0, "warning_count": 0},
    }


def test_geoseal_agentbus_envelope_binds_hydra_and_dual_tokenizers() -> None:
    envelope = build_geoseal_agentbus_envelope(_summary())

    assert envelope["schema_version"] == "scbe-geoseal-agentbus-envelope-v1"
    assert envelope["route"]["route_tongue"] == "ca"
    assert envelope["hydra_protocols"]["formation"] == "mirror_room"
    assert "mission_rehearsal_gate" in envelope["hydra_protocols"]["protocols"]
    assert envelope["hydra_protocols"]["provider_lanes"]["primary"] == ["offline"]
    assert envelope["hydra_protocols"]["provider_lanes"]["secondary"] == ["ollama"]
    assert envelope["dual_tokenizer_seal"]["roundtrip_ok"] is True
    assert envelope["dual_tokenizer_seal"]["tokenizer_a"]["tongue"] == "ko"
    assert envelope["dual_tokenizer_seal"]["tokenizer_b"]["tongue"] == "ca"

    verification = verify_geoseal_agentbus_envelope(envelope)
    assert verification["ok"] is True
    assert verification["route_tongue"] == "ca"


def test_geoseal_agentbus_task_types_route_to_distinct_tongues() -> None:
    expected = {
        "coding": "ca",
        "review": "ru",
        "research": "av",
        "governance": "dr",
        "training": "um",
        "general": "ko",
    }

    for task_type, tongue in expected.items():
        envelope = build_geoseal_agentbus_envelope(_summary(task_type))
        assert envelope["route"]["route_tongue"] == tongue
