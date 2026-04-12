"""
LLM proxy routes for SCBE-AETHERMOORE.

Security model:
- Never expose third-party API keys to browser bundles.
- All vendor calls are made server-side with keys loaded from environment variables.
- Requests are gated by SCBE API keys (x-api-key) for local/dev usage.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from src.api.auth_config import VALID_API_KEYS

logger = logging.getLogger("scbe.api.llm")

llm_router = APIRouter(prefix="/v1/llm", tags=["llm"])


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return VALID_API_KEYS[x_api_key]


class GeminiInlineData(BaseModel):
    mimeType: str = Field(..., description="MIME type, e.g. image/jpeg")
    data: str = Field(..., description="Base64-encoded data (no data: prefix)")


class GeminiContentPart(BaseModel):
    text: Optional[str] = None
    inlineData: Optional[GeminiInlineData] = None


class GeminiGenerateRequest(BaseModel):
    model: str = Field(default="gemini-1.5-flash", description="Gemini model id")
    contents: List[GeminiContentPart] = Field(
        ...,
        min_length=1,
        description="Ordered content parts (text and/or inlineData)",
    )
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, ge=1, le=8192)


class GeminiGenerateResponse(BaseModel):
    text: str
    provider: Literal["gemini"] = "gemini"
    model: str
    ts: int


def _resolve_gemini_api_key() -> Optional[str]:
    # Support both names to reduce ops friction.
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


@llm_router.post("/gemini/generate", response_model=GeminiGenerateResponse)
async def gemini_generate(request: GeminiGenerateRequest, x_api_key: str = Header(...)):
    """
    Server-side Gemini proxy.

    Requires SCBE API key (`x-api-key`) and runs vendor calls server-side.
    """
    _ = await verify_api_key(x_api_key)

    api_key = _resolve_gemini_api_key()
    if not api_key:
        # Fail-closed for external calls, but return a deterministic response to keep dev UX stable.
        return GeminiGenerateResponse(
            text="[Gemini disabled: set GEMINI_API_KEY or GOOGLE_API_KEY on the API server]",
            model=request.model,
            ts=int(time.time()),
        )

    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(request.model)

        parts: List[Any] = []
        for part in request.contents:
            if part.text:
                parts.append(part.text)
            if part.inlineData:
                try:
                    raw = base64.b64decode(part.inlineData.data)
                except Exception as exc:
                    raise HTTPException(status_code=400, detail=f"Invalid base64 inlineData: {exc}") from exc
                parts.append({"mime_type": part.inlineData.mimeType, "data": raw})

        resp = model.generate_content(
            parts if len(parts) > 1 else parts[0],
            generation_config=genai.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_output_tokens,
            ),
        )
        text = getattr(resp, "text", None) or "[empty Gemini response]"
        return GeminiGenerateResponse(text=text, model=request.model, ts=int(time.time()))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gemini proxy error")
        raise HTTPException(status_code=502, detail=f"Gemini proxy error: {exc}") from exc
