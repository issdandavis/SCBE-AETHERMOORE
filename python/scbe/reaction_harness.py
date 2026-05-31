"""Reusable bijective reaction harness.

The harness scores whether a transform preserves identity, loses identity, or
loses information that can be restored through declared recovery fields. It is
domain-neutral: chemistry, code translation, tokenizer routing, and agent
workflow transforms can all use the same field-comparison surface.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .reaction_state import (
    ReactionDomain,
    ReactionEndpoint,
    ReactionRecalculation,
    ReactionStatePacket,
    build_reaction_state_packet,
)

FieldStatus = Literal["preserved", "recovered", "lost", "changed", "ignored_loss"]


@dataclass(frozen=True, slots=True)
class ReactionFieldCheck:
    """One field-level comparison inside a bounded reaction."""

    field: str
    status: FieldStatus
    source_value: Any = None
    target_value: Any = None
    recovered_value: Any = None
    note: str = ""

    @property
    def ok_for_identity(self) -> bool:
        return self.status in {"preserved", "recovered", "ignored_loss"}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BijectiveReactionResult:
    """Result of a reaction-harness evaluation."""

    ok: bool
    packet: ReactionStatePacket
    field_checks: list[ReactionFieldCheck]
    preserved_fields: list[str] = field(default_factory=list)
    recovered_fields: list[str] = field(default_factory=list)
    changed_fields: list[str] = field(default_factory=list)
    lost_fields: list[str] = field(default_factory=list)
    ignored_loss_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "classification": self.packet.classification,
            "packet": self.packet.to_dict(),
            "field_checks": [check.to_dict() for check in self.field_checks],
            "preserved_fields": list(self.preserved_fields),
            "recovered_fields": list(self.recovered_fields),
            "changed_fields": list(self.changed_fields),
            "lost_fields": list(self.lost_fields),
            "ignored_loss_fields": list(self.ignored_loss_fields),
        }


def _field_present(fields: dict[str, Any], name: str) -> bool:
    return name in fields and fields[name] is not None


def evaluate_bijective_reaction(
    *,
    domain: ReactionDomain,
    bounded_operation: str,
    source: ReactionEndpoint,
    target: ReactionEndpoint,
    source_fields: dict[str, Any],
    target_fields: dict[str, Any],
    required_identity_fields: list[str] | tuple[str, ...],
    recoverable_fields: dict[str, Any] | None = None,
    allowed_loss_fields: list[str] | tuple[str, ...] = (),
    step: int = 1,
    recalculation: ReactionRecalculation | None = None,
    semantic_engravings: list[str] | tuple[str, ...] = (),
    claim_boundary: list[str] | tuple[str, ...] = (),
    previous_packet_hash: str | None = None,
    generated_at_utc: str | None = None,
) -> BijectiveReactionResult:
    """Evaluate a field-preserving or field-recovering transform.

    A required identity field may pass in two ways:
    - the target field equals the source field;
    - a recovery field equals the source field, proving the value survived in a
      different lane.

    Allowed-loss fields are recorded as loss notes but do not break identity.
    """

    recoverable_fields = recoverable_fields or {}
    checks: list[ReactionFieldCheck] = []

    preserved: list[str] = []
    recovered: list[str] = []
    changed: list[str] = []
    lost: list[str] = []
    ignored_loss: list[str] = []

    for field_name in required_identity_fields:
        source_value = source_fields.get(field_name)
        target_has_value = _field_present(target_fields, field_name)
        target_value = target_fields.get(field_name)
        recovered_value = recoverable_fields.get(field_name)

        if target_has_value and target_value == source_value:
            preserved.append(field_name)
            checks.append(
                ReactionFieldCheck(
                    field=field_name,
                    status="preserved",
                    source_value=source_value,
                    target_value=target_value,
                )
            )
        elif field_name in recoverable_fields and recovered_value == source_value:
            recovered.append(field_name)
            checks.append(
                ReactionFieldCheck(
                    field=field_name,
                    status="recovered",
                    source_value=source_value,
                    target_value=target_value,
                    recovered_value=recovered_value,
                    note="identity restored from recovery lane",
                )
            )
        elif not target_has_value:
            lost.append(field_name)
            checks.append(
                ReactionFieldCheck(
                    field=field_name,
                    status="lost",
                    source_value=source_value,
                    note="required identity field absent from target and recovery lanes",
                )
            )
        else:
            changed.append(field_name)
            checks.append(
                ReactionFieldCheck(
                    field=field_name,
                    status="changed",
                    source_value=source_value,
                    target_value=target_value,
                    note="required identity field changed without matching recovery evidence",
                )
            )

    for field_name in allowed_loss_fields:
        if _field_present(source_fields, field_name) and not _field_present(
            target_fields, field_name
        ):
            ignored_loss.append(field_name)
            checks.append(
                ReactionFieldCheck(
                    field=field_name,
                    status="ignored_loss",
                    source_value=source_fields.get(field_name),
                    note="allowed loss recorded for audit; not identity-breaking",
                )
            )

    identity_preserved = not changed and not lost
    recalculation = recalculation or ReactionRecalculation(
        identity_ok=True if identity_preserved else None,
        extra={"identity_preserved": identity_preserved},
    )
    if identity_preserved and recalculation.identity_ok is None:
        recalculation = ReactionRecalculation(
            syntax_ok=recalculation.syntax_ok,
            tests_ok=recalculation.tests_ok,
            scientific_checks_ok=recalculation.scientific_checks_ok,
            unit_checks_ok=recalculation.unit_checks_ok,
            identity_ok=identity_preserved,
            extra=dict(recalculation.extra),
        )

    loss_notes = [
        f"required identity field changed: {field_name}" for field_name in changed
    ] + [
        f"required identity field lost: {field_name}" for field_name in lost
    ] + [
        f"allowed field lost: {field_name}" for field_name in ignored_loss
    ]
    recovery_evidence = [f"recovered field: {field_name}" for field_name in recovered]

    packet = build_reaction_state_packet(
        domain=domain,
        step=step,
        bounded_operation=bounded_operation,
        source=source,
        target=target,
        semantic_engravings=[
            *semantic_engravings,
            *[f"preserved field: {field_name}" for field_name in preserved],
            *recovery_evidence,
        ],
        loss_notes=loss_notes,
        recalculation=recalculation,
        identity_preserved=identity_preserved,
        recovery_evidence=recovery_evidence,
        claim_boundary=claim_boundary,
        previous_packet_hash=previous_packet_hash,
        generated_at_utc=generated_at_utc,
    )

    return BijectiveReactionResult(
        ok=identity_preserved and not recalculation.has_failure,
        packet=packet,
        field_checks=checks,
        preserved_fields=preserved,
        recovered_fields=recovered,
        changed_fields=changed,
        lost_fields=lost,
        ignored_loss_fields=ignored_loss,
    )
