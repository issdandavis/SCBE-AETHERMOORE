"""Coding trial pipeline: legitimacy -> non-destructive probe -> JSON packet."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Literal, Sequence

from src.coding_board.probe import Observation, probe_command
from src.crypto.geoseal_legitimacy import CoarseLocation, run_legitimacy_trial


def _command_text_for_legitimacy(argv: list[str], workspace: Path | None) -> str:
    """Keep command-shape scanning, but do not treat the runtime exe as a touched source path."""

    if not argv:
        return ""
    normalized = list(argv)
    head = Path(normalized[0])
    if head.is_absolute():
        normalized[0] = head.name
    if workspace is not None:
        ws = workspace.expanduser().resolve()
        for idx, part in enumerate(normalized[1:], start=1):
            if part.startswith("-"):
                continue
            candidate = Path(part)
            if not candidate.is_absolute() and ("/" in part or "\\" in part):
                candidate = ws / candidate
            elif not candidate.is_absolute():
                continue
            try:
                resolved = candidate.expanduser().resolve()
            except OSError:
                continue
            if resolved == ws or ws in resolved.parents:
                normalized[idx] = str(resolved)
    return subprocess.list2cmdline(normalized)


def run_coding_trial(
    *,
    goal: str,
    command: Sequence[str],
    workspace: Path | None,
    origin: Literal["user", "agent", "workflow"] = "user",
    expected_tool: str = "terminal.command.request",
    expected_state: str = "unspecified",
    privacy: Literal["local_only", "hosted"] = "local_only",
    location: CoarseLocation | None = None,
    network_state: Literal["offline", "local", "online", "unknown"] = "unknown",
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Run the first coding harness loop without committing changes."""

    argv = [str(part) for part in command if str(part)]
    command_text = _command_text_for_legitimacy(argv, workspace)
    legitimacy = run_legitimacy_trial(
        goal=goal,
        expected_tool=expected_tool,
        origin=origin,
        expected_state=expected_state,
        privacy=privacy,
        command=command_text,
        workspace=workspace,
        location=location,
        network_state=network_state,
    )
    decision = legitimacy["decision"]["decision"]

    if decision == "DENY":
        observation = Observation(
            mode="skipped",
            ran=False,
            dry_run=True,
            legal=False,
            argv=argv,
            reason="legitimacy trial denied command",
        )
    else:
        observation = probe_command(argv, workspace=workspace, timeout=timeout)

    return {
        "schema_version": "scbe-coding-trial-v1",
        "goal": goal,
        "command": argv,
        "legitimacy": legitimacy,
        "probe": observation.to_dict(),
        "accepted": decision == "ALLOW_CLI" and observation.legal,
    }
