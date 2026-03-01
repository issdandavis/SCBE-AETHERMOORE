"""
PollyPad IDE — Local AI Gateway for Any Editor/Terminal/Browser
================================================================

FastAPI server that wraps OctoArmor's 20 tentacles into a local HTTP API.
Every IDE, terminal tool, or browser extension can call this to get
governed AI responses routed through the cheapest available provider.

Start::

    python -m uvicorn src.fleet.polly_pad_ide:app --host 127.0.0.1 --port 8200

Then from any editor or terminal::

    curl http://localhost:8200/chat -d '{"prompt":"Explain hyperbolic geometry"}'
    curl http://localhost:8200/code -d '{"prompt":"Write a Python fibonacci generator"}'
    curl http://localhost:8200/status

Architecture::

    IDE/Terminal/Browser
         │  HTTP
         ▼
    ┌─── PollyPad IDE (port 8200) ───┐
    │  /chat     /code    /research  │
    │  /govern   /status  /models    │
    │  /batch    /history /flush     │
    └──────────┬─────────────────────┘
               │
    ┌──── OctoArmor (20 tentacles) ──┐
    │  SCBE Tokenizer Gateway        │
    │  Polly Raven Observer          │
    │  Sacred Tongue Encoding        │
    │  Auto-fallback on failure      │
    └────────────────────────────────┘

Firebase sync (optional):
    Set FIREBASE_CREDENTIALS_PATH or FIREBASE_PROJECT_ID to enable
    persistent session storage and training data sync.

@module fleet/polly_pad_ide
@layer Layer 5, Layer 13, Layer 14
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# Project root setup
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

# Load .env
_env_path = REPO_ROOT / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                if _v and _k.strip():
                    os.environ.setdefault(_k.strip(), _v.strip())

from src.fleet.octo_armor import (
    OctoArmor,
    Tentacle,
    TENTACLE_REGISTRY,
    TONGUE_TASK_MAP,
)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError(
        "FastAPI + pydantic required: pip install fastapi uvicorn pydantic"
    )


# ═══════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    prompt: str
    task_type: Optional[str] = None
    tentacle: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    context: Optional[str] = None
    session_id: Optional[str] = None


class BatchRequest(BaseModel):
    prompts: List[ChatRequest]


class ChatResponse(BaseModel):
    status: str
    tentacle: Optional[str] = None
    model: Optional[str] = None
    tongue: Optional[str] = None
    response: Optional[str] = None
    latency_ms: Optional[float] = None
    quality: Optional[float] = None
    session_id: Optional[str] = None
    observation_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# Session Manager — In-memory conversation history
# ═══════════════════════════════════════════════════════════════

@dataclass
class PadSession:
    """A PollyPad IDE session — tracks conversation history."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    messages: List[Dict[str, str]] = field(default_factory=list)
    tongue: str = "KO"
    total_tokens: int = 0
    total_requests: int = 0

    def add_exchange(self, prompt: str, response: str, tongue: str) -> None:
        self.messages.append({"role": "user", "content": prompt})
        self.messages.append({"role": "assistant", "content": response})
        self.tongue = tongue
        self.total_tokens += len(prompt) // 4 + len(response) // 4
        self.total_requests += 1

    def get_context(self, max_turns: int = 6) -> str:
        """Build conversation context from recent history."""
        recent = self.messages[-(max_turns * 2):]
        parts = []
        for msg in recent:
            role = msg["role"]
            parts.append(f"[{role}]: {msg['content'][:500]}")
        return "\n".join(parts)


class SessionStore:
    """In-memory session store with optional Firebase sync."""

    def __init__(self):
        self._sessions: Dict[str, PadSession] = {}
        self._firebase_db = None

    def get_or_create(self, session_id: Optional[str] = None) -> PadSession:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        sid = session_id or f"pad-{uuid.uuid4().hex[:8]}"
        session = PadSession(session_id=sid)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Optional[PadSession]:
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at,
                "messages": len(s.messages),
                "tongue": s.tongue,
                "total_requests": s.total_requests,
            }
            for s in self._sessions.values()
        ]

    def init_firebase(self, project_id: str, credentials_path: Optional[str] = None):
        """Initialize Firebase Firestore for persistent session storage."""
        try:
            import firebase_admin
            from firebase_admin import credentials as fb_creds, firestore

            if not firebase_admin._apps:
                if credentials_path and Path(credentials_path).exists():
                    cred = fb_creds.Certificate(credentials_path)
                    firebase_admin.initialize_app(cred, {"projectId": project_id})
                else:
                    firebase_admin.initialize_app(options={"projectId": project_id})

            self._firebase_db = firestore.client()
            return True
        except Exception as exc:
            print(f"[PollyPad] Firebase init skipped: {exc}")
            return False

    def sync_to_firebase(self, session: PadSession) -> bool:
        """Push session to Firebase Firestore."""
        if not self._firebase_db:
            return False
        try:
            doc_ref = self._firebase_db.collection("pollypad_sessions").document(
                session.session_id
            )
            doc_ref.set({
                "session_id": session.session_id,
                "created_at": session.created_at,
                "tongue": session.tongue,
                "total_requests": session.total_requests,
                "total_tokens": session.total_tokens,
                "message_count": len(session.messages),
                "last_messages": session.messages[-10:],
                "updated_at": time.time(),
            })
            return True
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="PollyPad IDE",
    description="Local AI gateway powered by OctoArmor — 20 tentacles, SCBE governance",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
_armor: Optional[OctoArmor] = None
_sessions: Optional[SessionStore] = None


def get_armor() -> OctoArmor:
    global _armor
    if _armor is None:
        _armor = OctoArmor()
    return _armor


def get_sessions() -> SessionStore:
    global _sessions
    if _sessions is None:
        _sessions = SessionStore()
        # Try Firebase init
        project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
        cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")
        if project_id:
            _sessions.init_firebase(project_id, cred_path or None)
    return _sessions


# ─── Health ──────────────────────────────────────────────

@app.get("/health")
async def health():
    armor = get_armor()
    available = armor.available_tentacles()
    return {
        "status": "ok",
        "service": "pollypad-ide",
        "available_tentacles": len(available),
        "total_tentacles": len(Tentacle),
        "tentacle_names": [t.value for t in available],
    }


# ─── Chat (general purpose) ─────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """General-purpose chat — routes to best available tentacle."""
    return await _do_reach(req, task_type_override=req.task_type or "general")


# ─── Code assist ─────────────────────────────────────────

@app.post("/code", response_model=ChatResponse)
async def code_assist(req: ChatRequest):
    """Code-focused request — routes to code-optimized tentacles."""
    return await _do_reach(req, task_type_override="code")


# ─── Research ────────────────────────────────────────────

@app.post("/research", response_model=ChatResponse)
async def research(req: ChatRequest):
    """Research query — routes to large-context tentacles."""
    return await _do_reach(req, task_type_override="research")


# ─── Governance check ───────────────────────────────────

@app.post("/govern", response_model=ChatResponse)
async def governance_check(req: ChatRequest):
    """Governance/safety evaluation — routes to reasoning-heavy tentacles."""
    gov_prompt = (
        f"Evaluate the following for AI safety and governance compliance. "
        f"Identify risks, suggest mitigations, and rate safety 1-10:\n\n{req.prompt}"
    )
    req_copy = req.model_copy()
    req_copy.prompt = gov_prompt
    return await _do_reach(req_copy, task_type_override="governance")


# ─── Batch ───────────────────────────────────────────────

@app.post("/batch")
async def batch_request(req: BatchRequest):
    """Send multiple prompts across tentacles concurrently."""
    armor = get_armor()
    tasks = []
    for chat_req in req.prompts:
        preferred = None
        if chat_req.tentacle:
            try:
                preferred = Tentacle(chat_req.tentacle)
            except ValueError:
                pass
        tasks.append(
            armor.reach(
                chat_req.prompt,
                task_type=chat_req.task_type,
                preferred_tentacle=preferred,
                model=chat_req.model,
                temperature=chat_req.temperature,
                max_tokens=chat_req.max_tokens,
            )
        )
    results = await asyncio.gather(*tasks, return_exceptions=True)
    responses = []
    for r in results:
        if isinstance(r, Exception):
            responses.append({"status": "error", "error": str(r)})
        else:
            responses.append(r)
    return {"results": responses}


# ─── Status / Dashboard ─────────────────────────────────

@app.get("/status")
async def status():
    """Full HYDRA dashboard — tentacle status, Polly stats, usage."""
    armor = get_armor()
    return armor.diagnostics()


@app.get("/tentacles")
async def tentacles():
    """Per-tentacle status with availability and rate limits."""
    armor = get_armor()
    return {"tentacles": armor.tentacle_status()}


@app.get("/models")
async def models():
    """List all available free models across all tentacles."""
    armor = get_armor()
    all_models = armor.all_free_models()
    total = sum(len(m) for m in all_models.values())
    return {"total_free_models": total, "by_tentacle": all_models}


@app.get("/tongues")
async def tongues():
    """Sacred Tongue task mapping reference."""
    return {
        "task_map": TONGUE_TASK_MAP,
        "tongues": {
            "KO": "Intent/Flow (Kindergarten)",
            "AV": "Creative/Boundary (Elementary)",
            "RU": "Security/Constraint (Middle School)",
            "CA": "Compute/Code (High School)",
            "UM": "Governance/Ethics (University)",
            "DR": "Architecture/Structure (Doctorate)",
        },
    }


# ─── Session management ─────────────────────────────────

@app.get("/sessions")
async def list_sessions():
    """List all active PollyPad sessions."""
    store = get_sessions()
    return {"sessions": store.list_sessions()}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details including conversation history."""
    store = get_sessions()
    session = store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "tongue": session.tongue,
        "total_requests": session.total_requests,
        "total_tokens": session.total_tokens,
        "messages": session.messages,
    }


# ─── Training data flush ────────────────────────────────

@app.post("/flush")
async def flush_training():
    """Flush Polly's accumulated observations to JSONL training file."""
    armor = get_armor()
    path = armor.flush_training_data()
    stats = armor.polly.stats()
    return {
        "flushed_to": path,
        "total_observations": stats.get("total", 0),
        "training_pairs": stats.get("training_pairs", 0),
    }


@app.get("/polly")
async def polly_mind():
    """Polly's mind map — knowledge graph built from all interactions."""
    armor = get_armor()
    return {
        "stats": armor.polly.stats(),
        "mind_map": armor.polly.get_mind_map(),
    }


# ─── Firebase status ────────────────────────────────────

@app.get("/firebase")
async def firebase_status():
    """Check Firebase connection status."""
    store = get_sessions()
    connected = store._firebase_db is not None
    return {
        "connected": connected,
        "project_id": os.environ.get("FIREBASE_PROJECT_ID", "not set"),
    }


# ═══════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════

async def _do_reach(req: ChatRequest, task_type_override: str) -> ChatResponse:
    """Execute OctoArmor.reach() with session tracking."""
    armor = get_armor()
    store = get_sessions()
    session = store.get_or_create(req.session_id)

    # Build context from session history
    context = req.context
    if not context and session.messages:
        context = session.get_context()

    preferred = None
    if req.tentacle:
        try:
            preferred = Tentacle(req.tentacle)
        except ValueError:
            raise HTTPException(400, f"Unknown tentacle: {req.tentacle}")

    result = await armor.reach(
        req.prompt,
        task_type=task_type_override,
        preferred_tentacle=preferred,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        context=context,
    )

    # Update session
    response_text = result.get("response") or ""
    tongue = result.get("tongue", "KO")
    if response_text:
        session.add_exchange(req.prompt, response_text, tongue)
        store.sync_to_firebase(session)

    return ChatResponse(
        status=result.get("status", "error"),
        tentacle=result.get("tentacle"),
        model=result.get("model"),
        tongue=tongue,
        response=response_text or result.get("error"),
        latency_ms=result.get("latency_ms"),
        quality=result.get("quality"),
        session_id=session.session_id,
        observation_id=result.get("observation_id"),
    )


# ═══════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════

def main():
    """Start the PollyPad IDE server."""
    import argparse

    parser = argparse.ArgumentParser(description="PollyPad IDE — Local AI Gateway")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8200, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on changes")
    args = parser.parse_args()

    import uvicorn
    print(f"\n{'='*60}")
    print(f"  PollyPad IDE — Local AI Gateway")
    print(f"  OctoArmor: 20 tentacles, SCBE governance")
    print(f"  http://{args.host}:{args.port}")
    print(f"{'='*60}")
    print(f"\n  Endpoints:")
    print(f"    POST /chat      — General chat")
    print(f"    POST /code      — Code assist (CA tongue)")
    print(f"    POST /research  — Research (large context)")
    print(f"    POST /govern    — Safety evaluation")
    print(f"    POST /batch     — Multi-prompt parallel")
    print(f"    GET  /status    — HYDRA dashboard")
    print(f"    GET  /tentacles — Provider status")
    print(f"    GET  /models    — Free model list")
    print(f"    GET  /tongues   — Sacred Tongue reference")
    print(f"    GET  /sessions  — Active sessions")
    print(f"    POST /flush     — Export training data")
    print(f"    GET  /polly     — Polly's mind map")
    print(f"    GET  /health    — Health check")
    print(f"    GET  /firebase  — Firebase status")
    print(f"\n")

    uvicorn.run(
        "src.fleet.polly_pad_ide:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
