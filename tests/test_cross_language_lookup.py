from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "system" / "build_cross_language_lookup.py"
ARTIFACT = REPO_ROOT / "artifacts" / "cross_language_lookup" / "full_cross_language_lookup.json"


def test_cross_language_lookup_builder_check_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_cross_language_lookup_has_full_primary_bijection_tables() -> None:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["schema"] == "scbe_cross_language_lookup_v1"
    for code in ("KO", "AV", "RU", "CA", "UM", "DR"):
        rows = data["byte_tables"][code]
        assert len(rows) == 256
        assert {row["byte_int"] for row in rows} == set(range(256))
        assert len({row["token"] for row in rows}) == 256


def test_cross_language_lookup_lexicon_and_extended_inheritance() -> None:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    lexicon = data["lexicon"]
    assert len(lexicon) == 64
    add = next(row for row in lexicon if row["name"] == "add")
    assert set(("KO", "AV", "RU", "CA", "UM", "DR", "GO", "ZI")).issubset(set(add["code"]))
    assert "GO_inherits_from" in add["code"]
    assert "ZI_inherits_from" in add["code"]
