"""Double-blind rotating drop-box authorization for short-lived key leases.

The drop box gives callers a temporary key lease, then rotates the key
immediately when the lease is returned. Public receipts contain only keyed
fingerprints and timing metadata so the monitor can audit behavior without
seeing plaintext key material or raw subject identifiers.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _fingerprint(value: str | bytes, salt: bytes) -> str:
    payload = value if isinstance(value, bytes) else value.encode("utf-8")
    return hmac.new(salt, payload, hashlib.sha256).hexdigest()


def _derive_next_key(current: bytes, lease_id: str, returned_at: datetime, nonce: bytes) -> bytes:
    payload = b"|".join([b"SCBE_DROP_BOX_ROTATE_V1", lease_id.encode("utf-8"), _iso(returned_at).encode("utf-8"), nonce])
    return hmac.new(current, payload, hashlib.sha256).digest()


@dataclass(frozen=True)
class KeyLease:
    lease_id: str
    key_id: str
    version: int
    material: bytes
    issued_at_utc: str
    expires_at_utc: str
    subject_fingerprint: str
    prompt_fingerprint: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "key_id": self.key_id,
            "version": self.version,
            "issued_at_utc": self.issued_at_utc,
            "expires_at_utc": self.expires_at_utc,
            "subject_fingerprint": self.subject_fingerprint,
            "prompt_fingerprint": self.prompt_fingerprint,
            "material": "[redacted]",
        }


@dataclass(frozen=True)
class RotationReceipt:
    lease_id: str
    key_id: str
    previous_version: int
    next_version: int
    returned_at_utc: str
    elapsed_seconds: float
    monitor_id: str
    timing_decision: str
    signals: tuple[str, ...]
    subject_fingerprint: str
    previous_key_fingerprint: str
    next_key_fingerprint: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "key_id": self.key_id,
            "previous_version": self.previous_version,
            "next_version": self.next_version,
            "returned_at_utc": self.returned_at_utc,
            "elapsed_seconds": self.elapsed_seconds,
            "monitor_id": self.monitor_id,
            "timing_decision": self.timing_decision,
            "signals": list(self.signals),
            "subject_fingerprint": self.subject_fingerprint,
            "previous_key_fingerprint": self.previous_key_fingerprint,
            "next_key_fingerprint": self.next_key_fingerprint,
        }


@dataclass
class _KeySlot:
    key_id: str
    material: bytes
    version: int = 1
    active_lease_id: str | None = None
    last_returned_at: datetime | None = None


@dataclass
class _LeaseState:
    lease: KeyLease
    subject_id: str
    issued_at: datetime
    expires_at: datetime
    key_material_at_issue: bytes


@dataclass
class RotationTimingMonitor:
    """Small deterministic monitor for key rotation timing behavior."""

    min_seconds: float = 1.0
    max_seconds: float = 300.0
    rapid_repeat_limit: int = 2
    _rapid_counts: dict[str, int] = field(default_factory=dict)

    def classify(self, subject_fingerprint: str, elapsed_seconds: float, expired: bool) -> tuple[str, tuple[str, ...]]:
        signals: list[str] = []
        if elapsed_seconds < self.min_seconds:
            signals.append("rotation_too_fast")
            self._rapid_counts[subject_fingerprint] = self._rapid_counts.get(subject_fingerprint, 0) + 1
        else:
            self._rapid_counts[subject_fingerprint] = 0
        if elapsed_seconds > self.max_seconds or expired:
            signals.append("rotation_stale")
        if self._rapid_counts.get(subject_fingerprint, 0) >= self.rapid_repeat_limit:
            signals.append("rapid_rotation_repeat")
        if not signals:
            return "normal", ()
        if "rapid_rotation_repeat" in signals or "rotation_stale" in signals:
            return "escalate", tuple(signals)
        return "watch", tuple(signals)


class RotatingDropBoxAuthorizer:
    """Prompted key pickup/drop system with immediate rotation on return."""

    def __init__(
        self,
        *,
        audit_salt: str | bytes | None = None,
        monitor_ids: tuple[str, ...] = ("slm-monitor-a", "slm-monitor-b", "slm-monitor-c"),
        lease_ttl_seconds: float = 60.0,
        timing_monitor: RotationTimingMonitor | None = None,
    ) -> None:
        self._audit_salt = (
            audit_salt if isinstance(audit_salt, bytes) else str(audit_salt or secrets.token_hex(32)).encode("utf-8")
        )
        self._monitor_ids = monitor_ids or ("slm-monitor-a",)
        self._lease_ttl = timedelta(seconds=lease_ttl_seconds)
        self._timing_monitor = timing_monitor or RotationTimingMonitor(max_seconds=lease_ttl_seconds)
        self._slots: dict[str, _KeySlot] = {}
        self._leases: dict[str, _LeaseState] = {}
        self._receipts: list[RotationReceipt] = []

    def register_key(self, key_id: str, material: str | bytes | None = None) -> None:
        if not key_id.strip():
            raise ValueError("key_id is required")
        if key_id in self._slots:
            raise ValueError(f"key already registered: {key_id}")
        if material is None:
            raw = secrets.token_bytes(32)
        elif isinstance(material, bytes):
            raw = bytes(material)
        else:
            raw = material.encode("utf-8")
        if not raw:
            raise ValueError("key material cannot be empty")
        self._slots[key_id] = _KeySlot(key_id=key_id, material=raw)

    def pickup(self, key_id: str, *, subject_id: str, prompt_id: str, now: datetime | None = None) -> KeyLease:
        if not prompt_id.strip():
            raise ValueError("prompt_id is required for prompted pickup")
        slot = self._require_slot(key_id)
        if slot.active_lease_id:
            raise RuntimeError(f"key is already leased: {key_id}")
        issued_at = now or _utc_now()
        expires_at = issued_at + self._lease_ttl
        lease_id = secrets.token_hex(12)
        lease = KeyLease(
            lease_id=lease_id,
            key_id=key_id,
            version=slot.version,
            material=slot.material,
            issued_at_utc=_iso(issued_at),
            expires_at_utc=_iso(expires_at),
            subject_fingerprint=_fingerprint(subject_id, self._audit_salt),
            prompt_fingerprint=_fingerprint(prompt_id, self._audit_salt),
        )
        slot.active_lease_id = lease_id
        self._leases[lease_id] = _LeaseState(
            lease=lease,
            subject_id=subject_id,
            issued_at=issued_at,
            expires_at=expires_at,
            key_material_at_issue=slot.material,
        )
        return lease

    def drop(self, lease_id: str, *, now: datetime | None = None) -> RotationReceipt:
        state = self._leases.pop(lease_id, None)
        if state is None:
            raise KeyError(f"unknown or already returned lease: {lease_id}")
        slot = self._require_slot(state.lease.key_id)
        if slot.active_lease_id != lease_id:
            raise RuntimeError("lease does not match active key slot")

        returned_at = now or _utc_now()
        elapsed = max(0.0, (returned_at - state.issued_at).total_seconds())
        previous_material = slot.material
        next_material = _derive_next_key(previous_material, lease_id, returned_at, secrets.token_bytes(16))
        previous_version = slot.version
        slot.material = next_material
        slot.version += 1
        slot.active_lease_id = None
        slot.last_returned_at = returned_at

        monitor_id = self._monitor_for(slot.key_id, slot.version)
        decision, signals = self._timing_monitor.classify(
            state.lease.subject_fingerprint,
            elapsed,
            expired=returned_at > state.expires_at,
        )
        receipt = RotationReceipt(
            lease_id=lease_id,
            key_id=slot.key_id,
            previous_version=previous_version,
            next_version=slot.version,
            returned_at_utc=_iso(returned_at),
            elapsed_seconds=round(elapsed, 6),
            monitor_id=monitor_id,
            timing_decision=decision,
            signals=signals,
            subject_fingerprint=state.lease.subject_fingerprint,
            previous_key_fingerprint=_fingerprint(previous_material, self._audit_salt),
            next_key_fingerprint=_fingerprint(next_material, self._audit_salt),
        )
        self._receipts.append(receipt)
        return receipt

    def public_receipts(self) -> list[dict[str, Any]]:
        return [receipt.public_dict() for receipt in self._receipts]

    def describe_slot(self, key_id: str) -> dict[str, Any]:
        slot = self._require_slot(key_id)
        return {
            "key_id": slot.key_id,
            "version": slot.version,
            "leased": bool(slot.active_lease_id),
            "active_lease_id": slot.active_lease_id,
            "last_returned_at_utc": _iso(slot.last_returned_at) if slot.last_returned_at else None,
            "key_fingerprint": _fingerprint(slot.material, self._audit_salt),
        }

    def _monitor_for(self, key_id: str, version: int) -> str:
        digest = hashlib.sha256(f"{key_id}:{version}".encode("utf-8")).digest()
        return self._monitor_ids[digest[0] % len(self._monitor_ids)]

    def _require_slot(self, key_id: str) -> _KeySlot:
        try:
            return self._slots[key_id]
        except KeyError as exc:
            raise KeyError(f"unknown key slot: {key_id}") from exc
