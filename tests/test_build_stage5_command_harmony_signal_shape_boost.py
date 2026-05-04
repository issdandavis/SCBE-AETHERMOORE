from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_stage5_command_harmony_signal_shape_boost.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_stage5_command_harmony_signal_shape_boost", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stage5_signal_shape_rows_cover_every_contract_kind() -> None:
    module = _load_module()
    train, holdout = module._build_rows()

    assert len(train) == 40
    assert len(holdout) == 4
    assert {row["metadata"]["kind"] for row in holdout} == set(module.KINDS)


def test_stage5_signal_shape_rows_start_with_required_prefix() -> None:
    module = _load_module()
    train, holdout = module._build_rows()

    for row in train + holdout:
        content = row["messages"][-1]["content"]
        kind = row["metadata"]["kind"]
        assert content.startswith("required-tokens: ")
        assert " ::" in content.splitlines()[0]
        for token in module.KINDS[kind]["required"]:
            assert token in content


def test_stage5_signal_shape_rows_reject_stale_command_markers() -> None:
    module = _load_module()
    train, holdout = module._build_rows()

    for row in train + holdout:
        content = row["messages"][-1]["content"]
        assert "command-harmony-map" not in content
        assert "--training-jsonl-output" not in content


def test_stage5_signal_shape_written_jsonl_is_valid() -> None:
    module = _load_module()
    module.main()

    train_rows = [
        json.loads(line) for line in module.TRAIN_OUT.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    holdout_rows = [
        json.loads(line) for line in module.HOLDOUT_OUT.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    manifest = json.loads(module.MANIFEST_OUT.read_text(encoding="utf-8"))

    assert len(train_rows) == manifest["train_rows"] == 40
    assert len(holdout_rows) == manifest["holdout_rows"] == 4
    assert manifest["repair_source"]["job_id"] == "69f69b559d85bec4d76f0e0e"
