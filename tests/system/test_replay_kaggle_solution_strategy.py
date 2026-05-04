from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "replay_kaggle_solution_strategy.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("replay_kaggle_solution_strategy", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_replay_compares_known_templates(tmp_path: Path) -> None:
    module = _load_module()

    payload = module.run_replay(tmp_path)

    assert payload["schema_version"] == "scbe_kaggle_solution_strategy_replay_v1"
    assert payload["aggregate"]["templates"] >= 5
    assert payload["aggregate"]["average_top5_coverage"] >= 0.6
    assert "substrate_requirements" in payload
    assert "substrate_adjusted_operation_ranks" in payload
    assert (tmp_path / "kaggle_solution_strategy_replay_latest.json").exists()
    assert (tmp_path / "kaggle_solution_strategy_replay_latest.md").exists()
    markdown = (tmp_path / "kaggle_solution_strategy_replay_latest.md").read_text(encoding="utf-8")
    assert "Kor'aelin" in markdown
    assert "Cassisivadan" in markdown


def test_template_mapping_preserves_operation_ranks() -> None:
    module = _load_module()
    ranks = {
        "op_training_eval_loop": 1,
        "op_rag_source_ingest": 5,
        "op_ensemble_model_council": 8,
    }
    template = {
        "competition": "x",
        "source_url": "https://example.test",
        "reported_result": "dry",
        "winner_path": ["validation_spine", "feature_factory", "diverse_ensemble"],
        "notes": "n",
    }

    row = module._compare_template(template, ranks, ranks)

    assert row["operation_ranks"]["op_training_eval_loop"] == 1
    assert row["operation_ranks"]["op_rag_source_ingest"] == 5
    assert row["operation_ranks"]["op_ensemble_model_council"] == 8
    assert row["raw_operation_ranks"]["op_ensemble_model_council"] == 8
    assert row["top5_hits"] == 2
    assert row["substrate_route"]["geoseal_required"] is True
    assert "Runethic" in row["substrate_route"]["sacred_tongues_full_names"]
    assert row["substrate_route"]["office_roles"]["op_training_eval_loop"] == "phase_lead"
    assert row["substrate_route"]["office_roles"]["op_ensemble_model_council"] == "desk_pair"


def test_substrate_adjusted_ranks_preserve_raw_ranks() -> None:
    module = _load_module()
    raw = {
        "op_training_eval_loop": 1,
        "op_rag_source_ingest": 2,
        "op_pathfinding_repo": 3,
        "op_public_benchmark_packet": 4,
        "op_sort_dirty_tree": 5,
        "op_ensemble_model_council": 6,
    }

    adjusted = module._substrate_adjusted_rank_map(raw)

    assert raw["op_ensemble_model_council"] == 6
    assert adjusted["op_ensemble_model_council"] <= 5
    assert set(adjusted) == set(raw)


def test_cli_writes_replay(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/replay_kaggle_solution_strategy.py",
            "--output-root",
            str(tmp_path),
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
    assert payload["claim_boundary"].startswith("dry strategy replay")
    assert "substrate-adjusted ranks" in payload["claim_boundary"]
    assert "bureaucratic_machine_flow" in payload["substrate_requirements"]
    assert (tmp_path / "kaggle_solution_strategy_replay_latest.json").exists()
