from __future__ import annotations

import asyncio
import json

import httpx

from ..models import OperationError, OperationRequest, OperationResult

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3"


async def llm_chat_handler(
    req: OperationRequest,
    event_queue: asyncio.Queue | None = None,
) -> OperationResult:
    messages = req.args.get("messages", [])
    model = req.args.get("model", DEFAULT_MODEL)
    content_parts: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={"model": model, "messages": messages, "stream": True},
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        content_parts.append(token)
                        if event_queue is not None:
                            await event_queue.put(
                                {"type": "token", "request_id": req.request_id, "content": token}
                            )
    except httpx.ConnectError:
        return OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(
                code="OLLAMA_UNAVAILABLE",
                message="Could not connect to Ollama at localhost:11434",
            ),
        )

    if event_queue is not None:
        await event_queue.put({"type": "done", "request_id": req.request_id})

    return OperationResult(
        request_id=req.request_id,
        ok=True,
        output={"content": "".join(content_parts)},
    )
