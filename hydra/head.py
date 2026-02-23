"""
HYDRA Head - Universal AI Interface
====================================

The "armor" that any AI can wear to operate in the HYDRA system.
Works with Claude, Codex, GPT, local LLMs, or any AI.

Features:
- Universal interface for any AI
- Automatic SCBE governance
- Cross-AI message passing
- Workflow execution
- Polly Pad integration
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import uuid

from .llm_providers import LLMProvider, LLMResponse, create_provider, HYDRA_SYSTEM_PROMPT


class AIType(str, Enum):
    """Supported AI types."""
    CLAUDE = "claude"
    CODEX = "codex"
    GPT = "gpt"
    GEMINI = "gemini"
    LOCAL = "local"
    CUSTOM = "custom"


class HeadStatus(str, Enum):
    """Head connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class HydraHead:
    """
    An AI head that connects to the HYDRA Spine.

    Any AI can become a HYDRA head by implementing the execute() method.
    The head provides:
    - SCBE governance for all actions
    - Message passing to other heads
    - Workflow orchestration
    - Central ledger access

    Usage:
        # Claude head
        head = HydraHead(ai_type="claude", model="opus")
        await head.connect(spine)
        result = await head.execute({"action": "navigate", "url": "..."})

        # Codex head
        head = HydraHead(ai_type="codex", model="code-davinci-002")
        await head.connect(spine)
    """

    ai_type: str = "claude"
    model: str = "sonnet"
    callsign: str = None
    head_id: str = field(default_factory=lambda: f"head-{uuid.uuid4().hex[:8]}")
    status: HeadStatus = HeadStatus.DISCONNECTED
    action_count: int = 0
    error_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Runtime state (set after connection)
    _spine: 'HydraSpine' = field(default=None, repr=False)
    _polly_pad: Optional[Dict] = field(default=None, repr=False)
    _provider: Optional[LLMProvider] = field(default=None, repr=False)

    def __post_init__(self):
        if self.callsign is None:
            # Generate callsign based on AI type
            prefixes = {
                "claude": "CT",   # Claude Trooper
                "codex": "CX",    # Codex
                "gpt": "GP",      # GPT
                "gemini": "GM",   # Gemini
                "local": "LC",    # Local
                "custom": "XX"    # Custom
            }
            prefix = prefixes.get(self.ai_type.lower(), "XX")
            self.callsign = f"{prefix}-{uuid.uuid4().hex[:4].upper()}"

        # Attempt to initialise the LLM provider for this head.
        # Non-fatal: if the required SDK is missing or no API key is set
        # the head still works for non-LLM operations (execute, workflows, etc.).
        self._provider = self._init_provider()

    # =========================================================================
    # LLM Provider Integration
    # =========================================================================

    def _init_provider(self) -> Optional[LLMProvider]:
        """Try to initialise an LLM provider based on ai_type and model.

        Returns None silently when the required package or API key is
        missing -- the head can still work without a live LLM connection.
        """
        # Map ai_type values that have a corresponding provider
        provider_types = {"claude", "gpt", "openai", "gemini", "google", "local", "anthropic", "huggingface", "hf"}
        key = self.ai_type.strip().lower()
        if key not in provider_types:
            return None
        try:
            # Let the factory pick the default model if self.model is a
            # short alias (e.g. "sonnet", "opus") -- pass it through so
            # users can override with a full model string.
            return create_provider(key, model=self.model)
        except (ImportError, ValueError) as exc:
            print(f"[HEAD] LLM provider not available for {self.ai_type}: {exc}")
            return None

    @property
    def has_llm(self) -> bool:
        """True if this head has a live LLM provider attached."""
        return self._provider is not None

    async def think(self, prompt: str, system: Optional[str] = None) -> str:
        """Call the LLM provider and return the text response.

        This is the simplest way to get an LLM completion through a
        HYDRA head.  The HYDRA system prompt is injected by default.

        Args:
            prompt: The user prompt / question.
            system: Optional system prompt override.

        Returns:
            The LLM's text response.

        Raises:
            RuntimeError: If no LLM provider is available on this head.
        """
        if self._provider is None:
            raise RuntimeError(
                f"Head {self.callsign} ({self.ai_type}) has no LLM provider. "
                "Ensure the required SDK is installed and the API key is set."
            )
        response: LLMResponse = await self._provider.complete(prompt, system=system)
        return response.text

    async def plan(self, task: str) -> List[Dict[str, Any]]:
        """Ask the LLM to decompose a task into executable HYDRA actions.

        The LLM is instructed to return a JSON array of action objects,
        each with at least an "action" key (one of: navigate, click,
        type, run, api) plus a "target" and optional "params".

        Args:
            task: Natural-language description of what needs to happen.

        Returns:
            A list of action dictionaries ready for ``head.execute()``.

        Raises:
            RuntimeError: If no LLM provider is available.
        """
        if self._provider is None:
            raise RuntimeError(
                f"Head {self.callsign} ({self.ai_type}) has no LLM provider. "
                "Ensure the required SDK is installed and the API key is set."
            )

        planning_prompt = (
            "You are a HYDRA planning agent. Decompose the following task "
            "into a JSON array of HYDRA action objects.\n\n"
            "Each action object MUST have:\n"
            '  - "action": one of "navigate", "click", "type", "run", "api"\n'
            '  - "target": the URL, selector, command, or endpoint\n'
            '  - "params": (optional) additional parameters dict\n\n'
            "Respond ONLY with valid JSON -- no markdown fences, no commentary.\n\n"
            f"Task: {task}"
        )

        response: LLMResponse = await self._provider.complete(
            planning_prompt,
            system=HYDRA_SYSTEM_PROMPT,
            temperature=0.3,  # Lower temperature for structured output
        )

        # Parse the JSON response robustly
        text = response.text.strip()
        # Strip markdown code fences if the LLM included them anyway
        if text.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = text.index("\n") if "\n" in text else 3
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            actions = json.loads(text)
        except json.JSONDecodeError:
            # Last resort: try to extract the first JSON array from the text
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                actions = json.loads(text[start:end + 1])
            else:
                raise ValueError(
                    f"LLM did not return valid JSON actions. Raw response:\n{response.text}"
                )

        if not isinstance(actions, list):
            actions = [actions]

        return actions

    async def connect(self, spine: 'HydraSpine') -> bool:
        """
        Connect this head to a HYDRA Spine.

        This is like putting on the armor - the head now has access
        to all HYDRA capabilities through the spine.
        """
        self.status = HeadStatus.CONNECTING

        try:
            self._spine = spine
            spine.connect_head(self)

            # Create message queue for this head
            if self.head_id not in spine.message_queues:
                spine.message_queues[self.head_id] = asyncio.Queue()

            self.status = HeadStatus.CONNECTED

            print(f"""
╔════════════════════════════════════════════════════════════════╗
║  HYDRA HEAD CONNECTED                                          ║
╠════════════════════════════════════════════════════════════════╣
║  Head ID:  {self.head_id:<50} ║
║  Callsign: {self.callsign:<50} ║
║  AI Type:  {self.ai_type:<50} ║
║  Model:    {self.model:<50} ║
║  Status:   {self.status.value:<50} ║
╚════════════════════════════════════════════════════════════════╝
            """)

            return True

        except Exception as e:
            self.status = HeadStatus.ERROR
            self.error_count += 1
            print(f"[HEAD] Connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the spine."""
        if self._spine:
            self._spine.disconnect_head(self.head_id)
            self._spine = None

        self.status = HeadStatus.DISCONNECTED
        print(f"[HEAD] {self.callsign} disconnected")

    async def execute(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command through the HYDRA spine.

        All commands are governed by SCBE before execution.
        Results are logged to the central ledger.
        """
        if self.status != HeadStatus.CONNECTED:
            return {
                "success": False,
                "error": f"Head not connected (status: {self.status.value})"
            }

        if not self._spine:
            return {"success": False, "error": "No spine connection"}

        self.status = HeadStatus.BUSY
        self.action_count += 1

        # Add head_id to command for tracking
        command["head_id"] = self.head_id

        try:
            result = await self._spine.execute(command)
            self.status = HeadStatus.CONNECTED
            return result

        except Exception as e:
            self.status = HeadStatus.ERROR
            self.error_count += 1
            return {"success": False, "error": str(e)}

    async def send_message(self, to_head: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to another HYDRA head.

        All inter-head messages are governed by SCBE to prevent
        instruction injection between AIs.
        """
        if not self._spine:
            return {"success": False, "error": "Not connected"}

        return await self._spine.execute({
            "action": "message",
            "from_head": self.head_id,
            "to_head": to_head,
            "message": message
        })

    async def receive_messages(self) -> list:
        """Receive pending messages from other heads."""
        if not self._spine:
            return []

        return await self._spine.receive_messages(self.head_id)

    async def remember(self, key: str, value: Any) -> bool:
        """Store a fact in the central ledger."""
        if not self._spine:
            return False

        result = await self._spine.execute({
            "action": "remember",
            "key": key,
            "value": value
        })
        return result.get("success", False)

    async def recall(self, key: str) -> Any:
        """Recall a fact from the central ledger."""
        if not self._spine:
            return None

        result = await self._spine.execute({
            "action": "recall",
            "key": key
        })
        return result.get("value")

    async def run_workflow(self, workflow_id: str = None, definition: Dict = None) -> Dict[str, Any]:
        """
        Execute a multi-phase workflow.

        Either provide a workflow_id for a pre-defined workflow,
        or pass a definition inline.
        """
        if not self._spine:
            return {"success": False, "error": "Not connected"}

        return await self._spine.execute({
            "action": "workflow",
            "workflow_id": workflow_id,
            "definition": definition
        })

    # =========================================================================
    # Polly Pad Integration
    # =========================================================================

    def equip_polly_pad(self, polly_pad: Dict[str, Any]) -> None:
        """
        Equip a Polly Pad to this head.

        The Polly Pad provides:
        - Hot-swappable capabilities
        - Mini-IDE interface
        - SCBE spectral identity
        """
        self._polly_pad = polly_pad
        print(f"[HEAD] {self.callsign} equipped Polly Pad: {polly_pad.get('id', 'unknown')}")

    def get_loadout(self) -> list:
        """Get the current capability loadout from Polly Pad."""
        if self._polly_pad:
            return self._polly_pad.get("loadout", [])
        return []

    def has_capability(self, capability_id: str) -> bool:
        """Check if this head has a specific capability."""
        loadout = self.get_loadout()
        return any(cap.get("id") == capability_id for cap in loadout)

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        return await self.execute({"action": "navigate", "target": url})

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element."""
        return await self.execute({"action": "click", "target": selector})

    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Type text into an element."""
        return await self.execute({
            "action": "type",
            "target": selector,
            "params": {"text": text}
        })

    async def run_command(self, command: str) -> Dict[str, Any]:
        """Run a terminal command."""
        return await self.execute({"action": "run", "target": command})

    async def call_api(self, url: str, method: str = "GET", body: Dict = None) -> Dict[str, Any]:
        """Make an API call."""
        return await self.execute({
            "action": "api",
            "target": url,
            "params": {"method": method, "body": body or {}}
        })


# =============================================================================
# Head Factory Functions
# =============================================================================

def create_claude_head(model: str = "sonnet", callsign: str = None) -> HydraHead:
    """Create a Claude head."""
    return HydraHead(ai_type="claude", model=model, callsign=callsign)


def create_codex_head(model: str = "code-davinci-002", callsign: str = None) -> HydraHead:
    """Create a Codex head."""
    return HydraHead(ai_type="codex", model=model, callsign=callsign)


def create_gpt_head(model: str = "gpt-4", callsign: str = None) -> HydraHead:
    """Create a GPT head."""
    return HydraHead(ai_type="gpt", model=model, callsign=callsign)


def create_local_head(model: str = "llama-3", callsign: str = None) -> HydraHead:
    """Create a local LLM head."""
    return HydraHead(ai_type="local", model=model, callsign=callsign)
