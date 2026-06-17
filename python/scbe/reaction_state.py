"""Shared SCBE reaction-state packet model.

Reaction-state packets are the common substrate for cross-language code
translation, chemistry decomposition/recomposition, tokenizer routing, and
future agent workflows. They track what moved, what changed, what was lost,
what was recalculated, and whether the transform is bijective under the
declared representation.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Literal

ReactionClassification = Literal["BIJECTIVE", "LOSSY_RECOVERABLE", "LOSSY_AMBIGUOUS", "INVALID"]
ReactionDomain = Literal["code", "chem", "audio", "agent", "data", "geometry", "mixed"]

TONGUE_COLUMNS = {
    "KO": "identity",
    "AV": "features",
    "RU": "operation",
    "CA": "constraints",
    "UM": "uncertainty_loss",
    "DR": "resolution",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def unit_check(computation: Any) -> tuple[bool, tuple[str, ...]]:
    """Honest source for ``ReactionRecalculation.unit_checks_ok``.

    ``computation`` is a zero-arg thunk that performs ``python.scbe.units``
    Quantity arithmetic; it raises on any dimensional/unit inconsistency
    (including the Mars-Climate-Orbiter same-dimension/different-unit class).
    Returns ``(ok, problems)``. The ``units`` engine is imported lazily so this
    shared substrate stays stdlib-only at import time.
    """
    from .units import check

    return check(computation)


def packet_from_dict(data: dict[str, Any]) -> "ReactionStatePacket":
    """Rehydrate a reaction packet from JSON-compatible data."""

    source = ReactionEndpoint(**data["source"])
    target = ReactionEndpoint(**data["target"])
    recalculation = ReactionRecalculation(**data["recalculation"])
    return ReactionStatePacket(
        schema_version=data["schema_version"],
        generated_at_utc=data["generated_at_utc"],
        domain=data["domain"],
        step=int(data["step"]),
        bounded_operation=data["bounded_operation"],
        source=source,
        target=target,
        semantic_engravings=list(data.get("semantic_engravings") or []),
        loss_notes=list(data.get("loss_notes") or []),
        recalculation=recalculation,
        classification=data["classification"],
        tongue_columns=dict(data.get("tongue_columns") or TONGUE_COLUMNS),
        claim_boundary=list(data.get("claim_boundary") or []),
        previous_packet_hash=data.get("previous_packet_hash"),
        packet_hash=data.get("packet_hash"),
        signature=data.get("signature"),
        signature_alg=data.get("signature_alg"),
        signer_public_key=data.get("signer_public_key"),
    )


@dataclass(frozen=True, slots=True)
class ReactionEndpoint:
    """One side of a reaction-state transform."""

    identity: str
    representation: str
    language: str | None = None
    tongue: str | None = None
    payload_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReactionRecalculation:
    """Checks rerun after a transform."""

    syntax_ok: bool | None = None
    tests_ok: bool | None = None
    scientific_checks_ok: bool | None = None
    unit_checks_ok: bool | None = None
    identity_ok: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def has_failure(self) -> bool:
        return any(
            value is False
            for value in (
                self.syntax_ok,
                self.tests_ok,
                self.scientific_checks_ok,
                self.unit_checks_ok,
                self.identity_ok,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReactionStatePacket:
    """Portable packet for bounded transforms with loss accounting."""

    schema_version: str
    generated_at_utc: str
    domain: ReactionDomain
    step: int
    bounded_operation: str
    source: ReactionEndpoint
    target: ReactionEndpoint
    semantic_engravings: list[str]
    loss_notes: list[str]
    recalculation: ReactionRecalculation
    classification: ReactionClassification
    tongue_columns: dict[str, str] = field(default_factory=lambda: dict(TONGUE_COLUMNS))
    claim_boundary: list[str] = field(default_factory=list)
    previous_packet_hash: str | None = None
    packet_hash: str | None = None
    signature: str | None = None
    signature_alg: str | None = None
    signer_public_key: str | None = None

    def unsigned_dict(self) -> dict[str, Any]:
        """Content for the integrity hash: drops the hash and signature fields so
        signing a packet never invalidates its content hash (and old, unsigned
        packets hash identically)."""
        data = asdict(self)
        for key in ("packet_hash", "signature", "signature_alg", "signer_public_key"):
            data.pop(key, None)
        return data

    def _signable_payload(self) -> dict[str, Any]:
        """Payload the signature is computed over: everything except the signature
        fields themselves. Includes ``packet_hash`` so the signature binds the hash
        (and therefore the previous_packet_hash chain link)."""
        data = asdict(self)
        for key in ("signature", "signature_alg", "signer_public_key"):
            data.pop(key, None)
        return data

    def compute_hash(self) -> str:
        return sha256_value(self.unsigned_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_hash(self) -> "ReactionStatePacket":
        return replace(self, packet_hash=self.compute_hash())

    def verify_hash(self) -> bool:
        return bool(self.packet_hash) and self.compute_hash() == self.packet_hash

    def sign(self, agent_id: str = "scbe-reaction-state") -> "ReactionStatePacket":
        """Attach a real signature using the agent-bus EventSigner (ML-DSA-65 PQC,
        Ed25519, or HMAC-SHA512 fallback). Never raises: if no signer is available
        the packet is returned unchanged (signature stays None)."""
        try:
            from agents.agent_bus_signing import EventSigner
        except Exception:  # pragma: no cover - signer module unavailable
            return self
        signer = EventSigner(agent_id)
        try:
            if not signer.initialize():
                return self
            sig_b64, pk_b64, alg = signer.sign(self._signable_payload())
        except Exception:  # pragma: no cover - defensive: signing must not break a flow
            return self
        if not sig_b64:
            return self
        return replace(self, signature=sig_b64, signature_alg=alg, signer_public_key=pk_b64)

    def verify_signature(self) -> bool | None:
        """Public-key verify the signature. Returns True/False for asymmetric
        signatures (ML-DSA-65, Ed25519), and None when the packet is unsigned or
        carries only a symmetric (HMAC) signature that cannot be publicly verified."""
        if not self.signature or self.signature_alg in (None, "unsigned", "HMAC-SHA512-sim"):
            return None
        try:
            from agents.agent_bus_signing import EventSigner
        except Exception:  # pragma: no cover
            return None
        return bool(
            EventSigner.verify(
                self._signable_payload(),
                self.signature,
                self.signer_public_key or "",
                self.signature_alg,
            )
        )


def classify_reaction(
    *,
    recalculation: ReactionRecalculation,
    identity_preserved: bool,
    loss_notes: list[str] | tuple[str, ...] = (),
    recovery_evidence: list[str] | tuple[str, ...] = (),
) -> ReactionClassification:
    if recalculation.has_failure or identity_preserved is False and not recovery_evidence:
        return "INVALID" if recalculation.has_failure else "LOSSY_AMBIGUOUS"
    if not loss_notes and identity_preserved:
        return "BIJECTIVE"
    if identity_preserved and recovery_evidence:
        return "LOSSY_RECOVERABLE"
    return "LOSSY_AMBIGUOUS"


def build_reaction_state_packet(
    *,
    domain: ReactionDomain,
    step: int,
    bounded_operation: str,
    source: ReactionEndpoint,
    target: ReactionEndpoint,
    semantic_engravings: list[str] | tuple[str, ...],
    loss_notes: list[str] | tuple[str, ...],
    recalculation: ReactionRecalculation,
    identity_preserved: bool,
    recovery_evidence: list[str] | tuple[str, ...] = (),
    claim_boundary: list[str] | tuple[str, ...] = (),
    previous_packet_hash: str | None = None,
    generated_at_utc: str | None = None,
) -> ReactionStatePacket:
    classification = classify_reaction(
        recalculation=recalculation,
        identity_preserved=identity_preserved,
        loss_notes=loss_notes,
        recovery_evidence=recovery_evidence,
    )
    packet = ReactionStatePacket(
        schema_version="scbe_reaction_state_packet_v1",
        generated_at_utc=generated_at_utc or utc_now(),
        domain=domain,
        step=step,
        bounded_operation=bounded_operation,
        source=source,
        target=target,
        semantic_engravings=list(semantic_engravings),
        loss_notes=list(loss_notes),
        recalculation=recalculation,
        classification=classification,
        claim_boundary=list(claim_boundary),
        previous_packet_hash=previous_packet_hash,
    )
    return packet.with_hash()


class ReactionLedger:
    """An append-only chain of reaction-state packets.

    Each appended packet's ``previous_packet_hash`` is anchored to the prior
    packet's ``packet_hash`` (so the chain is hash-linked) and, when a signer is
    available, the packet is signed (so the chain is tamper-proof, not just
    tamper-evident). ``verify()`` re-checks every hash, every link, and every
    asymmetric signature.
    """

    def __init__(self, agent_id: str = "scbe-reaction-state", sign: bool = True) -> None:
        self.agent_id = agent_id
        self.sign = sign
        self.packets: list[ReactionStatePacket] = []
        self._last_hash: str | None = None

    def append(self, **build_kwargs: Any) -> ReactionStatePacket:
        build_kwargs.setdefault("previous_packet_hash", self._last_hash)
        return self._anchor(build_reaction_state_packet(**build_kwargs))

    def append_packet(self, packet: ReactionStatePacket) -> ReactionStatePacket:
        """Chain an already-built packet (e.g. from ``balance_reaction_packet`` or
        ``geometry_view_packet``): re-anchor its ``previous_packet_hash`` to the
        prior packet, recompute the content hash, and sign. Lets domain builders
        stay single-purpose while the ledger owns chaining + signing."""
        return self._anchor(replace(packet, previous_packet_hash=self._last_hash))

    def _anchor(self, packet: ReactionStatePacket) -> ReactionStatePacket:
        packet = packet.with_hash()
        if self.sign:
            packet = packet.sign(self.agent_id)
        self.packets.append(packet)
        self._last_hash = packet.packet_hash
        return packet

    def verify(self) -> bool:
        prev: str | None = None
        for packet in self.packets:
            if not packet.verify_hash():
                return False
            if packet.previous_packet_hash != prev:
                return False
            if packet.verify_signature() is False:  # None (unsigned/symmetric) is allowed
                return False
            prev = packet.packet_hash
        return True

    def merkle_root(self) -> str:
        return merkle_tree_head([p.packet_hash or "" for p in self.packets])

    def inclusion_proof(self, index: int) -> dict[str, Any]:
        """Compact proof that packet ``index`` is committed by the current root —
        verifiable with ``verify_merkle_inclusion`` and nothing else."""
        hashes = [p.packet_hash or "" for p in self.packets]
        return {
            "schema_version": "scbe_merkle_inclusion_proof_v1",
            "packet_hash": hashes[index],
            "leaf_index": index,
            "tree_size": len(hashes),
            "audit_path": merkle_audit_path(hashes, index),
            "merkle_root": merkle_tree_head(hashes),
        }

    def checkpoint(self) -> dict[str, Any]:
        """Signed commitment to the exact set and count of packets so far.

        The linear chain proves order; the checkpoint adds omission-resistance
        (a dropped or truncated packet changes the root and the tree_size).
        Signed with the same EventSigner identity as the packets; unsigned
        (signature None) when no signer backend is available — never raises.
        """
        unsigned: dict[str, Any] = {
            "schema_version": "scbe_reaction_ledger_checkpoint_v1",
            "generated_at_utc": utc_now(),
            "agent_id": self.agent_id,
            "tree_size": len(self.packets),
            "merkle_root": self.merkle_root(),
            "first_packet_hash": self.packets[0].packet_hash if self.packets else None,
            "last_packet_hash": self._last_hash,
            "chain_verified": self.verify(),
        }
        signed = dict(unsigned)
        signed.update({"signature": None, "signature_alg": None, "signer_public_key": None})
        if not self.sign:
            return signed
        try:
            from agents.agent_bus_signing import EventSigner

            signer = EventSigner(self.agent_id)
            if signer.initialize():
                sig_b64, pk_b64, alg = signer.sign(unsigned)
                if sig_b64:
                    signed.update({"signature": sig_b64, "signature_alg": alg, "signer_public_key": pk_b64})
        except Exception:  # pragma: no cover - checkpointing must not break a flow
            pass
        return signed

    def acta_chain(self, issuer_id: str | None = None) -> list[dict[str, Any]]:
        """Export the ledger as an ACTA-compatible receipt chain (one signed
        envelope per packet, linked by previousReceiptHash per the draft)."""
        receipts: list[dict[str, Any]] = []
        prev: str | None = None
        for packet in self.packets:
            receipt = packet_to_acta_receipt(packet, issuer_id or self.agent_id, prev)
            receipts.append(receipt)
            prev = acta_receipt_hash(receipt)
        return receipts


def verify_checkpoint(checkpoint: dict[str, Any]) -> bool | None:
    """Public-key verify a ledger checkpoint. True/False for asymmetric
    signatures; None when unsigned or symmetric (mirrors verify_signature)."""
    signature = checkpoint.get("signature")
    alg = checkpoint.get("signature_alg")
    if not signature or alg in (None, "unsigned", "HMAC-SHA512-sim"):
        return None
    payload = {k: v for k, v in checkpoint.items() if k not in ("signature", "signature_alg", "signer_public_key")}
    try:
        from agents.agent_bus_signing import EventSigner
    except Exception:  # pragma: no cover
        return None
    return bool(EventSigner.verify(payload, signature, checkpoint.get("signer_public_key") or "", alg))


# --------------------------------------------------------------------------- #
# Merkle checkpointing (RFC 6962 tree shape)
# --------------------------------------------------------------------------- #
#
# A linear hash chain proves order and linkage but cannot prove COMPLETENESS:
# an operator who drops the tail of a chain (or a contiguous suffix) leaves no
# trace. A signed Merkle checkpoint over the packet hashes fixes that — the
# root commits to the exact set and count, and any packet can carry a compact
# inclusion proof against it. Leaf/node inputs are domain-separated (0x00/0x01
# prefixes, RFC 6962) so a node can never be replayed as a leaf.


def _merkle_leaf_hash(packet_hash: str) -> str:
    return hashlib.sha256(b"\x00" + bytes.fromhex(packet_hash)).hexdigest()


def _merkle_node_hash(left: str, right: str) -> str:
    return hashlib.sha256(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()


def merkle_tree_head(packet_hashes: list[str]) -> str:
    """RFC 6962 Merkle Tree Head over an ordered list of packet hashes."""
    n = len(packet_hashes)
    if n == 0:
        return hashlib.sha256(b"").hexdigest()
    if n == 1:
        return _merkle_leaf_hash(packet_hashes[0])
    k = 1
    while k * 2 < n:
        k *= 2
    return _merkle_node_hash(merkle_tree_head(packet_hashes[:k]), merkle_tree_head(packet_hashes[k:]))


def merkle_audit_path(packet_hashes: list[str], index: int) -> list[str]:
    """RFC 6962 section 2.1.1 inclusion (audit) path for the leaf at ``index``."""
    n = len(packet_hashes)
    if not 0 <= index < n:
        raise IndexError(f"leaf index {index} out of range for tree of size {n}")
    if n == 1:
        return []
    k = 1
    while k * 2 < n:
        k *= 2
    if index < k:
        return merkle_audit_path(packet_hashes[:k], index) + [merkle_tree_head(packet_hashes[k:])]
    return merkle_audit_path(packet_hashes[k:], index - k) + [merkle_tree_head(packet_hashes[:k])]


def verify_merkle_inclusion(
    packet_hash: str,
    leaf_index: int,
    tree_size: int,
    audit_path: list[str],
    merkle_root: str,
) -> bool:
    """RFC 9162 section 2.1.3.2 inclusion-proof verification."""
    if not 0 <= leaf_index < tree_size:
        return False
    fn, sn = leaf_index, tree_size - 1
    result = _merkle_leaf_hash(packet_hash)
    for sibling in audit_path:
        if sn == 0:
            return False
        if fn % 2 == 1 or fn == sn:
            result = _merkle_node_hash(sibling, result)
            if fn % 2 == 0:
                while fn % 2 == 0 and fn != 0:
                    fn >>= 1
                    sn >>= 1
        else:
            result = _merkle_node_hash(result, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and result == merkle_root


# --------------------------------------------------------------------------- #
# RFC 8785 (JCS) canonicalization + ACTA receipt interop
# --------------------------------------------------------------------------- #
#
# ``canonical_json``/``sha256_value`` above are this module's frozen internal
# convention — existing packet hashes must stay byte-identical, so they are
# untouched. JCS (RFC 8785) is the canonicalization the receipt-interop field
# converged on (the ACTA signed-receipts draft mandates it); it differs from
# json.dumps in number formatting (ECMA-262 shortest round-trip), raw-UTF-8
# strings, and UTF-16-code-unit key order. It is used ONLY for the new export
# views below, never for packet hashing.

_JCS_ESCAPES = {0x08: "\\b", 0x09: "\\t", 0x0A: "\\n", 0x0C: "\\f", 0x0D: "\\r", 0x22: '\\"', 0x5C: "\\\\"}


def _jcs_number(value: float) -> str:
    """ECMA-262 Number::toString (shortest round-trip form), per RFC 8785 3.2.2.3."""
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("NaN and Infinity are not allowed in JCS (RFC 8785)")
    if value == 0:
        return "0"  # IEEE -0 serializes as "0"
    sign = "-" if value < 0 else ""
    rep = repr(abs(value))  # Python repr is already shortest-round-trip
    if "e" in rep:
        mantissa, _, exp_str = rep.partition("e")
        exponent = int(exp_str)
    else:
        mantissa, exponent = rep, 0
    int_part, _, frac_part = mantissa.partition(".")
    if int_part != "0":
        point = len(int_part) + exponent  # decimal point position vs first significant digit
    else:
        point = exponent - (len(frac_part) - len(frac_part.lstrip("0")))
    digits = (int_part + frac_part).strip("0")
    k = len(digits)
    if k <= point <= 21:
        body = digits + "0" * (point - k)
    elif 0 < point <= 21:
        body = digits[:point] + "." + digits[point:]
    elif -6 < point <= 0:
        body = "0." + "0" * (-point) + digits
    else:
        e = point - 1
        suffix = f"e+{e}" if e >= 0 else f"e-{-e}"
        body = digits[0] + ("." + digits[1:] if k > 1 else "") + suffix
    return sign + body


def _jcs_string(value: str) -> str:
    parts = ['"']
    for ch in value:
        cp = ord(ch)
        esc = _JCS_ESCAPES.get(cp)
        if esc is not None:
            parts.append(esc)
        elif cp < 0x20:
            parts.append(f"\\u{cp:04x}")
        else:
            parts.append(ch)
    parts.append('"')
    return "".join(parts)


def jcs_dumps(value: Any) -> str:
    """RFC 8785 JSON Canonicalization Scheme serializer (stdlib-only)."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _jcs_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _jcs_number(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(jcs_dumps(item) for item in value) + "]"
    if isinstance(value, dict):
        # RFC 8785 3.2.3: keys sorted as arrays of UTF-16 code units.
        keys = sorted(value.keys(), key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(_jcs_string(k) + ":" + jcs_dumps(value[k]) for k in keys) + "}"
    raise TypeError(f"type not representable in JCS: {type(value).__name__}")


# ACTA = draft-farley-acta-signed-receipts-01 (IETF, Apr 2026): signed decision
# receipts with JCS canonicalization, hex-encoded signatures, and
# previousReceiptHash chaining. It RECOMMENDS ML-DSA-65 for new deployments —
# which is exactly our primary signer tier, so the mapping is direct.

ACTA_RECEIPT_TYPE = "scbe:reaction-state"
_ACTA_ALG_BY_SIGNER = {"Ed25519": "EdDSA", "ML-DSA-65": "ML-DSA-65"}


def acta_receipt_hash(receipt: dict[str, Any]) -> str:
    """draft 5.7: lowercase hex SHA-256 of JCS of the ENTIRE signed receipt
    (payload + signature), so re-signing an identical payload still yields a
    distinct chain link."""
    return hashlib.sha256(jcs_dumps(receipt).encode("utf-8")).hexdigest()


def packet_to_acta_receipt(
    packet: ReactionStatePacket,
    issuer_id: str = "scbe-reaction-state",
    previous_receipt_hash: str | None = None,
) -> dict[str, Any]:
    """Export a packet as an ACTA-compatible signed receipt envelope.

    The signature is computed over the exact JCS bytes of the payload (the
    draft's signing procedure), hex-encoded. Unsigned envelopes (signature
    None) are returned when no asymmetric signer backend is available.
    """
    payload: dict[str, Any] = {
        "type": ACTA_RECEIPT_TYPE,
        "issued_at": packet.generated_at_utc,
        "issuer_id": issuer_id,
        "action_ref": hashlib.sha256(jcs_dumps(packet.unsigned_dict()).encode("utf-8")).hexdigest(),
        "packet_hash": packet.packet_hash,
        "bounded_operation": packet.bounded_operation,
        "domain": packet.domain,
        "classification": packet.classification,
    }
    if previous_receipt_hash:
        payload["previousReceiptHash"] = previous_receipt_hash
    receipt: dict[str, Any] = {"payload": payload, "signature": None}
    try:
        from agents.agent_bus_signing import EventSigner

        signer = EventSigner(issuer_id)
        if signer.initialize():
            sig_b64, _pk_b64, alg = signer.sign_bytes(jcs_dumps(payload).encode("utf-8"))
            acta_alg = _ACTA_ALG_BY_SIGNER.get(alg)
            if sig_b64 and acta_alg:
                receipt["signature"] = {
                    "alg": acta_alg,
                    "kid": issuer_id,
                    "sig": base64.b64decode(sig_b64).hex(),
                }
    except Exception:  # pragma: no cover - export must not break a flow
        pass
    return receipt


def verify_acta_receipt(receipt: dict[str, Any], public_key_b64: str) -> bool | None:
    """Verify an ACTA receipt's signature over JCS(payload). The caller resolves
    ``kid`` to a public key (the draft keeps keys out of the receipt). Returns
    None for unsigned envelopes."""
    signature = receipt.get("signature")
    if not signature:
        return None
    signer_alg = {v: k for k, v in _ACTA_ALG_BY_SIGNER.items()}.get(signature.get("alg"))
    if not signer_alg:
        return False
    try:
        from agents.agent_bus_signing import EventSigner
    except Exception:  # pragma: no cover
        return None
    sig_b64 = base64.b64encode(bytes.fromhex(signature.get("sig", ""))).decode()
    message = jcs_dumps(receipt.get("payload", {})).encode("utf-8")
    return bool(EventSigner.verify_bytes(message, sig_b64, public_key_b64, signer_alg))


def verify_acta_chain(receipts: list[dict[str, Any]]) -> bool:
    """Keyless integrity check of the previousReceiptHash linkage (signature
    verification is per-receipt via ``verify_acta_receipt``)."""
    prev: str | None = None
    for receipt in receipts:
        link = receipt.get("payload", {}).get("previousReceiptHash")
        if link != prev:
            return False
        prev = acta_receipt_hash(receipt)
    return True


def rekor_hashedrekord_entry(
    checkpoint: dict[str, Any],
    signature_b64: str | None = None,
    public_key_pem_b64: str | None = None,
) -> dict[str, Any]:
    """Anchor-READY Sigstore Rekor proposed entry over the checkpoint's JCS digest.

    Dry-run by design: this module performs no network I/O, and the public
    Rekor instance only verifies PKIX keys (ECDSA / Ed25519ph) — it cannot
    verify ML-DSA today — so submission requires the caller to countersign the
    digest with a PKIX identity and POST the entry explicitly.
    """
    digest = hashlib.sha256(jcs_dumps(checkpoint).encode("utf-8")).hexdigest()
    return {
        "apiVersion": "0.0.1",
        "kind": "hashedrekord",
        "spec": {
            "data": {"hash": {"algorithm": "sha256", "value": digest}},
            "signature": {"content": signature_b64, "publicKey": {"content": public_key_pem_b64}},
        },
    }
