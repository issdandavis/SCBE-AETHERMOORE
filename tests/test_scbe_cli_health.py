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


def test_system_health_json_reports_pc_resource_state() -> None:
    result = run_scbe("system", "health", "--json", "--no-write", "--top-processes", "3")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_pc_health_v1"
    assert {"total_gb", "used_gb", "free_gb", "used_percent"} <= set(payload["ram"])
    assert isinstance(payload["drives"], list)
    assert isinstance(payload["warnings"], list)
    assert isinstance(payload["recommendations"], list)


def test_health_shortcut_matches_system_health_schema() -> None:
    result = run_scbe("health", "--json", "--no-write", "--top-processes", "1")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_pc_health_v1"


def test_natural_language_health_routes_to_pc_health() -> None:
    result = run_scbe("please", "check", "pc", "memory", "health", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "scbe_pc_health_v1"
