from __future__ import annotations

import io
from pathlib import Path
import zipfile

import pytest

from scripts.research.build_clay_frozen_multiview_kaggle_packet import (
    DESCRIPTOR_SCHEMA,
    PACKET_SCHEMA,
    descriptor,
    deterministic_zip,
    sha256_file,
    write_json,
)
from scripts.research.run_clay_frozen_multiview_kaggle_compat import (
    DESCRIPTOR_NAME,
    EXPECTED_DATASET_ID,
    PACKET_MANIFEST_NAME,
    _safe_archive_members,
    discover_packet,
    extract_and_verify_packet,
)


def _packet_fixture(tmp_path: Path) -> tuple[Path, Path]:
    packet = tmp_path / "packet-source"
    payload = packet / "scbe_repo" / "python" / "scbe" / "fixture.py"
    payload.parent.mkdir(parents=True)
    payload.write_text("VALUE = 7\n", encoding="utf-8", newline="\n")
    manifest = {
        "schema": PACKET_SCHEMA,
        "dataset_id": EXPECTED_DATASET_ID,
        "files": [descriptor(payload, relative_to=packet)],
        "remote_config": {"device": "cpu"},
    }
    manifest_path = packet / PACKET_MANIFEST_NAME
    write_json(manifest_path, manifest)

    dataset = tmp_path / "input" / "provider" / "dataset-v1"
    dataset.mkdir(parents=True)
    archive = dataset / "packet.zip"
    deterministic_zip(packet, archive)
    write_json(
        dataset / DESCRIPTOR_NAME,
        {
            "schema": DESCRIPTOR_SCHEMA,
            "dataset_id": EXPECTED_DATASET_ID,
            "archive": descriptor(archive),
            "packet_manifest": descriptor(manifest_path),
        },
    )
    return tmp_path / "input", dataset / DESCRIPTOR_NAME


def test_discovers_extracts_and_hash_verifies_one_packet(tmp_path: Path) -> None:
    input_root, expected_descriptor = _packet_fixture(tmp_path)

    descriptor_path, packet_descriptor = discover_packet(input_root)
    manifest_path, manifest = extract_and_verify_packet(descriptor_path, packet_descriptor, tmp_path / "runtime")

    assert descriptor_path == expected_descriptor
    assert manifest["schema"] == PACKET_SCHEMA
    assert sha256_file(manifest_path) == packet_descriptor["packet_manifest"]["sha256"]
    assert (tmp_path / "runtime" / "scbe_repo" / "python" / "scbe" / "fixture.py").read_text(
        encoding="utf-8"
    ) == "VALUE = 7\n"


def test_rejects_ambiguous_or_tampered_packet(tmp_path: Path) -> None:
    input_root, descriptor_path = _packet_fixture(tmp_path)
    duplicate = input_root / "second" / DESCRIPTOR_NAME
    duplicate.parent.mkdir()
    duplicate.write_bytes(descriptor_path.read_bytes())
    with pytest.raises(RuntimeError, match="expected one"):
        discover_packet(input_root)

    duplicate.unlink()
    descriptor_path.parent.joinpath("packet.zip").write_bytes(b"tampered")
    found_path, packet_descriptor = discover_packet(input_root)
    with pytest.raises(RuntimeError, match="byte count differs"):
        extract_and_verify_packet(found_path, packet_descriptor, tmp_path / "runtime")


def test_rejects_zip_path_traversal() -> None:
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("../escape.txt", "no")
    payload.seek(0)
    with zipfile.ZipFile(payload, "r") as archive:
        with pytest.raises(ValueError, match="unsafe archive member"):
            _safe_archive_members(archive)


def test_deterministic_zip_is_byte_identical(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "b.txt").write_text("b\n", encoding="utf-8")
    (source / "a.txt").write_text("a\n", encoding="utf-8")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    deterministic_zip(source, first)
    deterministic_zip(source, second)

    assert first.read_bytes() == second.read_bytes()
    assert sha256_file(first) == sha256_file(second)
