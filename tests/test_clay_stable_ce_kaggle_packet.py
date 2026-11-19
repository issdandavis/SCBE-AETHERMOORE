from __future__ import annotations

import io
import json
from pathlib import Path
import zipfile

import pytest

from scripts.research.build_clay_stable_ce_kaggle_packet import deterministic_zip
from scripts.research.run_clay_stable_ce_kaggle import (
    DESCRIPTOR_SCHEMA,
    EXPECTED_DATASET_ID,
    discover_packet,
    safe_archive_members,
)


def test_deterministic_zip_repeats_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "b.txt").write_text("b", encoding="utf-8")
    (source / "a.txt").write_text("a", encoding="utf-8")
    first = tmp_path / "first.packet"
    second = tmp_path / "second.packet"
    deterministic_zip(source, first)
    deterministic_zip(source, second)
    assert first.read_bytes() == second.read_bytes()


def test_safe_archive_rejects_parent_escape() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../escape.txt", "bad")
    buffer.seek(0)
    with zipfile.ZipFile(buffer, "r") as archive, pytest.raises(ValueError):
        safe_archive_members(archive)


def test_discover_packet_requires_exact_private_dataset(tmp_path: Path) -> None:
    descriptor = {
        "schema": DESCRIPTOR_SCHEMA,
        "dataset_id": EXPECTED_DATASET_ID,
        "archive": {},
        "packet_manifest": {},
    }
    path = tmp_path / "PACKET_DESCRIPTOR.json"
    path.write_text(json.dumps(descriptor), encoding="utf-8")
    found_path, found = discover_packet(tmp_path)
    assert found_path == path
    assert found["dataset_id"] == EXPECTED_DATASET_ID
