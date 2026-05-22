from __future__ import annotations

import time
from collections.abc import Callable, Coroutine
from typing import Any

from .models import OperationError, OperationRequest, OperationResult

Handler = Callable[[OperationRequest], Coroutine[Any, Any, OperationResult]]


class OperationRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, op: str, handler: Handler) -> None:
        self._handlers[op] = handler

    async def dispatch(self, req: OperationRequest) -> OperationResult:
        handler = self._handlers.get(req.op)
        if handler is None:
            return OperationResult(
                request_id=req.request_id,
                ok=False,
                error=OperationError(code="OP_NOT_FOUND", message=f"No handler registered for op: {req.op}"),
            )
        t0 = time.monotonic()
        result = await handler(req)
        return result.model_copy(update={"duration_ms": (time.monotonic() - t0) * 1000})
