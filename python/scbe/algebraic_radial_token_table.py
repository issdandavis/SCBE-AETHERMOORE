"""Deterministic algebraic token tables with sparse radial relay channels.

The table geometry is derived from a compact numeric seed before tokens are
assigned.  Token surfaces never determine the geometry: canonical identities
are converted to bounded carriers, then explicit numeric weights move those
carriers through the already-derived cells.

This is a mechanics surface, not evidence that radial routing improves a
model.  ``ABSENT`` and ``UNMEASURED`` relations are deliberately distinct from
a measured neutral trit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
import math
from typing import Iterable, Mapping, Sequence

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
TAU = 2.0 * math.pi


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _unit(values: Sequence[float]) -> tuple[float, ...]:
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("a carrier must contain finite values")
    norm = math.sqrt(math.fsum(value * value for value in values))
    if norm == 0.0:
        raise ValueError("a carrier cannot be the zero vector")
    return tuple(value / norm for value in values)


def _trit(value: float, tolerance: float) -> int:
    if value > tolerance:
        return 1
    if value < -tolerance:
        return -1
    return 0


class EvidenceState(str, Enum):
    """Whether a relation exists and whether it has actually been measured."""

    ABSENT = "ABSENT"
    UNMEASURED = "UNMEASURED"
    MEASURED = "MEASURED"


class ZeroKind(str, Enum):
    """Typed zero metadata; the numeric trit remains exactly zero."""

    NOT_ZERO = "NOT_ZERO"
    NEUTRAL = "NEUTRAL"
    POSITIVE_LIMIT = "POSITIVE_LIMIT"
    NEGATIVE_LIMIT = "NEGATIVE_LIMIT"


@dataclass(frozen=True, slots=True)
class RadialTableSpec:
    cell_count: int = 64
    sector_count: int = 8
    dimensions: int = 8
    depth_count: int = 4
    neighbor_count: int = 3
    portal_count: int = 1
    seed: int = 0
    beta: float = 1.0
    neutral_tolerance: float = 1e-12
    weight_gain: float = 1.0

    def __post_init__(self) -> None:
        if self.cell_count < 2 or self.sector_count < 1:
            raise ValueError("the table needs at least two cells and one sector")
        if self.cell_count % self.sector_count:
            raise ValueError("cell_count must be divisible by sector_count")
        if self.dimensions < 2 or self.dimensions % 2:
            raise ValueError("dimensions must be an even integer of at least two")
        if self.depth_count < 1 or self.neighbor_count < 1 or self.portal_count < 0:
            raise ValueError(
                "depth/neighbor counts must be positive and portal_count non-negative"
            )
        cells_per_sector = self.cell_count // self.sector_count
        if self.neighbor_count >= cells_per_sector:
            raise ValueError("neighbor_count must be smaller than cells per sector")
        if self.portal_count > self.cell_count - cells_per_sector:
            raise ValueError("portal_count exceeds the cells outside a sector")
        for name, value in (
            ("beta", self.beta),
            ("neutral_tolerance", self.neutral_tolerance),
            ("weight_gain", self.weight_gain),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class AlgebraicCell:
    cell_id: int
    sector: int
    ordinal: int
    radius: float
    phase: float
    coordinates: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class TokenCarrier:
    """A canonical token identity plus optional, explicit numeric weights."""

    canonical_id: str
    weights: tuple[float, ...] = ()
    evidence: EvidenceState = EvidenceState.MEASURED

    def __post_init__(self) -> None:
        if not self.canonical_id:
            raise ValueError("canonical_id must be non-empty")
        if not all(math.isfinite(value) for value in self.weights):
            raise ValueError("token weights must be finite")


@dataclass(frozen=True, slots=True)
class TokenOccupancy:
    canonical_id: str
    cell_id: int | None
    score: float | None
    tied_cell_ids: tuple[int, ...]
    evidence: EvidenceState


@dataclass(frozen=True, slots=True)
class RelationEvidence:
    state: EvidenceState
    multiplier: float = 1.0
    zero_kind: ZeroKind = ZeroKind.NEUTRAL

    def __post_init__(self) -> None:
        if not math.isfinite(self.multiplier):
            raise ValueError("relation multiplier must be finite")


@dataclass(frozen=True, slots=True)
class RelationSignal:
    source: int
    target: int
    sector: int
    target_sector: int
    depth: int
    evidence: EvidenceState
    raw_value: float | None
    trit: int | None
    magnitude: float | None
    zero_kind: ZeroKind | None


@dataclass(frozen=True, slots=True)
class RelayEdge:
    source: int
    target: int
    sector: int
    target_sector: int
    depth: int
    portal: bool
    trit: int
    magnitude: float
    raw_value: float
    zero_kind: ZeroKind


class AlgebraicRadialTokenTable:
    """Generate, move, populate, and route through a radial token table.

    For cell ``i`` in sector ``s`` and harmonic pair ``p``::

        theta_i = golden_angle * (ordinal_i + 1) + 2*pi*s/S + seed_phase
        x[i, 2p:2p+2] = radius_i/(p+1) * (cos((p+1)theta_i), sin((p+1)theta_i))

    A sector parameter applies the same orthogonal Givens rotations to every
    cell in that sector.  Therefore radii, norms, and all within-sector pairwise
    distances are invariant while sectors can move relative to one another.
    """

    def __init__(self, spec: RadialTableSpec):
        self.spec = spec
        self.base_cells = self._derive_cells()

    def _derive_cells(self) -> tuple[AlgebraicCell, ...]:
        cells_per_sector = self.spec.cell_count // self.spec.sector_count
        seed_digest = sha256(str(self.spec.seed).encode("ascii")).digest()
        seed_fraction = int.from_bytes(seed_digest[:8], "big") / float(2**64)
        seed_phase = TAU * seed_fraction
        rows: list[AlgebraicCell] = []
        for cell_id in range(self.spec.cell_count):
            sector = cell_id // cells_per_sector
            ordinal = cell_id % cells_per_sector
            radius = math.sqrt((ordinal + 0.5) / cells_per_sector)
            phase = (
                GOLDEN_ANGLE * (ordinal + 1)
                + TAU * sector / self.spec.sector_count
                + seed_phase
            ) % TAU
            coordinates: list[float] = []
            for pair in range(self.spec.dimensions // 2):
                harmonic = pair + 1
                amplitude = radius / harmonic
                coordinates.extend(
                    (
                        amplitude * math.cos(harmonic * phase),
                        amplitude * math.sin(harmonic * phase),
                    )
                )
            rows.append(
                AlgebraicCell(
                    cell_id=cell_id,
                    sector=sector,
                    ordinal=ordinal,
                    radius=radius,
                    phase=phase,
                    coordinates=tuple(coordinates),
                )
            )
        return tuple(rows)

    def move(self, sector_parameters: Sequence[float]) -> tuple[AlgebraicCell, ...]:
        """Rotate each sector in hyperspace without distorting that sector."""

        if len(sector_parameters) != self.spec.sector_count:
            raise ValueError("one finite movement parameter is required per sector")
        if not all(math.isfinite(value) for value in sector_parameters):
            raise ValueError("sector movement parameters must be finite")
        rows: list[AlgebraicCell] = []
        for cell in self.base_cells:
            angle = math.atan(float(sector_parameters[cell.sector]))
            coordinates = list(cell.coordinates)
            # A shared chain of adjacent Givens rotations is an orthogonal map.
            for axis in range(self.spec.dimensions - 1):
                local_angle = angle / (axis + 1)
                cosine = math.cos(local_angle)
                sine = math.sin(local_angle)
                left, right = coordinates[axis], coordinates[axis + 1]
                coordinates[axis] = cosine * left - sine * right
                coordinates[axis + 1] = sine * left + cosine * right
            rows.append(
                AlgebraicCell(
                    cell_id=cell.cell_id,
                    sector=cell.sector,
                    ordinal=cell.ordinal,
                    radius=cell.radius,
                    phase=(cell.phase + angle) % TAU,
                    coordinates=tuple(coordinates),
                )
            )
        return tuple(rows)

    def token_vector(self, token: TokenCarrier) -> tuple[float, ...] | None:
        """Lift a canonical identity and explicit weights into table space."""

        if token.evidence is not EvidenceState.MEASURED:
            return None
        if token.weights and len(token.weights) != self.spec.dimensions:
            raise ValueError("token weight dimension must match table dimensions")
        identity = token.canonical_id.encode("utf-8")
        stream = bytearray()
        counter = 0
        while len(stream) < self.spec.dimensions:
            stream.extend(sha256(identity + counter.to_bytes(4, "big")).digest())
            counter += 1
        base = [(stream[index] / 127.5) - 1.0 for index in range(self.spec.dimensions)]
        if token.weights:
            base = [
                value + self.spec.weight_gain * weight
                for value, weight in zip(base, token.weights, strict=True)
            ]
        return _unit(base)

    def assign(
        self,
        tokens: Iterable[TokenCarrier],
        cells: Sequence[AlgebraicCell] | None = None,
        *,
        tie_tolerance: float = 1e-12,
    ) -> tuple[TokenOccupancy, ...]:
        """Fill table cells by bounded carrier/cell alignment scores."""

        if tie_tolerance < 0 or not math.isfinite(tie_tolerance):
            raise ValueError("tie_tolerance must be finite and non-negative")
        cell_rows = tuple(cells or self.base_cells)
        self._validate_cells(cell_rows)
        output: list[TokenOccupancy] = []
        for token in tokens:
            vector = self.token_vector(token)
            if vector is None:
                output.append(
                    TokenOccupancy(token.canonical_id, None, None, (), token.evidence)
                )
                continue
            scored = [
                (
                    math.fsum(
                        left * right
                        for left, right in zip(vector, cell.coordinates, strict=True)
                    ),
                    cell.cell_id,
                )
                for cell in cell_rows
            ]
            best_score = max(score for score, _ in scored)
            tied = tuple(
                sorted(
                    cell_id
                    for score, cell_id in scored
                    if abs(score - best_score) <= tie_tolerance
                )
            )
            output.append(
                TokenOccupancy(
                    canonical_id=token.canonical_id,
                    cell_id=tied[0],
                    score=best_score,
                    tied_cell_ids=tied,
                    evidence=token.evidence,
                )
            )
        return tuple(output)

    def relation(
        self,
        source: AlgebraicCell,
        target: AlgebraicCell,
        depth: int,
        evidence: RelationEvidence | None = None,
    ) -> RelationSignal:
        """Evaluate one typed radial relation.

        Measured relations use

        ``g = multiplier * exp(-beta*||x_i-x_j||^2) * cos((d+1)*delta_phase)``.
        """

        if not 0 <= depth < self.spec.depth_count:
            raise ValueError("depth is outside the table")
        relation_evidence = evidence or RelationEvidence(EvidenceState.MEASURED)
        if relation_evidence.state is not EvidenceState.MEASURED:
            return RelationSignal(
                source.cell_id,
                target.cell_id,
                source.sector,
                target.sector,
                depth,
                relation_evidence.state,
                None,
                None,
                None,
                None,
            )
        distance_squared = math.fsum(
            (left - right) ** 2
            for left, right in zip(source.coordinates, target.coordinates, strict=True)
        )
        delta_phase = target.phase - source.phase
        raw_value = (
            relation_evidence.multiplier
            * math.exp(-self.spec.beta * distance_squared)
            * math.cos((depth + 1) * delta_phase)
        )
        orientation = _trit(raw_value, self.spec.neutral_tolerance)
        if orientation:
            zero_kind = ZeroKind.NOT_ZERO
        else:
            zero_kind = relation_evidence.zero_kind
        return RelationSignal(
            source.cell_id,
            target.cell_id,
            source.sector,
            target.sector,
            depth,
            relation_evidence.state,
            raw_value,
            orientation,
            abs(raw_value),
            zero_kind,
        )

    def build_relays(
        self,
        cells: Sequence[AlgebraicCell] | None = None,
        evidence: Mapping[tuple[int, int, int], RelationEvidence] | None = None,
    ) -> tuple[RelayEdge, ...]:
        """Build normalized local and cross-sector portal channels.

        Local channels preserve stable relations while each sector moves.
        Portal channels are re-ranked after movement and are the mechanism by
        which a sector can align with a different sector.
        """

        cell_rows = tuple(cells or self.base_cells)
        self._validate_cells(cell_rows)
        evidence_map = evidence or {}
        by_sector: dict[int, list[AlgebraicCell]] = {
            sector: [] for sector in range(self.spec.sector_count)
        }
        for cell in cell_rows:
            by_sector[cell.sector].append(cell)
        edges: list[RelayEdge] = []
        for sector in range(self.spec.sector_count):
            sector_cells = sorted(by_sector[sector], key=lambda cell: cell.cell_id)
            for depth in range(self.spec.depth_count):
                for source in sector_cells:
                    signals = [
                        self.relation(
                            source,
                            target,
                            depth,
                            evidence_map.get((source.cell_id, target.cell_id, depth)),
                        )
                        for target in cell_rows
                        if target.cell_id != source.cell_id
                    ]
                    measured_local = [
                        signal
                        for signal in signals
                        if signal.evidence is EvidenceState.MEASURED
                        and signal.magnitude is not None
                        and signal.target_sector == sector
                    ]
                    measured_portals = [
                        signal
                        for signal in signals
                        if signal.evidence is EvidenceState.MEASURED
                        and signal.magnitude is not None
                        and signal.target_sector != sector
                    ]
                    measured_local.sort(
                        key=lambda signal: (-float(signal.magnitude), signal.target)
                    )
                    measured_portals.sort(
                        key=lambda signal: (-float(signal.magnitude), signal.target)
                    )
                    selected = [
                        *measured_local[: self.spec.neighbor_count],
                        *measured_portals[: self.spec.portal_count],
                    ]
                    total = math.fsum(float(signal.magnitude) for signal in selected)
                    for signal in selected:
                        magnitude = (
                            0.0 if total == 0.0 else float(signal.magnitude) / total
                        )
                        edges.append(
                            RelayEdge(
                                source=signal.source,
                                target=signal.target,
                                sector=signal.sector,
                                target_sector=signal.target_sector,
                                depth=signal.depth,
                                portal=signal.target_sector != signal.sector,
                                trit=int(signal.trit),
                                magnitude=magnitude,
                                raw_value=float(signal.raw_value),
                                zero_kind=signal.zero_kind or ZeroKind.NEUTRAL,
                            )
                        )
        return tuple(edges)

    def flash(
        self,
        state: Mapping[int, Sequence[float]],
        relays: Iterable[RelayEdge],
        *,
        depth: int,
        residual: bool = True,
    ) -> dict[int, tuple[float, ...]]:
        """Execute one sparse, sector-local relay flash."""

        if not 0 <= depth < self.spec.depth_count:
            raise ValueError("depth is outside the table")
        width = {len(tuple(values)) for values in state.values()}
        if not state or len(width) != 1 or next(iter(width)) < 1:
            raise ValueError("state vectors must be non-empty and equal width")
        if set(state) != set(range(self.spec.cell_count)):
            raise ValueError("state must contain every cell exactly once")
        if not all(
            math.isfinite(value) for values in state.values() for value in values
        ):
            raise ValueError("state values must be finite")
        vector_width = next(iter(width))
        output = {
            cell_id: list(values) if residual else [0.0] * vector_width
            for cell_id, values in state.items()
        }
        for edge in relays:
            if edge.depth != depth or edge.trit == 0 or edge.magnitude == 0.0:
                continue
            source = state[edge.source]
            for index, value in enumerate(source):
                output[edge.target][index] += edge.trit * edge.magnitude * value
        return {cell_id: tuple(values) for cell_id, values in sorted(output.items())}

    def receipt(
        self,
        *,
        cells: Sequence[AlgebraicCell] | None = None,
        occupancies: Iterable[TokenOccupancy] = (),
        relays: Iterable[RelayEdge] = (),
        sector_parameters: Sequence[float] | None = None,
    ) -> dict[str, object]:
        """Return a canonical, reconstructable mechanics receipt."""

        core: dict[str, object] = {
            "schema": "scbe.algebraic-radial-token-table.v1",
            "claim_boundary": "deterministic mechanics only; no model-quality or speed claim",
            "equation_revision": "golden-harmonic-givens-sector-relay-v1",
            "spec": asdict(self.spec),
            "sector_parameters": list(
                sector_parameters or [0.0] * self.spec.sector_count
            ),
            "cells": [asdict(cell) for cell in (cells or self.base_cells)],
            "occupancies": [asdict(row) for row in occupancies],
            "relays": [asdict(edge) for edge in relays],
        }
        return {**core, "receipt_sha256": sha256(_canonical_json(core)).hexdigest()}

    def _validate_cells(self, cells: Sequence[AlgebraicCell]) -> None:
        if len(cells) != self.spec.cell_count:
            raise ValueError("cell set does not match the table size")
        if {cell.cell_id for cell in cells} != set(range(self.spec.cell_count)):
            raise ValueError("cell IDs must be a complete zero-based range")
        if any(len(cell.coordinates) != self.spec.dimensions for cell in cells):
            raise ValueError("cell coordinate dimension does not match the table")
        if not all(
            math.isfinite(value)
            for cell in cells
            for value in (*cell.coordinates, cell.radius, cell.phase)
        ):
            raise ValueError("cell geometry must be finite")


__all__ = [
    "AlgebraicCell",
    "AlgebraicRadialTokenTable",
    "EvidenceState",
    "GOLDEN_ANGLE",
    "RadialTableSpec",
    "RelationEvidence",
    "RelationSignal",
    "RelayEdge",
    "TokenCarrier",
    "TokenOccupancy",
    "ZeroKind",
]
