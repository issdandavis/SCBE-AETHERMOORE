"""Sealed compact handoff packets for agent-to-agent work transfer.

This layer sits above AgentPacketV1. It is built for small-context handoffs:
send enough public metadata for routing and audit, keep the task core compact,
and seal the task body with an agreed decode recipe.

The stdlib stream seal here is deterministic and testable, but it is not a
substitute for audited AES-GCM/ChaCha20-Poly1305 in hostile networks. Its job in
this repo is to enforce the process shape: derive per packet, authenticate,
decode by agreement, discard the derived material.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import zlib
from dataclasses import asdict, dataclass
from typing import Any

from .packet import AgentPacketV1, enforce_budget

SCHEMA = "agent_secure_handoff_v1"
DECODE_METHOD = "canonical-json.zlib.hmac-sha256-xorstream-v1"
KDF_METHOD = "hkdf-sha256-route-bound-v1"
KEY_LIFECYCLE = "derive-use-discard"
CANONICAL_SEPARATORS = (",", ":")


class HandoffIntegrityError(ValueError):
    """Raised when a sealed handoff cannot be authenticated or decoded."""


def _canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=CANONICAL_SEPARATORS, ensure_ascii=False).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    padding = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, length: int) -> bytes:
    output = b""
    previous = b""
    counter = 1
    while len(output) < length:
        previous = hmac.new(prk, previous + info + bytes([counter]), hashlib.sha256).digest()
        output += previous
        counter += 1
    return output[:length]


def _derive_keys(shared_secret: str | bytes, *, salt: bytes, info: bytes) -> tuple[bytes, bytes]:
    secret_bytes = shared_secret.encode("utf-8") if isinstance(shared_secret, str) else shared_secret
    if not secret_bytes:
        raise ValueError("shared_secret must be non-empty")
    prk = _hkdf_extract(salt, secret_bytes)
    material = _hkdf_expand(prk, info, 64)
    return material[:32], material[32:]


def _xor_stream(data: bytes, key: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < len(data):
        block = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(a ^ b for a, b in zip(data, out[: len(data)]))


@dataclass(frozen=True)
class DecodeAgreement:
    """Public recipe the receiving agent must use to open the handoff."""

    method: str = DECODE_METHOD
    kdf: str = KDF_METHOD
    compression: str = "zlib"
    canonical: str = "json.sorted.minified"
    route_bound: bool = True
    key_lifecycle: str = KEY_LIFECYCLE

    def validate(self) -> None:
        if self.method != DECODE_METHOD:
            raise ValueError(f"unsupported decode method: {self.method}")
        if self.kdf != KDF_METHOD:
            raise ValueError(f"unsupported kdf: {self.kdf}")
        if self.compression != "zlib":
            raise ValueError(f"unsupported compression: {self.compression}")
        if self.key_lifecycle != KEY_LIFECYCLE:
            raise ValueError(f"unsupported key lifecycle: {self.key_lifecycle}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecodeAgreement":
        agreement = cls(**data)
        agreement.validate()
        return agreement


def semantic_shadow(packet: AgentPacketV1) -> dict[str, Any]:
    """Public metadata that says useful things about the body without revealing it."""

    body = packet.to_dict()
    canonical = _canonical_bytes(body)
    refs = [ref.to_dict() if hasattr(ref, "to_dict") else asdict(ref) for ref in packet.context_refs]
    return {
        "schema": "agent_handoff_shadow_v1",
        "task_id": packet.task_id,
        "phase": packet.phase,
        "route": asdict(packet.route),
        "expected_output": packet.expected_output,
        "context_ref_count": len(packet.context_refs),
        "context_ref_kinds": sorted({ref.kind for ref in packet.context_refs}),
        "body_commitment": f"sha256:{hashlib.sha256(canonical).hexdigest()}",
        "field_commitments": {
            key: f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()[:24]}"
            for key, value in sorted(body.items())
            if key not in {"request", "context_refs"}
        },
        "context_refs_commitment": f"sha256:{hashlib.sha256(_canonical_bytes(refs)).hexdigest()}",
        "request_bytes": len(packet.request.encode("utf-8")),
        "public_hint": "shadow metadata only; sealed body is required for request/context details",
    }


def _route_info(sender_id: str, recipient_id: str, packet: AgentPacketV1, body_commitment: str) -> bytes:
    public = {
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "task_id": packet.task_id,
        "phase": packet.phase,
        "route": asdict(packet.route),
        "state_hash": body_commitment,
        "expected_output": packet.expected_output,
    }
    return _canonical_bytes(public)


def seal_handoff(
    packet: AgentPacketV1,
    *,
    sender_id: str,
    recipient_id: str,
    shared_secret: str | bytes,
    nonce: bytes | None = None,
    created_at: float | None = None,
) -> dict[str, Any]:
    """Build a compact sealed handoff packet from an AgentPacketV1."""

    packet.validate()
    enforce_budget(packet)
    agreement = DecodeAgreement()
    agreement.validate()
    salt = nonce or secrets.token_bytes(16)
    public_shadow = semantic_shadow(packet)
    route_info = _route_info(sender_id, recipient_id, packet, public_shadow["body_commitment"])
    seal_key, auth_key = _derive_keys(shared_secret, salt=salt, info=route_info + _canonical_bytes(agreement.to_dict()))
    plaintext = _canonical_bytes(packet.to_dict())
    compressed = zlib.compress(plaintext, level=9)
    ciphertext = _xor_stream(compressed, seal_key)
    protected = {
        "schema": SCHEMA,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "decode_agreement": agreement.to_dict(),
        "nonce": _b64(salt),
        "shadow": public_shadow,
        "ciphertext": _b64(ciphertext),
        "created_at": created_at if created_at is not None else time.time(),
    }
    tag = hmac.new(auth_key, _canonical_bytes(protected), hashlib.sha256).digest()
    sealed = {
        **protected,
        "auth_tag": f"hmac-sha256:{_b64(tag)}",
        "compactness": compactness_report(packet, sealed_bytes_hint=len(_canonical_bytes(protected)) + len(tag)),
    }
    return sealed


def open_handoff(sealed: dict[str, Any], *, shared_secret: str | bytes) -> AgentPacketV1:
    """Authenticate and decode a sealed handoff packet."""

    if sealed.get("schema") != SCHEMA:
        raise HandoffIntegrityError(f"expected schema {SCHEMA}, got {sealed.get('schema')!r}")
    agreement = DecodeAgreement.from_dict(sealed["decode_agreement"])
    salt = _unb64(sealed["nonce"])
    shadow = sealed["shadow"]
    route_info = _canonical_bytes(
        {
            "sender_id": sealed["sender_id"],
            "recipient_id": sealed["recipient_id"],
            "task_id": shadow["task_id"],
            "phase": shadow["phase"],
            "route": shadow["route"],
            "state_hash": shadow["body_commitment"],
            "expected_output": shadow["expected_output"],
        }
    )
    seal_key, auth_key = _derive_keys(shared_secret, salt=salt, info=route_info + _canonical_bytes(agreement.to_dict()))
    protected = {key: value for key, value in sealed.items() if key not in {"auth_tag", "compactness"}}
    expected = hmac.new(auth_key, _canonical_bytes(protected), hashlib.sha256).digest()
    raw_tag = str(sealed.get("auth_tag", ""))
    if not raw_tag.startswith("hmac-sha256:"):
        raise HandoffIntegrityError("missing hmac-sha256 auth_tag")
    actual = _unb64(raw_tag.split(":", 1)[1])
    if not hmac.compare_digest(expected, actual):
        raise HandoffIntegrityError("handoff authentication failed")
    try:
        compressed = _xor_stream(_unb64(sealed["ciphertext"]), seal_key)
        plaintext = zlib.decompress(compressed)
        data = json.loads(plaintext.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive normalization
        raise HandoffIntegrityError(f"handoff decode failed: {exc}") from exc
    packet = AgentPacketV1.from_dict(data)
    packet.validate()
    if semantic_shadow(packet)["body_commitment"] != shadow["body_commitment"]:
        raise HandoffIntegrityError("body commitment mismatch")
    return packet


def compactness_report(packet: AgentPacketV1, *, sealed_bytes_hint: int | None = None) -> dict[str, Any]:
    """Compare sealed handoff size with a naive prose handoff."""

    raw_packet = _canonical_bytes(packet.to_dict())
    referenced_context_bytes = sum(ref.bytes or 0 for ref in packet.context_refs)
    naive = {
        "task": packet.request,
        "state_hash": packet.state_hash,
        "context_refs": [asdict(ref) for ref in packet.context_refs],
        "route": asdict(packet.route),
        "budget": asdict(packet.budget),
        "expected_output": packet.expected_output,
    }
    naive_bytes = len(_canonical_bytes(naive))
    sealed_bytes = sealed_bytes_hint if sealed_bytes_hint is not None else len(raw_packet)
    return {
        "canonical_packet_bytes": len(raw_packet),
        "naive_handoff_bytes": naive_bytes,
        "referenced_context_bytes": referenced_context_bytes,
        "naive_with_context_bytes": naive_bytes + referenced_context_bytes,
        "sealed_envelope_bytes": sealed_bytes,
        "saves_space_vs_naive": sealed_bytes < naive_bytes,
        "saves_space_vs_naive_with_context": sealed_bytes < naive_bytes + referenced_context_bytes,
        "notes": [
            "Space savings come from referenced context and compressed sealed body, not from hiding required work.",
            "Shadow metadata improves auditability while omitting request and context-ref values.",
        ],
    }


__all__ = [
    "SCHEMA",
    "DECODE_METHOD",
    "KDF_METHOD",
    "KEY_LIFECYCLE",
    "DecodeAgreement",
    "HandoffIntegrityError",
    "semantic_shadow",
    "seal_handoff",
    "open_handoff",
    "compactness_report",
]
