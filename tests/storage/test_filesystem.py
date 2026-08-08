from __future__ import annotations

from pathlib import Path

import pytest

from storage import FileSystemSealedBlobStorage, SealedBlobRecord


def test_filesystem_storage_round_trip(tmp_path: Path) -> None:
    storage = FileSystemSealedBlobStorage(str(tmp_path / "sealed"))
    record = SealedBlobRecord(
        owner="principal-a",
        position=[1, 2, 3, 5, 8, 13],
        agent="agent-1",
        topic="topic-1",
        sealed_blob=b"sealed",
    )

    storage.save(record)

    assert storage.load(record.position, owner=record.owner) == record


def test_filesystem_storage_namespaces_records_by_owner(tmp_path: Path) -> None:
    storage = FileSystemSealedBlobStorage(str(tmp_path / "sealed"))
    position = [1, 2, 3, 5, 8, 13]
    record = SealedBlobRecord(
        owner="principal-a",
        position=position,
        agent="shared-agent-name",
        topic="topic-1",
        sealed_blob=b"principal-a-secret",
    )
    storage.save(record)

    with pytest.raises(FileNotFoundError):
        storage.load(position, owner="principal-b")

    storage.save(
        SealedBlobRecord(
            owner="principal-b",
            position=position,
            agent="shared-agent-name",
            topic="topic-2",
            sealed_blob=b"principal-b-secret",
        )
    )

    assert storage.load(position, owner="principal-a").sealed_blob == b"principal-a-secret"
    assert storage.load(position, owner="principal-b").sealed_blob == b"principal-b-secret"


@pytest.mark.parametrize(
    "position",
    [
        [1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5, True],
        [1, 2, 3, 4, 5, "../escape"],
        [1, 2, 3, 4, 5, 2**64],
    ],
)
def test_filesystem_storage_rejects_unsafe_positions(tmp_path: Path, position: list[object]) -> None:
    storage = FileSystemSealedBlobStorage(str(tmp_path / "sealed"))

    with pytest.raises(ValueError):
        storage.load(position, owner="principal-a")  # type: ignore[arg-type]
