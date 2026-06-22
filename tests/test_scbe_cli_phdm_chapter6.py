from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCBE = REPO_ROOT / "scbe.py"


def run_scbe(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCBE), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        timeout=40,
        check=False,
    )


def test_phdm_table_cli_exposes_chapter6_nodes() -> None:
    result = run_scbe("phdm", "table", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_phdm_chapter6_table_v1"
    assert payload["node_count"] == 16
    names = [row["name"] for row in payload["nodes"]]
    assert "Rhombicosidodecahedron" in names
    assert "Pentagonal Orthobirotunda" in names


def test_phdm_path_cli_allows_safe_core_path() -> None:
    result = run_scbe("phdm", "path", "Tetrahedron,Cube,Octahedron", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_phdm_chapter6_path_v1"
    assert payload["decision"] == "ALLOW"
    assert payload["negative_binary_signature"] == [1, 1, 1]


def test_phdm_penalty_cli_matches_attack_example() -> None:
    result = run_scbe("phdm", "penalty", "Tetrahedron", "Small Stellated Dodecahedron", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema"] == "scbe_phdm_chapter6_penalty_v1"
    assert payload["penalty"] == 8.0


def test_phdm_jailbreak_cli_denies_on_budget_exhaustion() -> None:
    result = run_scbe("phdm", "jailbreak", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["decision"] == "DENY"
    assert payload["cost"]["total"] > 100.0
    assert "energy_budget_exhausted" in payload["violations"]

