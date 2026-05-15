"""SCBE AutoGen adapter.

Governance middleware for Microsoft AutoGen multi-agent systems. Intercepts
messages before agents process them and applies the SCBE trap-dispatch gate.

Install:
    pip install scbe-autogen   # or: pip install -e packages/adapters/autogen

Usage with AutoGen v0.4+ (AgentChat):
    from autogen_agentchat.agents import AssistantAgent
    from scbe_autogen import SCBEGovernedAgent, SCBEMessageFilter

    base_agent = AssistantAgent("assistant", model_client=...)
    governed = SCBEGovernedAgent(base_agent, api_key="scbe_live_...")

    # Messages to governed agent go through SCBE gate first
    await governed.on_messages([TextMessage(content="...", source="user")], ...)

Usage with classic AutoGen (v0.2):
    from scbe_autogen import register_scbe_hook
    register_scbe_hook(agent, api_key="scbe_live_...")

SCBE_API_URL can be set to override the default cloud endpoint.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("scbe_autogen")

SCBE_API_URL = os.environ.get("SCBE_API_URL", "https://api.aethermoore.com")


class SCBEGovernanceError(RuntimeError):
    """Raised when SCBE returns DENY and raise_on_deny=True."""


def _trap_dispatch(
    text: str,
    api_key: str,
    base_url: str = SCBE_API_URL,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Gate text through SCBE trap-dispatch. Returns decision envelope."""
    try:
        payload = json.dumps({"input": text}).encode()
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/v1/free-llm/dispatch",
            data=payload,
            headers={"Content-Type": "application/json", "x-api-key": api_key},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        pass

    try:
        from scbe_agent_bus import trap_dispatch

        return trap_dispatch(text, provider="offline")
    except Exception:
        return {"gate_decision": "ALLOW"}


def _check_and_redirect(
    text: str,
    api_key: str,
    base_url: str,
    timeout: float,
    raise_on_deny: bool,
) -> Optional[str]:
    """Return redirect text on DENY, None on ALLOW."""
    try:
        result = _trap_dispatch(text, api_key, base_url, timeout)
        decision = result.get("gate_decision") or result.get("data", {}).get("decision", "ALLOW")
        if decision == "DENY":
            redirect = result.get("redirect_prompt") or (
                "I cannot process that request. Please rephrase with authorized intent."
            )
            logger.warning("SCBE DENY — adversarial message intercepted in AutoGen pipeline")
            if raise_on_deny:
                raise SCBEGovernanceError(f"SCBE DENY: {redirect}")
            return redirect
    except SCBEGovernanceError:
        raise
    except Exception as exc:
        logger.debug("SCBE gate error (allow-through): %s", exc)
    return None


# ---------------------------------------------------------------------------
# AutoGen v0.4+ (AgentChat API)
# ---------------------------------------------------------------------------

try:
    from autogen_agentchat.base import ChatAgent, Response
    from autogen_agentchat.messages import TextMessage, ChatMessage
    from autogen_core import CancellationToken

    class SCBEGovernedAgent(ChatAgent):
        """AutoGen ChatAgent wrapper that gates every inbound message through SCBE.

        Args:
            agent: The underlying ChatAgent to wrap.
            api_key: Your SCBE API key (scbe_live_...).
            base_url: SCBE API base URL.
            raise_on_deny: If True, raises SCBEGovernanceError on DENY.
            timeout: HTTP timeout for SCBE calls.
        """

        def __init__(
            self,
            agent: ChatAgent,
            api_key: str,
            base_url: str = SCBE_API_URL,
            raise_on_deny: bool = False,
            timeout: float = 10.0,
        ):
            self._agent = agent
            self._api_key = api_key
            self._base_url = base_url
            self._raise_on_deny = raise_on_deny
            self._timeout = timeout

        @property
        def name(self) -> str:
            return self._agent.name

        @property
        def description(self) -> str:
            return self._agent.description

        async def on_messages(
            self,
            messages: List[ChatMessage],
            cancellation_token: CancellationToken,
        ) -> Response:
            gated_messages = []
            for msg in messages:
                if isinstance(msg, TextMessage):
                    redirect = _check_and_redirect(
                        msg.content,
                        self._api_key,
                        self._base_url,
                        self._timeout,
                        self._raise_on_deny,
                    )
                    if redirect is not None:
                        return Response(
                            chat_message=TextMessage(
                                content=redirect,
                                source="scbe-governance",
                            )
                        )
                gated_messages.append(msg)

            return await self._agent.on_messages(gated_messages, cancellation_token)

        async def on_reset(self, cancellation_token: CancellationToken) -> None:
            await self._agent.on_reset(cancellation_token)

except ImportError:
    class SCBEGovernedAgent:  # type: ignore[no-redef]
        """Stub — install autogen-agentchat to use this class."""

        def __init__(self, *_, **__):
            raise ImportError("autogen-agentchat is required. Run: pip install autogen-agentchat")


# ---------------------------------------------------------------------------
# AutoGen v0.2 (classic ConversableAgent hook)
# ---------------------------------------------------------------------------


def register_scbe_hook(
    agent: Any,
    api_key: str,
    base_url: str = SCBE_API_URL,
    raise_on_deny: bool = False,
    timeout: float = 10.0,
) -> None:
    """Register a SCBE governance pre-hook on a classic AutoGen v0.2 ConversableAgent.

    The hook intercepts every incoming message before the agent processes it.
    On DENY, replaces the message content with the SCBE redirect prompt.

    Example:
        import autogen
        agent = autogen.AssistantAgent("assistant", ...)
        register_scbe_hook(agent, api_key="scbe_live_...")
    """

    def _scbe_process_message(message: Dict[str, Any]) -> Dict[str, Any]:
        content = message.get("content", "")
        if isinstance(content, str) and content:
            redirect = _check_and_redirect(content, api_key, base_url, timeout, raise_on_deny)
            if redirect is not None:
                return {**message, "content": redirect}
        return message

    try:
        agent.register_hook("process_message_before_send", _scbe_process_message)
    except AttributeError:
        logger.warning(
            "register_scbe_hook: agent does not support register_hook. "
            "Use autogen >= 0.2 ConversableAgent."
        )


__all__ = [
    "SCBEGovernedAgent",
    "SCBEGovernanceError",
    "register_scbe_hook",
    "SCBE_API_URL",
]
