"""Typed hardware/software/AI routing with provenance-preserving evidence.

This is a deterministic reference control plane.  It does not execute a backend,
learn a route, or claim that unlike substrates are equivalent.  Backends become
eligible only by declaring the same operation and compatible typed boundaries.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum, IntEnum
import hashlib
import json
import math
from typing import Iterable


class EvidenceVerdict(IntEnum):
    """Current evidence relation to a claim, not the claim's intrinsic identity."""

    CONTRADICTED = -1
    UNRESOLVED = 0
    SUPPORTED = 1


class ClaimType(str, Enum):
    FACT = "fact"
    OPINION = "opinion"
    FORECAST = "forecast"
    COMMAND = "command"
    PREFERENCE = "preference"
    NORMATIVE = "normative"


class BackendKind(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    FPGA = "fpga"
    FLUIDIC = "fluidic"
    IONIC = "ionic"
    REMOTE_MODEL = "remote_model"
    SOFTWARE = "software"
    SIMULATOR = "simulator"


@dataclass(frozen=True)
class EvidenceObservation:
    evidence_id: str
    source_bundle_id: str
    verdict: EvidenceVerdict
    confidence: float
    observed_at: str

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.source_bundle_id or not self.observed_at:
            raise ValueError("evidence identity, source bundle, and time are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")


@dataclass(frozen=True)
class DiscernmentResult:
    verdict: EvidenceVerdict
    confidence: float
    support_count: int
    unresolved_count: int
    contradiction_count: int
    reason: str


@dataclass(frozen=True)
class DiscernmentRecord:
    claim_id: str
    claim_type: ClaimType
    observations: tuple[EvidenceObservation, ...] = ()

    def evaluate(self) -> DiscernmentResult:
        counts = {verdict: 0 for verdict in EvidenceVerdict}
        for observation in self.observations:
            counts[observation.verdict] += 1

        common = {
            "support_count": counts[EvidenceVerdict.SUPPORTED],
            "unresolved_count": counts[EvidenceVerdict.UNRESOLVED],
            "contradiction_count": counts[EvidenceVerdict.CONTRADICTED],
        }
        if self.claim_type in {
            ClaimType.OPINION,
            ClaimType.COMMAND,
            ClaimType.PREFERENCE,
            ClaimType.NORMATIVE,
        }:
            return DiscernmentResult(
                EvidenceVerdict.UNRESOLVED,
                0.0,
                reason="claim type is not directly truth-evaluable as written",
                **common,
            )
        present = {item.verdict for item in self.observations}
        if not present or EvidenceVerdict.UNRESOLVED in present or len(present) != 1:
            return DiscernmentResult(
                EvidenceVerdict.UNRESOLVED,
                0.0,
                reason="missing, unresolved, or conflicting evidence remains visible",
                **common,
            )
        verdict = next(iter(present))
        confidence = sum(item.confidence for item in self.observations) / len(
            self.observations
        )
        return DiscernmentResult(
            verdict,
            confidence,
            reason="all current evidence observations agree",
            **common,
        )


@dataclass(frozen=True)
class MixtureComponent:
    """One visible swirl in an aggregate; order and source never disappear."""

    contribution_id: str
    source_bundle_id: str
    order: int
    weight: float
    relationship: str
    transform_id: str

    def __post_init__(self) -> None:
        if self.order < 0 or self.weight < 0.0:
            raise ValueError("mixture order and weight must be non-negative")
        if not all(
            (
                self.contribution_id,
                self.source_bundle_id,
                self.relationship,
                self.transform_id,
            )
        ):
            raise ValueError("mixture components require complete lineage")


@dataclass(frozen=True)
class HyperTokenEnvelope:
    occurrence_id: str
    payload_sha256: str
    tokenizer_sha256: str
    source_bundle_ids: tuple[str, ...]
    mixture_trace: tuple[MixtureComponent, ...] = ()
    evidence_claim_ids: tuple[str, ...] = ()
    semantic_links: tuple[str, ...] = ()
    grammar_constraints: tuple[str, ...] = ()
    policy_tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        for digest in (self.payload_sha256, self.tokenizer_sha256):
            if len(digest) != 64 or any(
                char not in "0123456789abcdef" for char in digest
            ):
                raise ValueError(
                    "token and tokenizer identities must be lowercase SHA-256"
                )
        if not self.occurrence_id or not self.source_bundle_ids:
            raise ValueError("occurrence and source bundle identities are required")
        orders = [item.order for item in self.mixture_trace]
        if orders != sorted(orders) or len(orders) != len(set(orders)):
            raise ValueError("mixture trace order must be unique and ascending")
        known = set(self.source_bundle_ids)
        if any(item.source_bundle_id not in known for item in self.mixture_trace):
            raise ValueError(
                "mixture contribution references an undeclared source bundle"
            )


@dataclass(frozen=True)
class OperationContract:
    operation_id: str
    operation: str
    input_type: str
    output_type: str
    max_latency_ms: float | None = None
    max_energy_j: float | None = None
    min_fidelity: float = 0.0
    requires_private_local: bool = False
    requires_deterministic: bool = False
    required_policy_tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not all(
            (self.operation_id, self.operation, self.input_type, self.output_type)
        ):
            raise ValueError("operation identity and boundary types are required")
        if not 0.0 <= self.min_fidelity <= 1.0:
            raise ValueError("minimum fidelity must be in [0, 1]")
        if self.max_latency_ms is not None and self.max_latency_ms <= 0:
            raise ValueError("latency budget must be positive")
        if self.max_energy_j is not None and self.max_energy_j <= 0:
            raise ValueError("energy budget must be positive")


@dataclass(frozen=True)
class BackendCapability:
    target_id: str
    kind: BackendKind
    operations: frozenset[str]
    input_types: frozenset[str]
    output_types: frozenset[str]
    latency_ms: float
    energy_j: float
    fidelity: float
    trust: float
    private_local: bool
    deterministic: bool
    policy_tags: frozenset[str] = field(default_factory=frozenset)
    available: bool = True

    def __post_init__(self) -> None:
        if not self.target_id or self.latency_ms < 0.0 or self.energy_j < 0.0:
            raise ValueError(
                "target identity and non-negative measurements are required"
            )
        if not 0.0 <= self.fidelity <= 1.0 or not 0.0 <= self.trust <= 1.0:
            raise ValueError("fidelity and trust must be in [0, 1]")


@dataclass(frozen=True)
class TypeAdapter:
    adapter_id: str
    source_type: str
    target_type: str
    latency_ms: float
    energy_j: float
    fidelity: float
    policy_tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not all((self.adapter_id, self.source_type, self.target_type)):
            raise ValueError("adapter identity and types are required")
        if self.latency_ms < 0.0 or self.energy_j < 0.0:
            raise ValueError("adapter costs must be non-negative")
        if not 0.0 <= self.fidelity <= 1.0:
            raise ValueError("adapter fidelity must be in [0, 1]")


@dataclass(frozen=True)
class RouteCandidate:
    target_id: str
    kind: BackendKind
    adapters: tuple[str, ...]
    latency_ms: float
    energy_j: float
    fidelity: float
    trust: float
    score: float


@dataclass(frozen=True)
class RoutingDecision:
    operation_id: str
    selected: RouteCandidate
    eligible: tuple[RouteCandidate, ...]
    rejected: tuple[tuple[str, tuple[str, ...]], ...]
    receipt_sha256: str


def _adapter_paths(
    source_type: str,
    accepted_types: frozenset[str],
    adapters: tuple[TypeAdapter, ...],
    max_hops: int,
) -> list[tuple[TypeAdapter, ...]]:
    if source_type in accepted_types:
        return [()]
    queue = deque([(source_type, ())])
    found: list[tuple[TypeAdapter, ...]] = []
    seen_depth: dict[str, int] = {source_type: 0}
    while queue:
        current, path = queue.popleft()
        if len(path) >= max_hops:
            continue
        for adapter in adapters:
            if adapter.source_type != current or adapter.adapter_id in {
                p.adapter_id for p in path
            }:
                continue
            next_path = (*path, adapter)
            if adapter.target_type in accepted_types:
                found.append(next_path)
                continue
            depth = len(next_path)
            if depth < seen_depth.get(adapter.target_type, max_hops + 1):
                seen_depth[adapter.target_type] = depth
                queue.append((adapter.target_type, next_path))
    return found


def _utility(value: float, budget: float | None) -> float:
    if budget is not None:
        return max(0.0, 1.0 - value / budget)
    return 1.0 / (1.0 + math.log1p(value))


def _jsonable(value):
    """Return a canonical JSON value for enums, sets, tuples, and mappings."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(item) for item in value)
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def route_operation(
    contract: OperationContract,
    capabilities: Iterable[BackendCapability],
    adapters: Iterable[TypeAdapter] = (),
    *,
    max_adapter_hops: int = 2,
) -> RoutingDecision:
    """Select a route after hard eligibility checks, with deterministic ranking."""

    adapter_tuple = tuple(adapters)
    eligible: list[RouteCandidate] = []
    rejected: list[tuple[str, tuple[str, ...]]] = []
    for target in capabilities:
        reasons: list[str] = []
        if not target.available:
            reasons.append("unavailable")
        if contract.operation not in target.operations:
            reasons.append("operation_not_supported")
        if contract.output_type not in target.output_types:
            reasons.append("output_type_not_supported")
        if contract.requires_private_local and not target.private_local:
            reasons.append("private_local_required")
        if contract.requires_deterministic and not target.deterministic:
            reasons.append("deterministic_required")
        if not contract.required_policy_tags.issubset(target.policy_tags):
            reasons.append("target_policy_tags_missing")
        paths = _adapter_paths(
            contract.input_type,
            target.input_types,
            adapter_tuple,
            max_adapter_hops,
        )
        if not paths:
            reasons.append("no_typed_input_path")
        if reasons:
            rejected.append((target.target_id, tuple(reasons)))
            continue

        target_candidates: list[RouteCandidate] = []
        for path in paths:
            latency = target.latency_ms + sum(item.latency_ms for item in path)
            energy = target.energy_j + sum(item.energy_j for item in path)
            fidelity = target.fidelity * math.prod(item.fidelity for item in path)
            if (
                contract.max_latency_ms is not None
                and latency > contract.max_latency_ms
            ):
                continue
            if contract.max_energy_j is not None and energy > contract.max_energy_j:
                continue
            if fidelity < contract.min_fidelity:
                continue
            score = (
                0.45 * fidelity
                + 0.25 * target.trust
                + 0.15 * _utility(latency, contract.max_latency_ms)
                + 0.15 * _utility(energy, contract.max_energy_j)
                - 0.025 * len(path)
            )
            target_candidates.append(
                RouteCandidate(
                    target_id=target.target_id,
                    kind=target.kind,
                    adapters=tuple(item.adapter_id for item in path),
                    latency_ms=latency,
                    energy_j=energy,
                    fidelity=fidelity,
                    trust=target.trust,
                    score=score,
                )
            )
        if target_candidates:
            eligible.extend(target_candidates)
        else:
            rejected.append((target.target_id, ("path_violates_budget_or_fidelity",)))

    if not eligible:
        details = "; ".join(
            f"{target}: {','.join(reasons)}" for target, reasons in rejected
        )
        raise ValueError(f"no eligible interchange route: {details}")

    ranked = tuple(
        sorted(
            eligible,
            key=lambda item: (
                -item.score,
                item.latency_ms,
                item.energy_j,
                item.target_id,
                item.adapters,
            ),
        )
    )
    rejected.sort(key=lambda item: item[0])
    receipt_payload = {
        "schema": "scbe.interchange-route.v1",
        "operation": asdict(contract),
        "selected": asdict(ranked[0]),
        "eligible": [asdict(item) for item in ranked],
        "rejected": rejected,
    }
    receipt_sha256 = hashlib.sha256(
        json.dumps(
            _jsonable(receipt_payload), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return RoutingDecision(
        operation_id=contract.operation_id,
        selected=ranked[0],
        eligible=ranked,
        rejected=tuple(rejected),
        receipt_sha256=receipt_sha256,
    )
