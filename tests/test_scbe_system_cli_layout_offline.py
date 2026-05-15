from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "scbe-system-cli.py"


def _run_cli(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--repo-root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_layout_plan_writes_non_destructive_partition_plan(tmp_path: Path) -> None:
    output_path = tmp_path / "root-layout-plan.json"

    result = _run_cli("layout", "plan", "--output", str(output_path), "--json")

    assert result.returncode == 0, result.stderr
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scbe_root_layout_plan_v1"
    assert payload["entry_count"] == len(payload["entries"])
    assert payload["entry_count"] > 0
    assert "This command does not move files." in payload["notes"]

    lanes = {entry["lane"] for entry in payload["entries"]}
    assert "deploy" in lanes
    assert "non_deploy_research" in lanes
    assert "non_deploy_archive" in lanes

    src_entry = next(entry for entry in payload["entries"] if entry["name"] == "src")
    assert src_entry["lane"] == "deploy"
    assert src_entry["destination"].endswith(str(Path("deploy_runtime") / "src"))


def test_offline_bundle_build_and_install_roundtrip(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    install_dir = tmp_path / "install"

    build_result = _run_cli(
        "offline",
        "build",
        "--profile",
        "cli-offline-core",
        "--output",
        str(bundle_dir),
        "--json",
    )

    assert build_result.returncode == 0, build_result.stderr
    manifest_path = bundle_dir / "bundle_manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "scbe_offline_bundle_v1"
    assert manifest["profile"] == "cli-offline-core"
    assert manifest["copied_files"] > 0
    assert "scripts/scbe-system-cli.py" in manifest["include"]
    assert not manifest["missing"]
    assert (bundle_dir / "payload" / "scripts" / "scbe-system-cli.py").exists()
    assert (bundle_dir / "payload" / "config" / "offline_bundle_profiles.json").exists()

    install_result = _run_cli("offline", "install", "--bundle", str(bundle_dir), "--target", str(install_dir), "--json")

    assert install_result.returncode == 0, install_result.stderr
    installed = json.loads(install_result.stdout)
    assert installed["schema_version"] == "scbe_offline_bundle_install_result_v1"
    assert installed["installed_files"] == manifest["copied_files"]
    assert (install_dir / "scripts" / "scbe-system-cli.py").exists()
    assert (install_dir / "config" / "offline_bundle_profiles.json").exists()
