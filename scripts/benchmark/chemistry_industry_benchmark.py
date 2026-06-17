#!/usr/bin/env python3
"""Benchmark SCBE chemistry CLI against common cheminformatics baselines.

This is not a leaderboard. It is a reproducible positioning artifact that
checks what is installed locally, runs safe smoke probes where possible, and
separates SCBE's symbolic/governance chemistry lane from scientific molecule
toolkits such as Open Babel and RDKit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "chemistry_industry"

BASELINES = {
    "openbabel_obabel": {
        "name": "Open Babel obabel",
        "kind": "chemistry_cli",
        "official_url": "https://open-babel.readthedocs.io/en/latest/Command-line_tools/babel.html",
        "local_commands": ["obabel", "babel"],
        "primary_claim": "interconvert, filter, and manipulate molecular file formats",
    },
    "rdkit_python": {
        "name": "RDKit",
        "kind": "cheminformatics_toolkit",
        "official_url": "https://www.rdkit.org/docs/Overview.html",
        "python_module": "rdkit",
        "primary_claim": "open-source cheminformatics toolkit with 2D/3D molecular operations",
    },
    "pubchem_pug_rest": {
        "name": "PubChem PUG-REST",
        "kind": "public_chemistry_api",
        "official_url": "https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest",
        "python_module": "requests",
        "primary_claim": "public programmatic lookup of PubChem compound data",
    },
    "openbabel_python": {
        "name": "Open Babel Python bindings",
        "kind": "chemistry_toolkit_bindings",
        "official_url": "https://open-babel.readthedocs.io/en/latest/UseTheLibrary/Python.html",
        "python_module": "openbabel",
        "primary_claim": "Open Babel library access from Python",
    },
}

FEATURES = [
    {
        "id": "chemical_file_conversion",
        "label": "Chemical file conversion",
        "scbe": False,
        "openbabel_obabel": True,
        "rdkit_python": True,
        "pubchem_pug_rest": False,
    },
    {
        "id": "smiles_structure_parsing",
        "label": "SMILES/scientific structure parsing",
        "scbe": True,
        "openbabel_obabel": True,
        "rdkit_python": True,
        "pubchem_pug_rest": True,
    },
    {
        "id": "descriptor_fingerprint_workflows",
        "label": "Descriptors/fingerprints",
        "scbe": True,
        "openbabel_obabel": True,
        "rdkit_python": True,
        "pubchem_pug_rest": True,
    },
    {
        "id": "forcefield_or_conformer_workflows",
        "label": "Forcefield/conformer workflows",
        "scbe": False,
        "openbabel_obabel": True,
        "rdkit_python": True,
        "pubchem_pug_rest": False,
    },
    {
        "id": "symbolic_atomic_token_flow",
        "label": "Symbolic atomic token flow",
        "scbe": True,
        "openbabel_obabel": False,
        "rdkit_python": False,
        "pubchem_pug_rest": False,
    },
    {
        "id": "governance_semantic_reaction_mapping",
        "label": "Governance/semantic reaction mapping",
        "scbe": True,
        "openbabel_obabel": False,
        "rdkit_python": False,
        "pubchem_pug_rest": False,
    },
    {
        "id": "machine_readable_cli_json",
        "label": "Machine-readable CLI JSON",
        "scbe": True,
        "openbabel_obabel": False,
        "rdkit_python": False,
        "pubchem_pug_rest": True,
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_command(command: list[str], timeout_s: int = 30) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "status": "missing",
            "command": command,
            "duration_ms": 0,
            "returncode": None,
            "error": str(exc),
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "command": command,
            "duration_ms": int((time.perf_counter() - t0) * 1000),
            "returncode": None,
            "error": f"timed out after {timeout_s}s",
        }

    duration_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "command": command,
        "duration_ms": duration_ms,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def python_module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def command_available(candidates: list[str]) -> str | None:
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
    return None


def probe_scbe(timeout_s: int) -> dict[str, Any]:
    probes = {
        "atomize": run_command(
            [sys.executable, "scbe.py", "chem", "atomize", "release payload after compare", "--json"],
            timeout_s=timeout_s,
        ),
        "bonds": run_command(
            [
                sys.executable,
                "scbe.py",
                "chem",
                "bonds",
                "0.1",
                "0.15",
                "0.2",
                "0.12",
                "0.14",
                "0.16",
                "--json",
            ],
            timeout_s=timeout_s,
        ),
        "orbitals": run_command(
            [sys.executable, "scbe.py", "chem", "orbitals", "--json"],
            timeout_s=timeout_s,
        ),
        "convert_rdkit": run_command(
            [
                sys.executable,
                "scbe.py",
                "chem",
                "convert",
                "--smiles",
                "CCO",
                "--to",
                "can",
                "--engine",
                "rdkit",
                "--json",
            ],
            timeout_s=timeout_s,
        ),
        "convert_openbabel": run_command(
            [
                sys.executable,
                "scbe.py",
                "chem",
                "convert",
                "--smiles",
                "CCO",
                "--to",
                "can",
                "--engine",
                "openbabel",
                "--json",
            ],
            timeout_s=timeout_s,
        ),
    }
    return {
        "name": "SCBE chem",
        "kind": "symbolic_governance_chemistry_cli",
        "installed": True,
        "status": "pass" if all(row["status"] == "pass" for row in probes.values()) else "fail",
        "probes": probes,
    }


def probe_openbabel(timeout_s: int) -> dict[str, Any]:
    found = command_available(BASELINES["openbabel_obabel"]["local_commands"])
    row = {
        **BASELINES["openbabel_obabel"],
        "installed": bool(found),
        "path": found,
        "status": "missing",
        "probes": {},
    }
    if not found:
        return row
    row["probes"]["version"] = run_command([found, "-V"], timeout_s=timeout_s)
    row["probes"]["smiles_to_canonical"] = run_command([found, "-:CCO", "-ocan"], timeout_s=timeout_s)
    row["status"] = "pass" if all(p["status"] == "pass" for p in row["probes"].values()) else "fail"
    return row


def probe_openbabel_python(timeout_s: int) -> dict[str, Any]:
    installed = python_module_available("openbabel")
    row = {
        **BASELINES["openbabel_python"],
        "installed": installed,
        "status": "missing",
        "probes": {},
    }
    if not installed:
        return row
    code = (
        "from openbabel import openbabel as ob; "
        "conv=ob.OBConversion(); "
        "ok=conv.SetInAndOutFormats('smi','can'); "
        "mol=ob.OBMol(); "
        "read=conv.ReadString(mol,'CCO'); "
        "print(ok, read, conv.WriteString(mol).strip())"
    )
    row["probes"]["smiles_to_canonical"] = run_command([sys.executable, "-c", code], timeout_s=timeout_s)
    row["status"] = "pass" if row["probes"]["smiles_to_canonical"]["status"] == "pass" else "fail"
    return row


def probe_rdkit(timeout_s: int) -> dict[str, Any]:
    installed = python_module_available("rdkit")
    row = {
        **BASELINES["rdkit_python"],
        "installed": installed,
        "status": "missing",
        "probes": {},
    }
    if not installed:
        return row
    code = (
        "from rdkit import Chem; "
        "from rdkit.Chem import Descriptors; "
        "m=Chem.MolFromSmiles('CCO'); "
        "print(Chem.MolToSmiles(m), round(Descriptors.MolWt(m), 3))"
    )
    row["probes"]["smiles_descriptor"] = run_command([sys.executable, "-c", code], timeout_s=timeout_s)
    row["status"] = "pass" if row["probes"]["smiles_descriptor"]["status"] == "pass" else "fail"
    return row


def probe_pubchem(timeout_s: int, live: bool) -> dict[str, Any]:
    installed = python_module_available("requests")
    row = {
        **BASELINES["pubchem_pug_rest"],
        "installed": installed,
        "status": "not_run" if installed else "missing",
        "live_network": live,
        "probes": {},
    }
    if not installed or not live:
        return row
    url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/ethanol/property/MolecularFormula/JSON"
    code = (
        "import requests; "
        f"r=requests.get({url!r}, timeout={timeout_s}); "
        "print(r.status_code); "
        "print(r.text[:200])"
    )
    row["probes"]["ethanol_formula"] = run_command([sys.executable, "-c", code], timeout_s=timeout_s + 5)
    row["status"] = "pass" if row["probes"]["ethanol_formula"]["status"] == "pass" else "fail"
    return row


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    tools = report["tools"]
    scientific = ["openbabel_obabel", "openbabel_python", "rdkit_python", "pubchem_pug_rest"]
    installed_scientific = [key for key in scientific if tools[key]["installed"]]
    passing_scientific = [key for key in installed_scientific if tools[key]["status"] == "pass"]
    return {
        "decision": (
            "SCBE_SYMBOLIC_PASS__SCIENTIFIC_BASELINES_MISSING"
            if tools["scbe"]["status"] == "pass" and not passing_scientific
            else "COMPARISON_AVAILABLE"
        ),
        "scbe_probe_status": tools["scbe"]["status"],
        "scientific_baselines_installed": installed_scientific,
        "scientific_baselines_passing": passing_scientific,
        "positioning": (
            "SCBE benchmarks as a symbolic chemistry/governance CLI with delegated "
            "molecule-native adapters for RDKit and Open Babel bindings. It still "
            "does not replace those engines for full file conversion, fingerprints, "
            "forcefields, or conformer workflows."
        ),
        "next_step": (
            "Expand the adapter layer to SDF/MOL file IO, fingerprints, conformers, and "
            "forcefield probes; repair the local obabel.exe wrapper or install the "
            "official Open Babel Windows package if raw obabel CLI conversion is required."
        ),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# SCBE Chemistry Industry Benchmark",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Decision: `{summary['decision']}`",
        "",
        "## Summary",
        "",
        summary["positioning"],
        "",
        "## Local Tool Status",
        "",
        "| Tool | Installed | Status | Purpose |",
        "| --- | --- | --- | --- |",
    ]
    for _key, row in report["tools"].items():
        lines.append(
            f"| {row['name']} | {row['installed']} | {row['status']} | {row.get('primary_claim', row['kind'])} |"
        )

    lines.extend(
        [
            "",
            "## Feature Matrix",
            "",
            "| Feature | SCBE | Open Babel | RDKit | PubChem |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for feature in report["feature_matrix"]:
        lines.append(
            "| {label} | {scbe} | {openbabel_obabel} | {rdkit_python} | {pubchem_pug_rest} |".format(**feature)
        )

    lines.extend(["", "## Next Step", "", summary["next_step"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def build_report(out_dir: Path, timeout_s: int = 30, live_pubchem: bool = False) -> dict[str, Any]:
    report = {
        "schema_version": "scbe_chemistry_industry_benchmark_v1",
        "generated_at_utc": utc_now(),
        "claim_boundary": [
            "Compares CLI/tooling capability surfaces and local smoke probes.",
            "Does not claim chemical validity, wet-lab validity, or scientific equivalence.",
            "SCBE's chemistry lane is symbolic/governance chemistry unless delegated to external engines.",
        ],
        "industry_sources": BASELINES,
        "feature_matrix": FEATURES,
        "tools": {
            "scbe": probe_scbe(timeout_s),
            "openbabel_obabel": probe_openbabel(timeout_s),
            "openbabel_python": probe_openbabel_python(timeout_s),
            "rdkit_python": probe_rdkit(timeout_s),
            "pubchem_pug_rest": probe_pubchem(timeout_s, live=live_pubchem),
        },
    }
    report["summary"] = summarize(report)

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"chemistry_industry_benchmark_{stamp}.json").write_text(payload, encoding="utf-8")
    (out_dir / "latest_report.json").write_text(payload, encoding="utf-8")
    write_markdown(report, out_dir / f"chemistry_industry_benchmark_{stamp}.md")
    write_markdown(report, out_dir / "LATEST.md")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print full JSON report")
    parser.add_argument("--timeout", type=int, default=30, help="timeout per local probe in seconds")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="artifact output directory")
    parser.add_argument("--live-pubchem", action="store_true", help="run a live PubChem PUG-REST probe")
    args = parser.parse_args()

    report = build_report(Path(args.out_dir), timeout_s=args.timeout, live_pubchem=args.live_pubchem)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print(f"scbe chemistry industry benchmark: decision={summary['decision']}")
        print(f"scbe={summary['scbe_probe_status']}")
        print(f"scientific_installed={','.join(summary['scientific_baselines_installed']) or 'none'}")
        print(f"report={Path(args.out_dir) / 'LATEST.md'}")
    return 0 if report["tools"]["scbe"]["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
