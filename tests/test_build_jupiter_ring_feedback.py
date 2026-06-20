"""Tests for the Jupiter-ring feedback dataset builder."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "training" / "build_jupiter_ring_feedback.py"
    spec = importlib.util.spec_from_file_location("build_jupiter_ring_feedback", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_records_pairs_prompt_output_and_evidence() -> None:
    mod = _load()
    records = mod.build_records()
    assert records
    sample = records[0]
    assert sample["category"] == "agentic-feedback-ring"
    roles = [m["role"] for m in sample["messages"]]
    assert roles[:3] == ["system", "user", "assistant"]
    assert any("Outcome evidence:" in m["content"] for m in sample["messages"])
    assert sample["metadata"]["deployment_status"] == "eval_only"


def test_write_outputs_creates_jsonl_and_manifest(tmp_path: Path) -> None:
    mod = _load()
    out = tmp_path / "ring.jsonl"
    manifest_path = tmp_path / "manifest.json"
    manifest = mod.write_outputs(out, manifest_path)
    assert manifest["schema_version"] == "scbe_jupiter_ring_feedback_v1"
    assert manifest["record_count"] > 0
    lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == manifest["record_count"]
