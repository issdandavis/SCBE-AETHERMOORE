from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "multi_model_compound_matrix.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("multi_model_compound_matrix", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_council_packet_ranks_ten_candidate_operations(tmp_path: Path) -> None:
    module = _load_module()

    packet = module.build_council_packet(
        tuning_path=tmp_path / "formation_tuning.json",
        output_root=tmp_path / "council",
        top_n=10,
    )

    assert packet["schema_version"] == "scbe_multi_model_compound_matrix_v1"
    assert len(packet["candidate_operations"]) == 10
    scores = [op["score"] for op in packet["candidate_operations"]]
    assert scores == sorted(scores, reverse=True)
    assert packet["council_conclusion"]["primary_use"] == packet["candidate_operations"][0]["id"]
    assert (tmp_path / "council" / "compound_matrix_packet.json").exists()
    assert (tmp_path / "council" / "full_system_review.md").exists()


def test_solution_patterns_include_leakage_and_oof_guards(tmp_path: Path) -> None:
    module = _load_module()

    packet = module.build_council_packet(tuning_path=tmp_path / "formation_tuning.json", output_root=tmp_path / "out")
    pattern_ids = {pattern["id"] for pattern in packet["solution_patterns"]}

    assert "metric_first_validation" in pattern_ids
    assert "oof_stack" in pattern_ids
    assert "fold_safe_pseudo_labeling" in pattern_ids
    assert any("leakage" in pattern["failure_mode"].lower() for pattern in packet["solution_patterns"])


def test_render_review_doc_mentions_sources_and_ranked_operations(tmp_path: Path) -> None:
    module = _load_module()
    packet = module.build_council_packet(tuning_path=tmp_path / "formation_tuning.json", output_root=tmp_path / "out")

    doc = module.render_review_doc(packet)

    assert "HYDRA Compound Matrix Council Review" in doc
    assert "Winning-Solution Patterns To Reuse" in doc
    assert "Ranked Candidate Operations" in doc
    assert "developer.nvidia.com" in doc


def test_cli_writes_packet(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/multi_model_compound_matrix.py",
            "--tuning-path",
            str(tmp_path / "formation_tuning.json"),
            "--output-root",
            str(tmp_path / "compound"),
            "--top",
            "4",
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
    assert len(payload["candidate_operations"]) == 4
    assert (tmp_path / "compound" / "compound_matrix_packet.json").exists()
