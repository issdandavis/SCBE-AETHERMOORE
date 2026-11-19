"""Verify and run the private offline Clay hybrid input-access packet.

Live training and checkpoints run on an explicitly measured scratch filesystem.
Checkpoint generations and terminal receipts are copied atomically to a
separately measured durable output root.  This wrapper has no publication or
promotion authority.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable
import zipfile

import torch

PACKET_SCHEMA = "clay.hybrid-input-access-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.hybrid-input-access-kaggle-dataset.v1"
RECEIPT_SCHEMA = "clay.hybrid-input-access-kaggle-run.v1"
EXPECTED_DATASET_ID = "issacizrealdavis/clay-hybrid-input-access-efficacy-input-20261119"
DESCRIPTOR_NAME = "PACKET_DESCRIPTOR.json"
PACKET_MANIFEST_NAME = "CLAY_HYBRID_INPUT_ACCESS_KAGGLE_PACKET.json"
EXPECTED_DESCRIPTOR_SHA256 = "__BUILD_PINNED_DESCRIPTOR_SHA256__"
EXPECTED_ARCHIVE_SHA256 = "__BUILD_PINNED_ARCHIVE_SHA256__"
EXPECTED_PACKET_MANIFEST_SHA256 = "__BUILD_PINNED_PACKET_MANIFEST_SHA256__"
EXPECTED_PREREGISTRATION_SHA256 = "__BUILD_PINNED_PREREGISTRATION_SHA256__"
EXPECTED_CAMPAIGN_SHA256 = "__BUILD_PINNED_CAMPAIGN_SHA256__"
EXPECTED_PRIOR_RECOVERY_SHA256 = "__BUILD_PINNED_PRIOR_RECOVERY_SHA256__"

GIB = 1024**3
TRAINING_FLOOR_BYTES = 25 * GIB
PEAK_WRITE_RESERVE_BYTES = 1 * GIB
MINIMUM_SCRATCH_LAUNCH_BYTES = TRAINING_FLOOR_BYTES + PEAK_WRITE_RESERVE_BYTES
DURABLE_MINIMUM_FREE_BYTES = 1 * GIB
EXPECTED_REMOTE_CONFIG = {
    "seeds": [20261134, 20261135, 20261136],
    "steps": 2000,
    "checkpoint_every": 250,
    "batch_size": 128,
    "threads": 2,
    "minimum_free_gib": 25.0,
    "training_floor_bytes": TRAINING_FLOOR_BYTES,
    "peak_write_reserve_bytes": PEAK_WRITE_RESERVE_BYTES,
    "minimum_scratch_launch_bytes": MINIMUM_SCRATCH_LAUNCH_BYTES,
    "durable_minimum_free_bytes": DURABLE_MINIMUM_FREE_BYTES,
    "device": "cpu",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected one JSON object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def closest_existing(path: Path) -> Path:
    anchor = path.resolve()
    while not anchor.exists():
        parent = anchor.parent
        if parent == anchor:
            raise RuntimeError(f"cannot locate filesystem for {path}")
        anchor = parent
    return anchor


def storage_observation(path: Path) -> dict[str, Any]:
    anchor = closest_existing(path)
    usage = shutil.disk_usage(anchor)
    return {
        "requested_path": str(path.resolve()),
        "measured_anchor": str(anchor),
        "device": int(os.stat(anchor).st_dev),
        "free_bytes": int(usage.free),
        "total_bytes": int(usage.total),
    }


def admit_storage(
    scratch_root: Path,
    durable_root: Path,
    *,
    scratch_required_bytes: int = MINIMUM_SCRATCH_LAUNCH_BYTES,
    durable_required_bytes: int = DURABLE_MINIMUM_FREE_BYTES,
) -> dict[str, Any]:
    if scratch_root.resolve() == durable_root.resolve():
        raise RuntimeError("scratch and durable roots must be distinct")
    scratch = storage_observation(scratch_root)
    durable = storage_observation(durable_root)
    if scratch["free_bytes"] < scratch_required_bytes:
        raise RuntimeError(
            "training scratch admission closed: " f"{scratch['free_bytes']} < {scratch_required_bytes} bytes"
        )
    if durable["free_bytes"] < durable_required_bytes:
        raise RuntimeError(
            "durable output admission closed: " f"{durable['free_bytes']} < {durable_required_bytes} bytes"
        )
    return {
        "schema": f"{RECEIPT_SCHEMA}.storage",
        "checked_at_utc": utc_now(),
        "scratch": scratch,
        "durable": durable,
        "scratch_required_bytes": scratch_required_bytes,
        "durable_required_bytes": durable_required_bytes,
    }


def require_runtime_floor(scratch_campaign: Path) -> dict[str, Any]:
    observation = storage_observation(scratch_campaign)
    if observation["free_bytes"] < TRAINING_FLOOR_BYTES:
        raise RuntimeError(
            "training scratch fell below preregistered floor: "
            f"{observation['free_bytes']} < {TRAINING_FLOOR_BYTES} bytes"
        )
    return observation


def require_durable_copy_capacity(durable_root: Path) -> dict[str, Any]:
    observation = storage_observation(durable_root)
    if observation["free_bytes"] < DURABLE_MINIMUM_FREE_BYTES:
        raise RuntimeError(
            "durable output fell below copy guard: " f"{observation['free_bytes']} < {DURABLE_MINIMUM_FREE_BYTES} bytes"
        )
    return observation


def verify_descriptor(path: Path, expected: dict[str, Any], *, label: str) -> None:
    if path.stat().st_size != int(expected["bytes"]):
        raise RuntimeError(f"{label} byte count differs: {path}")
    if sha256_file(path) != str(expected["sha256"]).casefold():
        raise RuntimeError(f"{label} hash differs: {path}")


def discover_packet(input_root: Path) -> tuple[Path, dict[str, Any]]:
    matches = []
    for path in sorted(input_root.rglob(DESCRIPTOR_NAME)):
        value = load_json(path)
        if value.get("schema") == DESCRIPTOR_SCHEMA and value.get("dataset_id") == EXPECTED_DATASET_ID:
            matches.append((path, value))
    if len(matches) != 1:
        raise RuntimeError(f"expected one hybrid packet, found {len(matches)}")
    path, value = matches[0]
    if sha256_file(path) != EXPECTED_DESCRIPTOR_SHA256:
        raise RuntimeError("packet descriptor trust anchor differs")
    if value.get("archive", {}).get("sha256") != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("packet archive descriptor trust anchor differs")
    if value.get("packet_manifest", {}).get("sha256") != EXPECTED_PACKET_MANIFEST_SHA256:
        raise RuntimeError("packet manifest descriptor trust anchor differs")
    return path, value


def safe_archive_members(archive: zipfile.ZipFile) -> tuple[zipfile.ZipInfo, ...]:
    members = tuple(archive.infolist())
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError(f"unsafe archive member: {member.filename}")
    return members


def extract_packet(
    descriptor_path: Path,
    descriptor_value: dict[str, Any],
    runtime_root: Path,
) -> dict[str, Any]:
    archive_descriptor = descriptor_value["archive"]
    archive_path = descriptor_path.parent / archive_descriptor["path"]
    verify_descriptor(archive_path, archive_descriptor, label="packet archive")
    if runtime_root.exists():
        if not runtime_root.is_dir():
            raise RuntimeError("runtime packet path is not a directory")
    else:
        runtime_root.mkdir(parents=True)
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.extractall(runtime_root, members=safe_archive_members(archive))
    manifest_path = runtime_root / PACKET_MANIFEST_NAME
    verify_descriptor(
        manifest_path,
        descriptor_value["packet_manifest"],
        label="packet manifest",
    )
    manifest = load_json(manifest_path)
    if manifest.get("schema") != PACKET_SCHEMA:
        raise ValueError("packet schema differs")
    if manifest.get("dataset_id") != EXPECTED_DATASET_ID:
        raise ValueError("packet dataset identity differs")
    if manifest.get("remote_config") != EXPECTED_REMOTE_CONFIG:
        raise ValueError("packet remote config differs from preregistration")
    expected_trust = {
        "preregistration_sha256": EXPECTED_PREREGISTRATION_SHA256,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
    }
    if manifest.get("trust_anchors") != expected_trust:
        raise ValueError("packet source trust anchors differ")
    authority = manifest.get("authority", {})
    expected_authority = {
        "visibility": "PRIVATE",
        "internet": "DISABLED",
        "execution": "NONE",
        "merge": "NONE",
        "promotion": "NONE",
        "tool_dispatch": "DISABLED",
    }
    if authority != expected_authority:
        raise ValueError("packet private/offline authority differs")
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe packet path: {relative}")
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root.resolve(strict=True)):
            raise ValueError(f"packet path escapes root: {relative}")
        verify_descriptor(path, item, label=f"packet file {relative}")
    expected_files = {
        PACKET_MANIFEST_NAME,
        *(str(item["path"]) for item in manifest["files"]),
    }
    actual_files = {path.relative_to(runtime_root).as_posix() for path in runtime_root.rglob("*") if path.is_file()}
    if actual_files != expected_files:
        raise RuntimeError("runtime packet inventory differs")
    paths = manifest["paths"]
    preregistration = runtime_root / paths["scbe_root"] / paths["preregistration"]
    campaign = runtime_root / paths["scbe_root"] / paths["campaign"]
    if sha256_file(preregistration) != EXPECTED_PREREGISTRATION_SHA256:
        raise RuntimeError("extracted preregistration trust anchor differs")
    if sha256_file(campaign) != EXPECTED_CAMPAIGN_SHA256:
        raise RuntimeError("extracted campaign trust anchor differs")
    return manifest


def inventory(root: Path, *, exclude: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
    rows = []
    if not root.exists():
        return rows
    files = [item for item in root.rglob("*") if item.is_file()]
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative_path = path.relative_to(root)
        relative = relative_path.as_posix()
        if any(part.endswith(".pending") for part in relative_path.parts):
            continue
        if relative in exclude or path.name.endswith(".pending"):
            continue
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def write_inventory_manifest(
    root: Path,
    manifest_name: str,
    schema: str,
    *,
    extra_exclude: frozenset[str] = frozenset(),
) -> Path:
    rows = inventory(root, exclude=frozenset({manifest_name}) | extra_exclude)
    path = root / manifest_name
    write_json(
        path,
        {
            "schema": schema,
            "created_at_utc": utc_now(),
            "files": rows,
            "file_count": len(rows),
            "total_bytes": sum(int(row["bytes"]) for row in rows),
        },
    )
    return path


def verify_inventory_manifest(
    root: Path,
    manifest_name: str,
    schema: str,
    *,
    expected_sha256: str | None = None,
    extra_exclude: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    manifest_path = root / manifest_name
    if expected_sha256 is not None and sha256_file(manifest_path) != expected_sha256:
        raise RuntimeError("recovery manifest trust anchor differs")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != schema:
        raise RuntimeError("recovery manifest schema differs")
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe recovery path: {relative}")
        path = (root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(root.resolve(strict=True)):
            raise ValueError(f"recovery path escapes root: {relative}")
        verify_descriptor(path, item, label=f"recovery file {relative}")
    actual = inventory(root, exclude=frozenset({manifest_name}) | extra_exclude)
    if actual != manifest["files"]:
        raise RuntimeError("recovery inventory differs")
    if int(manifest["file_count"]) != len(actual):
        raise RuntimeError("recovery file count differs")
    if int(manifest["total_bytes"]) != sum(int(row["bytes"]) for row in actual):
        raise RuntimeError("recovery total bytes differs")
    return manifest


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = destination.with_suffix(destination.suffix + ".pending")
    shutil.copy2(source, pending)
    if sha256_file(pending) != sha256_file(source):
        raise RuntimeError(f"durable copy hash differs: {source}")
    os.replace(pending, destination)


def sync_campaign_to_durable(
    scratch_campaign: Path,
    durable_campaign: Path,
    *,
    max_snapshot_attempts: int = 3,
) -> dict[str, Any]:
    require_runtime_floor(scratch_campaign)
    durable_observation = require_durable_copy_capacity(durable_campaign)
    durable_campaign.mkdir(parents=True, exist_ok=True)
    if max_snapshot_attempts < 1:
        raise ValueError("snapshot attempts must be positive")

    stable_inventory: list[dict[str, Any]] | None = None
    for _attempt in range(max_snapshot_attempts):
        try:
            before = inventory(scratch_campaign)
        except FileNotFoundError:
            continue
        pending = Path(
            tempfile.mkdtemp(
                prefix=".campaign-sync-",
                suffix=".pending",
                dir=durable_campaign.parent,
            )
        )
        try:
            live_copy_unstable = False
            for item in before:
                try:
                    atomic_copy(
                        scratch_campaign / item["path"],
                        pending / item["path"],
                    )
                except FileNotFoundError:
                    live_copy_unstable = True
                    break
                except RuntimeError as error:
                    if not str(error).startswith("durable copy hash differs:"):
                        raise
                    live_copy_unstable = True
                    break
            if live_copy_unstable:
                continue
            try:
                copied = inventory(pending)
                after = inventory(scratch_campaign)
            except FileNotFoundError:
                continue
            if before != after or copied != before:
                continue

            # Commit only from a stable pending snapshot. Checkpoint pointers
            # follow their slot bytes; terminal pointers follow model/results.
            def priority(item: dict[str, Any]) -> tuple[int, str]:
                relative = str(item["path"])
                name = PurePosixPath(relative).name
                if name == "latest.json":
                    return (1, relative)
                if relative in {"STATUS.json", "RESULT.json", "PROGRESS.json"}:
                    return (2, relative)
                return (0, relative)

            for item in sorted(copied, key=priority):
                atomic_copy(
                    pending / item["path"],
                    durable_campaign / item["path"],
                )
            durable_inventory = inventory(
                durable_campaign,
                exclude=frozenset({"DURABLE_CAMPAIGN_MANIFEST.json"}),
            )
            if durable_inventory != copied:
                raise RuntimeError("durable campaign commit differs from stable snapshot")
            stable_inventory = copied
            break
        finally:
            shutil.rmtree(pending, ignore_errors=True)
    if stable_inventory is None:
        raise RuntimeError("scratch campaign did not stabilize within bounded snapshot retries")
    manifest = write_inventory_manifest(
        durable_campaign,
        "DURABLE_CAMPAIGN_MANIFEST.json",
        f"{RECEIPT_SCHEMA}.durable-campaign",
    )
    verify_inventory_manifest(
        durable_campaign,
        manifest.name,
        f"{RECEIPT_SCHEMA}.durable-campaign",
    )
    return {
        "files": len(stable_inventory),
        "total_bytes": sum(int(row["bytes"]) for row in stable_inventory),
        "manifest_sha256": sha256_file(manifest),
        "durable_storage": durable_observation,
    }


def restore_durable_campaign(
    durable_campaign: Path,
    scratch_campaign: Path,
) -> bool:
    if not durable_campaign.exists():
        return False
    manifest_name = "DURABLE_CAMPAIGN_MANIFEST.json"
    manifest = verify_inventory_manifest(
        durable_campaign,
        manifest_name,
        f"{RECEIPT_SCHEMA}.durable-campaign",
    )
    expected = manifest["files"]
    if scratch_campaign.exists():
        actual = inventory(scratch_campaign)
        if actual == expected:
            return True
        if actual:
            raise RuntimeError("existing scratch campaign differs from durable recovery")
    scratch_campaign.mkdir(parents=True, exist_ok=True)
    for item in expected:
        source = durable_campaign / item["path"]
        destination = scratch_campaign / item["path"]
        atomic_copy(source, destination)
    if inventory(scratch_campaign) != expected:
        raise RuntimeError("scratch campaign restore differs")
    return True


def import_prior_output(input_root: Path, durable_root: Path) -> bool:
    if EXPECTED_PRIOR_RECOVERY_SHA256 == "NONE":
        return False
    matches = [
        path
        for path in input_root.rglob("RECOVERY_MANIFEST.json")
        if sha256_file(path) == EXPECTED_PRIOR_RECOVERY_SHA256
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one pinned prior recovery, found {len(matches)}")
    dataset_root = matches[0].parent.resolve(strict=True)
    temporary: Path | None = None
    try:
        prior_root = dataset_root
        if not (prior_root / "campaign").is_dir():
            # Kaggle datasets do not preserve nested directories unless they
            # are archived. Materialize the pinned recovery inventory from
            # content-addressed, top-level blobs before trusting any bytes.
            temporary = Path(
                tempfile.mkdtemp(
                    prefix=".prior-recovery-",
                    suffix=".pending",
                    dir=durable_root.parent,
                )
            )
            atomic_copy(
                matches[0],
                temporary / "RECOVERY_MANIFEST.json",
            )
            manifest_value = load_json(matches[0])
            if manifest_value.get("schema") != f"{RECEIPT_SCHEMA}.recovery":
                raise RuntimeError("prior recovery manifest schema differs")
            for item in manifest_value["files"]:
                relative = PurePosixPath(item["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"unsafe prior recovery path: {relative}")
                blob = dataset_root / f"recovery-{item['sha256']}.blob"
                verify_descriptor(blob, item, label=f"prior recovery blob {relative}")
                atomic_copy(blob, temporary / Path(*relative.parts))
            prior_root = temporary

        verify_inventory_manifest(
            prior_root,
            "RECOVERY_MANIFEST.json",
            f"{RECEIPT_SCHEMA}.recovery",
            expected_sha256=EXPECTED_PRIOR_RECOVERY_SHA256,
            extra_exclude=frozenset({"CLOUD_RUN_RECEIPT.json"}),
        )
        prior_campaign = prior_root / "campaign"
        if not prior_campaign.is_dir():
            raise RuntimeError("pinned prior output has no durable campaign")
        destination = durable_root / "campaign"
        if destination.exists():
            return False
        destination.mkdir(parents=True)
        for item in inventory(
            prior_campaign,
            exclude=frozenset({"DURABLE_CAMPAIGN_MANIFEST.json"}),
        ):
            atomic_copy(prior_campaign / item["path"], destination / item["path"])
        manifest = write_inventory_manifest(
            destination,
            "DURABLE_CAMPAIGN_MANIFEST.json",
            f"{RECEIPT_SCHEMA}.durable-campaign",
        )
        verify_inventory_manifest(
            destination,
            manifest.name,
            f"{RECEIPT_SCHEMA}.durable-campaign",
        )
        return True
    finally:
        if temporary is not None:
            shutil.rmtree(temporary, ignore_errors=True)


def write_recovery_manifest(durable_root: Path) -> Path:
    return write_inventory_manifest(
        durable_root,
        "RECOVERY_MANIFEST.json",
        f"{RECEIPT_SCHEMA}.recovery",
        extra_exclude=frozenset({"CLOUD_RUN_RECEIPT.json"}),
    )


def verify_recovery_root(
    durable_root: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    return verify_inventory_manifest(
        durable_root,
        "RECOVERY_MANIFEST.json",
        f"{RECEIPT_SCHEMA}.recovery",
        expected_sha256=expected_sha256,
        extra_exclude=frozenset({"CLOUD_RUN_RECEIPT.json"}),
    )


def validate_existing_output(
    durable_root: Path,
    *,
    command: list[str],
    cwd: Path,
    authority: dict[str, Any],
) -> dict[str, Any] | None:
    allowed = {
        "campaign",
        "CLOUD_ENVIRONMENT.json",
        "CLOUD_LAUNCH.json",
        "CLOUD_FAILURE.json",
        "CLOUD_RUN_RECEIPT.json",
        "RECOVERY_MANIFEST.json",
        "TRAINING.log",
    }
    extras = {path.name for path in durable_root.iterdir()} - allowed
    if extras:
        raise RuntimeError(f"foreign durable entries block resume: {sorted(extras)}")
    launch_path = durable_root / "CLOUD_LAUNCH.json"
    if launch_path.is_file():
        launch = load_json(launch_path)
        for key, value in {
            "command": command,
            "cwd": str(cwd),
            "authority": authority,
        }.items():
            if launch.get(key) != value:
                raise RuntimeError(f"existing launch receipt differs: {key}")
    receipt_path = durable_root / "CLOUD_RUN_RECEIPT.json"
    if not receipt_path.is_file():
        return None
    receipt = load_json(receipt_path)
    result = durable_root / "campaign" / "RESULT.json"
    recovery = durable_root / "RECOVERY_MANIFEST.json"
    if sha256_file(result) != receipt.get("campaign_result_sha256"):
        raise RuntimeError("completed campaign result hash differs")
    if sha256_file(recovery) != receipt.get("recovery_manifest_sha256"):
        raise RuntimeError("completed recovery manifest hash differs")
    verify_recovery_root(durable_root, str(receipt["recovery_manifest_sha256"]))
    verify_inventory_manifest(
        durable_root / "campaign",
        "DURABLE_CAMPAIGN_MANIFEST.json",
        f"{RECEIPT_SCHEMA}.durable-campaign",
    )
    return receipt


def run_private_segment(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    scratch_root = args.scratch_root.resolve()
    durable_root = args.durable_root.resolve()
    descriptor_path, descriptor_value = discover_packet(input_root)

    # The first observation is against the closest existing parent.  The
    # second, after packet extraction, is the exact filesystem containing the
    # live runtime and campaign checkpoints.
    preflight = admit_storage(scratch_root, durable_root)
    scratch_root.mkdir(parents=True, exist_ok=True)
    durable_root.mkdir(parents=True, exist_ok=True)
    runtime_root = scratch_root / "runtime"
    scratch_campaign = scratch_root / "campaign"
    durable_campaign = durable_root / "campaign"
    packet = extract_packet(descriptor_path, descriptor_value, runtime_root)
    admitted = admit_storage(scratch_campaign, durable_campaign)
    config = packet["remote_config"]
    if config != EXPECTED_REMOTE_CONFIG:
        raise RuntimeError("private CPU packet contract differs")
    paths = packet["paths"]
    scbe_root = runtime_root / paths["scbe_root"]
    baseline_run = runtime_root / paths["baseline_run"]
    source_dir = runtime_root / paths["source_dir"]
    preregistration = scbe_root / paths["preregistration"]
    campaign_source = scbe_root / paths["campaign"]
    for required in (
        scbe_root,
        baseline_run,
        source_dir,
        preregistration,
        campaign_source,
    ):
        required.resolve(strict=True)

    command = [
        sys.executable,
        "-m",
        "python.scbe.clay_hybrid_input_access_campaign",
        "--baseline-run",
        str(baseline_run),
        "--output-dir",
        str(scratch_campaign),
        "--source-dir",
        str(source_dir),
        "--preregistration",
        str(preregistration),
        "--steps",
        str(config["steps"]),
        "--checkpoint-every",
        str(config["checkpoint_every"]),
        "--batch-size",
        str(config["batch_size"]),
        "--threads",
        str(config["threads"]),
        "--minimum-free-gib",
        str(config["minimum_free_gib"]),
    ]
    import_prior_output(input_root, durable_root)
    completed = validate_existing_output(
        durable_root,
        command=command,
        cwd=scbe_root,
        authority=packet["authority"],
    )
    if completed is not None:
        return completed
    restored = restore_durable_campaign(durable_campaign, scratch_campaign)
    if not restored and scratch_campaign.exists() and inventory(scratch_campaign):
        raise RuntimeError("unverified scratch campaign blocks a fresh run")

    environment = {
        "schema": f"{RECEIPT_SCHEMA}.environment",
        "checked_at_utc": utc_now(),
        "platform": platform.platform(),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "dataset_descriptor_sha256": sha256_file(descriptor_path),
        "packet_manifest_sha256": sha256_file(runtime_root / PACKET_MANIFEST_NAME),
        "config": config,
        "authority": packet["authority"],
        "pre_extraction_storage": preflight,
        "exact_training_storage": admitted,
        "restored_durable_campaign": restored,
        "privacy_runtime_claim": (
            "CONFIGURED_BY_PRIVATE_OFFLINE_KERNEL_METADATA; runtime receipt alone " "does not prove network isolation"
        ),
    }
    write_json(durable_root / "CLOUD_ENVIRONMENT.json", environment)
    write_json(
        durable_root / "CLOUD_LAUNCH.json",
        {
            "schema": f"{RECEIPT_SCHEMA}.launch",
            "launched_at_utc": utc_now(),
            "command": command,
            "cwd": str(scbe_root),
            "authority": packet["authority"],
            "scratch_campaign": str(scratch_campaign),
            "durable_campaign": str(durable_campaign),
        },
    )
    child_env = os.environ.copy()
    child_env["SCBE_ROOT"] = str(scbe_root)
    log_path = durable_root / "TRAINING.log"
    try:
        with log_path.open("a", encoding="utf-8", newline="\n") as log:
            log.write(f"\n--- resume-at {utc_now()} ---\n")
            log.flush()
            process = subprocess.Popen(
                command,
                cwd=scbe_root,
                env=child_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
                try:
                    event = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    event = None
                if isinstance(event, dict) and event.get("status") in {
                    "TRAINING",
                    "ARM_COMPLETE",
                }:
                    try:
                        sync_campaign_to_durable(
                            scratch_campaign,
                            durable_campaign,
                        )
                        write_recovery_manifest(durable_root)
                    except Exception:
                        process.terminate()
                        process.wait(timeout=30)
                        raise
            return_code = process.wait()
    except Exception as error:
        write_json(
            durable_root / "CLOUD_FAILURE.json",
            {
                "schema": f"{RECEIPT_SCHEMA}.failure",
                "status": "FAILED",
                "error_type": type(error).__name__,
                "error": str(error),
                "failed_at_utc": utc_now(),
            },
        )
        write_recovery_manifest(durable_root)
        raise
    if return_code != 0:
        failure = {
            "schema": f"{RECEIPT_SCHEMA}.failure",
            "status": "FAILED",
            "return_code": return_code,
            "log_sha256": sha256_file(log_path),
            "failed_at_utc": utc_now(),
        }
        write_json(durable_root / "CLOUD_FAILURE.json", failure)
        write_recovery_manifest(durable_root)
        raise RuntimeError(f"hybrid input-access campaign exited {return_code}")

    sync_receipt = sync_campaign_to_durable(scratch_campaign, durable_campaign)
    result_path = durable_campaign / "RESULT.json"
    result_path.resolve(strict=True)
    recovery_path = write_recovery_manifest(durable_root)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "COMPLETE_CONTROLLED_SEGMENT_NO_PROMOTION",
        "completed_at_utc": utc_now(),
        "campaign_result_sha256": sha256_file(result_path),
        "recovery_manifest_sha256": sha256_file(recovery_path),
        "durable_campaign_manifest_sha256": sync_receipt["manifest_sha256"],
        "config": config,
        "authority": packet["authority"],
        "final_storage": admit_storage(scratch_campaign, durable_campaign),
        "claim_boundary": "Private controlled segment; no promotion authority.",
    }
    write_json(durable_root / "CLOUD_RUN_RECEIPT.json", receipt)
    validate_existing_output(
        durable_root,
        command=command,
        cwd=scbe_root,
        authority=packet["authority"],
    )
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument(
        "--scratch-root",
        type=Path,
        default=Path("/tmp/clay-hybrid-input-access-efficacy-20261119-v1"),
    )
    parser.add_argument(
        "--durable-root",
        type=Path,
        default=Path("/kaggle/working/clay-hybrid-input-access-efficacy-20261119-v1"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    receipt = run_private_segment(parse_args(arguments))
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
