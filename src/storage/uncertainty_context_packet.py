"""Exact, provenance-aware context halos for uncertainty-guided research.

The packet is an external context contract, not a neural activation or a model
weight. Exact integer masses preserve support, contradiction, and unresolved
uncertainty without collapsing missing evidence into a meaningful zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
from typing import Any, Literal, Sequence

SCHEMA_VERSION = "scbe_uncertainty_context_packet_v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EvidenceKind = Literal["observed", "inferred", "hypothesis", "opinion", "absent"]
EVIDENCE_KINDS = {"observed", "inferred", "hypothesis", "opinion", "absent"}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _fraction_record(value: Fraction) -> dict[str, int | float]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "float": float(value),
    }


@dataclass(frozen=True)
class EvidenceMass:
    """Exact integer accounting for one tangent's evidential state."""

    support: int
    contradiction: int
    uncertainty: int

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (self.support, self.contradiction, self.uncertainty)
        ):
            raise ValueError("evidence masses must be non-negative integers")

    @property
    def total(self) -> int:
        return self.support + self.contradiction + self.uncertainty

    def fractions(self) -> tuple[Fraction, Fraction, Fraction]:
        if self.total <= 0:
            raise ValueError("active evidence mass must have a positive integer base")
        return (
            Fraction(self.support, self.total),
            Fraction(self.contradiction, self.total),
            Fraction(self.uncertainty, self.total),
        )

    def to_record(self) -> dict[str, int]:
        return {
            "support": self.support,
            "contradiction": self.contradiction,
            "uncertainty": self.uncertainty,
            "base": self.total,
        }


@dataclass(frozen=True)
class ContextTangent:
    """One sourced activation around a focus value."""

    tangent_id: str
    focus_id: str
    relation: str
    claim: str
    evidence_kind: EvidenceKind
    source_hash: str
    source_uri: str
    source_span: str
    provenance_group: str
    mass: EvidenceMass
    raw_pointer: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "tangent_id": self.tangent_id,
            "focus_id": self.focus_id,
            "relation": self.relation,
            "claim": self.claim,
            "evidence_kind": self.evidence_kind,
            "source_hash": self.source_hash,
            "source_uri": self.source_uri,
            "source_span": self.source_span,
            "provenance_group": self.provenance_group,
            "mass": self.mass.to_record(),
            "raw_pointer": self.raw_pointer,
        }


def make_context_tangent(
    *,
    focus_id: str,
    relation: str,
    claim: str,
    evidence_kind: EvidenceKind,
    source_hash: str,
    source_uri: str,
    source_span: str = "",
    provenance_group: str = "",
    support: int = 0,
    contradiction: int = 0,
    uncertainty: int = 0,
    raw_pointer: str = "",
) -> ContextTangent:
    """Create a stable tangent while keeping ABSENT distinct from zero evidence."""

    if evidence_kind not in EVIDENCE_KINDS:
        raise ValueError(f"unsupported evidence kind {evidence_kind!r}")
    if not focus_id.strip() or not relation.strip():
        raise ValueError("focus_id and relation are required")
    mass = EvidenceMass(support, contradiction, uncertainty)
    if evidence_kind == "absent":
        if mass.total != 0 or claim or source_hash or source_uri or source_span:
            raise ValueError("ABSENT tangents carry no synthetic claim, source, or mass")
        group = provenance_group.strip() or f"absent:{relation.strip()}"
    else:
        if not claim.strip() or not source_uri.strip():
            raise ValueError("active tangents require a claim and source URI")
        if not SHA256_RE.fullmatch(source_hash.casefold()):
            raise ValueError("active tangent source_hash must be a lowercase SHA-256")
        mass.fractions()
        group = provenance_group.strip() or source_hash.casefold()
    identity = {
        "focus_id": focus_id.strip(),
        "relation": relation.strip(),
        "claim": claim,
        "evidence_kind": evidence_kind,
        "source_hash": source_hash.casefold(),
        "source_uri": source_uri,
        "source_span": source_span,
        "provenance_group": group,
        "mass": mass.to_record(),
        "raw_pointer": raw_pointer,
    }
    tangent_id = "tan_" + hashlib.sha256(_canonical_json(identity)).hexdigest()[:24]
    return ContextTangent(
        tangent_id=tangent_id,
        focus_id=identity["focus_id"],
        relation=identity["relation"],
        claim=identity["claim"],
        evidence_kind=identity["evidence_kind"],
        source_hash=identity["source_hash"],
        source_uri=identity["source_uri"],
        source_span=identity["source_span"],
        provenance_group=group,
        mass=mass,
        raw_pointer=identity["raw_pointer"],
    )


def _mean(values: Sequence[Fraction]) -> Fraction:
    if not values:
        raise ValueError("cannot average an empty fraction sequence")
    return sum(values, Fraction(0, 1)) / len(values)


def build_uncertainty_context_packet(focus_id: str, tangents: Sequence[ContextTangent]) -> dict[str, Any]:
    """Build an exact complex-axis context packet with provenance de-duplication.

    Tangents from one provenance group are averaged first. Independent groups
    are then averaged equally, preventing repeated transformations or excerpts
    from one source from masquerading as independent support.
    """

    if not focus_id.strip():
        raise ValueError("focus_id is required")
    ordered = sorted(tangents, key=lambda row: row.tangent_id)
    if len({row.tangent_id for row in ordered}) != len(ordered):
        raise ValueError("duplicate tangent identity")
    if any(row.focus_id != focus_id for row in ordered):
        raise ValueError("every tangent must bind the packet focus_id")
    active = [row for row in ordered if row.evidence_kind != "absent"]
    absent = [row for row in ordered if row.evidence_kind == "absent"]
    groups: dict[str, list[ContextTangent]] = {}
    for tangent in active:
        groups.setdefault(tangent.provenance_group, []).append(tangent)

    group_records: list[dict[str, Any]] = []
    group_axes: list[tuple[Fraction, Fraction, Fraction]] = []
    for group_id in sorted(groups):
        rows = groups[group_id]
        fractions = [row.mass.fractions() for row in rows]
        support = _mean([value[0] for value in fractions])
        contradiction = _mean([value[1] for value in fractions])
        uncertainty = _mean([value[2] for value in fractions])
        group_axes.append((support, contradiction, uncertainty))
        group_records.append(
            {
                "provenance_group": group_id,
                "tangent_count": len(rows),
                "support": _fraction_record(support),
                "contradiction": _fraction_record(contradiction),
                "uncertainty": _fraction_record(uncertainty),
            }
        )

    if group_axes:
        support = _mean([value[0] for value in group_axes])
        contradiction = _mean([value[1] for value in group_axes])
        uncertainty = _mean([value[2] for value in group_axes])
    else:
        support = contradiction = Fraction(0, 1)
        uncertainty = Fraction(1, 1)
    real_axis = support - contradiction
    imaginary_axis = uncertainty
    core = {
        "schema": SCHEMA_VERSION,
        "focus_id": focus_id,
        "aggregation": "equal_within_provenance_then_equal_across_provenance",
        "active_tangent_count": len(active),
        "absent_tangent_count": len(absent),
        "independent_provenance_group_count": len(groups),
        "axes": {
            "support": _fraction_record(support),
            "contradiction": _fraction_record(contradiction),
            "real_net_support": _fraction_record(real_axis),
            "imaginary_unresolved_uncertainty": _fraction_record(imaginary_axis),
        },
        "provenance_groups": group_records,
        "tangents": [row.to_record() for row in ordered],
        "boundary": (
            "External context only. Exact fractions are routing metadata, not calibrated "
            "probabilities, independent votes, neural activations, or model weights."
        ),
    }
    return {**core, "packet_sha256": hashlib.sha256(_canonical_json(core)).hexdigest()}


__all__ = [
    "SCHEMA_VERSION",
    "EvidenceMass",
    "ContextTangent",
    "make_context_tangent",
    "build_uncertainty_context_packet",
]
