from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "chemistry_industry_benchmark.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("chemistry_industry_benchmark", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_industry_benchmark_builds_report(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(tmp_path, timeout_s=30, live_pubchem=False)

    assert report["schema_version"] == "scbe_chemistry_industry_benchmark_v1"
    assert report["tools"]["scbe"]["status"] == "pass"
    assert report["tools"]["scbe"]["probes"]["convert_rdkit"]["status"] == "pass"
    assert report["tools"]["scbe"]["probes"]["convert_openbabel"]["status"] == "pass"
    assert "openbabel_obabel" in report["tools"]
    assert "openbabel_python" in report["tools"]
    assert "rdkit_python" in report["tools"]
    assert "pubchem_pug_rest" in report["tools"]
    assert report["summary"]["decision"]
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_industry_benchmark_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/chemistry_industry_benchmark.py",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=80,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "scbe_chemistry_industry_benchmark_v1"
    assert payload["tools"]["scbe"]["status"] == "pass"


def test_scbe_chem_industry_benchmark_command(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scbe.py",
            "chem",
            "industry-benchmark",
            "--out-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=80,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["summary"]["scbe_probe_status"] == "pass"
    assert payload["tools"]["rdkit_python"]["installed"] is True
