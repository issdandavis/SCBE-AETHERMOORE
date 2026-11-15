"""Fail-closed continuity watchdog for the byte-embedding thaw campaign.

This process is deliberately not a trainer or evaluator.  It observes only
process identity, file hashes, disk capacity, the atomic final-result path,
and two-slot checkpoint pointer metadata.  It never loads a checkpoint and it
never reads partial or final evaluation metrics.

While either the exact successor gate or exact campaign child is alive, the
watchdog is read-only.  A single headless gate relaunch can occur only after
two separated observations find both processes absent and every static,
storage, checkpoint, and result gate still passes.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


SCHEMA = "clay.byte-embedding-thaw-continuity-watch.v1"
POINTER_SCHEMA = "clay.frozen-multiview-adapter-campaign.v1.checkpoint-pointer"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(pending, path)


def _norm(value: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(value))).replace("/", "\\")


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_contract(path: Path, expected_sha256: str) -> dict[str, Any]:
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise RuntimeError(
            f"continuity contract hash differs: expected {expected_sha256}, got {actual}"
        )
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("schema") != f"{SCHEMA}.contract":
        raise RuntimeError("continuity contract schema differs")
    if int(contract.get("maximum_relaunches", -1)) != 1:
        raise RuntimeError("continuity contract must authorize exactly one relaunch")
    if float(contract.get("minimum_free_gib", 0.0)) < 25.0:
        raise RuntimeError("continuity contract disk floor is below 25 GiB")
    return contract


def validate_static_bindings(contract: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    observed: dict[str, Any] = {}
    bindings = contract.get("bindings")
    if not isinstance(bindings, Mapping):
        return {"valid": False, "errors": ["bindings are missing"], "observed": {}}
    for name, raw in bindings.items():
        if not isinstance(raw, Mapping):
            errors.append(f"{name}: binding is not an object")
            continue
        path = Path(str(raw.get("path", "")))
        expected = str(raw.get("sha256", ""))
        if not path.is_file():
            errors.append(f"{name}: file missing")
            observed[str(name)] = {"path": str(path), "sha256": None}
            continue
        actual = file_sha256(path)
        observed[str(name)] = {"path": str(path), "sha256": actual}
        if actual != expected:
            errors.append(f"{name}: sha256 differs")

    manifest_binding = bindings.get("run_manifest")
    if isinstance(manifest_binding, Mapping):
        manifest_path = Path(str(manifest_binding.get("path", "")))
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"run_manifest: {type(error).__name__}")
        else:
            comparisons = {
                "runner": "campaign_runner",
                "thaw_module": "thaw_module",
                "preregistration": "preregistration",
            }
            for manifest_key, binding_key in comparisons.items():
                binding = bindings.get(binding_key)
                if not isinstance(binding, Mapping):
                    errors.append(f"{binding_key}: binding missing")
                    continue
                if _norm(str(manifest.get(manifest_key, ""))) != _norm(
                    str(binding.get("path", ""))
                ):
                    errors.append(f"run_manifest: {manifest_key} path differs")
                if manifest.get(f"{manifest_key}_sha256") != binding.get("sha256"):
                    errors.append(f"run_manifest: {manifest_key} sha256 differs")
    return {"valid": not errors, "errors": errors, "observed": observed}


def checkpoint_snapshot(run_dir: Path, manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Verify pointer metadata and raw slot hashes without loading model data."""

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    horses = run_dir / "horses"
    pointers = sorted(horses.glob("*/checkpoints/latest.json")) if horses.is_dir() else []
    expected_horses: set[str] | None = None
    checkpoint_every: int | None = None
    if manifest is not None:
        config = manifest.get("config", {})
        arms = config.get("arms", []) if isinstance(config, Mapping) else []
        seeds = config.get("seeds", []) if isinstance(config, Mapping) else []
        expected_horses = {
            f"{arm}-seed-{seed}" for arm in arms for seed in seeds
        }
        checkpoint_every = int(config.get("checkpoint_every", 0))
    for pointer_path in pointers:
        relative = pointer_path.relative_to(run_dir).as_posix()
        horse_name = pointer_path.parents[1].name
        if expected_horses is not None and horse_name not in expected_horses:
            errors.append(f"{relative}: horse is not declared by manifest")
        try:
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{relative}: {type(error).__name__}")
            continue
        slot_name = pointer.get("slot")
        generation = pointer.get("generation")
        step = pointer.get("step")
        declared_hash = pointer.get("sha256")
        if pointer.get("schema") != POINTER_SCHEMA:
            errors.append(f"{relative}: schema differs")
        if not isinstance(generation, int) or generation < 0:
            errors.append(f"{relative}: invalid generation")
            continue
        expected_slot = "slot-a.pt" if generation % 2 == 0 else "slot-b.pt"
        if slot_name != expected_slot:
            errors.append(f"{relative}: generation/slot alternation differs")
        if not isinstance(step, int) or step < 0:
            errors.append(f"{relative}: invalid step")
        elif checkpoint_every and step != (generation + 1) * checkpoint_every:
            errors.append(f"{relative}: generation/step cadence differs")
        if slot_name not in {"slot-a.pt", "slot-b.pt"}:
            errors.append(f"{relative}: invalid slot")
            continue
        slot_path = pointer_path.parent / slot_name
        if not slot_path.is_file():
            errors.append(f"{relative}: pointed slot missing")
            actual_hash = None
        else:
            actual_hash = file_sha256(slot_path)
            if actual_hash != declared_hash:
                errors.append(f"{relative}: pointed slot sha256 differs")
        records.append(
            {
                "pointer": relative,
                "pointer_sha256": file_sha256(pointer_path),
                "slot": slot_name,
                "slot_sha256": actual_hash,
                "generation": generation,
                "step": step,
                "updated_at_utc": pointer.get("updated_at_utc"),
            }
        )
    progress = [
        {
            "pointer": row["pointer"],
            "generation": row["generation"],
            "step": row["step"],
            "slot_sha256": row["slot_sha256"],
        }
        for row in records
    ]
    return {
        "valid": not errors,
        "errors": errors,
        "pointer_count": len(records),
        "records": records,
        "progress_signature": canonical_sha256(progress),
        "total_checkpoint_steps": sum(
            int(row["step"]) for row in records if isinstance(row["step"], int)
        ),
    }


def _command_argv(command_line: str) -> list[str]:
    if os.name != "nt":
        import shlex

        return shlex.split(command_line)
    import ctypes
    from ctypes import wintypes

    count = ctypes.c_int()
    command_line_to_argv = ctypes.windll.shell32.CommandLineToArgvW
    command_line_to_argv.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    command_line_to_argv.restype = ctypes.POINTER(wintypes.LPWSTR)
    argv = command_line_to_argv(command_line, ctypes.byref(count))
    if not argv:
        raise OSError("CommandLineToArgvW failed")
    try:
        return [argv[index] for index in range(count.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)


def list_python_processes() -> list[dict[str, Any]]:
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object {$_.Name -in @('python.exe','pythonw.exe')} | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        creationflags=flags,
    )
    if not completed.stdout.strip():
        return []
    raw = json.loads(completed.stdout)
    rows = raw if isinstance(raw, list) else [raw]
    return [
        {
            "pid": int(row["ProcessId"]),
            "parent_pid": int(row["ParentProcessId"]),
            "name": str(row.get("Name") or ""),
            "executable": str(row.get("ExecutablePath") or ""),
            "command_line": str(row.get("CommandLine") or ""),
            "argv": _command_argv(str(row.get("CommandLine") or "")),
        }
        for row in rows
        if row.get("CommandLine")
    ]


def process_matches(process: Mapping[str, Any], identity: Mapping[str, Any]) -> bool:
    names = {str(value).lower() for value in identity.get("executable_names", [])}
    if str(process.get("name", "")).lower() not in names:
        return False
    argv = [str(value) for value in process.get("argv", [])]
    if len(argv) < 2:
        return False
    script_aliases = {_norm(str(value)) for value in identity.get("script_aliases", [])}
    script_matches = [value for value in argv[1:] if _norm(value) in script_aliases]
    if len(script_matches) != 1:
        return False
    pairs = identity.get("required_option_values", {})
    if not isinstance(pairs, Mapping):
        return False
    for option, expected in pairs.items():
        indices = [index for index, value in enumerate(argv) if value == option]
        if len(indices) != 1 or indices[0] + 1 >= len(argv):
            return False
        observed = argv[indices[0] + 1]
        if str(option).endswith(("-run", "-dir", "-script", "-registration", "-status", "-log")):
            if _norm(observed) != _norm(str(expected)):
                return False
        elif observed != str(expected):
            return False
    return True


def exact_process_state(
    processes: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]
) -> dict[str, Any]:
    identities = contract["process_identities"]
    parents = [
        row for row in processes if process_matches(row, identities["successor_gate"])
    ]
    children = [
        row for row in processes if process_matches(row, identities["campaign_child"])
    ]
    wrappers = [
        row for row in processes if process_matches(row, identities["recovery_wrapper"])
    ]
    errors: list[str] = []
    if len(parents) > 1:
        errors.append("multiple exact successor-gate processes")
    if len(children) > 1:
        errors.append("multiple exact campaign-child processes")
    if len(wrappers) > 1:
        errors.append("multiple exact recovery-wrapper processes")
    return {
        "valid": not errors,
        "errors": errors,
        "parent_pids": [int(row["pid"]) for row in parents],
        "child_pids": [int(row["pid"]) for row in children],
        "parent_present": bool(parents),
        "child_present": bool(children),
        "wrapper_pids": [int(row["pid"]) for row in wrappers],
        "wrapper_present": bool(wrappers),
    }


def relaunch_eligibility(
    *,
    first_process_state: Mapping[str, Any],
    second_process_state: Mapping[str, Any],
    result_exists: bool,
    static_valid: bool,
    checkpoint_valid: bool,
    free_bytes: int,
    minimum_free_bytes: int,
    relaunch_count: int,
    maximum_relaunches: int,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for label, state in (("first", first_process_state), ("second", second_process_state)):
        if not state.get("valid"):
            reasons.append(f"{label} process identity invalid")
        if (
            state.get("parent_present")
            or state.get("child_present")
            or state.get("wrapper_present")
        ):
            reasons.append(f"{label} poll found an exact process")
    if result_exists:
        reasons.append("atomic result exists")
    if not static_valid:
        reasons.append("static binding gate failed")
    if not checkpoint_valid:
        reasons.append("checkpoint gate failed")
    if free_bytes < minimum_free_bytes:
        reasons.append("disk floor failed")
    if relaunch_count >= maximum_relaunches:
        reasons.append("single relaunch authority exhausted")
    return not reasons, reasons


def _load_previous_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if value.get("schema") == SCHEMA else {}


def _write_status(
    path: Path,
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    state: str,
    static: Mapping[str, Any],
    checkpoints: Mapping[str, Any],
    processes: Mapping[str, Any],
    free_bytes: int,
    relaunch_count: int,
    previous: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    prior_signature = previous.get("progress_signature")
    signature = checkpoints.get("progress_signature")
    progress_changed = signature != prior_signature
    last_progress = (
        now.isoformat()
        if progress_changed or not previous.get("last_progress_at_utc")
        else previous.get("last_progress_at_utc")
    )
    last_progress_dt = _parse_utc(last_progress) or now
    heartbeat_age_seconds = max(0.0, (now - last_progress_dt).total_seconds())
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "status": state,
        "updated_at_utc": now.isoformat(),
        "authority": "CONTINUITY_ONLY_NO_EVALUATION_NO_KILL_NO_PROMOTION",
        "contract_sha256": contract_sha256,
        "run_dir": contract["run_dir"],
        "atomic_result": contract["atomic_result"],
        "atomic_result_exists": Path(contract["atomic_result"]).is_file(),
        "minimum_free_bytes": int(float(contract["minimum_free_gib"]) * 1024**3),
        "free_bytes": free_bytes,
        "storage_gate_passed": free_bytes
        >= int(float(contract["minimum_free_gib"]) * 1024**3),
        "static_bindings_valid": bool(static.get("valid")),
        "static_binding_errors": list(static.get("errors", [])),
        "checkpoint_pointer_slot_hash_valid": bool(checkpoints.get("valid")),
        "checkpoint_errors": list(checkpoints.get("errors", [])),
        "checkpoint_pointer_count": int(checkpoints.get("pointer_count", 0)),
        "total_checkpoint_steps": int(checkpoints.get("total_checkpoint_steps", 0)),
        "progress_signature": signature,
        "progress_changed": progress_changed,
        "last_progress_at_utc": last_progress,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "heartbeat_timeout_seconds": int(contract["heartbeat_timeout_seconds"]),
        "parent_present": bool(processes.get("parent_present")),
        "parent_pids": list(processes.get("parent_pids", [])),
        "child_present": bool(processes.get("child_present")),
        "child_pids": list(processes.get("child_pids", [])),
        "recovery_wrapper_present": bool(processes.get("wrapper_present")),
        "recovery_wrapper_pids": list(processes.get("wrapper_pids", [])),
        "process_identity_valid": bool(processes.get("valid")),
        "process_identity_errors": list(processes.get("errors", [])),
        "relaunch_count": relaunch_count,
        "maximum_relaunches": int(contract["maximum_relaunches"]),
        "never_kill": True,
        "evaluation_metrics_read": False,
    }
    if extra:
        payload.update(extra)
    atomic_json(path, payload)
    return payload


def _launch_headless_recovery(contract: Mapping[str, Any]) -> int:
    pythonw = Path(sys.executable)
    if pythonw.name.lower() != "pythonw.exe":
        pythonw = pythonw.with_name("pythonw.exe")
    launcher = Path(contract["bindings"]["headless_launcher"]["path"])
    recovery_config = Path(contract["bindings"]["relaunch_config"]["path"])
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    child = subprocess.Popen(
        [str(pythonw), str(launcher), "--config", str(recovery_config)],
        cwd=str(launcher.parent),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        close_fds=True,
    )
    return int(child.pid)


def _acquire_singleton_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            raise RuntimeError("another continuity watchdog holds the lock")
    return handle


def run(contract: Mapping[str, Any], contract_sha256: str) -> int:
    run_dir = Path(contract["run_dir"])
    result_path = Path(contract["atomic_result"])
    status_path = Path(contract["status_path"])
    lock_handle = _acquire_singleton_lock(Path(contract["lock_path"]))
    minimum_free_bytes = int(float(contract["minimum_free_gib"]) * 1024**3)
    poll_seconds = int(contract["poll_seconds"])
    absence_recheck_seconds = int(contract["absence_recheck_seconds"])
    maximum_relaunches = int(contract["maximum_relaunches"])
    previous = _load_previous_status(status_path)
    relaunch_count = int(previous.get("relaunch_count", 0))
    try:
        while True:
            static = validate_static_bindings(contract)
            manifest = json.loads(
                Path(contract["bindings"]["run_manifest"]["path"]).read_text(
                    encoding="utf-8"
                )
            )
            checkpoints = checkpoint_snapshot(run_dir, manifest)
            processes = exact_process_state(list_python_processes(), contract)
            free_bytes = shutil.disk_usage(run_dir.anchor or "C:/").free

            if result_path.is_file():
                _write_status(
                    status_path,
                    contract=contract,
                    contract_sha256=contract_sha256,
                    state="COMPLETE_ATOMIC_RESULT_PRESENT_NO_RELAUNCH",
                    static=static,
                    checkpoints=checkpoints,
                    processes=processes,
                    free_bytes=free_bytes,
                    relaunch_count=relaunch_count,
                    previous=previous,
                )
                return 0

            if (
                processes["parent_present"]
                or processes["child_present"]
                or processes["wrapper_present"]
            ):
                if processes["parent_present"] and processes["child_present"]:
                    state = "RUNNING_EXACT_PARENT_AND_CHILD_READ_ONLY"
                elif processes["parent_present"]:
                    state = "PARENT_PRESENT_CHILD_ABSENT_READ_ONLY"
                elif processes["wrapper_present"]:
                    state = "EXACT_RECOVERY_WRAPPER_PRESENT_READ_ONLY"
                else:
                    state = "CHILD_PRESENT_PARENT_ABSENT_READ_ONLY"
                payload = _write_status(
                    status_path,
                    contract=contract,
                    contract_sha256=contract_sha256,
                    state=state,
                    static=static,
                    checkpoints=checkpoints,
                    processes=processes,
                    free_bytes=free_bytes,
                    relaunch_count=relaunch_count,
                    previous=previous,
                )
                if (
                    processes["child_present"]
                    and payload["heartbeat_age_seconds"]
                    > int(contract["heartbeat_timeout_seconds"])
                ):
                    payload["status"] = "RUNNING_STALE_HEARTBEAT_ALERT_NO_KILL"
                    atomic_json(status_path, payload)
                previous = payload
                time.sleep(poll_seconds)
                continue

            first_payload = _write_status(
                status_path,
                contract=contract,
                contract_sha256=contract_sha256,
                state="FIRST_EXACT_ABSENCE_OBSERVED_WAITING_FOR_SECOND_POLL",
                static=static,
                checkpoints=checkpoints,
                processes=processes,
                free_bytes=free_bytes,
                relaunch_count=relaunch_count,
                previous=previous,
                extra={"existing_retry_authority_present": False},
            )
            previous = first_payload
            time.sleep(absence_recheck_seconds)

            static_second = validate_static_bindings(contract)
            checkpoints_second = checkpoint_snapshot(run_dir, manifest)
            processes_second = exact_process_state(list_python_processes(), contract)
            free_second = shutil.disk_usage(run_dir.anchor or "C:/").free
            eligible, reasons = relaunch_eligibility(
                first_process_state=processes,
                second_process_state=processes_second,
                result_exists=result_path.is_file(),
                static_valid=bool(static_second["valid"]),
                checkpoint_valid=bool(checkpoints_second["valid"]),
                free_bytes=free_second,
                minimum_free_bytes=minimum_free_bytes,
                relaunch_count=relaunch_count,
                maximum_relaunches=maximum_relaunches,
            )
            if not eligible:
                payload = _write_status(
                    status_path,
                    contract=contract,
                    contract_sha256=contract_sha256,
                    state="RELAUNCH_BLOCKED_FAIL_CLOSED",
                    static=static_second,
                    checkpoints=checkpoints_second,
                    processes=processes_second,
                    free_bytes=free_second,
                    relaunch_count=relaunch_count,
                    previous=previous,
                    extra={"relaunch_block_reasons": reasons},
                )
                previous = payload
                if result_path.is_file():
                    return 0
                time.sleep(poll_seconds)
                continue

            relaunch_count += 1
            previous = _write_status(
                status_path,
                contract=contract,
                contract_sha256=contract_sha256,
                state="ONE_RELAUNCH_AUTHORITY_CONSUMED_LAUNCH_PENDING",
                static=static_second,
                checkpoints=checkpoints_second,
                processes=processes_second,
                free_bytes=free_second,
                relaunch_count=relaunch_count,
                previous=previous,
                extra={"second_absence_poll_passed": True},
            )
            try:
                recovery_pid = _launch_headless_recovery(contract)
            except Exception as error:
                payload = dict(previous)
                payload.update(
                    {
                        "status": "RELAUNCH_ATTEMPT_USED_LAUNCH_FAILED_NO_FURTHER_ACTION",
                        "updated_at_utc": utc_now(),
                        "relaunch_error": f"{type(error).__name__}: {error}",
                    }
                )
                atomic_json(status_path, payload)
                previous = payload
                time.sleep(poll_seconds)
                continue
            payload = dict(previous)
            payload.update(
                {
                    "status": "ONE_EXACT_HEADLESS_RELAUNCH_LAUNCHED",
                    "updated_at_utc": utc_now(),
                    "recovery_launcher_pid": recovery_pid,
                    "existing_retry_authority_present": False,
                }
            )
            atomic_json(status_path, payload)
            previous = payload
            time.sleep(poll_seconds)
    finally:
        lock_handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract_path = args.contract.resolve(strict=True)
    contract = load_contract(contract_path, args.contract_sha256)
    return run(contract, args.contract_sha256)


if __name__ == "__main__":
    raise SystemExit(main())
