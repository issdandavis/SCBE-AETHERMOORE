from __future__ import annotations

import asyncio

from fastapi import FastAPI

from .audit import AuditWriter
from .gate import govern
from .handlers.echo import echo_handler
from .models import OperationError, OperationRequest, OperationResult
from .registry import OperationRegistry

app = FastAPI(title="Aether Desktop Backend", version="0.1.0")

_registry = OperationRegistry()
_registry.register("echo", echo_handler)

_audit = AuditWriter()

# Populated by the WS endpoint (Task 8); echo/gate tests don't need it.
_event_queues: dict[str, asyncio.Queue] = {}


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
