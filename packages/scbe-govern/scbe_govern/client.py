"""
SCBEGovern client — inline or remote mode.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GovResult:
    tier: str          # ALLOW | QUARANTINE | DENY
    score: float       # harmonic wall H(d,pd) ∈ (0,1]
    d_H: float         # hyperbolic distance
    pd: float          # pattern drift
    role: str          # atomic semantic role
    command: str
    agent_id: Optional[str] = None

    @property
    def allowed(self) -> bool:
        return self.tier in ("ALLOW", "QUARANTINE")

    @property
    def blocked(self) -> bool:
        return self.tier == "DENY"


class SCBEGovern:
    """Governance checker.  Works in two modes:

    Inline (default):
        gov = SCBEGovern()

    Remote (points at a running SCBE bridge):
        gov = SCBEGovern(base_url="http://localhost:8001", api_key="scbe-dev-key")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 10,
    ):
        self._base_url = base_url.rstrip("/") if base_url else None
        self._api_key = api_key or "scbe-dev-key"
        self._timeout = timeout
        self._inline = self._base_url is None

        if self._inline:
            self._load_inline()

    # ------------------------------------------------------------------
    # Inline engine
    # ------------------------------------------------------------------

    def _load_inline(self) -> None:
        import sys
        from pathlib import Path

        # 1. Bundled _core (always present in the installed package)
        try:
            from scbe_govern._core import (  # type: ignore[import]
                semantic_distance,
                danger_drift,
                harmonic_score,
                risk_tier,
                atomic_role_for_command,
            )
            self._d_H = semantic_distance
            self._pd = danger_drift
            self._score = harmonic_score
            self._tier = risk_tier
            self._role = atomic_role_for_command
            return
        except ImportError:
            pass

        # 2. Monorepo fallback (dev installs where _core isn't on path yet)
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "scripts" / "benchmark" / "scbe_governance_core.py"
            if candidate.exists():
                root = str(parent)
                if root not in sys.path:
                    sys.path.insert(0, root)
                break

        try:
            from scripts.benchmark.scbe_governance_core import (  # type: ignore[import]
                semantic_distance,
                danger_drift,
                harmonic_score,
                risk_tier,
                atomic_role_for_command,
            )
            self._d_H = semantic_distance
            self._pd = danger_drift
            self._score = harmonic_score
            self._tier = risk_tier
            self._role = atomic_role_for_command
        except ImportError as exc:
            raise ImportError(
                "scbe_govern._core not importable. Re-install: pip install scbe-govern"
            ) from exc

    def _check_inline(self, command: str, agent_id: Optional[str]) -> GovResult:
        d_H = self._d_H(command)
        pd = self._pd(command)
        score = self._score(d_H, pd)
        tier = self._tier(score)
        role, _ = self._role(command)
        return GovResult(
            tier=tier,
            score=round(score, 4),
            d_H=round(d_H, 4),
            pd=round(pd, 4),
            role=role,
            command=command,
            agent_id=agent_id,
        )

    # ------------------------------------------------------------------
    # Remote engine
    # ------------------------------------------------------------------

    def _post(self, path: str, body: dict) -> dict:
        payload = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self._api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read())

    def _check_remote(self, command: str, agent_id: Optional[str]) -> GovResult:
        body: dict = {"command": command}
        if agent_id:
            body["agent_id"] = agent_id
        data = self._post("/v1/govern/check", body)
        return GovResult(
            tier=data["tier"],
            score=data["score"],
            d_H=data["d_H"],
            pd=data["pd"],
            role=data["role"],
            command=data["command"],
            agent_id=data.get("agent_id"),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, command: str, agent_id: Optional[str] = None) -> GovResult:
        """Score a single command. Returns GovResult with .tier, .score, .allowed."""
        if self._inline:
            return self._check_inline(command, agent_id)
        return self._check_remote(command, agent_id)

    def batch(self, commands: List[str], agent_id: Optional[str] = None) -> List[GovResult]:
        """Score multiple commands. Returns list in same order."""
        if self._inline:
            return [self._check_inline(c, agent_id) for c in commands]
        body: dict = {"commands": commands}
        if agent_id:
            body["agent_id"] = agent_id
        data = self._post("/v1/govern/batch", body)
        return [
            GovResult(
                tier=r["tier"],
                score=r["score"],
                d_H=r["d_H"],
                pd=r["pd"],
                role=r["role"],
                command=r["command"],
                agent_id=agent_id,
            )
            for r in data["results"]
        ]

    def guard(self, command: str, agent_id: Optional[str] = None) -> GovResult:
        """Like check(), but raises ValueError on DENY."""
        result = self.check(command, agent_id)
        if result.blocked:
            raise ValueError(
                f"SCBE governance DENY: score={result.score:.3f} d_H={result.d_H:.3f} "
                f"command={command!r}"
            )
        return result
