from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "system" / "context_librarian.py"


def load_module():
    spec = importlib.util.spec_from_file_location("context_librarian", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_state(path: Path, **overrides):
    payload = {
        "agent_id": path.stem,
        "role": "builder",
        "status": "in_progress",
        "summary": "working",
        "open_tasks": ["wire pair harness", "run tests"],
        "completed_tasks": ["inspect repo"],
        "changed_paths": ["scripts/example.py"],
        "proof": ["pytest tests/example.py -q"],
        "blockers": [],
        "next_actions": ["continue"],
        "claims": {"smoke": "pending"},
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_merge_states_preserves_provenance_and_conflicts(tmp_path):
    module = load_module()
    left = tmp_path / "codex.json"
    right = tmp_path / "polly.json"
    _write_state(left, agent_id="agent.codex", changed_paths=["src/shared.py"], claims={"smoke": "green"})
    _write_state(right, agent_id="agent.polly", changed_paths=["src/shared.py"], claims={"smoke": "red"})

    payload = module.merge_states(module._load_state(left), module._load_state(right), mission_id="dual-air")

    assert payload["schema_version"] == "scbe_context_librarian_compact_v1"
    assert payload["mission_id"] == "dual-air"
    assert payload["sacred_tongue_bijection"]["ok"] is True
    assert {agent["agent_id"] for agent in payload["agents"]} == {"agent.codex", "agent.polly"}
    conflict_types = {conflict["type"] for conflict in payload["conflicts"]}
    assert {"path_contention", "claim_conflict"} <= conflict_types
    assert payload["helper_policy"]["model_may_resolve_conflicts"] is False


def test_completed_tasks_are_removed_from_open_tasks(tmp_path):
    module = load_module()
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    _write_state(left, open_tasks=["a", "b"], completed_tasks=["a"])
    _write_state(right, open_tasks=["b", "c"], completed_tasks=["c"])

    payload = module.merge_states(module._load_state(left), module._load_state(right))

    assert payload["merged"]["open_tasks"] == ["b"]
    assert payload["merged"]["completed_tasks"] == ["a", "c"]


def test_write_compact_creates_latest_json_and_markdown(tmp_path):
    module = load_module()
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    _write_state(left)
    _write_state(right, agent_id="agent.navigator", role="navigator")
    payload = module.merge_states(module._load_state(left), module._load_state(right))

    paths = module.write_compact(payload, tmp_path / "out")

    assert Path(paths["json"]).exists()
    assert Path(paths["markdown"]).exists()
    assert Path(paths["latest_json"]).exists()
    assert "Shared Context Compact" in Path(paths["markdown"]).read_text(encoding="utf-8")


def test_context_librarian_cli_json(tmp_path):
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    _write_state(left)
    _write_state(right, agent_id="agent.navigator", role="navigator")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/system/context_librarian.py",
            str(left),
            str(right),
            "--mission-id",
            "pair-smoke",
            "--json",
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mission_id"] == "pair-smoke"
    assert payload["helper_policy"]["truth_source"] == "packet_fields_and_proof_links"
