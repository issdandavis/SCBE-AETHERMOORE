"""
SCBE n8n Bridge — FastAPI service connecting n8n workflows to SCBE Web Agent
=============================================================================

Endpoints:
  POST /v1/governance/scan      — Semantic antivirus scan
  POST /v1/tongue/encode        — Sacred Tongue encoding
  POST /v1/buffer/post          — Content Buffer posting
  POST /v1/agent/task           — Submit web agent task
  GET  /v1/agent/task/{id}/status — Poll task status
  POST /v1/telemetry/post-result — Log post telemetry
  GET  /health                   — Health check

Start:
  uvicorn workflows.n8n.scbe_n8n_bridge:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# Resolve project paths
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SRC = os.path.join(_PROJECT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

try:
    from fastapi import FastAPI, HTTPException, Header, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    print("pip install fastapi uvicorn  # required for n8n bridge")
    raise

from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent import (
    SemanticAntivirus,
    ContentBuffer,
    Platform,
    PlatformPublisher,
    AgentOrchestrator,
    WebTask,
    TaskStatus,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.publishers import create_publisher

# ---------------------------------------------------------------------------
#  App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SCBE n8n Bridge",
    version="1.0.0",
    description="Connects n8n workflow automation to SCBE-AETHERMOORE web agent pipeline",
)

# Shared instances
_antivirus = SemanticAntivirus()
_buffer = ContentBuffer(antivirus=_antivirus)
_orchestrator = AgentOrchestrator(antivirus=_antivirus)
_telemetry: List[Dict[str, Any]] = []

# Register dry-run publishers (replace with real credentials in production)
for plat in Platform:
    _buffer.register_publisher(PlatformPublisher(plat))

# API key validation
_API_KEYS = set(
    k.strip()
    for k in os.environ.get("SCBE_API_KEYS", "scbe-dev-key,test-key").split(",")
    if k.strip()
)


def _check_key(api_key: Optional[str] = None):
    if api_key and api_key in _API_KEYS:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
#  Request/response models
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    content: str
    platforms: Optional[List[str]] = None
    scan_mode: str = "full"


class TongueEncodeRequest(BaseModel):
    text: str
    tongue: str = "KO"
    seal: bool = False
    context: Optional[List[float]] = None


class BufferPostRequest(BaseModel):
    text: str
    platforms: List[str] = ["twitter"]
    tags: Optional[List[str]] = None
    schedule_at: Optional[float] = None
    tongue_encode: bool = False
    tongue: Optional[str] = None


class TaskRequest(BaseModel):
    task_type: str = "navigate"
    target_url: Optional[str] = None
    goal: str = ""
    max_steps: int = 50
    parameters: Dict[str, Any] = {}
    # Content posting fields
    text: Optional[str] = None
    platforms: Optional[List[str]] = None


class TelemetryRequest(BaseModel):
    platform: str
    success: bool
    post_url: Optional[str] = None
    timestamp: Optional[str] = None


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "scbe-n8n-bridge",
        "version": "1.0.0",
        "buffer_queue": _buffer.summary(),
        "orchestrator": _orchestrator.summary(),
        "telemetry_count": len(_telemetry),
    }


@app.post("/v1/governance/scan")
async def governance_scan(req: ScanRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    profile = _antivirus.scan(req.content)
    return profile.to_dict()


@app.post("/v1/tongue/encode")
async def tongue_encode(req: TongueEncodeRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    try:
        from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.tongue_transport import TongueTransport
        transport = TongueTransport()
        if req.seal and req.context:
            env = transport.seal(req.text, tongue=req.tongue, context=req.context)
            return {
                "tongue": env.tongue,
                "encoded_text": env.encoded_text,
                "geoseal": env.geoseal,
                "transport": "tongue+geoseal",
            }
        else:
            env = transport.encode(req.text, tongue=req.tongue)
            return {
                "tongue": env.tongue,
                "encoded_text": env.encoded_text,
                "token_count": len(env.tokens),
                "transport": "tongue",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/buffer/post")
async def buffer_post(req: BufferPostRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    text = req.text

    # Optional tongue encoding
    if req.tongue_encode:
        try:
            from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.tongue_transport import TongueTransport
            transport = TongueTransport()
            tongue = req.tongue or "KO"
            env = transport.encode(text, tongue=tongue)
            text = env.encoded_text
        except Exception:
            pass  # Fall through to plain text

    post = _buffer.create_post(
        text=text,
        platforms=req.platforms,
        tags=req.tags,
        schedule_at=req.schedule_at,
    )

    if post.status.value == "blocked":
        return {
            "status": "blocked",
            "governance_verdict": post.governance_verdict,
            "governance_risk": post.governance_risk,
        }

    # Publish immediately if no schedule
    results = []
    if not req.schedule_at:
        publish_results = _buffer.publish_due()
        results = [
            {"platform": r.platform.value, "success": r.success, "url": r.post_url}
            for r in publish_results
        ]

    return {
        "post_id": post.post_id,
        "status": post.status.value,
        "platforms": [p.value for p in post.platforms],
        "governance_verdict": post.governance_verdict,
        "governance_risk": post.governance_risk,
        "results": results,
    }


@app.post("/v1/agent/task")
async def submit_task(req: TaskRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.agent_orchestrator import TaskType

    task = WebTask(
        task_type=TaskType(req.task_type),
        target_url=req.target_url,
        goal=req.goal,
        max_steps=req.max_steps,
        parameters=req.parameters,
    )

    if req.text:
        task.post_content = req.text
    if req.platforms:
        task.post_platforms = req.platforms

    task_id = _orchestrator.submit_task(task)
    return {
        "task_id": task_id,
        "status": task.status.value,
        "task_type": task.task_type.value,
    }


@app.get("/v1/agent/task/{task_id}/status")
async def task_status(task_id: str, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    task = _orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    result = None
    if task.result:
        result = task.result.to_dict()
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "task_type": task.task_type.value,
        "result": result,
    }


@app.post("/v1/telemetry/post-result")
async def telemetry_log(req: TelemetryRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    entry = {
        "platform": req.platform,
        "success": req.success,
        "post_url": req.post_url,
        "timestamp": req.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "logged_at": time.time(),
    }
    _telemetry.append(entry)
    return {"status": "logged", "total_entries": len(_telemetry)}


@app.get("/v1/telemetry")
async def telemetry_list(x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    return {"entries": _telemetry[-100:], "total": len(_telemetry)}
