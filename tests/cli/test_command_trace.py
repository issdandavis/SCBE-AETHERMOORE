"""Tests for CLI command-trace deterministic capture and promotion ledger.

Three behaviours under test:
  * a `CommandTrace` round-trips through bijective input packets bit-perfect;
  * the digest is stable across timestamps but distinguishes argv/env/stdin;
  * the `PromotionLedger` correctly counts recurrences and surfaces
    candidates above its threshold.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from src.cli.command_trace import (
    CommandTrace,
    PromotionLedger,
    TRACE_VERSION,
    record_and_observe,
    record_session,
    trace_from_packets,
    trace_to_packets,
)

# ---------------------------------------------------------------------------
#  Recording
# ---------------------------------------------------------------------------


def test_record_session_filters_env_via_allowlist() -> None:
    env = {
        "PYTHONPATH": "/repo",
        "GEOSEAL_TIER": "keyed",
        "RANDOM_NOISE": "ignored",
        "PWD": "/tmp",
    }
    trace = record_session(["geoseal", "ops"], env=env)
    keys = {k for k, _ in trace.env}
    assert "PYTHONPATH" in keys
    assert "GEOSEAL_TIER" in keys
    assert "RANDOM_NOISE" not in keys
    assert "PWD" not in keys


def test_record_session_default_timestamp_is_monotonic_ish() -> None:
    a = record_session(["geoseal", "ops"])
    b = record_session(["geoseal", "ops"])
    assert b.timestamp_us >= a.timestamp_us


def test_record_session_with_explicit_timestamp() -> None:
    trace = record_session(["geoseal", "ops"], timestamp_us=12345)
    assert trace.timestamp_us == 12345


# ---------------------------------------------------------------------------
#  Canonical bytes + digest
# ---------------------------------------------------------------------------


def test_canonical_bytes_starts_with_version() -> None:
    trace = record_session(["geoseal", "ops"], timestamp_us=0)
    assert trace.canonical_bytes().startswith(TRACE_VERSION.encode("utf-8"))


def test_digest_is_stable_across_timestamps() -> None:
    """Two traces with same argv+env+stdin but different timestamps must
    produce identical digests — that's the recurrence-detection contract."""
    a = record_session(["geoseal", "ops"], timestamp_us=1)
    b = record_session(["geoseal", "ops"], timestamp_us=999_999)
    assert a.digest() == b.digest()


def test_digest_changes_when_argv_changes() -> None:
    a = record_session(["geoseal", "ops"], timestamp_us=0)
    b = record_session(["geoseal", "emit"], timestamp_us=0)
    assert a.digest() != b.digest()


def test_digest_changes_when_stdin_changes() -> None:
    a = record_session(["geoseal", "exec"], stdin=b"hello", timestamp_us=0)
    b = record_session(["geoseal", "exec"], stdin=b"world", timestamp_us=0)
    assert a.digest() != b.digest()


def test_digest_changes_when_env_changes() -> None:
    a = record_session(["geoseal", "ops"], env={"GEOSEAL_TIER": "public"}, timestamp_us=0)
    b = record_session(["geoseal", "ops"], env={"GEOSEAL_TIER": "keyed"}, timestamp_us=0)
    assert a.digest() != b.digest()


# ---------------------------------------------------------------------------
#  Bijective transport via input telemetry
# ---------------------------------------------------------------------------


def test_trace_round_trip_through_packets_text_argv() -> None:
    trace = record_session(
        ["geoseal", "swarm-exec", "--task", "add", "--args", '{"a":1,"b":2}'],
        env={"GEOSEAL_TIER": "keyed"},
        timestamp_us=42,
    )
    packets = trace_to_packets(trace)
    assert packets, "encoder must produce at least one packet"
    decoded = trace_from_packets(packets)
    assert decoded.argv == trace.argv
    assert decoded.stdin == trace.stdin
    assert decoded.env == trace.env
    assert decoded.timestamp_us == trace.timestamp_us


def test_trace_round_trip_with_binary_stdin() -> None:
    """stdin may contain LF or NUL bytes — those must survive the
    canonical-bytes layout because the parser counts header lines, not splits."""
    blob = b"line1\nline2\x00\x01\xff\xfe\n"
    trace = record_session(["geoseal", "exec"], stdin=blob, timestamp_us=7)
    decoded = trace_from_packets(trace_to_packets(trace))
    assert decoded.stdin == blob


def test_trace_round_trip_with_unicode_argv() -> None:
    trace = record_session(["geoseal", "agent", "Kor'aelin"], timestamp_us=0)
    decoded = trace_from_packets(trace_to_packets(trace))
    assert decoded.argv == ("geoseal", "agent", "Kor'aelin")


def test_trace_packets_are_pure_av_channel() -> None:
    """KeyEvents default to the AV (Avali) tongue — symbolic channel."""
    trace = record_session(["geoseal", "ops"], timestamp_us=0)
    packets = trace_to_packets(trace)
    tongues = {tongue for tongue, _ in packets}
    assert tongues == {"av"}


def test_parse_canonical_rejects_bad_version() -> None:
    bad = b"not-the-trace-version\n0\n[]\n{}\n"
    with pytest.raises(ValueError, match="unknown trace version"):
        from src.cli.command_trace import _parse_canonical  # noqa: PLC0415

        _parse_canonical(bad)


def test_parse_canonical_rejects_truncated_header() -> None:
    bad = TRACE_VERSION.encode("utf-8") + b"\n0\n[]\n"  # only 3 lines, need 4
    with pytest.raises(ValueError, match="malformed trace header"):
        from src.cli.command_trace import _parse_canonical  # noqa: PLC0415

        _parse_canonical(bad)


# ---------------------------------------------------------------------------
#  Promotion ledger
# ---------------------------------------------------------------------------


def test_ledger_counts_repeated_invocations() -> None:
    ledger = PromotionLedger(threshold=3)
    for _ in range(5):
        record_and_observe(["geoseal", "ops"], ledger)
    digests = list(ledger.entries.keys())
    assert len(digests) == 1
    assert ledger.entries[digests[0]].count == 5


def test_ledger_threshold_gates_candidates() -> None:
    ledger = PromotionLedger(threshold=3)
    # twice — below threshold
    for _ in range(2):
        record_and_observe(["geoseal", "ops"], ledger)
    assert ledger.candidates() == []
    # third invocation crosses
    record_and_observe(["geoseal", "ops"], ledger)
    candidates = ledger.candidates()
    assert len(candidates) == 1
    assert candidates[0].sample_argv == ("geoseal", "ops")
    assert candidates[0].count == 3


def test_ledger_separates_distinct_invocation_patterns() -> None:
    ledger = PromotionLedger(threshold=2)
    for _ in range(3):
        record_and_observe(["geoseal", "ops"], ledger)
    for _ in range(2):
        record_and_observe(["geoseal", "emit"], ledger)
    candidates = ledger.candidates()
    # both patterns crossed threshold of 2
    assert len(candidates) == 2
    counts = sorted(e.count for e in candidates)
    assert counts == [2, 3]


def test_ledger_candidates_sorted_by_count_descending() -> None:
    ledger = PromotionLedger(threshold=1)
    record_and_observe(["geoseal", "rare"], ledger)
    for _ in range(5):
        record_and_observe(["geoseal", "common"], ledger)
    for _ in range(2):
        record_and_observe(["geoseal", "moderate"], ledger)
    counts = [e.count for e in ledger.candidates()]
    assert counts == [5, 2, 1]


def test_ledger_jsonl_round_trip(tmp_path: Path) -> None:
    ledger = PromotionLedger(threshold=2)
    for _ in range(4):
        record_and_observe(["geoseal", "ops"], ledger)
    record_and_observe(["geoseal", "emit"], ledger)

    path = tmp_path / "ledger.jsonl"
    ledger.save(path)
    assert path.exists()

    reloaded = PromotionLedger.load(path, threshold=2)
    assert set(reloaded.entries.keys()) == set(ledger.entries.keys())
    assert reloaded.candidates()[0].count == 4


def test_ledger_load_missing_file_returns_empty() -> None:
    ledger = PromotionLedger.load(Path("/tmp/nonexistent_ledger_xyz.jsonl"), threshold=2)
    assert ledger.entries == {}


# ---------------------------------------------------------------------------
#  End-to-end: record → packetize → recurrence detection
# ---------------------------------------------------------------------------


def test_recurrent_invocations_from_replayed_packets_are_counted() -> None:
    """Realistic agentic-ops loop: agent A records a session, encodes it as
    bijective packets and ships to agent B. Agent B replays. The replay
    should land in the same digest bucket as the original."""
    ledger = PromotionLedger(threshold=2)

    # Agent A's session
    trace_a = record_session(["geoseal", "swarm-exec", "--task", "add"], timestamp_us=100)
    packets = trace_to_packets(trace_a)

    # Agent B receives and replays
    trace_b = trace_from_packets(packets)

    ledger.observe(trace_a)
    ledger.observe(trace_b)

    # Both should be the same digest (timestamp difference is fine — it's
    # filtered out of the digest input).
    assert trace_a.digest() == trace_b.digest()
    candidates = ledger.candidates()
    assert len(candidates) == 1
    assert candidates[0].count == 2
