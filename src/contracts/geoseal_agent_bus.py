"""GeoSeal-native envelope helpers for agent-bus routing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER


TASK_TONGUE_ROUTE = {
    "coding": "ca",
    "review": "ru",
    "research": "av",
    "governance": "dr",
    "training": "um",
    "general": "ko",
}


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(payload: Any) -> str:
    data = payload if isinstance(payload, str) else canonical_json(payload)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _provider_ids(rows: Any) -> list[str]:
    providers: list[str] = []
    for row in _safe_list(rows):
        if isinstance(row, dict) and row.get("provider"):
            providers.append(str(row["provider"]))
    return providers


def _tokenizer_view(name: str, tongue: str, data: bytes) -> dict[str, Any]:
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, data)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue, tokens)
    token_text = "|".join(tokens)
    return {
        "name": name,
        "tongue": tongue,
        "token_count": len(tokens),
        "token_stream_sha256": hashlib.sha256(token_text.encode("utf-8")).hexdigest(),
        "roundtrip_ok": decoded == data,
        "preview": tokens[:8],
    }


def build_geoseal_agentbus_envelope(summary: dict[str, Any]) -> dict[str, Any]:
    """Build the native GeoSeal routing envelope for an agent-bus run.

    The envelope deliberately hashes task/provider content rather than carrying
    raw prompts or model outputs. It is safe to commit as a routing receipt and
    can be replayed through the triplet ledger.
    """

    task = _safe_dict(summary.get("task"))
    task_type = str(task.get("type") or "general")
    route_tongue = TASK_TONGUE_ROUTE.get(task_type, "ko")
    operation_shape = _safe_dict(summary.get("operation_shape"))
    dispatch = _safe_dict(summary.get("dispatch"))
    dispatch_result = _safe_dict(dispatch.get("result"))
    dispatch_route = _safe_dict(dispatch.get("route"))

    base_envelope = {
        "schema_version": "scbe-geoseal-agentbus-envelope-v1",
        "series_id": str(summary.get("series_id") or ""),
        "generated_at": str(summary.get("generated_at") or ""),
        "privacy": str(summary.get("privacy") or "local_only"),
        "budget_cents": float(summary.get("budget_cents") or 0.0),
        "route": {
            "task_type": task_type,
            "route_tongue": route_tongue,
            "selected_provider": str(summary.get("selected_provider") or ""),
            "provider_privacy": str(dispatch_route.get("privacy") or "local"),
            "provider_kind": str(dispatch_route.get("kind") or "offline"),
        },
        "task": {
            "sha256": str(task.get("sha256") or ""),
            "chars": int(task.get("chars") or 0),
        },
        "operation_shape": {
            "present": bool(operation_shape),
            "root_value": operation_shape.get("root_value"),
            "signature_hex": operation_shape.get("signature_hex"),
            "signature_binary": operation_shape.get("signature_binary"),
            "floating_point_policy": operation_shape.get("floating_point_policy"),
        },
        "hydra_protocols": {
            "formation": "mirror_room",
            "protocols": [
                "play_watch_rest",
                "local_first_provider_selection",
                "anti_amplification_watchers",
                "mission_rehearsal_gate",
                "observable_state_watcher",
                "message_triplet_ledger",
            ],
            "free_provider_order": ["offline", "ollama", "huggingface"],
            "provider_lanes": {
                "primary": _provider_ids(summary.get("primary_bus")),
                "secondary": _provider_ids(summary.get("secondary_bus")),
                "tertiary_count": int(summary.get("tertiary_bus_count") or 0),
            },
        },
        "dispatch": {
            "enabled": bool(dispatch.get("enabled")),
            "provider": str(dispatch.get("provider") or ""),
            "event_id": dispatch.get("event_id"),
            "finish_reason": dispatch_result.get("finish_reason"),
            "result_text_sha256": (
                hashlib.sha256(str(dispatch_result.get("text") or "").encode("utf-8")).hexdigest()
                if dispatch_result.get("text")
                else None
            ),
        },
        "governance": {
            "rehearsal_gate": _safe_dict(summary.get("rehearsal_gate")),
            "telemetry": _safe_dict(summary.get("telemetry")),
            "abort_condition": str(summary.get("abort_condition") or ""),
            "raw_prompt_policy": "hashes only; raw task text stays outside the route receipt",
        },
    }
    canonical = canonical_json(base_envelope).encode("utf-8")
    tokenizer_a = _tokenizer_view("intent_route_ko_v1", "ko", canonical)
    tokenizer_b = _tokenizer_view("bitcraft_route_ca_v1", "ca", canonical)
    envelope_hash = hashlib.sha256(canonical).hexdigest()
    return {
        **base_envelope,
        "envelope_hash": envelope_hash,
        "dual_tokenizer_seal": {
            "pair": ["intent_route_ko_v1", "bitcraft_route_ca_v1"],
            "tokenizer_a": tokenizer_a,
            "tokenizer_b": tokenizer_b,
            "pair_hash": sha256_hex({"a": tokenizer_a, "b": tokenizer_b}),
            "roundtrip_ok": bool(tokenizer_a["roundtrip_ok"] and tokenizer_b["roundtrip_ok"]),
        },
    }


def verify_geoseal_agentbus_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    seal = _safe_dict(envelope.get("dual_tokenizer_seal"))
    tokenizer_a = _safe_dict(seal.get("tokenizer_a"))
    tokenizer_b = _safe_dict(seal.get("tokenizer_b"))
    expected_pair_hash = sha256_hex({"a": tokenizer_a, "b": tokenizer_b})
    return {
        "schema_version": "scbe-geoseal-agentbus-envelope-verify-v1",
        "ok": (
            envelope.get("schema_version") == "scbe-geoseal-agentbus-envelope-v1"
            and bool(seal.get("roundtrip_ok"))
            and seal.get("pair_hash") == expected_pair_hash
            and bool(envelope.get("route", {}).get("route_tongue"))
        ),
        "route_tongue": envelope.get("route", {}).get("route_tongue"),
        "pair_hash": seal.get("pair_hash"),
        "expected_pair_hash": expected_pair_hash,
    }
