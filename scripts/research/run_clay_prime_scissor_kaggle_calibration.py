"""Verify a sealed prime-scissor packet and run GPU timing calibration only.

This standalone Kaggle entry has no material-training option.  It always calls
the experiment runner with ``--calibration-only``, fixed batch/step/storage
arguments, and fails if a horse, checkpoint, or model artifact appears.
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
import stat
import subprocess
import sys
from typing import Any, Iterable, Mapping
import zipfile

PACKET_SCHEMA = "clay.prime-scissor-input-kaggle-calibration-packet.v1"
DESCRIPTOR_SCHEMA = "clay.prime-scissor-input-kaggle-calibration-dataset.v1"
RECEIPT_SCHEMA = "clay.prime-scissor-input-kaggle-calibration.v1"
KERNEL_AUTHORITY_SCHEMA = "clay.prime-scissor-input-kaggle-calibration-kernel-authority.v1"
DESCRIPTOR_NAME = "PACKET_DESCRIPTOR.json"
MANIFEST_NAME = "PACKET_MANIFEST.json"
FIXED_BATCH_SIZE = 128
FIXED_GROW_STEPS = 18_000
FIXED_MINIMUM_FREE_GIB = 25.0
# The packet builder replaces this exact sentinel in the generated Kaggle
# code_file.  Keeping the source value null prevents a source checkout from
# silently acquiring launch authority.
EMBEDDED_KERNEL_AUTHORITY_JSON: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
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
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def verify_descriptor(path: Path, expected: Mapping[str, Any], *, label: str) -> None:
    if path.stat().st_size != int(expected["bytes"]):
        raise RuntimeError(f"{label} byte count differs: {path}")
    actual = sha256_file(path)
    if actual != str(expected["sha256"]).casefold():
        raise RuntimeError(f"{label} hash differs: expected {expected['sha256']}, got {actual}: {path}")


def _descriptor_relative_path(root: Path, value: object, *, label: str) -> Path:
    text = str(value)
    relative = PurePosixPath(text)
    if (
        not text
        or "\\" in text
        or "\x00" in text
        or relative.is_absolute()
        or ".." in relative.parts
        or not relative.parts
    ):
        raise ValueError(f"unsafe {label} path: {text}")
    resolved = (root / Path(*relative.parts)).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)):
        raise ValueError(f"{label} path escapes descriptor root: {text}")
    return resolved


def discover_packet(input_root: Path, dataset_id: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(input_root.rglob(DESCRIPTOR_NAME)):
        value = load_json(path)
        if value.get("schema") == DESCRIPTOR_SCHEMA and value.get("dataset_id") == dataset_id:
            matches.append((path, value))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {dataset_id} calibration packet, found {len(matches)}")
    return matches[0]


def load_kernel_authority(authority_path: Path) -> dict[str, Any]:
    default_path = Path(__file__).with_name("KERNEL_PACKET_AUTHORITY.json")
    requested = authority_path.resolve(strict=False)
    if authority_path.is_file():
        authority = load_json(authority_path.resolve(strict=True))
    elif requested == default_path.resolve(strict=False) and EMBEDDED_KERNEL_AUTHORITY_JSON is not None:
        value = json.loads(EMBEDDED_KERNEL_AUTHORITY_JSON)
        if not isinstance(value, dict):
            raise TypeError("embedded kernel packet authority is not one JSON object")
        if canonical_json(value) != EMBEDDED_KERNEL_AUTHORITY_JSON:
            raise RuntimeError("embedded kernel packet authority is not canonical JSON")
        authority = value
    else:
        # Preserve the strict missing-file failure for an explicit override or
        # an unrendered source entrypoint.
        authority = load_json(authority_path.resolve(strict=True))
    if authority.get("schema") != KERNEL_AUTHORITY_SCHEMA:
        raise RuntimeError("independent kernel packet authority schema differs")
    dataset_id = authority.get("dataset_id")
    if not isinstance(dataset_id, str) or "/" not in dataset_id:
        raise RuntimeError("independent kernel packet authority dataset id differs")
    return authority


def resolve_dataset_authority(
    authority_path: Path,
    requested_dataset_id: str | None,
) -> tuple[str, dict[str, Any]]:
    """Resolve packet discovery identity from the independently pinned authority."""

    authority = load_kernel_authority(authority_path)
    authority_dataset_id = str(authority["dataset_id"])
    if requested_dataset_id is not None and requested_dataset_id != authority_dataset_id:
        raise RuntimeError("explicit dataset id differs from independent kernel packet authority")
    return authority_dataset_id, authority


def verify_kernel_authority(
    authority_path: Path,
    descriptor_path: Path,
    packet_descriptor: Mapping[str, Any],
    *,
    authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    authority = dict(authority or load_kernel_authority(authority_path))
    verify_descriptor(
        descriptor_path,
        authority["packet_descriptor"],
        label="independently pinned packet descriptor",
    )
    for field in ("dataset_id", "packet_id", "archive", "packet_manifest"):
        if packet_descriptor.get(field) != authority.get(field):
            raise RuntimeError(f"packet descriptor differs from kernel authority: {field}")
    return authority


def _safe_members(archive: zipfile.ZipFile) -> tuple[zipfile.ZipInfo, ...]:
    members = tuple(archive.infolist())
    seen: set[str] = set()
    for member in members:
        name = member.filename
        relative = PurePosixPath(name)
        mode = (member.external_attr >> 16) & 0xFFFF
        if (
            not name
            or "\\" in name
            or "\x00" in name
            or relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
        ):
            raise ValueError(f"unsafe archive member: {name}")
        if name in seen:
            raise RuntimeError(f"duplicate archive member: {name}")
        seen.add(name)
        if stat.S_ISLNK(mode):
            raise ValueError(f"archive symlink is forbidden: {name}")
        if member.flag_bits & 0x1:
            raise ValueError(f"encrypted archive member is forbidden: {name}")
    return members


def _verify_manifest_self_hash(manifest: Mapping[str, Any]) -> None:
    expected = str(manifest.get("manifest_body_sha256", ""))
    if not expected or manifest.get("packet_id") != expected:
        raise RuntimeError("packet identity and manifest self-hash differ")
    body = dict(manifest)
    for field in ("packet_id", "manifest_body_sha256", "self_hash_rule"):
        body.pop(field, None)
    if stable_hash(body) != expected:
        raise RuntimeError("packet manifest self-hash differs")


def extract_and_verify_packet(
    descriptor_path: Path,
    packet_descriptor: Mapping[str, Any],
    runtime_root: Path,
) -> tuple[Path, dict[str, Any]]:
    if runtime_root.exists():
        raise FileExistsError(f"runtime root already exists: {runtime_root}")
    archive_record = packet_descriptor.get("archive")
    manifest_record = packet_descriptor.get("packet_manifest")
    if not isinstance(archive_record, Mapping) or not isinstance(manifest_record, Mapping):
        raise TypeError("packet descriptor lacks archive or manifest records")
    if manifest_record.get("path") != MANIFEST_NAME:
        raise ValueError("packet manifest descriptor path differs")
    archive_path = _descriptor_relative_path(
        descriptor_path.parent,
        archive_record["path"],
        label="archive descriptor",
    )
    verify_descriptor(archive_path, archive_record, label="calibration archive")
    runtime_root.mkdir(parents=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(runtime_root, members=_safe_members(archive))

    manifest_path = runtime_root / MANIFEST_NAME
    verify_descriptor(manifest_path, manifest_record, label="packet manifest")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != PACKET_SCHEMA:
        raise ValueError("packet manifest schema changed")
    if manifest.get("packet_id") != packet_descriptor.get("packet_id"):
        raise RuntimeError("dataset descriptor packet identity differs")
    _verify_manifest_self_hash(manifest)
    contract = manifest.get("fixed_run_contract")
    expected_contract = {
        "calibration_only": True,
        "device": "cuda",
        "batch_size": FIXED_BATCH_SIZE,
        "grow_steps_per_horse": FIXED_GROW_STEPS,
        "checkpoint_every": 500,
        "learning_rate": 0.002,
        "threads": 2,
        "minimum_free_gib": FIXED_MINIMUM_FREE_GIB,
        "internet": False,
        "gpu": True,
        "frozen_artifact_pack_sha256": manifest["facts"]["frozen_artifact_pack_sha256"],
    }
    if contract != expected_contract:
        raise RuntimeError("packet fixed calibration contract differs")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("packet manifest has no files")
    expected_paths = {MANIFEST_NAME}
    total = 0
    for item in files:
        if not isinstance(item, Mapping):
            raise TypeError("packet file descriptor must be an object")
        relative = PurePosixPath(str(item["path"]))
        if (
            "\\" in str(item["path"])
            or "\x00" in str(item["path"])
            or relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
        ):
            raise ValueError(f"unsafe packet path: {relative}")
        if str(relative) in expected_paths:
            raise RuntimeError(f"duplicate packet path: {relative}")
        expected_paths.add(str(relative))
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root.resolve()):
            raise ValueError(f"packet path escapes root: {relative}")
        verify_descriptor(path, item, label=f"packet file {relative}")
        total += int(item["bytes"])
    actual_paths = {path.relative_to(runtime_root).as_posix() for path in runtime_root.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise RuntimeError("archive contains unmanifested or missing files")
    if len(files) != int(manifest["file_count"]) or total != int(manifest["payload_bytes"]):
        raise RuntimeError("packet file count or payload byte total differs")
    artifact_path = runtime_root / "payload" / "frozen_artifacts" / "prime_scissor_inputs.pack"
    if not artifact_path.is_file():
        raise RuntimeError("packet lacks the required frozen artifact pack")
    artifact_hash = sha256_file(artifact_path)
    if artifact_hash != manifest["facts"]["frozen_artifact_pack_sha256"]:
        raise RuntimeError("frozen artifact pack hash differs from packet authority")
    return manifest_path, manifest


def calibration_command(packet_root: Path, output_root: Path, device: str) -> list[str]:
    if device not in {"auto", "cuda"}:
        raise ValueError("calibration device must be auto or cuda")
    repo = packet_root / "payload" / "scbe_repo"
    return [
        sys.executable,
        "-X",
        "utf8",
        str(repo / "python" / "scbe" / "clay_prime_scissor_input_campaign.py"),
        "--baseline-run",
        str(packet_root / "payload" / "baseline"),
        "--output-dir",
        str(output_root / "run"),
        "--preregistration",
        str(repo / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREREGISTRATION_20261118.md"),
        "--preflight-receipt",
        str(repo / "docs" / "research" / "CLAY_PRIME_SCISSOR_INPUT_PREFLIGHT_20261118.json"),
        "--clay-math-root",
        str(packet_root / "payload" / "clay_math_root"),
        "--source-dir",
        str(packet_root / "payload" / "loom_root" / "experiments" / "clay_action_compiler_20261109"),
        "--frozen-artifact-pack",
        str(packet_root / "payload" / "frozen_artifacts" / "prime_scissor_inputs.pack"),
        "--device",
        device,
        "--batch-size",
        str(FIXED_BATCH_SIZE),
        "--grow-steps",
        str(FIXED_GROW_STEPS),
        "--checkpoint-every",
        "500",
        "--learning-rate",
        "0.002",
        "--threads",
        "2",
        "--minimum-free-gib",
        str(FIXED_MINIMUM_FREE_GIB),
        "--calibration-only",
    ]


def _environment_receipt(output_root: Path, packet_id: str) -> dict[str, Any]:
    usage = shutil.disk_usage(output_root.anchor or "/")
    try:
        import torch

        torch_info: dict[str, Any] = {
            "version": torch.__version__,
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_version": torch.version.cuda,
            "device_count": int(torch.cuda.device_count()),
            "device_names": [torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())],
        }
    except Exception as error:  # pragma: no cover - only for broken cloud images
        torch_info = {"import_error": repr(error), "cuda_available": False}
    body = {
        "schema": f"{RECEIPT_SCHEMA}.environment",
        "created_at_utc": utc_now(),
        "packet_id": packet_id,
        "platform": platform.platform(),
        "python": sys.version,
        "executable": sys.executable,
        "torch": torch_info,
        "disk_free_gib": usage.free / (1024**3),
        "minimum_free_gib": FIXED_MINIMUM_FREE_GIB,
        "internet_expected": False,
        "kaggle_kernel_run_type": os.environ.get("KAGGLE_KERNEL_RUN_TYPE"),
    }
    return {**body, "receipt_sha256": stable_hash(body)}


def _forbidden_artifacts(output_root: Path) -> list[str]:
    forbidden: list[str] = []
    for path in output_root.rglob("*"):
        relative = path.relative_to(output_root).as_posix()
        if path.is_dir() and path.name in {"horses", "checkpoints"}:
            forbidden.append(relative + "/")
        elif path.is_file() and path.suffix.casefold() in {".pt", ".pth", ".ckpt"}:
            forbidden.append(relative)
    return sorted(forbidden)


def _run_calibration_inner(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    output_root = args.output_root.resolve()
    runtime_root = args.runtime_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    dataset_id, authority = resolve_dataset_authority(
        args.kernel_authority,
        args.dataset_id,
    )
    descriptor_path, packet_descriptor = discover_packet(input_root, dataset_id)
    verify_kernel_authority(
        args.kernel_authority,
        descriptor_path,
        packet_descriptor,
        authority=authority,
    )
    _, manifest = extract_and_verify_packet(descriptor_path, packet_descriptor, runtime_root)
    packet_id = str(manifest["packet_id"])
    environment = _environment_receipt(output_root, packet_id)
    write_json(output_root / "ENVIRONMENT_RECEIPT.json", environment)
    if environment.get("disk_free_gib", 0.0) < FIXED_MINIMUM_FREE_GIB:
        raise RuntimeError("Kaggle working disk does not clear the fixed 25 GiB floor")
    torch_info = environment.get("torch", {})
    if args.device == "cuda" and not bool(torch_info.get("cuda_available")):
        raise RuntimeError("private GPU kernel has no CUDA device")

    command = calibration_command(runtime_root, output_root, args.device)
    repo = runtime_root / "payload" / "scbe_repo"
    python_paths = [
        repo,
        repo / "python",
        runtime_root / "payload" / "clay_math_root",
        runtime_root / "payload" / "loom_root",
    ]
    environment_variables = os.environ.copy()
    environment_variables["PYTHONPATH"] = os.pathsep.join(
        [str(path) for path in python_paths]
        + ([environment_variables["PYTHONPATH"]] if environment_variables.get("PYTHONPATH") else [])
    )
    environment_variables["PYTHONHASHSEED"] = "0"
    environment_variables["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    launch_body = {
        "schema": f"{RECEIPT_SCHEMA}.launch",
        "created_at_utc": utc_now(),
        "packet_id": packet_id,
        "command": command,
        "command_sha256": stable_hash(command),
        "mode": "CALIBRATION_ONLY",
        "device": args.device,
        "batch_size": FIXED_BATCH_SIZE,
        "grow_steps_per_horse_for_projection": FIXED_GROW_STEPS,
        "minimum_free_gib": FIXED_MINIMUM_FREE_GIB,
        "internet": False,
        "material_training": "NONE",
    }
    launch = {**launch_body, "receipt_sha256": stable_hash(launch_body)}
    write_json(output_root / "LAUNCH_RECEIPT.json", launch)
    stdout_path = output_root / "CALIBRATION_STDOUT.log"
    stderr_path = output_root / "CALIBRATION_STDERR.log"
    result: subprocess.CompletedProcess[str] | None = None
    failure: dict[str, Any] | None = None
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=environment_variables,
        )
        stdout_path.write_text(result.stdout, encoding="utf-8", newline="\n")
        stderr_path.write_text(result.stderr, encoding="utf-8", newline="\n")
        if result.returncode != 0:
            raise RuntimeError(f"calibration runner exited {result.returncode}")
        timing_source = output_root / "run" / "TIMING_CALIBRATION.json"
        status_source = output_root / "run" / "STATUS.json"
        timing = load_json(timing_source)
        status_receipt = load_json(status_source)
        if status_receipt.get("status") != "CALIBRATION_COMPLETE_NO_HORSES_STARTED":
            raise RuntimeError("campaign did not exit through calibration-only status")
        if int(timing.get("representative_batch_size", -1)) != FIXED_BATCH_SIZE:
            raise RuntimeError("timing receipt batch size differs")
        if int(timing.get("preregistered_steps_per_horse_unchanged", -1)) != FIXED_GROW_STEPS:
            raise RuntimeError("timing receipt growth budget differs")
        if timing.get("actual_device") != "cuda":
            raise RuntimeError("timing receipt did not measure the Kaggle CUDA device")
        if int(timing.get("measured_steps", -1)) != 500:
            raise RuntimeError("timing receipt did not measure the required 500 steps")
        projected = float(timing.get("projected_15_horse_seconds_with_20_percent_margin", float("inf")))
        maximum = float(timing.get("maximum_admitted_seconds", -1.0))
        if maximum != 24 * 60 * 60 or projected > maximum:
            raise RuntimeError("timing receipt does not clear the fixed 24h quota gate")
        shutil.copyfile(timing_source, output_root / "TIMING_CALIBRATION.json")
        forbidden = _forbidden_artifacts(output_root)
        if forbidden:
            raise RuntimeError(f"calibration emitted forbidden artifacts: {forbidden}")
        recovery_body = {
            "schema": f"{RECEIPT_SCHEMA}.recovery",
            "status": "PASS_CALIBRATION_ONLY_NO_HORSES_STARTED",
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "packet_id": packet_id,
            "returncode": result.returncode,
            "timing_calibration_sha256": sha256_file(output_root / "TIMING_CALIBRATION.json"),
            "stdout_sha256": sha256_file(stdout_path),
            "stderr_sha256": sha256_file(stderr_path),
            "forbidden_artifacts": forbidden,
            "material_training": "NONE",
            "internet": False,
        }
        recovery = {
            **recovery_body,
            "receipt_sha256": stable_hash(recovery_body),
        }
        write_json(output_root / "RECOVERY_RECEIPT.json", recovery)
        return recovery
    except Exception as error:
        forbidden = _forbidden_artifacts(output_root)
        failure_body = {
            "schema": f"{RECEIPT_SCHEMA}.failure",
            "status": "FAIL_CLOSED_NO_MATERIAL_TRAINING",
            "failed_at_utc": utc_now(),
            "packet_id": packet_id,
            "error_type": type(error).__name__,
            "error": str(error),
            "returncode": None if result is None else result.returncode,
            "stdout_sha256": (sha256_file(stdout_path) if stdout_path.is_file() else None),
            "stderr_sha256": (sha256_file(stderr_path) if stderr_path.is_file() else None),
            "forbidden_artifacts": forbidden,
            "material_training": "NONE",
        }
        failure = {**failure_body, "receipt_sha256": stable_hash(failure_body)}
        write_json(output_root / "FAILURE_RECEIPT.json", failure)
        recovery_body = {
            "schema": f"{RECEIPT_SCHEMA}.recovery",
            "status": "FAIL_CLOSED_RECOVERY_RECORDED",
            "started_at_utc": started_at,
            "completed_at_utc": utc_now(),
            "packet_id": packet_id,
            "failure_receipt_sha256": sha256_file(output_root / "FAILURE_RECEIPT.json"),
            "material_training": "NONE",
        }
        write_json(
            output_root / "RECOVERY_RECEIPT.json",
            {**recovery_body, "receipt_sha256": stable_hash(recovery_body)},
        )
        raise


def run_calibration(args: argparse.Namespace) -> dict[str, Any]:
    """Run fail-closed while receipting even pre-launch verification failures."""

    try:
        return _run_calibration_inner(args)
    except Exception as error:
        output_root = args.output_root.resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        environment_path = output_root / "ENVIRONMENT_RECEIPT.json"
        if not environment_path.is_file():
            environment = _environment_receipt(output_root, "UNVERIFIED")
            write_json(environment_path, environment)
        else:
            environment = load_json(environment_path)
        packet_id = str(environment.get("packet_id", "UNVERIFIED"))
        launch_path = output_root / "LAUNCH_RECEIPT.json"
        if not launch_path.is_file():
            launch_body = {
                "schema": f"{RECEIPT_SCHEMA}.launch",
                "created_at_utc": utc_now(),
                "packet_id": packet_id,
                "status": "NOT_LAUNCHED_PACKET_OR_ENVIRONMENT_GATE_FAILED",
                "mode": "CALIBRATION_ONLY",
                "device": args.device,
                "batch_size": FIXED_BATCH_SIZE,
                "grow_steps_per_horse_for_projection": FIXED_GROW_STEPS,
                "minimum_free_gib": FIXED_MINIMUM_FREE_GIB,
                "internet": False,
                "material_training": "NONE",
            }
            write_json(
                launch_path,
                {**launch_body, "receipt_sha256": stable_hash(launch_body)},
            )
        failure_path = output_root / "FAILURE_RECEIPT.json"
        if not failure_path.is_file():
            failure_body = {
                "schema": f"{RECEIPT_SCHEMA}.failure",
                "status": "FAIL_CLOSED_NO_MATERIAL_TRAINING",
                "failed_at_utc": utc_now(),
                "packet_id": packet_id,
                "error_type": type(error).__name__,
                "error": str(error),
                "returncode": None,
                "forbidden_artifacts": _forbidden_artifacts(output_root),
                "material_training": "NONE",
            }
            write_json(
                failure_path,
                {**failure_body, "receipt_sha256": stable_hash(failure_body)},
            )
        recovery_path = output_root / "RECOVERY_RECEIPT.json"
        if not recovery_path.is_file():
            recovery_body = {
                "schema": f"{RECEIPT_SCHEMA}.recovery",
                "status": "FAIL_CLOSED_RECOVERY_RECORDED",
                "completed_at_utc": utc_now(),
                "packet_id": packet_id,
                "failure_receipt_sha256": sha256_file(failure_path),
                "material_training": "NONE",
            }
            write_json(
                recovery_path,
                {**recovery_body, "receipt_sha256": stable_hash(recovery_body)},
            )
        raise


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument(
        "--dataset-id",
        default=None,
        help=(
            "Optional explicit dataset identity. When omitted, the identity is derived "
            "from KERNEL_PACKET_AUTHORITY.json; an explicit value must match it."
        ),
    )
    parser.add_argument(
        "--kernel-authority",
        type=Path,
        default=Path(__file__).with_name("KERNEL_PACKET_AUTHORITY.json"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/kaggle/working/clay-prime-scissor-calibration"),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/kaggle/working/clay-prime-scissor-calibration-runtime"),
    )
    parser.add_argument("--device", choices=("auto", "cuda"), default="cuda")
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = run_calibration(args)
    print(canonical_json(receipt), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
