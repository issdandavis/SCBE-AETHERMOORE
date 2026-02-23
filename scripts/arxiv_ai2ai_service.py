#!/usr/bin/env python3
"""
AI-to-AI arXiv Retrieval Service
================================

Local FastAPI service for multi-agent paper retrieval and handoff packets.

Run:
    uvicorn scripts.arxiv_ai2ai_service:app --host 127.0.0.1 --port 8099
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from hydra.arxiv_retrieval import AI2AIRetrievalService, ArxivAPIError
from hydra.ledger import Ledger
from hydra.librarian import Librarian


app = FastAPI(
    title="SCBE HYDRA AI2AI arXiv Retrieval Service",
    version="0.1.0",
    description="Agent handoff packets from arXiv search + outline generation.",
)


_ledger = Ledger()
_librarian = Librarian(_ledger)
_service = AI2AIRetrievalService(librarian=_librarian)
_REQUIRED_API_KEY = os.getenv("AI2AI_API_KEY", "").strip()


class ArxivRetrieveRequest(BaseModel):
    requester: str = Field(..., min_length=1, max_length=120)
    query: str = Field(..., min_length=1, max_length=512)
    category: Optional[str] = Field(default="cs.AI", max_length=32)
    max_results: int = Field(default=5, ge=1, le=50)
    remember: bool = True
    raw_query: bool = False


def _verify_api_key(x_api_key: Optional[str]) -> None:
    if not _REQUIRED_API_KEY:
        return
    if (x_api_key or "").strip() != _REQUIRED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "service": "ai2ai-arxiv", "memory_backend": "hydra-librarian"}


@app.post("/retrieve/arxiv", tags=["Retrieval"])
def retrieve_arxiv(
    request: ArxivRetrieveRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> dict:
    _verify_api_key(x_api_key)
    try:
        packet = _service.retrieve_arxiv_packet(
            requester=request.requester,
            query=request.query,
            category=request.category,
            max_results=request.max_results,
            remember=request.remember,
            raw_query=request.raw_query,
        )
    except ArxivAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # defensive catch for runtime reliability
        raise HTTPException(status_code=500, detail=f"retrieval failed: {exc}") from exc

    return {"status": "ok", "packet": packet}


@app.post("/retrieve/arxiv/outline", tags=["Retrieval"])
def retrieve_arxiv_outline(
    request: ArxivRetrieveRequest,
    x_api_key: Optional[str] = Header(default=None),
) -> dict:
    _verify_api_key(x_api_key)
    try:
        packet = _service.retrieve_arxiv_packet(
            requester=request.requester,
            query=request.query,
            category=request.category,
            max_results=request.max_results,
            remember=request.remember,
            raw_query=request.raw_query,
        )
        outline = _service.build_related_work_outline(packet)
    except ArxivAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # defensive catch for runtime reliability
        raise HTTPException(status_code=500, detail=f"outline generation failed: {exc}") from exc

    return {"status": "ok", "packet_id": packet["packet_id"], "outline": outline}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("scripts.arxiv_ai2ai_service:app", host="127.0.0.1", port=8099, reload=False)
