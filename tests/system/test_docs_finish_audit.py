from __future__ import annotations

from pathlib import Path

from scripts.system.docs_finish_audit import audit_docs


def test_audit_docs_detects_markers_and_broken_links(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir(parents=True, exist_ok=True)

    good = docs / "good.md"
    good.write_text("# Good\n\nNo issues.\n", encoding="utf-8")

    bad = docs / "bad.md"
    bad.write_text("# Bad\n\nTODO: fix this\n\n[Broken](missing.md)\n", encoding="utf-8")

    report = audit_docs(repo_root=tmp_path, docs_dir="docs")
    assert report["schema_version"] == "scbe_docs_finish_audit_v1"
    assert report["files_scanned"] == 2
    assert report["files_with_findings"] == 1
    assert report["unfinished_marker_total"] == 1
    assert report["broken_local_link_total"] == 1
    findings = report["findings"]
    assert isinstance(findings, list) and findings
    assert findings[0]["path"] == "docs/bad.md"
