"""Governance seam — route every harness tool call through the SCBE gate.

This is the one load-bearing module of the Aether harness (Slice 1). It wraps a
Hermes-style tool dispatcher so that, before any tool runs, the action is
evaluated by the SCBE runtime gate (and, for command-like tools, the GeoSeal
execution scanner), and a GeoSeal receipt is emitted per call.

Policy ("hooks-first, deny-beats-bypass"):
    DENY                     -> block; return a deny-with-reason tool error to
                                the model (it adapts instead of dead-ending).
    ESCALATE / QUARANTINE    -> "tripped": allowed to proceed by default but
                                flagged on the receipt; an interactive caller
                                may pause for approve/changes/deny.
    ALLOW                    -> proceed.

Governance logic stays in src/governance + src/crypto (single source of truth);
this module only adapts the harness <-> gate and writes the audit chain.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

# Make the repo root importable so `src.*` resolves no matter where the harness
# is launched from (PowerShell, a vendored copy, a test runner).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
# This package dir, so `import policy` resolves however the seam is loaded.
_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

from src.governance.runtime_gate import Decision, RuntimeGate  # noqa: E402

from policy import check_action  # noqa: E402  (the deterministic, blocking rulebook)

try:  # GeoSeal execution scanner + sealed audit (optional, reused if present)
    from src.crypto.geoseal_execution_gate import (  # noqa: E402
        append_sealed_exec_audit,
        scan_command,
    )

    _HAVE_GEOSEAL = True
except Exception:  # pragma: no cover - geoseal optional
    append_sealed_exec_audit = None  # type: ignore[assignment]
    scan_command = None  # type: ignore[assignment]
    _HAVE_GEOSEAL = False

# Severity ordering so we can take the worst verdict across sources.
_SEVERITY = {"ALLOW": 0, "REVIEW": 1, "QUARANTINE": 2, "ESCALATE": 3, "DENY": 4}

# Tools whose primary argument is a shell command / executable code. These get
# the GeoSeal command scanner in addition to the gate.
_COMMAND_TOOLS = {"execute_code", "terminal", "bash", "shell", "run_command"}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _action_text(tool_name: str, tool_args: dict) -> str:
    """A compact, human-readable descriptor of the action for gate evaluation."""
    a = tool_args or {}
    if tool_name in _COMMAND_TOOLS:
        return str(a.get("code") or a.get("command") or a.get("script") or "")
    if tool_name in ("write_file", "create_file"):
        body = str(a.get("content") or a.get("text") or "")
        return f"write file {a.get('path') or a.get('file') or '?'}: {body[:400]}"
    if tool_name == "patch":
        return f"patch {a.get('path') or '?'}: {str(a.get('find') or a.get('old') or '')[:200]}"
    if tool_name in ("read_file", "search_files"):
        return f"read {a.get('path') or a.get('pattern') or a.get('query') or '?'}"
    if tool_name in ("browser_navigate", "navigate"):
        return f"navigate {a.get('url') or '?'}"
    if tool_name in ("delegate_task", "delegate"):
        return f"delegate: {a.get('task') or a.get('goal') or ''}"[:400]
    try:
        return f"{tool_name} {json.dumps(a, default=str)[:500]}"
    except Exception:
        return f"{tool_name} {str(a)[:500]}"


def _command_of(tool_name: str, tool_args: dict) -> Optional[str]:
    if tool_name in _COMMAND_TOOLS:
        return str((tool_args or {}).get("code") or (tool_args or {}).get("command") or "")
    return None


@dataclass
class SeamDecision:
    """Verdict for one tool call."""

    decision: str  # ALLOW | REVIEW | QUARANTINE | ESCALATE | DENY
    allowed: bool  # False only on DENY
    tripped: bool  # True if not ALLOW
    reason: str
    receipt: dict = field(default_factory=dict)

    def deny_message(self) -> str:
        return f"BLOCKED by governance ({self.decision}): {self.reason}"


@dataclass
class GovernanceSeam:
    """Holds a light, fast gate and emits a GeoSeal receipt per tool call."""

    gate: RuntimeGate = field(
        default_factory=lambda: RuntimeGate(
            coords_backend="stats",  # fast + deterministic; no model load per call
            use_classifier=False,
            use_bijective_tamper=False,
            use_identifier_canonicality=False,
            use_tree_of_escalation=False,
            reroute_rules=[],
        )
    )
    receipts_path: Path = field(default_factory=lambda: _REPO_ROOT / ".scbe" / "aether" / "receipts.jsonl")
    quarantine_blocks: bool = False  # autonomous default: only an enforced block stops a call
    gate_can_block: bool = False  # geometry gate is ADVISORY by default (see govern)

    def govern(self, tool_name: str, tool_args: Optional[dict] = None) -> SeamDecision:
        """Judge one action ("one hand"). Blocking is deterministic; the
        geometry gate only advises.

        Poker model: each call is a fresh hand — the verdict is computed from
        the stateless rulebook (policy catalog + GeoSeal scanner), so a risky
        move earlier in the session can't contaminate a later harmless one.
        The dealer still remembers: every hand is written to the receipt ledger.
        """
        tool_args = tool_args or {}
        action = _action_text(tool_name, tool_args)

        # 1. Geometry gate — ADVISORY by default. Its risk score is recorded on
        #    the receipt but does not block, because on real embeddings it is
        #    order-dependent and both over- and under-fires. Opt it into
        #    blocking with gate_can_block=True.
        gate_result = self.gate.evaluate(action, tool_name=tool_name)
        gate_decision = getattr(gate_result.decision, "name", str(gate_result.decision)).upper()
        if gate_decision not in _SEVERITY:
            gate_decision = "REVIEW"
        signals = list(getattr(gate_result, "signals", []) or [])

        # 2. GeoSeal command scanner — deterministic, blocking (command tools).
        scan_tier = None
        command = _command_of(tool_name, tool_args)
        if command is not None and scan_command is not None:
            scan = scan_command(command)
            scan_tier = scan.tier
            for f in getattr(scan, "findings", []) or []:
                signals.append(f"geoseal:{f.rule}({f.tier})")

        # 3. Policy catalog — deterministic, blocking (every tool). The rulebook.
        pol = check_action(tool_name, tool_args)
        policy_tier = {"BLOCK": "DENY", "WARN": "REVIEW"}.get(pol.severity, "ALLOW")
        for h in pol.hits:
            signals.append(f"policy:{h.rule}({h.severity})")

        # Enforced block = deterministic sources only, plus the gate iff the
        # caller opted it in, plus the explicit quarantine override.
        enforced = []
        if scan_tier == "DENY":
            enforced.append("DENY")
        if pol.blocked:
            enforced.append("DENY")
        if self.gate_can_block and gate_decision == "DENY":
            enforced.append("DENY")
        if self.quarantine_blocks and gate_decision in ("QUARANTINE", "ESCALATE"):
            enforced.append(gate_decision)

        # Displayed verdict = worst across everything (gate advisory included), so
        # a QUARANTINE still reads as "tripped" even when it is allowed to proceed.
        all_tiers = [gate_decision, policy_tier] + ([scan_tier] if scan_tier else [])
        final = max(all_tiers, key=lambda v: _SEVERITY.get(v, 1))

        allowed = not enforced
        tripped = enforced != [] or final != "ALLOW"
        reason = pol.headline() if pol.hits else ("; ".join(signals[:6]) or "clean")

        receipt = {
            "audit_id": _sha256(f"{_now_iso()}|{tool_name}|{action}")[:16],
            "timestamp": _now_iso(),
            "tool": tool_name,
            "args_sha256": _sha256(json.dumps(tool_args, sort_keys=True, default=str)),
            "action_preview": action[:200],
            "decision": final,
            "allowed": allowed,
            "blocked_by": enforced[0] if enforced else None,
            "advisory_gate": gate_decision,
            "cost": round(float(getattr(gate_result, "cost", 0.0)), 4),
            "scan_tier": scan_tier,
            "policy": pol.severity if pol.hits else "ALLOW",
            "signals": signals[:12],
        }
        self._emit(receipt)
        return SeamDecision(decision=final, allowed=allowed, tripped=tripped, reason=reason, receipt=receipt)

    def _emit(self, receipt: dict) -> None:
        """Always append a plain receipt; additionally seal it if a secret exists."""
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        with self.receipts_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(receipt, sort_keys=True) + "\n")
        if append_sealed_exec_audit is not None:
            try:  # sealed chain is best-effort (needs an audit secret in env)
                append_sealed_exec_audit({"decision": receipt, "timestamp": receipt["timestamp"]})
            except Exception:
                pass

    def stamp(self, d: SeamDecision) -> str:
        """One-line terminal receipt line."""
        mark = {"ALLOW": "✓", "REVIEW": "·", "QUARANTINE": "⚠", "ESCALATE": "‼", "DENY": "✗"}.get(d.decision, "·")
        return f"  ⊟ GeoSeal {mark} {d.decision} {d.receipt.get('tool')} #{d.receipt.get('audit_id')}"


def install(dispatch: Callable, seam: GovernanceSeam, *, on_block: Optional[Callable] = None) -> Callable:
    """Wrap a tool-dispatch callable so every call is governed first.

    `dispatch` is expected to be called as dispatch(tool_name, tool_args, *rest).
    On DENY the wrapped callable returns `on_block(SeamDecision)` (default: a
    structured error dict the harness can feed back to the model) and does NOT
    call the underlying dispatch.
    """

    def _default_block(d: SeamDecision) -> dict:
        return {"error": d.deny_message(), "governance": d.receipt}

    blocker = on_block or _default_block

    def wrapped(tool_name: str, tool_args: Optional[dict] = None, *rest: Any, **kw: Any):
        d = seam.govern(tool_name, tool_args or {})
        if not d.allowed:
            return blocker(d)
        return dispatch(tool_name, tool_args, *rest, **kw)

    wrapped._aether_governed = True  # type: ignore[attr-defined]
    return wrapped
