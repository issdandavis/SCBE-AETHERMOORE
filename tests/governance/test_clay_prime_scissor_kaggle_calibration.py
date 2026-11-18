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


def test_material_command_is_exact_full_campaign_without_selection_surface(
    tmp_path: Path,
) -> None:
    command = runner.material_command(tmp_path / "packet", tmp_path / "output", "cuda")

    assert "--calibration-only" not in command
    assert command[command.index("--batch-size") + 1] == "128"
    assert command[command.index("--grow-steps") + 1] == "18000"
    assert command[command.index("--checkpoint-every") + 1] == "500"
    assert command[command.index("--learning-rate") + 1] == "0.002"
    assert command[command.index("--threads") + 1] == "2"
    assert command[command.index("--minimum-free-gib") + 1] == "25.0"
    assert command[command.index("--device") + 1] == "cuda"
    assert "--arm" not in command
    assert "--seed" not in command
    assert "--max-horses" not in command
    assert "--aggregate-only" not in command


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


def test_dataset_discovery_identity_comes_from_suffixed_authority(
    tmp_path: Path,
) -> None:
    authority_path = tmp_path / "KERNEL_PACKET_AUTHORITY.json"
    dataset_id = "fixture/clay-prime-scissor-calibration-20261118-dd2623de"
    write_json(
        authority_path,
        {
            "schema": runner.KERNEL_AUTHORITY_SCHEMA,
            "dataset_id": dataset_id,
        },
    )

    resolved, authority = runner.resolve_dataset_authority(authority_path, None)
    assert resolved == dataset_id
    assert authority["dataset_id"] == dataset_id


def test_embedded_kernel_authority_is_default_only_and_canonical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_id = "fixture/clay-prime-scissor-calibration-20261118-dd2623de"
    authority = {
        "schema": runner.KERNEL_AUTHORITY_SCHEMA,
        "dataset_id": dataset_id,
    }
    generated_entry = tmp_path / "script.py"
    monkeypatch.setattr(runner, "__file__", str(generated_entry))
    monkeypatch.setattr(
        runner,
        "EMBEDDED_KERNEL_AUTHORITY_JSON",
        runner.canonical_json(authority),
    )

    resolved, loaded = runner.resolve_dataset_authority(
        generated_entry.with_name("KERNEL_PACKET_AUTHORITY.json"),
        None,
    )
    assert resolved == dataset_id
    assert loaded == authority

    with pytest.raises(FileNotFoundError):
        runner.resolve_dataset_authority(tmp_path / "explicit-missing.json", None)

    monkeypatch.setattr(
        runner,
        "EMBEDDED_KERNEL_AUTHORITY_JSON",
        json.dumps(authority, indent=2),
    )
    with pytest.raises(RuntimeError, match="not canonical JSON"):
        runner.resolve_dataset_authority(
            generated_entry.with_name("KERNEL_PACKET_AUTHORITY.json"),
            None,
        )


def test_generated_code_file_alone_discovers_and_verifies_attached_dataset(
    tmp_path: Path,
) -> None:
    descriptor_path, _, manifest = _sealed_packet(tmp_path)
    packet_descriptor = runner.load_json(descriptor_path)
    authority = {
        "schema": runner.KERNEL_AUTHORITY_SCHEMA,
        "dataset_id": packet_descriptor["dataset_id"],
        "packet_id": manifest["packet_id"],
        "packet_descriptor": descriptor(descriptor_path),
        "archive": packet_descriptor["archive"],
        "packet_manifest": packet_descriptor["packet_manifest"],
    }
    generated_entry = tmp_path / "generated" / "script.py"
    builder.render_kaggle_kernel_entry(
        Path(runner.__file__),
        generated_entry,
        authority,
    )

    rendered = generated_entry.read_text(encoding="utf-8")
    assert builder.EMBEDDED_KERNEL_AUTHORITY_SENTINEL not in rendered
    assert runner.canonical_json(authority) in rendered
    forbidden_host_root = tmp_path / "forbidden-host-worktree"
    forbidden_host_root.mkdir()
    receipt = builder.verify_kaggle_code_file_only(
        generated_entry,
        descriptor_path.parent,
        expected_dataset_id=packet_descriptor["dataset_id"],
        expected_packet_id=manifest["packet_id"],
        forbidden_host_root=forbidden_host_root,
        verify_clay_adapter=False,
    )
    assert receipt["status"] == "PASS_CODE_FILE_ONLY_AUTHORITY_AND_DATASET_DISCOVERY"
    assert receipt["code_file_count"] == 1
    assert receipt["sibling_authority_present"] is False
    assert receipt["dataset_source_attached"] is True
    assert receipt["packet_archive_verified"] is True
    assert receipt["clay_source_adapter_instantiated"] is False
    assert receipt["host_source_path_absent"] is False
    assert receipt["material_training"] == "NONE"
    assert receipt["calibration_started"] is False
    assert receipt["quota_spent"] is False


def test_calibration_environment_pins_extracted_scbe_without_ambient_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet_root = tmp_path / "extracted"
    repo = packet_root / "payload" / "scbe_repo"
    scbe_python = repo / "python"
    _write(scbe_python / "scbe" / "instrument.py")
    clay_math_root = packet_root / "payload" / "clay_math_root"
    loom_root = packet_root / "payload" / "loom_root"
    clay_math_root.mkdir(parents=True)
    loom_root.mkdir(parents=True)
    monkeypatch.setenv("PYTHONPATH", r"C:\host\wrong-source")
    monkeypatch.setenv("SCBE_ROOT", r"C:\host\wrong-scbe")
    monkeypatch.setenv("SCBE_PYTHON", r"C:\host\wrong-scbe\python")

    environment = runner.calibration_environment(packet_root)

    expected_roots = [repo, scbe_python, clay_math_root, loom_root]
    assert environment["PYTHONPATH"].split(runner.os.pathsep) == [str(path.resolve()) for path in expected_roots]
    assert environment["SCBE_ROOT"] == str(repo.resolve())
    assert environment["SCBE_PYTHON"] == str(scbe_python.resolve())
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert "wrong-source" not in environment["PYTHONPATH"]
    assert "wrong-scbe" not in environment["SCBE_ROOT"]


def test_explicit_dataset_identity_must_match_authority(tmp_path: Path) -> None:
    authority_path = tmp_path / "KERNEL_PACKET_AUTHORITY.json"
    dataset_id = "fixture/clay-prime-scissor-calibration-20261118-dd2623de"
    write_json(
        authority_path,
        {
            "schema": runner.KERNEL_AUTHORITY_SCHEMA,
            "dataset_id": dataset_id,
        },
    )

    with pytest.raises(RuntimeError, match="explicit dataset id differs"):
        runner.resolve_dataset_authority(authority_path, "fixture/unsuffixed")


def _sealed_receipt(path: Path, body: dict) -> Path:
    write_json(path, {**body, "receipt_sha256": runner.stable_hash(body)})
    return path


def _calibration_admission_fixture(root: Path) -> Path:
    packet_id = builder.SOURCE_CALIBRATION_PACKET_ID
    _sealed_receipt(
        root / "ENVIRONMENT_RECEIPT.json",
        {
            "schema": f"{runner.RECEIPT_SCHEMA}.environment",
            "packet_id": packet_id,
            "torch": {
                "cuda_available": True,
                "device_count": 2,
                "device_names": list(builder.EXPECTED_CALIBRATION_DEVICE_NAMES),
            },
        },
    )
    _sealed_receipt(
        root / "LAUNCH_RECEIPT.json",
        {
            "schema": f"{runner.RECEIPT_SCHEMA}.launch",
            "packet_id": packet_id,
            "mode": builder.CALIBRATION_MODE,
            "material_training": "NONE",
        },
    )
    timing_path = _sealed_receipt(
        root / "TIMING_CALIBRATION.json",
        {
            "schema": "clay.prime-scissor-input-campaign.v1.device-timing-calibration",
            "actual_device": "cuda",
            "measured_steps": 500,
            "representative_batch_size": 128,
            "preregistered_steps_per_horse_unchanged": 18_000,
            "seconds_per_step": builder.EXPECTED_CALIBRATION_SECONDS_PER_STEP,
            "projected_15_horse_seconds_with_20_percent_margin": (builder.EXPECTED_CAMPAIGN_SECONDS_WITH_MARGIN),
            "maximum_admitted_seconds": 86_400,
            "config_hash": builder.EXPECTED_CALIBRATION_CONFIG_HASH,
        },
    )
    _sealed_receipt(
        root / "RECOVERY_RECEIPT.json",
        {
            "schema": f"{runner.RECEIPT_SCHEMA}.recovery",
            "packet_id": packet_id,
            "status": "PASS_CALIBRATION_ONLY_NO_HORSES_STARTED",
            "returncode": 0,
            "forbidden_artifacts": [],
            "material_training": "NONE",
            "timing_calibration_sha256": builder.sha256_file(timing_path),
        },
    )
    return root


def test_material_admission_seals_exact_dual_t4_receipts_and_rejects_drift(
    tmp_path: Path,
) -> None:
    root = _calibration_admission_fixture(tmp_path / "calibration")

    specs, facts = builder.collect_calibration_admission(root)

    assert len(specs) == 4
    assert {spec.target for spec in specs} == {
        f"authorities/calibration/{name}"
        for name in (
            "ENVIRONMENT_RECEIPT.json",
            "LAUNCH_RECEIPT.json",
            "RECOVERY_RECEIPT.json",
            "TIMING_CALIBRATION.json",
        )
    }
    assert facts["source_calibration_packet_id"] == builder.SOURCE_CALIBRATION_PACKET_ID
    assert facts["seconds_per_step"] == builder.EXPECTED_CALIBRATION_SECONDS_PER_STEP
    assert facts["projected_15_horse_seconds_with_20_percent_margin"] == builder.EXPECTED_CAMPAIGN_SECONDS_WITH_MARGIN

    timing_path = root / "TIMING_CALIBRATION.json"
    timing = runner.load_json(timing_path)
    timing.pop("receipt_sha256")
    timing["seconds_per_step"] += 0.001
    _sealed_receipt(timing_path, timing)
    recovery_path = root / "RECOVERY_RECEIPT.json"
    recovery = runner.load_json(recovery_path)
    recovery.pop("receipt_sha256")
    recovery["timing_calibration_sha256"] = builder.sha256_file(timing_path)
    _sealed_receipt(recovery_path, recovery)
    with pytest.raises(RuntimeError, match="seconds-per-step differs"):
        builder.collect_calibration_admission(root)


def test_material_runtime_replays_every_calibration_receipt_hash(tmp_path: Path) -> None:
    packet_root = tmp_path / "packet"
    authority_root = _calibration_admission_fixture(packet_root / "authorities" / "calibration")
    receipt_hashes = {path.name: runner.sha256_file(path) for path in sorted(authority_root.glob("*.json"))}
    manifest = {
        "facts": {
            "calibration_admission": {
                "source_calibration_packet_id": runner.SOURCE_CALIBRATION_PACKET_ID,
                "receipt_sha256": receipt_hashes,
                "timing_calibration_sha256": receipt_hashes["TIMING_CALIBRATION.json"],
                "recovery_receipt_sha256": receipt_hashes["RECOVERY_RECEIPT.json"],
                "projected_15_horse_seconds_with_20_percent_margin": (runner.EXPECTED_CAMPAIGN_SECONDS_WITH_MARGIN),
            }
        }
    }

    admission = runner._validate_material_admission(packet_root, manifest)

    assert admission["source_calibration_packet_id"] == runner.SOURCE_CALIBRATION_PACKET_ID
    assert admission["device_names"] == list(runner.EXPECTED_CALIBRATION_DEVICE_NAMES)
    assert admission["seconds_per_step"] == runner.EXPECTED_CALIBRATION_SECONDS_PER_STEP

    launch_path = authority_root / "LAUNCH_RECEIPT.json"
    launch = runner.load_json(launch_path)
    launch["receipt_sha256"] = "0" * 64
    write_json(launch_path, launch)
    manifest["facts"]["calibration_admission"]["receipt_sha256"]["LAUNCH_RECEIPT.json"] = runner.sha256_file(
        launch_path
    )
    with pytest.raises(RuntimeError, match="receipt self-hash differs"):
        runner._validate_material_admission(packet_root, manifest)


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
    full_scbe_init = _write(
        worktree / builder.FULL_SCBE_INIT_SOURCE,
        b"full application initializer authority\n",
    )
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
    assert builder.GENERATED_SCBE_INIT_TARGET not in targets
    assert f"authorities/full_source/{builder.FULL_SCBE_INIT_SOURCE}" in targets
    assert not any("checkpoints" in target or "horses" in target for target in targets)
    assert facts["dataset_manifest_sha256"] == builder.EXPECTED_DATASET_MANIFEST_SHA256
    assert facts["frozen_artifact_authority_mode"] == ("COMMITTED_RELEASE_COPY_AND_VERIFY_NO_REGENERATION")
    assert facts["runtime_source_authority_sha256"][builder.FULL_SCBE_INIT_SOURCE] == (
        builder.sha256_file(full_scbe_init)
    )
    assert facts["generated_runtime_stub"]["path"] == builder.GENERATED_SCBE_INIT_TARGET
    assert facts["generated_runtime_stub"]["imports"] == []


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


def test_extracted_archive_replay_is_isolated_from_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worktree = tmp_path / "worktree-that-must-not-leak"
    worktree.mkdir()
    packet = tmp_path / "packet"
    script = packet / "payload" / "scbe_repo" / "python" / "scbe" / ("clay_prime_scissor_input_campaign.py")
    script.parent.mkdir(parents=True)
    script.write_text(
        """from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

forbidden = os.environ["CLAY_FORBIDDEN_WORKTREE"].casefold()
assert forbidden not in str(Path.cwd()).casefold()
assert forbidden not in os.environ.get("PYTHONPATH", "").casefold()
assert all(forbidden not in str(item).casefold() for item in sys.path)
probe = subprocess.run(
    ["git", "-C", str(Path.cwd()), "rev-parse", "--show-toplevel"],
    check=False,
    capture_output=True,
    text=True,
)
assert probe.returncode != 0, probe.stdout
print(json.dumps({"status": "FROZEN_ARTIFACT_VERIFIED_NO_CALIBRATION_NO_HORSES"}))
""",
        encoding="utf-8",
        newline="\n",
    )
    archive = tmp_path / "isolated.packet"
    deterministic_zip(packet, archive)
    outer_repository = tmp_path / "profile-repository"
    outer_repository.mkdir()
    subprocess.run(
        ["git", "init", "--quiet", str(outer_repository)],
        check=True,
        capture_output=True,
        text=True,
    )
    isolation_parent = outer_repository / "Temp"
    isolation_parent.mkdir()
    attack_probe = subprocess.run(
        ["git", "-C", str(isolation_parent), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert attack_probe.returncode == 0
    assert Path(attack_probe.stdout.strip()).resolve() == outer_repository.resolve()
    monkeypatch.setenv("PYTHONPATH", str(worktree))
    monkeypatch.chdir(worktree)

    receipt = builder.verify_extracted_archive_isolated(
        archive,
        worktree=worktree,
        isolation_parent=isolation_parent,
    )

    assert receipt["status"] == ("PASS_FROZEN_ARTIFACT_VERIFIED_NO_CALIBRATION_NO_HORSES")
    assert receipt["python_isolated_mode"] is True
    assert receipt["pythonpath_from_extracted_archive_only"] is True
    assert receipt["worktree_absent_from_subprocess_sys_path"] is True
    assert receipt["git_parent_discovery_blocked"] is True
    assert receipt["git_parent_probe_returncode"] != 0
    assert receipt["verification_output_created"] is False


def test_calibration_wrapper_emits_receipts_and_rejects_model_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    packet = tmp_path / "runtime-packet"
    packet.mkdir()
    manifest = {"packet_id": "a" * 64}
    descriptor_path = _write(tmp_path / runner.DESCRIPTOR_NAME, b"{}\n")
    authority_path = tmp_path / "KERNEL_PACKET_AUTHORITY.json"
    write_json(
        authority_path,
        {
            "schema": runner.KERNEL_AUTHORITY_SCHEMA,
            "dataset_id": "fixture/calibration",
        },
    )
    discovered_dataset_ids: list[str] = []

    def fake_discover(input_root: Path, dataset_id: str) -> tuple[Path, dict]:
        discovered_dataset_ids.append(dataset_id)
        return descriptor_path, {}

    monkeypatch.setattr(
        runner,
        "discover_packet",
        fake_discover,
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
        lambda authority_path, descriptor_path, packet_descriptor, **kwargs: {},
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
    sealed_child_environment = {
        "PYTHONPATH": str(tmp_path / "runtime-only"),
        "SCBE_ROOT": str(tmp_path / "runtime-scbe"),
        "SCBE_PYTHON": str(tmp_path / "runtime-scbe" / "python"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    }
    monkeypatch.setattr(
        runner,
        "calibration_environment",
        lambda packet_root: sealed_child_environment,
    )
    observed_child_launches: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_child_launches.append(kwargs)
        assert kwargs["env"] is sealed_child_environment
        assert kwargs["cwd"] == tmp_path / "unused-runtime"
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
            "--kernel-authority",
            str(authority_path),
            "--output-root",
            str(tmp_path / "output"),
            "--runtime-root",
            str(tmp_path / "unused-runtime"),
        ]
    )
    receipt = runner.run_calibration(args)
    assert receipt["status"] == "PASS_CALIBRATION_ONLY_NO_HORSES_STARTED"
    assert len(observed_child_launches) == 1
    assert discovered_dataset_ids == ["fixture/calibration"]
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


def test_material_artifact_manifest_requires_every_exact_horse(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    write_json(run_root / "RESULT.json", {"status": "COMPLETE"})
    write_json(run_root / "STATUS.json", {"status": "COMPLETE"})
    for arm in runner.FIXED_ARMS:
        for seed in runner.FIXED_SEEDS:
            horse = run_root / "horses" / f"{arm}-seed-{seed}"
            write_json(
                horse / "RESULT.json",
                {"status": "COMPLETE", "arm": arm, "seed": seed},
            )
            _write(horse / "MODEL.pt", f"{arm}:{seed}".encode())

    manifest = runner._material_artifact_manifest(run_root, "f" * 64)

    assert manifest["horse_count"] == 15
    assert {(row["arm"], row["seed"]) for row in manifest["horses"]} == {
        (arm, seed) for arm in runner.FIXED_ARMS for seed in runner.FIXED_SEEDS
    }
    assert all(row["model"]["sha256"] for row in manifest["horses"])
    assert all(row["result"]["sha256"] for row in manifest["horses"])
    runner.verify_receipt_self_hash(manifest, label="material artifact manifest")

    missing_model = run_root / "horses" / f"{runner.FIXED_ARMS[0]}-seed-{runner.FIXED_SEEDS[0]}" / "MODEL.pt"
    missing_model.unlink()
    with pytest.raises(RuntimeError, match="model is missing"):
        runner._material_artifact_manifest(run_root, "f" * 64)


def test_material_prelaunch_failure_is_receipted_and_auto_device_is_rejected(
    tmp_path: Path,
) -> None:
    authority_path = tmp_path / "KERNEL_PACKET_AUTHORITY.json"
    write_json(
        authority_path,
        {
            "schema": runner.KERNEL_AUTHORITY_SCHEMA,
            "dataset_id": "fixture/material",
            "entry_mode": runner.MATERIAL_MODE,
        },
    )
    output = tmp_path / "output"
    args = runner.parse_args(
        [
            "--input-root",
            str(tmp_path / "missing-input"),
            "--kernel-authority",
            str(authority_path),
            "--output-root",
            str(output),
            "--runtime-root",
            str(tmp_path / "runtime"),
            "--device",
            "auto",
        ]
    )

    with pytest.raises(RuntimeError, match="calibrated cuda device"):
        runner.run_material(args)

    assert (output / "ENVIRONMENT_RECEIPT.json").is_file()
    assert (output / "LAUNCH_RECEIPT.json").is_file()
    assert (output / "FAILURE_RECEIPT.json").is_file()
    assert (output / "RECOVERY_RECEIPT.json").is_file()
    launch = runner.load_json(output / "LAUNCH_RECEIPT.json")
    recovery = runner.load_json(output / "RECOVERY_RECEIPT.json")
    assert launch["status"] == "NOT_LAUNCHED_FIXED_CAMPAIGN_GATE_FAILED"
    assert launch["material_training"] == "NONE"
    assert recovery["status"] == "FAIL_CLOSED_MATERIAL_ARTIFACTS_PRESERVED"
    assert recovery["promotion"] == "NONE"


def test_packet_dispatch_uses_authority_and_material_output_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = runner.parse_args([])
    monkeypatch.setattr(
        runner,
        "load_kernel_authority",
        lambda path: {"entry_mode": runner.MATERIAL_MODE},
    )
    observed: list[tuple[Path, Path]] = []

    def fake_material(namespace: SimpleNamespace) -> dict:
        observed.append((namespace.output_root, namespace.runtime_root))
        return {"status": "DISPATCHED"}

    monkeypatch.setattr(runner, "run_material", fake_material)

    result = runner.run_packet(args)

    assert result == {"status": "DISPATCHED"}
    assert observed == [
        (
            Path("/kaggle/working/clay-prime-scissor-material"),
            Path("/kaggle/working/clay-prime-scissor-material-runtime"),
        )
    ]


def test_material_wrapper_persists_complete_campaign_and_aggregate_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calibration = _calibration_admission_fixture(tmp_path / "calibration-authority")
    receipt_hashes = {path.name: runner.sha256_file(path) for path in sorted(calibration.glob("*.json"))}
    packet_id = "b" * 64
    manifest = {
        "packet_id": packet_id,
        "fixed_run_contract": {"entry_mode": runner.MATERIAL_MODE},
        "facts": {
            "calibration_admission": {
                "source_calibration_packet_id": runner.SOURCE_CALIBRATION_PACKET_ID,
                "receipt_sha256": receipt_hashes,
                "timing_calibration_sha256": receipt_hashes["TIMING_CALIBRATION.json"],
                "recovery_receipt_sha256": receipt_hashes["RECOVERY_RECEIPT.json"],
                "projected_15_horse_seconds_with_20_percent_margin": (runner.EXPECTED_CAMPAIGN_SECONDS_WITH_MARGIN),
            }
        },
    }
    authority_path = tmp_path / "KERNEL_PACKET_AUTHORITY.json"
    write_json(
        authority_path,
        {
            "schema": runner.KERNEL_AUTHORITY_SCHEMA,
            "dataset_id": "fixture/material",
            "entry_mode": runner.MATERIAL_MODE,
        },
    )
    descriptor_path = _write(tmp_path / runner.DESCRIPTOR_NAME, b"{}\n")
    monkeypatch.setattr(
        runner,
        "discover_packet",
        lambda input_root, dataset_id: (descriptor_path, {}),
    )
    monkeypatch.setattr(
        runner,
        "verify_kernel_authority",
        lambda authority_path, descriptor_path, packet_descriptor, **kwargs: {},
    )

    def fake_extract(
        descriptor_path: Path,
        packet_descriptor: dict,
        runtime_root: Path,
    ) -> tuple[Path, dict]:
        runtime_root.mkdir()
        runner.shutil.copytree(
            calibration,
            runtime_root / "authorities" / "calibration",
        )
        return runtime_root / runner.MANIFEST_NAME, manifest

    monkeypatch.setattr(runner, "extract_and_verify_packet", fake_extract)
    monkeypatch.setattr(
        runner,
        "_environment_receipt",
        lambda output_root, requested_packet_id: {
            "packet_id": requested_packet_id,
            "disk_free_gib": 100.0,
            "torch": {
                "cuda_available": True,
                "device_count": 2,
                "device_names": list(runner.EXPECTED_CALIBRATION_DEVICE_NAMES),
            },
        },
    )
    child_environment = {
        "PYTHONPATH": "sealed",
        "SCBE_ROOT": "sealed-scbe",
        "SCBE_PYTHON": "sealed-scbe/python",
    }
    monkeypatch.setattr(runner, "calibration_environment", lambda packet_root: child_environment)
    observed_commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        observed_commands.append(command)
        assert kwargs["env"] is child_environment
        output = Path(command[command.index("--output-dir") + 1])
        for arm in runner.FIXED_ARMS:
            for seed in runner.FIXED_SEEDS:
                horse = output / "horses" / f"{arm}-seed-{seed}"
                write_json(
                    horse / "RESULT.json",
                    {"status": "COMPLETE", "arm": arm, "seed": seed},
                )
                _write(horse / "MODEL.pt", f"{arm}:{seed}".encode())
        write_json(output / "RESULT.json", {"status": "COMPLETE", "horse_count": 15})
        write_json(
            output / "STATUS.json",
            {
                "status": "COMPLETE",
                "result_sha256": runner.sha256_file(output / "RESULT.json"),
            },
        )
        return subprocess.CompletedProcess(command, 0, "complete\n", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    input_root = tmp_path / "input"
    input_root.mkdir()
    output_root = tmp_path / "output"
    args = runner.parse_args(
        [
            "--input-root",
            str(input_root),
            "--kernel-authority",
            str(authority_path),
            "--output-root",
            str(output_root),
            "--runtime-root",
            str(tmp_path / "runtime"),
        ]
    )

    recovery = runner.run_material(args)

    assert recovery["status"] == "PASS_MATERIAL_CAMPAIGN_COMPLETE_UNPROMOTED"
    assert recovery["horse_count"] == 15
    assert recovery["promotion"] == "NONE"
    assert len(observed_commands) == 1
    assert "--calibration-only" not in observed_commands[0]
    assert "--arm" not in observed_commands[0]
    assert "--seed" not in observed_commands[0]
    artifact_manifest = runner.load_json(output_root / "MATERIAL_ARTIFACT_MANIFEST.json")
    assert artifact_manifest["horse_count"] == 15
    assert len(artifact_manifest["horses"]) == 15
    assert recovery["artifact_manifest_sha256"] == runner.sha256_file(output_root / "MATERIAL_ARTIFACT_MANIFEST.json")


def test_kernel_metadata_contract_is_private_gpu_offline() -> None:
    args = runner.parse_args([])
    assert args.dataset_id is None
    assert args.device == "cuda"
    assert args.output_root == Path("/kaggle/working/clay-prime-scissor-calibration")
    assert args.runtime_root == Path("/kaggle/working/clay-prime-scissor-calibration-runtime")

    kernel_id = "issacizrealdavis/clay-prime-scissor-calibration-20261118-dd2623de"
    metadata = builder.kaggle_kernel_metadata(
        kernel_id=kernel_id,
        kernel_entry_name="run.py",
        dataset_id=kernel_id,
    )
    assert metadata["id"] == kernel_id
    assert metadata["title"] == kernel_id.rsplit("/", 1)[1]
    assert metadata["is_private"] is True
    assert metadata["enable_gpu"] is True
    assert metadata["enable_internet"] is False

    with pytest.raises(ValueError, match="clean lowercase provider slug"):
        builder.kernel_title_for_id("issacizrealdavis/Clay Prime Scissor")


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
