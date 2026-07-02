from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "build_aethermon_agent_adapter_v0.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_aethermon_agent_adapter_v0", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_build_aethermon_adapter_target(tmp_path: Path) -> None:
    mod = load_module()
    receipts = tmp_path / "episode_receipts.jsonl"
    summary = tmp_path / "episode_summary.json"
    browser = tmp_path / "browser.sft.jsonl"
    coding = tmp_path / "coding.sft.jsonl"
    train = tmp_path / "train.sft.jsonl"
    holdout = tmp_path / "holdout.sft.jsonl"
    manifest_path = tmp_path / "manifest.json"
    profile_path = tmp_path / "profile.json"

    tick = {
        "tick": 1,
        "action": "RIGHT",
        "valid": True,
        "success": False,
        "events": ["move:right"],
        "policy": {"reason": "route to training pad", "observed_legal_actions": ["RIGHT", "REST"]},
        "before": {"turn": 0, "position": [1, 1], "legal_actions": ["RIGHT", "REST"]},
    }
    write_jsonl(receipts, [tick])
    summary.write_text(json.dumps({"success": True, "turns": 3, "total_reward": 1.0}), encoding="utf-8")
    seed_row = {
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
            {"role": "assistant", "content": "{}"},
        ],
        "meta": {"source": "seed"},
    }
    write_jsonl(browser, [seed_row])
    write_jsonl(coding, [seed_row])

    manifest = mod.build(
        mod.BuildInputs(
            receipts=receipts,
            summary=summary,
            browser_use=browser,
            coding_system=coding,
            train_out=train,
            holdout_out=holdout,
            manifest_out=manifest_path,
            profile_out=profile_path,
            train_ratio=0.75,
            base_model="Qwen/Qwen2.5-Coder-0.5B-Instruct",
            max_steps=40,
        )
    )

    assert manifest["counts"]["total"] == 4
    assert manifest["counts"]["train"] == 3
    assert manifest["counts"]["holdout"] == 1
    assert train.exists()
    assert holdout.exists()
    assert profile_path.exists()

    rows = [json.loads(line) for line in train.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["messages"]
    assert any(row["meta"].get("domain") == "aethermon" for row in rows)

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile["profile_id"] == "aethermon-agent-adapter-v0-local"
    assert profile["training"]["max_steps"] == 40
