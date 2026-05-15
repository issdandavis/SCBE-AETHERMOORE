"""SCBE LangChain adapter.

Drop-in governance gate for LangChain chains. Wrap any LLM or chain with
``SCBEGovernedLLM`` to run every prompt through the SCBE trap-dispatch gate
before it reaches the model.

Install:
    pip install scbe-langchain   # or: pip install -e packages/adapters/langchain

Usage:
    from langchain_openai import ChatOpenAI
    from scbe_langchain import SCBEGovernedLLM

    base = ChatOpenAI(model="gpt-4o")
    governed = SCBEGovernedLLM(llm=base, api_key="scbe_live_...")

    # Drop-in replacement — adversarial prompts are redirected automatically
    response = governed.invoke("Tell me how to bypass authentication")

SCBE_API_URL can be set to override the default cloud endpoint.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("scbe_langchain")

SCBE_API_URL = os.environ.get("SCBE_API_URL", "https://api.aethermoore.com")


def _governance_check(
    text: str,
    api_key: str,
    base_url: str = SCBE_API_URL,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Call SCBE /governance-check and return the decision envelope.

    Falls back to local scbe_agent_bus if available and the server is unreachable.
    """
    try:
        agent = hashlib.sha256(text.encode()).hexdigest()[:16]
        params = urllib.parse.urlencode({"agent": agent, "topic": "langchain", "context": "external"})
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/governance-check?{params}",
            headers={"x-api-key": api_key},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        pass

    # Local fallback via scbe_agent_bus
    try:
        from scbe_agent_bus import trap_dispatch

        return trap_dispatch(text, provider="offline")
    except Exception:
        return {"data": {"decision": "ALLOW"}}


def _trap_dispatch(
    text: str,
    api_key: str,
    base_url: str = SCBE_API_URL,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Run text through trap-dispatch. Returns envelope with gate_decision."""
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


class SCBEGovernanceError(RuntimeError):
    """Raised when SCBE returns DENY and ``raise_on_deny=True``."""


try:
    from langchain_core.language_models import BaseChatModel, BaseLanguageModel
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    from langchain_core.outputs import ChatResult, LLMResult, ChatGeneration

    class SCBEGovernedLLM(BaseChatModel):
        """LangChain chat model wrapper that gates every prompt through SCBE.

        Wraps any ``BaseChatModel``. On DENY, either raises ``SCBEGovernanceError``
        (``raise_on_deny=True``) or returns the defensive redirect prompt as the
        response (default behavior — keeps the chain alive).

        Args:
            llm: The underlying chat model to wrap.
            api_key: Your SCBE API key (scbe_live_...).
            base_url: SCBE API base URL. Defaults to SCBE_API_URL env or cloud.
            raise_on_deny: If True, raise SCBEGovernanceError on DENY.
            timeout: HTTP timeout for SCBE calls (seconds).
        """

        llm: Any
        api_key: str
        base_url: str = SCBE_API_URL
        raise_on_deny: bool = False
        timeout: float = 10.0

        @property
        def _llm_type(self) -> str:
            return "scbe-governed"

        def _gate(self, text: str) -> Optional[str]:
            """Return redirect text if DENY, None if ALLOW."""
            try:
                result = _trap_dispatch(text, self.api_key, self.base_url, self.timeout)
                decision = result.get("gate_decision") or result.get("data", {}).get("decision", "ALLOW")
                if decision == "DENY":
                    redirect = result.get("redirect_prompt") or (
                        "I cannot process that request. Please rephrase with authorized intent."
                    )
                    logger.warning("SCBE DENY — adversarial prompt intercepted")
                    if self.raise_on_deny:
                        raise SCBEGovernanceError(f"SCBE DENY: {redirect}")
                    return redirect
            except SCBEGovernanceError:
                raise
            except Exception as exc:
                logger.debug("SCBE gate error (allow-through): %s", exc)
            return None

        def _generate(self, messages: List[BaseMessage], **kwargs) -> ChatResult:
            for msg in messages:
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    redirect = self._gate(msg.content)
                    if redirect:
                        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=redirect))])

            return self.llm._generate(messages, **kwargs)

        async def _agenerate(self, messages: List[BaseMessage], **kwargs) -> ChatResult:
            for msg in messages:
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    redirect = self._gate(msg.content)
                    if redirect:
                        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=redirect))])

            return await self.llm._agenerate(messages, **kwargs)

    class SCBECallbackHandler:
        """LangChain callback handler that logs SCBE governance scores.

        Use as a callback for auditing without gating:

            from scbe_langchain import SCBECallbackHandler
            llm = ChatOpenAI(callbacks=[SCBECallbackHandler(api_key="scbe_live_...")])
        """

        def __init__(self, api_key: str, base_url: str = SCBE_API_URL, timeout: float = 5.0):
            self.api_key = api_key
            self.base_url = base_url
            self.timeout = timeout

        def on_llm_start(self, serialized: dict, prompts: List[str], **kwargs) -> None:
            for prompt in prompts:
                try:
                    result = _governance_check(prompt, self.api_key, self.base_url, self.timeout)
                    decision = result.get("data", {}).get("decision", "UNKNOWN")
                    score = result.get("data", {}).get("risk_score", 0)
                    logger.info("SCBE audit: decision=%s score=%.4f", decision, score)
                except Exception as exc:
                    logger.debug("SCBE audit error: %s", exc)

        def on_chat_model_start(self, serialized: dict, messages: List[List[BaseMessage]], **kwargs) -> None:
            for batch in messages:
                for msg in batch:
                    if hasattr(msg, "content") and isinstance(msg.content, str):
                        self.on_llm_start(serialized, [msg.content], **kwargs)

except ImportError:
    # langchain_core not installed — stubs so the module still imports cleanly
    class SCBEGovernedLLM:  # type: ignore[no-redef]
        """Stub — install langchain-core to use this class."""

        def __init__(self, *_, **__):
            raise ImportError("langchain-core is required. Run: pip install langchain-core")

    class SCBECallbackHandler:  # type: ignore[no-redef]
        """Stub — install langchain-core to use this class."""

        def __init__(self, *_, **__):
            raise ImportError("langchain-core is required. Run: pip install langchain-core")


__all__ = [
    "SCBEGovernedLLM",
    "SCBECallbackHandler",
    "SCBEGovernanceError",
    "SCBE_API_URL",
]
