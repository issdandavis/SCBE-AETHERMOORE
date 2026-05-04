from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "training_data" / "build_chemistry_adapter_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_chemistry_adapter_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assistant_payload(row: dict) -> dict:
    payload = json.loads(row["messages"][-1]["content"])
    assert isinstance(payload, dict)
    return payload


def test_records_cover_adapter_fix_invariants() -> None:
    module = _load_module()

    rows = module.build_records()
    scenarios = {row["metadata"]["scenario"] for row in rows}

    assert "invalid_smiles_error_path_booleans" in scenarios
    assert "ethanol_elements_are_real" in scenarios
    assert "pressure_threshold_denies_valid_molecule" in scenarios
    assert "score_for_sft_contains_training_fields" in scenarios


def test_invalid_smiles_row_requires_all_adapter_booleans() -> None:
    module = _load_module()

    row = next(
        row for row in module.build_records() if row["metadata"]["scenario"] == "invalid_smiles_error_path_booleans"
    )
    payload = _assistant_payload(row)

    assert payload["expected"]["can_promote"] is False
    assert payload["expected"]["rdkit_ok"] is False
    assert payload["expected"]["valence_ok"] is False
    assert payload["expected"]["fusion_ok"] is False
    assert "missing required fields" in " ".join(payload["reasoning"])


def test_real_element_row_blocks_all_fe_regression() -> None:
    module = _load_module()

    row = next(row for row in module.build_records() if row["metadata"]["scenario"] == "ethanol_elements_are_real")
    payload = _assistant_payload(row)

    assert payload["expected_elements"] == ["C", "C", "O"]
    assert payload["forbidden_elements"] == ["Fe", "Fe", "Fe"]
    assert "Generic ENTITY fallback to Fe" in " ".join(payload["reasoning"])


def test_write_outputs_and_copy_kaggle(tmp_path: Path) -> None:
    module = _load_module()
    out_dir = tmp_path / "sft"
    kaggle_dir = tmp_path / "kaggle"

    result = module.write_outputs(out_dir, copy_kaggle=True, kaggle_dir=kaggle_dir)

    assert result["ok"] is True
    assert result["train_records"] > result["eval_records"] >= 1
    assert (out_dir / module.TRAIN_NAME).exists()
    assert (out_dir / module.EVAL_NAME).exists()
    assert (out_dir / module.MANIFEST_NAME).exists()
    assert (kaggle_dir / module.TRAIN_NAME).exists()
    assert (kaggle_dir / module.EVAL_NAME).exists()
    assert (kaggle_dir / module.MANIFEST_NAME).exists()

    manifest = json.loads((out_dir / module.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "chemistry_adapter_invariants_manifest_v1"
    assert "all_elements_as_fe" in manifest["gate"]["blocked"]
    assert "missing_adapter_booleans" in manifest["gate"]["blocked"]
