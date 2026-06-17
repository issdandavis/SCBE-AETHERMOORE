from __future__ import annotations

import json
import zipfile

from scripts.system.build_black_box_download import build_black_box_download


def test_build_black_box_download_creates_verified_zip(tmp_path):
    manifest = build_black_box_download(tmp_path)

    assert manifest["schema"] == "scbe_black_box_download_v1"
    assert manifest["verification"]["ok"] is True
    assert manifest["archive"]["bytes"] > 0

    archive_path = tmp_path / manifest["archive"]["file"]
    assert archive_path.exists()

    bundle_dir = tmp_path / manifest["bundle_name"]
    report = json.loads((bundle_dir / "sample-output" / "latest_black_box_report.json").read_text(encoding="utf-8"))
    assert report["schema"] == "scbe_black_box_report_v1"
    assert report["findings"]
    assert (bundle_dir / "sample-output" / "latest_black_box_report.txt").exists()

    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
    assert "scbe_black_box.py" in names
    assert "run-windows.ps1" in names
    assert "run-unix.sh" in names
    assert "QUICKSTART.md" in names
    assert "manifest.json" in names
