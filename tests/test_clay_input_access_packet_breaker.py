"""Adversarial packet, recovery, and resume tests for Clay input access."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.research.build_clay_stable_ce_kaggle_packet import (
    descriptor,
    deterministic_zip,
)
from scripts.research import run_clay_input_access_kaggle as runner

RECEIPT_SCHEMA = runner.RECEIPT_SCHEMA
sha256_file = runner.sha256_file
validate_existing_output = runner.validate_existing_output
verify_recovery_root = runner.verify_recovery_root
write_json = runner.write_json
write_recovery_manifest = runner.write_recovery_manifest


def _synthetic_packet(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    remote_config: dict | None = None,
    authority: dict | None = None,
    preregistration: bytes = b"preregistered",
    campaign: bytes = b"campaign",
    expected_preregistration_sha256: str | None = None,
    expected_campaign_sha256: str | None = None,
) -> tuple[Path, Path, dict]:
    source = root / "source"
    preregistration_path = source / "scbe_repo" / "docs" / "pre.json"
    campaign_path = source / "scbe_repo" / "python" / "scbe" / "campaign.py"
    preregistration_path.parent.mkdir(parents=True)
    campaign_path.parent.mkdir(parents=True)
    preregistration_path.write_bytes(preregistration)
    campaign_path.write_bytes(campaign)
    files = [
        descriptor(preregistration_path, relative_to=source),
        descriptor(campaign_path, relative_to=source),
    ]
    preregistration_sha256 = sha256_file(preregistration_path)
    campaign_sha256 = sha256_file(campaign_path)
    manifest = {
        "schema": runner.PACKET_SCHEMA,
        "dataset_id": runner.EXPECTED_DATASET_ID,
        "remote_config": remote_config or dict(runner.EXPECTED_REMOTE_CONFIG),
        "trust_anchors": {
            "preregistration_sha256": preregistration_sha256,
            "campaign_sha256": campaign_sha256,
        },
        "authority": authority
        or {
            "visibility": "PRIVATE",
            "internet": "DISABLED",
        },
        "files": files,
        "paths": {
            "scbe_root": "scbe_repo",
            "preregistration": "docs/pre.json",
            "campaign": "python/scbe/campaign.py",
        },
    }
    manifest_path = source / runner.PACKET_MANIFEST_NAME
    write_json(manifest_path, manifest)
    dataset = root / "input" / "dataset"
    dataset.mkdir(parents=True)
    archive = dataset / "packet.zip"
    deterministic_zip(source, archive)
    descriptor_value = {
        "schema": runner.DESCRIPTOR_SCHEMA,
        "dataset_id": runner.EXPECTED_DATASET_ID,
        "archive": descriptor(archive),
        "packet_manifest": descriptor(manifest_path),
    }
    descriptor_path = dataset / runner.DESCRIPTOR_NAME
    write_json(descriptor_path, descriptor_value)
    monkeypatch.setattr(runner, "EXPECTED_DESCRIPTOR_SHA256", sha256_file(descriptor_path))
    monkeypatch.setattr(runner, "EXPECTED_ARCHIVE_SHA256", sha256_file(archive))
    monkeypatch.setattr(
        runner,
        "EXPECTED_PACKET_MANIFEST_SHA256",
        sha256_file(manifest_path),
    )
    monkeypatch.setattr(
        runner,
        "EXPECTED_PREREGISTRATION_SHA256",
        expected_preregistration_sha256 or preregistration_sha256,
    )
    monkeypatch.setattr(
        runner,
        "EXPECTED_CAMPAIGN_SHA256",
        expected_campaign_sha256 or campaign_sha256,
    )
    return root / "input", descriptor_path, descriptor_value


def _completed_output(root: Path) -> tuple[list[str], Path, dict[str, str]]:
    campaign = root / "campaign"
    checkpoint = campaign / "arms" / "input_access-seed-20261134" / "checkpoint.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"checkpoint-v1")
    result = campaign / "RESULT.json"
    result.write_text("{}\n", encoding="utf-8")
    command = ["python", "-m", "python.scbe.clay_input_access_campaign"]
    cwd = root / "runtime" / "scbe_repo"
    authority = {"visibility": "PRIVATE", "internet": "DISABLED"}
    write_json(
        root / "CLOUD_LAUNCH.json",
        {
            "schema": f"{RECEIPT_SCHEMA}.launch",
            "command": command,
            "cwd": str(cwd),
            "authority": authority,
        },
    )
    recovery = write_recovery_manifest(root)
    write_json(
        root / "CLOUD_RUN_RECEIPT.json",
        {
            "schema": RECEIPT_SCHEMA,
            "campaign_result_sha256": sha256_file(result),
            "recovery_manifest_sha256": sha256_file(recovery),
        },
    )
    return command, cwd, authority


def test_recovery_manifest_rejects_unlisted_campaign_file(tmp_path) -> None:
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    (campaign / "checkpoint.pt").write_bytes(b"listed")
    manifest = write_recovery_manifest(tmp_path)
    expected = sha256_file(manifest)
    (campaign / "forged.pt").write_bytes(b"not listed")
    with pytest.raises(RuntimeError):
        verify_recovery_root(tmp_path, expected)


def test_completed_resume_replays_recovery_inventory(tmp_path) -> None:
    command, cwd, authority = _completed_output(tmp_path)
    checkpoint = tmp_path / "campaign" / "arms" / "input_access-seed-20261134" / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint-forged-after-receipt")
    with pytest.raises(RuntimeError):
        validate_existing_output(
            tmp_path,
            command=command,
            cwd=cwd,
            authority=authority,
        )


def test_same_run_incomplete_output_is_resume_eligible(tmp_path) -> None:
    command = ["python", "-m", "python.scbe.clay_input_access_campaign"]
    cwd = tmp_path / "runtime" / "scbe_repo"
    authority = {"visibility": "PRIVATE", "internet": "DISABLED"}
    write_json(
        tmp_path / "CLOUD_LAUNCH.json",
        {
            "schema": f"{RECEIPT_SCHEMA}.launch",
            "command": command,
            "cwd": str(cwd),
            "authority": authority,
        },
    )
    checkpoint = tmp_path / "campaign" / "checkpoints" / "slot-0.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"partial")
    assert (
        validate_existing_output(
            tmp_path,
            command=command,
            cwd=cwd,
            authority=authority,
        )
        is None
    )


def test_pinned_prior_import_is_idempotent_for_same_run_resume(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_root = tmp_path / "input"
    prior = input_root / "prior-output"
    prior_checkpoint = prior / "campaign" / "checkpoints" / "slot-0.pt"
    prior_checkpoint.parent.mkdir(parents=True)
    prior_checkpoint.write_bytes(b"pinned-prior")
    recovery = write_recovery_manifest(prior)
    monkeypatch.setattr(
        runner,
        "EXPECTED_PRIOR_RECOVERY_SHA256",
        sha256_file(recovery),
    )
    output = tmp_path / "working"
    output.mkdir()
    assert runner.import_prior_campaign(input_root, output)
    assert (output / "campaign" / "checkpoints" / "slot-0.pt").read_bytes() == b"pinned-prior"
    assert not runner.import_prior_campaign(input_root, output)


def test_pinned_prior_import_rejects_forged_checkpoint(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_root = tmp_path / "input"
    prior = input_root / "prior-output"
    checkpoint = prior / "campaign" / "checkpoints" / "slot-0.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"trusted")
    recovery = write_recovery_manifest(prior)
    monkeypatch.setattr(
        runner,
        "EXPECTED_PRIOR_RECOVERY_SHA256",
        sha256_file(recovery),
    )
    checkpoint.write_bytes(b"forged")
    output = tmp_path / "working"
    output.mkdir()
    with pytest.raises(RuntimeError):
        runner.import_prior_campaign(input_root, output)


def test_packet_exact_trust_anchors_accept_only_pinned_bytes(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_root, _, _ = _synthetic_packet(tmp_path, monkeypatch)
    descriptor_path, descriptor_value = runner.discover_packet(input_root)
    manifest = runner.extract_packet(
        descriptor_path,
        descriptor_value,
        tmp_path / "runtime",
    )
    assert manifest["remote_config"] == runner.EXPECTED_REMOTE_CONFIG


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("remote_config", {**runner.EXPECTED_REMOTE_CONFIG, "steps": 1999}),
        ("authority", {"visibility": "PUBLIC", "internet": "ENABLED"}),
    ),
)
def test_packet_rejects_altered_execution_contract(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: dict,
) -> None:
    kwargs = {field: value}
    input_root, descriptor_path, descriptor_value = _synthetic_packet(
        tmp_path,
        monkeypatch,
        **kwargs,
    )
    discovered, value = runner.discover_packet(input_root)
    assert discovered == descriptor_path
    with pytest.raises(ValueError):
        runner.extract_packet(discovered, value, tmp_path / "runtime")


def test_packet_rejects_stale_preregistration_anchor(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = sha256_file(Path(__file__))
    input_root, _, _ = _synthetic_packet(
        tmp_path,
        monkeypatch,
        preregistration=b"edited after preregistration",
        expected_preregistration_sha256=expected,
    )
    descriptor_path, descriptor_value = runner.discover_packet(input_root)
    with pytest.raises(ValueError):
        runner.extract_packet(
            descriptor_path,
            descriptor_value,
            tmp_path / "runtime",
        )


@pytest.mark.parametrize("target", ("descriptor", "archive", "manifest"))
def test_packet_rejects_mutated_outer_trust_anchor(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    input_root, descriptor_path, descriptor_value = _synthetic_packet(
        tmp_path,
        monkeypatch,
    )
    if target == "descriptor":
        descriptor_path.write_text(
            descriptor_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        with pytest.raises(RuntimeError):
            runner.discover_packet(input_root)
        return
    if target == "archive":
        archive = descriptor_path.parent / descriptor_value["archive"]["path"]
        with archive.open("ab") as handle:
            handle.write(b"forged")
        discovered, value = runner.discover_packet(input_root)
        with pytest.raises(RuntimeError):
            runner.extract_packet(discovered, value, tmp_path / "runtime")
        return

    descriptor_value["packet_manifest"]["sha256"] = "0" * 64
    write_json(descriptor_path, descriptor_value)
    monkeypatch.setattr(
        runner,
        "EXPECTED_DESCRIPTOR_SHA256",
        sha256_file(descriptor_path),
    )
    with pytest.raises(RuntimeError):
        runner.discover_packet(input_root)
