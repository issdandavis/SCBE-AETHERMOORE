"""Safe repo-task routing for agentic coding loops.

This is the work-dispatch companion to ``copilot_router``. It turns a repo
maintenance request into an allowlisted command plan, seals each command with
GeoSeal, and can execute the plan without shell string interpolation.

The first lane is intentionally small: Python format/lint/compile checks. Other
tool families can be added by registering new command builders instead of
letting an LLM invent shell commands.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "scbe_repo_task_route_v1"
RepoTaskName = Literal["format", "lint", "verify", "format-lint"]
PYTHON_SUFFIXES = {".py"}
PYTHON_CMD = "python"


@dataclass(frozen=True)
class RepoTaskCommand:
    """One allowlisted command in a repo task route."""

    name: str
    argv: tuple[str, ...]
    mutates: bool
    paths: tuple[str, ...]
    expected_tool: str
    geoseal: dict[str, Any]

    @property
    def allowed(self) -> bool:
        return bool(self.geoseal["decision"]["allowed_cli"])

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["allowed"] = self.allowed
        return payload


@dataclass(frozen=True)
class RepoTaskRun:
    """Execution result for one command."""

    name: str
    argv: tuple[str, ...]
    returncode: int
    elapsed_ms: float
    stdout_tail: str
    stderr_tail: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["ok"] = self.ok
        return payload


@dataclass(frozen=True)
class RepoTaskRoute:
    """Plan plus optional execution results for a repo maintenance task."""

    schema: str
    task: RepoTaskName
    workspace: str
    paths: tuple[str, ...]
    commands: tuple[RepoTaskCommand, ...]
    executed: bool = False
    results: tuple[RepoTaskRun, ...] = ()

    @property
    def ok(self) -> bool:
        return all(command.allowed for command in self.commands) and all(
            result.ok for result in self.results
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "task": self.task,
            "workspace": self.workspace,
            "paths": list(self.paths),
            "commands": [command.to_dict() for command in self.commands],
            "executed": self.executed,
            "results": [result.to_dict() for result in self.results],
            "ok": self.ok,
        }


def build_repo_task_route(
    task: RepoTaskName,
    paths: Sequence[str | Path],
    *,
    workspace: Path = REPO_ROOT,
    delegated_origin: Literal["user", "workflow"] = "user",
) -> RepoTaskRoute:
    """Build a deterministic repo-task route for known-safe toolchains."""
    if task not in ("format", "lint", "verify", "format-lint"):
        raise ValueError(f"unsupported repo task: {task}")
    workspace = workspace.resolve()
    normalized = _normalize_paths(paths, workspace)
    if not normalized:
        raise ValueError("at least one path is required")

    python_paths = tuple(
        path for path in normalized if Path(path).suffix in PYTHON_SUFFIXES
    )
    if not python_paths:
        raise ValueError("repo-task route currently supports Python paths only")
    python_argv_paths = tuple(str(workspace / path) for path in python_paths)

    commands: list[RepoTaskCommand] = []
    if task in ("format", "format-lint"):
        commands.append(
            _command(
                name="python-black-format",
                argv=(
                    PYTHON_CMD,
                    "-m",
                    "black",
                    "--target-version",
                    "py314",
                    *python_argv_paths,
                ),
                mutates=True,
                rel_paths=python_paths,
                workspace=workspace,
                delegated_origin=delegated_origin,
            )
        )
    if task in ("lint", "format-lint"):
        commands.append(
            _command(
                name="python-flake8",
                argv=(PYTHON_CMD, "-m", "flake8", *python_argv_paths),
                mutates=False,
                rel_paths=python_paths,
                workspace=workspace,
                delegated_origin=delegated_origin,
            )
        )
    if task in ("verify", "format-lint"):
        commands.append(
            _command(
                name="python-py-compile",
                argv=(PYTHON_CMD, "-m", "py_compile", *python_argv_paths),
                mutates=False,
                rel_paths=python_paths,
                workspace=workspace,
                delegated_origin=delegated_origin,
            )
        )

    return RepoTaskRoute(
        schema=SCHEMA_VERSION,
        task=task,
        workspace=str(workspace),
        paths=normalized,
        commands=tuple(commands),
    )


def execute_repo_task_route(route: RepoTaskRoute) -> RepoTaskRoute:
    """Execute an already-built route if every command is GeoSeal-allowed."""
    blocked = [command.name for command in route.commands if not command.allowed]
    if blocked:
        raise ValueError(f"route has blocked commands: {', '.join(blocked)}")

    results: list[RepoTaskRun] = []
    for command in route.commands:
        start = time.perf_counter()
        completed = subprocess.run(
            list(command.argv),
            cwd=route.workspace,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        results.append(
            RepoTaskRun(
                name=command.name,
                argv=command.argv,
                returncode=completed.returncode,
                elapsed_ms=round(elapsed_ms, 3),
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
            )
        )
        if completed.returncode != 0:
            break
    return RepoTaskRoute(
        schema=route.schema,
        task=route.task,
        workspace=route.workspace,
        paths=route.paths,
        commands=route.commands,
        executed=True,
        results=tuple(results),
    )


def _command(
    *,
    name: str,
    argv: tuple[str, ...],
    mutates: bool,
    rel_paths: tuple[str, ...],
    workspace: Path,
    delegated_origin: Literal["user", "workflow"],
) -> RepoTaskCommand:
    _assert_allowlisted(argv)
    geoseal = _run_geoseal(
        goal=f"run repo task command {name}",
        expected_tool="fs.write" if mutates else "terminal.command.request",
        command=subprocess.list2cmdline(argv),
        workspace=workspace,
        origin=delegated_origin,
    )
    return RepoTaskCommand(
        name=name,
        argv=argv,
        mutates=mutates,
        paths=rel_paths,
        expected_tool="fs.write" if mutates else "terminal.command.request",
        geoseal=geoseal,
    )


def _normalize_paths(paths: Sequence[str | Path], workspace: Path) -> tuple[str, ...]:
    normalized: list[str] = []
    for path in paths:
        raw = Path(path)
        resolved = (
            (workspace / raw).resolve() if not raw.is_absolute() else raw.resolve()
        )
        if not (resolved == workspace or workspace in resolved.parents):
            raise ValueError(f"path escapes workspace: {path}")
        if not resolved.exists():
            raise ValueError(f"path does not exist: {path}")
        if resolved.is_dir():
            raise ValueError(f"path must be a file, not a directory: {path}")
        normalized.append(resolved.relative_to(workspace).as_posix())
    return tuple(dict.fromkeys(normalized))


def _assert_allowlisted(argv: Sequence[str]) -> None:
    if len(argv) < 3:
        raise ValueError("command is too short")
    if Path(argv[0]).name.lower() not in {"python.exe", "python"}:
        raise ValueError(f"command executable is not allowlisted: {argv[0]}")
    if argv[1] != "-m":
        raise ValueError("python command must use -m module form")
    module = argv[2]
    if module not in {"black", "flake8", "py_compile"}:
        raise ValueError(f"python module is not allowlisted: {module}")


def _run_geoseal(
    *,
    goal: str,
    expected_tool: str,
    command: str,
    workspace: Path,
    origin: Literal["user", "workflow"],
) -> dict[str, Any]:
    with contextlib.redirect_stdout(io.StringIO()):
        from src.crypto.geoseal_legitimacy import CoarseLocation, run_legitimacy_trial

    return run_legitimacy_trial(
        goal=goal,
        expected_tool=expected_tool,
        origin=origin,
        command=command,
        workspace=workspace,
        location=CoarseLocation(
            source="user_confirmed",
            label="delegated local repo maintenance",
            confidence=0.95,
        ),
        network_state="local",
    )


def _tail(text: str | None, *, max_chars: int = 1200) -> str:
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def route_to_json(route: RepoTaskRoute) -> str:
    return json.dumps(route.to_dict(), indent=2, sort_keys=True)


__all__ = [
    "REPO_ROOT",
    "SCHEMA_VERSION",
    "RepoTaskCommand",
    "RepoTaskRoute",
    "RepoTaskRun",
    "build_repo_task_route",
    "execute_repo_task_route",
    "route_to_json",
]
