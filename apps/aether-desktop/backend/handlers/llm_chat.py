from __future__ import annotations

import asyncio
import json
import os

import httpx

from ..models import OperationError, OperationRequest, OperationResult

# ── provider constants ────────────────────────────────────────────────────────

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"

_OLLAMA_URL = "http://localhost:11434/api/chat"
_OLLAMA_DEFAULT_MODEL = "llama3"


def _llm_config(provider_url: str | None) -> tuple[str, str, dict[str, str], bool]:
    """Return (url, default_model, extra_headers, is_openai_compat).

    Priority: explicit provider_url > GROQ_API_KEY > OLLAMA_URL env > localhost Ollama.
    Computed at call time so monkeypatch.setenv works in tests.
    """
    groq_key = os.getenv("GROQ_API_KEY", "")
    ollama_url = os.getenv("AETHER_DESKTOP_OLLAMA_URL", os.getenv("OLLAMA_URL", _OLLAMA_URL))

    if provider_url:
        url = provider_url
    elif groq_key:
        url = _GROQ_URL
    else:
        url = ollama_url

    headers: dict[str, str] = {}
    if "groq.com" in url and groq_key:
        headers["Authorization"] = f"Bearer {groq_key}"

    is_openai_compat = "openai" in url or "groq.com" in url
    default_model = _GROQ_DEFAULT_MODEL if is_openai_compat else _OLLAMA_DEFAULT_MODEL
    default_model = os.getenv("AETHER_DESKTOP_DEFAULT_MODEL", default_model)

    return url, default_model, headers, is_openai_compat


# ── streaming helpers ─────────────────────────────────────────────────────────


async def _stream_openai_compat(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    body: dict,
    event_queue: asyncio.Queue | None,
    request_id: str,
    content_parts: list[str],
) -> None:
    async with client.stream("POST", url, headers=headers, json=body) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            token = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if token:
                content_parts.append(token)
                if event_queue is not None:
                    await event_queue.put({"type": "token", "request_id": request_id, "content": token})


async def _stream_ollama(
    client: httpx.AsyncClient,
    url: str,
    body: dict,
    event_queue: asyncio.Queue | None,
    request_id: str,
    content_parts: list[str],
) -> None:
    async with client.stream("POST", url, json=body) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            if token:
                content_parts.append(token)
                if event_queue is not None:
                    await event_queue.put({"type": "token", "request_id": request_id, "content": token})


# ── handler ───────────────────────────────────────────────────────────────────


async def llm_chat_handler(
    req: OperationRequest,
    event_queue: asyncio.Queue | None = None,
) -> OperationResult:
    messages = req.args.get("messages", [])
    provider_url = str(req.args["provider_url"]) if "provider_url" in req.args else None
    url, default_model, headers, is_openai_compat = _llm_config(provider_url)
    model = str(req.args.get("model") or default_model)
    content_parts: list[str] = []

    body: dict = {"model": model, "messages": messages, "stream": True}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if is_openai_compat:
                await _stream_openai_compat(client, url, headers, body, event_queue, req.request_id, content_parts)
            else:
                await _stream_ollama(client, url, body, event_queue, req.request_id, content_parts)
    except httpx.ConnectError:
        await _emit_done(event_queue, req.request_id, "LLM_UNAVAILABLE")
        return OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(
                code="LLM_UNAVAILABLE",
                message=f"Could not connect to LLM at {url}",
            ),
        )
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        await _emit_done(event_queue, req.request_id, "LLM_CHAT_FAILED")
        return OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(code="LLM_CHAT_FAILED", message=str(exc)),
        )

    await _emit_done(event_queue, req.request_id)
    return OperationResult(
        request_id=req.request_id,
        ok=True,
        output={"content": "".join(content_parts)},
    )


async def _emit_done(
    event_queue: asyncio.Queue | None,
    request_id: str,
    error_code: str | None = None,
) -> None:
    if event_queue is None:
        return
    event: dict[str, str] = {"type": "done", "request_id": request_id}
    if error_code is not None:
        event["error_code"] = error_code
    await event_queue.put(event)
