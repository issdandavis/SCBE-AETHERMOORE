"""Regression tests for Stage 6 balanced SFT extra builder."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_stage6_balanced_extras.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_stage6_balanced_extras", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_balanced_lattice_rows_have_messages_and_metadata() -> None:
    mod = _load_module()
    rows = mod.build_lattice_rows()
    assert len(rows) >= 8
    for row in rows:
        assert "messages" in row
        assert row["record_type"] == "COMMAND_LATTICE"
        assert row["metadata"]["risk_tier"] in {"low", "medium", "high"}


def test_balanced_cross_rows_are_dialogue_json() -> None:
    mod = _load_module()
    rows = mod.build_cross_rows()
    assert len(rows) >= 10
    for row in rows:
        assert row["meta"]["program"] == "cross_tongue_dialogue_bijective"
        assistant = row["messages"][-1]["content"]
        payload = json.loads(assistant)
        assert "semantic_verification" in payload
        assert payload["semantic_verification"]["roundtrip_ok"] is True


@pytest.mark.parametrize(
    "filename,min_lines",
    [
        ("command_lattice_seed_train_balanced.sft.jsonl", 8),
        ("cross_tongue_dialogue_bijective_v1_train_balanced.sft.jsonl", 10),
    ],
)
def test_committed_balanced_files_exist(filename: str, min_lines: int) -> None:
    path = Path(__file__).resolve().parents[1] / "training-data" / "sft" / filename
    if not path.exists():
        pytest.skip(f"missing {filename}; run scripts/build_stage6_balanced_extras.py")
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= min_lines
