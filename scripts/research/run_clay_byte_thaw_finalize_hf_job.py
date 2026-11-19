# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "jsonschema==4.26.0",
#   "numpy==2.4.6",
#   "huggingface_hub==0.36.2",
#   "scikit-learn==1.9.0",
#   "torch==2.13.0",
# ]
# ///
"""Private HF Job wrapper for Clay byte-thaw finalize/replay only."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from huggingface_hub import CommitOperationAdd, HfApi, snapshot_download

REPO_ID = "issdandavis/clay-byte-thaw-finalize-20261119"
REPO_TYPE = "dataset"
INPUT_PREFIX = "input/v2"
RUNNER_PATH = "code/run_clay_byte_thaw_finalize_kaggle.py"
EXPECTED = {
    f"{INPUT_PREFIX}/clay-byte-thaw-finalize.packet": {
        "bytes": 36184119,
        "sha256": "5af43e7e138e3c1109fb40689fb2bb3400384610342bae8aebac636266723686",
    },
    f"{INPUT_PREFIX}/PACKET_DESCRIPTOR.json": {
        "bytes": 712,
        "sha256": "471647529905de1afcc84e6f4a89814fe730f9929baf80170bea8df95767b241",
    },
    RUNNER_PATH: {
        "bytes": 20207,
        "sha256": "359b56fa6776a7f7e171b1f5ee4f674c2d76eb2a2bed4de69c92434b3b23126f",
    },
}
MINIMUM_FREE_GIB = 25.0
WORK = Path("/tmp/clay-byte-thaw-finalize")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def inventory(paths: list[Path], root: Path) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(paths)
    ]


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN was not injected as a Job secret")
    run_id = os.environ.get("CLAY_BYTE_THAW_RUN_ID", "").strip()
    if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in run_id):
        raise ValueError("CLAY_BYTE_THAW_RUN_ID is missing or unsafe")

    if WORK.exists():
        raise FileExistsError(f"work root already exists: {WORK}")
    WORK.mkdir(parents=True)
    capacity = shutil.disk_usage(WORK)
    capacity_receipt = {
        "checked_at_utc": utc_now(),
        "path": str(WORK),
        "total_bytes": capacity.total,
        "free_bytes": capacity.free,
        "free_gib": capacity.free / (1024**3),
        "minimum_free_gib": MINIMUM_FREE_GIB,
        "passed": capacity.free / (1024**3) >= MINIMUM_FREE_GIB,
        "python": sys.version,
    }
    print(json.dumps({"capacity": capacity_receipt}, sort_keys=True), flush=True)
    if not capacity_receipt["passed"]:
        raise RuntimeError("HF Job storage is below the unchanged 25 GiB gate")

    downloaded = Path(
        snapshot_download(
            repo_id=REPO_ID,
            repo_type=REPO_TYPE,
            token=token,
            local_dir=WORK / "repo",
            allow_patterns=[f"{INPUT_PREFIX}/*", RUNNER_PATH],
        )
    )
    input_inventory: list[dict[str, object]] = []
    for relative, expected in EXPECTED.items():
        path = (downloaded / relative).resolve(strict=True)
        got = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        if got != expected:
            raise RuntimeError(f"downloaded input differs: {relative}")
        input_inventory.append({"path": relative, **got})

    output = WORK / "output"
    runtime = WORK / "runtime"
    runner = downloaded / RUNNER_PATH
    input_root = downloaded / INPUT_PREFIX
    command = [
        sys.executable,
        str(runner),
        "--input-root",
        str(input_root),
        "--output-root",
        str(output),
        "--runtime-root",
        str(runtime),
    ]
    print(json.dumps({"launch": command, "torch_expected": "2.13.0"}), flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"exact finalize/replay runner exited {completed.returncode}")

    final = json.loads((output / "CLOUD_RUN_RECEIPT.json").read_text(encoding="utf-8"))
    replay = json.loads((output / "lineage_campaign/INDEPENDENT_REPLAY.json").read_text(encoding="utf-8"))
    environment = json.loads((output / "CLOUD_ENVIRONMENT.json").read_text(encoding="utf-8"))
    if final.get("status") != "COMPLETE_EXACT_LINEAGE_REPLAY_PASS_NO_PROMOTION":
        raise RuntimeError("final receipt status differs")
    if final.get("training_occurred") is not False or final.get("optimizer_updates") != 0:
        raise RuntimeError("final receipt does not prove zero training")
    if replay.get("status") != "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION":
        raise RuntimeError("independent replay status differs")
    if replay.get("errors"):
        raise RuntimeError("independent replay contains errors")
    if float(environment["free_gib"]) < MINIMUM_FREE_GIB:
        raise RuntimeError("exact runner did not observe the unchanged storage gate")

    selected_relatives = [
        "CLOUD_RUN_RECEIPT.json",
        "CLOUD_ENVIRONMENT.json",
        "RECOVERY_MANIFEST.json",
        "provider_campaign/RESULT.json",
        "provider_campaign/STATUS.json",
        "lineage_campaign/RESULT.json",
        "lineage_campaign/STATUS.json",
        "lineage_campaign/INDEPENDENT_REPLAY.json",
        "lineage_campaign/INDEPENDENT_REPLAY_LEDGER.jsonl",
    ]
    selected = [(output / relative).resolve(strict=True) for relative in selected_relatives]
    output_inventory = inventory(selected, output)
    job_receipt = {
        "schema": "clay.byte-thaw-finalize-hf-job.v1",
        "status": "COMPLETE_EXACT_LINEAGE_REPLAY_PASS_NO_PROMOTION",
        "completed_at_utc": utc_now(),
        "run_id": run_id,
        "repo_id": REPO_ID,
        "repo_type": REPO_TYPE,
        "capacity": capacity_receipt,
        "inputs": input_inventory,
        "outputs": output_inventory,
        "training_occurred": False,
        "optimizer_updates": 0,
        "independent_replay_status": replay["status"],
        "independent_replay_errors": replay["errors"],
        "max_metric_delta": replay["max_metric_delta"],
        "aggregate_comparison_delta": replay["aggregate_comparison_delta"],
        "aggregate_paired_delta": replay["aggregate_paired_delta"],
        "model_count": len(replay["model_receipts"]),
        "publication": "NONE_PRIVATE_DATASET_ONLY",
        "promotion": "NONE",
    }
    job_receipt_path = WORK / "HF_JOB_RECEIPT.json"
    write_json(job_receipt_path, job_receipt)

    prefix = f"outputs/{run_id}"
    operations = [
        CommitOperationAdd(
            path_in_repo=f"{prefix}/{relative}",
            path_or_fileobj=str(output / relative),
        )
        for relative in selected_relatives
    ]
    operations.append(
        CommitOperationAdd(
            path_in_repo=f"{prefix}/HF_JOB_RECEIPT.json",
            path_or_fileobj=str(job_receipt_path),
        )
    )
    HfApi(token=token).create_commit(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        operations=operations,
        commit_message=f"Private Clay byte-thaw finalize receipts {run_id}",
    )
    print(json.dumps(job_receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
