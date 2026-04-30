from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_ca_geoseal_smoke_repair_sft.py"
EXACT_MODULE_PATH = ROOT / "scripts" / "build_ca_opcode_exact_repair_sft.py"
COMBINED_MODULE_PATH = ROOT / "scripts" / "build_ca_geoseal_combined_repair_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_ca_geoseal_smoke_repair_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_exact_module():
    spec = importlib.util.spec_from_file_location("build_ca_opcode_exact_repair_sft", EXACT_MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_combined_module():
    spec = importlib.util.spec_from_file_location("build_ca_geoseal_combined_repair_sft", COMBINED_MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ca_geoseal_smoke_repair_builder_emits_targeted_rows(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    sft_root = tmp_path / "training-data" / "sft"
    monkeypatch.setattr(module, "SFT_ROOT", sft_root)
    monkeypatch.setattr(module, "TRAIN_OUT", sft_root / "ca_geoseal_smoke_repair_v1_train.sft.jsonl")
    monkeypatch.setattr(module, "HOLDOUT_OUT", sft_root / "ca_geoseal_smoke_repair_v1_holdout.sft.jsonl")
    monkeypatch.setattr(module, "MANIFEST_OUT", sft_root / "ca_geoseal_smoke_repair_v1_manifest.json")

    manifest = module.build()

    assert manifest["counts"]["train"] == 100
    assert manifest["counts"]["holdout"] == 3
    assert manifest["must_recall"]["abs"] == "0x09"
    assert manifest["must_recall"]["add"] == "0x00"
    assert manifest["must_recall"]["abs_add_sequence"] == ["0x09", "0x09", "0x00"]

    rows = [
        json.loads(line)
        for line in module.TRAIN_OUT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    serialized = json.dumps(rows)
    assert "CA opcode sequence for abs(a) + abs(b): 0x09, 0x09, 0x00" in serialized
    assert "def depth2_keys(obj: dict) -> list[str]:" in serialized
    assert "undefined helpers" in serialized
    assert {row["meta"]["kind"] for row in rows} == {"ca_opcode_abs_add", "depth2_json_keys"}


def test_ca_opcode_exact_repair_builder_emits_add_byte_drill(tmp_path: Path, monkeypatch) -> None:
    module = _load_exact_module()
    sft_root = tmp_path / "training-data" / "sft"
    monkeypatch.setattr(module, "SFT_ROOT", sft_root)
    monkeypatch.setattr(module, "TRAIN_OUT", sft_root / "ca_opcode_exact_repair_v2_train.sft.jsonl")
    monkeypatch.setattr(module, "HOLDOUT_OUT", sft_root / "ca_opcode_exact_repair_v2_holdout.sft.jsonl")
    monkeypatch.setattr(module, "MANIFEST_OUT", sft_root / "ca_opcode_exact_repair_v2_manifest.json")

    manifest = module.build()

    assert manifest["counts"]["train"] == 80
    assert manifest["counts"]["holdout"] == 2
    assert manifest["must_recall"]["abs"] == "0x09"
    assert manifest["must_recall"]["add"] == "0x00"
    assert manifest["must_recall"]["forbidden_add_opcode"] == "0x09"
    assert manifest["must_recall"]["abs_add_sequence"] == ["0x09", "0x09", "0x00"]

    rows = [
        json.loads(line)
        for line in module.TRAIN_OUT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    serialized = json.dumps(rows)
    assert "Never use 0x09 for add" in serialized
    assert "0x09, 0x09, 0x00" in serialized
    assert {row["meta"]["kind"] for row in rows} == {"ca_opcode_abs_add_exact"}


def test_ca_geoseal_combined_repair_builder_keeps_both_smoke_surfaces(tmp_path: Path, monkeypatch) -> None:
    module = _load_combined_module()
    sft_root = tmp_path / "training-data" / "sft"
    monkeypatch.setattr(module, "SFT_ROOT", sft_root)
    monkeypatch.setattr(module, "TRAIN_OUT", sft_root / "ca_geoseal_combined_repair_v3_train.sft.jsonl")
    monkeypatch.setattr(module, "HOLDOUT_OUT", sft_root / "ca_geoseal_combined_repair_v3_holdout.sft.jsonl")
    monkeypatch.setattr(module, "MANIFEST_OUT", sft_root / "ca_geoseal_combined_repair_v3_manifest.json")

    manifest = module.build()

    assert manifest["counts"]["train"] == 144
    assert manifest["counts"]["holdout"] == 4
    assert manifest["must_recall"]["abs_add_sequence"] == ["0x09", "0x09", "0x00"]

    rows = [
        json.loads(line)
        for line in module.TRAIN_OUT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    serialized = json.dumps(rows)
    assert "CA: 0x09, 0x09, 0x00" in serialized
    assert "def depth2_keys(obj: dict) -> list[str]:" in serialized
    assert {row["meta"]["kind"] for row in rows} == {"ca_opcode_abs_add_exact", "depth2_json_keys"}
