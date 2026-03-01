import json
from pathlib import Path

from scripts.scan_postprocess import (
    _classify_file,
    build_folder_map,
    propose_tasks,
    FileRow,
)


def test_classify_archive_paths():
    row = FileRow(path="artifacts/repo_scans/20260101/foo.bin", size_bytes=10, ext=".bin", kind="other")
    c = _classify_file(row)
    assert c.category == "archive"
    assert "archive_path_hint" in c.reasons


def test_classify_risky_governance_area():
    row = FileRow(path="src/governance/decision.py", size_bytes=10_000, ext=".py", kind="code")
    c = _classify_file(row)
    assert c.category == "risky"
    assert "governance_core" in c.reasons


def test_build_folder_map_rollups_and_sorting():
    rows = [
        FileRow(path="src/governance/a.py", size_bytes=100, ext=".py", kind="code"),
        FileRow(path="src/governance/b.py", size_bytes=100, ext=".py", kind="code"),
        FileRow(path="src/util/c.py", size_bytes=100, ext=".py", kind="code"),
        FileRow(path="artifacts/x.bin", size_bytes=100, ext=".bin", kind="other"),
    ]
    cl = [_classify_file(r) for r in rows]
    rollups, summary = build_folder_map(cl)

    assert summary["totals"]["risky"] >= 1
    assert summary["totals"]["archive"] >= 1
    assert summary["folders"] >= 2

    # Governance folder should appear near top due to risky density
    assert any(r.folder == "src/governance" for r in rollups)


def test_propose_tasks_has_expected_core_items():
    rows = [
        FileRow(path="src/governance/decision.py", size_bytes=100, ext=".py", kind="code"),
        FileRow(path="src/api/server.py", size_bytes=100, ext=".py", kind="code"),
        FileRow(path="scripts/system/start_gateway.ps1", size_bytes=100, ext=".ps1", kind="code"),
        FileRow(path="config/.env", size_bytes=100, ext=".env", kind="config"),
    ]
    cl = [_classify_file(r) for r in rows]
    tasks = propose_tasks(cl)

    assert len(tasks) >= 3
    ids = {t.id for t in tasks}
    assert "T01" in ids  # governance choke-point audit
    assert "T02" in ids  # secrets/config hygiene
    assert "T03" in ids  # API contract
    # suggested files should be normalized and present
    for t in tasks:
        for p in t.suggested_files:
            assert "\\" not in p


def test_tasks_json_serializable(tmp_path: Path):
    rows = [
        FileRow(path="src/governance/decision.py", size_bytes=100, ext=".py", kind="code"),
        FileRow(path="src/api/server.py", size_bytes=100, ext=".py", kind="code"),
    ]
    cl = [_classify_file(r) for r in rows]
    tasks = propose_tasks(cl)
    payload = {"tasks": [t.__dict__ for t in tasks]}
    out = tmp_path / "tasks.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    assert out.exists()
