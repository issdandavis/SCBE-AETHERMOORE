"""Fail-closed restart guard for one frozen multi-view training campaign.

The supervisor never trains, edits checkpoints, changes campaign parameters,
dispatches cloud work, or grants promotion authority.  It verifies the pinned
campaign contract and the trainer's atomic checkpoint pointers, observes the
exact producer command, and relaunches that same hidden command only after the
producer is absent on two checks and the original storage gate still passes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any

SCHEMA = "clay.frozen-multiview-adapter-supervisor.v1"
MANIFEST_SCHEMA = "clay.frozen-multiview-adapter-campaign.v1.manifest"
POINTER_SCHEMA = "clay.frozen-multiview-adapter-campaign.v1.checkpoint-pointer"
AUTHORITY = {
    "training_parameters": "PINNED_EXISTING_CAMPAIGN_ONLY",
    "checkpoint_mutation": "NONE",
    "cloud_dispatch": "NONE",
    "execution": "NONE",
    "promotion": "NONE",
    "partial_unfreeze": "NONE",
}
TERMINAL_STATUSES = {
    "COMPLETE_RESULT_PRESENT_NO_RESTART",
    "INTEGRITY_BLOCKED_RESTART_NEEDS_REVIEW",
    "RESTART_LIMIT_REACHED_NEEDS_REVIEW",
}


class IntegrityError(RuntimeError):
    """Raised when an immutable restart prerequisite no longer matches."""


@dataclass(frozen=True)
class SupervisorContract:
    run_dir: Path
    run_manifest_sha256: str
    headless_config: Path
    headless_config_sha256: str
    headless_launcher: Path
    headless_launcher_sha256: str
    training_cli: Path
    training_cli_sha256: str
    status_output: Path
    lock_path: Path
    max_restarts: int = 3
    max_no_progress_restarts: int = 3
    grace_seconds: int = 30
    startup_seconds: int = 30

    def normalized(self) -> "SupervisorContract":
        return SupervisorContract(
            run_dir=self.run_dir.resolve(strict=True),
            run_manifest_sha256=_require_sha256(self.run_manifest_sha256),
            headless_config=self.headless_config.resolve(strict=True),
            headless_config_sha256=_require_sha256(self.headless_config_sha256),
            headless_launcher=self.headless_launcher.resolve(strict=True),
            headless_launcher_sha256=_require_sha256(self.headless_launcher_sha256),
            training_cli=self.training_cli.resolve(strict=True),
            training_cli_sha256=_require_sha256(self.training_cli_sha256),
            status_output=self.status_output.resolve(),
            lock_path=self.lock_path.resolve(),
            max_restarts=self.max_restarts,
            max_no_progress_restarts=self.max_no_progress_restarts,
            grace_seconds=self.grace_seconds,
            startup_seconds=self.startup_seconds,
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise IntegrityError(f"JSON object required: {path}")
    return value


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(pending, path)


def _require_sha256(value: str) -> str:
    normalized = str(value).lower()
    if len(normalized) != 64 or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        raise ValueError("expected a lowercase-or-uppercase SHA-256 digest")
    return normalized


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(os.path.abspath(str(left))) == os.path.normcase(
        os.path.abspath(str(right))
    )


def _argument_value(arguments: Sequence[str], flag: str) -> str:
    indexes = [index for index, value in enumerate(arguments) if value == flag]
    if len(indexes) != 1 or indexes[0] + 1 >= len(arguments):
        raise IntegrityError(f"headless command must contain exactly one {flag}")
    return arguments[indexes[0] + 1].strip('"')


def _contract_sha256(contract: SupervisorContract) -> str:
    return stable_sha256(
        {
            "run_dir": str(contract.run_dir),
            "run_manifest_sha256": contract.run_manifest_sha256,
            "headless_config": str(contract.headless_config),
            "headless_config_sha256": contract.headless_config_sha256,
            "headless_launcher": str(contract.headless_launcher),
            "headless_launcher_sha256": contract.headless_launcher_sha256,
            "training_cli": str(contract.training_cli),
            "training_cli_sha256": contract.training_cli_sha256,
            "max_restarts": contract.max_restarts,
            "max_no_progress_restarts": contract.max_no_progress_restarts,
        }
    )


def verify_contract(
    contract: SupervisorContract,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify every static file and argument that may authorize a restart."""

    if contract.max_restarts < 1 or contract.max_no_progress_restarts < 1:
        raise IntegrityError("restart limits must be positive")
    if contract.grace_seconds < 0 or contract.startup_seconds < 0:
        raise IntegrityError("restart timing bounds cannot be negative")

    manifest_path = contract.run_dir / "RUN_MANIFEST.json"
    if not manifest_path.is_file():
        raise IntegrityError(f"campaign manifest missing: {manifest_path}")
    if sha256_file(manifest_path) != contract.run_manifest_sha256:
        raise IntegrityError("campaign manifest hash differs from restart contract")
    manifest = read_json(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise IntegrityError("unexpected campaign manifest schema")

    for path_key, hash_key in (
        ("runner", "runner_sha256"),
        ("data_builder", "data_builder_sha256"),
        ("preregistration", "preregistration_sha256"),
    ):
        pinned_path = Path(str(manifest.get(path_key, ""))).resolve(strict=True)
        expected = _require_sha256(str(manifest.get(hash_key, "")))
        if sha256_file(pinned_path) != expected:
            raise IntegrityError(f"manifest-pinned {path_key} hash differs")

    static_files = (
        (contract.headless_config, contract.headless_config_sha256, "headless config"),
        (
            contract.headless_launcher,
            contract.headless_launcher_sha256,
            "headless launcher",
        ),
        (contract.training_cli, contract.training_cli_sha256, "training CLI"),
    )
    for path, expected, label in static_files:
        if sha256_file(path) != expected:
            raise IntegrityError(f"{label} hash differs from restart contract")

    headless = read_json(contract.headless_config)
    expected_keys = {"executable", "arguments", "working_directory", "log"}
    if set(headless) != expected_keys:
        raise IntegrityError("headless config fields differ from launcher contract")
    executable = Path(os.path.expandvars(str(headless["executable"]))).resolve(
        strict=True
    )
    if executable.name.casefold() not in {"python.exe", "python3.exe"}:
        raise IntegrityError(
            "headless trainer executable is not a Python console interpreter"
        )

    arguments = [
        value.strip('"')
        for value in shlex.split(str(headless["arguments"]), posix=False)
    ]
    script_arguments = [
        value for value in arguments if value.casefold().endswith(".py")
    ]
    if len(script_arguments) != 1 or not _same_path(
        script_arguments[0], contract.training_cli
    ):
        raise IntegrityError("headless command does not target the pinned training CLI")
    if not _same_path(_argument_value(arguments, "--output-dir"), contract.run_dir):
        raise IntegrityError("headless command output directory differs from campaign")
    if not _same_path(
        _argument_value(arguments, "--preregistration"), manifest["preregistration"]
    ):
        raise IntegrityError("headless command preregistration differs from manifest")
    config = manifest.get("config")
    if not isinstance(config, dict):
        raise IntegrityError("campaign config object missing")
    if not _same_path(_argument_value(arguments, "--source-dir"), config["source_dir"]):
        raise IntegrityError("headless command source directory differs from manifest")

    exact_values = {
        "--seeds": ",".join(str(value) for value in config["seeds"]),
        "--data-seed": str(config["data_seed"]),
        "--rows-per-view": str(config["rows_per_view"]),
        "--holdout-rows": str(config["holdout_rows"]),
        "--count-steps": str(config["count_steps"]),
        "--grow-steps": str(config["grow_steps"]),
        "--checkpoint-every": str(config["checkpoint_every"]),
        "--batch-size": str(config["batch_size"]),
        "--threads": str(config["threads"]),
    }
    for flag, expected in exact_values.items():
        if _argument_value(arguments, flag) != expected:
            raise IntegrityError(f"headless command {flag} differs from manifest")
    if float(_argument_value(arguments, "--learning-rate")) != float(
        config["learning_rate"]
    ):
        raise IntegrityError("headless command learning rate differs from manifest")
    if float(_argument_value(arguments, "--minimum-free-gib")) != float(
        manifest["minimum_free_gib"]
    ):
        raise IntegrityError("headless command storage gate differs from manifest")

    repo_root = contract.training_cli.parents[2]
    if not _same_path(headless["working_directory"], repo_root):
        raise IntegrityError(
            "headless command working directory differs from training repo"
        )
    return manifest, headless


def verify_checkpoint_pointers(run_dir: Path) -> dict[str, Any]:
    """Hash every active two-slot pointer without deserializing model state."""

    pointers: dict[str, dict[str, Any]] = {}
    for pointer_path in sorted(run_dir.rglob("latest.json")):
        pointer = read_json(pointer_path)
        if pointer.get("schema") != POINTER_SCHEMA:
            raise IntegrityError(
                f"unexpected checkpoint pointer schema: {pointer_path}"
            )
        slot_name = pointer.get("slot")
        if slot_name not in {"slot-a.pt", "slot-b.pt"}:
            raise IntegrityError(
                f"checkpoint pointer names an invalid slot: {pointer_path}"
            )
        expected = _require_sha256(str(pointer.get("sha256", "")))
        slot = pointer_path.parent / str(slot_name)
        if not slot.is_file() or sha256_file(slot) != expected:
            raise IntegrityError(
                f"checkpoint pointer does not match its slot: {pointer_path}"
            )
        generation = pointer.get("generation")
        step = pointer.get("step")
        if not isinstance(generation, int) or generation < 0:
            raise IntegrityError(f"invalid checkpoint generation: {pointer_path}")
        if not isinstance(step, int) or step < 0:
            raise IntegrityError(f"invalid checkpoint step: {pointer_path}")
        relative = pointer_path.relative_to(run_dir).as_posix()
        pointers[relative] = {
            "generation": generation,
            "step": step,
            "slot": slot_name,
            "sha256": expected,
            "pointer_sha256": sha256_file(pointer_path),
            "updated_at_utc": pointer.get("updated_at_utc"),
        }
    return {
        "pointer_count": len(pointers),
        "step_sum": sum(value["step"] for value in pointers.values()),
        "pointers": pointers,
        "pointers_sha256": stable_sha256(pointers),
    }


def progress_snapshot(run_dir: Path, checkpoints: Mapping[str, Any]) -> dict[str, Any]:
    terminal_paths = sorted(
        [*run_dir.glob("parents/*/RESULT.json"), *run_dir.glob("horses/*/RESULT.json")]
    )
    result_hashes = {
        path.relative_to(run_dir).as_posix(): sha256_file(path)
        for path in terminal_paths
    }
    payload = {
        "campaign_result_exists": (run_dir / "RESULT.json").is_file(),
        "terminal_result_count": len(terminal_paths),
        "terminal_result_hashes": result_hashes,
        "checkpoint_pointer_count": checkpoints["pointer_count"],
        "checkpoint_step_sum": checkpoints["step_sum"],
        "checkpoint_pointers_sha256": checkpoints["pointers_sha256"],
    }
    return {**payload, "signature_sha256": stable_sha256(payload)}


def _hidden_subprocess_options() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return {
        "creationflags": subprocess.CREATE_NO_WINDOW,
        "startupinfo": startup,
    }


def list_windows_python_processes() -> list[dict[str, Any]]:
    """Return command lines for Python processes without opening a console."""

    if os.name != "nt":
        raise RuntimeError("the frozen campaign supervisor currently targets Windows")
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        raise RuntimeError("PowerShell is required for exact Windows process matching")
    command = (
        "$ErrorActionPreference='Stop'; "
        "@(Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -in @('python.exe','python3.exe','pythonw.exe') } | "
        "Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine) | "
        "ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        **_hidden_subprocess_options(),
    )
    text = completed.stdout.strip()
    if not text:
        return []
    decoded = json.loads(text)
    rows = decoded if isinstance(decoded, list) else [decoded]
    return [dict(row) for row in rows if isinstance(row, dict)]


def matching_trainers(
    processes: Sequence[Mapping[str, Any]], contract: SupervisorContract
) -> list[dict[str, Any]]:
    script = os.path.normcase(str(contract.training_cli)).replace("/", "\\").casefold()
    run_dir = os.path.normcase(str(contract.run_dir)).replace("/", "\\").casefold()
    matches = []
    for row in processes:
        command = str(row.get("CommandLine") or "").replace("/", "\\").casefold()
        if script in command and "--output-dir" in command and run_dir in command:
            matches.append(
                {
                    "pid": int(row["ProcessId"]),
                    "parent_pid": int(row.get("ParentProcessId") or 0),
                    "executable": row.get("ExecutablePath"),
                }
            )
    return matches


def launch_exact_headless(contract: SupervisorContract) -> int:
    """Launch the already pinned run_headless config and return wrapper PID."""

    interpreter = Path(sys.executable).resolve()
    pythonw = interpreter.with_name("pythonw.exe") if os.name == "nt" else interpreter
    if not pythonw.is_file():
        raise FileNotFoundError(pythonw)
    process = subprocess.Popen(
        [
            str(pythonw),
            "-B",
            str(contract.headless_launcher),
            "--config",
            str(contract.headless_config),
        ],
        cwd=str(contract.headless_launcher.parent),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **_hidden_subprocess_options(),
    )
    return int(process.pid)


def _load_previous_state(
    contract: SupervisorContract, contract_sha256: str
) -> dict[str, Any]:
    if not contract.status_output.is_file():
        return {}
    try:
        state = read_json(contract.status_output)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    if state.get("schema") != SCHEMA or state.get("contract_sha256") != contract_sha256:
        return {}
    return state


def _base_state(
    contract: SupervisorContract,
    *,
    contract_sha256: str,
    status: str,
    previous: Mapping[str, Any],
    **fields: Any,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "authority": AUTHORITY,
        "run_dir": str(contract.run_dir),
        "contract_sha256": contract_sha256,
        "restart_count": int(previous.get("restart_count", 0)),
        "consecutive_no_progress_restarts": int(
            previous.get("consecutive_no_progress_restarts", 0)
        ),
        "last_restart_progress_signature": previous.get(
            "last_restart_progress_signature"
        ),
        "cloud_failover": "NOT_DISPATCHED_BY_LOCAL_RESTART_GUARD",
        **fields,
        "updated_at_utc": utc_now(),
    }


def _write_state(contract: SupervisorContract, state: dict[str, Any]) -> dict[str, Any]:
    atomic_json(contract.status_output, state)
    return state


def inspect_and_maybe_restart(
    contract: SupervisorContract,
    *,
    process_lister: Callable[[], list[dict[str, Any]]] = list_windows_python_processes,
    launcher: Callable[[SupervisorContract], int] = launch_exact_headless,
    free_bytes: Callable[[Path], int] | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Perform one bounded observation/recovery cycle."""

    normalized = contract.normalized()
    contract_sha256 = _contract_sha256(normalized)
    previous = _load_previous_state(normalized, contract_sha256)
    campaign_result = normalized.run_dir / "RESULT.json"
    if campaign_result.is_file():
        state = _base_state(
            normalized,
            contract_sha256=contract_sha256,
            status="COMPLETE_RESULT_PRESENT_NO_RESTART",
            previous=previous,
            campaign_result_sha256=sha256_file(campaign_result),
            claim_boundary=(
                "Atomic campaign result exists; this guard cannot relaunch, score, "
                "promote, merge, or unfreeze it."
            ),
        )
        return _write_state(normalized, state)

    try:
        manifest, _ = verify_contract(normalized)
        checkpoints = verify_checkpoint_pointers(normalized.run_dir)
        progress = progress_snapshot(normalized.run_dir, checkpoints)
    except Exception as error:
        state = _base_state(
            normalized,
            contract_sha256=contract_sha256,
            status="INTEGRITY_BLOCKED_RESTART_NEEDS_REVIEW",
            previous=previous,
            error_type=type(error).__name__,
            error_message=str(error),
            claim_boundary="No process was launched and no checkpoint was modified.",
        )
        return _write_state(normalized, state)

    matches = matching_trainers(process_lister(), normalized)
    if matches:
        state = _base_state(
            normalized,
            contract_sha256=contract_sha256,
            status="RUNNING_EXACT_PRODUCER",
            previous=previous,
            matching_trainers=matches,
            progress=progress,
            minimum_free_gib=float(manifest["minimum_free_gib"]),
            cloud_failover="LOCAL_ACTIVE_NOT_NEEDED",
            claim_boundary="Read-only observation; the active producer was not touched.",
        )
        return _write_state(normalized, state)

    grace_state = _base_state(
        normalized,
        contract_sha256=contract_sha256,
        status="TRAINER_MISSING_GRACE_RECHECK",
        previous=previous,
        progress=progress,
        grace_seconds=normalized.grace_seconds,
        claim_boundary="No launch before a second exact-process check.",
    )
    _write_state(normalized, grace_state)
    sleeper(float(normalized.grace_seconds))
    matches = matching_trainers(process_lister(), normalized)
    if matches:
        state = _base_state(
            normalized,
            contract_sha256=contract_sha256,
            status="RUNNING_EXACT_PRODUCER_AFTER_GRACE",
            previous=previous,
            matching_trainers=matches,
            progress=progress,
            minimum_free_gib=float(manifest["minimum_free_gib"]),
            cloud_failover="LOCAL_ACTIVE_NOT_NEEDED",
        )
        return _write_state(normalized, state)

    disk_free = (
        free_bytes(normalized.run_dir)
        if free_bytes is not None
        else shutil.disk_usage(normalized.run_dir.anchor).free
    )
    minimum_free_bytes = int(float(manifest["minimum_free_gib"]) * (1024**3))
    if disk_free < minimum_free_bytes:
        state = _base_state(
            normalized,
            contract_sha256=contract_sha256,
            status="STORAGE_GATE_BLOCKED_LOCAL_RESTART",
            previous=previous,
            progress=progress,
            free_bytes=disk_free,
            minimum_free_bytes=minimum_free_bytes,
            cloud_failover="ELIGIBLE_FOR_SEPARATE_PINNED_CLOUD_FAILOVER",
            claim_boundary=(
                "The original 25 GiB-class gate remains authoritative; this guard "
                "does not lower it or create an unpinned cloud duplicate."
            ),
        )
        return _write_state(normalized, state)

    restart_count = int(previous.get("restart_count", 0))
    no_progress = int(previous.get("consecutive_no_progress_restarts", 0))
    prior_signature = previous.get("last_restart_progress_signature")
    current_signature = progress["signature_sha256"]
    if restart_count and prior_signature == current_signature:
        no_progress += 1
    else:
        no_progress = 0
    if (
        restart_count >= normalized.max_restarts
        or no_progress >= normalized.max_no_progress_restarts
    ):
        state = _base_state(
            normalized,
            contract_sha256=contract_sha256,
            status="RESTART_LIMIT_REACHED_NEEDS_REVIEW",
            previous=previous,
            restart_count=restart_count,
            consecutive_no_progress_restarts=no_progress,
            progress=progress,
            free_bytes=disk_free,
            minimum_free_bytes=minimum_free_bytes,
            cloud_failover="ELIGIBLE_FOR_SEPARATE_PINNED_CLOUD_FAILOVER",
            claim_boundary="No further local process was launched.",
        )
        return _write_state(normalized, state)

    wrapper_pid = launcher(normalized)
    restart_count += 1
    deadline = time.monotonic() + normalized.startup_seconds
    matches = []
    while True:
        matches = matching_trainers(process_lister(), normalized)
        if matches or time.monotonic() >= deadline:
            break
        sleeper(1.0)
    status = (
        "RUNNING_AFTER_EXACT_RESTART"
        if matches
        else "RESTART_LAUNCHED_NOT_YET_OBSERVED"
    )
    state = _base_state(
        normalized,
        contract_sha256=contract_sha256,
        status=status,
        previous=previous,
        restart_count=restart_count,
        consecutive_no_progress_restarts=no_progress,
        last_restart_progress_signature=current_signature,
        wrapper_pid=wrapper_pid,
        matching_trainers=matches,
        progress=progress,
        free_bytes=disk_free,
        minimum_free_bytes=minimum_free_bytes,
        cloud_failover="LOCAL_RESTART_ATTEMPTED",
        claim_boundary=(
            "Only the hash-pinned original headless command was launched; campaign "
            "parameters and checkpoints were not changed."
        ),
    )
    return _write_state(normalized, state)


class ProcessLock:
    """A held one-byte OS lock; stale lock files are safe after process exit."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.stream: Any | None = None

    def __enter__(self) -> "ProcessLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        self.stream.seek(0, os.SEEK_END)
        if self.stream.tell() == 0:
            self.stream.write(b"0")
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close()
            self.stream = None
            raise RuntimeError("another supervisor holds the campaign lock") from error
        return self

    def __exit__(self, *args: Any) -> None:
        if self.stream is None:
            return
        self.stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        self.stream.close()
        self.stream = None


def watch(
    contract: SupervisorContract,
    *,
    poll_seconds: int = 300,
    once: bool = False,
) -> int:
    if poll_seconds < 60:
        raise ValueError("poll_seconds must be at least 60")
    normalized = contract.normalized()
    with ProcessLock(normalized.lock_path):
        while True:
            state = inspect_and_maybe_restart(normalized)
            print(
                json.dumps(
                    {
                        "status": state["status"],
                        "restart_count": state["restart_count"],
                        "terminal_result_count": state.get("progress", {}).get(
                            "terminal_result_count"
                        ),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            if once:
                return (
                    1
                    if state["status"]
                    in TERMINAL_STATUSES - {"COMPLETE_RESULT_PRESENT_NO_RESTART"}
                    else 0
                )
            if state["status"] in TERMINAL_STATUSES:
                return (
                    0 if state["status"] == "COMPLETE_RESULT_PRESENT_NO_RESTART" else 1
                )
            time.sleep(poll_seconds)
