from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "observable_state_watcher.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("observable_state_watcher", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_watcher_builds_three_lanes_without_raw_prompt_or_file_content(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mirror_dir = tmp_path / "mirror" / "series-a"
    mirror_dir.mkdir(parents=True)
    (mirror_dir / "latest_round.json").write_text(
        json.dumps(
            {
                "selected_provider": "offline",
                "task": {"sha256": "a" * 64, "chars": 29, "type": "coding"},
                "operation_shape": {
                    "root_value": 12026,
                    "signature_binary": "1" * 64,
                },
                "primary_bus": [
                    {
                        "provider": "offline",
                        "role": "play",
                        "score": 8.0,
                        "reason": "local",
                    }
                ],
                "secondary_bus": [
                    {
                        "provider": "ollama",
                        "role": "watch",
                        "score": 8.0,
                        "watch_policy": "observe",
                    }
                ],
                "tertiary_bus": [{"provider": "openai", "role": "rest", "reason": "remote blocked"}],
            }
        ),
        encoding="utf-8",
    )
    dispatch_log = tmp_path / "dispatch.jsonl"
    dispatch_log.write_text(
        json.dumps(
            {
                "event_id": "evt1",
                "route": {"provider": "offline"},
                "prompt": {"sha256": "b" * 64, "chars": 17},
                "result": {
                    "provider": "offline",
                    "model": "offline-model",
                    "finish_reason": "offline_deterministic",
                    "text_sha256": "c" * 64,
                    "text_chars": 19,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    file_snapshot = tmp_path / "snapshot.json"
    file_snapshot.write_text(
        json.dumps(
            {
                "summary": {"tracked": 1, "exists": 1},
                "files": [
                    {
                        "path": "secret.txt",
                        "git_status": "??",
                        "sha256": "d" * 64,
                        "size_bytes": 42,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    state = module.build_watcher_state(
        series_id="series-a",
        mirror_root=tmp_path / "mirror",
        dispatch_log=dispatch_log,
        file_snapshot_path=file_snapshot,
    )

    assert set(state["lanes"]) == {"action", "live_text", "packet_state"}
    assert state["lanes"]["action"]["selected_provider"] == "offline"
    assert state["lanes"]["action"]["operation_shape"]["root_value"] == 12026
    assert state["lanes"]["live_text"]["events"][0]["text_sha256_prefix"] == "c" * 16
    assert state["lanes"]["packet_state"]["file_packets"][0]["sha256_binary"] == "1101" * 12
    dumped = json.dumps(state)
    assert "hidden chain-of-thought" in dumped
    assert "raw file contents" in dumped
    assert "actual secret content" not in dumped
    assert "Use the SCBE mirror-room bus" not in dumped


def test_watcher_weights_are_normalized_phi_lanes() -> None:
    module = _load_module()

    weights = module.WatcherWeights().normalized()

    assert set(weights) == {"action", "live_text", "packet_state"}
    assert round(sum(weights.values()), 8) == 1.0
    assert weights["action"] < weights["live_text"] < weights["packet_state"]


def test_write_watcher_state_creates_output_file(tmp_path: Path) -> None:
    module = _load_module()
    state = {"schema_version": "scbe-observable-state-watcher-v1", "lanes": {}}

    output = module.write_watcher_state(state, tmp_path / "watcher.json")

    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "scbe-observable-state-watcher-v1"
