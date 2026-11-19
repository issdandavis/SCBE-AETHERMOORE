from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.research.build_clay_hybrid_input_access_kaggle_packet import (
    DURABLE_MINIMUM_FREE_BYTES,
    MINIMUM_SCRATCH_LAUNCH_BYTES,
    TRAINING_FLOOR_BYTES,
    TRUST_PLACEHOLDERS,
    _stage_prior_recovery_dataset,
    render_kernel_entry,
)
from scripts.research import run_clay_hybrid_input_access_kaggle as runner


def test_kernel_template_materializes_every_external_trust_anchor(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "kernel.py"
    anchors = {key: f"{index:064x}" for index, key in enumerate(TRUST_PLACEHOLDERS, 1)}
    render_kernel_entry(Path(runner.__file__).resolve(), destination, anchors)
    text = destination.read_text(encoding="utf-8")
    assert not any(placeholder in text for placeholder in TRUST_PLACEHOLDERS.values())
    assert all(value in text for value in anchors.values())


def test_builder_and_runner_share_exact_storage_contract() -> None:
    assert TRAINING_FLOOR_BYTES == runner.TRAINING_FLOOR_BYTES == 25 * 1024**3
    assert MINIMUM_SCRATCH_LAUNCH_BYTES == runner.MINIMUM_SCRATCH_LAUNCH_BYTES == 26 * 1024**3
    assert DURABLE_MINIMUM_FREE_BYTES == runner.DURABLE_MINIMUM_FREE_BYTES == 1024**3


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
    script = Path(__file__).parents[1] / "scripts" / "research" / "build_clay_hybrid_input_access_kaggle_packet.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--preregistration" in completed.stdout


def test_prior_recovery_dataset_is_flat_content_addressed_and_exact(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    campaign = source / "campaign"
    campaign.mkdir(parents=True)
    (campaign / "same-a.bin").write_bytes(b"same")
    (campaign / "same-b.bin").write_bytes(b"same")
    (campaign / "other.bin").write_bytes(b"other")
    manifest = runner.write_recovery_manifest(source)

    destination = tmp_path / "dataset"
    receipt = _stage_prior_recovery_dataset(
        recovery_manifest=manifest,
        destination=destination,
        dataset_id="issacizrealdavis/test-private-recovery",
    )
    assert receipt["source_file_count"] == 3
    assert receipt["unique_blob_count"] == 2
    assert len(list(destination.glob("recovery-*.blob"))) == 2
    assert (destination / "RECOVERY_MANIFEST.json").read_bytes() == manifest.read_bytes()
    metadata = json.loads((destination / "dataset-metadata.json").read_text())
    assert metadata["isPrivate"] is True


def test_prior_recovery_dataset_rejects_source_changed_after_manifest(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    campaign = source / "campaign"
    campaign.mkdir(parents=True)
    state = campaign / "state.json"
    state.write_text('{"step": 2000}', encoding="utf-8")
    manifest = runner.write_recovery_manifest(source)
    state.write_text('{"step": 2001}', encoding="utf-8")

    with pytest.raises(RuntimeError, match="byte count differs|hash differs"):
        _stage_prior_recovery_dataset(
            recovery_manifest=manifest,
            destination=tmp_path / "dataset",
            dataset_id="issacizrealdavis/test-private-recovery",
        )
