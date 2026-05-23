from __future__ import annotations

import os

from fastapi import HTTPException, Query, Request


async def require_api_key(
    request: Request,
    query_key: str | None = Query(None, alias="api_key"),
) -> None:
    required = os.getenv("AETHER_DESKTOP_API_KEY", "")
    if not required:
        return  # dev mode: open
    actual = request.headers.get("X-API-Key") or query_key
    if actual != required:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
