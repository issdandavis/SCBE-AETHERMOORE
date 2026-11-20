"""Run one hash-pinned, read-only Clay VQCC corpus intake on Kaggle CPU.

The default entry point is deliberately launch-disabled until a separate,
one-use execution admission is reviewed and changed.  An admitted run reads the
private corpus mount, builds the already-reviewed source-family split and
bounded samples under ``/tmp``, and atomically publishes only a bounded archive
and terminal receipt under ``/kaggle/working``.  It cannot train, upload,
submit, promote, or mutate the attached corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
INPUT_ROOT = Path("/kaggle/input")
WORK_ROOT = Path("/kaggle/working")
SCRATCH_ROOT = Path("/tmp")
OUTPUT_NAME = "clay_vqcc_readonly_intake_v1"
ADMISSION_PATH = HERE / "EXECUTION_ADMISSION.json"
METADATA_PATH = HERE / "kernel-metadata.json"
SPEC_PATH = HERE / "CAMPAIGN_SPEC.json"
EXPECTED_DATASET_REF = "issacizrealdavis/clay-vqcc-research-corpus/2"
EXPECTED_DATASET_VERSION = 2
EXPECTED_MANIFEST_SHA256 = "e4a9e7e9911fd8cdd8f858595a57b047402eb32a51571a54db580f4be87597c5"
EXPECTED_SPEC_SHA256 = "eb8e658fcc166e4ce15828096ac0fded56d97ce43135933d553465cbee640de2"
MINIMUM_WRITABLE_BYTES = 26_843_545_600
MAX_PERSISTED_BYTES = 134_217_728
MAX_INPUT_MOUNTS = 256
EXPECTED_SOURCE_HASHES = {
    "CAMPAIGN_SPEC.json": EXPECTED_SPEC_SHA256,
    "PARENT_VOCAB_AUDIT.json": "8f620583963cfffc05b0553186b4a6a6c8f1054979cb0a4ca32d4a3bd96834f0",
    "build_vqcc_split.py": "4db41f97786c3336262d784e2d20d8a94ec824944fbe4dc04ac8b433ec978728",
    "clay_vqcc_byte_codec.py": "693fa47109b00688249f15ea09e0155d0647db7f17ac11768bef70653406ee87",
    "findings_task.py": "1068f77846e296a2380715f3bf48a58e89eec49292ab24350248cd7067e5d8c7",
    "load_vqcc_corpus.py": "9ff2a53f8ed7bf1cfe55554dcaf76578b76fc5a2af1357156679cf7bd437061a",
    "run_readonly_intake.py": "3c3d55cc8228738c31331c3e0ea2ca8725fb33cef0b7d4d81a14e9b136cc832c",
    "task_manifest.py": "35dbb40ce8847ba3bee80ca3128009729bd137cb0f5fc677316a763abd1270d0",
    "vqcc_task.py": "67d46ae1fbd379c4e7793d1121e45d4b19b3b1af9f2766ce7640b13afd0e90d5",
}


class ReleaseError(RuntimeError):
    """Raised when the staged release differs from its reviewed contract."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("xb") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"))
        stream.write(b"\n")


def verify_bundled_sources() -> dict[str, str]:
    observed: dict[str, str] = {}
    for name, expected in EXPECTED_SOURCE_HASHES.items():
        path = HERE / name
        if not path.is_file():
            raise ReleaseError(f"bundled source missing: {name}")
        actual = sha256_file(path)
        if actual != expected:
            raise ReleaseError(f"bundled source differs: {name}: {actual}")
        observed[name] = actual
    return observed


def verify_kernel_metadata() -> dict[str, Any]:
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    expected = {
        "dataset_sources": [EXPECTED_DATASET_REF],
        "competition_sources": [],
        "kernel_sources": [],
        "enable_gpu": False,
        "enable_internet": False,
        "is_private": True,
        "kernel_type": "script",
        "language": "python",
        "code_file": "clay_vqcc_readonly_intake.py",
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            raise ReleaseError(f"kernel metadata differs at {field}: {metadata.get(field)!r}")
    return metadata


def require_execution_admission() -> dict[str, Any]:
    admission = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
    if (
        admission.get("schema") != "clay.vqcc-readonly-intake.execution-admission.v1"
        or admission.get("state") != "READY_FOR_ONE_USE"
        or admission.get("execution_authorized") is not True
        or admission.get("consumed_at_utc") is not None
    ):
        raise ReleaseError("read-only intake is staged but not authorized for execution")
    if admission.get("dataset_ref") != EXPECTED_DATASET_REF:
        raise ReleaseError("execution admission names a different dataset")
    if admission.get("dataset_version") != EXPECTED_DATASET_VERSION:
        raise ReleaseError("execution admission names a different dataset version")
    if admission.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256:
        raise ReleaseError("execution admission names a different corpus manifest")
    return admission


def discover_corpus_root(input_root: Path) -> Path:
    input_root = input_root.resolve(strict=True)
    mounts = sorted(path for path in input_root.iterdir() if path.is_dir())
    if len(mounts) > MAX_INPUT_MOUNTS:
        raise ReleaseError(f"too many Kaggle input mounts: {len(mounts)}")
    matches: list[Path] = []
    for mount in mounts:
        manifest = mount / "CORPUS_MANIFEST.json"
        if manifest.is_file() and sha256_file(manifest) == EXPECTED_MANIFEST_SHA256:
            matches.append(mount.resolve(strict=True))
    if len(matches) != 1:
        raise ReleaseError(
            f"expected exactly one pinned corpus mount, found {len(matches)}"
        )
    root = matches[0]
    if input_root not in root.parents:
        raise ReleaseError("resolved corpus mount escaped /kaggle/input")
    return root


def require_storage_gate(path: Path) -> int:
    path = path.resolve(strict=True)
    free = shutil.disk_usage(path).free
    if free < MINIMUM_WRITABLE_BYTES:
        raise ReleaseError(
            f"storage gate failed at {path}: {free} < {MINIMUM_WRITABLE_BYTES}"
        )
    return free


def _zip_tree(source: Path, destination: Path) -> dict[str, Any]:
    files = sorted(path for path in source.rglob("*") if path.is_file())
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(source).as_posix())
    size = destination.stat().st_size
    if size > MAX_PERSISTED_BYTES:
        raise ReleaseError(f"persisted intake archive exceeds bound: {size}")
    return {
        "files": len(files),
        "bytes": size,
        "sha256": sha256_file(destination),
    }


def run_admitted_intake(
    *,
    input_root: Path = INPUT_ROOT,
    work_root: Path = WORK_ROOT,
    scratch_root: Path = SCRATCH_ROOT,
) -> dict[str, Any]:
    sources = verify_bundled_sources()
    metadata = verify_kernel_metadata()
    admission = require_execution_admission()
    scratch_free = require_storage_gate(scratch_root)
    corpus_root = discover_corpus_root(input_root)
    work_root = work_root.resolve(strict=True)
    final_output = work_root / OUTPUT_NAME
    if final_output.exists():
        raise FileExistsError(f"refusing to overwrite immutable output: {final_output}")

    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import run_readonly_intake  # noqa: PLC0415

    scratch_parent = Path(tempfile.mkdtemp(prefix="clay-vqcc-intake-", dir=scratch_root))
    work_staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT_NAME}.tmp-", dir=work_root))
    try:
        intake_output = scratch_parent / "intake"
        receipt = run_readonly_intake.run_readonly_intake(
            corpus_root,
            intake_output,
            spec_path=SPEC_PATH,
            expected_spec_sha256=EXPECTED_SPEC_SHA256,
        )
        archive_path = work_staging / "intake.zip"
        archive = _zip_tree(intake_output, archive_path)
        terminal = {
            "schema": "clay.vqcc-readonly-intake.kaggle-terminal.v1",
            "status": "PASS_PREPARED_ONLY",
            "execution_id": admission.get("execution_id"),
            "dataset": {
                "ref": EXPECTED_DATASET_REF,
                "version": EXPECTED_DATASET_VERSION,
                "manifest_sha256": EXPECTED_MANIFEST_SHA256,
                "mount_name": corpus_root.name,
            },
            "runtime": {
                "private": metadata["is_private"],
                "internet": metadata["enable_internet"],
                "gpu": metadata["enable_gpu"],
                "scratch_free_bytes_before": scratch_free,
                "minimum_writable_bytes": MINIMUM_WRITABLE_BYTES,
            },
            "bundled_sources": sources,
            "intake_receipt_sha256": sha256_file(intake_output / "INTAKE_RECEIPT.json"),
            "intake_status": receipt["status"],
            "artifact": {"path": "intake.zip", **archive},
            "prohibited_actions": {
                "training": False,
                "dataset_mutation": False,
                "competition_submission": False,
                "checkpoint_promotion": False,
            },
        }
        terminal["receipt_payload_sha256"] = hashlib.sha256(canonical_json(terminal)).hexdigest()
        write_json_exclusive(work_staging / "TERMINAL_RECEIPT.json", terminal)
        work_staging.rename(final_output)
        return terminal
    except BaseException:
        if work_staging.exists() and work_staging.parent == work_root:
            shutil.rmtree(work_staging)
        raise
    finally:
        if scratch_parent.exists() and scratch_parent.parent == scratch_root.resolve():
            shutil.rmtree(scratch_parent)


def write_smoke_receipt(path: Path) -> dict[str, Any]:
    sources = verify_bundled_sources()
    metadata = verify_kernel_metadata()
    admission = json.loads(ADMISSION_PATH.read_text(encoding="utf-8"))
    if admission.get("execution_authorized") is not False or admission.get("state") != "NOT_CONSUMED":
        raise ReleaseError("local smoke is valid only for a launch-disabled packet")
    receipt = {
        "schema": "clay.vqcc-readonly-intake.release-smoke.v1",
        "status": "PASS_NO_CORPUS_READ_NO_CLOUD_EXECUTION",
        "cloud_execution": False,
        "training": False,
        "dataset_mutation": False,
        "competition_submission": False,
        "admission_state": admission["state"],
        "execution_authorized": admission["execution_authorized"],
        "source_hashes": sources,
        "kernel": {
            "private": metadata["is_private"],
            "internet": metadata["enable_internet"],
            "gpu": metadata["enable_gpu"],
        },
    }
    write_json_exclusive(path, receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-output", type=Path)
    args = parser.parse_args(argv)
    if args.smoke_output is not None:
        receipt = write_smoke_receipt(args.smoke_output)
    else:
        if os.name != "posix" or not Path("/kaggle").is_dir():
            raise ReleaseError("admitted intake requires Kaggle Linux")
        receipt = run_admitted_intake()
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
