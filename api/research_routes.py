"""
Research upload, retrieval, and grounded chat routes.

This router gives the website and other AI clients a governed access path for:
- uploading research records,
- searching stored research,
- retrieving full documents,
- proxying grounded chat requests through Hugging Face with server-side auth.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .auth import CustomerContext, verify_api_key_with_legacy

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESEARCH_STORE_DIR = ROOT / "artifacts" / "research_api"
HF_CHAT_ROUTER_URL = os.environ.get(
    "HF_CHAT_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions"
).strip()
TERM_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")

router = APIRouter(prefix="/v1/research", tags=["Research"])


class ResearchUploadRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=240)
    content: str = Field(..., min_length=1)
    source_url: Optional[str] = Field(default=None, max_length=1000)
    source_type: str = Field(default="note", max_length=64)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResearchUploadResponse(BaseModel):
    document_id: str
    duplicate: bool
    content_hash: str
    stored_at: str


class ResearchSearchHit(BaseModel):
    document_id: str
    title: str
    source_type: str
    source_url: Optional[str]
    tags: List[str]
    snippet: str
    score: int
    updated_at: str


class ResearchSearchResponse(BaseModel):
    query: str
    count: int
    hits: List[ResearchSearchHit]


class ResearchDocumentResponse(BaseModel):
    document_id: str
    title: str
    content: str
    source_type: str
    source_url: Optional[str]
    tags: List[str]
    metadata: Dict[str, Any]
    content_hash: str
    created_at: str
    updated_at: str


class ChatMessage(BaseModel):
    role: str
    content: Any


class ResearchChatRequest(BaseModel):
    model: str = Field(..., min_length=1)
    messages: List[ChatMessage] = Field(..., min_length=1)
    max_tokens: int = Field(default=480, ge=32, le=4096)
    temperature: float = Field(default=0.45, ge=0.0, le=2.0)
    stream: bool = Field(default=False)
    search_limit: int = Field(default=4, ge=1, le=12)


def _research_store_dir() -> Path:
    configured = os.environ.get("SCBE_RESEARCH_STORE_DIR", "").strip()
    base = Path(configured) if configured else DEFAULT_RESEARCH_STORE_DIR
    documents_dir = base / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    return documents_dir


def _document_path(document_id: str) -> Path:
    return _research_store_dir() / f"{document_id}.json"


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text.strip()
    return ""


def _content_hash(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _safe_tags(tags: List[str]) -> List[str]:
    clean: List[str] = []
    seen: set[str] = set()
    for tag in tags:
        text = str(tag or "").strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        clean.append(text[:64])
    return clean


def _load_all_documents() -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    for path in sorted(_research_store_dir().glob("*.json")):
        try:
            documents.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return documents


def _find_by_hash(content_hash: str) -> Optional[Dict[str, Any]]:
    for document in _load_all_documents():
        if document.get("content_hash") == content_hash:
            return document
    return None


def _query_terms(query: str) -> List[str]:
    return [term.lower() for term in TERM_RE.findall(query or "")]


def _document_search_text(document: Dict[str, Any]) -> str:
    parts = [
        str(document.get("title", "")),
        str(document.get("content", "")),
        str(document.get("source_type", "")),
        str(document.get("source_url", "")),
        " ".join(str(tag) for tag in document.get("tags", [])),
        json.dumps(document.get("metadata", {}), sort_keys=True),
    ]
    return "\n".join(parts).lower()


def _score_document(document: Dict[str, Any], terms: List[str]) -> int:
    if not terms:
        return 0
    title = str(document.get("title", "")).lower()
    tags = " ".join(str(tag) for tag in document.get("tags", [])).lower()
    haystack = _document_search_text(document)
    score = 0
    for term in terms:
        if term in title:
            score += 5
        if term in tags:
            score += 3
        if term in haystack:
            score += 1
    return score


def _build_snippet(content: str, terms: List[str], radius: int = 180) -> str:
    text = re.sub(r"\s+", " ", content).strip()
    if not text:
        return ""
    lowered = text.lower()
    start = 0
    for term in terms:
        idx = lowered.find(term)
        if idx >= 0:
            start = max(0, idx - radius // 2)
            end = min(len(text), idx + len(term) + radius)
            snippet = text[start:end].strip()
            if start > 0:
                snippet = f"...{snippet}"
            if end < len(text):
                snippet = f"{snippet}..."
            return snippet
    return text[:radius] + ("..." if len(text) > radius else "")


def _search_documents(query: str, limit: int) -> List[ResearchSearchHit]:
    terms = _query_terms(query)
    hits: List[ResearchSearchHit] = []
    for document in _load_all_documents():
        score = _score_document(document, terms)
        if score <= 0:
            continue
        hits.append(
            ResearchSearchHit(
                document_id=str(document["document_id"]),
                title=str(document.get("title", "")),
                source_type=str(document.get("source_type", "")),
                source_url=document.get("source_url"),
                tags=[str(tag) for tag in document.get("tags", [])],
                snippet=_build_snippet(str(document.get("content", "")), terms),
                score=score,
                updated_at=str(document.get("updated_at", "")),
            )
        )
    hits.sort(key=lambda item: (-item.score, item.updated_at, item.document_id))
    return hits[:limit]


def _grounding_block(hits: List[ResearchSearchHit], documents: List[Dict[str, Any]]) -> str:
    if not hits:
        return ""
    docs_by_id = {str(doc["document_id"]): doc for doc in documents}
    lines = [
        "Use the following SCBE research context when it is relevant.",
        "Cite the document title or source URL when you rely on it.",
        "If the context is insufficient, say so instead of inventing facts.",
        "",
    ]
    for hit in hits:
        document = docs_by_id.get(hit.document_id, {})
        lines.extend(
            [
                f"[{hit.document_id}] {hit.title}",
                f"source_type: {hit.source_type}",
                f"source_url: {hit.source_url or ''}",
                f"tags: {', '.join(hit.tags)}",
                f"snippet: {hit.snippet}",
                f"full_content: {str(document.get('content', ''))[:2400]}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _hf_token() -> str:
    for env_name in ("HF_TOKEN", "HUGGINGFACE_API_KEY", "HF_API_KEY"):
        token = os.environ.get(env_name, "").strip()
        if token:
            return token
    raise HTTPException(
        status_code=503,
        detail="HF_TOKEN (or HF_API_KEY / HUGGINGFACE_API_KEY) is not configured on the server.",
    )


def _mobile_chat_bypass_enabled() -> bool:
    return os.environ.get("SCBE_ALLOW_LOCAL_MOBILE_CHAT", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _call_huggingface_chat(
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
    temperature: float,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        HF_CHAT_ROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_hf_token()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise HTTPException(status_code=502, detail=f"Hugging Face router error: {detail[:400]}")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Hugging Face router unavailable: {exc.reason}")

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Hugging Face router returned invalid JSON.")

    text = _normalize_text(data.get("choices", [{}])[0].get("message", {}).get("content"))
    if not text:
        text = _normalize_text(data.get("message", {}).get("content"))
    if not text:
        text = _normalize_text(data.get("content"))
    if not text:
        text = _normalize_text(data.get("generated_text"))
    if not text:
        text = _normalize_text(data.get("text"))
    if not text:
        raise HTTPException(status_code=502, detail="Hugging Face router returned no assistant text.")
    return text


def _run_grounded_chat(request: ResearchChatRequest) -> Dict[str, Any]:
    latest_user_message = ""
    for message in reversed(request.messages):
        if message.role == "user":
            latest_user_message = _normalize_text(message.content)
            if latest_user_message:
                break

    documents = _load_all_documents()
    hits = _search_documents(latest_user_message, request.search_limit) if latest_user_message else []
    grounding = _grounding_block(hits, documents)

    upstream_messages = [
        {"role": msg.role, "content": _normalize_text(msg.content) or str(msg.content)}
        for msg in request.messages
    ]
    if grounding:
        insert_at = 1 if upstream_messages and upstream_messages[0]["role"] == "system" else 0
        upstream_messages.insert(insert_at, {"role": "system", "content": grounding})

    assistant_text = _call_huggingface_chat(
        model=request.model,
        messages=upstream_messages,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": assistant_text},
                "finish_reason": "stop",
            }
        ],
        "research_hits": [hit.dict() for hit in hits],
    }


@router.post("/upload", response_model=ResearchUploadResponse)
async def upload_research(
    request: ResearchUploadRequest,
    _: CustomerContext = Depends(verify_api_key_with_legacy),
):
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Research content cannot be empty.")

    content_hash = _content_hash(content)
    existing = _find_by_hash(content_hash)
    if existing:
        return ResearchUploadResponse(
            document_id=str(existing["document_id"]),
            duplicate=True,
            content_hash=content_hash,
            stored_at=str(existing.get("updated_at") or existing.get("created_at") or _utc_now()),
        )

    document_id = f"doc-{content_hash[:16]}"
    now = _utc_now()
    payload = {
        "document_id": document_id,
        "title": request.title.strip(),
        "content": content,
        "source_url": (request.source_url or "").strip() or None,
        "source_type": request.source_type.strip() or "note",
        "tags": _safe_tags(request.tags),
        "metadata": request.metadata,
        "content_hash": content_hash,
        "created_at": now,
        "updated_at": now,
    }
    _document_path(document_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return ResearchUploadResponse(
        document_id=document_id,
        duplicate=False,
        content_hash=content_hash,
        stored_at=now,
    )


@router.get("/search", response_model=ResearchSearchResponse)
async def search_research(
    q: str = Query(..., min_length=1, description="Lexical search query"),
    limit: int = Query(10, ge=1, le=25),
    _: CustomerContext = Depends(verify_api_key_with_legacy),
):
    hits = _search_documents(q, limit)
    return ResearchSearchResponse(query=q, count=len(hits), hits=hits)


@router.get("/documents/{document_id}", response_model=ResearchDocumentResponse)
async def get_research_document(
    document_id: str,
    _: CustomerContext = Depends(verify_api_key_with_legacy),
):
    path = _document_path(document_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Research document not found.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Research document is unreadable.")
    return ResearchDocumentResponse(**data)


@router.post("/chat")
async def grounded_research_chat(
    request: ResearchChatRequest,
    _: CustomerContext = Depends(verify_api_key_with_legacy),
):
    return _run_grounded_chat(request)


@router.post("/mobile-chat")
async def grounded_mobile_chat(
    request: ResearchChatRequest,
):
    if not _mobile_chat_bypass_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "Local mobile chat is disabled. Set SCBE_ALLOW_LOCAL_MOBILE_CHAT=1 on the host "
                "to allow emulator or private device chat without entering provider keys."
            ),
        )
    return _run_grounded_chat(request)
