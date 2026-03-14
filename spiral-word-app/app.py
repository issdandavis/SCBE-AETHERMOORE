"""
@file app.py
@module spiral-word-app/app
@layer Layer 9, Layer 13, Layer 14
@component FastAPI Backend with WebSocket Sync

Main server for the SpiralWord collaborative editor.
Provides REST API for document CRUD and AI integration,
plus WebSocket endpoints for real-time sync.

Run: uvicorn app:app --reload --host 0.0.0.0 --port 8000
"""

import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sync_engine import SyncEngine, EditOp
from governance import (
    audit_log,
    check_governance,
    check_replay,
    classify_intent,
    sign_operation,
    verify_signature,
)
from ai_ports import ai_ports

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("spiralword.app")

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

sync = SyncEngine()

# WebSocket connections per document: doc_id -> set of WebSocket
connections: Dict[str, Set[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SpiralWord server starting")
    yield
    logger.info("SpiralWord server shutting down")


app = FastAPI(
    title="SpiralWord",
    description="Collaborative text editor with SCBE-AETHERMOORE governance",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class InsertRequest(BaseModel):
    position: int = 0
    content: str
    site_id: str = "api"


class DeleteRequest(BaseModel):
    position: int
    length: int = 1
    site_id: str = "api"


class ReplaceRequest(BaseModel):
    content: str
    site_id: str = "api"


class AIEditRequest(BaseModel):
    prompt: str
    provider: str = "echo"
    options: dict = None
    site_id: str = "ai"


# ---------------------------------------------------------------------------
# REST API — Documents
# ---------------------------------------------------------------------------


@app.get("/docs")
async def list_documents():
    """List all open documents."""
    return sync.list_docs()


@app.get("/doc/{doc_id}")
async def get_document(doc_id: str):
    """Get document content and metadata."""
    doc = sync.get_or_create(doc_id)
    return doc.snapshot()


@app.post("/doc/{doc_id}/insert")
async def insert_text(doc_id: str, req: InsertRequest):
    """Insert text at position."""
    allowed, reason = check_governance("insert")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    doc = sync.get_or_create(doc_id)
    op = doc.insert(req.position, req.content, site_id=req.site_id)

    # L9: Replay check (should always pass for fresh ops)
    check_replay(op.nonce)

    # L14: Audit
    audit_log.record(
        doc_id=doc_id,
        site_id=req.site_id,
        action="insert",
        op_checksum=op.checksum(),
        governance_decision=reason,
    )

    # Broadcast to WebSocket peers
    await _broadcast(doc_id, op)

    return {"status": "ok", "version": doc.version, "op_id": op.op_id}


@app.post("/doc/{doc_id}/delete")
async def delete_text(doc_id: str, req: DeleteRequest):
    """Delete text at position."""
    allowed, reason = check_governance("delete")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    doc = sync.get_or_create(doc_id)
    op = doc.delete(req.position, req.length, site_id=req.site_id)

    check_replay(op.nonce)
    audit_log.record(
        doc_id=doc_id,
        site_id=req.site_id,
        action="delete",
        op_checksum=op.checksum(),
        governance_decision=reason,
    )
    await _broadcast(doc_id, op)

    return {"status": "ok", "version": doc.version, "op_id": op.op_id}


@app.post("/doc/{doc_id}/replace")
async def replace_document(doc_id: str, req: ReplaceRequest):
    """Replace entire document content."""
    allowed, reason = check_governance("replace_all")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    doc = sync.get_or_create(doc_id)
    ops = doc.replace_all(req.content, site_id=req.site_id)

    for op in ops:
        check_replay(op.nonce)
        audit_log.record(
            doc_id=doc_id,
            site_id=req.site_id,
            action="replace_all",
            op_checksum=op.checksum(),
            governance_decision=reason,
        )
        await _broadcast(doc_id, op)

    return {"status": "ok", "version": doc.version}


@app.delete("/doc/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document entirely."""
    allowed, reason = check_governance("delete")
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sync.delete_doc(doc_id):
        return {"status": "deleted", "doc_id": doc_id}
    raise HTTPException(status_code=404, detail="Document not found")


# ---------------------------------------------------------------------------
# REST API — AI Ports
# ---------------------------------------------------------------------------


@app.post("/doc/{doc_id}/ai")
async def ai_edit(doc_id: str, req: AIEditRequest):
    """
    Use an AI provider to generate text, then insert it into the document.

    The AI response is appended at the end of the document.
    Governance checks are applied to the prompt before dispatch.
    """
    # AI port handles its own governance check
    result = ai_ports.call(req.prompt, provider=req.provider, options=req.options)

    if result.startswith("[BLOCKED]") or result.startswith("[ERROR]"):
        return {"status": "blocked", "message": result}

    doc = sync.get_or_create(doc_id)
    op = doc.insert(doc.length, result, site_id=req.site_id)

    tongue, confidence = classify_intent(req.prompt)
    audit_log.record(
        doc_id=doc_id,
        site_id=req.site_id,
        action="ai_edit",
        op_checksum=op.checksum(),
        governance_decision=f"AI:{req.provider}",
        tongue=tongue,
        confidence=confidence,
    )
    await _broadcast(doc_id, op)

    return {
        "status": "ok",
        "version": doc.version,
        "ai_provider": req.provider,
        "tongue": tongue,
        "confidence": confidence,
        "generated_length": len(result),
    }


@app.get("/ai/providers")
async def list_ai_providers():
    """List available AI providers."""
    return {"providers": ai_ports.list_providers()}


# ---------------------------------------------------------------------------
# REST API — Governance & Audit
# ---------------------------------------------------------------------------


@app.get("/audit")
async def get_audit_log(n: int = 20):
    """Get recent audit log entries."""
    return audit_log.recent(n)


@app.get("/governance/check")
async def governance_check(action: str, prompt: str = ""):
    """Test a governance decision without applying it."""
    allowed, reason = check_governance(action, prompt)
    tongue, confidence = classify_intent(prompt) if prompt else ("KO", 1.0)
    return {
        "allowed": allowed,
        "reason": reason,
        "tongue": tongue,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# WebSocket — Real-Time Sync
# ---------------------------------------------------------------------------


@app.websocket("/ws/{doc_id}")
async def websocket_endpoint(websocket: WebSocket, doc_id: str):
    """
    WebSocket endpoint for real-time document sync.

    Protocol:
    1. On connect: server sends current document snapshot.
    2. Client sends serialized EditOp JSON messages.
    3. Server applies op, broadcasts to all other peers.
    4. L9: Replay protection on each incoming op nonce.
    5. L13: Signature verification if op includes "sig" field.
    """
    await websocket.accept()

    if doc_id not in connections:
        connections[doc_id] = set()
    connections[doc_id].add(websocket)

    doc = sync.get_or_create(doc_id)

    # Send current state to new joiner
    try:
        await websocket.send_text(json.dumps({
            "type": "snapshot",
            "data": doc.snapshot(),
        }))
    except Exception:
        connections[doc_id].discard(websocket)
        return

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "op":
                op_data = msg["data"]
                op = EditOp.from_dict(op_data)

                # L9: Replay protection
                if not check_replay(op.nonce):
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Replay detected",
                    }))
                    continue

                # L13: Signature check (optional)
                if "sig" in msg:
                    if not verify_signature(op_data, msg["sig"]):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Invalid signature",
                        }))
                        continue

                # Apply remote op
                applied = doc.apply_remote(op)
                if applied:
                    # L14: Audit
                    audit_log.record(
                        doc_id=doc_id,
                        site_id=op.site_id,
                        action=f"ws_{op.op_type}",
                        op_checksum=op.checksum(),
                        governance_decision="ALLOW:ws",
                    )

                    # Broadcast to all OTHER peers
                    for peer in connections.get(doc_id, set()):
                        if peer != websocket:
                            try:
                                await peer.send_text(json.dumps({
                                    "type": "op",
                                    "data": op.to_dict(),
                                }))
                            except Exception:
                                pass

            elif msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        connections.get(doc_id, set()).discard(websocket)
        logger.info("WebSocket disconnected from doc %s", doc_id)
    except Exception as e:
        connections.get(doc_id, set()).discard(websocket)
        logger.error("WebSocket error on doc %s: %s", doc_id, e)


async def _broadcast(doc_id: str, op: EditOp):
    """Broadcast an operation to all WebSocket peers for a document."""
    msg = json.dumps({"type": "op", "data": op.to_dict()})
    for peer in list(connections.get(doc_id, set())):
        try:
            await peer.send_text(msg)
        except Exception:
            connections.get(doc_id, set()).discard(peer)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
