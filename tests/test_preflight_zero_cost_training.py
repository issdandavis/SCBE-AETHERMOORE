"""Tests for zero-cost training dataset preflight."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec_path = REPO_ROOT / "scripts" / "system" / "preflight_zero_cost_training.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("preflight_zero_cost_training", spec_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_preflight_ok_when_all_files_exist(tmp_path: Path) -> None:
    mod = _load()
    train = tmp_path / "t.jsonl"
    eval_f = tmp_path / "e.jsonl"
    train.write_text("{}\n", encoding="utf-8")
    eval_f.write_text("{}\n", encoding="utf-8")
    profile = {
        "profile_id": "test-profile",
        "dataset": {
            "root": str(tmp_path),
            "train_files": [train.name],
            "eval_files": [eval_f.name],
        },
    }
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile), encoding="utf-8")
    result = mod.run_preflight(p)
    assert result["ok"] is True
    assert result["missing_count"] == 0


def test_preflight_fails_on_missing(tmp_path: Path) -> None:
    mod = _load()
    profile = {
        "profile_id": "test-profile",
        "dataset": {
            "root": str(tmp_path),
            "train_files": ["nope.jsonl"],
            "eval_files": [],
        },
    }
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile), encoding="utf-8")
    result = mod.run_preflight(p)
    assert result["ok"] is False
    assert "nope.jsonl" in result["missing"]


def test_preflight_fails_on_empty_file(tmp_path: Path) -> None:
    mod = _load()
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    profile = {
        "profile_id": "test-profile",
        "dataset": {"root": str(tmp_path), "train_files": [empty.name], "eval_files": []},
    }
    p = tmp_path / "profile.json"
    p.write_text(json.dumps(profile), encoding="utf-8")
    result = mod.run_preflight(p)
    assert result["ok"] is False
    assert empty.name in result["empty"]
