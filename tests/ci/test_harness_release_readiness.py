from __future__ import annotations

from pathlib import Path

from scripts.ci.harness_release_readiness import build_release_readiness


def test_release_readiness_hashes_files_and_reports_dirty_state(tmp_path: Path) -> None:
    (tmp_path / "src/agent_comms").mkdir(parents=True)
    (tmp_path / "src/agent_comms/packet.py").write_text("packet\n", encoding="utf-8")
    (tmp_path / "tests/agent_comms").mkdir(parents=True)
    (tmp_path / "tests/agent_comms/test_packet.py").write_text("test\n", encoding="utf-8")

    def fake_status(_root, _paths):
        return {"src/agent_comms/packet.py": "M", "tests/agent_comms/test_packet.py": "clean"}

    report = build_release_readiness(
        root=tmp_path,
        paths=["src/agent_comms/packet.py", "tests/agent_comms/test_packet.py"],
        git_status_func=fake_status,
    )

    assert report["schema_version"] == "scbe_harness_release_readiness_v1"
    assert report["summary"]["files"] == 2
    assert report["summary"]["missing"] == 0
    assert report["summary"]["uncommitted"] == 1
    assert report["gates"]["ready_to_publish"] is False
    assert report["files"][0]["sha256"]


def test_release_readiness_flags_missing_expected_file(tmp_path: Path) -> None:
    report = build_release_readiness(
        root=tmp_path,
        paths=["src/agent_comms/missing.py"],
        git_status_func=lambda _root, _paths: {},
    )

    assert report["summary"]["missing"] == 1
    assert report["missing"] == ["src/agent_comms/missing.py"]
    assert report["gates"]["all_expected_files_exist"] is False
