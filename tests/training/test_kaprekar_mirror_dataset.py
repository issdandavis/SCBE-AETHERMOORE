"""Tests for the deterministic Kaprekar mirror auxiliary-view exporter."""

from __future__ import annotations

import hashlib
import json

from src.training.kaprekar_mirror_dataset import (
    AUDIT_ONLY_FIELDS,
    FEATURE_ALLOWLIST,
    LABEL_ONLY_FIELDS,
    assert_family_disjoint,
    build_records,
    canonical_family_id,
    split_for_family,
    write_dataset,
)


def test_family_id_groups_digit_permutations() -> None:
    assert canonical_family_id("3524") == canonical_family_id("4253") == "2345"
    assert split_for_family("2345", split_seed=6174) == split_for_family(
        "2345",
        split_seed=6174,
    )


def test_four_digit_records_are_family_disjoint_and_complete() -> None:
    records = build_records(width=4)

    assert len(records) == 10_000
    assert sum(not record["is_repdigit"] for record in records) == 9_990
    assert_family_disjoint(records)

    family_splits: dict[str, set[str]] = {}
    for record in records:
        family_splits.setdefault(record["family_id"], set()).add(record["split"])
    assert len(family_splits) == 715
    assert all(len(splits) == 1 for splits in family_splits.values())


def test_record_separates_features_labels_and_audit_data() -> None:
    record = build_records(width=4)[3524]

    assert record["state"] == "3524"
    assert record["labels"]["primary_next_state"] == "3087"
    assert record["auxiliary_view"]["primary_bottom"] == "6174"
    assert record["auxiliary_view"]["mirror_bottom"] == "4716"
    assert record["audit"]["palindrome_envelope"] == "35244253"

    assert not set(FEATURE_ALLOWLIST) & set(LABEL_ONLY_FIELDS)
    assert not set(FEATURE_ALLOWLIST) & set(AUDIT_ONLY_FIELDS)


def test_repdigits_are_marked_as_a_separate_training_role() -> None:
    records = build_records(width=2)
    repdigits = [record for record in records if record["is_repdigit"]]

    assert len(repdigits) == 10
    assert {record["training_role"] for record in repdigits} == {"special_zero_basin"}


def test_export_is_byte_deterministic_and_manifest_hashes_output(tmp_path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_output = first_dir / "view.jsonl"
    second_output = second_dir / "view.jsonl"
    first_manifest_path = first_dir / "view.manifest.json"
    second_manifest_path = second_dir / "view.manifest.json"

    first_manifest = write_dataset(
        first_output,
        first_manifest_path,
        width=3,
        split_seed=495,
    )
    second_manifest = write_dataset(
        second_output,
        second_manifest_path,
        width=3,
        split_seed=495,
    )

    assert first_output.read_bytes() == second_output.read_bytes()
    assert first_manifest_path.read_bytes() == second_manifest_path.read_bytes()
    assert first_manifest == second_manifest
    assert (
        first_manifest["output_sha256"]
        == hashlib.sha256(first_output.read_bytes()).hexdigest()
    )
    assert first_manifest["family_disjoint"] is True
    assert first_manifest["promotion_state"] == "shadow_only"

    parsed = json.loads(first_manifest_path.read_text(encoding="utf-8"))
    assert parsed["feature_allowlist"] == list(FEATURE_ALLOWLIST)
    assert parsed["label_only_fields"] == list(LABEL_ONLY_FIELDS)
