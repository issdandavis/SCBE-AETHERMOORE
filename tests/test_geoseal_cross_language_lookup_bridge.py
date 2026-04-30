from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOOKUP_PATH = REPO_ROOT / "artifacts" / "cross_language_lookup" / "full_cross_language_lookup.json"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "src.geoseal_cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _lexicon_template(artifact: dict, op_name: str, tongue: str) -> str:
    row = next(item for item in artifact["lexicon"] if item["name"] == op_name)
    return row["code"][tongue]


def test_geoseal_emit_matches_cross_language_lookup_templates() -> None:
    artifact = json.loads(LOOKUP_PATH.read_text(encoding="utf-8"))
    op = "add"
    kwargs = {"a": "x", "b": "y"}

    for tongue in ("KO", "AV", "RU", "CA", "UM", "DR"):
        result = _run_cli("emit", op, "--tongue", tongue, *(f"{k}={v}" for k, v in kwargs.items()))
        assert result.returncode == 0, f"{tongue}: {result.stderr}"
        first_line = result.stdout.splitlines()[0].strip()
        expected = _lexicon_template(artifact, op, tongue).format(**kwargs)
        assert expected in first_line


def test_geoseal_encode_cmd_matches_lookup_byte_table_for_ascii_A() -> None:
    artifact = json.loads(LOOKUP_PATH.read_text(encoding="utf-8"))
    # ASCII "A" == 0x41
    ko_rows = artifact["byte_tables"]["KO"]
    expected = next(row["token"] for row in ko_rows if row["byte_hex"] == "0x41")
    encoded = _run_cli("encode-cmd", "--tongue", "KO", "A")
    assert encoded.returncode == 0, encoded.stderr
    assert encoded.stdout.strip() == expected
