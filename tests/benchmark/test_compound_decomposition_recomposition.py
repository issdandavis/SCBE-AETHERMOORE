from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "compound_decomposition_recomposition.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "compound_decomposition_recomposition", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compound_recomposition_recovers_known_solutions(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(tmp_path)

    assert report["schema_version"] == "scbe_compound_decomposition_recomposition_v1"
    assert report["summary"]["decision"] == "PASS"
    assert report["summary"]["case_count"] >= 25
    assert report["summary"]["passed"] == report["summary"]["case_count"]
    for case in report["cases"]:
        packet = case["reaction_state_packet"]
        assert packet["schema_version"] == "scbe_reaction_state_packet_v1"
        assert packet["classification"] == "LOSSY_RECOVERABLE"
        assert packet["packet_hash"]
        assert packet["domain"] == "chem"
    assert (tmp_path / "latest_report.json").exists()
    assert (tmp_path / "LATEST.md").exists()


def test_atom_only_mud_step_exposes_ambiguity() -> None:
    module = _load_module()

    ethanol_case = next(case for case in module.CASES if case.name == "ethanol")
    result = module.run_case(ethanol_case)
    recomposition = next(
        step for step in result["steps"] if step["name"] == "recomposition_search"
    )

    assert recomposition["output"]["atom_only_ambiguous"] is True
    assert "dimethyl ether" in recomposition["output"]["atom_only_candidates"]
    assert recomposition["output"]["selected"]["name"] == "ethanol"
    assert (
        result["reaction_state_packet"]["recalculation"]["extra"]["atom_only_ambiguous"]
        is True
    )


def test_expanded_corpus_covers_multiple_functional_families() -> None:
    module = _load_module()

    case_names = {case.name for case in module.CASES}

    assert "ethanol" in case_names
    assert "acetone" in case_names
    assert "propanal" in case_names
    assert "benzene" in case_names
    assert "glycine" in case_names
    assert "caffeine" in case_names
    assert "glucose" in case_names


def test_compound_recomposition_cli_smoke(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark/compound_decomposition_recomposition.py",
            "--out-dir",
            str(tmp_path),
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
    assert "scbe_compound_decomposition_recomposition_v1" in proc.stdout
    assert (tmp_path / "latest_report.json").exists()
