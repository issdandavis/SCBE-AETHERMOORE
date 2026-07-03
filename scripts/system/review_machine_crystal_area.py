"""Full adjacent-surface review for the Machine Crystal area.

This command is intentionally broader than a unit test and narrower than a full
repo test run. It reviews every adjacent surface created for the Machine Crystal:

* primitive octahedral runtime
* higher shape macros
* PHDM path-state injection gate
* cube/octahedron/Fano bridge
* Bhargava arithmetic cube/factorial overlays
* p/n/e chemistry+nuclear conservation cube
* particle chemistry balancer + valence rung
* cube-to-adjacent-geometry relation map
* benchmark scripts
* docs/specs/research files
* artifact receipt paths

Usage:
    python scripts/system/review_machine_crystal_area.py
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.scbe.machine_crystal import demo_receipt
from python.scbe.machine_crystal_bhargava import bhargava_crystal_receipt
from python.scbe.machine_crystal_bhargava_factorial import bhargava_factorial_receipt
from python.scbe.machine_crystal_dual import duality_receipt
from python.scbe.machine_crystal_geometry_map import geometry_relation_receipt
from python.scbe.machine_crystal_higher import benchmark_cases, path_state_inject
from python.scbe.machine_crystal_particle_chem import particle_chem_receipt
from python.scbe.machine_crystal_pne_cube import pne_cube_receipt


REQUIRED_PATHS = [
    "python/scbe/machine_crystal.py",
    "python/scbe/machine_crystal_higher.py",
    "python/scbe/machine_crystal_dual.py",
    "python/scbe/machine_crystal_bhargava.py",
    "python/scbe/machine_crystal_bhargava_factorial.py",
    "python/scbe/machine_crystal_geometry_map.py",
    "python/scbe/machine_crystal_pne_cube.py",
    "python/scbe/machine_crystal_particle_chem.py",
    "scripts/benchmarks/bench_machine_crystal_higher.py",
    "scripts/benchmarks/bench_machine_crystal_dual.py",
    "scripts/benchmarks/bench_machine_crystal_bhargava.py",
    "scripts/benchmarks/bench_machine_crystal_bhargava_factorial.py",
    "docs/specs/MACHINE_CRYSTAL_GEOMETRIC_TURING_OBJECT_2026-06-27.md",
    "docs/specs/MACHINE_CRYSTAL_DUAL_FANO_BRIDGE_2026-06-27.md",
    "docs/research/MACHINE_CRYSTAL_PATH_STATE_RESEARCH_2026-06-27.md",
    "docs/research/MACHINE_CRYSTAL_PATH_STATE_EVIDENCE_2026-06-27.csv",
    "docs/research/MACHINE_CRYSTAL_PATH_STATE_OPEN_QUESTIONS_2026-06-27.md",
    "docs/research/MACHINE_CRYSTAL_BHARGAVA_CUBE_OVERLAY_2026-06-27.md",
    "docs/research/MACHINE_CRYSTAL_BHARGAVA_FACTORIAL_2026-06-27.md",
    "docs/research/MACHINE_CRYSTAL_GEOMETRY_RELATION_MAP_2026-06-27.md",
    "docs/research/MACHINE_CRYSTAL_PNE_CUBE_2026-06-27.md",
    "docs/research/MACHINE_CRYSTAL_PARTICLE_CHEM_2026-06-27.md",
]


BENCH_COMMANDS = [
    [sys.executable, "scripts/benchmarks/bench_machine_crystal_higher.py"],
    [sys.executable, "scripts/benchmarks/bench_machine_crystal_dual.py"],
    [sys.executable, "scripts/benchmarks/bench_machine_crystal_bhargava.py"],
    [sys.executable, "scripts/benchmarks/bench_machine_crystal_bhargava_factorial.py"],
    [sys.executable, "-m", "python.scbe.machine_crystal_pne_cube"],
    [sys.executable, "-m", "python.scbe.machine_crystal_particle_chem"],
    [sys.executable, "-m", "python.scbe.machine_crystal_geometry_map"],
]


def _check(name: str, passed: bool, detail: Any = None) -> dict:
    return {
        "name": name,
        "passed": bool(passed),
        "detail": detail,
    }


def _run_command(command: list[str]) -> dict:
    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    return {
        "command": command,
        "exit_code": proc.returncode,
        "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def review() -> dict:
    checks: list[dict] = []

    primitive = demo_receipt()
    checks.append(
        _check(
            "primitive_shape_expression_outputs_03",
            primitive["shape_receipt"]["receipt"]["output_hex"] == "03",
            primitive["shape_receipt"]["receipt"],
        )
    )
    checks.append(
        _check(
            "primitive_direct_and_shape_hash_match",
            primitive["program"]["sha256"] == primitive["shape_receipt"]["program"]["sha256"],
            {
                "direct": primitive["program"]["sha256"],
                "shape": primitive["shape_receipt"]["program"]["sha256"],
            },
        )
    )

    higher = benchmark_cases()
    checks.append(
        _check(
            "higher_copy_emit_65_cases",
            higher["copy_emit_passed"] and higher["copy_emit_cases"] == 65,
            higher,
        )
    )
    checks.append(
        _check(
            "higher_quasicrystal_unique_128",
            higher["quasicrystal_programs"] == 128
            and higher["quasicrystal_unique_hashes"] == 128,
            {
                "programs": higher["quasicrystal_programs"],
                "unique": higher["quasicrystal_unique_hashes"],
                "claim_boundary": "distinct_programs_not_quasicrystal_proof",
            },
        )
    )

    safe = path_state_inject(
        "star*5 prism cube lens",
        "Tetrahedron,Cube,Octahedron,Dodecahedron,Icosahedron",
    )
    risky = path_state_inject(
        "star*5 prism cube lens",
        "Tetrahedron,Great Stellated Dodecahedron,Cube",
    )
    checks.append(
        _check(
            "safe_phdm_path_executes",
            safe["injection"]["decision"] == "EXECUTED"
            and safe["injection"]["receipt"]["output_hex"] == "05",
            safe["injection"],
        )
    )
    checks.append(
        _check(
            "risky_phdm_path_does_not_execute",
            risky["injection"]["decision"] != "EXECUTED",
            risky["injection"],
        )
    )

    dual = duality_receipt()
    checks.append(
        _check(
            "dual_fano_bridge_passes",
            dual["verdict"] == "PASS" and all(dual["checks"].values()),
            dual["checks"],
        )
    )

    bhargava = bhargava_crystal_receipt()
    checks.append(
        _check(
            "bhargava_cube_overlay_passes",
            bhargava["verdict"] == "PASS" and all(bhargava["checks"].values()),
            bhargava["checks"],
        )
    )

    factorial = bhargava_factorial_receipt()
    checks.append(
        _check(
            "bhargava_factorial_layer_passes",
            factorial["verdict"] == "PASS" and all(factorial["checks"].values()),
            factorial["checks"],
        )
    )

    pne = pne_cube_receipt()
    checks.append(
        _check(
            "pne_chemistry_nuclear_cube_passes",
            pne["verdict"] == "PASS" and all(pne["checks"].values()),
            pne["checks"],
        )
    )

    particle_chem = particle_chem_receipt()
    checks.append(
        _check(
            "particle_chem_balancer_valence_passes",
            particle_chem["verdict"] == "PASS" and all(particle_chem["checks"].values()),
            particle_chem["checks"],
        )
    )

    relation_map = geometry_relation_receipt()
    checks.append(
        _check(
            "geometry_relation_map_passes",
            relation_map["verdict"] == "PASS" and all(relation_map["checks"].values()),
            relation_map["checks"],
        )
    )

    path_checks = []
    for rel in REQUIRED_PATHS:
        exists = (ROOT / rel).exists()
        path_checks.append({"path": rel, "exists": exists})
    checks.append(_check("required_adjacent_files_exist", all(p["exists"] for p in path_checks), path_checks))

    command_results = [_run_command(command) for command in BENCH_COMMANDS]
    checks.append(
        _check(
            "benchmark_scripts_exit_zero",
            all(result["exit_code"] == 0 for result in command_results),
            command_results,
        )
    )

    artifact_dir = ROOT / "artifacts/machine_crystal"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_checks = [
        {
            "path": "artifacts/machine_crystal/higher_benchmark.json",
            "exists": (ROOT / "artifacts/machine_crystal/higher_benchmark.json").exists(),
        },
        {
            "path": "artifacts/machine_crystal/dual_fano_receipt.json",
            "exists": (ROOT / "artifacts/machine_crystal/dual_fano_receipt.json").exists(),
        },
        {
            "path": "artifacts/machine_crystal/bhargava_cube_overlay.json",
            "exists": (ROOT / "artifacts/machine_crystal/bhargava_cube_overlay.json").exists(),
        },
        {
            "path": "artifacts/machine_crystal/bhargava_factorial.json",
            "exists": (ROOT / "artifacts/machine_crystal/bhargava_factorial.json").exists(),
        },
        {
            "path": "artifacts/machine_crystal/pne_cube.json",
            "exists": (ROOT / "artifacts/machine_crystal/pne_cube.json").exists(),
        },
        {
            "path": "artifacts/machine_crystal/particle_chem.json",
            "exists": (ROOT / "artifacts/machine_crystal/particle_chem.json").exists(),
        },
        {
            "path": "artifacts/machine_crystal/geometry_relation_map.json",
            "exists": (ROOT / "artifacts/machine_crystal/geometry_relation_map.json").exists(),
        },
    ]
    checks.append(_check("benchmark_artifacts_exist", all(a["exists"] for a in artifact_checks), artifact_checks))

    passed = all(check["passed"] for check in checks)
    receipt = {
        "schema": "scbe_machine_crystal_area_review_v1",
        "scope": "machine_crystal_adjacent_surfaces",
        "command": "python scripts/system/review_machine_crystal_area.py",
        "verdict": "PASS" if passed else "FAIL",
        "checks": checks,
    }
    out_path = artifact_dir / "area_review.json"
    out_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    receipt["artifact_path"] = str(out_path.relative_to(ROOT)).replace("\\", "/")
    return receipt


def main() -> int:
    receipt = review()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
