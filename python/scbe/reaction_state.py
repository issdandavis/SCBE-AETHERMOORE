"""Shared SCBE reaction-state packet model.

Reaction-state packets are the common substrate for cross-language code
translation, chemistry decomposition/recomposition, tokenizer routing, and
future agent workflows. They track what moved, what changed, what was lost,
what was recalculated, and whether the transform is bijective under the
declared representation.
"""

from __future__ import annotations

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
