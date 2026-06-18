#!/usr/bin/env python3
"""SCBE chemistry/STISTA CLI capability lane.

This is a local executable evidence lane for SCBE's chemistry-inspired systems:
atomic tokenization/STISTA, chemical fusion, tongue bond scoring, ternary
chemistry proxies, semantic atomic braid, and GeoSeed orbitals.

It is intentionally not a wet-lab chemistry planner score. The lane proves the
CLI has deterministic symbolic chemistry surfaces, tests, receipts, and private
proof pointers that can be cited without publishing patent text.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "benchmarks" / "chemistry_cli_capability"

TEST_SLICES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "stista-atomic-tokenizer",
        (
            "tests/governance/test_atomic_tokenization_and_fusion.py",
            "tests/test_geoseal_cli_tokenizer_atomic.py",
            "tests/tokenizer/test_atomic_workflow_units.py",
        ),
    ),
    (
        "symbolic-chemistry",
        (
            "tests/test_chemical_bonds.py",
            "tests/test_ternary_dirichlet_chemistry.py",
            "tests/test_semantic_atomic_braid.py",
        ),
    ),
    (
        "geoseed-orbitals",
        ("tests/geoseed/test_orbital_model.py",),
    ),
)

CAPABILITY_FILES: tuple[str, ...] = (
    "python/scbe/atomic_tokenization.py",
    "python/scbe/chemical_fusion.py",
    "python/scbe/history_reducer.py",
    "python/scbe/ca_opcode_table.py",
    "src/geoseed/orbital_model.py",
    "src/governance/chemical_bonds.py",
    "src/minimal/ternary_dirichlet_chemistry.py",
    "src/spiralverse/semantic_atomic_braid.py",
    "src/tokenizer/atomic_workflow_units.py",
    "src/tokenizer/chemistry_command_stack.py",
    "src/training/execution_feedback.py",
)

PRIVATE_PROOF_FILES: tuple[str, ...] = (
    "docs/legal/patent-workbench/application_status.json",
    "docs/legal/patent-workbench/manifest.json",
    "docs/legal/patent-workbench/claim_support_scan.json",
    "docs/legal/patent-workbench/filing_readiness_checklist.json",
    "docs/legal/patent-workbench/benchmarks/resonant_thought_lattice_benchmark.json",
)


@dataclass(frozen=True)
class TestReceipt:
    lane: str
    ok: bool
    command: list[str]
    duration_ms: int
    returncode: int
    stdout_tail: str
    stderr_tail: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def run_pytest_slice(name: str, paths: tuple[str, ...], timeout_s: int) -> TestReceipt:
    command = [sys.executable, "-m", "pytest", *paths, "-q"]
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    t0 = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        env=env,
        check=False,
    )
    duration_ms = int((time.perf_counter() - t0) * 1000)
    return TestReceipt(
        lane=name,
        ok=proc.returncode == 0,
        command=command,
        duration_ms=duration_ms,
        returncode=proc.returncode,
        stdout_tail=proc.stdout[-2000:],
        stderr_tail=proc.stderr[-2000:],
    )


def import_module(name: str):
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    python_root = REPO_ROOT / "python"
    if str(python_root) not in sys.path:
        sys.path.insert(0, str(python_root))
    return importlib.import_module(name)


def direct_runtime_probes() -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []

    try:
        atomic = import_module("python.scbe.atomic_tokenization")
        fusion = import_module("python.scbe.chemical_fusion")
        tokens = ["encrypt", "payload", "before", "allow"]
        states = [atomic.map_token_to_atomic_state(token, context_class="cli") for token in tokens]
        fused = fusion.fuse_atomic_states(states)
        active_tongues = [tongue for tongue, value in fused.tau_hat.items() if value != 0]
        probes.append(
            {
                "id": "stista_atomic_fusion_probe",
                "ok": bool(states) and bool(fused.tau_hat) and bool(fused.reconstruction_votes),
                "tokens": tokens,
                "state_count": len(states),
                "active_tongues": active_tongues,
                "signed_edge_tension": round(float(fused.signed_edge_tension), 6),
                "coherence_penalty": round(float(fused.coherence_penalty), 6),
                "valence_pressure": round(float(fused.valence_pressure), 6),
                "claim": "STISTA maps CLI tokens into atomic states and fuses them deterministically.",
            }
        )
    except Exception as exc:  # pragma: no cover - reported in artifact
        probes.append({"id": "stista_atomic_fusion_probe", "ok": False, "error": repr(exc)})

    try:
        bonds = import_module("src.governance.chemical_bonds")
        report = bonds.TongueMolecule([0.1, 0.15, 0.2, 0.12, 0.14, 0.16]).report()
        probes.append(
            {
                "id": "tongue_molecule_probe",
                "ok": 0.0 <= float(report.stability) <= 1.0 and len(report.bonds) == 3,
                "dominant_class": report.dominant_class,
                "stability": round(float(report.stability), 6),
                "bond_count": len(report.bonds),
                "claim": "Tongue interactions are scored as molecule-like bonds with bounded stability.",
            }
        )
    except Exception as exc:  # pragma: no cover - reported in artifact
        probes.append({"id": "tongue_molecule_probe", "ok": False, "error": repr(exc)})

    try:
        ternary = import_module("src.minimal.ternary_dirichlet_chemistry")
        activities = ternary.TernaryActivities(positive=1.0, negative=1.0, neutral=0.25)
        sigma = ternary.equilibrium_sigma(activities)
        gap = ternary.chemical_potential_gap(sigma, activities)
        probes.append(
            {
                "id": "ternary_equilibrium_probe",
                "ok": abs(float(gap)) < 1e-9 and 0.0 <= float(sigma) <= 1.0,
                "equilibrium_sigma": round(float(sigma), 9),
                "potential_gap": round(float(gap), 12),
                "claim": "Chemistry-style equilibrium proxy returns a finite matched-potential state.",
            }
        )
    except Exception as exc:  # pragma: no cover - reported in artifact
        probes.append({"id": "ternary_equilibrium_probe", "ok": False, "error": repr(exc)})

    try:
        orbital = import_module("src.geoseed.orbital_model")
        summary = orbital.orbital_summary()
        checkpoint = summary.get("golden_ratio_checkpoint", {})
        probes.append(
            {
                "id": "geoseed_orbital_probe",
                "ok": summary.get("total_m_states") == 36 and bool(checkpoint.get("exact")),
                "schema_version": summary.get("schema_version"),
                "total_m_states": summary.get("total_m_states"),
                "ca_radius": checkpoint.get("poincare_r"),
                "claim": "GeoSeed maps six tongues to hyperbolic orbital shells with golden-ratio checkpoint.",
            }
        )
    except Exception as exc:  # pragma: no cover - reported in artifact
        probes.append({"id": "geoseed_orbital_probe", "ok": False, "error": repr(exc)})

    return probes


def file_inventory(paths: tuple[str, ...], include_hash: bool) -> list[dict[str, Any]]:
    rows = []
    for rel in paths:
        path = REPO_ROOT / rel
        rows.append(
            {
                "path": rel,
                "exists": path.exists(),
                "sha256": sha256_file(path) if include_hash else None,
            }
        )
    return rows


def build_report(out_dir: Path, run_tests: bool = True, timeout_s: int = 180) -> dict[str, Any]:
    receipts = [run_pytest_slice(name, paths, timeout_s) for name, paths in TEST_SLICES] if run_tests else []
    probes = direct_runtime_probes()
    capability_files = file_inventory(CAPABILITY_FILES, include_hash=True)
    private_proof = file_inventory(PRIVATE_PROOF_FILES, include_hash=True)

    tests_passed = sum(1 for receipt in receipts if receipt.ok)
    probes_passed = sum(1 for probe in probes if probe.get("ok") is True)
    capability_present = sum(1 for row in capability_files if row["exists"])
    private_present = sum(1 for row in private_proof if row["exists"])
    total_checks = len(receipts) + len(probes) + len(capability_files)
    passed_checks = tests_passed + probes_passed + capability_present
    pass_rate = passed_checks / total_checks if total_checks else 0.0

    decision = "PASS" if tests_passed == len(receipts) and probes_passed == len(probes) else "HOLD"
    if not run_tests:
        decision = "INVENTORY_ONLY" if probes_passed == len(probes) else "HOLD"

    report = {
        "schema_version": "scbe_chemistry_cli_capability_v1",
        "generated_at_utc": utc_now(),
        "commit": git_commit(),
        "claim_boundary": [
            "Local executable evidence for SCBE symbolic chemistry, STISTA atomic tokenization, "
            "and GeoSeed orbital surfaces.",
            "Not a validated wet-lab chemistry planner, not an RDKit/DeepChem/Materials Project "
            "replacement, and not a public leaderboard score.",
            "Private proof entries expose path presence and SHA-256 hashes only; patent text and "
            "internal licensing content are not copied into this artifact.",
        ],
        "summary": {
            "decision": decision,
            "pass_rate": pass_rate,
            "tests_passed": tests_passed,
            "tests_total": len(receipts),
            "probes_passed": probes_passed,
            "probes_total": len(probes),
            "capability_files_present": capability_present,
            "capability_files_total": len(capability_files),
            "private_proof_present": private_present,
            "private_proof_total": len(private_proof),
        },
        "positioning": {
            "website_safe_claim": (
                "SCBE includes an executable chemistry-native CLI lane for symbolic chemistry, "
                "STISTA atomic token flow, and GeoSeed orbital invariants, with receipts and "
                "private-proof hashes."
            ),
            "avoid_claim": (
                "Do not claim exclusive market coverage or real-world chemistry validity without "
                "external comparison and domain validation."
            ),
            "middle_layer": (
                "Use SCBE Chem Middle Layer to translate between STISTA symbolic chemistry and "
                "external scientific engines such as RDKit, Open Babel, ASE, DeepChem, NASA CEA, and PAHdb."
            ),
            "next_product_step": (
                "Add scbe chem commands for atomize, bridge, fuse, bonds, orbitals, and proof "
                "export on top of this benchmark lane."
            ),
        },
        "test_receipts": [receipt.__dict__ for receipt in receipts],
        "runtime_probes": probes,
        "capability_files": capability_files,
        "private_proof": {
            "policy": "hash-only private proof inventory",
            "rows": private_proof,
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"chemistry_cli_capability_{stamp}.json").write_text(payload, encoding="utf-8")
    (out_dir / "latest_report.json").write_text(payload, encoding="utf-8")
    write_markdown(report, out_dir / f"chemistry_cli_capability_{stamp}.md")
    write_markdown(report, out_dir / "LATEST.md")
    return report


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# SCBE Chemistry/STISTA CLI Capability",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Commit: `{report['commit']}`",
        f"- Decision: `{summary['decision']}`",
        f"- Pass rate: `{summary['pass_rate']:.1%}`",
        "",
        "## What This Proves",
        "",
        report["positioning"]["website_safe_claim"],
        "",
        "## Runtime Probes",
        "",
        "| Probe | OK | Claim |",
        "| --- | --- | --- |",
    ]
    for probe in report["runtime_probes"]:
        lines.append(f"| {probe['id']} | {probe.get('ok')} | {probe.get('claim', probe.get('error', 'n/a'))} |")

    lines.extend(["", "## Test Receipts", "", "| Lane | OK | Duration ms |", "| --- | --- | ---: |"])
    for receipt in report["test_receipts"]:
        lines.append(f"| {receipt['lane']} | {receipt['ok']} | {receipt['duration_ms']} |")

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Local symbolic chemistry and atomic-tokenizer evidence only.",
            "- Not a wet-lab chemistry planner score.",
            "- Private proof is represented by hashes and presence checks, not copied legal content.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print full JSON report")
    parser.add_argument(
        "--inventory-only", action="store_true", help="skip pytest slices and run probes/inventory only"
    )
    parser.add_argument("--timeout", type=int, default=180, help="timeout per pytest slice in seconds")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="artifact output directory")
    args = parser.parse_args()

    report = build_report(Path(args.out_dir), run_tests=not args.inventory_only, timeout_s=args.timeout)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print(
            "scbe chemistry capability: "
            f"decision={summary['decision']} "
            f"tests={summary['tests_passed']}/{summary['tests_total']} "
            f"probes={summary['probes_passed']}/{summary['probes_total']} "
            f"private_proof={summary['private_proof_present']}/{summary['private_proof_total']}"
        )
        print(f"report={Path(args.out_dir) / 'LATEST.md'}")
    return 0 if report["summary"]["decision"] in {"PASS", "INVENTORY_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
