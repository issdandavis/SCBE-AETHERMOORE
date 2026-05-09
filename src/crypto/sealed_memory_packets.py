"""Sealed memory packets built on Sacred Tongues transport and RWP v3.

This module does not make Sacred Tongues a security boundary by itself. The
tokenizer supplies exact byte-for-token reversibility; RWP v3 supplies the
authenticated encryption boundary.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Optional, Union

from .rwp_v3 import RWPEnvelope, RWPv3Protocol, get_rwp_pqc_governance_status
from .sacred_tongues import SACRED_TONGUE_TOKENIZER

SCHEMA_VERSION = "scbe.sealed_memory_packet.v1"
DEFAULT_TONGUE = "ca"

BytesLike = Union[bytes, bytearray, memoryview]
Payload = Union[str, BytesLike]
Secret = Union[str, BytesLike]


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _coerce_secret(secret: Secret) -> bytes:
    if isinstance(secret, str):
        value = secret.encode("utf-8")
    elif isinstance(secret, (bytes, bytearray, memoryview)):
        value = bytes(secret)
    else:
        raise TypeError("secret must be str or bytes-like")
    if not value:
        raise ValueError("secret must not be empty")
    return value


def _coerce_payload(payload: Payload) -> bytes:
    if isinstance(payload, str):
        return payload.encode("utf-8")
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return bytes(payload)
    raise TypeError("payload must be str or bytes-like")


def _normalize_metadata(metadata: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    normalized = dict(metadata)
    _canonical_json_bytes(normalized)
    return normalized


def _token_hash(tokens: List[str]) -> str:
    return _sha256_hex(_canonical_json_bytes(tokens))


def _metadata_hash(metadata: Mapping[str, Any]) -> str:
    return _sha256_hex(_canonical_json_bytes(metadata))


def _build_aad(packet_fields: Mapping[str, Any], metadata: Mapping[str, Any]) -> bytes:
    aad = {
        "schema_version": packet_fields["schema_version"],
        "kind": packet_fields["kind"],
        "label": packet_fields["label"],
        "tongue": packet_fields["tongue"],
        "token_count": packet_fields["token_count"],
        "source_sha256": packet_fields["source_sha256"],
        "token_sha256": packet_fields["token_sha256"],
        "metadata_sha256": _metadata_hash(metadata),
    }
    return _canonical_json_bytes(aad)


def seal_memory_packet(
    secret: Secret,
    payload: Payload,
    *,
    tongue: str = DEFAULT_TONGUE,
    label: str = "memory",
    metadata: Optional[Mapping[str, Any]] = None,
    enable_pqc: bool = False,
) -> Dict[str, Any]:
    """Encode payload into a bijective tongue stream, then seal it with RWP v3.

    The returned dict is JSON-serializable. The plaintext Sacred Tongue tokens
    are encrypted inside the RWP envelope; only hashes and routing metadata stay
    outside for audit and lookup.
    """

    if tongue not in SACRED_TONGUE_TOKENIZER.tongues:
        raise ValueError(f"unknown Sacred Tongue code: {tongue}")
    if not label:
        raise ValueError("label must not be empty")

    secret_bytes = _coerce_secret(secret)
    payload_bytes = _coerce_payload(payload)
    normalized_metadata = _normalize_metadata(metadata)

    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, payload_bytes)
    token_document = {"tongue": tongue, "tokens": tokens}
    token_document_bytes = _canonical_json_bytes(token_document)

    packet_fields: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "sealed_memory_packet",
        "label": label,
        "tongue": tongue,
        "token_count": len(tokens),
        "source_sha256": _sha256_hex(payload_bytes),
        "token_sha256": _token_hash(tokens),
    }
    aad = _build_aad(packet_fields, normalized_metadata)

    protocol = RWPv3Protocol(enable_pqc=enable_pqc)
    envelope = protocol.encrypt(
        password=secret_bytes,
        plaintext=token_document_bytes,
        aad=aad,
    )

    return {
        **packet_fields,
        "metadata": normalized_metadata,
        "envelope": envelope.to_dict(),
        "crypto_governance": get_rwp_pqc_governance_status(),
    }


def unseal_memory_packet(
    secret: Secret,
    packet: Mapping[str, Any],
    *,
    enable_pqc: bool = False,
) -> Dict[str, Any]:
    """Open a sealed memory packet and verify transport and payload hashes."""

    secret_bytes = _coerce_secret(secret)
    normalized_metadata = _normalize_metadata(packet.get("metadata", {}))

    packet_fields = {
        "schema_version": packet.get("schema_version"),
        "kind": packet.get("kind"),
        "label": packet.get("label"),
        "tongue": packet.get("tongue"),
        "token_count": packet.get("token_count"),
        "source_sha256": packet.get("source_sha256"),
        "token_sha256": packet.get("token_sha256"),
    }
    if packet_fields["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported sealed memory packet schema")
    if packet_fields["kind"] != "sealed_memory_packet":
        raise ValueError("unsupported sealed memory packet kind")
    if packet_fields["tongue"] not in SACRED_TONGUE_TOKENIZER.tongues:
        raise ValueError(f"unknown Sacred Tongue code: {packet_fields['tongue']}")
    if (
        not isinstance(packet_fields["token_count"], int)
        or packet_fields["token_count"] < 0
    ):
        raise ValueError("invalid token_count")

    aad = _build_aad(packet_fields, normalized_metadata)
    protocol = RWPv3Protocol(enable_pqc=enable_pqc)
    try:
        envelope = RWPEnvelope.from_dict(packet["envelope"])
    except Exception as exc:
        raise ValueError("invalid RWP envelope") from exc

    sealed_aad = SACRED_TONGUE_TOKENIZER.decode_section("aad", envelope.aad)
    if sealed_aad != aad:
        raise ValueError("sealed packet AAD mismatch")

    token_document_bytes = protocol.decrypt(secret_bytes, envelope)
    try:
        token_document = json.loads(token_document_bytes.decode("utf-8"))
    except Exception as exc:
        raise ValueError("sealed token document is not valid JSON") from exc

    if token_document.get("tongue") != packet_fields["tongue"]:
        raise ValueError("sealed token tongue does not match packet tongue")
    tokens = token_document.get("tokens")
    if not isinstance(tokens, list) or not all(
        isinstance(token, str) for token in tokens
    ):
        raise ValueError("sealed token document has invalid token list")
    if len(tokens) != packet_fields["token_count"]:
        raise ValueError("sealed token count mismatch")
    if _token_hash(tokens) != packet_fields["token_sha256"]:
        raise ValueError("sealed token hash mismatch")

    payload_bytes = SACRED_TONGUE_TOKENIZER.decode_tokens(
        packet_fields["tongue"], tokens
    )
    if _sha256_hex(payload_bytes) != packet_fields["source_sha256"]:
        raise ValueError("sealed payload hash mismatch")

    try:
        text = payload_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = None

    return {
        "payload": payload_bytes,
        "text": text,
        "tokens": tokens,
        "metadata": normalized_metadata,
        "label": packet_fields["label"],
        "tongue": packet_fields["tongue"],
        "source_sha256": packet_fields["source_sha256"],
        "token_sha256": packet_fields["token_sha256"],
        "roundtrip_ok": True,
    }


def verify_memory_packet(
    secret: Secret, packet: Mapping[str, Any], *, enable_pqc: bool = False
) -> bool:
    """Return True only if the sealed packet opens and all hashes verify."""

    try:
        unseal_memory_packet(secret, packet, enable_pqc=enable_pqc)
    except Exception:
        return False
    return True
