#!/usr/bin/env python3
"""Finalize Clay's completed byte-thaw campaign in a private Lightning Sandbox.

This controller is deliberately recovery-only.  It requests a short-lived CPU
Sandbox, verifies the provider has at least the campaign's unchanged 25 GiB
free-space floor, transfers the content-addressed packet in bounded base64
chunks, runs the exact recovery/replay entrypoint, reads the small receipts
back, verifies their provider hashes, and deletes the Sandbox in ``finally``.
It never creates an optimizer, updates a model, promotes a result, or publishes
an artifact.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import traceback
from typing import Any

from lightning_sdk.sandbox import Sandbox, SandboxConfig

MINIMUM_FREE_GIB = 25.0
CHUNK_BYTES = 512 * 1024
EXPECTED_ARCHIVE_SHA256 = "5af43e7e138e3c1109fb40689fb2bb3400384610342bae8aebac636266723686"
EXPECTED_DESCRIPTOR_SHA256 = "471647529905de1afcc84e6f4a89814fe730f9929baf80170bea8df95767b241"
EXPECTED_RUNNER_SHA256 = "359b56fa6776a7f7e171b1f5ee4f674c2d76eb2a2bed4de69c92434b3b23126f"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


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
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def run_command(sandbox: Any, executable: str, argv: list[str], timeout: float) -> dict[str, Any]:
    command = sandbox.run_command(executable, argv)
    command.wait(timeout=timeout)
    stdout = command.stdout()
    stderr = command.stderr()
    return {
        "argv": [executable, *argv],
        "exit_code": command.exit_code,
        "stdout_tail": stdout[-12000:],
        "stderr_tail": stderr[-12000:],
        "stdout_sha256": sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(stderr.encode("utf-8")),
    }


def safe_error(exc: BaseException) -> dict[str, Any]:
    """Record failure type/call sites without serializing provider/auth text."""
    return {
        "type": type(exc).__name__,
        "stack": [
            {"file": frame.filename, "line": frame.lineno, "function": frame.name}
            for frame in traceback.extract_tb(exc.__traceback__)
        ],
    }


def parse_last_json(command: dict[str, Any]) -> dict[str, Any]:
    lines = [line for line in command["stdout_tail"].splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("remote command produced no JSON")
    value = json.loads(lines[-1])
    if not isinstance(value, dict):
        raise TypeError("remote command did not produce one JSON object")
    return value


def verify_local_inputs(packet_dir: Path, runner: Path) -> dict[str, Any]:
    archive = packet_dir / "clay-byte-thaw-finalize.packet"
    descriptor = packet_dir / "PACKET_DESCRIPTOR.json"
    for path in (archive, descriptor, runner):
        path.resolve(strict=True)
    hashes = {
        "archive": {"bytes": archive.stat().st_size, "sha256": sha256_file(archive)},
        "descriptor": {"bytes": descriptor.stat().st_size, "sha256": sha256_file(descriptor)},
        "runner": {"bytes": runner.stat().st_size, "sha256": sha256_file(runner)},
    }
    expected = {
        "archive": EXPECTED_ARCHIVE_SHA256,
        "descriptor": EXPECTED_DESCRIPTOR_SHA256,
        "runner": EXPECTED_RUNNER_SHA256,
    }
    for name, digest in expected.items():
        if hashes[name]["sha256"] != digest:
            raise RuntimeError(f"local {name} hash differs")
    descriptor_value = json.loads(descriptor.read_text(encoding="utf-8"))
    if descriptor_value["archive"]["bytes"] != archive.stat().st_size:
        raise RuntimeError("descriptor archive byte count differs")
    if descriptor_value["archive"]["sha256"] != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("descriptor archive hash differs")
    return hashes


def upload_packet(
    sandbox: Any,
    *,
    packet_dir: Path,
    runner: Path,
    remote_root: str,
    receipt: dict[str, Any],
) -> None:
    remote_input = f"{remote_root}/input"
    remote_chunks = f"{remote_root}/chunks"
    sandbox.create_directory(remote_root)
    sandbox.create_directory(remote_input)
    sandbox.create_directory(remote_chunks)
    sandbox.write_file(
        f"{remote_input}/PACKET_DESCRIPTOR.json",
        (packet_dir / "PACKET_DESCRIPTOR.json").read_text(encoding="utf-8"),
    )
    sandbox.write_file(f"{remote_root}/runner.py", runner.read_text(encoding="utf-8"))

    archive = packet_dir / "clay-byte-thaw-finalize.packet"
    chunks = 0
    with archive.open("rb") as handle:
        while True:
            block = handle.read(CHUNK_BYTES)
            if not block:
                break
            sandbox.write_file(
                f"{remote_chunks}/{chunks:04d}.b64",
                base64.b64encode(block).decode("ascii"),
            )
            chunks += 1
    receipt["transfer"] = {
        "encoding": "independently-decodable-base64-chunks",
        "chunk_bytes": CHUNK_BYTES,
        "chunk_count": chunks,
        "local_archive_bytes": archive.stat().st_size,
        "local_archive_sha256": EXPECTED_ARCHIVE_SHA256,
    }


def readback_json(
    sandbox: Any,
    *,
    remote_path: str,
    local_path: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    text = sandbox.read_file(remote_path)
    if text is None:
        raise FileNotFoundError(f"provider readback missing: {remote_path}")
    data = text.encode("utf-8")
    got = sha256_bytes(data)
    if got != expected_sha256:
        raise RuntimeError(f"provider readback hash differs: {remote_path}")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    value = json.loads(text)
    if not isinstance(value, dict):
        raise TypeError(f"provider readback is not one JSON object: {remote_path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--instance-type", default="cpu-2")
    parser.add_argument("--runtime", default="python313")
    parser.add_argument("--storage-gb", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    args = parser.parse_args()

    key = os.environ.get("LIGHTNING_SANDBOX_API_KEY", "").strip()
    if not key:
        raise SystemExit("LIGHTNING_SANDBOX_API_KEY is not set")
    packet_dir = args.packet_dir.resolve(strict=True)
    runner = args.runner.resolve(strict=True)
    evidence_dir = args.evidence_dir.resolve()
    if evidence_dir.exists() and any(evidence_dir.iterdir()):
        raise FileExistsError(f"evidence directory is not empty: {evidence_dir}")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = evidence_dir / "LIGHTNING_RECOVERY_RECEIPT.json"
    local_inputs = verify_local_inputs(packet_dir, runner)

    created = datetime.now(timezone.utc)
    name = "clay-byte-thaw-finalize-" + created.strftime("%Y%m%d-%H%M%S")
    remote_root = "/workspace/clay-byte-thaw-finalize"
    remote_output = f"{remote_root}/output"
    remote_runtime = f"{remote_root}/runtime"
    sandbox = None
    receipt: dict[str, Any] = {
        "schema": "clay.byte-thaw-finalize-lightning.v1",
        "created_at_utc": created.isoformat(),
        "provider": "Lightning private teamspace-scoped Sandbox",
        "name": name,
        "instance_type": args.instance_type,
        "runtime": args.runtime,
        "persistent": False,
        "requested_storage_gb": args.storage_gb,
        "minimum_free_gib": MINIMUM_FREE_GIB,
        "training_authority": "REUSE_ONLY_NO_OPTIMIZER_UPDATES",
        "publication_authority": "NONE",
        "promotion_authority": "NONE",
        "local_inputs": local_inputs,
        "commands": [],
        "provider_readback": {},
        "success": False,
        "deleted": False,
    }
    try:
        sandbox = Sandbox.create(
            config=SandboxConfig(api_key=key),
            name=name,
            instance_type=args.instance_type,
            runtime=args.runtime,
            persistent=False,
            storage_gb=args.storage_gb,
            timeout=int(args.timeout_seconds * 1000),
        )
        receipt["sandbox_id"] = sandbox.sandbox_id
        receipt["initial_status"] = str(sandbox.status)

        capacity_code = (
            "import json,shutil,sys; import torch; "
            "u=shutil.disk_usage('/workspace'); "
            "print(json.dumps({'free_bytes':u.free,'free_gib':u.free/(1024**3),"
            "'total_bytes':u.total,'torch':torch.__version__,'python':sys.version}))"
        )
        capacity_command = run_command(sandbox, "python", ["-c", capacity_code], args.timeout_seconds)
        receipt["commands"].append(capacity_command)
        if capacity_command["exit_code"] != 0:
            raise RuntimeError("provider capacity/runtime probe failed")
        capacity = parse_last_json(capacity_command)
        receipt["capacity"] = capacity
        if float(capacity["free_gib"]) < MINIMUM_FREE_GIB:
            raise RuntimeError("provider storage is below the unchanged 25 GiB gate")

        upload_packet(
            sandbox,
            packet_dir=packet_dir,
            runner=runner,
            remote_root=remote_root,
            receipt=receipt,
        )
        rebuild_code = (
            "import base64,hashlib,json,pathlib; "
            f"r=pathlib.Path({remote_root!r}); o=r/'input'/'clay-byte-thaw-finalize.packet'; "
            "h=hashlib.sha256(); n=0; f=o.open('wb'); "
            "parts=sorted((r/'chunks').glob('*.b64')); "
            "[(lambda b:(f.write(b),h.update(b)))(base64.b64decode(p.read_text())) for p in parts]; "
            "f.close(); n=o.stat().st_size; "
            "print(json.dumps({'bytes':n,'sha256':h.hexdigest(),'chunks':len(parts)}))"
        )
        rebuild = run_command(sandbox, "python", ["-c", rebuild_code], args.timeout_seconds)
        receipt["commands"].append(rebuild)
        if rebuild["exit_code"] != 0:
            raise RuntimeError("provider packet reconstruction failed")
        remote_packet = parse_last_json(rebuild)
        receipt["remote_packet"] = remote_packet
        if remote_packet["sha256"] != EXPECTED_ARCHIVE_SHA256:
            raise RuntimeError("provider packet hash differs")
        if int(remote_packet["bytes"]) != int(local_inputs["archive"]["bytes"]):
            raise RuntimeError("provider packet byte count differs")

        launch = run_command(
            sandbox,
            "python",
            [
                f"{remote_root}/runner.py",
                "--input-root",
                f"{remote_root}/input",
                "--output-root",
                remote_output,
                "--runtime-root",
                remote_runtime,
            ],
            args.timeout_seconds,
        )
        receipt["commands"].append(launch)
        if launch["exit_code"] != 0:
            raise RuntimeError("exact provider recovery/replay failed")

        hash_targets = {
            "cloud_run_receipt": f"{remote_output}/CLOUD_RUN_RECEIPT.json",
            "cloud_environment": f"{remote_output}/CLOUD_ENVIRONMENT.json",
            "recovery_manifest": f"{remote_output}/RECOVERY_MANIFEST.json",
            "lineage_result": f"{remote_output}/lineage_campaign/RESULT.json",
            "lineage_status": f"{remote_output}/lineage_campaign/STATUS.json",
            "independent_replay": f"{remote_output}/lineage_campaign/INDEPENDENT_REPLAY.json",
            "provider_result": f"{remote_output}/provider_campaign/RESULT.json",
            "provider_status": f"{remote_output}/provider_campaign/STATUS.json",
        }
        hash_code = (
            "import hashlib,json,pathlib,sys; out={}; "
            "[(lambda p,n:out.update({n:{'bytes':p.stat().st_size,"
            "'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}))"
            "(pathlib.Path(v),k) "
            "for k,v in json.loads(sys.argv[1]).items()]; print(json.dumps(out,sort_keys=True))"
        )
        hashed = run_command(
            sandbox,
            "python",
            ["-c", hash_code, json.dumps(hash_targets, sort_keys=True)],
            args.timeout_seconds,
        )
        receipt["commands"].append(hashed)
        if hashed["exit_code"] != 0:
            raise RuntimeError("provider output hashing failed")
        remote_hashes = parse_last_json(hashed)
        receipt["provider_hashes"] = remote_hashes

        values: dict[str, dict[str, Any]] = {}
        for name_key, remote_path in hash_targets.items():
            values[name_key] = readback_json(
                sandbox,
                remote_path=remote_path,
                local_path=evidence_dir / f"{name_key.upper()}.json",
                expected_sha256=remote_hashes[name_key]["sha256"],
            )
            receipt["provider_readback"][name_key] = {
                **remote_hashes[name_key],
                "local_path": str(evidence_dir / f"{name_key.upper()}.json"),
            }

        final = values["cloud_run_receipt"]
        replay = values["independent_replay"]
        environment = values["cloud_environment"]
        if final.get("status") != "COMPLETE_EXACT_LINEAGE_REPLAY_PASS_NO_PROMOTION":
            raise RuntimeError("provider final receipt status differs")
        if final.get("training_occurred") is not False or final.get("optimizer_updates") != 0:
            raise RuntimeError("provider final receipt does not prove zero training")
        if replay.get("status") != "PASS_INDEPENDENT_INFERENCE_REPLAY_NO_PROMOTION" or replay.get("errors"):
            raise RuntimeError("independent replay did not pass")
        if float(environment["free_gib"]) < MINIMUM_FREE_GIB:
            raise RuntimeError("exact runner did not observe the unchanged storage gate")
        receipt["aggregate"] = {
            "status": final["status"],
            "training_occurred": final["training_occurred"],
            "optimizer_updates": final["optimizer_updates"],
            "provider_admitted_free_gib": final["provider_campaign"]["admitted_free_gib"],
            "independent_replay_status": replay["status"],
            "independent_replay_errors": replay["errors"],
            "max_metric_delta": replay["max_metric_delta"],
            "aggregate_comparison_delta": replay["aggregate_comparison_delta"],
            "aggregate_paired_delta": replay["aggregate_paired_delta"],
            "model_count": len(replay["model_receipts"]),
        }
        receipt["success"] = True
    except Exception as exc:
        receipt["error"] = safe_error(exc)
    finally:
        if sandbox is not None:
            try:
                sandbox.delete()
                receipt["deleted"] = True
            except Exception as exc:
                receipt["delete_error"] = safe_error(exc)
                try:
                    sandbox.stop()
                    receipt["stopped_after_delete_failure"] = True
                except Exception as stop_exc:
                    receipt["stop_error"] = safe_error(stop_exc)
        receipt["finished_at_utc"] = utc_now()
        write_json(receipt_path, receipt)

    print(
        json.dumps(
            {
                "success": receipt["success"],
                "deleted": receipt["deleted"],
                "sandbox_id": receipt.get("sandbox_id"),
                "free_gib": receipt.get("capacity", {}).get("free_gib"),
                "receipt": str(receipt_path),
                "error_type": receipt.get("error", {}).get("type"),
            },
            sort_keys=True,
        )
    )
    return 0 if receipt["success"] and receipt["deleted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
