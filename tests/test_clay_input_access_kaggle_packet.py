from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.research.build_clay_input_access_kaggle_packet import (
    TRUST_PLACEHOLDERS,
    render_kernel_entry,
)
from scripts.research import run_clay_input_access_kaggle as runner


def test_kernel_template_materializes_every_external_trust_anchor(tmp_path: Path) -> None:
    source = Path(runner.__file__).resolve()
    destination = tmp_path / "kernel.py"
    anchors = {key: f"{index:064x}" for index, key in enumerate(TRUST_PLACEHOLDERS, 1)}
    render_kernel_entry(source, destination, anchors)
    text = destination.read_text(encoding="utf-8")
    assert not any(placeholder in text for placeholder in TRUST_PLACEHOLDERS.values())
    assert all(value in text for value in anchors.values())


def test_discover_packet_rejects_descriptor_not_matching_kernel_anchor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    descriptor = tmp_path / runner.DESCRIPTOR_NAME
    descriptor.write_text(
        json.dumps(
            {
                "schema": runner.DESCRIPTOR_SCHEMA,
                "dataset_id": runner.EXPECTED_DATASET_ID,
                "archive": {"sha256": "archive"},
                "packet_manifest": {"sha256": "manifest"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "EXPECTED_DESCRIPTOR_SHA256", "forged")
    monkeypatch.setattr(runner, "EXPECTED_ARCHIVE_SHA256", "archive")
    monkeypatch.setattr(runner, "EXPECTED_PACKET_MANIFEST_SHA256", "manifest")
    with pytest.raises(RuntimeError, match="descriptor trust anchor"):
        runner.discover_packet(tmp_path)


def test_safe_archive_members_rejects_traversal(tmp_path: Path) -> None:
    import zipfile

    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape", "x")
    with zipfile.ZipFile(archive, "r") as handle:
        with pytest.raises(ValueError, match="unsafe archive member"):
            runner.safe_archive_members(handle)


def test_packet_builder_supports_direct_cli_help() -> None:
    script = Path(__file__).parents[1] / "scripts" / "research" / "build_clay_input_access_kaggle_packet.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--preregistration" in completed.stdout
