"""SCBE agent-bus Python surface.

Routes AI/human/AI events through the SCBE governed event runner
(`scripts/scbe-system-cli.py agentbus run`) and returns a typed envelope
matching the `scbe-agentbus-pipe-result-v1` schema used by the Node sibling
package `scbe-agent-bus` on npm.

Usage:

    from scbe_agent_bus import run_event

    result = run_event({"task": "summarize repo state"}, repo_root="/path/to/repo")
    print(result["ok"], result["result"])

The `repo_root` must point at a checkout of issdandavis/SCBE-AETHERMOORE that
contains `scripts/scbe-system-cli.py`. If `repo_root` is omitted it defaults
to the current working directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal, Optional, TypedDict

from .companions import COMPANION_PACKAGES, recommend_companion_packages
from .lineage import (
    LINEAGE_SCHEMA,
    REPORT_SCHEMA,
    AuditHealth,
    FolderStat,
    LineageEntry,
    LineageKind,
    WorkspaceLineage,
    WorkspaceReport,
    has_unverified_exports,
    is_clean_chain,
    read_lineage,
    read_report,
)
from .workspace import (
    WorkspaceError,
    trap_dispatch,
    trap_dispatch_batch,
    trap_redirect,
    workspace_export,
    workspace_import,
    workspace_ingest,
    workspace_lineage,
    workspace_new,
    workspace_report,
    workspace_verify,
    workspace_verify_all,
)

__all__ = [
    "AgentBusEvent",
    "AgentBusResult",
    "RunnerOptions",
    "run_event",
    "run_batch",
    "AgentBusError",
    "COMPANION_PACKAGES",
    "recommend_companion_packages",
    # workspace audit chain
    "WorkspaceError",
    "workspace_new",
    "workspace_ingest",
    "workspace_export",
    "workspace_verify",
    "workspace_verify_all",
    "workspace_lineage",
    "workspace_report",
    "workspace_import",
    # trap-in-good-loops
    "trap_redirect",
    "trap_dispatch",
    "trap_dispatch_batch",
    # typed receipt readers
    "LineageEntry",
    "WorkspaceLineage",
    "FolderStat",
    "WorkspaceReport",
    "LineageKind",
    "AuditHealth",
    "LINEAGE_SCHEMA",
    "REPORT_SCHEMA",
    "read_lineage",
    "read_report",
    "has_unverified_exports",
    "is_clean_chain",
    "__version__",
]

__version__ = "0.3.0"

Privacy = Literal["local_only", "remote_ok"]
TaskType = Literal["coding", "review", "research", "governance", "training", "general"]


class AgentBusEvent(TypedDict, total=False):
    task: str
    operation_command: str
    task_type: TaskType
    series_id: str
    privacy: Privacy
    budget_cents: float
    dispatch: bool
    dispatch_provider: str


class AgentBusEventInfo(TypedDict):
    task_sha256: Optional[str]
    task_chars: int
    series_id: str
    operation_command_chars: int


class AgentBusResult(TypedDict):
    schema_version: Literal["scbe-agentbus-pipe-result-v1"]
    event_index: int
    started_at: str
    finished_at: str
    ok: bool
    exit_code: Optional[int]
    stderr_tail: str
    event: AgentBusEventInfo
    result: Any


class RunnerOptions(TypedDict, total=False):
    repo_root: str
    python: str
    continue_on_error: bool


class AgentBusError(RuntimeError):
    """Raised for malformed events or missing runner."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_event(event: AgentBusEvent | dict, index: int) -> dict:
    if not isinstance(event, dict):
        raise AgentBusError(f"event {index} must be a dict")
    task = str(event.get("task") or event.get("text") or "").strip()
    if not task:
        raise AgentBusError(f"event {index} missing task/text")
    return {
        "task": task,
        "operation_command": str(
            event.get("operation_command") or event.get("operationCommand") or ""
        ).strip(),
        "task_type": str(
            event.get("task_type") or event.get("taskType") or "general"
        ).strip(),
        "series_id": str(
            event.get("series_id") or event.get("seriesId") or f"pipe-event-{index}"
        ).strip(),
        "privacy": str(event.get("privacy") or "local_only").strip(),
        "budget_cents": float(
            event.get("budget_cents", event.get("budgetCents", 0)) or 0
        ),
        "dispatch": event.get("dispatch") is not False,
        "dispatch_provider": str(
            event.get("dispatch_provider") or event.get("dispatchProvider") or "offline"
        ).strip(),
    }


def _resolve_repo_root(repo_root: Optional[str]) -> Path:
    return Path(repo_root or os.getcwd()).resolve()


def _resolve_runner(repo_root: Path) -> Path:
    return repo_root / "scripts" / "scbe-system-cli.py"


def _run_one(
    normalized: dict,
    index: int,
    repo_root: Path,
    python: str,
) -> AgentBusResult:
    runner = _resolve_runner(repo_root)
    if not runner.exists():
        raise AgentBusError(
            f"agent-bus runner not found at {runner}. "
            "Pass repo_root pointing at a SCBE-AETHERMOORE checkout."
        )

    argv = [
        python,
        str(runner),
        "--repo-root",
        str(repo_root),
        "agentbus",
        "run",
        "--task",
        normalized["task"],
        "--task-type",
        normalized["task_type"],
        "--series-id",
        normalized["series_id"],
        "--privacy",
        normalized["privacy"],
        "--budget-cents",
        str(normalized["budget_cents"]),
        "--dispatch-provider",
        normalized["dispatch_provider"],
        "--json",
    ]
    if normalized["operation_command"]:
        argv += ["--operation-command", normalized["operation_command"]]
    if normalized["dispatch"]:
        argv.append("--dispatch")

    started_at = _now_iso()
    completed = subprocess.run(
        argv,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    finished_at = _now_iso()

    payload: Any = None
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        payload = None

    task_sha256 = None
    if isinstance(payload, dict):
        task = payload.get("task") if isinstance(payload.get("task"), dict) else None
        if isinstance(task, dict):
            sha = task.get("sha256")
            task_sha256 = str(sha) if isinstance(sha, str) else None

    return AgentBusResult(
        schema_version="scbe-agentbus-pipe-result-v1",
        event_index=index,
        started_at=started_at,
        finished_at=finished_at,
        ok=completed.returncode == 0 and bool(payload),
        exit_code=completed.returncode,
        stderr_tail=(completed.stderr or "")[-1000:],
        event=AgentBusEventInfo(
            task_sha256=task_sha256,
            task_chars=len(normalized["task"]),
            series_id=normalized["series_id"],
            operation_command_chars=len(normalized["operation_command"]),
        ),
        result=payload,
    )


def run_event(
    event: AgentBusEvent | dict,
    *,
    repo_root: Optional[str] = None,
    python: Optional[str] = None,
) -> AgentBusResult:
    """Run a single agent-bus event and return the typed envelope."""
    rows = run_batch([event], repo_root=repo_root, python=python)
    if not rows:
        raise AgentBusError("agent-bus runner returned no rows")
    return rows[0]


def run_batch(
    events: Iterable[AgentBusEvent | dict],
    *,
    repo_root: Optional[str] = None,
    python: Optional[str] = None,
    continue_on_error: bool = False,
) -> list[AgentBusResult]:
    """Run a batch of agent-bus events, in order, until error (unless continue_on_error)."""
    events_list = list(events)
    if not events_list:
        raise AgentBusError("events sequence is empty")
    repo_root_path = _resolve_repo_root(repo_root)
    py = python or os.environ.get("PYTHON") or sys.executable or "python"
    rows: list[AgentBusResult] = []
    for i, event in enumerate(events_list, start=1):
        normalized = _normalize_event(event, i)
        row = _run_one(normalized, i, repo_root_path, py)
        rows.append(row)
        if not row["ok"] and not continue_on_error:
            break
    return rows
