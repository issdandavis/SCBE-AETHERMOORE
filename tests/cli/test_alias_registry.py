"""Tests for the alias registry — the floating-tower data structure.

Module-level tests cover register/lookup/unregister/persist + the
validation rules (reserved names, format, overwrite policy). CLI-level
tests live in test_promote_cli.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.cli.alias_registry import (
    ALIAS_SCHEMA_VERSION,
    AliasEntry,
    AliasError,
    AliasNameError,
    AliasNotFoundError,
    AliasRegistry,
    RESERVED_ALIAS_NAMES,
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
#  Name validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "add-ru",  # canonical
        "ax",  # short
        "tongue-broadcast-1",  # digits permitted
        "a" + ("a" * 63),  # max length
    ],
)
def test_valid_alias_names_accepted(name: str) -> None:
    AliasRegistry.validate_name(name)  # no raise


@pytest.mark.parametrize(
    "name",
    [
        "",  # empty
        "1add",  # starts with digit
        "-add",  # starts with dash
        "Add",  # uppercase
        "add_ru",  # underscore not in pattern
        "add ru",  # whitespace
        "add!",  # punctuation
        "a" * 65,  # too long
    ],
)
def test_malformed_alias_names_rejected(name: str) -> None:
    with pytest.raises(AliasNameError, match="must match"):
        AliasRegistry.validate_name(name)


@pytest.mark.parametrize("name", sorted(RESERVED_ALIAS_NAMES))
def test_reserved_names_rejected(name: str) -> None:
    with pytest.raises(AliasNameError, match="reserved"):
        AliasRegistry.validate_name(name)


# ---------------------------------------------------------------------------
#  CRUD
# ---------------------------------------------------------------------------


def test_register_returns_entry_with_provenance() -> None:
    reg = AliasRegistry()
    entry = reg.register("ax", **_entry())
    assert isinstance(entry, AliasEntry)
    assert entry.name == "ax"
    assert entry.op_name == "add"
    assert entry.dst_tongue == "RU"
    assert entry.default_args == {"a": "x", "b": "y"}
    assert entry.source_digest == "0" * 64
    assert entry.promoted_from_count == 4
    assert entry.created_at_us > 0


def test_register_normalises_dst_tongue_to_upper() -> None:
    reg = AliasRegistry()
    entry = reg.register("ax", **_entry(dst_tongue="ru"))
    assert entry.dst_tongue == "RU"


def test_register_duplicate_without_overwrite_raises() -> None:
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    with pytest.raises(AliasNameError, match="already exists"):
        reg.register("ax", **_entry())


def test_register_duplicate_with_overwrite_replaces() -> None:
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    new_entry = reg.register("ax", **_entry(op_name="sub"), overwrite=True)
    assert new_entry.op_name == "sub"
    assert reg.lookup("ax").op_name == "sub"


def test_lookup_missing_alias_raises() -> None:
    reg = AliasRegistry()
    with pytest.raises(AliasNotFoundError, match="no alias"):
        reg.lookup("nope")


def test_unregister_returns_removed_entry() -> None:
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    removed = reg.unregister("ax")
    assert removed.name == "ax"
    assert "ax" not in reg.aliases


def test_unregister_missing_raises() -> None:
    reg = AliasRegistry()
    with pytest.raises(AliasNotFoundError):
        reg.unregister("nope")


def test_list_aliases_sorted_by_creation() -> None:
    reg = AliasRegistry()
    reg.register("first", **_entry())
    reg.register("second", **_entry(op_name="sub"))
    listing = reg.list_aliases()
    assert [e.name for e in listing] == ["first", "second"]


# ---------------------------------------------------------------------------
#  Persistence
# ---------------------------------------------------------------------------


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    reg.register("mul-ko", **_entry(op_name="mul", dst_tongue="KO"))
    path = tmp_path / "registry.json"
    reg.save(path)
    assert path.exists()
    reloaded = AliasRegistry.load(path)
    assert set(reloaded.aliases.keys()) == {"ax", "mul-ko"}
    assert reloaded.lookup("mul-ko").op_name == "mul"


def test_save_writes_known_schema_version(tmp_path: Path) -> None:
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    path = tmp_path / "registry.json"
    reg.save(path)
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["version"] == ALIAS_SCHEMA_VERSION


def test_save_is_atomic_via_temp_rename(tmp_path: Path) -> None:
    """A second save shouldn't leave a stray .tmp file behind."""
    reg = AliasRegistry()
    reg.register("ax", **_entry())
    path = tmp_path / "registry.json"
    reg.save(path)
    reg.register("by", **_entry(op_name="sub"))
    reg.save(path)
    # No leftover temp files.
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_load_missing_file_returns_empty_registry(tmp_path: Path) -> None:
    reg = AliasRegistry.load(tmp_path / "nonexistent.json")
    assert reg.aliases == {}


def test_load_corrupt_file_raises_alias_error(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(AliasError, match="corrupt"):
        AliasRegistry.load(path)


def test_load_unknown_schema_version_raises(tmp_path: Path) -> None:
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps({"version": "geoseal-aliases-vX", "aliases": {}}),
        encoding="utf-8",
    )
    with pytest.raises(AliasError, match="schema version"):
        AliasRegistry.load(path)


# ---------------------------------------------------------------------------
#  Entry serialisation
# ---------------------------------------------------------------------------


def test_entry_round_trip_through_dict() -> None:
    reg = AliasRegistry()
    original = reg.register("ax", **_entry())
    data = original.to_dict()
    rebuilt = AliasEntry.from_dict(data)
    assert rebuilt == original


def test_from_dict_tolerates_missing_default_args() -> None:
    """Old snapshots without `default_args` should still load."""
    rebuilt = AliasEntry.from_dict(
        {
            "name": "ax",
            "op_name": "add",
            "dst_tongue": "RU",
            "source_digest": "0" * 64,
            "created_at_us": 0,
        }
    )
    assert rebuilt.default_args == {}
