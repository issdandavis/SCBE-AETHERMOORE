"""
Tests for HYDRA Switchboard -- lease-based task queue + role channels.
=====================================================================

Covers:
- Enqueue and claim basic flow
- Lease expiry and reclaim by another worker
- Dedupe key enforcement (prevent duplicate tasks)
- Priority ordering (lower priority number = claimed first)
- Role-scoped messaging (post + retrieve)
- Stats accuracy
- Complete / fail lifecycle
"""

import json
import time
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hydra.switchboard import Switchboard


@pytest.fixture
def sb(tmp_path):
    """Create a fresh Switchboard backed by a temp SQLite database."""
    db_path = str(tmp_path / "test_switchboard.db")
    return Switchboard(db_path=db_path)


# =========================================================================
# Enqueue + Claim
# =========================================================================


class TestEnqueueAndClaim:
    """Basic task enqueue and claim lifecycle."""

    def test_enqueue_returns_task_id(self, sb: Switchboard):
        result = sb.enqueue_task(role="coder", payload={"cmd": "build"})
        assert "task_id" in result
        assert result["role"] == "coder"
        assert result["status"] == "queued"
        assert result["deduped"] is False

    def test_claim_returns_task(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        claimed = sb.claim_task(worker_id="w1", roles=["coder"])
        assert claimed is not None
        assert claimed["status"] == "leased"
        assert claimed["lease_owner"] == "w1"
        assert claimed["payload"] == {"cmd": "build"}

    def test_claim_empty_queue_returns_none(self, sb: Switchboard):
        claimed = sb.claim_task(worker_id="w1", roles=["coder"])
        assert claimed is None

    def test_claim_wrong_role_returns_none(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        claimed = sb.claim_task(worker_id="w1", roles=["reviewer"])
        assert claimed is None

    def test_double_claim_returns_none_for_second(self, sb: Switchboard):
        """Only one worker can claim a single task."""
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        first = sb.claim_task(worker_id="w1", roles=["coder"])
        second = sb.claim_task(worker_id="w2", roles=["coder"])
        assert first is not None
        assert second is None

    def test_claim_increments_attempts(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        claimed = sb.claim_task(worker_id="w1", roles=["coder"])
        assert claimed["attempts"] == 1


# =========================================================================
# Lease expiry + reclaim
# =========================================================================


class TestLeaseExpiry:
    """When a lease expires, the task returns to the queue."""

    def test_expired_lease_can_be_reclaimed(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        # Claim with a 1-second lease
        first = sb.claim_task(worker_id="w1", roles=["coder"], lease_seconds=1)
        assert first is not None

        # Wait for lease to expire
        time.sleep(1.5)

        # Second worker should be able to claim
        second = sb.claim_task(worker_id="w2", roles=["coder"], lease_seconds=60)
        assert second is not None
        assert second["lease_owner"] == "w2"
        assert second["attempts"] == 2

    def test_active_lease_blocks_reclaim(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        sb.claim_task(worker_id="w1", roles=["coder"], lease_seconds=300)
        # Should NOT be available to w2
        second = sb.claim_task(worker_id="w2", roles=["coder"])
        assert second is None


# =========================================================================
# Dedup key enforcement
# =========================================================================


class TestDeduplication:
    """Dedupe key prevents duplicate enqueues while task is active."""

    def test_dedup_blocks_duplicate(self, sb: Switchboard):
        first = sb.enqueue_task(role="coder", payload={"cmd": "a"}, dedupe_key="build-main")
        second = sb.enqueue_task(role="coder", payload={"cmd": "b"}, dedupe_key="build-main")
        assert second["deduped"] is True
        assert second["task_id"] == first["task_id"]

    def test_different_dedup_keys_allowed(self, sb: Switchboard):
        first = sb.enqueue_task(role="coder", payload={"cmd": "a"}, dedupe_key="build-main")
        second = sb.enqueue_task(role="coder", payload={"cmd": "b"}, dedupe_key="build-dev")
        assert second["deduped"] is False
        assert second["task_id"] != first["task_id"]

    def test_dedup_allows_after_completion(self, sb: Switchboard):
        """Once a task is done, the same dedupe key can be reused."""
        sb.enqueue_task(role="coder", payload={"cmd": "a"}, dedupe_key="build-main")
        claimed = sb.claim_task(worker_id="w1", roles=["coder"])
        sb.complete_task(claimed["task_id"], "w1", {"ok": True})

        # Now the same dedupe key should be re-enqueueable
        new = sb.enqueue_task(role="coder", payload={"cmd": "b"}, dedupe_key="build-main")
        assert new["deduped"] is False

    def test_no_dedup_key_allows_duplicates(self, sb: Switchboard):
        first = sb.enqueue_task(role="coder", payload={"cmd": "a"})
        second = sb.enqueue_task(role="coder", payload={"cmd": "a"})
        assert first["task_id"] != second["task_id"]


# =========================================================================
# Priority ordering
# =========================================================================


class TestPriorityOrdering:
    """Lower priority number is claimed first."""

    def test_lower_priority_claimed_first(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "low"}, priority=200)
        sb.enqueue_task(role="coder", payload={"cmd": "high"}, priority=10)
        sb.enqueue_task(role="coder", payload={"cmd": "medium"}, priority=100)

        first = sb.claim_task(worker_id="w1", roles=["coder"])
        assert first["payload"]["cmd"] == "high"
        assert first["priority"] == 10

        second = sb.claim_task(worker_id="w2", roles=["coder"])
        assert second["payload"]["cmd"] == "medium"

        third = sb.claim_task(worker_id="w3", roles=["coder"])
        assert third["payload"]["cmd"] == "low"

    def test_same_priority_fifo(self, sb: Switchboard):
        """Tasks with equal priority are FIFO (created_at ordering)."""
        sb.enqueue_task(role="coder", payload={"seq": 1}, priority=100)
        sb.enqueue_task(role="coder", payload={"seq": 2}, priority=100)
        sb.enqueue_task(role="coder", payload={"seq": 3}, priority=100)

        first = sb.claim_task(worker_id="w1", roles=["coder"])
        second = sb.claim_task(worker_id="w2", roles=["coder"])
        third = sb.claim_task(worker_id="w3", roles=["coder"])

        assert first["payload"]["seq"] == 1
        assert second["payload"]["seq"] == 2
        assert third["payload"]["seq"] == 3


# =========================================================================
# Role-scoped messaging
# =========================================================================


class TestRoleMessages:
    """Post and retrieve role-scoped messages."""

    def test_post_and_retrieve(self, sb: Switchboard):
        msg_id = sb.post_role_message("coders", "alice", {"text": "hello"})
        assert isinstance(msg_id, int)
        assert msg_id > 0

        messages = sb.get_role_messages("coders")
        assert len(messages) == 1
        assert messages[0]["sender"] == "alice"
        assert messages[0]["message"] == {"text": "hello"}

    def test_since_id_filters(self, sb: Switchboard):
        id1 = sb.post_role_message("coders", "alice", {"text": "first"})
        id2 = sb.post_role_message("coders", "bob", {"text": "second"})

        messages = sb.get_role_messages("coders", since_id=id1)
        assert len(messages) == 1
        assert messages[0]["sender"] == "bob"

    def test_different_channels_isolated(self, sb: Switchboard):
        sb.post_role_message("coders", "alice", {"text": "for coders"})
        sb.post_role_message("reviewers", "bob", {"text": "for reviewers"})

        coder_msgs = sb.get_role_messages("coders")
        reviewer_msgs = sb.get_role_messages("reviewers")
        assert len(coder_msgs) == 1
        assert len(reviewer_msgs) == 1
        assert coder_msgs[0]["sender"] == "alice"
        assert reviewer_msgs[0]["sender"] == "bob"

    def test_empty_channel_returns_empty_list(self, sb: Switchboard):
        messages = sb.get_role_messages("nonexistent")
        assert messages == []


# =========================================================================
# Complete / Fail lifecycle
# =========================================================================


class TestTaskLifecycle:
    """Complete and fail transitions."""

    def test_complete_task(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        claimed = sb.claim_task(worker_id="w1", roles=["coder"])
        ok = sb.complete_task(claimed["task_id"], "w1", {"output": "success"})
        assert ok is True

        # Task should not be claimable again
        assert sb.claim_task(worker_id="w2", roles=["coder"]) is None

    def test_fail_task(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        claimed = sb.claim_task(worker_id="w1", roles=["coder"])
        ok = sb.fail_task(claimed["task_id"], "w1", "timeout error")
        assert ok is True

        # Failed tasks are NOT re-queued automatically
        assert sb.claim_task(worker_id="w2", roles=["coder"]) is None

    def test_complete_wrong_worker_fails(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        claimed = sb.claim_task(worker_id="w1", roles=["coder"])
        ok = sb.complete_task(claimed["task_id"], "imposter", {"output": "hacked"})
        assert ok is False

    def test_renew_lease(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"cmd": "build"})
        claimed = sb.claim_task(worker_id="w1", roles=["coder"], lease_seconds=5)
        ok = sb.renew_lease(claimed["task_id"], "w1", lease_seconds=300)
        assert ok is True


# =========================================================================
# Stats
# =========================================================================


class TestStats:
    """Stats query returns accurate counts."""

    def test_stats_empty(self, sb: Switchboard):
        stats = sb.stats()
        assert stats["by_status"] == {}
        assert stats["by_role"] == {}
        assert stats["leased"] == []
        assert stats["role_message_count"] == 0

    def test_stats_after_operations(self, sb: Switchboard):
        sb.enqueue_task(role="coder", payload={"a": 1})
        sb.enqueue_task(role="coder", payload={"b": 2})
        sb.enqueue_task(role="reviewer", payload={"c": 3})
        sb.claim_task(worker_id="w1", roles=["coder"])
        sb.post_role_message("coders", "system", {"text": "go"})

        stats = sb.stats()
        assert stats["by_status"]["queued"] == 2
        assert stats["by_status"]["leased"] == 1
        assert stats["by_role"]["coder"] == 2
        assert stats["by_role"]["reviewer"] == 1
        assert stats["role_message_count"] == 1
        assert len(stats["leased"]) == 1

    def test_empty_role_raises(self, sb: Switchboard):
        with pytest.raises(ValueError, match="role is required"):
            sb.enqueue_task(role="", payload={"bad": True})
