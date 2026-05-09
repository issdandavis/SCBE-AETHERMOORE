"""Deterministic CLI session capture, replay, and digest-based promotion.

A `CommandTrace` is a tuple of (argv, stdin_bytes, env_subset, timestamp_us)
serialised as a single byte stream and pushed through the bijective input
tokenizer. Two consequences:

  * **Replay** — the byte stream decodes back to the same argv+stdin, so
    one agent's CLI invocation is re-runnable verbatim by another.
  * **Promotion** — `trace.digest()` is a SHA-256 over the canonical bytes.
    A `PromotionLedger` counts how often each digest recurs across sessions;
    when a count crosses a threshold, the trace is a candidate for being
    registered as a named subcommand. That's the floating-tower mechanic:
    the CLI grows new primitives from agent usage, not from a release.

What this is NOT
----------------
This is a transport-and-recognition layer. It does not execute commands
(call out to subprocess.run yourself), it does not enforce policy (the
SCBE governance gate is a separate concern), and it is not a shell history
replacement (geoseal already has a per-call ledger; this is a complementary
deterministic-replay surface).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from src.input.bijective_input import (
    KeyAction,
    KeyEvent,
    decode_trace,
    encode_trace,
)

# ---------------------------------------------------------------------------
#  Schema
# ---------------------------------------------------------------------------

# Canonical-bytes layout (UTF-8, line-delimited):
#   line 0   "geoseal-cmd-trace/v1"
#   line 1   timestamp_us (decimal int)
#   line 2   argv as JSON array (preserves order + exact strings)
#   line 3   env subset as JSON object (sorted keys, only allow-listed keys)
#   line 4+  stdin payload, raw bytes after the LF
#
# We split off stdin so binary content survives without escaping, but keep
# header lines as UTF-8 JSON for readability when humans grep .scbe/.

TRACE_VERSION = "geoseal-cmd-trace/v1"

# By default, copy only env keys that are likely to alter command behaviour.
# This stops PWD / TERM / random session noise from polluting the digest.
DEFAULT_ENV_ALLOWLIST: Tuple[str, ...] = (
    "GEOSEAL_AUDIT_SECRET",
    "GEOSEAL_TIER",
    "PYTHONPATH",
    "SCBE_TONGUE",
    "SCBE_RUNTIME",
)


@dataclass(frozen=True)
class CommandTrace:
    argv: Tuple[str, ...]
    stdin: bytes
    env: Tuple[Tuple[str, str], ...]  # sorted, allow-listed
    timestamp_us: int

    def canonical_bytes(self) -> bytes:
        header = "\n".join(
            [
                TRACE_VERSION,
                str(self.timestamp_us),
                json.dumps(list(self.argv), ensure_ascii=False),
                json.dumps(dict(self.env), ensure_ascii=False, sort_keys=True),
            ]
        ).encode("utf-8")
        return header + b"\n" + self.stdin

    def digest(self) -> str:
        """Stable SHA-256 over the *content* (argv + env + stdin), not timing.

        Timing varies from session to session; the digest is meant to recognise
        repeated *intent*, so we hash a trimmed payload that drops timestamp.
        """
        body = json.dumps(
            {
                "argv": list(self.argv),
                "env": dict(self.env),
                "stdin_sha256": hashlib.sha256(self.stdin).hexdigest(),
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(body).hexdigest()


# ---------------------------------------------------------------------------
#  Recording
# ---------------------------------------------------------------------------


def record_session(
    argv: Sequence[str],
    *,
    stdin: bytes = b"",
    env: Optional[Mapping[str, str]] = None,
    env_allowlist: Sequence[str] = DEFAULT_ENV_ALLOWLIST,
    timestamp_us: Optional[int] = None,
) -> CommandTrace:
    """Capture a CLI invocation as a `CommandTrace`.

    Pass `env=os.environ` from the caller; we filter via the allowlist so
    the digest stays stable across machines.
    """
    if timestamp_us is None:
        timestamp_us = int(time.time() * 1_000_000)
    env = env or {}
    filtered = tuple(sorted((k, env[k]) for k in env_allowlist if k in env))
    return CommandTrace(
        argv=tuple(argv),
        stdin=bytes(stdin),
        env=filtered,
        timestamp_us=timestamp_us,
    )


# ---------------------------------------------------------------------------
#  Bijective transport via input telemetry
# ---------------------------------------------------------------------------


def trace_to_packets(trace: CommandTrace) -> List[Tuple[str, List[str]]]:
    """Serialise a trace as bijective key-event packets (one packet per byte).

    The bijective_input layer is byte-perfect, so this round-trips exactly.
    We use KeyEvents because argv is symbolic — the AV (Avali) tongue is
    the canonical channel for symbolic transport.
    """
    canonical = trace.canonical_bytes()
    events = [
        KeyEvent(
            timestamp_us=trace.timestamp_us + i,
            keycode=byte,
            action=KeyAction.DOWN,
        )
        for i, byte in enumerate(canonical)
    ]
    return encode_trace(events)


def trace_from_packets(packets: Sequence[Tuple[str, Sequence[str]]]) -> CommandTrace:
    """Inverse of `trace_to_packets`. Empty packet list returns an empty trace."""
    events = decode_trace(packets)
    canonical = bytes(ev.keycode for ev in events if isinstance(ev, KeyEvent))
    return _parse_canonical(canonical)


def _parse_canonical(blob: bytes) -> CommandTrace:
    if not blob:
        raise ValueError("empty canonical blob")
    # Split off the four header lines from the stdin tail. The stdin payload
    # may contain arbitrary bytes including LF, so we partition by line count
    # rather than splitlines().
    parts: List[bytes] = []
    cursor = 0
    for _ in range(4):
        nl = blob.find(b"\n", cursor)
        if nl < 0:
            raise ValueError("malformed trace header — too few lines")
        parts.append(blob[cursor:nl])
        cursor = nl + 1
    stdin = blob[cursor:]

    version = parts[0].decode("utf-8")
    if version != TRACE_VERSION:
        raise ValueError(f"unknown trace version: {version!r}")

    timestamp_us = int(parts[1].decode("utf-8"))
    argv = tuple(json.loads(parts[2].decode("utf-8")))
    env_dict = json.loads(parts[3].decode("utf-8"))
    env = tuple(sorted((k, v) for k, v in env_dict.items()))
    return CommandTrace(argv=argv, stdin=stdin, env=env, timestamp_us=timestamp_us)


# ---------------------------------------------------------------------------
#  Promotion ledger — the floating-tower mechanic
# ---------------------------------------------------------------------------


@dataclass
class PromotionEntry:
    digest: str
    count: int
    first_seen_us: int
    last_seen_us: int
    sample_argv: Tuple[str, ...]


@dataclass
class PromotionLedger:
    """Counts trace recurrences. When a digest crosses `threshold`, the trace
    is reported as a *candidate* — actual subcommand registration is the
    operator's call, this just surfaces what's worth promoting."""

    threshold: int = 3
    entries: dict = field(default_factory=dict)  # digest -> PromotionEntry

    def observe(self, trace: CommandTrace) -> PromotionEntry:
        d = trace.digest()
        existing = self.entries.get(d)
        if existing is None:
            entry = PromotionEntry(
                digest=d,
                count=1,
                first_seen_us=trace.timestamp_us,
                last_seen_us=trace.timestamp_us,
                sample_argv=trace.argv,
            )
            self.entries[d] = entry
            return entry
        existing.count += 1
        existing.last_seen_us = max(existing.last_seen_us, trace.timestamp_us)
        return existing

    def candidates(self) -> List[PromotionEntry]:
        """Return entries that have crossed the promotion threshold,
        sorted by recurrence count descending."""
        return sorted(
            [e for e in self.entries.values() if e.count >= self.threshold],
            key=lambda e: e.count,
            reverse=True,
        )

    def to_jsonl(self) -> str:
        """Serialise the ledger as one JSON object per line."""
        return "\n".join(
            json.dumps(
                {
                    "digest": e.digest,
                    "count": e.count,
                    "first_seen_us": e.first_seen_us,
                    "last_seen_us": e.last_seen_us,
                    "sample_argv": list(e.sample_argv),
                }
            )
            for e in self.entries.values()
        )

    @classmethod
    def from_jsonl(cls, text: str, threshold: int = 3) -> "PromotionLedger":
        ledger = cls(threshold=threshold)
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ledger.entries[row["digest"]] = PromotionEntry(
                digest=row["digest"],
                count=int(row["count"]),
                first_seen_us=int(row["first_seen_us"]),
                last_seen_us=int(row["last_seen_us"]),
                sample_argv=tuple(row["sample_argv"]),
            )
        return ledger

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_jsonl(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, threshold: int = 3) -> "PromotionLedger":
        path = Path(path)
        if not path.exists():
            return cls(threshold=threshold)
        return cls.from_jsonl(path.read_text(encoding="utf-8"), threshold=threshold)


# ---------------------------------------------------------------------------
#  Convenience: end-to-end record + observe
# ---------------------------------------------------------------------------


def record_and_observe(
    argv: Sequence[str],
    ledger: PromotionLedger,
    *,
    stdin: bytes = b"",
    env: Optional[Mapping[str, str]] = None,
) -> Tuple[CommandTrace, PromotionEntry]:
    trace = record_session(argv, stdin=stdin, env=env)
    entry = ledger.observe(trace)
    return trace, entry


__all__ = [
    "CommandTrace",
    "DEFAULT_ENV_ALLOWLIST",
    "PromotionEntry",
    "PromotionLedger",
    "TRACE_VERSION",
    "record_and_observe",
    "record_session",
    "trace_from_packets",
    "trace_to_packets",
]
