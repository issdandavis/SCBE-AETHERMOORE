from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "system" / "kaggle_kernel_terminal.py"
SPEC = importlib.util.spec_from_file_location("kaggle_kernel_terminal", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_stage_smoke_preset_writes_wrapper_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("KAGGLE_USERNAME", "tester")

    manifest = MODULE.stage_preset(
        MODULE.PRESETS["smoke-governance"],
        target_dir=tmp_path / "smoke-stage",
        public=False,
    )

    stage_dir = Path(manifest["stage_dir"])
    metadata = json.loads((stage_dir / "kernel-metadata.json").read_text(encoding="utf-8"))
    runner = (stage_dir / "runner.py").read_text(encoding="utf-8")

    assert manifest["kernel_ref"] == "tester/scbe-governance-kaggle-smoke"
    assert metadata["id"] == "tester/scbe-governance-kaggle-smoke"
    assert metadata["code_file"] == "runner.py"
    assert metadata["enable_gpu"] is True
    assert metadata["enable_internet"] is True
    assert metadata["is_private"] is True
    assert (stage_dir / "kaggle_notebook_smoke.py").exists()
    assert "--require-kaggle" in runner
    assert "--micro-train" in runner


def test_stage_direct_preset_uses_source_file_as_code_file(tmp_path, monkeypatch):
    monkeypatch.setenv("KAGGLE_USERNAME", "tester")

    manifest = MODULE.stage_preset(
        MODULE.PRESETS["polly-comparison"],
        target_dir=tmp_path / "polly-stage",
        public=True,
    )

    stage_dir = Path(manifest["stage_dir"])
    metadata = json.loads((stage_dir / "kernel-metadata.json").read_text(encoding="utf-8"))

    assert metadata["id"] == "tester/scbe-polly-kaggle-comparison"
    assert metadata["code_file"] == "train_polly_kaggle_comparison.py"
    assert metadata["is_private"] is False
    assert (stage_dir / "train_polly_kaggle_comparison.py").exists()
