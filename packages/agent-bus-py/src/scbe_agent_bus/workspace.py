"""Workspace audit chain wrappers for scbe-agent-bus.

Thin Python surface over the `scbe-agent-bus workspace` and `scbe trap-*`
Node CLIs. Each call invokes the JSON-mode CLI and returns the parsed
envelope. Read-only consumers should use :mod:`scbe_agent_bus.lineage`
which parses the receipt JSON into typed dataclasses.

Requires `scbe-agent-bus` (npm) and/or `scbe-aethermoore-cli` (npm) on
PATH. Install via::

    npm i -g scbe-agent-bus scbe-aethermoore-cli

Or set ``SCBE_AGENT_BUS_BIN`` / ``SCBE_CLI_BIN`` to absolute binary paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, Optional


class WorkspaceError(RuntimeError):
    """Raised when a workspace CLI call fails or emits invalid JSON."""


def _resolve_bin(env_var: str, command: str) -> str:
    explicit = os.environ.get(env_var)
    if explicit:
        return explicit
    found = shutil.which(command) or shutil.which(f"{command}.cmd")
    if not found:
        raise WorkspaceError(
            f"`{command}` not on PATH. Install via `npm i -g {command}` "
            f"or set ${env_var} to the absolute binary path."
        )
    return found


def _agent_bus_bin() -> str:
    return _resolve_bin("SCBE_AGENT_BUS_BIN", "scbe-agent-bus")


def _scbe_bin() -> str:
    return _resolve_bin("SCBE_CLI_BIN", "scbe")


def _run_json(argv: list[str], stdin: Optional[str] = None, timeout: float = 60.0) -> dict:
    # On Windows, .cjs/.js files are not directly executable — must be run via `node`.
    # When the path was resolved via npm's PATH shim (.cmd) the OS handles this for us;
    # when it was set explicitly via $SCBE_*_BIN to the raw script, we wrap it.
    if argv and (argv[0].endswith(".cjs") or argv[0].endswith(".mjs") or argv[0].endswith(".js")):
        node = shutil.which("node") or shutil.which("node.exe") or "node"
        argv = [node, *argv]
    completed = subprocess.run(
        argv,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise WorkspaceError(
            f"{argv[0]} exited {completed.returncode}: {completed.stderr[-400:]}"
        )
    try:
        return json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise WorkspaceError(
            f"{argv[0]} did not emit valid JSON (exit {completed.returncode}): "
            f"{completed.stdout[:200]!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Workspace formation + audit chain
# ---------------------------------------------------------------------------


def workspace_new(hint: Optional[str] = None, root: Optional[str] = None) -> dict:
    """Form a new local bus workspace.

    Returns the `aethermoor.bus.workspace_receipt.v1` envelope with
    `workspace_root`, `workspace_id`, and `created_at`.
    """
    argv = [_agent_bus_bin(), "workspace", "new", "--json"]
    if hint:
        argv += ["--hint", hint]
    if root:
        argv += ["--root", root]
    return _run_json(argv)


def workspace_ingest(workspace_root: str, source_path: str, rename: Optional[str] = None) -> dict:
    """Copy a file into ``<workspace>/00_inbox/`` with a sha256 provenance receipt."""
    argv = [
        _agent_bus_bin(),
        "workspace",
        "ingest",
        "--workspace-root",
        workspace_root,
        "--source-path",
        source_path,
        "--json",
    ]
    if rename:
        argv += ["--rename", rename]
    return _run_json(argv)


def workspace_export(
    workspace_root: str,
    out: Optional[str] = None,
    include: Optional[Iterable[str]] = None,
) -> dict:
    """Export selected workspace folders into ``30_exports/<export-id>/`` with sha256 manifest."""
    argv = [_agent_bus_bin(), "workspace", "export", "--workspace-root", workspace_root, "--json"]
    if out:
        argv += ["--out", out]
    if include:
        argv += ["--include", ",".join(include)]
    return _run_json(argv)


def workspace_verify(export_path: str) -> dict:
    """Verify a single export against its manifest. Returns
    ``aethermoor.bus.workspace_verify.v1``."""
    return _run_json(
        [_agent_bus_bin(), "workspace", "verify", "--export-path", export_path, "--json"]
    )


def workspace_verify_all(workspace_root: str) -> dict:
    """Verify every export under ``<workspace>/30_exports/``. Returns
    ``aethermoor.bus.workspace_verify_all.v1``."""
    return _run_json(
        [
            _agent_bus_bin(),
            "workspace",
            "verify",
            "--all",
            "--workspace-root",
            workspace_root,
            "--json",
        ]
    )


def workspace_lineage(workspace_root: str) -> dict:
    """Walk ``<workspace>/20_receipts/`` and emit the chronological audit chain.

    Returns ``aethermoor.bus.workspace_lineage.v1`` with formation/ingest/
    export/verify/import/trap_dispatch counts and an
    ``unverified_exports[]`` list.
    """
    return _run_json(
        [
            _agent_bus_bin(),
            "workspace",
            "lineage",
            "--workspace-root",
            workspace_root,
            "--json",
        ]
    )


def workspace_report(workspace_root: str) -> dict:
    """Operator dashboard. Returns ``aethermoor.bus.workspace_report.v1``
    with folder file/byte counts, lineage summary, and ``audit_health``."""
    return _run_json(
        [
            _agent_bus_bin(),
            "workspace",
            "report",
            "--workspace-root",
            workspace_root,
            "--json",
        ]
    )


def workspace_import(
    export_path: str,
    target_root: Optional[str] = None,
    hint: Optional[str] = None,
) -> dict:
    """Cold-restore a workspace from a previously-exported manifest.

    Refuses any export that fails verification. Returns
    ``aethermoor.bus.workspace_import.v1``.
    """
    argv = [
        _agent_bus_bin(),
        "workspace",
        "import",
        "--export-path",
        export_path,
        "--json",
    ]
    if target_root:
        argv += ["--target-root", target_root]
    if hint:
        argv += ["--hint", hint]
    return _run_json(argv)


# ---------------------------------------------------------------------------
# Trap-in-good-loops dispatch surface
# ---------------------------------------------------------------------------


def trap_redirect(
    input_text: Optional[str] = None,
    file_path: Optional[str] = None,
    stdin_text: Optional[str] = None,
) -> dict:
    """Run the governance proxy preflight on input. Returns
    ``scbe.trap_redirect.v1`` with the defensive prompt that would be
    forwarded in place of attacker text (DENY) or pass-through (ALLOW)."""
    if not any((input_text, file_path, stdin_text)):
        raise WorkspaceError("trap_redirect requires input_text, file_path, or stdin_text")
    argv = [_scbe_bin(), "trap-redirect", "--json"]
    if input_text is not None:
        argv += ["--input", input_text]
    if file_path:
        argv += ["--file", file_path]
    return _run_json(argv, stdin=stdin_text)


def trap_dispatch(
    input_text: Optional[str] = None,
    *,
    file_path: Optional[str] = None,
    stdin_text: Optional[str] = None,
    provider: str = "offline",
    model: Optional[str] = None,
    ollama_url: Optional[str] = None,
    timeout_ms: Optional[int] = None,
    workspace_root: Optional[str] = None,
) -> dict:
    """Forward a prompt to a FREE local provider via the trap-in-good-loops gate.

    Paid provider names are rejected by the CLI parser with exit 2 — this
    surface never spends money. Default ``provider='offline'`` returns a
    deterministic echo (sha256 + bytes) with zero network calls. Use
    ``provider='ollama'`` for a local Ollama daemon.

    Returns ``scbe.trap_dispatch.v1``. When ``workspace_root`` is set, the
    envelope is also persisted as
    ``aethermoor.bus.workspace_trap_dispatch.v1`` under
    ``<workspace>/20_receipts/``.
    """
    if not any((input_text, file_path, stdin_text)):
        raise WorkspaceError("trap_dispatch requires input_text, file_path, or stdin_text")
    argv = [_scbe_bin(), "trap-dispatch", "--provider", provider, "--json"]
    if input_text is not None:
        argv += ["--input", input_text]
    if file_path:
        argv += ["--file", file_path]
    if model:
        argv += ["--model", model]
    if ollama_url:
        argv += ["--ollama-url", ollama_url]
    if timeout_ms is not None:
        argv += ["--timeout-ms", str(int(timeout_ms))]
    if workspace_root:
        argv += ["--workspace-root", workspace_root]
    return _run_json(argv, stdin=stdin_text)


def trap_dispatch_batch(
    batch_file: str,
    *,
    provider: str = "offline",
    model: Optional[str] = None,
    workspace_root: Optional[str] = None,
) -> dict:
    """Process a JSONL corpus through trap-dispatch in one pass.

    Each row is raw text or ``{"input":"...","tag":"..."}``. Returns
    ``scbe.trap_dispatch_batch.v1`` with ``dispatch_pass / dispatch_fail
    / redirect_emitted / deny / allow`` aggregates. Combines with
    ``workspace_root`` to persist one workspace receipt per row.
    """
    if not Path(batch_file).exists():
        raise WorkspaceError(f"batch file not found: {batch_file}")
    argv = [
        _scbe_bin(),
        "trap-dispatch",
        "--batch",
        batch_file,
        "--provider",
        provider,
        "--json",
    ]
    if model:
        argv += ["--model", model]
    if workspace_root:
        argv += ["--workspace-root", workspace_root]
    return _run_json(argv, timeout=600.0)


__all__ = [
    "WorkspaceError",
    "workspace_new",
    "workspace_ingest",
    "workspace_export",
    "workspace_verify",
    "workspace_verify_all",
    "workspace_lineage",
    "workspace_report",
    "workspace_import",
    "trap_redirect",
    "trap_dispatch",
    "trap_dispatch_batch",
]
