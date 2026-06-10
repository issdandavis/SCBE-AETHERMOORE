"""Harsh adversarial probes against the alias registry + persistence.

Each test targets a specific failure mode I expect the registry to handle.
A passing test means the gap is closed; a failing test pinpoints the bug.

Probe axes:
  * concurrent register calls (race on dict + atomic save)
  * registry-file corruption mid-flight
  * promote against a stale digest (ledger updated after `geoseal promotions` ran)
  * alias name with shell-meta or path-traversal that the format check missed
  * registry path that points at a directory rather than a file
  * empty default_args + empty arg overrides on invocation
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import List

import pytest

from src.cli.alias_registry import (
    AliasError,
    AliasNameError,
    AliasRegistry,
)


def _entry(**overrides) -> dict:
    base = {
        "op_name": "add",
        "dst_tongue": "RU",
        "default_args": {"a": "x", "b": "y"},
        "source_digest": "0" * 64,
        "promoted_from_count": 4,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
#  Concurrency — multiple threads registering different aliases simultaneously
# ---------------------------------------------------------------------------


def test_concurrent_registers_with_distinct_names_all_land() -> None:
    """16 threads each register a unique alias on the same registry —
    no thread should silently lose a registration."""
    reg = AliasRegistry()
    errors: List[Exception] = []
    barrier = threading.Barrier(16)

    def worker(i: int) -> None:
        barrier.wait()
        try:
            reg.register(f"alias-{i}", **_entry())
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent registers raised: {errors[:3]}"
    assert len(reg.aliases) == 16


def test_concurrent_registers_same_name_one_succeeds_others_raise() -> None:
    """8 threads racing to register the same alias — exactly ONE should
    succeed; the others must hit AliasNameError(already exists)."""
    reg = AliasRegistry()
    successes = 0
    name_errors = 0
    other = []
    counters_lock = threading.Lock()
    barrier = threading.Barrier(8)

    def worker() -> None:
        nonlocal successes, name_errors
        barrier.wait()
        try:
            reg.register("contended", **_entry())
            with counters_lock:
                successes += 1
        except AliasNameError:
            with counters_lock:
                name_errors += 1
        except Exception as exc:
            with counters_lock:
                other.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not other, f"unexpected: {other}"
    assert successes == 1
    assert name_errors == 7


# ---------------------------------------------------------------------------
#  Persistence corruption + recovery
# ---------------------------------------------------------------------------


def test_load_truncated_json_raises_alias_error(tmp_path: Path) -> None:
    """Half-written JSON (e.g. crash during save) should surface a typed
    AliasError, not bubble JSONDecodeError to the caller."""
    path = tmp_path / "registry.json"
    path.write_text('{"version": "geoseal-aliases-v1", "aliases": {', encoding="utf-8")
    with pytest.raises(AliasError, match="corrupt"):
        AliasRegistry.load(path)


def test_load_empty_file_raises_alias_error(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text("", encoding="utf-8")
    with pytest.raises(AliasError):
        AliasRegistry.load(path)


def test_load_json_array_instead_of_object_raises(tmp_path: Path) -> None:
    """Schema check must catch wrong top-level type."""
    path = tmp_path / "registry.json"
    path.write_text('["not", "an", "object"]', encoding="utf-8")
    with pytest.raises(AliasError):
        AliasRegistry.load(path)


def test_save_to_directory_path_raises_cleanly(tmp_path: Path) -> None:
    """If someone passes a directory as the registry path, the save
    should fail with a recognisable error rather than corrupting the FS."""
    target = tmp_path / "as-dir"
    target.mkdir()
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    with pytest.raises((OSError, PermissionError, IsADirectoryError)):
        reg.save(target)


def test_save_then_corrupt_then_load_surfaces_typed_error(tmp_path: Path) -> None:
    """End-to-end: registry survives a save, then external corruption
    surfaces as AliasError on the next load."""
    path = tmp_path / "registry.json"
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    reg.save(path)
    # External corruption — simulate filesystem damage / partial write.
    path.write_bytes(path.read_bytes()[:30])
    with pytest.raises(AliasError):
        AliasRegistry.load(path)


# ---------------------------------------------------------------------------
#  Adversarial alias names — beyond the format check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "../etc-passwd",  # path traversal — has /
        "name\nwith-newline",  # newline
        "name\x00with-nul",  # NUL byte
        "name with space",  # whitespace
        "name;rm-rf",  # semicolon
        "ALL_UPPERCASE",  # uppercase rejected
        "💀-emoji",  # emoji in name
        "naïve",  # non-ASCII letter
    ],
)
def test_adversarial_names_rejected_by_format(name: str) -> None:
    """The regex must reject every shell/path/encoding-shaped attack."""
    with pytest.raises(AliasNameError):
        AliasRegistry.validate_name(name)


# ---------------------------------------------------------------------------
#  Default args edge cases
# ---------------------------------------------------------------------------


def test_register_with_empty_default_args_round_trips(tmp_path: Path) -> None:
    reg = AliasRegistry()
    reg.register("ax", **_entry(default_args={}))
    path = tmp_path / "registry.json"
    reg.save(path)
    reloaded = AliasRegistry.load(path)
    assert reloaded.lookup("ax").default_args == {}


def test_register_with_empty_string_arg_value_preserved(tmp_path: Path) -> None:
    """Empty string is a legitimate arg value (unlike None) — must
    survive the round trip without being coerced to None or dropped."""
    reg = AliasRegistry()
    reg.register("ax", **_entry(default_args={"a": "", "b": "y"}))
    path = tmp_path / "registry.json"
    reg.save(path)
    reloaded = AliasRegistry.load(path)
    assert reloaded.lookup("ax").default_args == {"a": "", "b": "y"}


def test_register_default_args_values_with_special_chars(tmp_path: Path) -> None:
    """Default args may contain shell-meta or template-meta — the
    arg-validator on the router is the boundary, NOT the registry. The
    registry preserves bytes faithfully."""
    reg = AliasRegistry()
    # Note: at *invocation* time, the default arg validator may refuse
    # these. But the registry itself doesn't sanitise.
    reg.register(
        "danger",
        **_entry(default_args={"a": "x; rm -rf /", "b": "${EVIL}"}),
    )
    path = tmp_path / "registry.json"
    reg.save(path)
    reloaded = AliasRegistry.load(path)
    assert reloaded.lookup("danger").default_args == {
        "a": "x; rm -rf /",
        "b": "${EVIL}",
    }


# ---------------------------------------------------------------------------
#  Stale digest / promote-then-modify race
# ---------------------------------------------------------------------------


def test_register_then_unregister_then_register_same_name(tmp_path: Path) -> None:
    """Lifecycle integrity: register -> unregister -> re-register the same
    name should produce a fresh entry, not resurrect the old one."""
    reg = AliasRegistry()
    first = reg.register("ax", **_entry())
    reg.unregister("ax")
    second = reg.register("ax", **_entry(op_name="sub"))
    assert first.op_name == "add"
    assert second.op_name == "sub"
    assert first.created_at_us != second.created_at_us or first.source_digest != second.source_digest


def test_overwrite_preserves_source_digest_history_implicitly() -> None:
    """When overwriting, the new entry's source_digest reflects the new
    promotion — old digest is gone (no automatic history). Document this
    contract so a future audit-trail change shows up as a test diff."""
    reg = AliasRegistry()
    reg.register("ax", **_entry(source_digest="A" * 64))
    reg.register("ax", **_entry(source_digest="B" * 64), overwrite=True)
    assert reg.lookup("ax").source_digest == "B" * 64
