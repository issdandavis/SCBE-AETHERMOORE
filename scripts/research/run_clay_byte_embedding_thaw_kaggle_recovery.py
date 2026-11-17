"""Aggregate and independently replay a sealed byte-thaw packet on CPU.

The entry point has no training surface.  It verifies every packet byte,
materializes a writable view of the immutable run, aggregates terminal horse
results, and optionally reopens the sealed models for independent inference.
Absolute Windows authorities remain unchanged in the original manifests; on
POSIX a deterministic alias layer resolves them to packet-relative inputs.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import sys
from typing import Any, Iterable, Iterator, Mapping
import zipfile

import numpy as np
import torch

PACKET_SCHEMA = "clay.byte-embedding-thaw-kaggle-recovery-packet.v1"
DESCRIPTOR_SCHEMA = "clay.byte-embedding-thaw-kaggle-recovery-dataset.v1"
RECEIPT_SCHEMA = "clay.byte-embedding-thaw-kaggle-recovery.v1"
DEFAULT_DATASET_ID = "issacizrealdavis/clay-byte-thaw-aggregation-replay-20261117"
DESCRIPTOR_NAME = "PACKET_DESCRIPTOR.json"
MANIFEST_NAME = "PACKET_MANIFEST.json"


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


def discover_packet(input_root: Path, dataset_id: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(input_root.rglob(DESCRIPTOR_NAME)):
        value = load_json(path)
        if value.get("schema") == DESCRIPTOR_SCHEMA and value.get("dataset_id") == dataset_id:
            matches.append((path, value))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {dataset_id} recovery packet, found {len(matches)}")
    return matches[0]


def _safe_members(archive: zipfile.ZipFile) -> tuple[zipfile.ZipInfo, ...]:
    members = tuple(archive.infolist())
    for member in members:
        relative = PurePosixPath(member.filename)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"unsafe archive member: {member.filename}")
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
    archive_path = descriptor_path.parent / str(archive_record["path"])
    verify_descriptor(archive_path, archive_record, label="recovery archive")
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
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("packet manifest has no files")
    seen: set[str] = set()
    total = 0
    for item in files:
        if not isinstance(item, Mapping):
            raise TypeError("packet file descriptor must be an object")
        relative = PurePosixPath(str(item["path"]))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError(f"unsafe packet path: {relative}")
        if str(relative) in seen:
            raise RuntimeError(f"duplicate packet path: {relative}")
        seen.add(str(relative))
        path = (runtime_root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(runtime_root.resolve()):
            raise ValueError(f"packet path escapes root: {relative}")
        verify_descriptor(path, item, label=f"packet file {relative}")
        total += int(item["bytes"])
    if len(files) != int(manifest["file_count"]) or total != int(manifest["payload_bytes"]):
        raise RuntimeError("packet file count or payload byte total differs")
    return manifest_path, manifest


def _copy_or_link(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        if os.name != "nt":
            try:
                destination.symlink_to(source)
                return "symlink"
            except OSError:
                pass
        shutil.copyfile(source, destination)
        if sha256_file(source) != sha256_file(destination):
            raise RuntimeError(f"staged copy differs: {source} -> {destination}")
        return "copy"


def materialize_run_view(source: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        raise FileExistsError(f"staged run already exists: {destination}")
    counts = {"hardlink": 0, "symlink": 0, "copy": 0}
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        method = _copy_or_link(path, destination / path.relative_to(source))
        counts[method] += 1
    return {
        "source": str(source),
        "destination": str(destination),
        "files": sum(counts.values()),
        **counts,
    }


def _packet_records_by_prefix(manifest: Mapping[str, Any], prefix: str) -> dict[str, Mapping[str, Any]]:
    normalized = prefix.rstrip("/") + "/"
    return {
        str(item["path"])[len(normalized) :]: item
        for item in manifest["files"]
        if str(item["path"]).startswith(normalized)
    }


def _verify_native_mapping(
    packet_root: Path,
    manifest: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> None:
    native = Path(str(mapping["windows_path"]))
    if not native.exists():
        raise FileNotFoundError(
            f"native Windows authority is unavailable; use the POSIX/Kaggle alias runtime: {native}"
        )
    packet_prefix = str(mapping["packet_path"])
    records = _packet_records_by_prefix(manifest, packet_prefix)
    if not records:
        raise RuntimeError(f"path map has no packet records: {packet_prefix}")
    for relative, expected in records.items():
        native_file = native / Path(*PurePosixPath(relative).parts)
        verify_descriptor(native_file, expected, label=f"native mapped authority {relative}")
        packet_file = packet_root / Path(*PurePosixPath(str(expected["path"])).parts)
        verify_descriptor(packet_file, expected, label=f"packet mapped authority {relative}")


@contextmanager
def mapped_authority_context(
    packet_root: Path,
    manifest: Mapping[str, Any],
    alias_root: Path,
) -> Iterator[dict[str, Any]]:
    path_map = load_json(packet_root / "PATH_MAP.json")
    mappings = [
        item
        for item in path_map.get("mappings", [])
        if isinstance(item, Mapping) and item.get("runtime_use") == "posix_alias"
    ]
    old_cwd = Path.cwd()
    if os.name == "nt":
        native_mappings = [
            item
            for item in path_map.get("mappings", [])
            if isinstance(item, Mapping) and item.get("runtime_use") in {"posix_alias", "native_verify"}
        ]
        for mapping in native_mappings:
            _verify_native_mapping(packet_root, manifest, mapping)
        receipt = {"mode": "verified_native_windows_authorities", "aliases": []}
        try:
            yield receipt
        finally:
            os.chdir(old_cwd)
        return

    alias_root.mkdir(parents=True, exist_ok=False)
    aliases: list[dict[str, str]] = []
    for mapping in mappings:
        name = str(mapping["windows_path"])
        if "/" in name:
            raise ValueError(f"POSIX alias contains a path separator: {name}")
        target = (packet_root / Path(*PurePosixPath(str(mapping["packet_path"])).parts)).resolve(strict=True)
        alias = alias_root / name
        alias.symlink_to(target, target_is_directory=True)
        aliases.append({"logical_windows_path": name, "target": str(target)})
    os.chdir(alias_root)
    try:
        yield {"mode": "posix_exact_string_aliases", "aliases": aliases}
    finally:
        os.chdir(old_cwd)


def _import_runtime(packet_root: Path) -> tuple[Any, Any, Any]:
    scbe_root = (packet_root / "runtime" / "scbe_repo").resolve(strict=True)
    os.environ["SCBE_ROOT"] = str(scbe_root)
    if str(scbe_root) not in sys.path:
        sys.path.insert(0, str(scbe_root))
    from python.scbe import clay_byte_embedding_thaw_campaign as campaign
    from python.scbe import clay_byte_embedding_thaw_replay as replay
    from python.scbe.clay_frozen_multiview_adapter import atomic_json

    return campaign, replay, atomic_json


def aggregate_terminal_results(packet_root: Path, staged_run: Path) -> dict[str, Any]:
    campaign_module, _, atomic_json = _import_runtime(packet_root)
    manifest = load_json(staged_run / "RUN_MANIFEST.json")
    config = dict(manifest["config"])
    config["seeds"] = tuple(int(seed) for seed in config["seeds"])
    config["arms"] = tuple(str(arm) for arm in config["arms"])
    config["source_hashes"] = dict(config["source_hashes"])
    campaign_config = campaign_module.ThawCampaignConfig(**config)
    learned = []
    for seed in campaign_config.seeds:
        for arm in campaign_config.arms:
            learned.append(load_json(staged_run / "horses" / f"{arm}-seed-{seed}" / "RESULT.json"))
    if len(learned) != 9 or any(row.get("status") != "COMPLETE" for row in learned):
        raise RuntimeError("aggregation requires nine complete terminal horse results")
    baseline = load_json(packet_root / "payload" / "baseline" / "RESULT.json")
    result = campaign_module.aggregate(learned, baseline, campaign_config)
    atomic_json(staged_run / "RESULT.json", result)
    serialized = load_json(staged_run / "RESULT.json")
    if serialized.get("config") != manifest.get("config"):
        raise RuntimeError("aggregation rewrote the exact run config")
    return serialized


def _no_intervention_semantic_match(packet_root: Path, seed: int) -> bool:
    baseline_root = packet_root / "payload" / "baseline"
    baseline = load_json(baseline_root / "RESULT.json")
    aggregate_rows = [row for row in baseline["per_arm"]["no_intervention_adapter"] if int(row["seed"]) == seed]
    if len(aggregate_rows) != 1:
        return False
    aggregate = aggregate_rows[0]
    parent = load_json(baseline_root / "parents" / f"seed-{seed}" / "RESULT.json")
    return (
        int(parent["seed"]) == int(aggregate["seed"])
        and parent["metrics"] == aggregate["metrics"]
        and parent["predictions"] == aggregate["predictions"]
        and float(parent["counting_accuracy"])
        == float(aggregate["counting_accuracy"])
        == float(aggregate["parent_counting_accuracy"])
        and int(aggregate["trainable_parameters"]) == 0
    )


def qualify_recovery_replay(
    packet_root: Path,
    raw_replay: Mapping[str, Any],
    *,
    tolerance: float,
) -> dict[str, Any]:
    """Resolve two known metadata mismatches without waiving inference errors."""

    remaining = [str(error) for error in raw_replay.get("errors", [])]
    adjustments: list[dict[str, Any]] = []
    stale_error = "baseline independent replay verifier binding is stale"
    if stale_error in remaining:
        baseline_replay = load_json(packet_root / "payload" / "baseline" / "INDEPENDENT_REPLAY.json")
        historical = packet_root / "authorities" / "baseline_verifier" / "clay_frozen_multiview_replay.py"
        expected = str(baseline_replay["independent_dataset_builder_sha256"])
        actual = sha256_file(historical)
        if actual == expected:
            remaining.remove(stale_error)
            adjustments.append(
                {
                    "kind": "historical_baseline_verifier_binding",
                    "raw_error": stale_error,
                    "historical_verifier_sha256": actual,
                    "reason": (
                        "The current verifier contains the later exact-Fraction "
                        "overflow fix; the packet retains the exact verifier bytes "
                        "bound by the already-closed baseline replay."
                    ),
                }
            )

    for seed in (20261134, 20261135, 20261136):
        error = f"no_intervention_adapter seed {seed}: terminal baseline result differs"
        if error in remaining and _no_intervention_semantic_match(packet_root, seed):
            remaining.remove(error)
            adjustments.append(
                {
                    "kind": "no_intervention_semantic_projection",
                    "seed": seed,
                    "raw_error": error,
                    "reason": (
                        "The parent RESULT and imported aggregate row use different "
                        "schemas, but seed, predictions, metrics, counting accuracy, "
                        "and explicit zero-new-parameter semantics match exactly."
                    ),
                }
            )

    receipts = raw_replay.get("model_receipts")
    if not isinstance(receipts, list):
        receipts = []
    mismatch_total = sum(int(row.get("prediction_mismatches", -1)) for row in receipts if isinstance(row, Mapping))
    inference_pass = (
        len(receipts) == 15
        and mismatch_total == 0
        and float(raw_replay.get("max_metric_delta", float("inf"))) <= tolerance
        and float(raw_replay.get("aggregate_comparison_delta", float("inf"))) <= tolerance
        and float(raw_replay.get("aggregate_paired_delta", float("inf"))) <= tolerance
        and int(raw_replay.get("ledger", {}).get("rows", -1)) == 22_500
    )
    result = dict(raw_replay)
    result["raw_replay_status"] = raw_replay.get("status")
    result["raw_replay_errors"] = list(raw_replay.get("errors", []))
    result["raw_replay_sha256"] = stable_hash(raw_replay)
    result["recovery_adjustments"] = adjustments
    result["prediction_mismatch_total"] = mismatch_total
    result["errors"] = remaining
    result["status"] = (
        "PASS_RECOVERY_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION"
        if inference_pass and not remaining
        else "FAIL_RECOVERY_INDEPENDENT_INFERENCE_REPLAY"
    )
    result["recovery_replay_sha256"] = stable_hash(result)
    return result


def _receipt_body_hash(receipt: Mapping[str, Any]) -> str:
    body = dict(receipt)
    body.pop("receipt_body_sha256", None)
    return stable_hash(body)


def run_recovery(args: argparse.Namespace) -> dict[str, Any]:
    input_root = args.input_root.resolve(strict=True)
    output_root = args.output_root.resolve()
    runtime_root = args.runtime_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"output is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    descriptor_path, packet_descriptor = discover_packet(input_root, args.dataset_id)
    manifest_path, manifest = extract_and_verify_packet(descriptor_path, packet_descriptor, runtime_root)
    run_manifest = load_json(runtime_root / "payload" / "run" / "RUN_MANIFEST.json")
    if load_json(runtime_root / "authorities" / "RUN_CONFIG.json") != run_manifest["config"]:
        raise RuntimeError("extracted run config authority differs")
    if load_json(runtime_root / "authorities" / "DATASET_MANIFEST.json") != run_manifest["dataset"]:
        raise RuntimeError("extracted dataset authority differs")
    if sha256_file(runtime_root / "PATH_MAP.json") != manifest["path_map_sha256"]:
        raise RuntimeError("path map hash differs")

    staged_run = output_root / "run"
    view_receipt = materialize_run_view(runtime_root / "payload" / "run", staged_run)
    aggregation = aggregate_terminal_results(runtime_root, staged_run)
    aggregation_path = staged_run / "RESULT.json"
    if args.mode == "aggregate":
        replay_result: dict[str, Any] | None = None
    else:
        _, replay_module, atomic_json = _import_runtime(runtime_root)
        with mapped_authority_context(runtime_root, manifest, output_root / "path_aliases") as alias_receipt:
            replay_result = replay_module.verify_run(
                staged_run,
                tolerance=args.tolerance,
                ledger_output=output_root / "INDEPENDENT_REPLAY_LEDGER.jsonl",
            )
            replay_result = qualify_recovery_replay(
                runtime_root,
                replay_result,
                tolerance=args.tolerance,
            )
        atomic_json(output_root / "INDEPENDENT_REPLAY.json", replay_result)
        if replay_result.get("status") != "PASS_RECOVERY_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION":
            failure = {
                "schema": f"{RECEIPT_SCHEMA}.failure",
                "status": "FAIL_CLOSED",
                "errors": replay_result.get("errors", []),
                "packet_id": manifest["packet_id"],
                "authority": manifest["authority"],
            }
            write_json(output_root / "RECOVERY_FAILURE.json", failure)
            raise RuntimeError("independent inference replay failed closed")

    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "PASS_AGGREGATION_ONLY_NO_TRAINING"
            if replay_result is None
            else "PASS_AGGREGATION_AND_INDEPENDENT_REPLAY_NO_TRAINING"
        ),
        "completed_at_utc": utc_now(),
        "packet_id": manifest["packet_id"],
        "packet_manifest": str(manifest_path),
        "packet_manifest_sha256": sha256_file(manifest_path),
        "dataset_descriptor_sha256": sha256_file(descriptor_path),
        "platform": platform.platform(),
        "python": sys.version,
        "numpy": np.__version__,
        "torch": torch.__version__,
        "threads": args.threads,
        "run_view": view_receipt,
        "aggregation_result": str(aggregation_path),
        "aggregation_result_sha256": sha256_file(aggregation_path),
        "producer_gate": aggregation.get("producer_gate"),
        "independent_replay": (
            None
            if replay_result is None
            else {
                "path": str(output_root / "INDEPENDENT_REPLAY.json"),
                "sha256": sha256_file(output_root / "INDEPENDENT_REPLAY.json"),
                "status": replay_result["status"],
                "errors": replay_result["errors"],
                "ledger_sha256": replay_result["ledger"]["sha256"],
                "prediction_mismatch_total": sum(
                    int(row["prediction_mismatches"]) for row in replay_result["model_receipts"]
                ),
                "alias_resolution": alias_receipt,
            }
        ),
        "authority": {
            "training": "NONE",
            "weight_mutation": "NONE",
            "merge": "NONE",
            "promotion": "NONE",
            "upload": "NONE",
        },
        "claim_boundary": (
            "Terminal aggregation and independent inference replay only.  All "
            "weights were opened read-only and no training path exists here."
        ),
    }
    receipt["receipt_body_sha256"] = _receipt_body_hash(receipt)
    write_json(output_root / "RECOVERY_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=Path("/kaggle/input"))
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/kaggle/working/clay-byte-thaw-aggregation-replay"),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/kaggle/working/clay-byte-thaw-recovery-packet"),
    )
    parser.add_argument("--mode", choices=("aggregate", "all"), default="all")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--tolerance", type=float, default=1e-12)
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    if args.threads < 1:
        raise ValueError("threads must be positive")
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    receipt = run_recovery(args)
    print(canonical_json(receipt), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
