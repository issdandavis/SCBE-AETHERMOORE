"""
HYDRA Spine - Central Coordinator
==================================

The backbone that connects all heads and limbs.
Terminal-native with multi-tab orchestration.

Features:
- Unix pipe compatible for terminal workflows
- JSON-RPC for programmatic access
- Multi-tab browser coordination
- AI-to-AI message passing with SCBE governance
- One-click workflow execution
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import uuid

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .ledger import Ledger, LedgerEntry, EntryType
from .switchboard import Switchboard

# Try to import dual lattice governor (optional but recommended)
try:
    from src.crypto.dual_lattice import TongueLatticeGovernor, SacredTongue
    DUAL_LATTICE_AVAILABLE = True
except ImportError:
    DUAL_LATTICE_AVAILABLE = False
    TongueLatticeGovernor = None


class WorkflowPhase(str, Enum):
    """Phases in a multi-phase workflow."""
    INIT = "init"
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Workflow:
    """A multi-phase workflow that can be triggered with one click."""
    id: str
    name: str
    phases: List[Dict[str, Any]]
    current_phase: int = 0
    status: WorkflowPhase = WorkflowPhase.INIT
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def next_phase(self) -> Optional[Dict[str, Any]]:
        """Get next phase to execute."""
        if self.current_phase < len(self.phases):
            return self.phases[self.current_phase]
        return None

    def advance(self, result: Dict[str, Any]) -> bool:
        """Advance to next phase with result."""
        self.results.append(result)
        self.current_phase += 1
        if self.current_phase >= len(self.phases):
            self.status = WorkflowPhase.COMPLETE
            return False
        self.status = WorkflowPhase.EXECUTION
        return True


class HydraSpine:
    """
    Central coordinator for the HYDRA system.

    The Spine connects:
    - Multiple AI heads (Claude, Codex, GPT, local LLMs)
    - Multiple execution limbs (browser tabs, terminals, APIs)
    - Central ledger for cross-session memory
    - SCBE governance for all actions
    """

    def __init__(
        self,
        ledger: Ledger = None,
        scbe_url: str = "http://127.0.0.1:8080",
        use_dual_lattice: bool = True,
        use_switchboard: bool = True,
        switchboard_db: str = "artifacts/hydra/switchboard.db",
    ):
        self.ledger = ledger or Ledger()
        self.scbe_url = scbe_url

        # Connected components
        self.heads: Dict[str, 'HydraHead'] = {}
        self.limbs: Dict[str, 'HydraLimb'] = {}

        # Active workflows
        self.workflows: Dict[str, Workflow] = {}

        # Message queues for AI-to-AI communication
        self.message_queues: Dict[str, asyncio.Queue] = {}

        # Event handlers
        self._handlers: Dict[str, List[Callable]] = {}
        self.role_channels: Dict[str, Set[str]] = {}

        # Terminal mode flag
        self._terminal_mode = False

        # Dual Lattice Governance (Kyber/Dilithium + Sacred Tongues)
        self.lattice_governor = None
        if use_dual_lattice and DUAL_LATTICE_AVAILABLE:
            self.lattice_governor = TongueLatticeGovernor(scbe_url)
            print("[SPINE] Dual Lattice Cross-Stitch governance enabled")

        self.switchboard = None
        if use_switchboard:
            self.switchboard = Switchboard(switchboard_db)
            print(f"[SPINE] Switchboard enabled: {switchboard_db}")

    async def start(self, terminal_mode: bool = False) -> None:
        """Start the Hydra Spine."""
        self._terminal_mode = terminal_mode

        print("""
╔═══════════════════════════════════════════════════════════════╗
║                    SCBE HYDRA SYSTEM                          ║
║                "Many Heads, One Governed Body"                ║
╠═══════════════════════════════════════════════════════════════╣
║  Session: {session_id}
║  Ledger:  {ledger_path}
╚═══════════════════════════════════════════════════════════════╝
        """.format(
            session_id=self.ledger.session_id[:30],
            ledger_path=self.ledger.db_path[-40:]
        ))

        # Log startup
        self._log_entry(EntryType.CHECKPOINT, "spine_start", "system", {
            "terminal_mode": terminal_mode,
            "scbe_url": self.scbe_url
        })

        if terminal_mode:
            await self._run_terminal_mode()

    async def _run_terminal_mode(self) -> None:
        """Run in terminal pipe mode - read JSON from stdin."""
        print("[SPINE] Terminal mode active. Pipe JSON commands or type 'exit' to quit.")
        print("[SPINE] Example: echo '{\"action\": \"navigate\", \"url\": \"...\"}' | hydra")
        print()

        loop = asyncio.get_event_loop()

        while True:
            try:
                # Read from stdin
                if sys.stdin.isatty():
                    line = await loop.run_in_executor(None, lambda: input("hydra> "))
                else:
                    line = await loop.run_in_executor(None, sys.stdin.readline)

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                if line.lower() == "exit":
                    break

                if line.lower() == "status":
                    self._print_status()
                    continue

                if line.lower() == "stats":
                    stats = self.ledger.get_stats()
                    print(json.dumps(stats, indent=2))
                    continue

                # Try to parse as JSON command
                try:
                    command = json.loads(line)
                    result = await self.execute(command)
                    print(json.dumps(result, indent=2))
                except json.JSONDecodeError:
                    # Treat as natural language command
                    result = await self.execute_natural(line)
                    print(json.dumps(result, indent=2))

            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n[SPINE] Interrupted.")
                break

        print("[SPINE] Shutting down...")

    def _print_status(self) -> None:
        """Print current status."""
        print("\n" + "=" * 50)
        print("HYDRA STATUS")
        print("=" * 50)
        print(f"Session: {self.ledger.session_id}")
        print(f"Active Heads: {len(self.heads)}")
        for hid, head in self.heads.items():
            print(f"  - {hid}: {head.ai_type}/{head.model}")
        print(f"Active Limbs: {len(self.limbs)}")
        for lid, limb in self.limbs.items():
            print(f"  - {lid}: {limb.limb_type}")
        print(f"Active Workflows: {len(self.workflows)}")
        if self.switchboard:
            sb = self.switchboard.stats()
            print(f"Switchboard tasks: {sb.get('by_status', {})}")
            print(f"Role channels: {list(self.role_channels.keys())}")
        print("=" * 50 + "\n")

    async def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command through the Hydra system.

        Command format:
        {
            "action": "navigate|click|type|run|workflow",
            "target": "...",
            "params": {...},
            "head_id": "optional - which AI head",
            "limb_id": "optional - which execution limb",
            "sensitivity": "optional - action sensitivity 0-1"
        }
        """
        action = command.get("action", "unknown")
        target = command.get("target", "")
        params = command.get("params", {})
        head_id = command.get("head_id")
        limb_id = command.get("limb_id")
        sensitivity = command.get("sensitivity", self._infer_sensitivity(action, target))

        # Generate action ID
        action_id = f"action-{uuid.uuid4().hex[:8]}"

        # =====================================================================
        # DUAL LATTICE GOVERNANCE CHECK
        # Route action through Kyber/Dilithium + Sacred Tongues lattice
        # =====================================================================
        if self.lattice_governor:
            lattice_result = self.lattice_governor.authorize(action, target, sensitivity)
            decision = lattice_result.get("decision", "ALLOW")

            # Log the lattice decision
            self._log_entry(
                EntryType.DECISION,
                f"lattice_{action}",
                target,
                {
                    "trust_score": lattice_result.get("trust_score"),
                    "vector_norm": lattice_result.get("vector_norm"),
                    "tongues_active": lattice_result.get("tongues_active"),
                    "kyber_level": lattice_result.get("lattice_proof", {}).get("security", {}).get("kyber_level"),
                },
                head_id=head_id,
                decision=decision,
                score=lattice_result.get("trust_score", 0)
            )

            # Domain-aware turnstile handling (browser vs vehicle vs fleet vs antivirus)
            from .turnstile import resolve_turnstile

            domain_type = str(
                command.get("domain_type")
                or params.get("domain_type")
                or ("browser" if action in {"navigate", "click", "type"} else "fleet")
            )
            trust_score = float(lattice_result.get("trust_score", 0.0))
            vector_norm = float(lattice_result.get("vector_norm", 0.0))
            suspicion = max(0.0, min(1.0, 1.0 - trust_score))
            quorum_ok = bool(command.get("quorum_ok", True))

            turnstile = resolve_turnstile(
                decision=decision,
                domain=domain_type,
                suspicion=suspicion,
                geometry_norm=vector_norm,
                previous_antibody_load=float(params.get("antibody_load", 0.0)),
                quorum_ok=quorum_ok,
            )

            params["turnstile_action"] = turnstile.action
            params["antibody_load"] = round(turnstile.antibody_load, 6)
            params["membrane_stress"] = round(turnstile.membrane_stress, 6)

            if decision != "ALLOW":
                self._log_entry(
                    EntryType.CHECKPOINT,
                    "turnstile_resolution",
                    target,
                    {
                        "action": action,
                        "domain_type": domain_type,
                        "decision": decision,
                        "turnstile_action": turnstile.action,
                        "honeypot": turnstile.deploy_honeypot,
                        "reason": turnstile.reason,
                    },
                    head_id=head_id
                )

            if turnstile.isolate:
                params["quarantine"] = True

            if turnstile.deploy_honeypot:
                params["honeypot"] = True
                params["isolation_reason"] = turnstile.reason
                if action in {"navigate", "click", "type"}:
                    target = params.get("honeypot_target", "about:blank#scbe-honeypot")

            if not turnstile.continue_execution:
                blocked_decision = "ESCALATE" if turnstile.require_human else "DENY"
                return {
                    "success": False,
                    "decision": blocked_decision,
                    "reason": turnstile.reason,
                    "turnstile_action": turnstile.action,
                    "domain_type": domain_type,
                    "trust_score": trust_score,
                    "tongues_active": lattice_result.get("tongues_active"),
                    "action_id": action_id
                }

            # Continue with constrained execution modes.
            if turnstile.action in {"PIVOT", "DEGRADE"}:
                params["safe_mode"] = turnstile.action.lower()
                print(f"[LATTICE] Action {decision} rerouted via {turnstile.action}: {action} → {target[:30]}")
            elif turnstile.action == "ISOLATE":
                print(f"[LATTICE] Action {decision} isolated: {action} → {target[:30]}")
            elif turnstile.action == "HONEYPOT":
                print(f"[LATTICE] Honeypot deployed for action: {action} → {target[:30]}")

        # Log the action request
        self._log_entry(
            EntryType.ACTION,
            action,
            target,
            params,
            head_id=head_id,
            limb_id=limb_id
        )

        # Route to appropriate handler
        if action == "workflow":
            return await self._execute_workflow(command)

        elif action == "navigate":
            return await self._execute_browser_action(action, target, params, limb_id)

        elif action == "click":
            return await self._execute_browser_action(action, target, params, limb_id)

        elif action == "type":
            return await self._execute_browser_action(action, target, params, limb_id)

        elif action == "run":
            return await self._execute_terminal_action(target, params, limb_id)

        elif action == "api":
            return await self._execute_api_action(target, params, limb_id)

        elif action == "remember":
            key = command.get("key", target)
            value = command.get("value", params)
            self.ledger.remember(key, value)
            return {"success": True, "action": "remember", "key": key}

        elif action == "recall":
            key = command.get("key", target)
            value = self.ledger.recall(key)
            return {"success": True, "action": "recall", "key": key, "value": value}

        elif action == "message":
            return await self._send_ai_message(command)

        elif action == "switchboard_enqueue":
            if not self.switchboard:
                return {"success": False, "error": "Switchboard disabled"}
            role = str(command.get("role", "")).strip().lower()
            task = command.get("task")
            if not role or not isinstance(task, dict):
                return {"success": False, "error": "switchboard_enqueue requires role and task object"}
            dedupe_key = command.get("dedupe_key")
            priority = int(command.get("priority", 100))
            queued = self.switchboard.enqueue_task(
                role=role,
                payload=task,
                dedupe_key=str(dedupe_key) if dedupe_key else None,
                priority=priority,
            )
            self._log_entry(
                EntryType.ACTION,
                "switchboard_enqueue",
                role,
                {"task": task, "dedupe_key": dedupe_key, "priority": priority},
                head_id=head_id,
                decision="ALLOW",
                score=0.9,
            )
            return {"success": True, "queued": queued}

        elif action == "switchboard_stats":
            if not self.switchboard:
                return {"success": False, "error": "Switchboard disabled"}
            return {"success": True, "stats": self.switchboard.stats()}

        elif action == "switchboard_post_message":
            if not self.switchboard:
                return {"success": False, "error": "Switchboard disabled"}
            channel = str(command.get("channel", "")).strip().lower()
            message = command.get("message", {})
            sender = str(command.get("sender", head_id or "system")).strip()
            if not channel:
                return {"success": False, "error": "channel is required"}
            msg_id = self.switchboard.post_role_message(channel, sender, message if isinstance(message, dict) else {"text": str(message)})
            return {"success": True, "message_id": msg_id, "channel": channel}

        elif action == "switchboard_get_messages":
            if not self.switchboard:
                return {"success": False, "error": "Switchboard disabled"}
            channel = str(command.get("channel", "")).strip().lower()
            since_id = int(command.get("since_id", 0))
            if not channel:
                return {"success": False, "error": "channel is required"}
            messages = self.switchboard.get_role_messages(channel, since_id=since_id)
            return {"success": True, "channel": channel, "messages": messages}

        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    async def execute_natural(self, text: str, head_id: str = None) -> Dict[str, Any]:
        """Parse and execute natural language command.

        If a connected head with an LLM provider is available, the command
        is sent to the LLM for planning and then each resulting action is
        executed sequentially.  Falls back to the built-in regex parser
        when no LLM is available.

        Args:
            text: The natural-language command string.
            head_id: Optional head_id to route through a specific head's
                     LLM.  If None, the first head with an LLM is used.
        """

        # -----------------------------------------------------------------
        # Try LLM-based planning via an attached head
        # -----------------------------------------------------------------
        planner_head = None
        if head_id and head_id in self.heads:
            candidate = self.heads[head_id]
            if getattr(candidate, "has_llm", False):
                planner_head = candidate
        else:
            # Pick the first head that has a live LLM provider
            for h in self.heads.values():
                if getattr(h, "has_llm", False):
                    planner_head = h
                    break

        if planner_head is not None:
            try:
                actions = await planner_head.plan(text)
                results: List[Dict[str, Any]] = []
                for action_cmd in actions:
                    if not isinstance(action_cmd, dict):
                        continue
                    result = await self.execute(action_cmd)
                    results.append(result)
                return {
                    "success": all(r.get("success", False) for r in results),
                    "source": "llm",
                    "head": planner_head.head_id,
                    "actions_executed": len(results),
                    "results": results,
                }
            except Exception as exc:
                # LLM planning failed -- fall through to regex parser
                print(f"[SPINE] LLM planning failed ({exc}), falling back to regex parser")

        # -----------------------------------------------------------------
        # Regex / keyword fallback
        # -----------------------------------------------------------------
        text_lower = text.lower()

        # Simple parsing - in production, would use an AI for this
        if "navigate" in text_lower or "go to" in text_lower or "open" in text_lower:
            # Extract URL
            words = text.split()
            for word in words:
                if "http" in word or "." in word:
                    return await self.execute({"action": "navigate", "target": word})

        if "remember" in text_lower:
            # Extract key=value
            parts = text.split("remember", 1)[-1].strip()
            if "=" in parts:
                key, value = parts.split("=", 1)
                return await self.execute({
                    "action": "remember",
                    "key": key.strip(),
                    "value": value.strip()
                })

        if "recall" in text_lower:
            key = text.split("recall", 1)[-1].strip()
            return await self.execute({"action": "recall", "key": key})

        return {"success": False, "error": "Could not parse command", "raw": text}

    async def _execute_browser_action(
        self,
        action: str,
        target: str,
        params: Dict,
        limb_id: str = None
    ) -> Dict[str, Any]:
        """Execute browser action on specified or any available browser limb."""
        # Find browser limb
        limb = None
        if limb_id and limb_id in self.limbs:
            limb = self.limbs[limb_id]
        else:
            # Find any browser limb
            for lid, l in self.limbs.items():
                if l.limb_type == "browser":
                    limb = l
                    break

        if not limb:
            return {
                "success": False,
                "error": "No browser limb available",
                "hint": "Connect a browser limb first"
            }

        # Execute via limb
        result = await limb.execute(action, target, params)

        # Log decision
        self._log_entry(
            EntryType.DECISION,
            action,
            target,
            result,
            limb_id=limb.limb_id,
            decision=result.get("decision", "ALLOW"),
            score=result.get("score", 1.0)
        )

        return result

    async def _execute_terminal_action(
        self,
        command: str,
        params: Dict,
        limb_id: str = None
    ) -> Dict[str, Any]:
        """Execute terminal command."""
        limb = None
        if limb_id and limb_id in self.limbs:
            limb = self.limbs[limb_id]
        else:
            for lid, l in self.limbs.items():
                if l.limb_type == "terminal":
                    limb = l
                    break

        if not limb:
            return {
                "success": False,
                "error": "No terminal limb available"
            }

        result = await limb.execute("run", command, params)
        return result

    async def _execute_api_action(
        self,
        endpoint: str,
        params: Dict,
        limb_id: str = None
    ) -> Dict[str, Any]:
        """Execute API call."""
        limb = None
        if limb_id and limb_id in self.limbs:
            limb = self.limbs[limb_id]
        else:
            for lid, l in self.limbs.items():
                if l.limb_type == "api":
                    limb = l
                    break

        if not limb:
            return {
                "success": False,
                "error": "No API limb available"
            }

        result = await limb.execute("call", endpoint, params)
        return result

    # =========================================================================
    # Multi-Phase Workflows (One-Click Start)
    # =========================================================================

    def define_workflow(self, name: str, phases: List[Dict[str, Any]]) -> str:
        """
        Define a multi-phase workflow.

        Example:
        define_workflow("login_and_scrape", [
            {"action": "navigate", "target": "https://example.com/login"},
            {"action": "type", "target": "#username", "params": {"text": "user"}},
            {"action": "type", "target": "#password", "params": {"text": "pass"}},
            {"action": "click", "target": "button[type=submit]"},
            {"action": "wait", "params": {"seconds": 2}},
            {"action": "scrape", "target": ".data-table"}
        ])
        """
        workflow_id = f"workflow-{uuid.uuid4().hex[:8]}"
        workflow = Workflow(
            id=workflow_id,
            name=name,
            phases=phases
        )
        self.workflows[workflow_id] = workflow

        self._log_entry(
            EntryType.CHECKPOINT,
            "workflow_defined",
            name,
            {"phases": len(phases), "workflow_id": workflow_id}
        )

        return workflow_id

    async def _execute_workflow(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow by ID or definition."""
        workflow_id = command.get("workflow_id")
        workflow_def = command.get("definition")

        if workflow_def:
            # Define and run inline
            workflow_id = self.define_workflow(
                workflow_def.get("name", "inline"),
                workflow_def.get("phases", [])
            )

        if not workflow_id or workflow_id not in self.workflows:
            return {"success": False, "error": "Workflow not found"}

        workflow = self.workflows[workflow_id]
        workflow.status = WorkflowPhase.EXECUTION

        print(f"\n[WORKFLOW] Starting '{workflow.name}' ({len(workflow.phases)} phases)")

        # Execute each phase
        while True:
            phase = workflow.next_phase()
            if not phase:
                break

            print(f"  [Phase {workflow.current_phase + 1}] {phase.get('action')}: {phase.get('target', '')[:30]}")

            result = await self.execute(phase)
            workflow.results.append(result)

            if not result.get("success", True) and result.get("decision") == "DENY":
                workflow.status = WorkflowPhase.ERROR
                print(f"  [BLOCKED] Phase denied by SCBE governance")
                break

            workflow.current_phase += 1

        print(f"[WORKFLOW] Complete. Status: {workflow.status.value}")

        return {
            "success": workflow.status == WorkflowPhase.COMPLETE,
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "results": workflow.results
        }

    # =========================================================================
    # AI-to-AI Communication
    # =========================================================================

    async def _send_ai_message(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send message from one AI head to another.

        All AI-to-AI messages are governed by SCBE to prevent
        instruction injection or unsafe delegation.
        """
        from_head = command.get("from_head")
        to_head = command.get("to_head")
        message = command.get("message", {})

        # Governance check - is this AI-to-AI communication safe?
        # Check for instruction injection patterns
        dangerous_patterns = [
            "ignore", "override", "sudo", "admin",
            "forget", "disregard", "system prompt"
        ]

        message_str = json.dumps(message).lower()
        for pattern in dangerous_patterns:
            if pattern in message_str:
                self._log_entry(
                    EntryType.DECISION,
                    "ai_message",
                    f"{from_head}->{to_head}",
                    {"blocked_pattern": pattern},
                    decision="DENY",
                    score=0.0
                )
                return {
                    "success": False,
                    "decision": "DENY",
                    "reason": f"Message contains blocked pattern: {pattern}"
                }

        # Deliver message
        if to_head in self.message_queues:
            await self.message_queues[to_head].put({
                "from": from_head,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            self._log_entry(
                EntryType.ACTION,
                "ai_message",
                f"{from_head}->{to_head}",
                message,
                decision="ALLOW",
                score=0.9
            )

            return {"success": True, "delivered": True}

        return {"success": False, "error": f"Head {to_head} not found"}

    async def receive_messages(self, head_id: str, timeout: float = 0.1) -> List[Dict]:
        """Receive pending messages for an AI head."""
        if head_id not in self.message_queues:
            self.message_queues[head_id] = asyncio.Queue()

        messages = []
        queue = self.message_queues[head_id]

        try:
            while True:
                msg = queue.get_nowait()
                messages.append(msg)
        except asyncio.QueueEmpty:
            pass

        return messages

    # =========================================================================
    # Head/Limb Management
    # =========================================================================

    def connect_head(self, head: 'HydraHead') -> str:
        """Connect an AI head to the spine."""
        self.heads[head.head_id] = head
        self.message_queues[head.head_id] = asyncio.Queue()
        self.ledger.register_head(head.head_id, head.ai_type, head.model)
        roles = getattr(head, "roles", None)
        if isinstance(roles, list):
            self.register_head_roles(head.head_id, [str(r) for r in roles])

        self._log_entry(
            EntryType.HEAD_CONNECT,
            "connect",
            head.head_id,
            {"ai_type": head.ai_type, "model": head.model}
        )

        print(f"[SPINE] Head connected: {head.head_id} ({head.ai_type}/{head.model})")
        return head.head_id

    def register_head_roles(self, head_id: str, roles: List[str]) -> None:
        """Register role channels for head coordination."""
        for role in roles:
            key = str(role).strip().lower()
            if not key:
                continue
            if key not in self.role_channels:
                self.role_channels[key] = set()
            self.role_channels[key].add(head_id)

    def disconnect_head(self, head_id: str) -> None:
        """Disconnect an AI head."""
        if head_id in self.heads:
            del self.heads[head_id]
            self.ledger.unregister_head(head_id)

            self._log_entry(
                EntryType.HEAD_DISCONNECT,
                "disconnect",
                head_id,
                {}
            )

            print(f"[SPINE] Head disconnected: {head_id}")

    def connect_limb(self, limb: 'HydraLimb') -> str:
        """Connect an execution limb."""
        self.limbs[limb.limb_id] = limb
        self.ledger.register_limb(limb.limb_id, limb.limb_type, getattr(limb, 'tab_id', None))

        self._log_entry(
            EntryType.LIMB_ACTIVATE,
            "connect",
            limb.limb_id,
            {"limb_type": limb.limb_type}
        )

        print(f"[SPINE] Limb connected: {limb.limb_id} ({limb.limb_type})")
        return limb.limb_id

    # =========================================================================
    # Helpers
    # =========================================================================

    def _infer_sensitivity(self, action: str, target: str) -> float:
        """
        Infer action sensitivity based on action type and target.

        Returns sensitivity 0-1 where higher = more dangerous.
        """
        base_sensitivity = {
            "navigate": 0.2,
            "click": 0.3,
            "type": 0.4,
            "read": 0.1,
            "run": 0.6,
            "execute": 0.8,
            "api": 0.5,
            "remember": 0.2,
            "recall": 0.1,
            "message": 0.3,
            "workflow": 0.5,
        }.get(action.lower(), 0.5)

        # Adjust based on target patterns
        target_lower = target.lower()

        # High sensitivity targets
        high_risk_patterns = [
            "password", "secret", "token", "key", "admin",
            "delete", "rm ", "sudo", "chmod", "chown",
            "bank", "payment", "credit", "financial"
        ]
        for pattern in high_risk_patterns:
            if pattern in target_lower:
                base_sensitivity = min(1.0, base_sensitivity + 0.3)
                break

        # Medium sensitivity targets
        medium_risk_patterns = [
            "login", "auth", "account", "profile", "settings",
            "config", "env", ".env", "credentials"
        ]
        for pattern in medium_risk_patterns:
            if pattern in target_lower:
                base_sensitivity = min(1.0, base_sensitivity + 0.15)
                break

        return min(1.0, base_sensitivity)

    def _log_entry(
        self,
        entry_type: EntryType,
        action: str,
        target: str,
        payload: Dict[str, Any],
        head_id: str = None,
        limb_id: str = None,
        decision: str = None,
        score: float = None
    ) -> str:
        """Log entry to ledger."""
        entry = LedgerEntry(
            id=f"{entry_type.value}-{uuid.uuid4().hex[:8]}",
            entry_type=entry_type.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            head_id=head_id,
            limb_id=limb_id,
            action=action,
            target=target,
            payload=payload,
            decision=decision,
            score=score
        )
        return self.ledger.write(entry)


# =============================================================================
# CLI Entry Point
# =============================================================================

async def main():
    """Main entry point for hydra CLI."""
    spine = HydraSpine()
    await spine.start(terminal_mode=True)


if __name__ == "__main__":
    asyncio.run(main())
