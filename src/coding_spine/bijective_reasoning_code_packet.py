"""Bijective reasoning/code packet builder.

This module promotes code packetization from a CLI-only surface into a reusable
runtime artifact: intent -> route -> semantic packet -> code view -> transport
-> verification.  It is deliberately deterministic so it can be used before an
LLM writes code and again after code exists.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from src.ca_lexicon import ALL_LANG_MAP, LANG_MAP, TONGUE_PARENT
from src.coding_spine.deterministic_tongue_router import route_prompt
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER
from src.tokenizer.code_weight_packets import build_code_weight_packet

SCHEMA_VERSION = "scbe-bijective-reasoning-code-packet-v1"
TONGUES: tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_obj(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256_text(canonical)


def _language_to_tongue(language: str) -> tuple[str, str | None]:
    lang = (language or "").strip().lower()
    for tongue, mapped in ALL_LANG_MAP.items():
        if mapped == lang:
            return tongue, TONGUE_PARENT.get(tongue)
    return "KO", None


def _transport_tongue(tongue: str) -> str:
    return tongue.strip().lower()


def _transport_channel(text: str, tongue: str) -> dict[str, Any]:
    raw = text.encode("utf-8", errors="replace")
    transport = _transport_tongue(tongue)
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(transport, raw)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(transport, tokens).decode("utf-8", errors="replace")
    joined = " ".join(tokens)
    return {
        "tongue": tongue,
        "byte_count": len(raw),
        "token_count": len(tokens),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "token_sha256": _sha256_text(joined),
        "roundtrip_ok": decoded == text,
        "tokens_preview": tokens[:16],
    }


def _tile_key(row: int, col: int) -> str:
    return f"tile:{row}:{col}"


def _lang_at_tile(row: int, col: int) -> str:
    n = len(TONGUES)
    return TONGUES[(row % n + col % n) % n]


def _tile_for_text(text: str) -> tuple[int, int]:
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
    return digest[0] % 64, digest[1] % 64


def _voxel6(row: int, col: int, layer: int = 0) -> list[int]:
    return [row, col, layer, 0, 0, 0]


def _operation_name(text: str, fallback: str) -> str:
    for pattern in (
        r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bint\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    words = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", fallback.lower())
    return "_".join(words[:5]) or "operation"


def _operation_signature(*, intent: str, source: str, route: dict[str, Any], quarks: list[str]) -> str:
    name = _operation_name(source, intent)
    material = {
        "intent_sha256": _sha256_text(intent),
        "source_sha256": _sha256_text(source),
        "route": route,
        "quarks": quarks,
        "operation": name,
    }
    return f"{name}:{_sha256_obj(material)[:16]}"


def _language_views(*, source: str, language: str, route_language: str) -> dict[str, Any]:
    views: dict[str, Any] = {}
    for lang in sorted(set(ALL_LANG_MAP.values())):
        if source and lang == language:
            views[lang] = {"status": "source", "content": source}
        elif lang == route_language.lower():
            views[lang] = {"status": "target", "content": source if lang == language else ""}
        else:
            views[lang] = {"status": "not_materialized", "content": ""}
    return views


def _merge_geometry(contact_points: list[dict[str, Any]], *, roundtrip_ok: bool) -> dict[str, Any]:
    hard = sum(1 for point in contact_points if point.get("kind") == "hard" and point.get("ok"))
    near = sum(1 for point in contact_points if point.get("kind") == "near" and point.get("ok"))
    return {
        "rule": "one_hard_contact_and_two_near_contacts",
        "hard_contact_count": hard,
        "near_contact_count": near,
        "promote_ready": bool(roundtrip_ok and hard >= 1 and near >= 2),
    }


def build_bijective_reasoning_code_packet(
    *,
    intent: str,
    source: str = "",
    language: str = "python",
    source_name: str = "inline",
    tile_row: int | None = None,
    tile_col: int | None = None,
    permission_mode: str = "observe",
) -> dict[str, Any]:
    """Build a first-class reasoning/code packet.

    ``source`` may be empty. In that case the packet represents pre-code
    routing: the semantic basis is the intent and code views remain pending.
    """

    clean_intent = " ".join((intent or "").split())
    clean_source = source or ""
    if not clean_intent and not clean_source:
        raise ValueError("intent or source is required")

    requested_language = (language or "python").strip().lower()
    forced_tongue, parent_tongue = _language_to_tongue(requested_language)
    route = route_prompt(clean_intent or clean_source, force_tongue=forced_tongue)
    route_language = (ALL_LANG_MAP.get(route.tongue) or LANG_MAP.get(route.tongue) or route.language).lower()

    semantic_basis = clean_source if clean_source else clean_intent
    code_weight = build_code_weight_packet(
        semantic_basis,
        language=requested_language if clean_source else route_language,
        source_name=source_name,
    )
    quarks = list(code_weight.get("semantic_expression", {}).get("quarks") or ["semantic_operation"])

    if tile_row is None or tile_col is None:
        tile_row, tile_col = _tile_for_text(clean_intent or semantic_basis)
    tile_lang = _lang_at_tile(tile_row, tile_col)

    route_packet = {
        "tongue": route.tongue,
        "language": route_language,
        "requested_language": requested_language,
        "parent_tongue": parent_tongue,
        "source": route.source,
        "reason": route.reason,
        "confidence": route.confidence,
        "tile": _tile_key(tile_row, tile_col),
        "tile_tongue": tile_lang,
        "voxel6": _voxel6(tile_row, tile_col),
    }
    operation_signature = _operation_signature(
        intent=clean_intent,
        source=clean_source,
        route=route_packet,
        quarks=quarks,
    )
    transport = {
        "intent": _transport_channel(clean_intent, route.tongue),
        "semantic_basis": _transport_channel(semantic_basis, route.tongue),
        "code": _transport_channel(clean_source, route.tongue) if clean_source else None,
    }
    contact_points = [
        {"kind": "hard", "name": "transport_roundtrip", "ok": True},
        {"kind": "near", "name": "deterministic_route", "ok": route.confidence >= 0.5},
        {"kind": "near", "name": "stisa_semantic_rows", "ok": bool((code_weight.get("stisa") or {}).get("token_rows"))},
    ]
    roundtrip_ok = all(channel is None or bool(channel.get("roundtrip_ok")) for channel in transport.values())
    packet_core = {
        "schema_version": SCHEMA_VERSION,
        "intent": {
            "plain": clean_intent,
            "domain": "coding",
            "operation": _operation_name(clean_source, clean_intent),
            "source_state": "source_code" if clean_source else "precode_intent",
        },
        "route": route_packet,
        "semantic_ir": {
            "quarks": quarks,
            "operation_signature": operation_signature,
            "code_weight_packet_version": code_weight.get("schema_version"),
            "lexical_token_count": len(code_weight.get("lexical_tokens") or []),
            "stisa_row_count": len((code_weight.get("stisa") or {}).get("token_rows") or []),
        },
        "code_views": _language_views(source=clean_source, language=requested_language, route_language=route_language),
        "transport": transport,
        "reconstruction": {
            "roundtrip_ok": roundtrip_ok,
            "language_matches_tongue": route.tongue == forced_tongue,
            "known_losses": [] if clean_source else ["code_view_not_materialized"],
        },
        "compact_agent_packet": {
            "phase": "precode" if not clean_source else "packetize",
            "route": {
                "tongue": route.tongue,
                "language": route_language,
                "tile": _tile_key(tile_row, tile_col),
            },
            "state_hash": _sha256_text("|".join([clean_intent, clean_source, route.tongue, route_language])),
            "budget": {"max_input_tokens": 900, "max_output_tokens": 300},
            "expected_output": "delta|vote|patch|verdict",
        },
        "permission": {
            "mode": permission_mode,
            "execution_allowed": permission_mode in {"workspace-write", "maintenance"},
            "tokenizer_is_security_boundary": False,
        },
        "verification": {
            "compile": None,
            "tests": [],
            "contact_points": contact_points,
        },
        "merge_geometry": _merge_geometry(contact_points, roundtrip_ok=roundtrip_ok),
        "training_hooks": {
            "use_as": [
                "precode_route_record",
                "bijective_reasoning_code_packet",
                "compact_agent_packet_trace",
            ],
            "compact_trace_fields": [
                "schema_version",
                "intent.source_state",
                "route",
                "semantic_ir.operation_signature",
                "compact_agent_packet",
                "merge_geometry",
            ],
            "promotion_gate": "roundtrip_ok and merge_geometry.promote_ready",
        },
    }
    packet_hash = _sha256_obj(packet_core)
    packet_core["identity"] = {
        "packet_id": f"brc1-{packet_hash[:16]}",
        "source_name": source_name,
        "packet_sha256": packet_hash,
    }
    return packet_core


__all__ = ["SCHEMA_VERSION", "build_bijective_reasoning_code_packet"]
