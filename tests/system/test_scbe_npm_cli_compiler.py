import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "packages" / "cli" / "bin" / "scbe.js"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(CLI), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )


def test_cli_exposes_ca_plan_compiler() -> None:
    proc = run_cli("ca-plan", "--ops", "abs abs add", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["tongue"] == "CA"
    assert payload["hex_sequence"] == ["0x09", "0x09", "0x00"]


def test_cli_compile_ca_alias_emits_source() -> None:
    proc = run_cli(
        "compile",
        "ca",
        "--opcodes",
        "0x09 0x09 0x00",
        "--target",
        "python",
        "--fn",
        "score",
        "--args",
        "a,b",
    )

    assert proc.returncode == 0, proc.stderr
    assert "def score(a, b):" in proc.stdout
    assert "# add (0x00)" in proc.stdout


def test_cli_route_compiles_aetherpp_program() -> None:
    proc = run_cli("route", "--program", 'encode "run tests" in tongue KO', "--check")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["route_tongue"] == "KO"


def test_cli_run_wraps_normal_terminal_command_with_metadata() -> None:
    proc = run_cli("run", "node --version", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_terminal_run_v1"
    assert payload["success"] is True
    assert payload["compass"]["lane"] == "node"
    assert payload["governance"]["allowed"] is True


def test_cli_status_reports_terminal_capabilities() -> None:
    proc = run_cli("status")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_terminal_status_v1"
    assert payload["compiler_available"] is True
    assert payload["router_available"] is True
