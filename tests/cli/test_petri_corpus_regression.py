"""Petri corpus regression — load-bearing claims about the upstream seeds.

This test runs only when the gitignored seed mirror at
``external/benchmarks/petri-seeds/`` has been populated (per
``docs/external/PETRI_SEEDS.md``). When it has, every assertion is a
canary-contract guarantee — if upstream Petri ever drops the canary on
some seed, removes seeds wholesale, or renames the canonical adversarial
tags, this file fails loudly and the contamination boundary surfaces as
a test diff rather than a silent training-data leak.

CI behaviour: the test skips when the directory is empty or missing,
so the public-repo CI never depends on benchmark data being present.
Local regression: when you've populated the directory, the test runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cli.petri_seed_loader import (
    load_seed_directory,
    split_by_training_safety,
)

_REAL_SEEDS_DIR = Path(__file__).resolve().parents[2] / "external" / "benchmarks" / "petri-seeds"


def _real_seeds_available() -> bool:
    if not _REAL_SEEDS_DIR.exists():
        return False
    return any(_REAL_SEEDS_DIR.glob("*.md"))


pytestmark = pytest.mark.skipif(
    not _real_seeds_available(),
    reason=(f"populate {_REAL_SEEDS_DIR} per docs/external/PETRI_SEEDS.md " "to run the regression"),
)


# ---------------------------------------------------------------------------
#  Canary contract — the load-bearing guarantee
# ---------------------------------------------------------------------------


def test_every_real_seed_is_training_blocked() -> None:
    """100% of real Petri seeds must trip the canary detector. If even
    one slips through, either upstream removed the canary on that seed
    (escalate to Petri maintainers) or our detector regressed."""
    seeds = load_seed_directory(_REAL_SEEDS_DIR)
    blocked, safe = split_by_training_safety(seeds)
    assert len(safe) == 0, f"{len(safe)} seeds slipped past canary detection: " f"{sorted(s.id for s in safe)[:10]}"
    assert len(blocked) == len(seeds)


# ---------------------------------------------------------------------------
#  Corpus shape — drift detection
# ---------------------------------------------------------------------------


# Lower bound on seed count. Petri shipped v1=111, v2=181 by 2026-04;
# baseline v1 (2026-05-08) loaded 173. If a future clone drops below
# 150 the upstream layout probably moved and the seed-mirror script
# in docs/external/PETRI_SEEDS.md needs updating.
_MIN_SEED_COUNT = 150


def test_real_corpus_size_is_within_expected_range() -> None:
    seeds = load_seed_directory(_REAL_SEEDS_DIR)
    assert len(seeds) >= _MIN_SEED_COUNT, (
        f"only {len(seeds)} seeds loaded; expected >={_MIN_SEED_COUNT}. "
        "upstream layout may have moved — re-check "
        "docs/external/PETRI_SEEDS.md clone instructions."
    )


# Tags Anthropic published as canonical adversarial categories. If any
# of these vanish from the upstream corpus, the adversarial threat
# surface has materially shifted and we want to know.
_REQUIRED_TAGS = (
    "cooperation_with_misuse",
    "deception",
    "jailbreak",
    "oversight_subversion",
    "self_preservation",
    "sycophancy",
)


def test_required_adversarial_tags_present() -> None:
    seeds = load_seed_directory(_REAL_SEEDS_DIR)
    all_tags: set[str] = set()
    for s in seeds:
        all_tags.update(s.metadata.get("tags") or [])
    missing = [t for t in _REQUIRED_TAGS if t not in all_tags]
    assert not missing, (
        f"upstream Petri dropped required adversarial tags: {missing}. " f"present tags: {sorted(all_tags)}"
    )


# ---------------------------------------------------------------------------
#  Body sanity — corrupt-load detection
# ---------------------------------------------------------------------------


def test_no_real_seed_has_empty_body() -> None:
    """An empty body means either a malformed seed (frontmatter ate the
    whole file) or the loader dropped the body during parsing. Either
    way, surface it."""
    seeds = load_seed_directory(_REAL_SEEDS_DIR)
    empties = [s.id for s in seeds if not s.input.strip()]
    assert empties == [], f"seeds with empty body: {empties}"


def test_real_corpus_body_lengths_within_expected_envelope() -> None:
    """Petri seeds are short auditor instructions; bodies past ~10K chars
    suggest a parse error consumed adjacent files or the upstream corpus
    moved to long-form scenarios that need a separate handler."""
    seeds = load_seed_directory(_REAL_SEEDS_DIR)
    too_long = [(s.id, len(s.input)) for s in seeds if len(s.input) > 10_000]
    assert too_long == [], f"seeds exceeding 10K chars: {too_long[:5]}"


# ---------------------------------------------------------------------------
#  Idempotence — load -> reload yields equal output
# ---------------------------------------------------------------------------


def test_directory_load_is_idempotent() -> None:
    """Two reads of the same directory must produce the same seed set,
    same ids, same training_blocked flags. Catches caching bugs and
    filesystem-iteration nondeterminism."""
    a = load_seed_directory(_REAL_SEEDS_DIR)
    b = load_seed_directory(_REAL_SEEDS_DIR)
    assert [s.id for s in a] == [s.id for s in b]
    assert [s.training_blocked for s in a] == [s.training_blocked for s in b]
    assert [s.input for s in a] == [s.input for s in b]
