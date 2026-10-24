"""SCBE reconciliation stubs (research prototype, paper-trading only).

Reconstructed 2026-10-24 from the session that produced
docs/research/crypto_blockchain_mechanisms/07_reconciliation_engine_spec.md.

Design rules encoded here:
- Client order ID is the golden thread (FIX tag 11 analogue).
- Fills are deduplicated on (venue, symbol, trade_id); timestamp is metadata.
- Quantities and prices are scaled integers, never floats.
- "No data" is a distinct state from "flat" and fails closed.
- Breaks are classified by type, and every decision is appended to a
  hash-chained log so the record can be audited later.

No network calls, no keys, no real orders.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

SCALE = 10**8  # 1e-8 units, satoshi-style


def to_scaled(value: str | Decimal) -> int:
    """Convert a decimal string to a scaled integer without float rounding."""
    d = Decimal(str(value)) * SCALE
    if d != d.to_integral_value():
        raise ValueError(f"precision beyond 1e-8: {value}")
    return int(d)


class PositionState(Enum):
    KNOWN = "known"      # authoritative report received (may be zero = confirmed flat)
    NO_DATA = "no_data"  # unknown: could be flat, long, or short


class BreakType(Enum):
    MISSING_FILL = "missing_fill"          # venue reports fill we never recorded
    PHANTOM_FILL = "phantom_fill"          # we recorded a fill venue does not report
    QTY_MISMATCH = "qty_mismatch"
    PRICE_MISMATCH = "price_mismatch"
    POSITION_MISMATCH = "position_mismatch"
    UNKNOWN_ORDER = "unknown_order"        # fill with client ID we never issued
    NO_DATA = "no_data"


@dataclass(frozen=True)
class Fill:
    venue: str
    symbol: str
    trade_id: str
    client_order_id: str
    qty: int        # scaled, signed (+buy / -sell)
    price: int      # scaled
    ts_ms: int
    feed_ts_ms: int | None = None  # venue feed timestamp, for stale-feed diagnosis

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.venue, self.symbol, self.trade_id)


@dataclass(frozen=True)
class Break:
    kind: BreakType
    venue: str
    symbol: str
    detail: str


class DecisionLog:
    """Append-only, hash-chained log of decisions."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self.entries: list[dict] = []

    def append(self, event: str, payload: dict) -> str:
        prev = self.entries[-1]["hash"] if self.entries else self.GENESIS
        body = json.dumps({"prev": prev, "event": event, "payload": payload}, sort_keys=True)
        h = hashlib.sha256(body.encode()).hexdigest()
        self.entries.append({"prev": prev, "event": event, "payload": payload, "hash": h})
        return h

    def verify(self) -> bool:
        prev = self.GENESIS
        for e in self.entries:
            body = json.dumps({"prev": prev, "event": e["event"], "payload": e["payload"]}, sort_keys=True)
            if e["prev"] != prev or hashlib.sha256(body.encode()).hexdigest() != e["hash"]:
                return False
            prev = e["hash"]
        return True


@dataclass
class Ledger:
    """Internal record of issued orders and observed fills."""

    issued_orders: set[str] = field(default_factory=set)
    fills: dict[tuple[str, str, str], Fill] = field(default_factory=dict)

    def issue(self, client_order_id: str) -> None:
        self.issued_orders.add(client_order_id)

    def record_fill(self, fill: Fill) -> bool:
        """Record a fill. Returns False if it was a duplicate (idempotent)."""
        if fill.key in self.fills:
            return False
        self.fills[fill.key] = fill
        return True

    def position(self, venue: str, symbol: str) -> int:
        return sum(f.qty for f in self.fills.values() if f.venue == venue and f.symbol == symbol)


@dataclass(frozen=True)
class VenueReport:
    """Authoritative snapshot from a venue. position=None means no data."""

    venue: str
    symbol: str
    position: int | None
    fills: tuple[Fill, ...] = ()


def reconcile(ledger: Ledger, report: VenueReport, log: DecisionLog | None = None) -> list[Break]:
    """Compare internal ledger against an authoritative venue report."""
    breaks: list[Break] = []
    v, s = report.venue, report.symbol
    if report.position is None:
        breaks.append(Break(BreakType.NO_DATA, v, s, "venue returned no position data"))
    venue_keys = {f.key: f for f in report.fills}
    ours = {k: f for k, f in ledger.fills.items() if k[0] == v and k[1] == s}
    for k, vf in venue_keys.items():
        if vf.client_order_id not in ledger.issued_orders:
            breaks.append(Break(BreakType.UNKNOWN_ORDER, v, s, f"client id {vf.client_order_id}"))
        of = ours.get(k)
        if of is None:
            breaks.append(Break(BreakType.MISSING_FILL, v, s, f"trade {k[2]}"))
            continue
        if of.qty != vf.qty:
            breaks.append(Break(BreakType.QTY_MISMATCH, v, s, f"trade {k[2]}: {of.qty} vs {vf.qty}"))
        if of.price != vf.price:
            breaks.append(Break(BreakType.PRICE_MISMATCH, v, s, f"trade {k[2]}: {of.price} vs {vf.price}"))
    if report.fills:  # only flag phantoms when the venue sent a fill list
        for k in ours.keys() - venue_keys.keys():
            breaks.append(Break(BreakType.PHANTOM_FILL, v, s, f"trade {k[2]}"))
    if report.position is not None and report.position != ledger.position(v, s):
        breaks.append(Break(BreakType.POSITION_MISMATCH, v, s,
                            f"ledger {ledger.position(v, s)} vs venue {report.position}"))
    if log is not None:
        log.append("reconcile", {"venue": v, "symbol": s,
                                 "breaks": sorted(b.kind.value for b in breaks)})
    return breaks


def position_state(report: VenueReport) -> PositionState:
    return PositionState.NO_DATA if report.position is None else PositionState.KNOWN


def may_trade(report: VenueReport, breaks: list[Break]) -> bool:
    """Fail closed: any uncertainty or unresolved break blocks new risk."""
    return position_state(report) is PositionState.KNOWN and not breaks
