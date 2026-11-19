"""Finalize and independently replay Clay byte thaw in private offline Kaggle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
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

PACKET_SCHEMA = "clay.byte-thaw-finalize-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.byte-thaw-finalize-kaggle-dataset.v1"
RECEIPT_SCHEMA = "clay.byte-thaw-finalize-kaggle-run.v1"
EXPECTED_DATASET_ID = "issacizrealdavis/clay-byte-thaw-finalize-input-20261119"
EXPECTED_CONFIG_HASH = "583f4362158068a056e52ea8894163989fe810378d60b858e60c4e9a70c0e0d6"
EXPECTED_RUNNER_SHA256 = "41ae605fe8a72df2bc24c6a55a43eb30a7a93e324838dd3b731cf1f8b5a4d956"
EXPECTED_REPLAY_SHA256 = "9b3bc0310e1d011d68a87f2bc3101a9bddc0dd7121822e38809f1f7d24585de8"
EXPECTED_SEEDS = (20261134, 20261135, 20261136)
EXPECTED_ARMS = (
    "byte_thaw_multiview",
    "byte_thaw_static",
    "byte_thaw_sample_shuffled",
)
DESCRIPTOR_NAME = "PACKET_DESCRIPTOR.json"
PACKET_MANIFEST_NAME = "CLAY_BYTE_THAW_FINALIZE_PACKET.json"


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
        raise RuntimeError(f"expected one byte-thaw packet, found {len(matches)}")
    return matches[0]


def safe_archive_members(archive: zipfile.ZipFile) -> tuple[zipfile.ZipInfo, ...]:
    members = tuple(archive.infolist())
    for member in members:
        relative = PurePosixPath(member.filename)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"unsafe archive member: {member.filename}")
    return members


def extract_packet(descriptor_path: Path, descriptor_value: dict[str, Any], runtime_root: Path) -> dict[str, Any]:
    if runtime_root.exists():
        raise FileExistsError(f"runtime packet already exists: {runtime_root}")
    archive_descriptor = descriptor_value["archive"]
    archive_path = descriptor_path.parent / archive_descriptor["path"]
    verify_descriptor(archive_path, archive_descriptor, label="packet archive")
    runtime_root.mkdir(parents=True)
    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(runtime_root, members=safe_archive_members(archive))
    manifest_path = runtime_root / PACKET_MANIFEST_NAME
    verify_descriptor(manifest_path, descriptor_value["packet_manifest"], label="packet manifest")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != PACKET_SCHEMA:
        raise RuntimeError("packet schema differs")
    if manifest.get("dataset_id") != EXPECTED_DATASET_ID:
        raise RuntimeError("packet dataset identity differs")
    if manifest["lineage"].get("config_hash") != EXPECTED_CONFIG_HASH:
        raise RuntimeError("packet lineage config differs")
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe packet path: {relative}")
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root):
            raise ValueError(f"packet path escapes root: {relative}")
        verify_descriptor(path, item, label=f"packet file {relative}")
    return manifest


def file_inventory(root: Path) -> list[dict[str, Any]]:
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


def horse_inventory(root: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for seed in EXPECTED_SEEDS:
        for arm in EXPECTED_ARMS:
            key = f"{arm}-seed-{seed}"
            horse = root / "horses" / key
            rows[key] = {
                "model_sha256": sha256_file((horse / "MODEL.pt").resolve(strict=True)),
                "result_sha256": sha256_file((horse / "RESULT.json").resolve(strict=True)),
            }
    return rows


def run_logged(command: list[str], *, cwd: Path, log_path: Path) -> None:
    environment = os.environ.copy()
    environment["SCBE_ROOT"] = str(cwd)
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
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
        raise RuntimeError(f"command exited {return_code}: {command}")


def _provider_campaign(*, packet: dict[str, Any], runtime_root: Path, output_root: Path) -> dict[str, Any]:
    paths = packet["paths"]
    scbe_root = (runtime_root / paths["scbe_root"]).resolve(strict=True)
    source_dir = (runtime_root / paths["source_dir"]).resolve(strict=True)
    exact_baseline = (runtime_root / paths["baseline_run"]).resolve(strict=True)
    lineage_input = (runtime_root / paths["lineage_input"]).resolve(strict=True)
    preregistration = (scbe_root / paths["preregistration"]).resolve(strict=True)
    runner = (scbe_root / "python/scbe/clay_byte_embedding_thaw_campaign.py").resolve(strict=True)
    if sha256_file(runner) != EXPECTED_RUNNER_SHA256:
        raise RuntimeError("provider runner hash differs")
    provider_baseline = output_root / "provider_baseline"
    shutil.copytree(exact_baseline, provider_baseline)
    provider_manifest_path = provider_baseline / "RUN_MANIFEST.json"
    provider_manifest = load_json(provider_manifest_path)
    provider_manifest["config"]["source_dir"] = str(source_dir)
    write_json(provider_manifest_path, provider_manifest)
    provider_campaign = output_root / "provider_campaign"
    for seed in EXPECTED_SEEDS:
        for arm in EXPECTED_ARMS:
            key = f"{arm}-seed-{seed}"
            shutil.copytree(lineage_input / "horses" / key, provider_campaign / "horses" / key)
    before = horse_inventory(provider_campaign)
    config = packet["remote_config"]
    command = [
        sys.executable,
        "-m",
        "python.scbe.clay_byte_embedding_thaw_campaign",
        "--baseline-run",
        str(provider_baseline),
        "--output-dir",
        str(provider_campaign),
        "--preregistration",
        str(preregistration),
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
        output_root / "PROVIDER_LAUNCH.json",
        {"schema": f"{RECEIPT_SCHEMA}.provider-launch", "command": command, "cwd": str(scbe_root)},
    )
    run_logged(command, cwd=scbe_root, log_path=output_root / "PROVIDER_CAMPAIGN.log")
    after = horse_inventory(provider_campaign)
    if after != before:
        raise RuntimeError("provider campaign changed a completed horse artifact")
    checkpoints = sorted(provider_campaign.glob("horses/*/checkpoints/*"))
    if checkpoints:
        raise RuntimeError("provider campaign created optimizer checkpoints")
    provider_result = load_json(provider_campaign / "RESULT.json")
    provider_status = load_json(provider_campaign / "STATUS.json")
    if provider_result.get("status") != "COMPLETE" or provider_status.get("status") != "COMPLETE":
        raise RuntimeError("provider campaign did not finish atomically")
    return {
        "command": command,
        "runner_sha256": sha256_file(runner),
        "horse_artifacts_unchanged": True,
        "optimizer_updates": 0,
        "checkpoint_files_created": 0,
        "result_sha256": sha256_file(provider_campaign / "RESULT.json"),
        "status_sha256": sha256_file(provider_campaign / "STATUS.json"),
        "manifest_sha256": sha256_file(provider_campaign / "RUN_MANIFEST.json"),
        "admitted_free_gib": load_json(provider_campaign / "RUN_MANIFEST.json")["admitted_free_gib"],
    }


def _build_exact_lineage_result(
    *, packet: dict[str, Any], runtime_root: Path, output_root: Path
) -> tuple[Path, dict[str, Any]]:
    paths = packet["paths"]
    scbe_root = (runtime_root / paths["scbe_root"]).resolve(strict=True)
    baseline_run = (runtime_root / paths["baseline_run"]).resolve(strict=True)
    lineage_input = (runtime_root / paths["lineage_input"]).resolve(strict=True)
    lineage_run = output_root / "lineage_campaign"
    shutil.copytree(lineage_input, lineage_run)
    sys.path.insert(0, str(scbe_root))
    from python.scbe import clay_byte_embedding_thaw_campaign as campaign_module

    manifest = load_json(lineage_run / "RUN_MANIFEST.json")
    if campaign_module.file_sha256(Path(campaign_module.__file__).resolve()) != EXPECTED_RUNNER_SHA256:
        raise RuntimeError("loaded aggregation module hash differs")
    config = campaign_module.ThawCampaignConfig(**manifest["config"])
    if campaign_module.stable_hash(asdict(config)) != manifest["config_hash"]:
        raise RuntimeError("reconstructed exact campaign config differs")
    baseline = load_json(baseline_run / "RESULT.json")
    learned = []
    for seed in EXPECTED_SEEDS:
        for arm in EXPECTED_ARMS:
            learned.append(load_json(lineage_run / "horses" / f"{arm}-seed-{seed}" / "RESULT.json"))
    result = campaign_module.aggregate(learned, baseline, config)
    if result.get("config") != manifest["config"]:
        raise RuntimeError("exact aggregate config differs from original manifest")
    campaign_module.atomic_json(lineage_run / "RESULT.json", result)
    campaign_module.atomic_json(
        lineage_run / "STATUS.json",
        {
            "schema": f"{campaign_module.SCHEMA}.status",
            "status": "COMPLETE",
            "result_sha256": campaign_module.file_sha256(lineage_run / "RESULT.json"),
            "updated_at_utc": campaign_module.utc_now(),
        },
    )
    return lineage_run, {
        "config_hash": manifest["config_hash"],
        "manifest_sha256": sha256_file(lineage_run / "RUN_MANIFEST.json"),
        "result_sha256": sha256_file(lineage_run / "RESULT.json"),
        "status_sha256": sha256_file(lineage_run / "STATUS.json"),
        "producer_gate": result["producer_gate"],
        "learned_parameter_count_matched": result["learned_parameter_count_matched"],
        "counting_and_base_parent_preserved": result["counting_and_base_parent_preserved"],
        "thawed_rows_changed": result["thawed_rows_changed"],
        "comparisons": result["comparisons"],
        "paired_comparisons": result["paired_comparisons"],
    }


def _compatibility_link(scbe_root: Path, windows_name: str, target: Path) -> Path:
    alias = scbe_root / windows_name
    if alias.exists() or alias.is_symlink():
        raise FileExistsError(f"compatibility alias already exists: {alias}")
    alias.symlink_to(target, target_is_directory=True)
    return alias


def _independent_replay(
    *, packet: dict[str, Any], runtime_root: Path, output_root: Path, lineage_run: Path
) -> dict[str, Any]:
    if os.name == "nt":
        raise RuntimeError("exact Windows-path replay aliases require the private Linux provider")
    paths = packet["paths"]
    scbe_root = (runtime_root / paths["scbe_root"]).resolve(strict=True)
    baseline_run = (runtime_root / paths["baseline_run"]).resolve(strict=True)
    source_dir = (runtime_root / paths["source_dir"]).resolve(strict=True)
    manifest = load_json(lineage_run / "RUN_MANIFEST.json")
    replay = (scbe_root / "python/scbe/clay_byte_embedding_thaw_replay.py").resolve(strict=True)
    if sha256_file(replay) != EXPECTED_REPLAY_SHA256:
        raise RuntimeError("independent verifier hash differs")
    aliases = [
        _compatibility_link(scbe_root, manifest["config"]["baseline_run"], baseline_run),
        _compatibility_link(scbe_root, manifest["config"]["source_dir"], source_dir),
    ]
    replay_output = lineage_run / "INDEPENDENT_REPLAY.json"
    ledger_output = lineage_run / "INDEPENDENT_REPLAY_LEDGER.jsonl"
    command = [
        sys.executable,
        "-m",
        "python.scbe.clay_byte_embedding_thaw_replay",
        "--run-dir",
        str(lineage_run),
        "--output",
        str(replay_output),
        "--ledger-output",
        str(ledger_output),
        "--threads",
        str(packet["remote_config"]["threads"]),
        "--summary-only",
    ]
    write_json(
        output_root / "REPLAY_LAUNCH.json",
        {
            "schema": f"{RECEIPT_SCHEMA}.replay-launch",
            "command": command,
            "cwd": str(scbe_root),
            "compatibility_aliases": [str(alias) for alias in aliases],
        },
    )
    run_logged(command, cwd=scbe_root, log_path=output_root / "INDEPENDENT_REPLAY.log")
    result = load_json(replay_output)
    if result.get("status") != "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION" or result.get("errors"):
        raise RuntimeError("independent replay did not pass")
    return {
        "command": command,
        "verifier_sha256": sha256_file(replay),
        "status": result["status"],
        "errors": result["errors"],
        "producer_result_sha256": result["producer_result_sha256"],
        "manifest_sha256": result["manifest_sha256"],
        "dataset_manifest_sha256": result["dataset_manifest_sha256"],
        "producer_gate_replayed": result["producer_gate_replayed"],
        "max_metric_delta": result["max_metric_delta"],
        "aggregate_comparison_delta": result["aggregate_comparison_delta"],
        "aggregate_paired_delta": result["aggregate_paired_delta"],
        "model_count": len(result["model_receipts"]),
        "replay_result_sha256": sha256_file(replay_output),
        "ledger_sha256": sha256_file(ledger_output),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    output_root = args.output_root.resolve()
    runtime_root = args.runtime_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    descriptor_path, descriptor_value = discover_packet(input_root)
    packet = extract_packet(descriptor_path, descriptor_value, runtime_root)
    environment = {
        "schema": f"{RECEIPT_SCHEMA}.environment",
        "checked_at_utc": utc_now(),
        "platform": platform.platform(),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "free_bytes": shutil.disk_usage(output_root).free,
        "free_gib": shutil.disk_usage(output_root).free / (1024**3),
        "dataset_descriptor_sha256": sha256_file(descriptor_path),
        "packet_manifest_sha256": sha256_file(runtime_root / PACKET_MANIFEST_NAME),
        "authority": packet["authority"],
    }
    write_json(output_root / "CLOUD_ENVIRONMENT.json", environment)
    if args.verify_only:
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": "PACKET_VERIFIED_ONLY_NO_CAMPAIGN_RUN",
            "completed_at_utc": utc_now(),
            "environment": environment,
            "packet_file_count": len(packet["files"]),
            "authority": packet["authority"],
        }
        write_json(output_root / "CLOUD_RUN_RECEIPT.json", receipt)
        return receipt
    if environment["free_gib"] < float(packet["remote_config"]["minimum_free_gib"]):
        raise RuntimeError("provider storage is below the original 25 GiB gate")
    provider = _provider_campaign(packet=packet, runtime_root=runtime_root, output_root=output_root)
    lineage_run, lineage = _build_exact_lineage_result(
        packet=packet, runtime_root=runtime_root, output_root=output_root
    )
    replay = _independent_replay(
        packet=packet,
        runtime_root=runtime_root,
        output_root=output_root,
        lineage_run=lineage_run,
    )
    if replay["producer_result_sha256"] != lineage["result_sha256"]:
        raise RuntimeError("replay did not bind the recovered lineage result")
    inventory = file_inventory(output_root)
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
        "status": "COMPLETE_EXACT_LINEAGE_REPLAY_PASS_NO_PROMOTION",
        "completed_at_utc": utc_now(),
        "provider_campaign": provider,
        "lineage_campaign": lineage,
        "independent_replay": replay,
        "optimizer_updates": 0,
        "training_occurred": False,
        "recovery_manifest_sha256": sha256_file(recovery_path),
        "authority": packet["authority"],
        "claim_boundary": "Private recovery and independent measurement only; no promotion authority.",
    }
    write_json(output_root / "CLOUD_RUN_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/kaggle/working/clay-byte-thaw-finalize-20261119-v1"),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/kaggle/working/clay-byte-thaw-finalize-runtime"),
    )
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    result = run(parse_args(arguments))
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
