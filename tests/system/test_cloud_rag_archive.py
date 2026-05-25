from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "cloud_rag_archive.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cloud_rag_archive", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_plan_archive_reports_reclaimable_bytes_when_delete_requested(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "a.txt").write_text("lamp", encoding="utf-8")
    (source / "b.bin").write_bytes(b"door")
    cloud_root = tmp_path / "cloud"
    cloud_root.mkdir()
    manifest = tmp_path / "plan.json"

    args = argparse.Namespace(
        source=str(source),
        cloud_root=str(cloud_root),
        bucket="SCBE_RAG_ARCHIVE",
        lane="generated-media",
        archive_id="unit-plan",
        local_manifest=str(manifest),
        delete_source=True,
    )

    plan = module.plan_archive(args)

    assert plan["source_files"] == 2
    assert plan["source_bytes"] == 8
    assert plan["estimated_reclaimable_bytes"] == 8
    assert plan["cloud_root_exists"] is True
    assert manifest.exists()


def test_archive_verifies_catalogs_and_deletes_source(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "note.md").write_text("# Note\n\nRAG visible text.", encoding="utf-8")
    cloud_root = tmp_path / "cloud"
    cloud_root.mkdir()
    manifest = tmp_path / "latest.json"

    args = argparse.Namespace(
        source=str(source),
        cloud_root=str(cloud_root),
        bucket="SCBE_RAG_ARCHIVE",
        lane="docs",
        archive_id="unit-archive",
        local_manifest=str(manifest),
        delete_source=True,
        dry_run=False,
    )

    module.archive(args)

    dest = cloud_root / "SCBE_RAG_ARCHIVE" / "docs" / "unit-archive"
    assert not source.exists()
    assert (dest / "note.md").exists()
    assert (dest / module.MANIFEST_NAME).exists()
    assert manifest.exists()
    catalog = tmp_path / ".scbe" / "cloud_rag" / "catalog.jsonl"
    assert catalog.exists()
    assert "RAG visible text" in catalog.read_text(encoding="utf-8")


def test_cleanup_verified_deletes_source_from_manifest(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "note.txt").write_text("verified", encoding="utf-8")
    dest = tmp_path / "cloud" / "SCBE_RAG_ARCHIVE" / "test" / "archive"
    dest.mkdir(parents=True)
    manifest = tmp_path / "latest.json"
    module.write_json(
        manifest,
        {
            "archive_id": "archive",
            "before_free_bytes": 0,
            "destination": str(dest),
            "source": str(source),
            "verified": True,
        },
    )

    args = argparse.Namespace(manifest=str(manifest))

    module.cleanup_verified(args)

    assert not source.exists()
    assert '"source_deleted": true' in manifest.read_text(encoding="utf-8")
