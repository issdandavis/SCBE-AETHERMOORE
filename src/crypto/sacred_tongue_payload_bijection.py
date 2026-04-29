"""Canonical JSON → bytes → Sacred Tongue tokens → bytes bijection for build artifacts.

Used to prove a structured harness payload survives lossless encoding in every
SS1 tongue (ko, av, ru, ca, um, dr) before trusting cross-language tool lanes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from src.crypto.sacred_tongues import TONGUES, SacredTongueTokenizer

SCHEMA_VERSION = "scbe_sacred_tongue_payload_bijection_v1"

# Stable, diff-friendly serialization (no incidental whitespace).
CANONICAL_SEPARATORS = (",", ":")


def canonical_json_bytes(obj: Any) -> bytes:
    """UTF-8 JSON with sorted keys and minimal separators."""
    return json.dumps(
        obj, sort_keys=True, separators=CANONICAL_SEPARATORS, ensure_ascii=False
    ).encode("utf-8")


def prove_bytes_all_tongues(
    data: bytes, tokenizer: SacredTongueTokenizer | None = None
) -> dict[str, Any]:
    """Round-trip `data` through each tongue's byte bijection."""
    tok = tokenizer or SacredTongueTokenizer()
    per: dict[str, Any] = {}
    all_ok = True
    for code in TONGUES:
        tokens = tok.encode_bytes(code, data)
        back = tok.decode_tokens(code, tokens)
        ok = back == data
        if not ok:
            all_ok = False
        per[code] = {
            "ok": ok,
            "byte_length": len(data),
            "token_count": len(tokens),
            "first_token": tokens[0] if tokens else "",
            "last_token": tokens[-1] if tokens else "",
        }
    return {
        "tongues": per,
        "all_ok": all_ok,
        "tongue_order": list(TONGUES.keys()),
    }


def prove_dict(obj: dict[str, Any]) -> dict[str, Any]:
    """Full proof record for a JSON object (typically a build/eval payload)."""
    data = canonical_json_bytes(obj)
    digest = hashlib.sha256(data).hexdigest()
    body = prove_bytes_all_tongues(data)
    return {
        "schema_version": SCHEMA_VERSION,
        "canonical_sha256": digest,
        "canonical_byte_length": len(data),
        "ok": body["all_ok"],
        "tongues": body["tongues"],
        "tongue_order": body["tongue_order"],
    }
