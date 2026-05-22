"""Non-destructive coding probes for generated command candidates."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class Observation:
    """Mechanical probe result for a coding command."""

    mode: str
    ran: bool
    dry_run: bool
    legal: bool
    argv: list[str] = field(default_factory=list)
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_workspace(workspace: Path | None) -> Path:
    return (workspace or Path.cwd()).expanduser().resolve()


def _path_within(path: Path, workspace: Path) -> bool:
    resolved = path.expanduser().resolve()
    return resolved == workspace or workspace in resolved.parents


def _normalize_argv(argv: Sequence[str]) -> list[str]:
    return [str(part) for part in argv if str(part)]


def _py_compile_files(argv: list[str]) -> list[str]:
    if len(argv) >= 3 and Path(argv[0]).name.lower() in {"python", "python.exe", "py", "py.exe"}:
        if argv[1:3] == ["-m", "py_compile"]:
            return argv[3:]
    if len(argv) >= 2 and argv[0] == "py_compile":
        return argv[1:]
    return []


def _is_pytest_command(argv: list[str]) -> bool:
    if not argv:
        return False
    head = Path(argv[0]).name.lower()
    if head in {"pytest", "pytest.exe"}:
        return True
    return len(argv) >= 3 and head in {"python", "python.exe", "py", "py.exe"} and argv[1:3] == ["-m", "pytest"]


def _run(argv: list[str], *, cwd: Path, timeout: float) -> Observation:
    proc = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return Observation(
        mode="subprocess",
        ran=True,
        dry_run=True,
        legal=proc.returncode == 0,
        argv=argv,
        returncode=proc.returncode,
        stdout=proc.stdout[-4000:],
        stderr=proc.stderr[-4000:],
        reason="probe command completed",
    )


def probe_command(argv: Sequence[str], workspace: Path | None = None, *, timeout: float = 30.0) -> Observation:
    """Probe a coding command without committing side effects.

    Supported first slice:
    - Python compile checks via ``python -m py_compile <files>``.
    - Pytest collection via ``pytest --collect-only``.
    - fs write/delete shapes return a would-write observation without executing.
    """

    normalized = _normalize_argv(argv)
    if not normalized:
        return Observation(mode="empty", ran=False, dry_run=True, legal=False, reason="empty command")

    ws = _resolve_workspace(workspace)
    joined = " ".join(normalized).lower()
    if joined.startswith("fs.write") or joined.startswith("fs.delete"):
        return Observation(
            mode="would_write", ran=False, dry_run=True, legal=False, argv=normalized, reason="write/delete op"
        )

    compile_files = _py_compile_files(normalized)
    if compile_files:
        for file_name in compile_files:
            file_path = Path(file_name)
            if not file_path.is_absolute():
                file_path = ws / file_path
            if not _path_within(file_path, ws):
                return Observation(
                    mode="py_compile",
                    ran=False,
                    dry_run=True,
                    legal=False,
                    argv=normalized,
                    reason=f"source outside workspace: {file_name}",
                )
        run_argv = [sys.executable, "-m", "py_compile", *compile_files]
        result = _run(run_argv, cwd=ws, timeout=timeout)
        return Observation(**{**result.to_dict(), "mode": "py_compile"})

    if _is_pytest_command(normalized):
        probe_argv = list(normalized)
        if "--collect-only" not in probe_argv:
            probe_argv.append("--collect-only")
        result = _run(probe_argv, cwd=ws, timeout=timeout)
        return Observation(**{**result.to_dict(), "mode": "pytest_collect"})

    return Observation(
        mode="unsupported",
        ran=False,
        dry_run=True,
        legal=False,
        argv=normalized,
        reason="no non-destructive probe registered for command",
    )
