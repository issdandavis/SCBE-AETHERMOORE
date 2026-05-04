"""Tests for aligned-foundations v2 packet (concept_id threading + faces).

Guards:
- every concept_id is unique (one row per concept; no duplicate teaching across rows)
- every row carries a non-empty faces list and a parsable assistant body
- tongue rows match the canonical coding-routing map (KO=Python, ...)
- coding-primitive rows route via the same canonical map (snippet language matches tongue)
- chemistry rows declare a valid Sacred Tongue lane
- holdout split is non-empty for every category
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SFT_ROOT = REPO_ROOT / "training-data" / "sft"
TRAIN = SFT_ROOT / "aligned_foundations_v2_train.sft.jsonl"
HOLDOUT = SFT_ROOT / "aligned_foundations_v2_holdout.sft.jsonl"
MANIFEST = SFT_ROOT / "aligned_foundations_v2_manifest.json"

CANONICAL_TONGUE_LANG = {
    "KO": "Python",
    "AV": "TypeScript",
    "RU": "Rust",
    "CA": "C",
    "UM": "Julia",
    "DR": "Haskell",
}


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def all_rows() -> list[dict]:
    return _read_jsonl(TRAIN) + _read_jsonl(HOLDOUT)


def test_manifest_counts_match_files(manifest, all_rows):
    train = _read_jsonl(TRAIN)
    holdout = _read_jsonl(HOLDOUT)
    assert manifest["counts"]["train"] == len(train)
    assert manifest["counts"]["holdout"] == len(holdout)
    assert manifest["counts"]["total"] == len(all_rows) == len(train) + len(holdout)


def test_concept_ids_unique(all_rows):
    ids = [row["meta"]["concept_id"] for row in all_rows]
    assert len(ids) == len(set(ids)), "concept_id must appear in exactly one row"


def test_every_row_has_faces_and_body(all_rows):
    for row in all_rows:
        assert row["meta"]["faces"], f"row {row['meta']['concept_id']} has no faces"
        body = row["messages"][-1]["content"]
        assert "invariant:" in body, f"row {row['meta']['concept_id']} missing invariant line"


def test_tongue_rows_match_canonical_map(all_rows):
    tongue_rows = [r for r in all_rows if r["meta"]["category"] == "tongues"]
    assert len(tongue_rows) == 6
    for row in tongue_rows:
        body = row["messages"][-1]["content"]
        abbr = row["meta"]["concept_id"].split(":", 1)[1]
        expected_lang = CANONICAL_TONGUE_LANG[abbr]
        assert (
            f"coding_face: {abbr} -> {expected_lang}" in body
        ), f"tongue {abbr} body must declare canonical coding face {expected_lang}"


def test_coding_rows_route_via_canonical_map(all_rows):
    coding_rows = [r for r in all_rows if r["meta"]["category"] == "coding"]
    assert len(coding_rows) == 12
    for row in coding_rows:
        body = row["messages"][-1]["content"]
        tongue_line = next(line for line in body.splitlines() if line.startswith("tongue: "))
        lang_line = next(line for line in body.splitlines() if line.startswith("language: "))
        tongue = tongue_line.split(": ", 1)[1].strip()
        language = lang_line.split(": ", 1)[1].strip()
        assert CANONICAL_TONGUE_LANG[tongue] == language, (
            f"coding primitive {row['meta']['concept_id']} routes {tongue}->{language} "
            f"but canonical map says {tongue}->{CANONICAL_TONGUE_LANG[tongue]}"
        )


def test_chemistry_rows_declare_valid_tongue(all_rows):
    chem_rows = [r for r in all_rows if r["meta"]["category"] == "chemistry"]
    assert len(chem_rows) == 12
    for row in chem_rows:
        body = row["messages"][-1]["content"]
        tongue_line = next(line for line in body.splitlines() if line.startswith("tongue_face:"))
        tongue = tongue_line.split(":", 1)[1].strip()
        assert (
            tongue in CANONICAL_TONGUE_LANG
        ), f"chemistry row {row['meta']['concept_id']} declares unknown tongue {tongue}"


def test_holdout_split_non_empty_per_category(manifest):
    holdout = _read_jsonl(HOLDOUT)
    holdout_categories = {row["meta"]["category"] for row in holdout}
    declared = set(manifest["categories"].keys())
    missing = declared - holdout_categories
    assert not missing, f"holdout missing categories: {missing}"


def test_face_index_covers_all_six_faces(manifest):
    expected = {"math", "english", "binary", "sacred_tongues", "chemistry", "coding"}
    assert set(manifest["faces"]) == expected
