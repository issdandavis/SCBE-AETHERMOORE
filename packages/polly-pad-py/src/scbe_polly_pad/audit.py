"""Append-only Polly Pad audit receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditReceipt:
    """One canonical audit event in a hash-chained JSONL ledger."""

    event_id: str
    ts: str
    actor: str
    action: str
    subject: str
    payload: dict[str, Any]
    prev_hash: str
    event_hash: str


@dataclass(frozen=True)
class AuditVerification:
    """Integrity summary for a Polly Pad audit ledger."""

    ok: bool
    count: int
    head_hash: str
    broken_at: int | None = None
    reason: str | None = None


def default_ledger_path(base_dir: str | Path | None = None) -> Path:
    """Return the default Polly audit ledger path."""

    root = Path(base_dir) if base_dir is not None else Path.cwd()
    return root / ".polly" / "audit.jsonl"


def canonical_json(payload: dict[str, Any]) -> str:
    """Serialize payload deterministically for hashing."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_event_hash(event: dict[str, Any]) -> str:
    """Compute the canonical SHA-256 event hash."""

    material = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at line {line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"ledger line {line_no} is not an object")
            events.append(value)
    return events


def iter_events(path: str | Path) -> Iterable[AuditReceipt]:
    """Yield audit receipts from a JSONL ledger."""

    for event in _read_events(Path(path)):
        yield AuditReceipt(
            event_id=str(event["event_id"]),
            ts=str(event["ts"]),
            actor=str(event["actor"]),
            action=str(event["action"]),
            subject=str(event["subject"]),
            payload=dict(event.get("payload", {})),
            prev_hash=str(event["prev_hash"]),
            event_hash=str(event["event_hash"]),
        )


def append_event(
    path: str | Path,
    *,
    actor: str,
    action: str,
    subject: str,
    payload: dict[str, Any] | None = None,
    event_id: str | None = None,
    ts: str | None = None,
) -> AuditReceipt:
    """Append a receipt to the ledger and return it."""

    ledger = Path(path)
    prior = _read_events(ledger)
    prev_hash = str(prior[-1]["event_hash"]) if prior else GENESIS_HASH
    event: dict[str, Any] = {
        "event_id": event_id or f"evt-{uuid4().hex}",
        "ts": ts or datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "subject": subject,
        "payload": payload or {},
        "prev_hash": prev_hash,
    }
    event["event_hash"] = compute_event_hash(event)

    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(event) + "\n")

    return AuditReceipt(
        event_id=str(event["event_id"]),
        ts=str(event["ts"]),
        actor=str(event["actor"]),
        action=str(event["action"]),
        subject=str(event["subject"]),
        payload=dict(event["payload"]),
        prev_hash=str(event["prev_hash"]),
        event_hash=str(event["event_hash"]),
    )


def verify_ledger(path: str | Path) -> AuditVerification:
    """Verify hash continuity and event hashes for a ledger."""

    ledger = Path(path)
    try:
        events = _read_events(ledger)
    except ValueError as exc:
        return AuditVerification(ok=False, count=0, head_hash=GENESIS_HASH, broken_at=1, reason=str(exc))

    prev_hash = GENESIS_HASH
    for index, event in enumerate(events, start=1):
        actual_prev = str(event.get("prev_hash", ""))
        if actual_prev != prev_hash:
            return AuditVerification(
                ok=False,
                count=len(events),
                head_hash=prev_hash,
                broken_at=index,
                reason="previous hash mismatch",
            )
        expected_hash = compute_event_hash(event)
        actual_hash = str(event.get("event_hash", ""))
        if actual_hash != expected_hash:
            return AuditVerification(
                ok=False,
                count=len(events),
                head_hash=prev_hash,
                broken_at=index,
                reason="event hash mismatch",
            )
        prev_hash = actual_hash

    return AuditVerification(ok=True, count=len(events), head_hash=prev_hash)


def export_ledger(path: str | Path) -> dict[str, Any]:
    """Return a portable ledger export with integrity status."""

    verification = verify_ledger(path)
    return {
        "ledger": str(Path(path)),
        "ok": verification.ok,
        "count": verification.count,
        "head_hash": verification.head_hash,
        "broken_at": verification.broken_at,
        "reason": verification.reason,
        "events": [receipt.__dict__ for receipt in iter_events(path)] if verification.ok else [],
    }
