"""Build a private offline Kaggle packet for Clay input-access efficacy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Iterable

from scripts.research.build_clay_stable_ce_kaggle_packet import (
    LOOM_FILES,
    SOURCE_HASH_FILES,
    copy_exact,
    descriptor,
    deterministic_zip,
    git_files,
    git_value,
    load_json,
    sha256_file as file_sha256,
    write_json,
)

PACKET_SCHEMA = "clay.input-access-kaggle-packet.v1"
DESCRIPTOR_SCHEMA = "clay.input-access-kaggle-dataset.v1"
BUILD_SCHEMA = "clay.input-access-kaggle-build.v1"
EXPECTED_BASELINE_MANIFEST_SHA256 = "7f2516af8ae5a122f357565afad60ab412fdf54e76a3018cd8f1ddbfdb702a97"
EXPECTED_BASELINE_RESULT_SHA256 = "c5261ada862a2851db0b1dd7e53835b5ddef22299660921527a249a866361482"
EXPECTED_DATASET_MANIFEST_SHA256 = "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041"
EXPECTED_SEEDS = (20261134, 20261135, 20261136)
EXPECTED_PREREGISTRATION_SHA256 = "f5613e79353dfcdaddb2935e8b087d66f50c025cb31ca75824e17e1bca0f4080"
EXPECTED_PARENT_ROWS = {
    20261134: ("e719ca2398f0a96e4c80d2119897ad36202fb34bd8fbe37190655d581411b910", 0.7037037037037037),
    20261135: ("bb4d912d413dd76174986a89b24f713268e90138808b69107aac01736c218438", 0.37037037037037035),
    20261136: ("820f0ed122b27261eb91391d4b69efe987f2e8a8e5f79b27c9e2a7f431267929", 0.4074074074074074),
}
INPUT_ACCESS_PARENT_COMMIT = "fdb2f77ab16082f1ba80406c23139d7afd30905d"
TRUST_PLACEHOLDERS = {
    "descriptor_sha256": "__BUILD_PINNED_DESCRIPTOR_SHA256__",
    "archive_sha256": "__BUILD_PINNED_ARCHIVE_SHA256__",
    "packet_manifest_sha256": "__BUILD_PINNED_PACKET_MANIFEST_SHA256__",
    "preregistration_sha256": "__BUILD_PINNED_PREREGISTRATION_SHA256__",
    "campaign_sha256": "__BUILD_PINNED_CAMPAIGN_SHA256__",
    "prior_recovery_sha256": "__BUILD_PINNED_PRIOR_RECOVERY_SHA256__",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def render_kernel_entry(
    source: Path,
    destination: Path,
    trust_anchors: dict[str, str],
) -> None:
    text = source.read_text(encoding="utf-8")
    for key, placeholder in TRUST_PLACEHOLDERS.items():
        if text.count(placeholder) != 1:
            raise RuntimeError(f"kernel trust placeholder count differs: {key}")
        text = text.replace(placeholder, trust_anchors[key])
    destination.write_text(text, encoding="utf-8", newline="\n")


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
            if file_sha256(source) != file_sha256(target):
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
    prior_recovery_manifest: Path | None = None,
    prior_dataset_id: str | None = None,
) -> dict[str, Any]:
    scbe_root = scbe_root.resolve(strict=True)
    baseline_run = baseline_run.resolve(strict=True)
    source_dir = source_dir.resolve(strict=True)
    preregistration = preregistration.resolve(strict=True)
    output_root = output_root.resolve()
    kernel_entry_source = kernel_entry_source.resolve(strict=True)
    if (prior_recovery_manifest is None) != (prior_dataset_id is None):
        raise ValueError("prior recovery manifest and private dataset ID must be paired")
    prior_recovery_sha256 = "NONE"
    if prior_recovery_manifest is not None:
        prior_recovery_sha256 = file_sha256(prior_recovery_manifest.resolve(strict=True))
    if output_root.exists():
        raise FileExistsError(f"output already exists: {output_root}")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(scbe_root),
            "merge-base",
            "--is-ancestor",
            INPUT_ACCESS_PARENT_COMMIT,
            "HEAD",
        ],
        check=False,
    )
    if ancestry.returncode != 0:
        raise RuntimeError("verified stable-CE result commit is not an ancestor")
    baseline_manifest_path = baseline_run / "RUN_MANIFEST.json"
    baseline_result_path = baseline_run / "RESULT.json"
    if file_sha256(baseline_manifest_path) != EXPECTED_BASELINE_MANIFEST_SHA256:
        raise RuntimeError("baseline manifest differs")
    if file_sha256(baseline_result_path) != EXPECTED_BASELINE_RESULT_SHA256:
        raise RuntimeError("baseline result differs")
    baseline_manifest = load_json(baseline_manifest_path)
    baseline_result = load_json(baseline_result_path)
    if file_sha256(preregistration) != EXPECTED_PREREGISTRATION_SHA256:
        raise RuntimeError("preregistration hash differs")
    if baseline_manifest["config"]["dataset_manifest_sha256"] != EXPECTED_DATASET_MANIFEST_SHA256:
        raise RuntimeError("baseline dataset identity differs")
    if tuple(baseline_manifest["config"]["seeds"]) != EXPECTED_SEEDS:
        raise RuntimeError("baseline seeds differ")
    for key, filename in SOURCE_HASH_FILES.items():
        if file_sha256(source_dir / filename) != baseline_manifest["config"]["source_hashes"][key]:
            raise RuntimeError(f"pinned action source differs: {key}")
    for seed in EXPECTED_SEEDS:
        parent_dir = baseline_run / "parents" / f"seed-{seed}"
        result = load_json(parent_dir / "RESULT.json")
        aggregate = [row for row in baseline_result["parents"] if int(row["seed"]) == seed]
        if len(aggregate) != 1:
            raise RuntimeError(f"aggregate parent row differs: {seed}")
        expected_hash, expected_counting = EXPECTED_PARENT_ROWS[seed]
        if aggregate[0]["parent_sha256"] != expected_hash:
            raise RuntimeError(f"aggregate parent hash differs: {seed}")
        if float(aggregate[0]["counting_accuracy"]) != expected_counting:
            raise RuntimeError(f"aggregate parent counting differs: {seed}")
        if result.get("parent_sha256") != expected_hash:
            raise RuntimeError(f"adjacent parent result hash differs: {seed}")
        if float(result.get("counting_accuracy")) != expected_counting:
            raise RuntimeError(f"adjacent parent counting differs: {seed}")
        if file_sha256(parent_dir / "PARENT.pt") != expected_hash:
            raise RuntimeError(f"parent bytes differ: {seed}")

    campaign = scbe_root / "python" / "scbe" / "clay_input_access_campaign.py"
    campaign.resolve(strict=True)
    campaign_sha256 = file_sha256(campaign)
    loom_root = source_dir.parents[1]
    output_root.mkdir(parents=True)
    dataset_dir = output_root / "dataset"
    kernel_dir = output_root / "kernel"
    dataset_dir.mkdir()
    kernel_dir.mkdir()

    with tempfile.TemporaryDirectory(prefix="clay-input-access-packet-") as temporary:
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
            "input_access_parent_commit": INPUT_ACCESS_PARENT_COMMIT,
            "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
            "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
            "dataset_manifest_sha256": EXPECTED_DATASET_MANIFEST_SHA256,
            "trust_anchors": {
                "preregistration_sha256": EXPECTED_PREREGISTRATION_SHA256,
                "campaign_sha256": campaign_sha256,
            },
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
        manifest_path = packet_root / "CLAY_INPUT_ACCESS_KAGGLE_PACKET.json"
        write_json(manifest_path, packet_manifest)
        packet_manifest_sha256 = file_sha256(manifest_path)
        archive_path = dataset_dir / "clay-input-access-efficacy.packet"
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

    trust_anchors = {
        "descriptor_sha256": file_sha256(dataset_dir / "PACKET_DESCRIPTOR.json"),
        "archive_sha256": file_sha256(archive_path),
        "packet_manifest_sha256": packet_manifest_sha256,
        "preregistration_sha256": EXPECTED_PREREGISTRATION_SHA256,
        "campaign_sha256": campaign_sha256,
        "prior_recovery_sha256": prior_recovery_sha256,
    }

    write_json(
        dataset_dir / "dataset-metadata.json",
        {
            "title": "Clay Input Access Efficacy Input 20261119",
            "id": dataset_id,
            "licenses": [{"name": "other"}],
            "isPrivate": True,
        },
    )
    render_kernel_entry(
        kernel_entry_source,
        kernel_dir / kernel_entry_source.name,
        trust_anchors,
    )
    write_json(
        kernel_dir / "kernel-metadata.json",
        {
            "id": kernel_id,
            "title": "Clay Input Access Efficacy 20261119",
            "code_file": kernel_entry_source.name,
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": False,
            "enable_internet": False,
            "dataset_sources": [
                dataset_id,
                *([prior_dataset_id] if prior_dataset_id is not None else []),
            ],
            "competition_sources": [],
            "kernel_sources": [],
        },
    )
    receipt = {
        "schema": BUILD_SCHEMA,
        "status": "BUILT_PRIVATE_OFFLINE_NOT_UPLOADED_NOT_RUN",
        "created_at_utc": utc_now(),
        "source_commit": git_value(scbe_root, "rev-parse", "HEAD"),
        "input_access_parent_commit": INPUT_ACCESS_PARENT_COMMIT,
        "dataset_id": dataset_id,
        "kernel_id": kernel_id,
        "baseline_manifest_sha256": EXPECTED_BASELINE_MANIFEST_SHA256,
        "baseline_result_sha256": EXPECTED_BASELINE_RESULT_SHA256,
        "trust_anchors": trust_anchors,
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
        default="issacizrealdavis/clay-input-access-efficacy-input-20261119",
    )
    parser.add_argument(
        "--kernel-id",
        default="issacizrealdavis/clay-input-access-efficacy-20261119",
    )
    parser.add_argument(
        "--kernel-entry-source",
        type=Path,
        default=Path(__file__).with_name("run_clay_input_access_kaggle.py"),
    )
    parser.add_argument("--prior-recovery-manifest", type=Path)
    parser.add_argument("--prior-dataset-id")
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
        prior_recovery_manifest=args.prior_recovery_manifest,
        prior_dataset_id=args.prior_dataset_id,
    )
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
