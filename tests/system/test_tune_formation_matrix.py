from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "tune_formation_matrix.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("tune_formation_matrix", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_sweep_returns_ranked_candidates(tmp_path: Path) -> None:
    module = _load_module()

    payload = module.run_sweep(grid=3, top_n=5, output_path=tmp_path / "tuning.json")

    assert payload["schema_version"] == "scbe_formation_matrix_tuning_v1"
    assert payload["candidate_count"] == 5 * 3**5
    assert len(payload["top"]) == 5
    assert payload["best"]["score"] >= payload["top"][-1]["score"]
    assert Path(tmp_path / "tuning.json").exists()


def test_best_candidate_has_square_graph_matrix() -> None:
    module = _load_module()

    payload = module.run_sweep(grid=3, top_n=3, output_path=None)
    best = payload["best"]
    matrix = best["graph_matrix"]

    assert len(matrix) == best["agents"]
    assert all(len(row) == best["agents"] for row in matrix)
    assert all(matrix[index][index] == 0.0 for index in range(best["agents"]))


def test_graph_matrix_gate_roles_receive_extra_weight() -> None:
    module = _load_module()

    low_gate = module.build_graph_matrix(agents=4, interaction=0.5, gate_pressure=0.2)
    high_gate = module.build_graph_matrix(agents=4, interaction=0.5, gate_pressure=1.2)

    assert high_gate[0][2] > low_gate[0][2]
    assert high_gate[1][2] > low_gate[1][2]


def test_cli_no_write_outputs_json() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/tune_formation_matrix.py",
            "--grid",
            "2",
            "--top",
            "2",
            "--no-write",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["candidate_count"] == 5 * 2**5
    assert len(payload["top"]) == 2
