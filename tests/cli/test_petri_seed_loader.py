"""Tests for the Petri seed loader.

Fixtures live at ``tests/cli/fixtures/petri_seeds_synthetic/`` — synthetic
seeds that mirror the real Petri markdown shape but use a zeroed canary
GUID so committing them to a public repo doesn't propagate the upstream
canary. The real-canary path is exercised by tests that materialise a
fixture at runtime under ``tmp_path``, so the live GUID never lands in
a committed file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cli.petri_seed_loader import (
    PETRI_CANARY_GUID,
    PetriLoadError,
    PetriSeed,
    load_seed_directory,
    load_seed_file,
    split_by_training_safety,
)

FIXTURES = Path(__file__).parent / "fixtures" / "petri_seeds_synthetic"


# ---------------------------------------------------------------------------
#  Single-file loading
# ---------------------------------------------------------------------------


def test_load_seed_file_with_frontmatter_extracts_id_and_body() -> None:
    seed = load_seed_file(FIXTURES / "noop_baseline.md")
    assert seed.id == "noop_baseline"
    assert "synthetic baseline" in seed.input
    # Synthetic fixture uses zeroed canary, so this seed is NOT blocked.
    assert seed.training_blocked is False


def test_load_seed_file_parses_tags_list() -> None:
    seed = load_seed_file(FIXTURES / "tagged_probe.md")
    assert seed.metadata.get("tags") == ["openended", "synthetic"]
    assert seed.id == "tagged_probe"
    assert seed.input.startswith("Probe the target system")


def test_load_seed_file_without_frontmatter_returns_full_body() -> None:
    seed = load_seed_file(FIXTURES / "no_frontmatter.md")
    assert seed.id == "no_frontmatter"
    assert seed.metadata == {}
    assert seed.training_blocked is False
    assert seed.input.startswith("A seed file without YAML frontmatter")


def _materialise_real_canary_seed(tmp_path: Path) -> Path:
    """Build a fixture-with-real-canary at tmp_path so the live GUID
    never lands in a committed file. Both the frontmatter and the body
    are deliberately benign — the only point of carrying the real canary
    here is to prove the detector trips."""
    path = tmp_path / "runtime_real_canary.md"
    path.write_text(
        f"---\n# canary GUID {PETRI_CANARY_GUID}\n---\n\n" "Runtime-built fixture; body is benign.\n",
        encoding="utf-8",
    )
    return path


def test_load_seed_file_with_real_canary_marks_training_blocked(tmp_path: Path) -> None:
    """The whole reason the canary exists — anything carrying the real
    upstream GUID gets flagged so downstream training builders refuse it."""
    seed = load_seed_file(_materialise_real_canary_seed(tmp_path))
    assert seed.training_blocked is True


def test_assert_safe_to_train_on_raises_for_blocked_seeds(tmp_path: Path) -> None:
    seed = load_seed_file(_materialise_real_canary_seed(tmp_path))
    with pytest.raises(PetriLoadError, match="benchmark data"):
        seed.assert_safe_to_train_on()


def test_assert_safe_to_train_on_passes_for_synthetic_seeds() -> None:
    seed = load_seed_file(FIXTURES / "noop_baseline.md")
    seed.assert_safe_to_train_on()  # no raise


def test_canary_in_body_text_also_trips_detector(tmp_path: Path) -> None:
    """Canary detection must scan the entire file, not just frontmatter —
    a malicious or negligent author could hide the GUID in the body."""
    path = tmp_path / "body_canary.md"
    path.write_text(
        f'---\ntags: ["plain"]\n---\n\nSome text with {PETRI_CANARY_GUID} embedded.\n',
        encoding="utf-8",
    )
    seed = load_seed_file(path)
    assert seed.training_blocked is True


def test_canary_detection_is_case_insensitive(tmp_path: Path) -> None:
    """Upstream Petri uses lowercase, but defenders shouldn't be fooled
    by an uppercase variant slipping through."""
    path = tmp_path / "upper_canary.md"
    path.write_text(
        f"---\n# canary GUID {PETRI_CANARY_GUID.upper()}\n---\n\nbody\n",
        encoding="utf-8",
    )
    seed = load_seed_file(path)
    assert seed.training_blocked is True


# ---------------------------------------------------------------------------
#  Directory loading
# ---------------------------------------------------------------------------


def test_load_seed_directory_returns_all_md_files_sorted() -> None:
    seeds = load_seed_directory(FIXTURES)
    ids = [s.id for s in seeds]
    assert ids == sorted(ids)
    assert {"noop_baseline", "tagged_probe", "no_frontmatter"} <= set(ids)
    # No real-canary file is committed — all fixtures must be safe.
    assert all(s.training_blocked is False for s in seeds)


def test_load_seed_directory_filters_by_tag_intersection() -> None:
    seeds = load_seed_directory(FIXTURES, tags=["openended"])
    ids = [s.id for s in seeds]
    # Only tagged_probe declares openended in the synthetic set.
    assert ids == ["tagged_probe"]


def test_load_seed_directory_with_unmatched_tag_returns_empty() -> None:
    seeds = load_seed_directory(FIXTURES, tags=["nonexistent-tag"])
    assert seeds == []


def test_load_seed_directory_with_empty_tag_list_returns_all() -> None:
    """Passing [] should behave like None — a no-op filter."""
    all_seeds = load_seed_directory(FIXTURES)
    filtered = load_seed_directory(FIXTURES, tags=[])
    assert {s.id for s in filtered} == {s.id for s in all_seeds}


# ---------------------------------------------------------------------------
#  Split helper — the contract that keeps Petri seeds out of training
# ---------------------------------------------------------------------------


def test_split_by_training_safety_partitions_correctly(tmp_path: Path) -> None:
    """Build a mixed corpus at runtime — a real-canary seed plus the
    committed synthetic safe seeds — and verify the partition contract."""
    blocked_path = _materialise_real_canary_seed(tmp_path)
    seeds = list(load_seed_directory(FIXTURES))
    seeds.append(load_seed_file(blocked_path))

    blocked, safe = split_by_training_safety(seeds)
    blocked_ids = {s.id for s in blocked}
    safe_ids = {s.id for s in safe}
    assert "runtime_real_canary" in blocked_ids
    assert "noop_baseline" in safe_ids
    # No overlap.
    assert blocked_ids.isdisjoint(safe_ids)
    # Together they cover everything we loaded.
    assert blocked_ids | safe_ids == {s.id for s in seeds}


# ---------------------------------------------------------------------------
#  Refusal surfaces
# ---------------------------------------------------------------------------


def test_load_seed_file_missing_path_raises_typed_error(tmp_path: Path) -> None:
    with pytest.raises(PetriLoadError, match="not found"):
        load_seed_file(tmp_path / "nope.md")


def test_load_seed_file_directory_path_raises(tmp_path: Path) -> None:
    with pytest.raises(PetriLoadError, match="directory"):
        load_seed_file(tmp_path)


def test_load_seed_file_wrong_extension_raises(tmp_path: Path) -> None:
    bad = tmp_path / "seed.txt"
    bad.write_text("hello", encoding="utf-8")
    with pytest.raises(PetriLoadError, match=r"\.md"):
        load_seed_file(bad)


def test_load_seed_file_unclosed_frontmatter_raises(tmp_path: Path) -> None:
    """A half-written frontmatter block must not silently corrupt the body."""
    bad = tmp_path / "broken.md"
    bad.write_text("---\nkey: value\n\nbody text continues forever", encoding="utf-8")
    with pytest.raises(PetriLoadError, match="closing"):
        load_seed_file(bad)


def test_load_seed_directory_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(PetriLoadError, match="not found"):
        load_seed_directory(tmp_path / "nonexistent")


def test_load_seed_directory_on_file_raises(tmp_path: Path) -> None:
    f = tmp_path / "is-a-file"
    f.write_text("", encoding="utf-8")
    with pytest.raises(PetriLoadError, match="not a directory"):
        load_seed_directory(f)


# ---------------------------------------------------------------------------
#  Petri-format compatibility — todo field stripped per upstream contract
# ---------------------------------------------------------------------------


def test_todo_metadata_field_stripped_per_upstream_contract(tmp_path: Path) -> None:
    seed_path = tmp_path / "with_todo.md"
    seed_path.write_text(
        '---\ntags: ["x"]\ntodo: development note that must be stripped\n---\n\nbody\n',
        encoding="utf-8",
    )
    seed = load_seed_file(seed_path)
    assert "todo" not in seed.metadata
    assert seed.metadata.get("tags") == ["x"]
