"""Atom-transfer recorder for GeoSeed tongue routing.

This module tracks symbolic atom transfers: minimal token units moving from one
Sacred Tongue shell to another during tokenization or compilation. It is a
deterministic audit scaffold, not a chemistry simulator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

PHI = (1.0 + math.sqrt(5.0)) / 2.0
LN_PHI = math.log(PHI)
TONGUE_ORDER = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_INDEX = {tongue: index for index, tongue in enumerate(TONGUE_ORDER)}


def normalize_tongue(tongue: str) -> str:
    """Normalize and validate a Sacred Tongue abbreviation."""

    normalized = tongue.strip().upper()
    if normalized not in TONGUE_INDEX:
        raise ValueError(f"unknown tongue {tongue!r}; expected one of {', '.join(TONGUE_ORDER)}")
    return normalized


def transfer_cost(from_tongue: str, to_tongue: str) -> float:
    """Return the hyperbolic shell-hop cost between two tongue abbreviations."""

    start = normalize_tongue(from_tongue)
    end = normalize_tongue(to_tongue)
    return abs(TONGUE_INDEX[end] - TONGUE_INDEX[start]) * LN_PHI


@dataclass(frozen=True)
class TransferEvent:
    """One symbolic atom transfer across the GeoSeed tongue ladder."""

    from_tongue: str
    to_tongue: str
    token: str
    geodesic_cost: float
    is_self: bool
    step: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_tongue": self.from_tongue,
            "to_tongue": self.to_tongue,
            "token": self.token,
            "geodesic_cost": round(self.geodesic_cost, 12),
            "is_self": self.is_self,
            "step": self.step,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TransferMatrix:
    """Dense 6x6 transfer matrix with counts, row rates, and shell-hop costs."""

    counts: list[list[int]]
    rates: list[list[float]]
    costs: list[list[float]]
    total_events: int
    self_transfer_count: int
    cross_transfer_count: int

    def dominant_flow(self, include_self: bool = False) -> dict[str, Any] | None:
        """Return the highest-count transfer lane."""

        best: tuple[int, int, int] | None = None
        for row_index, row in enumerate(self.counts):
            for col_index, count in enumerate(row):
                if count == 0:
                    continue
                if not include_self and row_index == col_index:
                    continue
                if best is None or count > best[2]:
                    best = (row_index, col_index, count)
        if best is None:
            return None
        row_index, col_index, count = best
        return {
            "from_tongue": TONGUE_ORDER[row_index],
            "to_tongue": TONGUE_ORDER[col_index],
            "count": count,
            "rate": self.rates[row_index][col_index],
            "geodesic_cost": self.costs[row_index][col_index],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "tongues": list(TONGUE_ORDER),
            "counts": self.counts,
            "rates": self.rates,
            "costs": self.costs,
            "total_events": self.total_events,
            "self_transfer_count": self.self_transfer_count,
            "cross_transfer_count": self.cross_transfer_count,
            "dominant_flow": self.dominant_flow(),
        }


class AtomTransferRecorder:
    """Record token movements through the six-shell GeoSeed tongue ladder."""

    def __init__(self, session_id: str = "default") -> None:
        self.session_id = session_id
        self._events: list[TransferEvent] = []
        self._step = 0

    @property
    def events(self) -> tuple[TransferEvent, ...]:
        return tuple(self._events)

    @property
    def event_count(self) -> int:
        return len(self._events)

    def record(
        self,
        from_tongue: str,
        to_tongue: str,
        token: str,
        metadata: dict[str, Any] | None = None,
    ) -> TransferEvent:
        """Record one token transfer and return the immutable event."""

        start = normalize_tongue(from_tongue)
        end = normalize_tongue(to_tongue)
        event = TransferEvent(
            from_tongue=start,
            to_tongue=end,
            token=str(token),
            geodesic_cost=transfer_cost(start, end),
            is_self=start == end,
            step=self._step,
            metadata=dict(metadata or {}),
        )
        self._events.append(event)
        self._step += 1
        return event

    def record_batch(self, records: Iterable[tuple[str, str, str] | dict[str, Any]]) -> tuple[TransferEvent, ...]:
        """Record a batch of tuple or mapping records."""

        events: list[TransferEvent] = []
        for record in records:
            if isinstance(record, dict):
                events.append(
                    self.record(
                        str(record["from_tongue"]),
                        str(record["to_tongue"]),
                        str(record["token"]),
                        metadata=dict(record.get("metadata", {})),
                    )
                )
            else:
                from_tongue, to_tongue, token = record
                events.append(self.record(from_tongue, to_tongue, token))
        return tuple(events)

    def events_for_token(self, token: str) -> tuple[TransferEvent, ...]:
        return tuple(event for event in self._events if event.token == token)

    def events_from(self, tongue: str) -> tuple[TransferEvent, ...]:
        start = normalize_tongue(tongue)
        return tuple(event for event in self._events if event.from_tongue == start)

    def events_to(self, tongue: str) -> tuple[TransferEvent, ...]:
        end = normalize_tongue(tongue)
        return tuple(event for event in self._events if event.to_tongue == end)

    def total_geodesic_cost(self) -> float:
        return sum(event.geodesic_cost for event in self._events)

    def mean_hop_distance(self, include_self: bool = False) -> float:
        events = [event for event in self._events if include_self or not event.is_self]
        if not events:
            return 0.0
        return sum(event.geodesic_cost for event in events) / len(events)

    def transfer_matrix(self) -> TransferMatrix:
        counts = [[0 for _ in TONGUE_ORDER] for _ in TONGUE_ORDER]
        for event in self._events:
            counts[TONGUE_INDEX[event.from_tongue]][TONGUE_INDEX[event.to_tongue]] += 1

        rates: list[list[float]] = []
        for row in counts:
            row_total = sum(row)
            if row_total == 0:
                rates.append([0.0 for _ in row])
            else:
                rates.append([count / row_total for count in row])

        costs = [
            [round(abs(col_index - row_index) * LN_PHI, 12) for col_index in range(len(TONGUE_ORDER))]
            for row_index in range(len(TONGUE_ORDER))
        ]
        self_count = sum(1 for event in self._events if event.is_self)
        return TransferMatrix(
            counts=counts,
            rates=rates,
            costs=costs,
            total_events=len(self._events),
            self_transfer_count=self_count,
            cross_transfer_count=len(self._events) - self_count,
        )

    def summary(self) -> dict[str, Any]:
        matrix = self.transfer_matrix()
        return {
            "schema_version": "geoseed_transfer_recorder_v1",
            "session_id": self.session_id,
            "event_count": self.event_count,
            "total_geodesic_cost": round(self.total_geodesic_cost(), 12),
            "mean_cross_hop_distance": round(self.mean_hop_distance(include_self=False), 12),
            "dominant_flow": matrix.dominant_flow(),
            "self_transfer_count": matrix.self_transfer_count,
            "cross_transfer_count": matrix.cross_transfer_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "geoseed_transfer_recorder_v1",
            "session_id": self.session_id,
            "events": [event.to_dict() for event in self._events],
            "matrix": self.transfer_matrix().to_dict(),
            "summary": self.summary(),
        }

    def reset(self) -> None:
        self._events.clear()
        self._step = 0
