from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.research import run_clay_hybrid_input_access_kaggle as runner


def test_storage_admission_measures_exact_existing_scratch_and_durable_parents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch_mount = tmp_path / "scratch-mount"
    durable_mount = tmp_path / "durable-mount"
    scratch_mount.mkdir()
    durable_mount.mkdir()
    scratch = scratch_mount / "live" / "campaign"
    durable = durable_mount / "output" / "campaign"
    measured: list[Path] = []

    def fake_usage(path: Path) -> SimpleNamespace:
        measured.append(Path(path))
        if Path(path) == scratch_mount.resolve():
            return SimpleNamespace(
                free=runner.MINIMUM_SCRATCH_LAUNCH_BYTES,
                total=100 * runner.GIB,
            )
        return SimpleNamespace(
            free=runner.DURABLE_MINIMUM_FREE_BYTES,
            total=10 * runner.GIB,
        )

    monkeypatch.setattr(runner.shutil, "disk_usage", fake_usage)
    receipt = runner.admit_storage(scratch, durable)
    assert measured == [scratch_mount.resolve(), durable_mount.resolve()]
    assert receipt["scratch"]["free_bytes"] == 26 * runner.GIB
    assert receipt["durable"]["free_bytes"] == runner.GIB


def test_storage_admission_rejects_25gib_without_peak_write_reserve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(free=25 * runner.GIB, total=100 * runner.GIB),
    )
    with pytest.raises(RuntimeError, match="scratch admission closed"):
        runner.admit_storage(tmp_path / "scratch", tmp_path / "durable")


def test_storage_admission_rejects_low_durable_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = tmp_path / "scratch"
    durable = tmp_path / "durable"
    scratch.mkdir()
    durable.mkdir()

    def fake_usage(path: Path) -> SimpleNamespace:
        free = 30 * runner.GIB if Path(path) == scratch.resolve() else runner.GIB - 1
        return SimpleNamespace(free=free, total=100 * runner.GIB)

    monkeypatch.setattr(runner.shutil, "disk_usage", fake_usage)
    with pytest.raises(RuntimeError, match="durable output admission closed"):
        runner.admit_storage(scratch, durable)


def test_durable_checkpoint_copy_is_hash_verified_and_pointer_committed_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = tmp_path / "scratch-campaign"
    durable = tmp_path / "durable-campaign"
    checkpoints = scratch / "arms" / "arm-seed-1" / "checkpoints"
    checkpoints.mkdir(parents=True)
    (checkpoints / "slot-a.pt").write_bytes(b"checkpoint-a")
    (checkpoints / "latest.json").write_text(
        json.dumps({"slot": "slot-a.pt", "sha256": "example"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runner,
        "require_runtime_floor",
        lambda path: {"free_bytes": 30 * runner.GIB},
    )
    monkeypatch.setattr(
        runner,
        "require_durable_copy_capacity",
        lambda path: {"free_bytes": 2 * runner.GIB},
    )
    copied: list[str] = []
    original = runner.atomic_copy

    def recording_copy(source: Path, destination: Path) -> None:
        if destination.is_relative_to(durable):
            copied.append(source.name)
        original(source, destination)

    monkeypatch.setattr(runner, "atomic_copy", recording_copy)
    receipt = runner.sync_campaign_to_durable(scratch, durable)
    assert copied.index("slot-a.pt") < copied.index("latest.json")
    assert receipt["files"] == 2
    runner.verify_inventory_manifest(
        durable,
        "DURABLE_CAMPAIGN_MANIFEST.json",
        f"{runner.RECEIPT_SCHEMA}.durable-campaign",
    )
    assert (durable / "arms" / "arm-seed-1" / "checkpoints" / "slot-a.pt").read_bytes() == b"checkpoint-a"


def test_snapshot_sync_retries_concurrent_mutation_then_commits_stable_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = tmp_path / "scratch"
    durable = tmp_path / "durable"
    scratch.mkdir()
    source_file = scratch / "state.json"
    source_file.write_bytes(b"v1")
    monkeypatch.setattr(
        runner,
        "require_runtime_floor",
        lambda path: {"free_bytes": 30 * runner.GIB},
    )
    monkeypatch.setattr(
        runner,
        "require_durable_copy_capacity",
        lambda path: {"free_bytes": 2 * runner.GIB},
    )
    original = runner.atomic_copy
    source_copies = 0

    def mutate_once(source: Path, destination: Path) -> None:
        nonlocal source_copies
        original(source, destination)
        if source == source_file:
            source_copies += 1
            if source_copies == 1:
                source_file.write_bytes(b"v2")

    monkeypatch.setattr(runner, "atomic_copy", mutate_once)
    receipt = runner.sync_campaign_to_durable(
        scratch,
        durable,
        max_snapshot_attempts=3,
    )
    assert source_copies == 2
    assert (durable / "state.json").read_bytes() == b"v2"
    assert receipt["files"] == 1
    assert not list(tmp_path.glob("*.pending"))


def test_snapshot_sync_fails_after_bounded_concurrent_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = tmp_path / "scratch"
    durable = tmp_path / "durable"
    scratch.mkdir()
    source_file = scratch / "state.json"
    source_file.write_bytes(b"v0")
    monkeypatch.setattr(
        runner,
        "require_runtime_floor",
        lambda path: {"free_bytes": 30 * runner.GIB},
    )
    monkeypatch.setattr(
        runner,
        "require_durable_copy_capacity",
        lambda path: {"free_bytes": 2 * runner.GIB},
    )
    original = runner.atomic_copy
    mutations = 0

    def always_mutate(source: Path, destination: Path) -> None:
        nonlocal mutations
        original(source, destination)
        if source == source_file:
            mutations += 1
            source_file.write_text(f"v{mutations}", encoding="utf-8")

    monkeypatch.setattr(runner, "atomic_copy", always_mutate)
    with pytest.raises(RuntimeError, match="bounded snapshot retries"):
        runner.sync_campaign_to_durable(
            scratch,
            durable,
            max_snapshot_attempts=2,
        )
    assert mutations == 2
    assert not (durable / "state.json").exists()
    assert not list(tmp_path.glob("*.pending"))


def test_inventory_uses_platform_neutral_posix_relative_order(tmp_path: Path) -> None:
    for relative in (
        "campaign/z.json",
        "campaign/A.json",
        "TRAINING.log",
        "CLOUD_ENVIRONMENT.json",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")

    paths = [item["path"] for item in runner.inventory(tmp_path)]
    assert paths == sorted(paths)


def test_durable_restore_rejects_tampered_checkpoint(tmp_path: Path) -> None:
    durable = tmp_path / "durable-campaign"
    durable.mkdir()
    checkpoint = durable / "slot-a.pt"
    checkpoint.write_bytes(b"sealed")
    runner.write_inventory_manifest(
        durable,
        "DURABLE_CAMPAIGN_MANIFEST.json",
        f"{runner.RECEIPT_SCHEMA}.durable-campaign",
    )
    checkpoint.write_bytes(b"forged")
    with pytest.raises(RuntimeError, match="byte count differs|hash differs"):
        runner.restore_durable_campaign(durable, tmp_path / "scratch")


def test_recovery_manifest_excludes_terminal_receipt_without_losing_tamper_checks(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    (campaign / "RESULT.json").write_text("{}", encoding="utf-8")
    path = runner.write_recovery_manifest(tmp_path)
    digest = runner.sha256_file(path)
    (tmp_path / "CLOUD_RUN_RECEIPT.json").write_text("{}", encoding="utf-8")
    runner.verify_recovery_root(tmp_path, digest)
    (campaign / "RESULT.json").write_text('{"forged": true}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="byte count differs|hash differs"):
        runner.verify_recovery_root(tmp_path, digest)


def _stage_flat_recovery_blobs(source: Path, dataset: Path) -> str:
    manifest_path = runner.write_recovery_manifest(source)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset.mkdir()
    runner.atomic_copy(manifest_path, dataset / manifest_path.name)
    for item in manifest["files"]:
        blob = dataset / f"recovery-{item['sha256']}.blob"
        if not blob.exists():
            runner.atomic_copy(source / item["path"], blob)
    return runner.sha256_file(manifest_path)


def test_import_prior_output_materializes_flat_content_addressed_blobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "prior"
    campaign = source / "campaign"
    campaign.mkdir(parents=True)
    (campaign / "state.json").write_text('{"step": 2000}', encoding="utf-8")
    dataset = tmp_path / "dataset"
    recovery_sha256 = _stage_flat_recovery_blobs(source, dataset)
    monkeypatch.setattr(runner, "EXPECTED_PRIOR_RECOVERY_SHA256", recovery_sha256)

    durable = tmp_path / "durable"
    assert runner.import_prior_output(dataset, durable) is True
    assert (durable / "campaign" / "state.json").read_text(encoding="utf-8") == ('{"step": 2000}')
    runner.verify_inventory_manifest(
        durable / "campaign",
        "DURABLE_CAMPAIGN_MANIFEST.json",
        f"{runner.RECEIPT_SCHEMA}.durable-campaign",
    )
    assert not list(tmp_path.glob("*.pending"))


def test_import_prior_output_rejects_tampered_content_addressed_blob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "prior"
    campaign = source / "campaign"
    campaign.mkdir(parents=True)
    (campaign / "state.json").write_text('{"step": 2000}', encoding="utf-8")
    dataset = tmp_path / "dataset"
    recovery_sha256 = _stage_flat_recovery_blobs(source, dataset)
    monkeypatch.setattr(runner, "EXPECTED_PRIOR_RECOVERY_SHA256", recovery_sha256)
    next(dataset.glob("recovery-*.blob")).write_bytes(b"forged")

    with pytest.raises(RuntimeError, match="byte count differs|hash differs"):
        runner.import_prior_output(dataset, tmp_path / "durable")
    assert not list(tmp_path.glob("*.pending"))


def test_parse_args_separates_scratch_and_durable_defaults() -> None:
    args = runner.parse_args([])
    assert args.scratch_root == Path("/tmp/clay-hybrid-input-access-efficacy-20261119-v1")
    assert args.durable_root == Path("/kaggle/working/clay-hybrid-input-access-efficacy-20261119-v1")
    assert os.fspath(args.scratch_root) != os.fspath(args.durable_root)
