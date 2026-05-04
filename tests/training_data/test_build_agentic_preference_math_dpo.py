from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "training_data" / "build_agentic_preference_math_dpo.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_agentic_preference_math_dpo", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_rows_have_dpo_shape_and_math_boosters() -> None:
    module = _load_module()

    rows = module.build_rows()

    assert len(rows) == 6
    for row in rows:
        assert {"prompt", "chosen", "rejected", "system", "meta", "id"} <= set(row)
        assert row["chosen"] != row["rejected"]
        assert row["meta"]["difficulty_band"] in {"easy", "medium", "hard"}
        assert row["meta"]["preference_granularity"] in {"answer", "action_step", "receipt_checklist"}
        assert row["meta"]["reward_stability_mode"] == "geometric_mean_clip"
        assert 0 < row["meta"]["geometric_mean_reward"] <= 1


def test_rows_block_raw_key_and_reward_outlier_failures() -> None:
    module = _load_module()

    blob = "\n".join(json.dumps(row, sort_keys=True) for row in module.build_rows())

    assert "DENY_RAW_KEY_HANDOFF" in blob
    assert "HOLD_OUTLIER" in blob
    assert "raw_api_keys" in blob
    assert "highest one-time score" in blob


def test_write_manifest_counts_granularity_and_difficulty(tmp_path: Path) -> None:
    module = _load_module()

    result = module.write_outputs(tmp_path)

    assert result["ok"] is True
    manifest = json.loads((tmp_path / module.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["row_count"] == 6
    assert manifest["difficulty_counts"] == {"easy": 2, "medium": 2, "hard": 2}
    assert manifest["training_boundary"]["not_for_sft_kaggle_kernel"] is True
    assert "multi_granularity_preference" in manifest["math_boosters"]
