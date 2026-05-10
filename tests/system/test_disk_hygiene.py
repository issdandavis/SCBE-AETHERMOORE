"""Smoke tests for the disk-hygiene scanner scripts.

Both scripts are READ-ONLY: they walk a tree and emit a JSON report.
Tests use isolated tmp_path trees so we don't touch real user files.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "system"
DEDUP = SCRIPTS_DIR / "find_home_dedup.py"
BLOAT = SCRIPTS_DIR / "find_regenerable_bloat.py"


def _run(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(script), *args]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(cwd) if cwd else str(REPO_ROOT),
        env=env,
    )


def _make_dupes(root: Path) -> tuple[Path, Path, Path]:
    """Three identical 1KB files in different subdirs."""
    payload = ("hello-world-" * 80).encode("utf-8")  # > 256-byte min threshold
    a = root / "a" / "file.txt"
    b = root / "b" / "file.txt"
    c = root / "src" / "file.txt"
    for p in (a, b, c):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
    return a, b, c


@pytest.mark.skipif(not DEDUP.exists(), reason="find_home_dedup.py missing")
def test_dedup_finds_known_duplicates(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"
    _make_dupes(tmp_path)

    result = _run(
        DEDUP,
        "--scope-root",
        str(tmp_path).replace("\\", "/"),
        "--output-dir",
        str(out_dir).replace("\\", "/"),
        "--top",
        "5",
    )
    assert result.returncode == 0, result.stderr

    reports = list(out_dir.glob("dedup_report_*.json"))
    assert len(reports) == 1, "expected exactly one report"
    report = json.loads(reports[0].read_text(encoding="utf-8"))

    assert report["schema"] == "home_dedup_report_v1"
    assert report["totals"]["n_clusters"] >= 1
    assert report["totals"]["n_redundant_files"] >= 2  # 3 copies = 2 redundant
    cluster = report["duplicate_clusters"][0]
    assert cluster["n_copies"] == 3
    # Suggested keeper must be one of the 3 cluster paths.
    # (Note: tmp_path lives under artifacts/ here, which the heuristic
    # explicitly avoids — the src/-preference branch can't fire from a
    # tmp tree, so we only assert the keeper is a valid cluster member.)
    assert cluster["suggested_keep"] in cluster["paths"]
    assert cluster["suggested_keep_reason"]


@pytest.mark.skipif(not DEDUP.exists(), reason="find_home_dedup.py missing")
def test_dedup_skips_excluded_dirs(tmp_path: Path) -> None:
    """node_modules siblings must NOT appear in any cluster."""
    out_dir = tmp_path / "reports"
    payload = ("noise-" * 80).encode("utf-8")
    for sub in ("node_modules/pkg-a", "node_modules/pkg-b"):
        p = tmp_path / sub / "index.js"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)

    result = _run(
        DEDUP,
        "--scope-root",
        str(tmp_path).replace("\\", "/"),
        "--output-dir",
        str(out_dir).replace("\\", "/"),
    )
    assert result.returncode == 0, result.stderr

    report = json.loads(next(out_dir.glob("dedup_report_*.json")).read_text(encoding="utf-8"))
    for cluster in report["duplicate_clusters"]:
        for path in cluster["paths"]:
            assert "node_modules" not in path.replace("\\", "/"), f"node_modules leaked into report: {path}"


@pytest.mark.skipif(not BLOAT.exists(), reason="find_regenerable_bloat.py missing")
def test_bloat_finds_node_modules(tmp_path: Path) -> None:
    out_dir = tmp_path / "reports"
    nm = tmp_path / "myproject" / "node_modules" / "lodash"
    nm.mkdir(parents=True)
    (nm / "index.js").write_bytes(b"x" * 4096)

    result = _run(
        BLOAT,
        "--scope-root",
        str(tmp_path).replace("\\", "/"),
        "--output-dir",
        str(out_dir).replace("\\", "/"),
    )
    assert result.returncode == 0, result.stderr

    report = json.loads(next(out_dir.glob("regenerable_bloat_*.json")).read_text(encoding="utf-8"))
    assert report["schema"] == "regenerable_bloat_v1"
    assert report["totals"]["regenerable_dirs_found"] >= 1
    assert "node_modules" in report["by_kind"]
    assert report["by_kind"]["node_modules"]["bytes"] >= 4096


@pytest.mark.skipif(not BLOAT.exists(), reason="find_regenerable_bloat.py missing")
def test_bloat_does_not_descend_into_hits(tmp_path: Path) -> None:
    """Once we find node_modules, we should not double-count nested .venvs inside it."""
    out_dir = tmp_path / "reports"
    nested = tmp_path / "outer" / "node_modules" / "fake-pkg" / ".venv"
    nested.mkdir(parents=True)
    (nested / "marker").write_bytes(b"y" * 1024)

    result = _run(
        BLOAT,
        "--scope-root",
        str(tmp_path).replace("\\", "/"),
        "--output-dir",
        str(out_dir).replace("\\", "/"),
    )
    assert result.returncode == 0, result.stderr

    report = json.loads(next(out_dir.glob("regenerable_bloat_*.json")).read_text(encoding="utf-8"))
    # Only the outer node_modules should be reported; .venv inside it is rolled in.
    nm_hits = [h for h in report["hits"] if h["kind"] == "node_modules"]
    venv_hits = [h for h in report["hits"] if h["kind"] == ".venv"]
    assert len(nm_hits) == 1
    assert len(venv_hits) == 0, f"unexpectedly descended into hit: {venv_hits}"


@pytest.mark.skipif(not BLOAT.exists(), reason="find_regenerable_bloat.py missing")
def test_bloat_ignores_hard_skip_dirs(tmp_path: Path) -> None:
    """OneDrive subtree must never be descended into."""
    out_dir = tmp_path / "reports"
    inside_onedrive = tmp_path / "OneDrive" / "myproject" / "node_modules"
    inside_onedrive.mkdir(parents=True)
    (inside_onedrive / "x").write_bytes(b"z" * 1024)

    result = _run(
        BLOAT,
        "--scope-root",
        str(tmp_path).replace("\\", "/"),
        "--output-dir",
        str(out_dir).replace("\\", "/"),
    )
    assert result.returncode == 0, result.stderr

    report = json.loads(next(out_dir.glob("regenerable_bloat_*.json")).read_text(encoding="utf-8"))
    for hit in report["hits"]:
        assert (
            "onedrive" not in hit["path"].replace("\\", "/").lower()
        ), f"OneDrive leaked into bloat scan: {hit['path']}"
