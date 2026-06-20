"""Persistent alias registry — promotion candidates upgrade to named primitives.

The registry is the floating-tower mechanic in code. Workflow:

  1. Agent runs `geoseal route` repeatedly with the same dispatch shape.
  2. The promotion ledger counts recurrences (already shipped).
  3. Operator runs `geoseal promote --digest <hex> --as <name>`.
  4. The registry stores (alias -> op + tongue + default_args).
  5. Future invocations use `geoseal alias <name>` instead of full
     `--manual --op-name ... --dst-tongue ...`.

Default-args policy
-------------------
A promoted alias remembers the args it was promoted with. At invocation,
caller-supplied `--arg` flags override per-key; missing keys fall back
to the stored defaults. This makes aliases both fully-concrete (just
run them) and parameterisable (override args when the call differs).

Storage
-------
A single JSON file at `.scbe/route_aliases.json`. Atomic-write via
temp-file rename so a crashed promote can't corrupt the registry.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional

# ---------------------------------------------------------------------------
#  Monotonic creation-timestamp source
# ---------------------------------------------------------------------------
#
# `created_at_us` is both a human-facing wall-clock stamp and the sort key
# for `list_aliases()`. On coarse-resolution clocks (notably Windows, where
# `time.time()` granularity is ~15.6 ms) two registrations in quick
# succession — e.g. register -> unregister -> re-register the same name —
# can land on the *identical* microsecond value, making a freshly minted
# entry indistinguishable from the one it replaced. Guard against that by
# handing out strictly-increasing microsecond stamps: each new entry gets a
# value at least 1 us greater than the previous one, while still tracking
# real wall-clock time when the clock advances normally.

_ts_lock = threading.Lock()
_last_created_at_us = 0


def _next_created_at_us() -> int:
    """Return a strictly-increasing wall-clock microsecond timestamp.

    Thread-safe and monotonic per process, so back-to-back registrations
    never collide even on coarse-resolution system clocks.
    """
    global _last_created_at_us
    now = int(time.time() * 1_000_000)
    with _ts_lock:
        if now <= _last_created_at_us:
            now = _last_created_at_us + 1
        _last_created_at_us = now
        return now


# ---------------------------------------------------------------------------
#  Errors
# ---------------------------------------------------------------------------


class AliasError(Exception):
    """Base for registry refusals — operator-facing rather than wired
    into the QuarantineError funnel since aliasing is a CLI-time concern,
    not a routing-tier concern."""


class AliasNameError(AliasError):
    """Alias name is malformed, conflicts with a built-in subcommand,
    or is already in use."""


class AliasNotFoundError(AliasError):
    """Lookup / unregister target doesn't exist in the registry."""


# ---------------------------------------------------------------------------
#  Schema
# ---------------------------------------------------------------------------

ALIAS_SCHEMA_VERSION = "geoseal-aliases-v1"

# Alias names follow shell-friendly conventions: lowercase letters,
# digits, hyphens; must start with a letter to avoid colliding with
# argparse's leading-dash interpretation.
_ALIAS_NAME_RE = re.compile(r"^[a-z][a-z0-9\-]{0,63}$")

# Names reserved for built-in subcommands so a promotion can't shadow
# them. Keep this list in sync with geoseal_cli.py — checked at register time.
RESERVED_ALIAS_NAMES: frozenset = frozenset(
    {
        "alias",
        "aliases",
        "promote",
        "promotions",
        "unpromote",
        "route",
        "cross-build",
        "xb",
        "seal-here",
        "swarm-exec",
        "exec",
        "shell",
        "run",
        "swarm",
        "agent",
        "cursor",
        "ops",
        "emit",
        "seal",
        "verify",
        "history",
        "replay",
    }
)


@dataclass(frozen=True)
class AliasEntry:
    name: str
    op_name: str
    dst_tongue: str
    default_args: Dict[str, str]
    source_digest: str
    created_at_us: int
    promoted_from_count: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "op_name": self.op_name,
            "dst_tongue": self.dst_tongue,
            "default_args": dict(self.default_args),
            "source_digest": self.source_digest,
            "created_at_us": self.created_at_us,
            "promoted_from_count": self.promoted_from_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "AliasEntry":
        return cls(
            name=str(data["name"]),
            op_name=str(data["op_name"]),
            dst_tongue=str(data["dst_tongue"]),
            default_args=dict(data.get("default_args") or {}),
            source_digest=str(data["source_digest"]),
            created_at_us=int(data["created_at_us"]),
            promoted_from_count=int(data.get("promoted_from_count", 0)),
        )


# ---------------------------------------------------------------------------
#  Registry
# ---------------------------------------------------------------------------


@dataclass
class AliasRegistry:
    aliases: Dict[str, AliasEntry] = field(default_factory=dict)

    # ----- Validation ---------------------------------------------------

    @staticmethod
    def validate_name(name: str) -> None:
        if not isinstance(name, str) or not _ALIAS_NAME_RE.fullmatch(name):
            raise AliasNameError(
                f"alias name {name!r} must match {_ALIAS_NAME_RE.pattern} "
                "(lowercase letters/digits/hyphens, start with letter, max 64 chars)"
            )
        if name in RESERVED_ALIAS_NAMES:
            raise AliasNameError(
                f"alias name {name!r} collides with a built-in subcommand "
                f"(reserved: {sorted(RESERVED_ALIAS_NAMES)})"
            )

    # ----- CRUD ---------------------------------------------------------

    def register(
        self,
        name: str,
        *,
        op_name: str,
        dst_tongue: str,
        default_args: Optional[Mapping[str, str]] = None,
        source_digest: str,
        promoted_from_count: int = 0,
        overwrite: bool = False,
    ) -> AliasEntry:
        self.validate_name(name)
        if name in self.aliases and not overwrite:
            raise AliasNameError(f"alias {name!r} already exists; pass overwrite=True to replace")
        entry = AliasEntry(
            name=name,
            op_name=op_name,
            dst_tongue=dst_tongue.upper(),
            default_args=dict(default_args or {}),
            source_digest=source_digest,
            created_at_us=_next_created_at_us(),
            promoted_from_count=promoted_from_count,
        )
        self.aliases[name] = entry
        return entry

    def lookup(self, name: str) -> AliasEntry:
        if name not in self.aliases:
            raise AliasNotFoundError(f"no alias named {name!r}")
        return self.aliases[name]

    def unregister(self, name: str) -> AliasEntry:
        if name not in self.aliases:
            raise AliasNotFoundError(f"no alias named {name!r}")
        return self.aliases.pop(name)

    def list_aliases(self) -> List[AliasEntry]:
        return sorted(self.aliases.values(), key=lambda a: a.created_at_us)

    # ----- Persistence --------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "version": ALIAS_SCHEMA_VERSION,
            "aliases": {name: entry.to_dict() for name, entry in self.aliases.items()},
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "AliasRegistry":
        if not isinstance(data, Mapping):
            raise AliasError(f"alias registry root must be a JSON object, got {type(data).__name__}")
        version = data.get("version")
        if version != ALIAS_SCHEMA_VERSION:
            raise AliasError(
                f"unknown alias registry schema version: {version!r} " f"(expected {ALIAS_SCHEMA_VERSION})"
            )
        registry = cls()
        for name, entry_data in (data.get("aliases") or {}).items():
            registry.aliases[str(name)] = AliasEntry.from_dict(entry_data)
        return registry

    def save(self, path: Path) -> None:
        """Atomic write — writes to a temp file alongside the target then
        renames, so a crashed save can't corrupt the registry."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: Path) -> "AliasRegistry":
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AliasError(f"corrupt alias registry at {path}: {exc}") from exc
        return cls.from_dict(data)


# ---------------------------------------------------------------------------
#  Default registry path
# ---------------------------------------------------------------------------

DEFAULT_ALIAS_REGISTRY_PATH = Path(".scbe/route_aliases.json")


__all__ = [
    "ALIAS_SCHEMA_VERSION",
    "AliasEntry",
    "AliasError",
    "AliasNameError",
    "AliasNotFoundError",
    "AliasRegistry",
    "DEFAULT_ALIAS_REGISTRY_PATH",
    "RESERVED_ALIAS_NAMES",
]
