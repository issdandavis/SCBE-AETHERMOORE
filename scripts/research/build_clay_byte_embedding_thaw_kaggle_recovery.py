"""Build the exact, offline Kaggle recovery packet for byte-embedding thaw.

This builder packages immutable terminal artifacts for aggregation and
independent inference replay only.  It never opens a trainer, mutates a tensor,
merges weights, or writes into the source campaign directory.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.research.build_clay_frozen_multiview_kaggle_packet import (
    LOOM_FILES as PROVEN_LOOM_FILES,
    canonical_json,
    copy_exact,
    descriptor,
    deterministic_zip,
    load_json,
    sha256_file,
    write_json,
)

PACKET_SCHEMA = "clay.byte-embedding-thaw-kaggle-recovery-packet.v1"
DESCRIPTOR_SCHEMA = "clay.byte-embedding-thaw-kaggle-recovery-dataset.v1"
BUILD_SCHEMA = "clay.byte-embedding-thaw-kaggle-recovery-build.v1"
RUN_SCHEMA = "clay.byte-embedding-thaw-campaign.v1.manifest"
EXPECTED_RUN_MANIFEST_SHA256 = "6bb0fd276c1d2d9c309dc9e04ea9fb4d9aaf84aab62b2060c166059c1da492cc"
EXPECTED_CONFIG_HASH = "583f4362158068a056e52ea8894163989fe810378d60b858e60c4e9a70c0e0d6"
EXPECTED_DATASET_MANIFEST_SHA256 = "7460665cbb718097438227c452f1915e88bdc5a10ac643122b17908b505d0041"
BASELINE_VERIFIER_COMMIT = "4b3483e1f821470fbd3cfee3ad4187dec74c69de"

RUNTIME_MODULES = (
    "python/__init__.py",
    "python/scbe/clay_byte_embedding_thaw.py",
    "python/scbe/clay_byte_embedding_thaw_campaign.py",
    "python/scbe/clay_byte_embedding_thaw_replay.py",
    "python/scbe/clay_frozen_multiview_adapter.py",
    "python/scbe/clay_frozen_multiview_data.py",
    "python/scbe/clay_frozen_multiview_replay.py",
    "python/scbe/clay_paired_orbit_training.py",
    "python/scbe/concept_exposure_ledger.py",
    "python/scbe/atomic_tokenization.py",
    "python/scbe/bit_spine.py",
    "python/scbe/ca_opcode_table.py",
    "python/scbe/ca_semantics.py",
    "python/scbe/chemical_fusion.py",
    "python/scbe/chemistry_dimensions.py",
    "python/scbe/instrument.py",
    "python/scbe/reaction_balance.py",
    "python/scbe/reaction_state.py",
    "python/scbe/tongue_isa.py",
    "python/scbe/turing_rubix.py",
)
SOURCE_HASH_FILES = {
    "policy": "trit_compiled_action_policy.py",
    "topology": "topology_sector_action_ab.py",
    "sandbox": "developmental_game_sandbox.py",
    "regional": "regional_breathing_field.py",
}
RUN_STATUS_FILES = (
    "STATUS.json",
    "CONTINUITY_WATCH_STATUS.json",
    "INDEPENDENT_REPLAY_WATCH_STATUS.json",
    "SUCCESSOR_STATUS.json",
)
BASELINE_AUTHORITY_FILES = (
    "RUN_MANIFEST.json",
    "RESULT.json",
    "INDEPENDENT_REPLAY.json",
    "INDEPENDENT_REPLAY_WATCH_STATUS.json",
)


@dataclass(frozen=True, slots=True)
class FileSpec:
    source: Path
    target: str
    role: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_hash(path: Path, expected: str, *, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected.casefold():
        raise RuntimeError(f"{label} hash differs: expected {expected}, got {actual}: {path}")


def _add(specs: list[FileSpec], source: Path, target: str, role: str) -> None:
    source = source.resolve(strict=True)
    if not source.is_file():
        raise FileNotFoundError(source)
    specs.append(FileSpec(source=source, target=target, role=role))


def _validate_pointer(directory: Path, *, expected_step: int) -> dict[str, Any]:
    pointer_path = directory / "checkpoints" / "latest.json"
    pointer = load_json(pointer_path)
    slot = directory / "checkpoints" / str(pointer["slot"])
    if int(pointer["step"]) != expected_step:
        raise RuntimeError(f"terminal pointer is not at step {expected_step}: {pointer_path}")
    _require_hash(slot, str(pointer["sha256"]), label="terminal checkpoint pointer")
    for name in ("slot-a.pt", "slot-b.pt"):
        if not (directory / "checkpoints" / name).is_file():
            raise FileNotFoundError(directory / "checkpoints" / name)
    return pointer


def _source_specs(
    run_manifest_path: Path,
    kernel_entry_source: Path,
) -> tuple[list[FileSpec], dict[str, Any], dict[str, Any]]:
    run_manifest_path = run_manifest_path.resolve(strict=True)
    _require_hash(
        run_manifest_path,
        EXPECTED_RUN_MANIFEST_SHA256,
        label="byte-thaw run manifest",
    )
    run_manifest = load_json(run_manifest_path)
    if run_manifest.get("schema") != RUN_SCHEMA:
        raise ValueError("byte-thaw run manifest schema changed")
    config = run_manifest.get("config")
    if not isinstance(config, dict):
        raise TypeError("byte-thaw run config is not an object")
    if config.get("device") != "cpu":
        raise ValueError("recovery packet is pinned to the CPU campaign")
    if config.get("authority") != "MEASUREMENT_ONLY_NO_EXECUTION_NO_PROMOTION":
        raise ValueError("byte-thaw authority boundary changed")
    if stable_hash(config) != run_manifest.get("config_hash"):
        raise RuntimeError("byte-thaw config hash differs")
    if run_manifest.get("config_hash") != EXPECTED_CONFIG_HASH:
        raise RuntimeError("unexpected byte-thaw config identity")
    dataset = run_manifest.get("dataset")
    if not isinstance(dataset, dict):
        raise TypeError("byte-thaw dataset manifest is not an object")
    if dataset.get("manifest_sha256") != EXPECTED_DATASET_MANIFEST_SHA256:
        raise RuntimeError("byte-thaw dataset identity changed")

    run_dir = run_manifest_path.parent.resolve(strict=True)
    baseline_dir = Path(str(config["baseline_run"])).resolve(strict=True)
    source_dir = Path(str(config["source_dir"])).resolve(strict=True)
    loom_root = source_dir.parents[1]
    runner = Path(str(run_manifest["runner"])).resolve(strict=True)
    thaw_module = Path(str(run_manifest["thaw_module"])).resolve(strict=True)
    preregistration = Path(str(run_manifest["preregistration"])).resolve(strict=True)
    worktree = runner.parents[2]

    _require_hash(runner, str(run_manifest["runner_sha256"]), label="campaign runner")
    _require_hash(thaw_module, str(run_manifest["thaw_module_sha256"]), label="thaw module")
    _require_hash(
        preregistration,
        str(run_manifest["preregistration_sha256"]),
        label="preregistration",
    )
    baseline_manifest = baseline_dir / "RUN_MANIFEST.json"
    baseline_result = baseline_dir / "RESULT.json"
    _require_hash(
        baseline_manifest,
        str(config["baseline_manifest_sha256"]),
        label="baseline manifest",
    )
    _require_hash(
        baseline_result,
        str(config["baseline_result_sha256"]),
        label="baseline result",
    )
    for key, filename in SOURCE_HASH_FILES.items():
        _require_hash(
            source_dir / filename,
            str(config["source_hashes"][key]),
            label=f"action source {key}",
        )

    specs: list[FileSpec] = []
    _add(specs, run_manifest_path, "payload/run/RUN_MANIFEST.json", "run_manifest")
    for name in RUN_STATUS_FILES:
        path = run_dir / name
        if path.is_file():
            _add(specs, path, f"authorities/source_status/{name}", "source_status")

    seeds = tuple(int(seed) for seed in config["seeds"])
    arms = tuple(str(arm) for arm in config["arms"])
    expected_steps = int(config["grow_steps"])
    terminal_pointers: list[dict[str, Any]] = []
    for arm in arms:
        for seed in seeds:
            name = f"{arm}-seed-{seed}"
            horse = run_dir / "horses" / name
            pointer = _validate_pointer(horse, expected_step=expected_steps)
            result = load_json(horse / "RESULT.json")
            if result.get("status") != "COMPLETE" or int(result.get("steps", -1)) != expected_steps:
                raise RuntimeError(f"horse is not terminal: {horse}")
            _require_hash(horse / "MODEL.pt", str(result["model_sha256"]), label="terminal model")
            terminal_pointers.append({"horse": name, **pointer})
            for relative, role in (
                ("MODEL.pt", "terminal_model"),
                ("RESULT.json", "terminal_result"),
                ("checkpoints/latest.json", "terminal_pointer"),
                ("checkpoints/slot-a.pt", "terminal_checkpoint_slot"),
                ("checkpoints/slot-b.pt", "terminal_checkpoint_slot"),
            ):
                _add(
                    specs,
                    horse / relative,
                    f"payload/run/horses/{name}/{relative}",
                    role,
                )

    for name in BASELINE_AUTHORITY_FILES:
        _add(specs, baseline_dir / name, f"payload/baseline/{name}", "baseline_authority")

    parent_pointers: list[dict[str, Any]] = []
    baseline = load_json(baseline_result)
    parent_rows = {int(row["seed"]): row for row in baseline.get("parents", [])}
    for seed in seeds:
        parent = baseline_dir / "parents" / f"seed-{seed}"
        parent_result = load_json(parent / "RESULT.json")
        recorded = parent_rows.get(seed, parent_result)
        _require_hash(
            parent / "PARENT.pt",
            str(recorded["parent_sha256"]),
            label="parent checkpoint",
        )
        pointer = _validate_pointer(parent, expected_step=int(recorded["steps"]))
        parent_pointers.append({"seed": seed, **pointer})
        for relative, role in (
            ("PARENT.pt", "parent_checkpoint"),
            ("RESULT.json", "parent_result"),
            ("checkpoints/latest.json", "parent_checkpoint_pointer"),
            ("checkpoints/slot-a.pt", "parent_checkpoint_slot"),
            ("checkpoints/slot-b.pt", "parent_checkpoint_slot"),
        ):
            _add(
                specs,
                parent / relative,
                f"payload/baseline/parents/seed-{seed}/{relative}",
                role,
            )

        control_name = f"frozen_adapter_multiview-seed-{seed}"
        control = baseline_dir / "horses" / control_name
        control_result = load_json(control / "RESULT.json")
        _require_hash(
            control / "MODEL.pt",
            str(control_result["model_sha256"]),
            label="baseline control model",
        )
        _add(
            specs,
            control / "MODEL.pt",
            f"payload/baseline/horses/{control_name}/MODEL.pt",
            "baseline_control_model",
        )
        _add(
            specs,
            control / "RESULT.json",
            f"payload/baseline/horses/{control_name}/RESULT.json",
            "baseline_control_result",
        )

    for relative in RUNTIME_MODULES:
        _add(
            specs,
            worktree / relative,
            f"runtime/scbe_repo/{relative}",
            "runtime_source",
        )
    _add(
        specs,
        kernel_entry_source,
        f"runtime/{kernel_entry_source.name}",
        "path_neutral_entrypoint",
    )
    _add(
        specs,
        preregistration,
        "authorities/CLAY_BYTE_EMBEDDING_THAW_PREREGISTRATION_20261115.md",
        "preregistration",
    )
    for relative in PROVEN_LOOM_FILES:
        source = loom_root / relative
        role = "action_source" if source.is_relative_to(source_dir) else "action_source_dependency"
        _add(specs, source, f"payload/loom_root/{relative}", role)

    path_map = {
        "schema": f"{PACKET_SCHEMA}.path-map",
        "rule": (
            "Exact Windows authorities map to packet-relative immutable inputs; " "manifest strings are not rewritten."
        ),
        "mappings": [
            {
                "windows_path": str(run_dir),
                "packet_path": "payload/run",
                "kind": "directory",
                "runtime_use": "staged_run_input",
            },
            {
                "windows_path": str(baseline_dir),
                "packet_path": "payload/baseline",
                "kind": "directory",
                "runtime_use": "posix_alias",
            },
            {
                "windows_path": str(source_dir),
                "packet_path": "payload/loom_root/experiments/clay_action_compiler_20261109",
                "kind": "directory",
                "runtime_use": "posix_alias",
            },
            {
                "windows_path": str(loom_root),
                "packet_path": "payload/loom_root",
                "kind": "directory",
                "runtime_use": "native_verify",
            },
            {
                "windows_path": str(runner),
                "packet_path": "runtime/scbe_repo/python/scbe/clay_byte_embedding_thaw_campaign.py",
                "kind": "file",
                "runtime_use": "provenance",
            },
            {
                "windows_path": str(thaw_module),
                "packet_path": "runtime/scbe_repo/python/scbe/clay_byte_embedding_thaw.py",
                "kind": "file",
                "runtime_use": "provenance",
            },
            {
                "windows_path": str(preregistration),
                "packet_path": "authorities/CLAY_BYTE_EMBEDDING_THAW_PREREGISTRATION_20261115.md",
                "kind": "file",
                "runtime_use": "provenance",
            },
        ],
    }
    facts = {
        "run_dir": str(run_dir),
        "baseline_dir": str(baseline_dir),
        "source_dir": str(source_dir),
        "worktree": str(worktree),
        "terminal_pointers": terminal_pointers,
        "parent_pointers": parent_pointers,
        "path_map": path_map,
    }
    return specs, run_manifest, facts


def _write_generated_authorities(packet_root: Path, run_manifest: dict[str, Any], facts: dict[str, Any]) -> None:
    minimal_init = packet_root / "runtime" / "scbe_repo" / "python" / "scbe" / "__init__.py"
    minimal_init.parent.mkdir(parents=True, exist_ok=True)
    minimal_init.write_text(
        '"""Minimal sealed package for byte-thaw aggregation and replay only."""\n',
        encoding="utf-8",
        newline="\n",
    )
    write_json(packet_root / "authorities" / "RUN_CONFIG.json", run_manifest["config"])
    write_json(packet_root / "authorities" / "DATASET_MANIFEST.json", run_manifest["dataset"])
    write_json(
        packet_root / "authorities" / "ACTION_BYTES.json",
        {
            "schema": f"{PACKET_SCHEMA}.action-bytes",
            "source": "developmental_game_sandbox.py",
            "names": [
                "rest",
                "push_x_positive",
                "push_x_negative",
                "push_y_positive",
                "push_y_negative",
                "inspect",
                "remember",
                "recall",
                "help",
            ],
            "decimal": list(range(0xA0, 0xA9)),
            "hex": [f"0x{value:02x}" for value in range(0xA0, 0xA9)],
        },
    )
    write_json(packet_root / "PATH_MAP.json", facts["path_map"])
    baseline_replay = load_json(Path(facts["baseline_dir"]) / "INDEPENDENT_REPLAY.json")
    historical_bytes = subprocess.check_output(
        [
            "git",
            "-C",
            facts["worktree"],
            "show",
            (f"{BASELINE_VERIFIER_COMMIT}:" "python/scbe/clay_frozen_multiview_replay.py"),
        ]
    )
    expected_verifier_hash = str(baseline_replay["independent_dataset_builder_sha256"])
    actual_verifier_hash = sha256(historical_bytes).hexdigest()
    if actual_verifier_hash != expected_verifier_hash:
        raise RuntimeError(
            "historical baseline verifier does not match its replay receipt: "
            f"expected {expected_verifier_hash}, got {actual_verifier_hash}"
        )
    historical_path = packet_root / "authorities" / "baseline_verifier" / "clay_frozen_multiview_replay.py"
    historical_path.parent.mkdir(parents=True, exist_ok=True)
    historical_path.write_bytes(historical_bytes)


def _packet_files(packet_root: Path, roles: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in packet_root.rglob("*") if item.is_file()):
        relative = path.relative_to(packet_root).as_posix()
        if relative == "PACKET_MANIFEST.json":
            continue
        row = descriptor(path, relative_to=packet_root)
        row["role"] = roles.get(relative, "generated_authority")
        rows.append(row)
    return rows


def build_packet(
    *,
    run_manifest_path: Path,
    output_parent: Path,
    dataset_id: str,
    kernel_id: str,
    kernel_entry_source: Path,
) -> dict[str, Any]:
    kernel_entry_source = kernel_entry_source.resolve(strict=True)
    output_parent = output_parent.resolve()
    specs, run_manifest, facts = _source_specs(run_manifest_path, kernel_entry_source)

    with tempfile.TemporaryDirectory(prefix="clay-byte-thaw-recovery-") as temporary:
        packet_root = Path(temporary) / "packet"
        packet_root.mkdir()
        roles: dict[str, str] = {}
        for spec in specs:
            target = packet_root / Path(*spec.target.split("/"))
            copy_exact(spec.source, target)
            roles[spec.target] = spec.role
        _write_generated_authorities(packet_root, run_manifest, facts)
        files = _packet_files(packet_root, roles)
        manifest_body: dict[str, Any] = {
            "schema": PACKET_SCHEMA,
            "authority": {
                "training": "NONE",
                "weight_mutation": "NONE",
                "merge": "NONE",
                "promotion": "NONE",
                "upload": "NONE",
            },
            "claim_boundary": (
                "Exact terminal aggregation and independent inference replay only; "
                "no training, weight mutation, merge, promotion, or upload authority."
            ),
            "dataset_id": dataset_id,
            "kernel_id": kernel_id,
            "source_run_manifest_sha256": sha256_file(run_manifest_path.resolve(strict=True)),
            "source_config_hash": run_manifest["config_hash"],
            "source_dataset_manifest_sha256": run_manifest["dataset"]["manifest_sha256"],
            "expected_terminal_horses": 9,
            "expected_terminal_steps": 162_000,
            "terminal_pointers": facts["terminal_pointers"],
            "parent_pointers": facts["parent_pointers"],
            "path_map_sha256": sha256_file(packet_root / "PATH_MAP.json"),
            "files": files,
            "file_count": len(files),
            "payload_bytes": sum(int(row["bytes"]) for row in files),
            "cpu_contract": {
                "accelerator": "NONE",
                "internet": False,
                "threads": 2,
                "writable_output_required": True,
            },
        }
        packet_id = stable_hash(manifest_body)
        manifest = {
            **manifest_body,
            "packet_id": packet_id,
            "manifest_body_sha256": packet_id,
            "self_hash_rule": (
                "SHA256(canonical JSON after removing packet_id, manifest_body_sha256, and self_hash_rule)"
            ),
        }
        # self_hash_rule is explanatory and excluded with the two seal fields.
        body_for_hash = dict(manifest)
        for field in ("packet_id", "manifest_body_sha256", "self_hash_rule"):
            body_for_hash.pop(field)
        if stable_hash(body_for_hash) != packet_id:
            raise AssertionError("packet manifest self-hash construction failed")
        write_json(packet_root / "PACKET_MANIFEST.json", manifest)

        output_root = output_parent / f"clay-byte-thaw-aggregation-replay-{packet_id[:16]}"
        if output_root.exists():
            raise FileExistsError(f"content-addressed output already exists: {output_root}")
        dataset_dir = output_root / "dataset"
        kernel_dir = output_root / "kernel"
        dataset_dir.mkdir(parents=True)
        kernel_dir.mkdir()
        archive = dataset_dir / f"clay-byte-thaw-aggregation-replay-{packet_id[:16]}.packet"
        deterministic_zip(packet_root, archive)
        write_json(
            dataset_dir / "PACKET_DESCRIPTOR.json",
            {
                "schema": DESCRIPTOR_SCHEMA,
                "dataset_id": dataset_id,
                "packet_id": packet_id,
                "archive": descriptor(archive),
                "packet_manifest": descriptor(packet_root / "PACKET_MANIFEST.json"),
                "authority": manifest["authority"],
            },
        )
        write_json(
            dataset_dir / "dataset-metadata.json",
            {
                "title": f"Clay Byte Thaw Aggregation Replay {packet_id[:16]}",
                "id": dataset_id,
                "licenses": [{"name": "other"}],
            },
        )
        copy_exact(kernel_entry_source, kernel_dir / kernel_entry_source.name)
        write_json(
            kernel_dir / "kernel-metadata.json",
            {
                "id": kernel_id,
                "title": f"Clay Byte Thaw Aggregation Replay {packet_id[:16]}",
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
        write_json(
            output_root / "PRIVATE_KAGGLE_LAUNCH_PLAN.json",
            {
                "schema": f"{BUILD_SCHEMA}.launch-plan",
                "status": "READY_NOT_UPLOADED_NOT_RUN",
                "dataset_id": dataset_id,
                "kernel_id": kernel_id,
                "internet": False,
                "gpu": False,
                "training": "NONE",
                "commands": {
                    "create_dataset_first_time": f'kaggle datasets create -p "{dataset_dir}" --dir-mode zip',
                    "version_existing_dataset": (
                        f'kaggle datasets version -p "{dataset_dir}" '
                        f'-m "byte-thaw aggregation replay {packet_id[:16]}" '
                        "--dir-mode zip"
                    ),
                    "push_private_cpu_kernel": f'kaggle kernels push -p "{kernel_dir}"',
                },
                "expected_outputs": [
                    "/kaggle/working/clay-byte-thaw-aggregation-replay/run/RESULT.json",
                    "/kaggle/working/clay-byte-thaw-aggregation-replay/INDEPENDENT_REPLAY.json",
                    "/kaggle/working/clay-byte-thaw-aggregation-replay/INDEPENDENT_REPLAY_LEDGER.jsonl",
                    "/kaggle/working/clay-byte-thaw-aggregation-replay/RECOVERY_RECEIPT.json",
                ],
                "authority": {
                    "upload": "REQUIRES_SEPARATE_USER_ACTION",
                    "run": "REQUIRES_SEPARATE_USER_ACTION",
                    "training": "NONE",
                    "weight_mutation": "NONE",
                    "merge": "NONE",
                    "promotion": "NONE",
                },
            },
        )

    receipt = {
        "schema": BUILD_SCHEMA,
        "status": "BUILT_PRIVATE_OFFLINE_NOT_UPLOADED_NOT_RUN",
        "created_at_utc": utc_now(),
        "packet_id": packet_id,
        "output_root": str(output_root),
        "source_run_manifest_sha256": EXPECTED_RUN_MANIFEST_SHA256,
        "packet_payload_bytes": int(manifest["payload_bytes"]),
        "packet_file_count": int(manifest["file_count"]),
        "archive": descriptor(archive, relative_to=output_root),
        "dataset_descriptor": descriptor(dataset_dir / "PACKET_DESCRIPTOR.json", relative_to=output_root),
        "kernel_entry": descriptor(kernel_dir / kernel_entry_source.name, relative_to=output_root),
        "launch_plan": descriptor(output_root / "PRIVATE_KAGGLE_LAUNCH_PLAN.json", relative_to=output_root),
        "authority": {
            "training": "NONE",
            "weight_mutation": "NONE",
            "merge": "NONE",
            "promotion": "NONE",
            "upload": "NONE",
            "kaggle_run": "NONE",
        },
    }
    write_json(output_root / "BUILD_RECEIPT.json", receipt)
    return receipt


def parse_args(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", required=True, type=Path)
    parser.add_argument("--output-parent", required=True, type=Path)
    parser.add_argument(
        "--dataset-id",
        default="issacizrealdavis/clay-byte-thaw-aggregation-replay-20261117",
    )
    parser.add_argument(
        "--kernel-id",
        default="issacizrealdavis/clay-byte-thaw-aggregation-replay-20261117",
    )
    parser.add_argument(
        "--kernel-entry-source",
        type=Path,
        default=Path(__file__).with_name("run_clay_byte_embedding_thaw_kaggle_recovery.py"),
    )
    return parser.parse_args(arguments)


def main(arguments: Iterable[str] | None = None) -> int:
    args = parse_args(arguments)
    receipt = build_packet(
        run_manifest_path=args.run_manifest,
        output_parent=args.output_parent,
        dataset_id=args.dataset_id,
        kernel_id=args.kernel_id,
        kernel_entry_source=args.kernel_entry_source,
    )
    print(canonical_json(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
