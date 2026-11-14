"""Build a private, hash-pinned Kaggle packet for Clay compatibility training.

The packet preserves the exact CPU trainer and source files named by an active
run manifest.  It creates a separate reduced-budget cloud lineage; it does not
resume, mutate, promote, merge, or authorize the local campaign.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
from typing import Any, Iterable
import zipfile

PACKET_SCHEMA = "clay.frozen-multiview-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.frozen-multiview-kaggle-dataset.v1"
BUILD_SCHEMA = "clay.frozen-multiview-kaggle-packet-build.v1"
RUN_SCHEMA = "clay.frozen-multiview-adapter-campaign.v1.manifest"

LOOM_FILES = (
    "block_speech.py",
    "clay_bijective_router.py",
    "clay_rubix_surface.py",
    "clay_tool_sandbox.py",
    "clay_tool_sequence_curriculum.py",
    "droid_voice.py",
    "loom_multiplex.py",
    "node_catalog.py",
    "numeric_funnel.py",
    "opcode_cube_multiplex.py",
    "opcode_vectors.py",
    "quine_state_playground.py",
    "radial_trifold.py",
    "tongues/opcode_compose.py",
    "tongues/tongue_opcodes.py",
    "turing_blocks.py",
    "turing_wafer.py",
    "experiments/clay_action_compiler_20261109/action_compiler.py",
    "experiments/clay_action_compiler_20261109/developmental_game_sandbox.py",
    "experiments/clay_action_compiler_20261109/regional_breathing_field.py",
    "experiments/clay_action_compiler_20261109/topology_sector_action_ab.py",
    "experiments/clay_action_compiler_20261109/trit_compiled_action_policy.py",
    "experiments/clay_action_compiler_20261109/trit_token_weight_bank.py",
)

SOURCE_HASH_FILES = {
    "policy": "trit_compiled_action_policy.py",
    "topology": "topology_sector_action_ab.py",
    "sandbox": "developmental_game_sandbox.py",
    "regional": "regional_breathing_field.py",
}


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


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def descriptor(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    return {
        "path": (path.relative_to(relative_to).as_posix() if relative_to else path.name),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected one JSON object: {path}")
    return value


def verify_descriptor(path: Path, expected: dict[str, Any], *, label: str) -> None:
    if path.stat().st_size != int(expected["bytes"]):
        raise RuntimeError(f"{label} byte count differs: {path}")
    if sha256_file(path) != str(expected["sha256"]).casefold():
        raise RuntimeError(f"{label} hash differs: {path}")


def git_value(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_files(root: Path, prefix: str) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", prefix],
        capture_output=True,
        check=True,
    )
    names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    paths = tuple((root / name).resolve(strict=True) for name in sorted(names))
    if not paths:
        raise RuntimeError(f"git tracked no files under {root / prefix}")
    return paths


def copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if sha256_file(source) != sha256_file(destination):
        raise RuntimeError(f"copy differs: {source} -> {destination}")


def deterministic_zip(source_root: Path, output: Path) -> None:
    files = sorted(path for path in source_root.rglob("*") if path.is_file())
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = PurePosixPath(path.relative_to(source_root).as_posix())
            info = zipfile.ZipInfo(str(relative), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def assert_new_directory(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"output already exists: {path}")


def _copy_packet_sources(
    *,
    packet_root: Path,
    scbe_root: Path,
    loom_root: Path,
    runner: Path,
    runner_entry: Path,
    preregistration: Path,
) -> list[dict[str, Any]]:
    copied: list[Path] = []
    scbe_packet = packet_root / "scbe_repo"
    loom_packet = packet_root / "loom_root"

    for source in git_files(scbe_root, "python"):
        target = scbe_packet / source.relative_to(scbe_root)
        copy_exact(source, target)
        copied.append(target)

    explicit_scbe = (runner, runner_entry, preregistration)
    for source in explicit_scbe:
        if not source.is_relative_to(scbe_root):
            raise ValueError(f"SCBE input escapes repository: {source}")
        target = scbe_packet / source.relative_to(scbe_root)
        copy_exact(source, target)
        copied.append(target)

    for relative in LOOM_FILES:
        source = (loom_root / relative).resolve(strict=True)
        if not source.is_relative_to(loom_root):
            raise ValueError(f"Loom input escapes repository: {source}")
        target = loom_packet / relative
        copy_exact(source, target)
        copied.append(target)

    return [descriptor(path, relative_to=packet_root) for path in sorted(copied)]


def build_packet(
    *,
    run_manifest_path: Path,
    output_root: Path,
    dataset_id: str,
    kernel_id: str,
    kernel_entry_source: Path,
) -> dict[str, Any]:
    run_manifest_path = run_manifest_path.resolve(strict=True)
    output_root = output_root.resolve()
    kernel_entry_source = kernel_entry_source.resolve(strict=True)
    assert_new_directory(output_root)

    run_manifest = load_json(run_manifest_path)
    if run_manifest.get("schema") != RUN_SCHEMA:
        raise ValueError("run manifest schema changed")
    config = run_manifest.get("config")
    if not isinstance(config, dict) or config.get("device") != "cpu":
        raise ValueError("compatibility packet requires the pinned CPU trainer")
    if config.get("authority") != "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION_NO_PARTIAL_UNFREEZE":
        raise ValueError("run authority boundary changed")

    runner = Path(str(run_manifest["runner"])).resolve(strict=True)
    data_builder = Path(str(run_manifest["data_builder"])).resolve(strict=True)
    preregistration = Path(str(run_manifest["preregistration"])).resolve(strict=True)
    verify_descriptor(
        runner,
        {"bytes": runner.stat().st_size, "sha256": run_manifest["runner_sha256"]},
        label="runner",
    )
    verify_descriptor(
        data_builder,
        {
            "bytes": data_builder.stat().st_size,
            "sha256": run_manifest["data_builder_sha256"],
        },
        label="data builder",
    )
    verify_descriptor(
        preregistration,
        {
            "bytes": preregistration.stat().st_size,
            "sha256": run_manifest["preregistration_sha256"],
        },
        label="preregistration",
    )

    scbe_root = runner.parents[2]
    runner_entry = (scbe_root / "scripts" / "research" / "run_clay_frozen_multiview_adapter.py").resolve(strict=True)
    source_dir = Path(str(config["source_dir"])).resolve(strict=True)
    loom_root = source_dir.parents[1]
    for key, filename in SOURCE_HASH_FILES.items():
        source = source_dir / filename
        expected = str(config["source_hashes"][key]).casefold()
        if sha256_file(source) != expected:
            raise RuntimeError(f"pinned {key} source differs: {source}")

    output_root.mkdir(parents=True)
    dataset_dir = output_root / "dataset"
    kernel_dir = output_root / "kernel"
    dataset_dir.mkdir()
    kernel_dir.mkdir()

    with tempfile.TemporaryDirectory(prefix="clay-kaggle-packet-") as temporary:
        packet_root = Path(temporary) / "packet"
        packet_root.mkdir()
        files = _copy_packet_sources(
            packet_root=packet_root,
            scbe_root=scbe_root,
            loom_root=loom_root,
            runner=runner,
            runner_entry=runner_entry,
            preregistration=preregistration,
        )
        packet_manifest: dict[str, Any] = {
            "schema": PACKET_SCHEMA,
            "created_at_utc": utc_now(),
            "authority": {
                "execution": "NONE",
                "merge": "NONE",
                "partial_unfreeze": "NONE",
                "promotion": "NONE",
                "tool_dispatch": "DISABLED",
            },
            "claim_boundary": (
                "Reduced-budget Linux/CPU compatibility training only; not a "
                "replication of the full local result and not promotion evidence."
            ),
            "dataset_id": dataset_id,
            "kernel_id": kernel_id,
            "source_run_manifest": descriptor(run_manifest_path),
            "source_run_config_hash": run_manifest["config_hash"],
            "source_scbe_commit": git_value(scbe_root, "rev-parse", "HEAD"),
            "source_loom_commit": git_value(loom_root, "rev-parse", "HEAD"),
            "source_hashes": dict(sorted(config["source_hashes"].items())),
            "files": files,
            "remote_config": {
                "seeds": [20261141, 20261142, 20261143],
                "data_seed": int(config["data_seed"]),
                "rows_per_view": 200,
                "holdout_rows": 300,
                "count_steps": 1000,
                "grow_steps": 1000,
                "checkpoint_every": 250,
                "batch_size": 64,
                "learning_rate": float(config["learning_rate"]),
                "threads": 2,
                "minimum_free_gib": 25.0,
                "device": "cpu",
            },
        }
        packet_manifest_path = packet_root / "CLAY_FROZEN_MULTIVIEW_KAGGLE_PACKET.json"
        write_json(packet_manifest_path, packet_manifest)
        archive_path = dataset_dir / "clay-frozen-multiview-kaggle-packet.zip"
        deterministic_zip(packet_root, archive_path)

        dataset_descriptor = {
            "schema": DESCRIPTOR_SCHEMA,
            "dataset_id": dataset_id,
            "archive": descriptor(archive_path),
            "packet_manifest": descriptor(packet_manifest_path),
            "authority": packet_manifest["authority"],
            "remote_config": packet_manifest["remote_config"],
        }
        write_json(dataset_dir / "PACKET_DESCRIPTOR.json", dataset_descriptor)

    write_json(
        dataset_dir / "dataset-metadata.json",
        {
            "title": "Clay Frozen Multiview Compatibility Input 20261114",
            "id": dataset_id,
            "licenses": [{"name": "other"}],
        },
    )
    copy_exact(kernel_entry_source, kernel_dir / kernel_entry_source.name)
    write_json(
        kernel_dir / "kernel-metadata.json",
        {
            "id": kernel_id,
            "title": "Clay Frozen Multiview Compatibility 20261114",
            "code_file": kernel_entry_source.name,
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": False,
            "enable_internet": False,
            "dataset_sources": [dataset_id],
            "competition_sources": [],
            "kernel_sources": [],
        },
    )

    receipt = {
        "schema": BUILD_SCHEMA,
        "status": "BUILT_PRIVATE_NOT_LAUNCHED",
        "created_at_utc": utc_now(),
        "dataset_id": dataset_id,
        "kernel_id": kernel_id,
        "source_run_manifest": descriptor(run_manifest_path),
        "inventory": {
            "packet_file_count": len(files),
            "dataset": [
                descriptor(path, relative_to=output_root) for path in sorted(dataset_dir.iterdir()) if path.is_file()
            ],
            "kernel": [
                descriptor(path, relative_to=output_root) for path in sorted(kernel_dir.iterdir()) if path.is_file()
            ],
        },
        "authority": {
            "launch": "SEPARATELY_AUTHORIZED_BY_USER",
            "merge": "NONE",
            "partial_unfreeze": "NONE",
            "promotion": "NONE",
            "publication": "PRIVATE_ONLY",
        },
    }
    write_json(output_root / "BUILD_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--dataset-id",
        default="issacizrealdavis/clay-frozen-multiview-compat-input-20261114",
    )
    parser.add_argument(
        "--kernel-id",
        default="issacizrealdavis/clay-frozen-multiview-compat-20261114",
    )
    parser.add_argument(
        "--kernel-entry-source",
        type=Path,
        default=Path(__file__).with_name("run_clay_frozen_multiview_kaggle_compat.py"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = build_packet(
        run_manifest_path=args.run_manifest,
        output_root=args.output_root,
        dataset_id=args.dataset_id,
        kernel_id=args.kernel_id,
        kernel_entry_source=args.kernel_entry_source,
    )
    print(canonical_json(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
