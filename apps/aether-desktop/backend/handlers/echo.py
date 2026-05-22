from __future__ import annotations

from ..models import OperationRequest, OperationResult


async def echo_handler(req: OperationRequest) -> OperationResult:
    return OperationResult(
        request_id=req.request_id,
        ok=True,
        output={"echo": req.args.get("msg", ""), "op": req.op, "args": req.args},
    )
