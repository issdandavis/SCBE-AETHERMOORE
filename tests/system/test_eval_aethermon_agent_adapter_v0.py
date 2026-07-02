from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "eval_aethermon_agent_adapter_v0.py"


def load_module():
    spec = importlib.util.spec_from_file_location("eval_aethermon_agent_adapter_v0", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def action_row(action: str = "RIGHT") -> dict:
    observation = {"turn": 0, "position": [1, 1], "legal_actions": ["RIGHT", "REST"]}
    return {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "Choose the next AETHERMON action for this observation:\n" + json.dumps(observation)},
            {"role": "assistant", "content": json.dumps({"action": action, "reason": "move"})},
        ],
        "meta": {"domain": "aethermon", "kind": "action_policy_tick", "source": "receipt", "tick": 1},
    }


def json_row() -> dict:
    return {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "Return route JSON"},
            {"role": "assistant", "content": json.dumps({"route": "ok"})},
        ],
        "meta": {"domain": "browser_use", "source": "browser"},
    }


def test_oracle_mode_passes_gate(tmp_path: Path) -> None:
    mod = load_module()
    holdout = tmp_path / "holdout.jsonl"
    out = tmp_path / "receipt.json"
    write_jsonl(holdout, [action_row(), json_row()])

    receipt = mod.evaluate(holdout, mode="oracle", predictions_path=None, out_path=out)

    assert receipt["summary"]["rows"] == 2
    assert receipt["summary"]["rates"]["json_valid"] == 1.0
    assert receipt["summary"]["rates"]["aethermon_action_match"] == 1.0
    assert receipt["summary"]["promotion_gate"]["ok"] is True
    assert out.exists()


def test_abstain_mode_closes_gate(tmp_path: Path) -> None:
    mod = load_module()
    holdout = tmp_path / "holdout.jsonl"
    out = tmp_path / "receipt.json"
    write_jsonl(holdout, [action_row(), json_row()])

    receipt = mod.evaluate(holdout, mode="abstain", predictions_path=None, out_path=out)

    assert receipt["summary"]["abstained"] == 2
    assert receipt["summary"]["trusted"] == 0
    assert receipt["summary"]["promotion_gate"]["ok"] is False


def test_prediction_mode_catches_illegal_action(tmp_path: Path) -> None:
    mod = load_module()
    row = action_row()
    holdout = tmp_path / "holdout.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    out = tmp_path / "receipt.json"
    write_jsonl(holdout, [row])
    write_jsonl(predictions, [{"id": mod.row_id(row), "content": json.dumps({"action": "BATTLE"})}])

    receipt = mod.evaluate(holdout, mode="predictions", predictions_path=predictions, out_path=out)

    score = receipt["scores"][0]
    assert score["predicted_action"] == "BATTLE"
    assert score["legal_action"] is False
    assert score["action_match"] is False
    assert receipt["summary"]["promotion_gate"]["ok"] is False
