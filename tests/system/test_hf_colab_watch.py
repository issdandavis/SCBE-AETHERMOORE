from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "hf_colab_watch.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hf_colab_watch", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def result_with_a_cells(count: int) -> dict:
    langs = ["py", "jl", "rs", "hs"]
    models = ["Qwen2.5-Coder-0.5B", "Qwen2.5-Coder-1.5B"]
    result = {"meta": {"stamp": "20260702_050228"}, "A": {}}
    made = 0
    for model in models:
        result["A"][model] = {}
        for lang in langs:
            if made >= count:
                break
            result["A"][model][lang] = {"greedy": 0.5, "curve": {"1": 0.5}}
            made += 1
    return result


def test_stage_state_detects_stale_partial_a() -> None:
    mod = load_module()
    source = mod.ResultSource(
        path=Path("results_20260702_050228.json"),
        name="results_20260702_050228.json",
        modified_at=datetime(2026, 7, 2, 6, 12, tzinfo=timezone.utc),
        repo_id="issdandavis/scbe-bench-results",
    )
    payload = mod.stage_state(result_with_a_cells(7), source, stale_minutes=0.0)

    assert payload["schema_version"] == "scbe_colab_hf_watch_v1"
    assert payload["ok"] is True
    assert payload["state"]["status"] == "stale_partial_a"
    assert payload["state"]["a_cells"] == 7
    assert payload["state"]["b_complete"] is False


def test_stage_state_detects_complete_result() -> None:
    mod = load_module()
    result = result_with_a_cells(8)
    result["B"] = {"v1": {}, "v2": {}}
    result["C"] = {"base": {}, "adapter": {}}
    source = mod.ResultSource(path=Path("results_20260702_060000.json"), name="results_20260702_060000.json", modified_at=None)

    payload = mod.stage_state(result, source, stale_minutes=45.0)

    assert payload["state"]["status"] == "complete"
    assert payload["state"]["a_complete"] is True
    assert payload["state"]["b_complete"] is True
    assert payload["state"]["c_complete"] is True


def test_cli_file_mode_writes_receipt(tmp_path: Path) -> None:
    mod = load_module()
    result_path = tmp_path / "results_20260702_050228.json"
    result_path.write_text(json.dumps(result_with_a_cells(8) | {"B": {}, "C": {}}), encoding="utf-8")
    receipt_dir = Path("artifacts") / "pytest_tmp" / "colab_hf_watch"

    rc = mod.main(["--file", str(result_path), "--write-receipt", "--receipt-dir", str(receipt_dir), "--json"])

    assert rc == 0
    receipts = sorted((REPO_ROOT / receipt_dir).glob("hf_watch_*.json"))
    assert receipts
    receipt = json.loads(receipts[-1].read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "scbe_colab_hf_watch_v1"
    assert receipt["receipt_path"].startswith("artifacts/pytest_tmp/colab_hf_watch/")
