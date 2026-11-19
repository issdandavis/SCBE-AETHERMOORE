"""Build the hash-pinned private Kaggle recovery packet for Clay byte thaw."""

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

import torch

PACKET_SCHEMA = "clay.byte-thaw-finalize-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.byte-thaw-finalize-kaggle-dataset.v1"
BUILD_SCHEMA = "clay.byte-thaw-finalize-kaggle-build.v1"
EXPECTED_SOURCE_COMMIT = "12dde4d50fcbc700bc88bc6706c7473476104691"
EXPECTED_RUNNER_SHA256 = "41ae605fe8a72df2bc24c6a55a43eb30a7a93e324838dd3b731cf1f8b5a4d956"
EXPECTED_REPLAY_SHA256 = "9b3bc0310e1d011d68a87f2bc3101a9bddc0dd7121822e38809f1f7d24585de8"
EXPECTED_THAW_MODULE_SHA256 = "1404b980af543e1a9dcb032f1807dca225eee57e80cb776c34f39831917c0577"
EXPECTED_PREREGISTRATION_SHA256 = "86ae011264baec865f9391aa123a4a5535bf345bb1a512168befd38015ab7f1b"
EXPECTED_BASELINE_MANIFEST_SHA256 = "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97"
EXPECTED_BASELINE_RESULT_SHA256 = "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482"
EXPECTED_DATASET_MANIFEST_SHA256 = "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041"
EXPECTED_CAMPAIGN_CONFIG_SHA256 = "583f4362158068a056e52ea8894163989fe810378d60b858e60c4e9a70c0e0d6"
EXPECTED_SEEDS = (20261134, 20261135, 20261136)
EXPECTED_ARMS = (
    "byte_thaw_multiview",
    "byte_thaw_static",
    "byte_thaw_sample_shuffled",
)
PREREGISTRATION_RELATIVE = Path("docs/research/CLAY_BYTE_EMBEDDING_THAW_PREREGISTRATION_20261115.md")
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
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def descriptor(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(relative_to).as_posix() if relative_to else path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if sha256_file(source) != sha256_file(destination):
        raise RuntimeError(f"copy differs: {source} -> {destination}")


def tracked_files(root: Path, prefix: str) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", prefix],
        capture_output=True,
        check=True,
    )
    names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    return tuple((root / name).resolve(strict=True) for name in sorted(names))


def deterministic_zip(source_root: Path, output: Path) -> None:
    files = sorted(path for path in source_root.rglob("*") if path.is_file())
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = PurePosixPath(path.relative_to(source_root).as_posix())
            info = zipfile.ZipInfo(str(relative), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def _verify_lineage(
    *, campaign_run: Path, baseline_run: Path, source_dir: Path, preregistration: Path, scbe_root: Path
) -> dict[str, Any]:
    manifest_path = campaign_run / "RUN_MANIFEST.json"
    manifest = load_json(manifest_path)
    baseline_manifest_path = baseline_run / "RUN_MANIFEST.json"
    baseline_result_path = baseline_run / "RESULT.json"
    expected = {
        baseline_manifest_path: EXPECTED_BASELINE_MANIFEST_SHA256,
        baseline_result_path: EXPECTED_BASELINE_RESULT_SHA256,
        preregistration: EXPECTED_PREREGISTRATION_SHA256,
        scbe_root / "python/scbe/clay_byte_embedding_thaw_campaign.py": EXPECTED_RUNNER_SHA256,
        scbe_root / "python/scbe/clay_byte_embedding_thaw_replay.py": EXPECTED_REPLAY_SHA256,
        scbe_root / "python/scbe/clay_byte_embedding_thaw.py": EXPECTED_THAW_MODULE_SHA256,
    }
    for path, digest in expected.items():
        if sha256_file(path.resolve(strict=True)) != digest:
            raise RuntimeError(f"pinned input differs: {path}")
    if sha256_file(manifest_path) != sha256_file(campaign_run / "RUN_MANIFEST.json"):
        raise RuntimeError("campaign manifest read was unstable")
    if manifest.get("config_hash") != EXPECTED_CAMPAIGN_CONFIG_SHA256:
        raise RuntimeError("campaign config hash differs")
    if manifest["config"].get("dataset_manifest_sha256") != EXPECTED_DATASET_MANIFEST_SHA256:
        raise RuntimeError("campaign dataset identity differs")
    if tuple(manifest["config"].get("seeds", ())) != EXPECTED_SEEDS:
        raise RuntimeError("campaign seed contract differs")
    if tuple(manifest["config"].get("arms", ())) != EXPECTED_ARMS:
        raise RuntimeError("campaign arm contract differs")
    for key, filename in SOURCE_HASH_FILES.items():
        if sha256_file(source_dir / filename) != manifest["config"]["source_hashes"][key]:
            raise RuntimeError(f"pinned Clay source differs: {key}")
    horse_rows = []
    for seed in EXPECTED_SEEDS:
        parent = baseline_run / "parents" / f"seed-{seed}"
        parent_result = load_json(parent / "RESULT.json")
        if sha256_file(parent / "PARENT.pt") != parent_result["parent_sha256"]:
            raise RuntimeError(f"baseline parent hash differs: {seed}")
        for arm in EXPECTED_ARMS:
            horse = campaign_run / "horses" / f"{arm}-seed-{seed}"
            result = load_json(horse / "RESULT.json")
            if int(result.get("steps", -1)) != 18_000 or result.get("status") != "COMPLETE":
                raise RuntimeError(f"horse is not terminal: {arm} seed {seed}")
            model_path = horse / "MODEL.pt"
            model_hash = sha256_file(model_path)
            if model_hash != result.get("model_sha256"):
                raise RuntimeError(f"horse model hash differs: {arm} seed {seed}")
            payload = torch.load(model_path, map_location="cpu", weights_only=False)
            identity = {
                "schema": "clay.byte-embedding-thaw-campaign.v1.horse",
                "arm": arm,
                "seed": seed,
                "config_hash": EXPECTED_CAMPAIGN_CONFIG_SHA256,
            }
            if any(payload.get(key) != value for key, value in identity.items()):
                raise RuntimeError(f"horse payload identity differs: {arm} seed {seed}")
            horse_rows.append({"arm": arm, "seed": seed, "model_sha256": model_hash})
    return {"manifest_sha256": sha256_file(manifest_path), "horses": horse_rows}


def _copy_packet_files(
    *,
    packet_root: Path,
    scbe_root: Path,
    campaign_run: Path,
    baseline_run: Path,
    source_dir: Path,
    preregistration: Path,
) -> list[dict[str, Any]]:
    copied: list[Path] = []
    scbe_packet = packet_root / "scbe_repo"
    for source in tracked_files(scbe_root, "python"):
        target = scbe_packet / source.relative_to(scbe_root)
        copy_exact(source, target)
        copied.append(target)
    prereg_target = scbe_packet / PREREGISTRATION_RELATIVE
    copy_exact(preregistration, prereg_target)
    copied.append(prereg_target)
    loom_root = source_dir.parents[1]
    for relative in LOOM_FILES:
        source = (loom_root / relative).resolve(strict=True)
        target = packet_root / "loom_root" / relative
        copy_exact(source, target)
        copied.append(target)
    baseline_files = [
        "RUN_MANIFEST.json",
        "RESULT.json",
        "INDEPENDENT_REPLAY.json",
        "INDEPENDENT_REPLAY_WATCH_STATUS.json",
    ]
    for relative in baseline_files:
        source = (baseline_run / relative).resolve(strict=True)
        target = packet_root / "baseline_run" / relative
        copy_exact(source, target)
        copied.append(target)
    for seed in EXPECTED_SEEDS:
        for relative in (f"parents/seed-{seed}/PARENT.pt", f"parents/seed-{seed}/RESULT.json"):
            source = (baseline_run / relative).resolve(strict=True)
            target = packet_root / "baseline_run" / relative
            copy_exact(source, target)
            copied.append(target)
        for relative in (
            f"horses/frozen_adapter_multiview-seed-{seed}/MODEL.pt",
            f"horses/frozen_adapter_multiview-seed-{seed}/RESULT.json",
        ):
            source = (baseline_run / relative).resolve(strict=True)
            target = packet_root / "baseline_run" / relative
            copy_exact(source, target)
            copied.append(target)
    original_manifest = campaign_run / "RUN_MANIFEST.json"
    target_manifest = packet_root / "lineage_input" / "RUN_MANIFEST.json"
    copy_exact(original_manifest, target_manifest)
    copied.append(target_manifest)
    for seed in EXPECTED_SEEDS:
        for arm in EXPECTED_ARMS:
            for filename in ("MODEL.pt", "RESULT.json"):
                relative = Path("horses") / f"{arm}-seed-{seed}" / filename
                source = (campaign_run / relative).resolve(strict=True)
                target = packet_root / "lineage_input" / relative
                copy_exact(source, target)
                copied.append(target)
    return [descriptor(path, relative_to=packet_root) for path in sorted(copied)]


def build_packet(
    *,
    scbe_root: Path,
    campaign_run: Path,
    baseline_run: Path,
    source_dir: Path,
    preregistration: Path,
    output_root: Path,
    dataset_id: str,
    kernel_id: str,
    kernel_entry_source: Path,
) -> dict[str, Any]:
    scbe_root = scbe_root.resolve(strict=True)
    campaign_run = campaign_run.resolve(strict=True)
    baseline_run = baseline_run.resolve(strict=True)
    source_dir = source_dir.resolve(strict=True)
    preregistration = preregistration.resolve(strict=True)
    kernel_entry_source = kernel_entry_source.resolve(strict=True)
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"output already exists: {output_root}")
    if (
        subprocess.run(
            ["git", "-C", str(scbe_root), "merge-base", "--is-ancestor", EXPECTED_SOURCE_COMMIT, "HEAD"],
            check=False,
        ).returncode
        != 0
    ):
        raise RuntimeError("pinned source commit is not an ancestor")
    lineage = _verify_lineage(
        campaign_run=campaign_run,
        baseline_run=baseline_run,
        source_dir=source_dir,
        preregistration=preregistration,
        scbe_root=scbe_root,
    )
    output_root.mkdir(parents=True)
    dataset_dir = output_root / "dataset"
    kernel_dir = output_root / "kernel"
    dataset_dir.mkdir()
    kernel_dir.mkdir()
    with tempfile.TemporaryDirectory(prefix="clay-byte-thaw-finalize-") as temporary:
        packet_root = Path(temporary) / "packet"
        packet_root.mkdir()
        files = _copy_packet_files(
            packet_root=packet_root,
            scbe_root=scbe_root,
            campaign_run=campaign_run,
            baseline_run=baseline_run,
            source_dir=source_dir,
            preregistration=preregistration,
        )
        packet_manifest = {
            "schema": PACKET_SCHEMA,
            "created_at_utc": utc_now(),
            "dataset_id": dataset_id,
            "kernel_id": kernel_id,
            "source_commit": subprocess.run(
                ["git", "-C", str(scbe_root), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip(),
            "files": files,
            "lineage": {
                **lineage,
                "config_hash": EXPECTED_CAMPAIGN_CONFIG_SHA256,
                "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
                "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
                "dataset_manifest_sha256": EXPECTED_DATASET_MANIFEST_SHA256,
                "runner_sha256": EXPECTED_RUNNER_SHA256,
                "replay_sha256": EXPECTED_REPLAY_SHA256,
                "thaw_module_sha256": EXPECTED_THAW_MODULE_SHA256,
                "preregistration_sha256": EXPECTED_PREREGISTRATION_SHA256,
            },
            "paths": {
                "scbe_root": "scbe_repo",
                "source_dir": "loom_root/experiments/clay_action_compiler_20261109",
                "baseline_run": "baseline_run",
                "lineage_input": "lineage_input",
                "preregistration": PREREGISTRATION_RELATIVE.as_posix(),
            },
            "remote_config": {
                "grow_steps": 18_000,
                "checkpoint_every": 500,
                "batch_size": 128,
                "learning_rate": 0.002,
                "threads": 2,
                "minimum_free_gib": 25.0,
                "device": "cpu",
                "expected_optimizer_updates": 0,
            },
            "authority": {
                "visibility": "PRIVATE",
                "internet": "DISABLED",
                "training": "REUSE_ONLY_NO_OPTIMIZER_UPDATES",
                "execution": "NONE",
                "merge": "NONE",
                "promotion": "NONE",
                "publication": "NONE",
            },
        }
        packet_manifest_path = packet_root / "CLAY_BYTE_THAW_FINALIZE_PACKET.json"
        write_json(packet_manifest_path, packet_manifest)
        archive_path = dataset_dir / "clay-byte-thaw-finalize.packet"
        deterministic_zip(packet_root, archive_path)
        write_json(
            dataset_dir / "PACKET_DESCRIPTOR.json",
            {
                "schema": DESCRIPTOR_SCHEMA,
                "dataset_id": dataset_id,
                "archive": descriptor(archive_path),
                "packet_manifest": descriptor(packet_manifest_path),
                "authority": packet_manifest["authority"],
            },
        )
    write_json(
        dataset_dir / "dataset-metadata.json",
        {
            "title": "Clay Byte Thaw Finalize Input 20261119",
            "id": dataset_id,
            "licenses": [{"name": "other"}],
            "isPrivate": True,
        },
    )
    copy_exact(kernel_entry_source, kernel_dir / kernel_entry_source.name)
    write_json(
        kernel_dir / "kernel-metadata.json",
        {
            "id": kernel_id,
            "title": "Clay Byte Thaw Finalize 20261119",
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
        "status": "BUILT_PRIVATE_OFFLINE_NOT_UPLOADED_NOT_RUN",
        "created_at_utc": utc_now(),
        "dataset_id": dataset_id,
        "kernel_id": kernel_id,
        "lineage": lineage,
        "inventory": {
            "packet_file_count": len(files),
            "dataset": [descriptor(path, relative_to=output_root) for path in sorted(dataset_dir.iterdir())],
            "kernel": [descriptor(path, relative_to=output_root) for path in sorted(kernel_dir.iterdir())],
        },
        "authority": packet_manifest["authority"],
    }
    write_json(output_root / "BUILD_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scbe-root", required=True, type=Path)
    parser.add_argument("--campaign-run", required=True, type=Path)
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--preregistration", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--dataset-id", default="issacizrealdavis/clay-byte-thaw-finalize-input-20261119")
    parser.add_argument("--kernel-id", default="issacizrealdavis/clay-byte-thaw-finalize-20261119")
    parser.add_argument(
        "--kernel-entry-source",
        type=Path,
        default=Path(__file__).with_name("run_clay_byte_thaw_finalize_kaggle.py"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    result = build_packet(
        scbe_root=args.scbe_root,
        campaign_run=args.campaign_run,
        baseline_run=args.baseline_run,
        source_dir=args.source_dir,
        preregistration=args.preregistration,
        output_root=args.output_root,
        dataset_id=args.dataset_id,
        kernel_id=args.kernel_id,
        kernel_entry_source=args.kernel_entry_source,
    )
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
