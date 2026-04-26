from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "auto_file_tracker.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("auto_file_tracker", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_snapshot_tracks_hash_without_copying_file_contents(tmp_path: Path) -> None:
    module = _load_module()
    tracked = tmp_path / "tracked.txt"
    tracked.write_text(
        "secret-ish content that must not enter packets", encoding="utf-8"
    )

    snapshot = module.build_snapshot([tracked], label="unit", repo_root=tmp_path)

    record = snapshot["files"][0]
    assert record["path"] == "tracked.txt"
    assert record["exists"] is True
    assert record["sha256"] == hashlib.sha256(tracked.read_bytes()).hexdigest()
    assert record["size_bytes"] == tracked.stat().st_size
    assert "secret-ish content" not in json.dumps(snapshot)
    assert snapshot["content_policy"].startswith("hash-only")


def test_snapshot_uses_formation_route_tuple(tmp_path: Path) -> None:
    module = _load_module()
    tracked = tmp_path / "tracked.py"
    tracked.write_text("print('ok')\n", encoding="utf-8")
    route = module.FormationRoute(
        topic="agent.bus.verify",
        source="pytest",
        tongue="RU",
        trust_class="test",
        mission_class="coding",
        locality="local",
        delivery_class="interactive_reliable",
    )

    snapshot = module.build_snapshot(
        [tracked], label="route-test", route=route, repo_root=tmp_path
    )

    assert snapshot["route"]["tuple"] == [
        "agent.bus.verify",
        "pytest",
        "RU",
        "test",
        "coding",
        "local",
    ]
    assert snapshot["route"]["delivery_class"] == "interactive_reliable"


def test_snapshot_marks_missing_files(tmp_path: Path) -> None:
    module = _load_module()
    missing = tmp_path / "missing.md"

    snapshot = module.build_snapshot(
        [missing], label="missing-test", repo_root=tmp_path
    )

    assert snapshot["summary"]["tracked"] == 1
    assert snapshot["summary"]["exists"] == 0
    assert snapshot["summary"]["missing"] == 1
    assert snapshot["files"][0]["exists"] is False
    assert snapshot["files"][0]["sha256"] is None


def test_write_snapshot_emits_latest_history_and_changed_files(tmp_path: Path) -> None:
    module = _load_module()
    tracked = tmp_path / "dirty.txt"
    tracked.write_text("dirty\n", encoding="utf-8")
    snapshot = module.build_snapshot([tracked], label="write-test", repo_root=tmp_path)
    snapshot["files"][0]["git_status"] = "??"
    snapshot["summary"]["dirty_or_untracked"] = 1

    written = module.write_snapshot(snapshot, tmp_path / "out")

    assert written["snapshot"].exists()
    assert written["history"].exists()
    assert written["changed"].exists()
    latest = json.loads(written["snapshot"].read_text(encoding="utf-8"))
    changed = json.loads(written["changed"].read_text(encoding="utf-8"))
    assert latest["label"] == "write-test"
    assert changed["files"][0]["path"] == "dirty.txt"
    assert len(written["history"].read_text(encoding="utf-8").splitlines()) == 1
