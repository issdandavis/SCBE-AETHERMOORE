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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ReactionClassification = Literal[
    "BIJECTIVE", "LOSSY_RECOVERABLE", "LOSSY_AMBIGUOUS", "INVALID"
]
ReactionDomain = Literal["code", "chem", "agent", "data", "mixed"]

TONGUE_COLUMNS = {
    "KO": "identity",
    "AV": "features",
    "RU": "operation",
    "CA": "constraints",
    "UM": "uncertainty_loss",
    "DR": "resolution",
}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


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

    def unsigned_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("packet_hash", None)
        return data

    def compute_hash(self) -> str:
        return sha256_value(self.unsigned_dict())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    def with_hash(self) -> "ReactionStatePacket":
        packet_hash = self.compute_hash()
        return ReactionStatePacket(
            schema_version=self.schema_version,
            generated_at_utc=self.generated_at_utc,
            domain=self.domain,
            step=self.step,
            bounded_operation=self.bounded_operation,
            source=self.source,
            target=self.target,
            semantic_engravings=list(self.semantic_engravings),
            loss_notes=list(self.loss_notes),
            recalculation=self.recalculation,
            classification=self.classification,
            tongue_columns=dict(self.tongue_columns),
            claim_boundary=list(self.claim_boundary),
            previous_packet_hash=self.previous_packet_hash,
            packet_hash=packet_hash,
        )

    def verify_hash(self) -> bool:
        return bool(self.packet_hash) and self.compute_hash() == self.packet_hash


def classify_reaction(
    *,
    recalculation: ReactionRecalculation,
    identity_preserved: bool,
    loss_notes: list[str] | tuple[str, ...] = (),
    recovery_evidence: list[str] | tuple[str, ...] = (),
) -> ReactionClassification:
    if (
        recalculation.has_failure
        or identity_preserved is False
        and not recovery_evidence
    ):
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
