from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "chemistry_cli_capability.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("chemistry_cli_capability", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_chemistry_capability_inventory_builds_report(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(tmp_path, run_tests=False)

    assert report["schema_version"] == "scbe_chemistry_cli_capability_v1"
    assert report["summary"]["decision"] in {"INVENTORY_ONLY", "HOLD"}
    assert report["summary"]["capability_files_present"] >= 8
    assert report["summary"]["private_proof_total"] >= 1
    assert report["positioning"]["website_safe_claim"]
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_chemistry_capability_probes_execute() -> None:
    module = _load_module()

    probes = module.direct_runtime_probes()

    assert {probe["id"] for probe in probes} == {
        "stista_atomic_fusion_probe",
        "tongue_molecule_probe",
        "ternary_equilibrium_probe",
        "geoseed_orbital_probe",
    }
    assert all(probe["ok"] is True for probe in probes)


def test_chemistry_capability_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/chemistry_cli_capability.py",
            "--out-dir",
            str(tmp_path),
            "--inventory-only",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr
    assert "scbe_chemistry_cli_capability_v1" in proc.stdout
    assert (tmp_path / "latest_report.json").exists()
