from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket

from .audit import AuditWriter
from .gate import govern
from .handlers.echo import echo_handler
from .handlers.llm_chat import llm_chat_handler
from .models import OperationError, OperationRequest, OperationResult
from .registry import OperationRegistry

app = FastAPI(title="Aether Desktop Backend", version="0.1.0")

_registry = OperationRegistry()
_registry.register("echo", echo_handler)

_audit = AuditWriter()

# WS event queues keyed by request_id; populated before /v1/op is called.
_event_queues: dict[str, asyncio.Queue] = {}


async def _llm_chat_with_events(req: OperationRequest) -> OperationResult:
    queue = _event_queues.get(req.request_id)
    return await llm_chat_handler(req, event_queue=queue)


_registry.register("llm.chat", _llm_chat_with_events)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/op")
async def op_endpoint(req: OperationRequest) -> OperationResult:
    decision = govern(req)
    _audit.write_request(req, decision)

    if decision.decision in ("DENY", "QUARANTINE"):
        result = OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(code=decision.decision, message=decision.reason),
        )
        _audit.complete(req.request_id, result)
        return result

    result = await _registry.dispatch(req)
    _audit.complete(req.request_id, result)
    return result


@app.websocket("/v1/events")
async def events_ws(websocket: WebSocket, request_id: str) -> None:
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues[request_id] = queue
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                break
            await websocket.send_json(event)
            if event.get("type") == "done":
                break
    finally:
        _event_queues.pop(request_id, None)
        await websocket.close()
