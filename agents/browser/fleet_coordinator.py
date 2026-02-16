"""Fleet-level orchestration for multi-browser AetherBrowse sessions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

from agents.browser.session_manager import AetherbrowseSession, AetherbrowseSessionConfig


@dataclass
class FleetCoordinatorConfig:
    size: int = 1
    backend: str = "cdp"
    host: str = "127.0.0.1"
    port: int = 9222
    auto_escalate: bool = False
    safe_radius: float = 0.92
    phdm_dim: int = 16
    sensitivity_factor: float = 1.0


class AetherbrowseFleet:
    def __init__(self, config: Optional[FleetCoordinatorConfig] = None):
        self.config = config or FleetCoordinatorConfig()
        self.sessions: list[AetherbrowseSession] = []
        self._next = 0

    async def initialize(self) -> bool:
        for idx in range(self.config.size):
            session_cfg = AetherbrowseSessionConfig(
                backend=self.config.backend,
                host=self.config.host,
                port=self.config.port,
                agent_id=f"aetherbrowse-fleet-{idx+1}",
                auto_escalate=self.config.auto_escalate,
                safe_radius=self.config.safe_radius,
                phdm_dim=self.config.phdm_dim,
                sensitivity_factor=self.config.sensitivity_factor,
            )
            session = AetherbrowseSession(session_cfg)
            ok = await session.initialize()
            if not ok:
                await self.shutdown()
                return False
            self.sessions.append(session)
        return True

    async def shutdown(self) -> None:
        if not self.sessions:
            return
        await asyncio.gather(*[s.close() for s in self.sessions], return_exceptions=True)
        self.sessions = []
        self._next = 0

    async def __aenter__(self):
        if not await self.initialize():
            raise RuntimeError("Fleet initialization failed.")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.shutdown()
        return False

    def _select_session(self) -> AetherbrowseSession:
        if not self.sessions:
            raise RuntimeError("No active sessions.")
        session = self.sessions[self._next % len(self.sessions)]
        self._next += 1
        return session

    async def execute(
        self,
        action: str,
        target: str,
        value: Optional[str] = None,
        *,
        context: Optional[Dict[str, Any]] = None,
        audit_only: bool = False,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if session_id is None:
            session = self._select_session()
        else:
            try:
                session = next(s for s in self.sessions if s.session_id == session_id)
            except StopIteration as exc:
                raise ValueError(f"Session not found: {session_id}") from exc

        return await session.execute_action(action, target, value, context=context, audit_only=audit_only)

    async def execute_script(self, script: list[dict[str, Any]]) -> list[Dict[str, Any]]:
        results = []
        for item in script:
            results.append(
                await self.execute(
                    action=str(item.get("action", "")),
                    target=str(item.get("target", "")),
                    value=item.get("value"),
                )
            )
        return results

    def collect_audit_logs(self) -> Dict[str, list[Dict[str, Any]]]:
        return {session.session_id: session.get_audit_log() for session in self.sessions}

    def summary(self) -> Dict[str, Any]:
        return {
            "size": len(self.sessions),
            "sessions": [
                {
                    "session_id": session.session_id,
                    "agent_id": session.config.agent_id,
                    "current_url": session.current_url,
                }
                for session in self.sessions
            ],
        }
