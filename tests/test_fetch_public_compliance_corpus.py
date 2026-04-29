"""Tests for compliance corpus manifest and fetch script helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "config" / "compliance" / "public_sources.json"
SCRIPT = REPO_ROOT / "scripts" / "system" / "fetch_public_compliance_corpus.py"


def test_public_sources_manifest_shape() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data.get("version") == 1
    sources = data["sources"]
    assert isinstance(sources, list) and len(sources) >= 4
    http_ids = [s["id"] for s in sources if s.get("fetch_kind") == "http_get"]
    assert "nist_ai_rmf_100_1" in http_ids
    purchase = [s for s in sources if s.get("fetch_kind") == "purchase_only"]
    assert (
        purchase
    ), "expect at least one purchase_only row so ISO/SOC scope is explicit"


def test_fetch_script_dry_run_zero_network_writes(tmp_path: Path) -> None:
    out = tmp_path / "fetched"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--manifest",
            str(MANIFEST),
            "--out",
            str(out),
            "--dry-run",
            "--only",
            "nist_ai_rmf_100_1",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload.get("dry_run") is True
    assert len(payload.get("results", [])) == 1
    assert not out.exists() or not any(
        out.iterdir()
    ), "dry-run must not write corpus files"


def test_filter_excludes_large_without_flag() -> None:
    # Import the module under test without executing network code.
    import importlib.util

    spec = importlib.util.spec_from_file_location("fetch_cc", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources = data["sources"]
    filtered = mod._filter_sources(sources, only_ids=None, include_large=False)
    ids = {s["id"] for s in filtered}
    assert "gdpr_eurlex_html" not in ids
    filtered_large = mod._filter_sources(sources, only_ids=None, include_large=True)
    ids_large = {s["id"] for s in filtered_large}
    assert "gdpr_eurlex_html" in ids_large
