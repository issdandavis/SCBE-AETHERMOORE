"""
HYDRA Swarm Browser --6-Agent Sacred Tongue Orchestrator
=========================================================

Instantiates 6 Sacred Tongue browser agents and coordinates
web tasks through SCBE governance.  Zero AI-vendor dependency:
uses local LLMs or HuggingFace Inference endpoints.

Each agent maps to a Sacred Tongue with a specialized role:

    KO (scout)   --navigates to target URLs
    AV (vision)  --takes screenshots, visual analysis
    RU (reader)  --extracts page content
    CA (clicker) --interacts with page elements
    UM (typer)   --fills forms, types text
    DR (judge)   --verifies results, final approval

Usage:
    from hydra.swarm_browser import SwarmBrowser
    swarm = SwarmBrowser(provider_type="local")
    await swarm.launch()
    result = await swarm.execute_task("search for SCBE on GitHub")
    await swarm.shutdown()
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .head import HydraHead
from .spine import HydraSpine
from .limbs import MultiTabBrowserLimb
from .ledger import Ledger
from .librarian import Librarian
from .consensus import RoundtableConsensus, VoteDecision
from .swarm_governance import (
    SwarmGovernance,
    GovernanceConfig,
    AgentRole,
    REALM_CENTERS,
)


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

AGENTS: Dict[str, Dict[str, Any]] = {
    "KO": {"role": "scout",   "phase": 0,   "actions": ["navigate"]},
    "AV": {"role": "vision",  "phase": 60,  "actions": ["screenshot"]},
    "RU": {"role": "reader",  "phase": 120, "actions": ["get_content"]},
    "CA": {"role": "clicker", "phase": 180, "actions": ["click"]},
    "UM": {"role": "typer",   "phase": 240, "actions": ["type"]},
    "DR": {"role": "judge",   "phase": 300, "actions": ["verify"]},
}

# Sensitivity thresholds --actions above this require Roundtable consensus
HIGH_SENSITIVITY_ACTIONS = {"click", "type", "submit", "download"}


class SwarmBrowser:
    """
    6-agent Sacred Tongue browser swarm.

    Coordinates 6 HydraHead instances, each with its own browser tab,
    through SwarmGovernance and RoundtableConsensus.
    """

    def __init__(
        self,
        provider_type: str = "local",
        model: str = "local-model",
        base_url: str = "http://localhost:1234/v1",
        backend_type: str = "playwright",
        headless: bool = True,
        scbe_url: str = "http://127.0.0.1:8080",
        dry_run: bool = False,
    ):
        self.provider_type = provider_type
        self.model = model
        self.base_url = base_url
        self.backend_type = backend_type
        self.headless = headless
        self.scbe_url = scbe_url
        self.dry_run = dry_run

        # Core components --initialized in launch()
        self.governance: Optional[SwarmGovernance] = None
        self.roundtable: Optional[RoundtableConsensus] = None
        self.ledger: Optional[Ledger] = None
        self.librarian: Optional[Librarian] = None
        self.spine: Optional[HydraSpine] = None
        self.browser: Optional[MultiTabBrowserLimb] = None

        # Per-tongue state
        self.heads: Dict[str, HydraHead] = {}
        self.tab_ids: Dict[str, str] = {}

        self._launched = False

    # =====================================================================
    # Lifecycle
    # =====================================================================

    async def launch(self) -> None:
        """Initialize all 6 agents, browser tabs, and governance."""
        if self._launched:
            return

        print("\n" + "=" * 60)
        print("  HYDRA SWARM BROWSER -- Launching 6 Sacred Tongue Agents")
        print("=" * 60)

        # --- Ledger + Librarian ---
        self.ledger = Ledger()
        self.librarian = Librarian(self.ledger)

        # --- Governance ---
        config = GovernanceConfig(min_agents=4)
        self.governance = SwarmGovernance(config)
        self.roundtable = RoundtableConsensus()

        # --- Spine ---
        self.spine = HydraSpine(
            ledger=self.ledger,
            scbe_url=self.scbe_url,
            use_dual_lattice=False,
            use_switchboard=False,
        )

        # --- Multi-tab browser ---
        if not self.dry_run:
            self.browser = MultiTabBrowserLimb(
                backend_type=self.backend_type,
                max_tabs=6,
                scbe_url=self.scbe_url,
            )
            await self.browser.activate()
            self.spine.connect_limb(self.browser)

        # --- Create 6 heads ---
        for tongue, spec in AGENTS.items():
            callsign = f"{tongue}-{spec['role']}"

            head = HydraHead(
                ai_type=self.provider_type,
                model=self.model,
                callsign=callsign,
            )

            # Connect to spine
            await head.connect(self.spine)
            self.heads[tongue] = head

            # Register in swarm governance
            position = list(REALM_CENTERS.get(tongue, [0.0] * 6))
            self.governance.add_agent(
                head.head_id,
                AgentRole.VALIDATOR,
                initial_position=position,
                initial_coherence=1.0,
            )

            # Register tongue in roundtable
            self.roundtable.register_tongue_head(tongue, head.head_id)

            # Create browser tab
            if self.browser:
                tab_id = await self.browser.create_tab(tongue)
                self.tab_ids[tongue] = tab_id

            print(f"  [{tongue}] {spec['role']:<8} head={head.head_id[:12]}  tab={self.tab_ids.get(tongue, 'dry-run')}")

        self._launched = True
        print(f"\nSwarm ready.  Provider: {self.provider_type}  Backend: {self.backend_type}")
        print(f"Dry-run: {self.dry_run}")
        print("=" * 60 + "\n")

    async def shutdown(self) -> None:
        """Clean up all browser instances and disconnect heads."""
        print("\n[SWARM] Shutting down...")

        for tongue, head in self.heads.items():
            await head.disconnect()

        if self.browser:
            for tab_id in list(self.browser.tabs.keys()):
                await self.browser.execute("close_tab", "", {"tab_id": tab_id})
            await self.browser.deactivate()

        self._launched = False
        print("[SWARM] All agents disconnected.\n")

    # =====================================================================
    # Task execution
    # =====================================================================

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a web task using the 6-agent swarm.

        Steps:
        1. Ask the planner head (KO) to decompose the task
        2. Dispatch each action to the appropriate tongue agent
        3. Use RoundtableConsensus for high-sensitivity actions
        4. Return aggregated results
        """
        if not self._launched:
            await self.launch()

        ko_head = self.heads.get("KO")
        results: List[Dict[str, Any]] = []

        # --- Plan the task ---
        plan: List[Dict[str, Any]] = []
        if ko_head and ko_head.has_llm:
            try:
                plan = await ko_head.plan(task_description)
                print(f"[PLANNER] LLM produced {len(plan)} action(s)")
            except Exception as exc:
                print(f"[PLANNER] LLM planning failed: {exc}")

        if not plan:
            # Fallback: single navigate action with the task as a search query
            plan = [{"action": "navigate", "target": task_description}]

        # --- Execute each planned action ---
        for step_idx, action_cmd in enumerate(plan):
            action = action_cmd.get("action", "navigate")
            target = action_cmd.get("target", "")
            params = action_cmd.get("params", {})

            tongue = self._select_tongue(action)
            print(f"  Step {step_idx + 1}: [{tongue}] {action} ->{target[:60]}")

            # Consensus check for sensitive actions
            if action in HIGH_SENSITIVITY_ACTIONS:
                consensus_ok = await self._consensus_check(action, target)
                if not consensus_ok:
                    results.append({
                        "step": step_idx + 1,
                        "tongue": tongue,
                        "action": action,
                        "target": target,
                        "success": False,
                        "reason": "Roundtable denied action",
                    })
                    continue

            result = await self._dispatch(tongue, action, target, params)
            result["step"] = step_idx + 1
            result["tongue"] = tongue
            results.append(result)

        # --- Store task result in Librarian ---
        self.librarian.remember(
            f"task:{datetime.now(timezone.utc).isoformat()}",
            {"task": task_description, "steps": len(results)},
            category="swarm_task",
            importance=0.6,
        )

        return {
            "task": task_description,
            "total_steps": len(results),
            "results": results,
            "success": all(r.get("success", False) for r in results),
        }

    # =====================================================================
    # Internal dispatch
    # =====================================================================

    def _select_tongue(self, action: str) -> str:
        """Map an action to the best tongue agent."""
        action_map = {
            "navigate": "KO",
            "screenshot": "AV",
            "get_content": "RU",
            "click": "CA",
            "type": "UM",
            "verify": "DR",
            "scroll": "KO",
            "submit": "CA",
            "download": "RU",
        }
        return action_map.get(action, "KO")

    async def _dispatch(
        self,
        tongue: str,
        action: str,
        target: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route an action to the correct agent's browser tab."""
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "action": action,
                "target": target,
                "tongue": tongue,
            }

        tab_id = self.tab_ids.get(tongue)
        if not tab_id or not self.browser:
            return {"success": False, "error": f"No tab for tongue {tongue}"}

        params["tab_id"] = tab_id
        result = await self.browser.execute(action, target, params)
        return result

    async def _consensus_check(self, action: str, target: str) -> bool:
        """Use RoundtableConsensus for high-sensitivity actions."""
        # Calculate sensitivity
        sensitivity = 0.6
        target_lower = target.lower()
        if any(x in target_lower for x in ["bank", "pay", "finance", "crypto"]):
            sensitivity = 0.95
        elif any(x in target_lower for x in ["login", "auth", "password"]):
            sensitivity = 0.8

        result = await self.roundtable.roundtable_consensus(
            action=action,
            target=target,
            sensitivity=sensitivity,
            context={"swarm": True},
            heads=self.heads,
        )

        return result.get("success", False)

    # =====================================================================
    # Convenience methods
    # =====================================================================

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Quick navigate via the scout agent."""
        return await self._dispatch("KO", "navigate", url, {})

    async def screenshot(self) -> Dict[str, Any]:
        """Quick screenshot via the vision agent."""
        return await self._dispatch("AV", "screenshot", "", {})

    async def get_content(self) -> Dict[str, Any]:
        """Quick content extraction via the reader agent."""
        return await self._dispatch("RU", "get_content", "", {})

    async def click(self, selector: str) -> Dict[str, Any]:
        """Quick click via the clicker agent (with consensus)."""
        ok = await self._consensus_check("click", selector)
        if not ok:
            return {"success": False, "reason": "Roundtable denied"}
        return await self._dispatch("CA", "click", selector, {})

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Quick type via the typer agent (with consensus)."""
        ok = await self._consensus_check("type", selector)
        if not ok:
            return {"success": False, "reason": "Roundtable denied"}
        return await self._dispatch("UM", "type", selector, {"text": text})

    def get_status(self) -> Dict[str, Any]:
        """Get swarm status."""
        gov_status = self.governance.get_status() if self.governance else {}
        return {
            "launched": self._launched,
            "agents": list(self.heads.keys()),
            "tabs": dict(self.tab_ids),
            "provider": self.provider_type,
            "model": self.model,
            "dry_run": self.dry_run,
            "governance": gov_status,
        }
