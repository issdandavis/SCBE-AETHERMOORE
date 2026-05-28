from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.security.rotating_drop_box import RotatingDropBoxAuthorizer, RotationTimingMonitor


def _t(seconds: int = 0) -> datetime:
    return datetime(2026, 5, 28, 12, 0, seconds, tzinfo=timezone.utc)


def test_prompted_pickup_and_drop_rotates_key_without_public_plaintext() -> None:
    box = RotatingDropBoxAuthorizer(audit_salt="unit-salt", lease_ttl_seconds=30)
    box.register_key("openai-workbench", "secret-material-v1")

    lease = box.pickup("openai-workbench", subject_id="issac", prompt_id="patent-round-001", now=_t(0))
    before = box.describe_slot("openai-workbench")
    receipt = box.drop(lease.lease_id, now=_t(5))
    after = box.describe_slot("openai-workbench")

    assert lease.material == b"secret-material-v1"
    assert lease.public_dict()["material"] == "[redacted]"
    assert before["version"] == 1
    assert after["version"] == 2
    assert before["key_fingerprint"] != after["key_fingerprint"]
    assert receipt.timing_decision == "normal"
    assert "secret-material-v1" not in str(receipt.public_dict())
    assert "issac" not in str(receipt.public_dict())


def test_double_blind_monitor_receives_fingerprints_and_monitor_rotation() -> None:
    box = RotatingDropBoxAuthorizer(
        audit_salt="unit-salt",
        monitor_ids=("monitor-a", "monitor-b"),
        lease_ttl_seconds=30,
    )
    box.register_key("github-token", "secret-material-v1")

    lease_1 = box.pickup("github-token", subject_id="user-a", prompt_id="p1", now=_t(0))
    receipt_1 = box.drop(lease_1.lease_id, now=_t(5))
    slot_after_first_drop = box.describe_slot("github-token")
    lease_2 = box.pickup("github-token", subject_id="user-a", prompt_id="p2", now=_t(6))
    receipt_2 = box.drop(lease_2.lease_id, now=_t(12))

    assert receipt_1.monitor_id in {"monitor-a", "monitor-b"}
    assert receipt_2.monitor_id in {"monitor-a", "monitor-b"}
    assert slot_after_first_drop["key_fingerprint"] == receipt_1.next_key_fingerprint
    assert lease_2.version == 2
    assert receipt_1.next_version == 2
    assert receipt_2.next_version == 3


def test_timing_monitor_flags_too_fast_and_repeated_rotations() -> None:
    box = RotatingDropBoxAuthorizer(
        audit_salt="unit-salt",
        lease_ttl_seconds=30,
        timing_monitor=RotationTimingMonitor(min_seconds=2, max_seconds=30, rapid_repeat_limit=2),
    )
    box.register_key("api-key", "secret-material-v1")

    lease_1 = box.pickup("api-key", subject_id="user-a", prompt_id="p1", now=_t(0))
    receipt_1 = box.drop(lease_1.lease_id, now=_t(1))
    lease_2 = box.pickup("api-key", subject_id="user-a", prompt_id="p2", now=_t(2))
    receipt_2 = box.drop(lease_2.lease_id, now=_t(3))

    assert receipt_1.timing_decision == "watch"
    assert "rotation_too_fast" in receipt_1.signals
    assert receipt_2.timing_decision == "escalate"
    assert "rapid_rotation_repeat" in receipt_2.signals


def test_expired_drop_is_stale_and_escalates() -> None:
    box = RotatingDropBoxAuthorizer(audit_salt="unit-salt", lease_ttl_seconds=10)
    box.register_key("model-key", "secret-material-v1")

    lease = box.pickup("model-key", subject_id="user-a", prompt_id="p1", now=_t(0))
    receipt = box.drop(lease.lease_id, now=_t(0) + timedelta(seconds=11))

    assert receipt.timing_decision == "escalate"
    assert "rotation_stale" in receipt.signals


def test_rejects_unprompted_pickup_and_double_checkout() -> None:
    box = RotatingDropBoxAuthorizer(audit_salt="unit-salt")
    box.register_key("api-key", "secret-material-v1")

    with pytest.raises(ValueError):
        box.pickup("api-key", subject_id="user-a", prompt_id="")

    box.pickup("api-key", subject_id="user-a", prompt_id="p1", now=_t(0))
    with pytest.raises(RuntimeError):
        box.pickup("api-key", subject_id="user-b", prompt_id="p2", now=_t(1))
