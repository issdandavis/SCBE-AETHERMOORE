from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

from scripts.python_pack_guard import guard_artifact, scan_member_names


def test_scan_member_names_accepts_bounded_runtime_surface() -> None:
    violations, missing = scan_member_names(
        [
            "scbe-aethermoore-3.3.0/README.md",
            "scbe-aethermoore-3.3.0/LICENSE",
            "scbe-aethermoore-3.3.0/spiralverse/__init__.py",
            "scbe-aethermoore-3.3.0/spiralverse/cli.py",
        ]
    )

    assert violations == []
    assert missing == []


def test_scan_member_names_flags_overshipped_paths() -> None:
    violations, missing = scan_member_names(
        [
            "scbe-aethermoore-3.3.0/README.md",
            "scbe-aethermoore-3.3.0/LICENSE",
            "scbe-aethermoore-3.3.0/spiralverse/__init__.py",
            "scbe-aethermoore-3.3.0/spiralverse/cli.py",
            "scbe-aethermoore-3.3.0/training-data/upg/governance_agent_loops_upg_seed.jsonl",
        ]
    )

    assert missing == []
    assert violations == [
        (
            "scbe-aethermoore-3.3.0/training-data/upg/governance_agent_loops_upg_seed.jsonl",
            "training data should not ship in Python artifacts",
        )
    ]


def test_guard_artifact_reads_wheel_and_sdist(tmp_path: Path) -> None:
    wheel_path = tmp_path / "scbe_aethermoore-3.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as zf:
        zf.writestr("README.md", "readme")
        zf.writestr("LICENSE", "mit")
        zf.writestr("spiralverse/__init__.py", "")
        zf.writestr("spiralverse/cli.py", "def main():\n    return 0\n")

    sdist_path = tmp_path / "scbe-aethermoore-3.3.0.tar.gz"
    with tarfile.open(sdist_path, "w:gz") as tf:
        for name, content in [
            ("scbe-aethermoore-3.3.0/README.md", "readme"),
            ("scbe-aethermoore-3.3.0/LICENSE", "mit"),
            ("scbe-aethermoore-3.3.0/spiralverse/__init__.py", ""),
            ("scbe-aethermoore-3.3.0/spiralverse/cli.py", "def main():\n    return 0\n"),
        ]:
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))

    for artifact in (wheel_path, sdist_path):
        violations, missing = guard_artifact(artifact)
        assert violations == []
        assert missing == []
