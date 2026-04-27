from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_binary_interpretation_matrix_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_binary_interpretation_matrix_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_dataset_from_binary_workbook(tmp_path: Path) -> None:
    module = _load_module()
    workbook = tmp_path / "binary.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "ASCII Table"
    ws.append([None, "ASCII TABLE"])
    ws.append([None, "Printable characters"])
    ws.append([None, "Decimal", "Hex", "Binary", "Character"])
    ws.append([None, 65, "0x41", "0b01000001", "'A'"])
    wb.save(workbook)

    output = tmp_path / "binary.sft.jsonl"
    manifest_path = tmp_path / "manifest.json"
    manifest = module.build_dataset(workbook, output, manifest_path)

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert manifest["record_count"] == 1
    assert rows[0]["track"] == "geoseal_coding_binary_substrate"
    assert rows[0]["metadata"]["sheet"] == "ASCII Table"
    assert "0b01000001" in rows[0]["messages"][1]["content"]
    assert "GeoSeal use" in rows[0]["messages"][2]["content"]
