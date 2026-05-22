from __future__ import annotations

import asyncio
import json
import os

import httpx

from ..models import OperationError, OperationRequest, OperationResult

OLLAMA_URL = os.getenv("AETHER_DESKTOP_OLLAMA_URL", os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat"))
DEFAULT_MODEL = os.getenv("AETHER_DESKTOP_DEFAULT_MODEL", "llama3")


async def llm_chat_handler(
    req: OperationRequest,
    event_queue: asyncio.Queue | None = None,
) -> OperationResult:
    messages = req.args.get("messages", [])
    model = req.args.get("model", DEFAULT_MODEL)
    content_parts: list[str] = []
    url = str(req.args.get("provider_url") or OLLAMA_URL)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                json={"model": model, "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        content_parts.append(token)
                        if event_queue is not None:
                            await event_queue.put({"type": "token", "request_id": req.request_id, "content": token})
    except httpx.ConnectError:
        await _emit_done(event_queue, req.request_id, "OLLAMA_UNAVAILABLE")
        return OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(
                code="OLLAMA_UNAVAILABLE",
                message=f"Could not connect to Ollama at {url}",
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
