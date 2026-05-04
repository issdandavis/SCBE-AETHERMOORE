from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "training_data" / "build_go_game_go_lang_strategy_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_go_game_go_lang_strategy_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_go_strategy_records_bridge_game_and_language() -> None:
    module = _load_module()

    rows = module.build_records()
    blob = "\n".join(json.dumps(row, sort_keys=True) for row in rows)

    assert len(rows) == 10
    assert "go_game_go_lang_agentic_strategy_v1" in blob
    assert "atari" in blob
    assert "ko" in blob
    assert "go_language_habit" in blob
    assert all(row["metadata"]["language"] == "Go" for row in rows)


def test_split_keeps_eval_small_and_deterministic() -> None:
    module = _load_module()

    train, eval_rows = module.split_records(module.build_records())

    assert len(train) == 8
    assert len(eval_rows) == 2
    assert {row["metadata"]["split"] for row in train} == {"train"}
    assert {row["metadata"]["split"] for row in eval_rows} == {"eval"}


def test_write_outputs_copy_kaggle_and_manifest_math_boosters(tmp_path: Path) -> None:
    module = _load_module()
    out_dir = tmp_path / "sft"
    kaggle_dir = tmp_path / "kaggle"

    result = module.write_outputs(out_dir, copy_kaggle=True, kaggle_dir=kaggle_dir)

    assert result["ok"] is True
    assert (out_dir / module.TRAIN_NAME).exists()
    assert (out_dir / module.EVAL_NAME).exists()
    assert (kaggle_dir / module.TRAIN_NAME).exists()
    manifest = json.loads((out_dir / module.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["train_records"] == 8
    assert manifest["eval_records"] == 2
    assert "curriculum_difficulty_scheduling" in manifest["math_boosters"]
