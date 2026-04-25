from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "system" / "topological_operator_packet.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "topological_operator_packet", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_artifact_wraps_operator_packet_without_raw_command_field() -> None:
    module = _load_module()

    artifact = module.build_artifact("korah aelin dahru")

    assert artifact["schema_version"] == "scbe-topological-operator-artifact-v1"
    assert artifact["command_chars"] == len("korah aelin dahru")
    assert artifact["packet"]["schema_version"] == "scbe-topological-operator-tree-v1"
    assert (
        artifact["packet"]["floating_point_policy"]
        == "forbidden for consensus signatures"
    )
    assert "korah aelin dahru" not in json.dumps(artifact)


def test_write_artifact_creates_parent_directories(tmp_path: Path) -> None:
    module = _load_module()
    artifact = module.build_artifact("korah aelin dahru")

    output = module.write_artifact(artifact, tmp_path / "nested" / "packet.json")

    assert output.exists()
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert (
        saved["packet"]["signature"]["sha256"]
        == artifact["packet"]["signature"]["sha256"]
    )


def test_cli_runs_from_repo_root_and_writes_packet(tmp_path: Path) -> None:
    output = tmp_path / "packet.json"

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--command",
            "korah aelin dahru",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["floating_point_policy"] == "forbidden for consensus signatures"
    assert output.exists()
