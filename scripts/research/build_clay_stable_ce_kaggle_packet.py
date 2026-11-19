"""Build a private offline Kaggle packet for Clay stable-CE efficacy."""

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

PACKET_SCHEMA = "clay.stable-ce-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.stable-ce-kaggle-dataset.v1"
BUILD_SCHEMA = "clay.stable-ce-kaggle-build.v1"
EXPECTED_BASELINE_MANIFEST_SHA256 = "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97"
EXPECTED_BASELINE_RESULT_SHA256 = "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482"
EXPECTED_DATASET_MANIFEST_SHA256 = "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041"
EXPECTED_SEEDS = (20261134, 20261135, 20261136)
STABLE_CE_BASE_COMMIT = "4acc1e6ff1545662b7f1dc9803adf81e597a06e2"

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


def descriptor(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    return {
        "path": path.relative_to(relative_to).as_posix() if relative_to else path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


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


def copy_exact(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    if sha256_file(source) != sha256_file(destination):
        raise RuntimeError(f"copy differs: {source} -> {destination}")


def git_value(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def git_files(root: Path, prefix: str) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", prefix],
        capture_output=True,
        check=True,
    )
    names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    return tuple((root / name).resolve(strict=True) for name in sorted(names))


def deterministic_zip(source_root: Path, output: Path) -> None:
    files = sorted(path for path in source_root.rglob("*") if path.is_file())
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative = PurePosixPath(path.relative_to(source_root).as_posix())
            info = zipfile.ZipInfo(str(relative), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def _copy_sources(
    *,
    packet_root: Path,
    scbe_root: Path,
    loom_root: Path,
    campaign: Path,
    preregistration: Path,
    baseline_run: Path,
) -> list[dict[str, Any]]:
    copied: list[Path] = []
    scbe_packet = packet_root / "scbe_repo"
    loom_packet = packet_root / "loom_root"
    baseline_packet = packet_root / "baseline_run"

    for source in git_files(scbe_root, "python"):
        target = scbe_packet / source.relative_to(scbe_root)
        copy_exact(source, target)
        copied.append(target)
    for source in (campaign, preregistration):
        if not source.is_relative_to(scbe_root):
            raise ValueError(f"SCBE input escapes repository: {source}")
        target = scbe_packet / source.relative_to(scbe_root)
        if target.exists():
            if sha256_file(source) != sha256_file(target):
                raise RuntimeError(f"duplicate packet source differs: {source}")
        else:
            copy_exact(source, target)
            copied.append(target)
    for relative in LOOM_FILES:
        source = (loom_root / relative).resolve(strict=True)
        target = loom_packet / relative
        copy_exact(source, target)
        copied.append(target)

    baseline_files = [
        baseline_run / "RUN_MANIFEST.json",
        baseline_run / "RESULT.json",
    ]
    for seed in EXPECTED_SEEDS:
        parent = baseline_run / "parents" / f"seed-{seed}"
        baseline_files.extend((parent / "PARENT.pt", parent / "RESULT.json"))
    for source in baseline_files:
        source = source.resolve(strict=True)
        target = baseline_packet / source.relative_to(baseline_run)
        copy_exact(source, target)
        copied.append(target)
    return [descriptor(path, relative_to=packet_root) for path in sorted(copied)]


def build_packet(
    *,
    scbe_root: Path,
    baseline_run: Path,
    source_dir: Path,
    preregistration: Path,
    output_root: Path,
    dataset_id: str,
    kernel_id: str,
    kernel_entry_source: Path,
) -> dict[str, Any]:
    scbe_root = scbe_root.resolve(strict=True)
    baseline_run = baseline_run.resolve(strict=True)
    source_dir = source_dir.resolve(strict=True)
    preregistration = preregistration.resolve(strict=True)
    output_root = output_root.resolve()
    kernel_entry_source = kernel_entry_source.resolve(strict=True)
    if output_root.exists():
        raise FileExistsError(f"output already exists: {output_root}")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(scbe_root),
            "merge-base",
            "--is-ancestor",
            STABLE_CE_BASE_COMMIT,
            "HEAD",
        ],
        check=False,
    )
    if ancestry.returncode != 0:
        raise RuntimeError("stable-CE source commit is not an ancestor")
    baseline_manifest_path = baseline_run / "RUN_MANIFEST.json"
    baseline_result_path = baseline_run / "RESULT.json"
    if sha256_file(baseline_manifest_path) != EXPECTED_BASELINE_MANIFEST_SHA256:
        raise RuntimeError("baseline manifest differs")
    if sha256_file(baseline_result_path) != EXPECTED_BASELINE_RESULT_SHA256:
        raise RuntimeError("baseline result differs")
    baseline_manifest = load_json(baseline_manifest_path)
    if baseline_manifest["config"]["dataset_manifest_sha256"] != EXPECTED_DATASET_MANIFEST_SHA256:
        raise RuntimeError("baseline dataset identity differs")
    if tuple(baseline_manifest["config"]["seeds"]) != EXPECTED_SEEDS:
        raise RuntimeError("baseline seeds differ")
    for key, filename in SOURCE_HASH_FILES.items():
        if sha256_file(source_dir / filename) != baseline_manifest["config"]["source_hashes"][key]:
            raise RuntimeError(f"pinned action source differs: {key}")
    for seed in EXPECTED_SEEDS:
        parent_dir = baseline_run / "parents" / f"seed-{seed}"
        result = load_json(parent_dir / "RESULT.json")
        if sha256_file(parent_dir / "PARENT.pt") != result["parent_sha256"]:
            raise RuntimeError(f"parent hash differs: {seed}")

    campaign = scbe_root / "python" / "scbe" / "clay_stable_ce_efficacy_campaign.py"
    campaign.resolve(strict=True)
    loom_root = source_dir.parents[1]
    output_root.mkdir(parents=True)
    dataset_dir = output_root / "dataset"
    kernel_dir = output_root / "kernel"
    dataset_dir.mkdir()
    kernel_dir.mkdir()

    with tempfile.TemporaryDirectory(prefix="clay-stable-ce-packet-") as temporary:
        packet_root = Path(temporary) / "packet"
        packet_root.mkdir()
        files = _copy_sources(
            packet_root=packet_root,
            scbe_root=scbe_root,
            loom_root=loom_root,
            campaign=campaign,
            preregistration=preregistration,
            baseline_run=baseline_run,
        )
        packet_manifest = {
            "schema": PACKET_SCHEMA,
            "created_at_utc": utc_now(),
            "dataset_id": dataset_id,
            "kernel_id": kernel_id,
            "source_commit": git_value(scbe_root, "rev-parse", "HEAD"),
            "stable_ce_base_commit": STABLE_CE_BASE_COMMIT,
            "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
            "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
            "dataset_manifest_sha256": EXPECTED_DATASET_MANIFEST_SHA256,
            "files": files,
            "paths": {
                "scbe_root": "scbe_repo",
                "source_dir": "loom_root/experiments/clay_action_compiler_20261109",
                "baseline_run": "baseline_run",
                "preregistration": preregistration.relative_to(scbe_root).as_posix(),
                "campaign": campaign.relative_to(scbe_root).as_posix(),
            },
            "remote_config": {
                "seeds": list(EXPECTED_SEEDS),
                "steps": 2000,
                "checkpoint_every": 250,
                "batch_size": 128,
                "threads": 2,
                "minimum_free_gib": 25.0,
                "device": "cpu",
            },
            "authority": {
                "visibility": "PRIVATE",
                "internet": "DISABLED",
                "execution": "NONE",
                "merge": "NONE",
                "promotion": "NONE",
                "tool_dispatch": "DISABLED",
            },
        }
        manifest_path = packet_root / "CLAY_STABLE_CE_KAGGLE_PACKET.json"
        write_json(manifest_path, packet_manifest)
        archive_path = dataset_dir / "clay-stable-ce-efficacy.packet"
        deterministic_zip(packet_root, archive_path)
        dataset_descriptor = {
            "schema": DESCRIPTOR_SCHEMA,
            "dataset_id": dataset_id,
            "archive": descriptor(archive_path),
            "packet_manifest": descriptor(manifest_path),
            "remote_config": packet_manifest["remote_config"],
            "authority": packet_manifest["authority"],
        }
        write_json(dataset_dir / "PACKET_DESCRIPTOR.json", dataset_descriptor)

    write_json(
        dataset_dir / "dataset-metadata.json",
        {
            "title": "Clay Stable CE Efficacy Input 20261119",
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
            "title": "Clay Stable CE Efficacy 20261119",
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
        "source_commit": git_value(scbe_root, "rev-parse", "HEAD"),
        "stable_ce_base_commit": STABLE_CE_BASE_COMMIT,
        "dataset_id": dataset_id,
        "kernel_id": kernel_id,
        "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
        "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
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
            "upload": "SEPARATELY_AUTHORIZED_PRIVATE_ONLY",
            "run": "SEPARATELY_AUTHORIZED_PRIVATE_ONLY",
            "publication": "NONE",
            "promotion": "NONE",
        },
    }
    write_json(output_root / "BUILD_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scbe-root", required=True, type=Path)
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--preregistration", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--dataset-id",
        default="issacizrealdavis/clay-stable-ce-efficacy-input-20261119",
    )
    parser.add_argument(
        "--kernel-id",
        default="issacizrealdavis/clay-stable-ce-efficacy-20261119",
    )
    parser.add_argument(
        "--kernel-entry-source",
        type=Path,
        default=Path(__file__).with_name("run_clay_stable_ce_kaggle.py"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = build_packet(
        scbe_root=args.scbe_root,
        baseline_run=args.baseline_run,
        source_dir=args.source_dir,
        preregistration=args.preregistration,
        output_root=args.output_root,
        dataset_id=args.dataset_id,
        kernel_id=args.kernel_id,
        kernel_entry_source=args.kernel_entry_source,
    )
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
