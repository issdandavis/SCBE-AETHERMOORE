"""Hermes plugin: route every tool call through the SCBE governance seam.

This is the thin adapter between the Hermes harness and our engine-agnostic
`governance_seam.GovernanceSeam`. It uses Hermes' native `pre_tool_call` hook
(the intended, non-monkeypatch extension point — same shape as the bundled
`security-guidance` plugin) so governance runs BEFORE any tool executes and a
DENY blocks the tool, feeding the reason back to the model.

Install (vendored fork): copy this file + governance_seam.py into the harness'
plugins dir as `plugins/scbe-governance/__init__.py` (re-exporting `register`),
or point the plugin loader at this module. Enable receipts/stamps via env.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# The seam lives next to this file; make it importable regardless of how the
# plugin loader imports us (package, path, or vendored copy).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from governance_seam import GovernanceSeam  # noqa: E402

_SEAM: Optional[GovernanceSeam] = None


def _seam() -> GovernanceSeam:
    global _SEAM
    if _SEAM is None:
        _SEAM = GovernanceSeam(quarantine_blocks=_env_flag("AETHER_QUARANTINE_BLOCKS"))
    return _SEAM


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _on_pre_tool_call(tool_name: str = "", args: Any = None, **_: Any) -> Optional[Dict[str, str]]:
    """Governed gate. Returns a block directive on DENY, else None (allow)."""
    seam = _seam()
    decision = seam.govern(tool_name, args if isinstance(args, dict) else {})
    # Terminal receipt line (stderr so it doesn't pollute tool stdout/JSON).
    try:
        print(seam.stamp(decision), file=sys.stderr, flush=True)
    except Exception:
        pass
    if not decision.allowed:
        return {
            "action": "block",
            "message": (f"{decision.deny_message()} " f"[GeoSeal receipt {decision.receipt.get('audit_id')}]"),
        }
    return None


def register(ctx) -> None:
    """Hermes plugin entry point."""
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
