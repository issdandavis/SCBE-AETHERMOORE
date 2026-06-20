import json
import shutil
import subprocess
from pathlib import Path

import pytest

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


def test_cli_version_reports_cli_and_core_versions() -> None:
    proc = run_cli("version", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_aethermoore_cli_version_v1"
    assert payload["cli_package"] == "scbe-aethermoore-cli"
    assert payload["cli_version"]
    assert payload["core_package"] == "scbe-aethermoore"
    assert payload["core_version"]


def test_cli_doctor_wraps_geoseal_with_cli_version_context() -> None:
    proc = run_cli("doctor", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_aethermoore_cli_doctor_v1"
    assert payload["cli_version"]
    assert payload["core_version"]
    assert payload["cli_package_bin"]["scbe"] == "bin/scbe.js"
    assert payload["geoseal_doctor"]["ok"] is True


def test_cli_demo_outputs_governed_magic_moment() -> None:
    proc = run_cli("demo", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_governed_output_demo_v1"
    assert payload["decision"] in {"QUARANTINE", "ESCALATE", "DENY"}
    assert payload["output"]
    assert payload["suggested_correction"]
    assert payload["geoseal"]["audit_id"].startswith("geoseal_")
    assert payload["geoseal"]["allowed"] is False
    assert any(reason.startswith("geoseal.execution_gate.") for reason in payload["reasons"])


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
    # The flow workspace dirs are runtime-created (artifacts/ is gitignored);
    # this test checks that status REPORTS them, so provision them first.
    (REPO_ROOT / "artifacts" / "flow_status").mkdir(parents=True, exist_ok=True)

    proc = run_cli("status")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_terminal_status_v1"
    assert payload["receipt"] == "SCBE_STATUS_READY=1"
    assert payload["compiler_available"] is True
    assert payload["router_available"] is True
    assert payload["git"]["commit"]
    assert "branch" in payload["git"]
    assert "ci" in payload
    assert payload["providers"]["local"]["available"] is True
    assert payload["budget"]["posture"] in {"local_free_default", "hosted_enabled"}
    assert payload["workspace"]["flow_status_ready"] is True


def test_cli_liboqs_reports_native_proof_receipt() -> None:
    from src.crypto.pqc_liboqs import get_pqc_governance_status

    if get_pqc_governance_status()["tier"] != 1:
        pytest.skip("native liboqs is optional in CI")

    proc = run_cli("liboqs", "--json")

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_liboqs_receipt_v1"
    assert payload["receipt"] == "SCBE_LIBOQS_PASS=1"
    assert payload["native_pass"] is True
    assert payload["status"]["tier"] == 1
    assert payload["status"]["liboqs_available"] is True
    assert payload["smoke"]["ml_kem_roundtrip"] is True
    assert payload["smoke"]["ml_dsa_verify"] is True


def test_cli_liboqs_reports_source_checkout_required_outside_repo(tmp_path: Path) -> None:
    # Simulate an installed npm package: copy the whole CLI package (bin + lib +
    # package.json) into node_modules, not just bin/scbe.js. scbe.js eagerly
    # requires ../lib/*, so a bin-only copy can never load — and from this
    # location repoRoot() resolves to tmp_path (no src/ tree), which is exactly
    # the "source checkout required" condition under test.
    package_src = CLI.parent.parent
    package_root = tmp_path / "node_modules" / "scbe-aethermoore-cli"
    shutil.copytree(package_src / "bin", package_root / "bin")
    shutil.copytree(package_src / "lib", package_root / "lib")
    shutil.copy2(package_src / "package.json", package_root / "package.json")
    copied_cli = package_root / "bin" / "scbe.js"

    proc = subprocess.run(
        ["node", str(copied_cli), "liboqs", "--json"],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 2, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_liboqs_receipt_v1"
    assert payload["receipt"] == "SCBE_LIBOQS_PASS=0"
    assert payload["native_pass"] is False
    assert payload["error"] == "source checkout required"
