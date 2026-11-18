from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace
import zipfile

import pytest
import torch

from python.scbe import clay_prime_scissor_input as prime_input
from scripts.research import build_clay_prime_scissor_kaggle_calibration as builder
from scripts.research import run_clay_prime_scissor_kaggle_calibration as runner
from scripts.research.build_clay_frozen_multiview_kaggle_packet import (
    descriptor,
    deterministic_zip,
    write_json,
)


def _write(path: Path, data: bytes = b"fixture\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def test_calibration_command_is_fixed_and_has_no_material_surface(
    tmp_path: Path,
) -> None:
    command = runner.calibration_command(tmp_path / "packet", tmp_path / "output", "cuda")

    assert "--calibration-only" in command
    assert command[command.index("--batch-size") + 1] == "128"
    assert command[command.index("--grow-steps") + 1] == "18000"
    assert command[command.index("--checkpoint-every") + 1] == "500"
    assert command[command.index("--learning-rate") + 1] == "0.002"
    assert command[command.index("--threads") + 1] == "2"
    assert command[command.index("--minimum-free-gib") + 1] == "25.0"
    assert command[command.index("--device") + 1] == "cuda"
    assert "--frozen-artifact-pack" in command
    assert "--arm" not in command
    assert "--seed" not in command
    assert "--max-horses" not in command
    assert "--aggregate-only" not in command
    with pytest.raises(ValueError, match="auto or cuda"):
        runner.calibration_command(tmp_path, tmp_path, "cpu")


def test_deterministic_archive_is_byte_identical(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _write(source / "b.bin", b"b")
    _write(source / "a.bin", b"a")
    first = tmp_path / "first.packet"
    second = tmp_path / "second.packet"

    deterministic_zip(source, first)
    deterministic_zip(source, second)

    assert first.read_bytes() == second.read_bytes()


def test_committed_frozen_authority_matches_preflight_and_every_member() -> None:
    root = Path(__file__).parents[2]
    artifact = root / builder.FROZEN_ARTIFACT_AUTHORITY
    authority = runner.load_json(root / "docs" / "research" / "CLAY_PRIME_SCISSOR_FROZEN_AUTHORITY_20261118.json")
    preflight = runner.load_json(root / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json")
    assert builder.sha256_file(artifact) == builder.EXPECTED_FROZEN_ARTIFACT_SHA256
    assert artifact.stat().st_size == builder.EXPECTED_FROZEN_ARTIFACT_BYTES
    assert authority["frozen_artifact"]["sha256"] == builder.sha256_file(artifact)
    assert authority["dataset_manifest_sha256"] == preflight["dataset_manifest_sha256"]
    assert authority["preflight_receipt_sha256"] == builder.EXPECTED_PREFLIGHT_SHA256

    with zipfile.ZipFile(artifact) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        assert set(archive.namelist()) == set(authority["frozen_artifact"]["member_sha256"])
        for member, expected in authority["frozen_artifact"]["member_sha256"].items():
            assert sha256(archive.read(member)).hexdigest() == expected

    assert metadata["dataset_manifest_sha256"] == preflight["dataset_manifest_sha256"]
    assert metadata["preflight_receipt_sha256"] == builder.EXPECTED_PREFLIGHT_SHA256
    assert metadata["feature_receipt_sha256"] == preflight["feature_tables"]["feature_receipt_sha256"]
    assert metadata["conditioning_receipt_sha256"] == preflight["empirical_conditioning_receipt_sha256"]
    assert metadata["bindings"]["train"]["seal_sha256"] == preflight["train_binding"]["seal_sha256"]
    assert (
        metadata["bindings"]["train"]["metadata"]["mapped_values_sha256"]
        == preflight["train_binding"]["mapped_values_sha256"]
    )
    assert metadata["bindings"]["holdout"]["seal_sha256"] == preflight["holdout_binding"]["seal_sha256"]
    assert (
        metadata["bindings"]["holdout"]["metadata"]["mapped_values_sha256"]
        == preflight["holdout_binding"]["mapped_values_sha256"]
    )
    for name, field in (
        ("prime_scissor", "prime_scissor_sha256"),
        ("canonical_onehot_matched", "canonical_onehot_matched_sha256"),
        ("deterministic_random_matched", "deterministic_random_matched_sha256"),
        ("no_intervention", "no_intervention_sha256"),
    ):
        assert metadata["tables"][name]["tensor_sha256"] == preflight["feature_tables"][field]


def test_safe_members_reject_traversal_duplicates_and_symlinks(tmp_path: Path) -> None:
    traversal = tmp_path / "traversal.zip"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("../escape", b"bad")
    with zipfile.ZipFile(traversal) as archive:
        with pytest.raises(ValueError, match="unsafe"):
            runner._safe_members(archive)

    duplicate = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(duplicate, "w") as archive:
        archive.writestr("same", b"one")
        archive.writestr("same", b"two")
    with zipfile.ZipFile(duplicate) as archive:
        with pytest.raises(RuntimeError, match="duplicate"):
            runner._safe_members(archive)

    symlink = tmp_path / "symlink.zip"
    with zipfile.ZipFile(symlink, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")
    with zipfile.ZipFile(symlink) as archive:
        with pytest.raises(ValueError, match="symlink"):
            runner._safe_members(archive)


def _sealed_packet(tmp_path: Path) -> tuple[Path, Path, dict]:
    packet = tmp_path / "packet"
    payload = _write(packet / "payload" / "fixture.bin", b"sealed")
    artifact = _write(
        packet / "payload" / "frozen_artifacts" / "prime_scissor_inputs.pack",
        b"frozen",
    )
    item = descriptor(payload, relative_to=packet)
    item["role"] = "fixture"
    artifact_item = descriptor(artifact, relative_to=packet)
    artifact_item["role"] = "exact_frozen_feature_and_binding_artifacts"
    artifact_hash = sha256(artifact.read_bytes()).hexdigest()
    body = {
        "schema": runner.PACKET_SCHEMA,
        "authority": {"material_training": "NONE"},
        "facts": {"frozen_artifact_pack_sha256": artifact_hash},
        "fixed_run_contract": {
            "calibration_only": True,
            "device": "cuda",
            "batch_size": 128,
            "grow_steps_per_horse": 18_000,
            "checkpoint_every": 500,
            "learning_rate": 0.002,
            "threads": 2,
            "minimum_free_gib": 25.0,
            "internet": False,
            "gpu": True,
            "frozen_artifact_pack_sha256": artifact_hash,
        },
        "files": [item, artifact_item],
        "file_count": 2,
        "payload_bytes": payload.stat().st_size + artifact.stat().st_size,
    }
    packet_id = runner.stable_hash(body)
    manifest = {
        **body,
        "packet_id": packet_id,
        "manifest_body_sha256": packet_id,
        "self_hash_rule": "excluded seal fields",
    }
    write_json(packet / runner.MANIFEST_NAME, manifest)
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    archive = dataset / "fixture.packet"
    deterministic_zip(packet, archive)
    descriptor_path = dataset / runner.DESCRIPTOR_NAME
    write_json(
        descriptor_path,
        {
            "schema": runner.DESCRIPTOR_SCHEMA,
            "dataset_id": "fixture/calibration",
            "packet_id": packet_id,
            "archive": descriptor(archive),
            "packet_manifest": descriptor(packet / runner.MANIFEST_NAME),
        },
    )
    return descriptor_path, archive, manifest


def test_sealed_packet_extracts_and_rejects_unmanifested_bytes(tmp_path: Path) -> None:
    descriptor_path, _, manifest = _sealed_packet(tmp_path)
    loaded_descriptor = runner.load_json(descriptor_path)
    _, loaded = runner.extract_and_verify_packet(descriptor_path, loaded_descriptor, tmp_path / "runtime")
    assert loaded["packet_id"] == manifest["packet_id"]

    packet = tmp_path / "bad-packet"
    _write(packet / "payload" / "fixture.bin", b"sealed")
    _write(
        packet / "payload" / "frozen_artifacts" / "prime_scissor_inputs.pack",
        b"frozen",
    )
    _write(packet / "payload" / "extra.bin", b"unmanifested")
    write_json(packet / runner.MANIFEST_NAME, manifest)
    bad_archive = tmp_path / "bad.packet"
    deterministic_zip(packet, bad_archive)
    bad_descriptor = dict(loaded_descriptor)
    bad_descriptor["archive"] = descriptor(bad_archive)
    bad_path = tmp_path / "BAD_DESCRIPTOR.json"
    write_json(bad_path, bad_descriptor)
    with pytest.raises(RuntimeError, match="unmanifested"):
        runner.extract_and_verify_packet(bad_path, bad_descriptor, tmp_path / "bad-runtime")


def test_independent_kernel_authority_rejects_replaced_descriptor(
    tmp_path: Path,
) -> None:
    descriptor_path, _, manifest = _sealed_packet(tmp_path)
    packet_descriptor = runner.load_json(descriptor_path)
    authority_path = tmp_path / "KERNEL_PACKET_AUTHORITY.json"
    write_json(
        authority_path,
        {
            "schema": runner.KERNEL_AUTHORITY_SCHEMA,
            "dataset_id": packet_descriptor["dataset_id"],
            "packet_id": manifest["packet_id"],
            "packet_descriptor": descriptor(descriptor_path),
            "archive": packet_descriptor["archive"],
            "packet_manifest": packet_descriptor["packet_manifest"],
        },
    )
    authority = runner.verify_kernel_authority(authority_path, descriptor_path, packet_descriptor)
    assert authority["packet_id"] == manifest["packet_id"]

    packet_descriptor["packet_id"] = "0" * 64
    write_json(descriptor_path, packet_descriptor)
    with pytest.raises(RuntimeError, match="descriptor"):
        runner.verify_kernel_authority(authority_path, descriptor_path, packet_descriptor)


def _baseline_fixture(root: Path) -> tuple[Path, dict]:
    baseline = root / "baseline"
    source_root = root / "source"
    source_dir = source_root / "experiments" / "clay_action_compiler_20261109"
    source_names = {
        "policy": "trit_compiled_action_policy.py",
        "topology": "topology_sector_action_ab.py",
        "sandbox": "developmental_game_sandbox.py",
        "regional": "regional_breathing_field.py",
    }
    source_hashes = {}
    for key, name in source_names.items():
        path = _write(source_dir / name, key.encode())
        source_hashes[key] = sha256(path.read_bytes()).hexdigest()
    parents = []
    for seed in builder.EXPECTED_SEEDS:
        parent_dir = baseline / "parents" / f"seed-{seed}"
        parent = _write(parent_dir / "PARENT.pt", f"parent-{seed}".encode())
        parent_hash = sha256(parent.read_bytes()).hexdigest()
        result = {"seed": seed, "parent_sha256": parent_hash}
        write_json(parent_dir / "RESULT.json", result)
        parents.append(result)
    manifest = {
        "schema": builder.EXPECTED_BASELINE_SCHEMA,
        "config": {
            "seeds": list(builder.EXPECTED_SEEDS),
            "grow_steps": 18_000,
            "batch_size": 128,
            "dataset_manifest_sha256": builder.EXPECTED_DATASET_MANIFEST_SHA256,
            "source_hashes": source_hashes,
        },
    }
    write_json(baseline / "RUN_MANIFEST.json", manifest)
    write_json(baseline / "RESULT.json", {"parents": parents})
    return source_root, manifest


def test_collect_specs_is_compact_and_parent_hash_pinned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_root, _ = _baseline_fixture(tmp_path)
    worktree = tmp_path / "worktree"
    math_root = tmp_path / "math"
    kernel = _write(tmp_path / "kernel.py")
    runtime = ("python/scbe/runtime.py",)
    docs = (
        "docs/research/CLAY_PRIME_SCISSOR_INPUT_PREREGISTRATION_20261118.md",
        "docs/research/CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json",
    )
    loom = tuple(
        f"experiments/clay_action_compiler_20261109/{name}"
        for name in (
            "trit_compiled_action_policy.py",
            "topology_sector_action_ab.py",
            "developmental_game_sandbox.py",
            "regional_breathing_field.py",
        )
    )
    math = ("__init__.py", "prime_lane_scissors.py")
    for relative in (*runtime, *docs):
        _write(worktree / relative)
    frozen_authority = _write(
        worktree / builder.FROZEN_ARTIFACT_AUTHORITY,
        b"sealed-frozen-authority",
    )
    for filename in math:
        _write(math_root / "clay-math" / "clay_math" / filename)
    monkeypatch.setattr(builder, "RUNTIME_MODULES", runtime)
    monkeypatch.setattr(builder, "AUTHORITY_DOCS", docs)
    monkeypatch.setattr(builder, "LOOM_FILES", loom)
    monkeypatch.setattr(builder, "MATH_MODULES", math)
    baseline = tmp_path / "baseline"
    monkeypatch.setattr(
        builder,
        "EXPECTED_BASELINE_MANIFEST_SHA256",
        builder.sha256_file(baseline / "RUN_MANIFEST.json"),
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_BASELINE_RESULT_SHA256",
        builder.sha256_file(baseline / "RESULT.json"),
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_PARENT_SHA256",
        {
            seed: builder.sha256_file(baseline / "parents" / f"seed-{seed}" / "PARENT.pt")
            for seed in builder.EXPECTED_SEEDS
        },
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_PARENT_RESULT_SHA256",
        {
            seed: builder.sha256_file(baseline / "parents" / f"seed-{seed}" / "RESULT.json")
            for seed in builder.EXPECTED_SEEDS
        },
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_PREREGISTRATION_SHA256",
        builder.sha256_file(worktree / docs[0]),
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_PREFLIGHT_SHA256",
        builder.sha256_file(worktree / docs[1]),
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_FROZEN_ARTIFACT_SHA256",
        builder.sha256_file(frozen_authority),
    )
    monkeypatch.setattr(
        builder,
        "EXPECTED_FROZEN_ARTIFACT_BYTES",
        frozen_authority.stat().st_size,
    )
    monkeypatch.setattr(
        builder,
        "require_clean_commit",
        lambda root: (builder.EXPECTED_MATH_COMMIT if root == math_root.resolve() else "1" * 40),
    )

    specs, facts = builder.collect_specs(
        worktree=worktree,
        baseline_run=tmp_path / "baseline",
        source_root=source_root,
        math_root=math_root,
        kernel_entry=kernel,
    )

    targets = {spec.target for spec in specs}
    assert len(targets) == len(specs)
    assert "payload/baseline/RUN_MANIFEST.json" in targets
    assert "payload/baseline/RESULT.json" in targets
    assert sum(target.endswith("/PARENT.pt") for target in targets) == 3
    assert sum(target.endswith("/RESULT.json") for target in targets) == 4
    assert "payload/frozen_artifacts/prime_scissor_inputs.pack" in targets
    assert not any("checkpoints" in target or "horses" in target for target in targets)
    assert facts["dataset_manifest_sha256"] == builder.EXPECTED_DATASET_MANIFEST_SHA256
    assert facts["frozen_artifact_authority_mode"] == ("COMMITTED_RELEASE_COPY_AND_VERIFY_NO_REGENERATION")


def test_packet_builder_verifies_committed_pack_without_regenerating(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = _write(tmp_path / "prime_scissor_inputs.pack", b"sealed")
    monkeypatch.setattr(
        builder,
        "EXPECTED_FROZEN_ARTIFACT_SHA256",
        builder.sha256_file(artifact),
    )

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        assert "--frozen-artifact-pack" in command
        assert command[command.index("--frozen-artifact-pack") + 1] == str(artifact)
        assert "--verify-frozen-artifact-pack-only" in command
        assert "--export-frozen-artifact-pack" not in command
        return subprocess.CompletedProcess(
            command,
            0,
            '{"status":"FROZEN_ARTIFACT_VERIFIED_NO_CALIBRATION_NO_HORSES"}\n',
            "",
        )

    monkeypatch.setattr(builder.subprocess, "run", fake_run)
    verified = builder._verify_frozen_artifacts(
        worktree=tmp_path,
        baseline_run=tmp_path,
        source_root=tmp_path,
        math_root=tmp_path,
        artifact=artifact,
    )
    assert verified == artifact
    assert not (artifact.parent / "verification-output-must-stay-absent").exists()


def test_calibration_wrapper_emits_receipts_and_rejects_model_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packet = tmp_path / "runtime-packet"
    packet.mkdir()
    manifest = {"packet_id": "a" * 64}
    descriptor_path = _write(tmp_path / runner.DESCRIPTOR_NAME, b"{}\n")
    monkeypatch.setattr(
        runner,
        "discover_packet",
        lambda input_root, dataset_id: (descriptor_path, {}),
    )
    monkeypatch.setattr(
        runner,
        "extract_and_verify_packet",
        lambda descriptor_path, packet_descriptor, runtime_root: (
            packet / runner.MANIFEST_NAME,
            manifest,
        ),
    )
    monkeypatch.setattr(
        runner,
        "verify_kernel_authority",
        lambda authority_path, descriptor_path, packet_descriptor: {},
    )
    monkeypatch.setattr(
        runner,
        "_environment_receipt",
        lambda output_root, packet_id: {
            "packet_id": packet_id,
            "disk_free_gib": 100.0,
            "torch": {"cuda_available": True},
        },
    )

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        output = Path(command[command.index("--output-dir") + 1])
        write_json(
            output / "TIMING_CALIBRATION.json",
            {
                "representative_batch_size": 128,
                "preregistered_steps_per_horse_unchanged": 18_000,
                "actual_device": "cuda",
                "measured_steps": 500,
                "projected_15_horse_seconds_with_20_percent_margin": 3600.0,
                "maximum_admitted_seconds": 86_400,
            },
        )
        write_json(
            output / "STATUS.json",
            {"status": "CALIBRATION_COMPLETE_NO_HORSES_STARTED"},
        )
        return subprocess.CompletedProcess(command, 0, "calibrated\n", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    args = runner.parse_args(
        [
            "--input-root",
            str(tmp_path),
            "--dataset-id",
            "fixture",
            "--output-root",
            str(tmp_path / "output"),
            "--runtime-root",
            str(tmp_path / "unused-runtime"),
        ]
    )
    receipt = runner.run_calibration(args)
    assert receipt["status"] == "PASS_CALIBRATION_ONLY_NO_HORSES_STARTED"
    assert not runner._forbidden_artifacts(tmp_path / "output")
    assert (tmp_path / "output" / "ENVIRONMENT_RECEIPT.json").is_file()
    assert (tmp_path / "output" / "LAUNCH_RECEIPT.json").is_file()
    assert (tmp_path / "output" / "RECOVERY_RECEIPT.json").is_file()

    second_output = tmp_path / "output-with-model"

    def fake_run_with_model(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = fake_run(command, **kwargs)
        _write(second_output / "run" / "horses" / "bad" / "MODEL.pt")
        return result

    monkeypatch.setattr(runner.subprocess, "run", fake_run_with_model)
    args.output_root = second_output
    with pytest.raises(RuntimeError, match="forbidden artifacts"):
        runner.run_calibration(args)
    failure = runner.load_json(second_output / "FAILURE_RECEIPT.json")
    assert failure["status"] == "FAIL_CLOSED_NO_MATERIAL_TRAINING"
    assert failure["forbidden_artifacts"]


def test_kernel_metadata_contract_is_private_gpu_offline() -> None:
    args = runner.parse_args([])
    assert args.device == "cuda"
    assert args.output_root == Path("/kaggle/working/clay-prime-scissor-calibration")
    assert args.runtime_root == Path("/kaggle/working/clay-prime-scissor-calibration-runtime")


def test_prelaunch_failure_still_emits_environment_launch_failure_and_recovery(
    tmp_path: Path,
) -> None:
    args = runner.parse_args(
        [
            "--input-root",
            str(tmp_path / "missing-input"),
            "--output-root",
            str(tmp_path / "failure-output"),
            "--runtime-root",
            str(tmp_path / "runtime"),
        ]
    )
    with pytest.raises(FileNotFoundError):
        runner.run_calibration(args)
    output = tmp_path / "failure-output"
    assert (output / "ENVIRONMENT_RECEIPT.json").is_file()
    assert (output / "LAUNCH_RECEIPT.json").is_file()
    assert (output / "FAILURE_RECEIPT.json").is_file()
    assert (output / "RECOVERY_RECEIPT.json").is_file()
    assert runner.load_json(output / "LAUNCH_RECEIPT.json")["status"].startswith("NOT_LAUNCHED")


def _tiny_binding(name: str) -> tuple[prime_input.SealedOccurrenceDerangement, list]:
    sample_ids = (f"{name}-0", f"{name}-1")
    mapped = torch.tensor([[1, 2], [3, 4]], dtype=torch.uint8)
    association = {"clears_randomized_association_gate": True}
    provisional = prime_input.SealedOccurrenceDerangement.__new__(prime_input.SealedOccurrenceDerangement)
    object.__setattr__(provisional, "sample_ids", sample_ids)
    object.__setattr__(provisional, "mapped_values", mapped)
    object.__setattr__(provisional, "occurrence_width", 2)
    object.__setattr__(provisional, "split_name", name)
    object.__setattr__(provisional, "seed", 7)
    object.__setattr__(provisional, "pool_sha256", "a" * 64)
    object.__setattr__(provisional, "permutation_sha256", "b" * 64)
    object.__setattr__(provisional, "mapped_values_sha256", prime_input.tensor_sha256(mapped))
    object.__setattr__(provisional, "association", association)
    object.__setattr__(provisional, "seal_sha256", "")
    seal = prime_input._sha256_json(provisional.metadata())
    binding = prime_input.SealedOccurrenceDerangement(
        sample_ids=sample_ids,
        mapped_values=mapped,
        occurrence_width=2,
        split_name=name,
        seed=7,
        pool_sha256="a" * 64,
        permutation_sha256="b" * 64,
        mapped_values_sha256=prime_input.tensor_sha256(mapped),
        association=association,
        seal_sha256=seal,
    )
    rows = [SimpleNamespace(sample=SimpleNamespace(sample_id=value)) for value in sample_ids]
    return binding, rows


def test_frozen_artifact_pack_round_trips_and_rejects_tamper(tmp_path: Path) -> None:
    names = (
        "prime_scissor",
        "canonical_onehot_matched",
        "deterministic_random_matched",
        "no_intervention",
    )
    tensors = {
        name: torch.arange(256 * 206, dtype=torch.float32).reshape(256, 206) + index for index, name in enumerate(names)
    }
    feature_receipt = {
        "table_sha256": {name: prime_input.tensor_sha256(value) for name, value in tensors.items()},
        "pivot_indices_sha256": "1" * 64,
        "pivot_descriptors_sha256": "2" * 64,
    }
    tables = prime_input.FeatureTables(tables=tensors, receipt=feature_receipt)
    train, train_rows = _tiny_binding("train")
    holdout, holdout_rows = _tiny_binding("holdout")
    conditioning = {"receipt_sha256": "3" * 64, "kind": "fixture"}
    pack = tmp_path / "frozen.pack"
    metadata = prime_input.export_frozen_artifact_pack(
        pack,
        tables=tables,
        train_binding=train,
        holdout_binding=holdout,
        conditioning_receipt=conditioning,
        dataset_manifest_sha256="4" * 64,
        preflight_receipt_sha256="5" * 64,
    )
    second_pack = tmp_path / "frozen-second.pack"
    prime_input.export_frozen_artifact_pack(
        second_pack,
        tables=tables,
        train_binding=train,
        holdout_binding=holdout,
        conditioning_receipt=conditioning,
        dataset_manifest_sha256="4" * 64,
        preflight_receipt_sha256="5" * 64,
    )
    assert pack.read_bytes() == second_pack.read_bytes()

    loaded = prime_input.load_frozen_artifact_pack(
        pack,
        train_rows=train_rows,
        holdout_rows=holdout_rows,
        dataset_manifest_sha256="4" * 64,
        preflight_receipt_sha256="5" * 64,
    )
    assert loaded.metadata["metadata_body_sha256"] == metadata["metadata_body_sha256"]
    assert loaded.train_binding.seal_sha256 == train.seal_sha256
    assert loaded.holdout_binding.seal_sha256 == holdout.seal_sha256
    assert all(torch.equal(loaded.tables.tables[name], tensors[name]) for name in names)

    with pytest.raises(RuntimeError, match="dataset identity"):
        prime_input.load_frozen_artifact_pack(
            pack,
            train_rows=train_rows,
            holdout_rows=holdout_rows,
            dataset_manifest_sha256="6" * 64,
            preflight_receipt_sha256="5" * 64,
        )
    with pytest.raises(RuntimeError, match="sample IDs"):
        prime_input.load_frozen_artifact_pack(
            pack,
            train_rows=list(reversed(train_rows)),
            holdout_rows=holdout_rows,
            dataset_manifest_sha256="4" * 64,
            preflight_receipt_sha256="5" * 64,
        )

    tampered = tmp_path / "tampered.pack"
    with zipfile.ZipFile(pack) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            payload = source.read(info)
            if info.filename == "tables/prime_scissor.bin":
                payload = bytes([payload[0] ^ 1]) + payload[1:]
            target.writestr(info, payload)
    with pytest.raises(RuntimeError, match="member hash"):
        prime_input.load_frozen_artifact_pack(
            tampered,
            train_rows=train_rows,
            holdout_rows=holdout_rows,
            dataset_manifest_sha256="4" * 64,
            preflight_receipt_sha256="5" * 64,
        )
