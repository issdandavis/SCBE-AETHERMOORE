from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_coding_system_full_sft.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_coding_system_full_sft", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_coding_system_full_sft_preserves_all_lanes() -> None:
    module = _load_module()
    manifest = module.build()

    assert manifest["counts"]["total"] == 56
    assert manifest["counts"]["train"] == 48
    assert manifest["counts"]["holdout"] == 8

    train_path = Path(manifest["outputs"]["train"])
    holdout_path = Path(manifest["outputs"]["holdout"])
    assert train_path.exists()
    assert holdout_path.exists()

    rows = _jsonl(train_path) + _jsonl(holdout_path)
    assert len(rows) == 56

    primaries = {row["meta"].get("primary") for row in rows if row["meta"].get("primary")}
    assert primaries == {"KO", "AV", "RU", "CA", "UM", "DR"}

    payloads = [json.loads(row["messages"][-1]["content"]) for row in rows]
    single_payloads = [item for item in payloads if item["schema_version"] == "scbe_full_coding_system_answer_v1"]
    assert single_payloads

    required = {
        "coding_primary",
        "music_theory",
        "atomic_tokenizer",
        "binary_transport",
        "code_lane_contract",
        "workflow_composition",
        "boundary",
    }
    for payload in single_payloads:
        assert required <= set(payload)
        assert payload["binary_transport"]["first_16_hex"]
        assert payload["atomic_tokenizer"]["stisa_field_names"]
        assert payload["workflow_composition"]["semantic_compound_commands"]
        boundary = payload["boundary"]
        assert "Semantic meaning" in boundary["semantic_vs_transport"]
        assert "Material chemistry" in boundary["chemistry_scope"]


def test_coding_system_full_sft_roundabout_records_cover_music_and_mirrors() -> None:
    module = _load_module()
    manifest = module.build()
    rows = _jsonl(Path(manifest["outputs"]["train"])) + _jsonl(Path(manifest["outputs"]["holdout"]))
    roundabouts = [
        json.loads(row["messages"][-1]["content"])
        for row in rows
        if row["meta"].get("kind") == "cross_primary_roundabout"
    ]

    assert len(roundabouts) == 8
    for payload in roundabouts:
        assert len(payload["lanes"]) == 6
        assert payload["mirror_pairs"] == {"KO": "DR", "AV": "CA", "RU": "UM"}
        assert payload["foundation_triangle"] == ["KO/Python", "AV/TypeScript", "RU/Rust"]
        assert "runtime tests" in payload["music_theory_use"]
        assert all(lane["first_8_hex"] for lane in payload["lanes"])
