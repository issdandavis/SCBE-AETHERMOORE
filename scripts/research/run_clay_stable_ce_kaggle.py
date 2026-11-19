"""Verify and run the private offline Clay stable-CE Kaggle packet."""

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

PACKET_SCHEMA = "clay.stable-ce-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.stable-ce-kaggle-dataset.v1"
RECEIPT_SCHEMA = "clay.stable-ce-kaggle-run.v1"
EXPECTED_DATASET_ID = "issacizrealdavis/clay-stable-ce-efficacy-input-20261119"
DESCRIPTOR_NAME = "PACKET_DESCRIPTOR.json"
PACKET_MANIFEST_NAME = "CLAY_STABLE_CE_KAGGLE_PACKET.json"


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
        raise RuntimeError(f"expected one stable-CE packet, found {len(matches)}")
    return matches[0]


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
    if runtime_root.exists():
        raise FileExistsError(f"runtime packet already exists: {runtime_root}")
    archive_descriptor = descriptor_value["archive"]
    archive_path = descriptor_path.parent / archive_descriptor["path"]
    verify_descriptor(archive_path, archive_descriptor, label="packet archive")
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
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe packet path: {relative}")
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root):
            raise ValueError(f"packet path escapes root: {relative}")
        verify_descriptor(path, item, label=f"packet file {relative}")
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


def run_private_segment(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    output_root = args.output_root.resolve()
    runtime_root = args.runtime_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    descriptor_path, descriptor_value = discover_packet(input_root)
    packet = extract_packet(descriptor_path, descriptor_value, runtime_root)
    config = packet["remote_config"]
    if config["device"] != "cpu" or packet["authority"]["visibility"] != "PRIVATE":
        raise RuntimeError("private CPU packet contract differs")
    paths = packet["paths"]
    scbe_root = runtime_root / paths["scbe_root"]
    baseline_run = runtime_root / paths["baseline_run"]
    source_dir = runtime_root / paths["source_dir"]
    preregistration = scbe_root / paths["preregistration"]
    campaign = scbe_root / paths["campaign"]
    for required in (scbe_root, baseline_run, source_dir, preregistration, campaign):
        required.resolve(strict=True)

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
    command = [
        sys.executable,
        "-m",
        "python.scbe.clay_stable_ce_efficacy_campaign",
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
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
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
        raise RuntimeError(f"stable-CE campaign exited {return_code}")
    result_path = output_root / "campaign" / "RESULT.json"
    result_path.resolve(strict=True)
    inventory = recovery_inventory(output_root)
    recovery_path = output_root / "RECOVERY_MANIFEST.json"
    write_json(
        recovery_path,
        {
            "schema": f"{RECEIPT_SCHEMA}.recovery",
            "created_at_utc": utc_now(),
            "files": inventory,
            "file_count": len(inventory),
            "total_bytes": sum(int(row["bytes"]) for row in inventory),
        },
    )
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
        default=Path("/kaggle/working/clay-stable-ce-efficacy-20261119-v1"),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/kaggle/working/clay-stable-ce-runtime-packet"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    receipt = run_private_segment(parse_args(arguments))
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
