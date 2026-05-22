from __future__ import annotations

import time
from pathlib import Path

from .models import DecisionKind, OperationDecision, OperationRequest, ZoneKind

_DENY_OPS: frozenset[str] = frozenset(
    {"terminal.shell.raw", "os.exec", "fs.delete", "deploy.publish", "hardware.actuate"}
)

_ALLOW_OPS: frozenset[str] = frozenset(
    {"echo", "llm.chat", "metrics.read", "fs.read", "fs.list", "git.status", "time.read"}
)

_HIGH_RISK_OPS: frozenset[str] = frozenset(
    {"fs.write", "terminal.command.request", "browser.navigate", "web.search", "git.push"}
)


def govern(req: OperationRequest) -> OperationDecision:
    t0 = time.monotonic()
    decision, zone, reason, policy = _evaluate(req)
    return OperationDecision(
        request_id=req.request_id,
        decision=decision,
        zone=zone,
        reason=reason,
        policy=policy,
        latency_ms=(time.monotonic() - t0) * 1000,
    )


def _evaluate(req: OperationRequest) -> tuple[DecisionKind, ZoneKind, str, str]:
    op = req.op

    if op in _DENY_OPS:
        return "DENY", "RED", f"op '{op}' is in the deny list", "deny-ops-list"

    if op in _ALLOW_OPS:
        return "ALLOW", "GREEN", f"op '{op}' is in the allow list", "allow-ops-list"

    if op in _HIGH_RISK_OPS:
        if req.workspace is None:
            return (
                "QUARANTINE",
                "YELLOW",
                f"op '{op}' requires a workspace but none was provided",
                "high-risk-requires-workspace",
            )
        ws_path = Path(req.workspace.root)
        if not ws_path.exists():
            return (
                "DENY",
                "RED",
                f"workspace path does not exist: {req.workspace.root}",
                "workspace-not-found",
            )
        return "ALLOW", "GREEN", f"op '{op}' allowed with valid workspace", "high-risk-workspace-ok"

    return (
        "QUARANTINE",
        "YELLOW",
        f"op '{op}' is not in any known op set; quarantined pending review",
        "unknown-op",
    )
