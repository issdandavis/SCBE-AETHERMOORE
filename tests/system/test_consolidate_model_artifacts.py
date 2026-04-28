import os
from pathlib import Path

from scripts.system.consolidate_model_artifacts import consolidate


def test_consolidate_exact_duplicates_with_hardlinks(tmp_path: Path):
    root = tmp_path / "models"
    root.mkdir()
    a = root / "a.safetensors"
    b = root / "b.safetensors"
    c = root / "c.safetensors"
    payload = b"x" * 2048
    a.write_bytes(payload)
    b.write_bytes(payload)
    c.write_bytes(b"y" * 2048)

    report = consolidate(roots=[root], output=tmp_path / "report.json", min_bytes=1024, apply=True)

    assert report["duplicate_group_count"] == 1
    assert report["hardlinked_files"] == 1
    assert a.read_bytes() == payload
    assert b.read_bytes() == payload
    assert c.read_bytes() == b"y" * 2048
    assert os.path.samefile(a, b)

