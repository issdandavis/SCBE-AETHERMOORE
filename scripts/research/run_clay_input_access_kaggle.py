"""Verify and run the private offline Clay input-access Kaggle packet."""

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
from typing import Any, Iterable
import zipfile

import torch

PACKET_SCHEMA = "clay.input-access-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.input-access-kaggle-dataset.v1"
RECEIPT_SCHEMA = "clay.input-access-kaggle-run.v1"
EXPECTED_DATASET_ID = "issacizrealdavis/clay-input-access-efficacy-input-20261119"
DESCRIPTOR_NAME = "PACKET_DESCRIPTOR.json"
PACKET_MANIFEST_NAME = "CLAY_INPUT_ACCESS_KAGGLE_PACKET.json"
EXPECTED_DESCRIPTOR_SHA256 = "__BUILD_PINNED_DESCRIPTOR_SHA256__"
EXPECTED_ARCHIVE_SHA256 = "__BUILD_PINNED_ARCHIVE_SHA256__"
EXPECTED_PACKET_MANIFEST_SHA256 = "__BUILD_PINNED_PACKET_MANIFEST_SHA256__"
EXPECTED_PREREGISTRATION_SHA256 = "__BUILD_PINNED_PREREGISTRATION_SHA256__"
EXPECTED_CAMPAIGN_SHA256 = "__BUILD_PINNED_CAMPAIGN_SHA256__"
EXPECTED_PRIOR_RECOVERY_SHA256 = "__BUILD_PINNED_PRIOR_RECOVERY_SHA256__"
EXPECTED_REMOTE_CONFIG = {
    "seeds": [20261134, 20261135, 20261136],
    "steps": 2000,
    "checkpoint_every": 250,
    "batch_size": 128,
    "threads": 2,
    "minimum_free_gib": 25.0,
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
        raise RuntimeError(f"expected one input-access packet, found {len(matches)}")
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
    if authority.get("visibility") != "PRIVATE" or authority.get("internet") != "DISABLED":
        raise ValueError("packet privacy/offline authority differs")
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe packet path: {relative}")
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root):
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


def recovery_inventory(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path.name.endswith(".pending") or path.name == "RECOVERY_MANIFEST.json":
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return rows


def write_recovery_manifest(root: Path) -> Path:
    inventory = recovery_inventory(root)
    path = root / "RECOVERY_MANIFEST.json"
    write_json(
        path,
        {
            "schema": f"{RECEIPT_SCHEMA}.recovery",
            "created_at_utc": utc_now(),
            "files": inventory,
            "file_count": len(inventory),
            "total_bytes": sum(int(row["bytes"]) for row in inventory),
        },
    )
    return path


def verify_recovery_root(root: Path, expected_sha256: str) -> dict[str, Any]:
    manifest_path = root / "RECOVERY_MANIFEST.json"
    if sha256_file(manifest_path) != expected_sha256:
        raise RuntimeError("prior recovery manifest trust anchor differs")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != f"{RECEIPT_SCHEMA}.recovery":
        raise RuntimeError("prior recovery schema differs")
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe prior recovery path: {relative}")
        path = (root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError(f"prior recovery path escapes root: {relative}")
        verify_descriptor(path, item, label=f"prior recovery file {relative}")
    actual = recovery_inventory(root)
    if actual != manifest["files"]:
        raise RuntimeError("prior recovery inventory differs")
    if int(manifest["file_count"]) != len(actual):
        raise RuntimeError("prior recovery file count differs")
    if int(manifest["total_bytes"]) != sum(int(row["bytes"]) for row in actual):
        raise RuntimeError("prior recovery total bytes differ")
    return manifest


def import_prior_campaign(input_root: Path, output_root: Path) -> bool:
    if EXPECTED_PRIOR_RECOVERY_SHA256 == "NONE":
        return False
    matches = [
        path
        for path in input_root.rglob("RECOVERY_MANIFEST.json")
        if sha256_file(path) == EXPECTED_PRIOR_RECOVERY_SHA256
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one pinned prior recovery, found {len(matches)}")
    prior_root = matches[0].parent.resolve(strict=True)
    verify_recovery_root(prior_root, EXPECTED_PRIOR_RECOVERY_SHA256)
    prior_campaign = prior_root / "campaign"
    if not prior_campaign.is_dir():
        raise RuntimeError("pinned prior recovery has no campaign directory")
    destination = output_root / "campaign"
    if destination.exists():
        return False
    shutil.copytree(prior_campaign, destination, copy_function=shutil.copy2)
    return True


def validate_existing_output(
    output_root: Path,
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
    extras = {path.name for path in output_root.iterdir()} - allowed
    if extras:
        raise RuntimeError(f"foreign output entries block resume: {sorted(extras)}")
    launch_path = output_root / "CLOUD_LAUNCH.json"
    if launch_path.is_file():
        launch = load_json(launch_path)
        for key, value in {
            "command": command,
            "cwd": str(cwd),
            "authority": authority,
        }.items():
            if launch.get(key) != value:
                raise RuntimeError(f"existing launch receipt differs: {key}")
    receipt_path = output_root / "CLOUD_RUN_RECEIPT.json"
    if receipt_path.is_file():
        receipt = load_json(receipt_path)
        result = output_root / "campaign" / "RESULT.json"
        recovery = output_root / "RECOVERY_MANIFEST.json"
        if sha256_file(result) != receipt.get("campaign_result_sha256"):
            raise RuntimeError("completed campaign result hash differs")
        if sha256_file(recovery) != receipt.get("recovery_manifest_sha256"):
            raise RuntimeError("completed recovery manifest hash differs")
        verify_recovery_root(output_root, str(receipt["recovery_manifest_sha256"]))
        return receipt
    return None


def run_private_segment(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    output_root = args.output_root.resolve()
    runtime_root = args.runtime_root.resolve()
    if output_root.exists() and not output_root.is_dir():
        raise RuntimeError("output root is not a directory")
    output_root.mkdir(parents=True, exist_ok=True)
    descriptor_path, descriptor_value = discover_packet(input_root)
    packet = extract_packet(descriptor_path, descriptor_value, runtime_root)
    config = packet["remote_config"]
    if config != EXPECTED_REMOTE_CONFIG:
        raise RuntimeError("private CPU packet contract differs")
    paths = packet["paths"]
    scbe_root = runtime_root / paths["scbe_root"]
    baseline_run = runtime_root / paths["baseline_run"]
    source_dir = runtime_root / paths["source_dir"]
    preregistration = scbe_root / paths["preregistration"]
    campaign = scbe_root / paths["campaign"]
    for required in (scbe_root, baseline_run, source_dir, preregistration, campaign):
        required.resolve(strict=True)

    command = [
        sys.executable,
        "-m",
        "python.scbe.clay_input_access_campaign",
        "--baseline-run",
        str(baseline_run),
        "--output-dir",
        str(output_root / "campaign"),
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
    import_prior_campaign(input_root, output_root)
    completed = validate_existing_output(
        output_root,
        command=command,
        cwd=scbe_root,
        authority=packet["authority"],
    )
    if completed is not None:
        return completed

    environment = {
        "schema": f"{RECEIPT_SCHEMA}.environment",
        "checked_at_utc": utc_now(),
        "platform": platform.platform(),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "free_bytes": shutil.disk_usage(output_root).free,
        "dataset_descriptor_sha256": sha256_file(descriptor_path),
        "packet_manifest_sha256": sha256_file(runtime_root / PACKET_MANIFEST_NAME),
        "config": config,
        "authority": packet["authority"],
    }
    write_json(output_root / "CLOUD_ENVIRONMENT.json", environment)
    write_json(
        output_root / "CLOUD_LAUNCH.json",
        {
            "schema": f"{RECEIPT_SCHEMA}.launch",
            "launched_at_utc": utc_now(),
            "command": command,
            "cwd": str(scbe_root),
            "authority": packet["authority"],
        },
    )
    child_env = os.environ.copy()
    child_env["SCBE_ROOT"] = str(scbe_root)
    log_path = output_root / "TRAINING.log"
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
                write_recovery_manifest(output_root)
        return_code = process.wait()
    if return_code != 0:
        failure = {
            "schema": f"{RECEIPT_SCHEMA}.failure",
            "status": "FAILED",
            "return_code": return_code,
            "log_sha256": sha256_file(log_path),
            "failed_at_utc": utc_now(),
        }
        write_json(output_root / "CLOUD_FAILURE.json", failure)
        write_recovery_manifest(output_root)
        raise RuntimeError(f"input-access campaign exited {return_code}")
    result_path = output_root / "campaign" / "RESULT.json"
    result_path.resolve(strict=True)
    recovery_path = write_recovery_manifest(output_root)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "COMPLETE_CONTROLLED_SEGMENT_NO_PROMOTION",
        "completed_at_utc": utc_now(),
        "campaign_result_sha256": sha256_file(result_path),
        "recovery_manifest_sha256": sha256_file(recovery_path),
        "config": config,
        "authority": packet["authority"],
        "claim_boundary": "Bounded private controlled segment; no promotion authority.",
    }
    write_json(output_root / "CLOUD_RUN_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/kaggle/working/clay-input-access-efficacy-20261119-v1"),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/kaggle/working/clay-input-access-runtime-packet"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    receipt = run_private_segment(parse_args(arguments))
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
