"""Run the private Clay frozen-adapter compatibility segment on Kaggle.

This entry point verifies and extracts one hash-pinned packet, records the
actual Linux/Python/Torch environment, and invokes Clay's unchanged CPU trainer.
The reduced cloud lineage is compatibility evidence only and has no promotion,
merge, execution, tool-dispatch, or partial-unfreeze authority.
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
from typing import Any, Iterable
import zipfile

import numpy as np
import torch

PACKET_SCHEMA = "clay.frozen-multiview-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.frozen-multiview-kaggle-dataset.v1"
RECEIPT_SCHEMA = "clay.frozen-multiview-kaggle-compatibility.v1"
EXPECTED_DATASET_ID = "issacizrealdavis/clay-frozen-multiview-compat-input-20261114"
PACKET_MANIFEST_NAME = "CLAY_FROZEN_MULTIVIEW_KAGGLE_PACKET.json"
DESCRIPTOR_NAME = "PACKET_DESCRIPTOR.json"


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
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def verify_descriptor(path: Path, expected: dict[str, Any], *, label: str) -> None:
    if path.stat().st_size != int(expected["bytes"]):
        raise RuntimeError(f"{label} byte count differs: {path}")
    if sha256_file(path) != str(expected["sha256"]).casefold():
        raise RuntimeError(f"{label} hash differs: {path}")


def discover_packet(input_root: Path) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(input_root.rglob(DESCRIPTOR_NAME)):
        value = load_json(path)
        if value.get("schema") == DESCRIPTOR_SCHEMA and value.get("dataset_id") == EXPECTED_DATASET_ID:
            matches.append((path, value))
    if len(matches) != 1:
        visible = [str(path) for path in sorted(input_root.glob("**/*"))[:200]]
        raise RuntimeError(
            f"expected one {EXPECTED_DATASET_ID} packet, found {len(matches)}; " f"visible paths: {visible}"
        )
    return matches[0]


def _safe_archive_members(archive: zipfile.ZipFile) -> tuple[zipfile.ZipInfo, ...]:
    members = tuple(archive.infolist())
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise ValueError(f"unsafe archive member: {member.filename}")
    return members


def extract_and_verify_packet(
    descriptor_path: Path,
    descriptor: dict[str, Any],
    runtime_root: Path,
) -> tuple[Path, dict[str, Any]]:
    if runtime_root.exists():
        raise FileExistsError(f"runtime packet path already exists: {runtime_root}")
    archive_descriptor = descriptor.get("archive")
    manifest_descriptor = descriptor.get("packet_manifest")
    if not isinstance(archive_descriptor, dict) or not isinstance(manifest_descriptor, dict):
        raise TypeError("packet descriptor lacks archive or manifest descriptor")
    archive_path = descriptor_path.parent / str(archive_descriptor["path"])
    verify_descriptor(archive_path, archive_descriptor, label="packet archive")

    runtime_root.mkdir(parents=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        members = _safe_archive_members(archive)
        archive.extractall(runtime_root, members=members)

    manifest_path = runtime_root / PACKET_MANIFEST_NAME
    verify_descriptor(manifest_path, manifest_descriptor, label="packet manifest")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != PACKET_SCHEMA:
        raise ValueError("packet manifest schema changed")
    if manifest.get("dataset_id") != EXPECTED_DATASET_ID:
        raise ValueError("packet dataset identity changed")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("packet manifest has no files")
    for item in files:
        if not isinstance(item, dict):
            raise TypeError("packet file descriptor must be an object")
        relative = PurePosixPath(str(item["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe packet path: {relative}")
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root):
            raise ValueError(f"packet path escapes root: {relative}")
        verify_descriptor(path, item, label=f"packet file {relative}")
    return manifest_path, manifest


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


def _effective(value: Any, fallback: Any) -> Any:
    return fallback if value is None else value


def run_compatibility(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    output_root = args.output_root.resolve()
    runtime_root = args.runtime_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    descriptor_path, dataset_descriptor = discover_packet(input_root)
    manifest_path, packet = extract_and_verify_packet(descriptor_path, dataset_descriptor, runtime_root)
    defaults = packet.get("remote_config")
    if not isinstance(defaults, dict) or defaults.get("device") != "cpu":
        raise ValueError("packet does not declare the CPU compatibility contract")

    config = {
        "seeds": str(_effective(args.seeds, ",".join(map(str, defaults["seeds"])))),
        "data_seed": int(_effective(args.data_seed, defaults["data_seed"])),
        "rows_per_view": int(_effective(args.rows_per_view, defaults["rows_per_view"])),
        "holdout_rows": int(_effective(args.holdout_rows, defaults["holdout_rows"])),
        "count_steps": int(_effective(args.count_steps, defaults["count_steps"])),
        "grow_steps": int(_effective(args.grow_steps, defaults["grow_steps"])),
        "checkpoint_every": int(_effective(args.checkpoint_every, defaults["checkpoint_every"])),
        "batch_size": int(_effective(args.batch_size, defaults["batch_size"])),
        "learning_rate": float(_effective(args.learning_rate, defaults["learning_rate"])),
        "threads": int(_effective(args.threads, defaults["threads"])),
        "minimum_free_gib": float(_effective(args.minimum_free_gib, defaults["minimum_free_gib"])),
        "device": "cpu",
    }

    scbe_root = runtime_root / "scbe_repo"
    loom_root = runtime_root / "loom_root"
    source_dir = loom_root / "experiments" / "clay_action_compiler_20261109"
    runner = scbe_root / "scripts" / "research" / "run_clay_frozen_multiview_adapter.py"
    preregistration = scbe_root / "docs" / "research" / "CLAY_FROZEN_MULTIVIEW_ADAPTER_PREREGISTRATION_20261113.md"
    for required in (source_dir, runner, preregistration):
        if not required.exists():
            raise FileNotFoundError(required)

    disk = shutil.disk_usage(output_root)
    environment = {
        "schema": f"{RECEIPT_SCHEMA}.environment",
        "checked_at_utc": utc_now(),
        "platform": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "numpy": np.__version__,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count(),
        "free_bytes": disk.free,
        "packet_manifest": str(manifest_path),
        "packet_manifest_sha256": sha256_file(manifest_path),
        "dataset_descriptor": str(descriptor_path),
        "dataset_descriptor_sha256": sha256_file(descriptor_path),
        "config": config,
        "authority": {
            "execution": "NONE",
            "merge": "NONE",
            "partial_unfreeze": "NONE",
            "promotion": "NONE",
            "tool_dispatch": "DISABLED",
        },
    }
    write_json(output_root / "CLOUD_ENVIRONMENT.json", environment)

    command = [
        sys.executable,
        str(runner),
        "--output-dir",
        str(output_root / "campaign"),
        "--source-dir",
        str(source_dir),
        "--preregistration",
        str(preregistration),
        "--seeds",
        config["seeds"],
        "--data-seed",
        str(config["data_seed"]),
        "--rows-per-view",
        str(config["rows_per_view"]),
        "--holdout-rows",
        str(config["holdout_rows"]),
        "--count-steps",
        str(config["count_steps"]),
        "--grow-steps",
        str(config["grow_steps"]),
        "--checkpoint-every",
        str(config["checkpoint_every"]),
        "--batch-size",
        str(config["batch_size"]),
        "--learning-rate",
        str(config["learning_rate"]),
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
            "config": config,
            "claim_boundary": (
                "Reduced-budget cross-platform checkpoint/loader compatibility; "
                "not comparable to the full local campaign."
            ),
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
        write_json(
            output_root / "CLOUD_FAILURE.json",
            {
                "schema": f"{RECEIPT_SCHEMA}.failure",
                "failed_at_utc": utc_now(),
                "return_code": return_code,
                "log_sha256": sha256_file(log_path),
                "authority": environment["authority"],
            },
        )
        raise RuntimeError(f"compatibility trainer exited {return_code}")

    campaign_result = output_root / "campaign" / "RESULT.json"
    if not campaign_result.is_file():
        raise RuntimeError("trainer completed without campaign RESULT.json")
    inventory = recovery_inventory(output_root)
    write_json(
        output_root / "RECOVERY_MANIFEST.json",
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
        "status": "COMPLETE_COMPATIBILITY_ONLY_NO_PROMOTION",
        "completed_at_utc": utc_now(),
        "campaign_result": str(campaign_result),
        "campaign_result_sha256": sha256_file(campaign_result),
        "recovery_manifest": str(output_root / "RECOVERY_MANIFEST.json"),
        "recovery_manifest_sha256": sha256_file(output_root / "RECOVERY_MANIFEST.json"),
        "config": config,
        "authority": environment["authority"],
        "claim_boundary": (
            "Cloud training mechanics and checkpoint recovery only. Reduced steps, "
            "rows, and new seeds make this ineligible for local capability gates."
        ),
    }
    write_json(output_root / "CLOUD_COMPAT_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/kaggle/working/clay-frozen-multiview-compat-20261114-v1"),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/kaggle/working/clay-frozen-multiview-runtime-packet"),
    )
    parser.add_argument("--seeds")
    parser.add_argument("--data-seed", type=int)
    parser.add_argument("--rows-per-view", type=int)
    parser.add_argument("--holdout-rows", type=int)
    parser.add_argument("--count-steps", type=int)
    parser.add_argument("--grow-steps", type=int)
    parser.add_argument("--checkpoint-every", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--threads", type=int)
    parser.add_argument("--minimum-free-gib", type=float)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    receipt = run_compatibility(parse_args(arguments))
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
