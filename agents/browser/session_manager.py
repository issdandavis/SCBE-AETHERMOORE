"""Session layer for AetherBrowse CDP wiring and action execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np

from agents.browser.action_validator import ActionValidationResult, ActionValidator, ValidationDecision, ValidationPolicy
from agents.browser.dom_snapshot import DomSnapshot, make_action_snapshot_context, make_dom_snapshot


class _MockBrowserBackend:
    """Deterministic mock backend for offline/audited operation."""

    def __init__(self) -> None:
        self.current_url = "about:blank"
        self.event_log: list[dict[str, Any]] = []

    async def initialize(self) -> bool:
        self.event_log.append({"event": "initialize", "ok": True})
        return True

    async def navigate(self, url: str) -> dict[str, Any]:
        self.current_url = url
        payload = {"action": "navigate", "url": url}
        self.event_log.append(payload)
        return payload

    async def click(self, selector: str) -> dict[str, Any]:
        payload = {"action": "click", "selector": selector}
        self.event_log.append(payload)
        return payload

    async def type_text(self, selector: str, value: str) -> dict[str, Any]:
        payload = {"action": "type", "selector": selector, "value": value}
        self.event_log.append(payload)
        return payload

    async def scroll(self, direction: str = "down", amount: int = 300) -> dict[str, Any]:
        payload = {"action": "scroll", "direction": direction, "amount": amount}
        self.event_log.append(payload)
        return payload

    async def screenshot(self) -> bytes:
        payload = b"mock-screenshot-bytes"
        self.event_log.append({"action": "screenshot", "bytes": len(payload)})
        return payload

    async def get_page_content(self) -> str:
        html = f"<html><body><div id='mock-page'>{self.current_url}</div></body></html>"
        self.event_log.append({"action": "get_page_content"})
        return html

    async def close(self) -> None:
        self.event_log.append({"event": "close"})



class SessionDecision(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE = "QUARANTINE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


def _as_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()  # type: ignore
    return dict(obj)


@dataclass
class AetherbrowseSessionConfig:
    backend: str = "cdp"
    host: str = "127.0.0.1"
    port: int = 9222
    target_id: Optional[str] = None
    agent_id: str = "aetherbrowse-agent"
    auto_escalate: bool = False
    safe_radius: float = 0.92
    phdm_dim: int = 16
    sensitivity_factor: float = 1.0


class AetherbrowseSession:
    """Wraps a backend and validates every command through validator + audit logger."""

    def __init__(self, config: AetherbrowseSessionConfig):
        self.config = config
        self.session_id = self._make_session_id(config.agent_id)
        self._backend = None
        self._connected = False
        self.current_url = ""
        self.current_embedding = None
        self.snapshot: Optional[DomSnapshot] = None
        self.audit_log: list[dict[str, Any]] = []
        self.validator = ActionValidator(
            ValidationPolicy(
                safe_radius=config.safe_radius,
                phdm_dim=config.phdm_dim,
                sensitivity_factor=config.sensitivity_factor,
            )
        )

    async def _create_backend(self):
        if self.config.backend == "mock":
            return _MockBrowserBackend()
        if self.config.backend != "cdp":
            raise ValueError(f"Unsupported backend '{self.config.backend}' in this phase.")

        from agents.browsers.cdp_backend import CDPBackend

        return CDPBackend(host=self.config.host, port=self.config.port, target_id=self.config.target_id)

    def _make_session_id(self, prefix: str) -> str:
        import uuid
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    async def initialize(self) -> bool:
        if self._connected:
            return True

        try:
            self._backend = await self._create_backend()
            ok = await self._backend.initialize()
            self._connected = bool(ok)
            if self._connected:
                return True
        except Exception as exc:
            self.audit_log.append(
                {
                    "event": "backend_init_failed",
                    "error": str(exc),
                    "session_id": self.session_id,
                }
            )
        return False

    async def close(self) -> None:
        if self._backend is None:
            return
        try:
            await self._backend.close()
        except Exception:
            pass
        self._connected = False
        self._backend = None

    async def __aenter__(self):
        if not await self.initialize():
            raise RuntimeError("Aetherbrowse session init failed.")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()
        return False

    def get_audit_log(self) -> list[dict[str, Any]]:
        return list(self.audit_log)

    async def _snapshot_current_page(self) -> Optional[DomSnapshot]:
        if self._backend is None:
            return None

        html = await self._backend.get_page_content()
        self.snapshot = make_dom_snapshot(
            html,
            source_url=self.current_url,
            include_html=False,
        )
        return self.snapshot

    def _record_audit(
        self,
        action: str,
        target: str,
        decision: SessionDecision,
        validation: ActionValidationResult,
        execution: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        entry = {
            "session_id": self.session_id,
            "agent_id": self.config.agent_id,
            "action": action,
            "target": target,
            "decision": decision.value,
            "validation": validation.to_dict(),
            "execution": execution,
            "error": error,
            "snapshot": make_action_snapshot_context(self.snapshot) if self.snapshot else None,
        }
        self.audit_log.append(entry)
        return entry

    async def _maybe_snapshot(self, action: str, execute_success: bool) -> None:
        if action in {"navigate", "snapshot", "extract", "scroll"} and execute_success:
            await self._snapshot_current_page()

    async def _dispatch(self, action: str, target: str, value: Optional[str]) -> Dict[str, Any]:
        if self._backend is None:
            raise RuntimeError("Session not initialized.")

        if action == "navigate":
            result = await self._backend.navigate(target)
            self.current_url = target
            return {"result": result}

        if action == "click":
            return {"result": await self._backend.click(target)}

        if action == "type":
            return {"result": await self._backend.type_text(target, value or "")}

        if action == "scroll":
            if not value:
                value = "down"
            direction = "down" if value not in {"down", "up"} else value
            amount = 300
            if "::" in value:
                # Optional compact format "down::500"
                parts = value.split("::", 1)
                direction = parts[0]
                try:
                    amount = int(parts[1])
                except ValueError:
                    amount = 300
            return {"result": await self._backend.scroll(direction=direction, amount=amount)}

        if action == "screenshot":
            payload = await self._backend.screenshot()
            return {"result": {"bytes": len(payload), "sha256": __import__("hashlib").sha256(payload).hexdigest()}}

        if action == "extract":
            html = await self._backend.get_page_content()
            self.snapshot = make_dom_snapshot(html, source_url=self.current_url)
            return {"result": self.snapshot.to_dict()}

        if action == "snapshot":
            snapshot = await self._snapshot_current_page()
            return {"result": snapshot.to_dict() if snapshot else {}}

        raise ValueError(f"Unsupported action '{action}'.")

    async def execute_action(
        self,
        action: str,
        target: str,
        value: Optional[str] = None,
        *,
        context: Optional[Dict[str, Any]] = None,
        audit_only: bool = False,
    ) -> Dict[str, Any]:
        action = action.strip().lower()
        target = target or ""

        validation = await self.validator.validate(
            action=action,
            target=target,
            context_embedding=self.current_embedding,
            context=context,
        )

        # For now use local decisions only; no external SCBE API dependency in this phase.
        if validation.decision == ValidationDecision.DENY:
            entry = self._record_audit(action, target, SessionDecision.DENY, validation, error="blocked_by_validator")
            return {
                "session_id": self.session_id,
                "action": action,
                "target": target,
                "decision": SessionDecision.DENY.value,
                "executed": False,
                "audit": _as_dict(entry),
            }

        if validation.decision == ValidationDecision.ESCALATE and not self.config.auto_escalate:
            entry = self._record_audit(action, target, SessionDecision.ESCALATE, validation, error="pending_escalation")
            return {
                "session_id": self.session_id,
                "action": action,
                "target": target,
                "decision": SessionDecision.ESCALATE.value,
                "executed": False,
                "audit": _as_dict(entry),
            }

        can_execute = validation.can_execute or (self.config.auto_escalate and validation.decision == ValidationDecision.ESCALATE)
        if not can_execute or audit_only:
            entry = self._record_audit(
                action, target,
                SessionDecision.ALLOW if can_execute else validation.decision,
                validation,
                error=None if audit_only else "dry-run",
            )
            return {
                "session_id": self.session_id,
                "action": action,
                "target": target,
                "decision": SessionDecision.ALLOW.value if can_execute else validation.decision.value,
                "executed": False,
                "audit": _as_dict(entry),
            }

        try:
            execution = await self._dispatch(action, target, value)
            await self._maybe_snapshot(action, True)
            self.current_embedding = np.array(validation.embedding, dtype=float)
            session_decision = SessionDecision.QUARANTINE if validation.decision == ValidationDecision.QUARANTINE else SessionDecision.ALLOW
            entry = self._record_audit(action, target, session_decision, validation, execution=execution)
            return {
                "session_id": self.session_id,
                "action": action,
                "target": target,
                "decision": session_decision.value,
                "executed": True,
                "execution": execution,
                "audit": _as_dict(entry),
            }
        except Exception as exc:
            entry = self._record_audit(action, target, SessionDecision.DENY, validation, error=str(exc))
            return {
                "session_id": self.session_id,
                "action": action,
                "target": target,
                "decision": SessionDecision.DENY.value,
                "executed": False,
                "error": str(exc),
                "audit": _as_dict(entry),
            }
