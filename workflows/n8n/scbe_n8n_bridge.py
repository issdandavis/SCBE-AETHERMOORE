h"""
SCBE n8n Bridge — FastAPI service connecting n8n workflows to SCBE Web Agent
=============================================================================

Endpoints:
  POST /v1/governance/scan        — Semantic antivirus scan
  GET  /v1/automations/health     — Self-hosted automation hub health
  GET  /v1/automations/rules      — List local automation rules
  POST /v1/automations/rules      — Register local automation rule
  DELETE /v1/automations/rules/{id} — Remove local automation rule
  POST /v1/automations/emit       — Emit event through local automation rules
  POST /v1/tongue/encode          — Sacred Tongue encoding
  POST /v1/buffer/post            — Content Buffer posting
  POST /v1/agent/task             — Submit web agent task
  GET  /v1/agent/task/{id}/status — Poll task status
  GET  /v1/llm/providers          — Provider availability for tool-calling router
  POST /v1/llm/dispatch           — Unified dispatch to HF/OpenAI/Claude/Grok + Zapier callback
  POST /v1/integrations/n8n/browse — Proxy to Playwright browser service
  GET  /v1/integrations/status    — Integration health (browser service)
  POST /v1/telemetry/post-result  — Log post telemetry
  POST /v1/training/ingest        — Ingest game events into HF training pipeline
  GET  /v1/training/status        — Training pipeline status
  POST /v1/council/deliberate     — AI Round Table: multi-LLM deliberation with governance
  GET  /v1/council/status         — Round Table session history
  POST /v1/workflow/lattice25d    — HyperbolicLattice25D note embedding and tagging
  GET  /health                    — Health check

Start:
  uvicorn workflows.n8n.scbe_n8n_bridge:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import asyncio
import logging
import json
import os
import re
import sys
import threading
import time
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from urllib import error as urllib_error
from urllib import request as urllib_request

# Resolve project paths
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SRC = os.path.join(_PROJECT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)
_DEMO = os.path.join(_PROJECT, "demo")
if _DEMO not in sys.path:
    sys.path.insert(0, _DEMO)

logger = logging.getLogger("scbe_n8n_bridge")

try:
    from fastapi import FastAPI, HTTPException, Header, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
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
from workflows.n8n.scbe_automation_hub import AutomationHub, parse_allowed_hosts

# ---------------------------------------------------------------------------
#  App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SCBE n8n Bridge",
    version="2.0.0",
    description="SCBE-AETHERMOORE web agent pipeline + AI Round Table council",
)

# CORS — allow the mobile app (Capacitor webview) and local dev
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
_BROWSER_SERVICE_URL = os.environ.get(
    "SCBE_BROWSER_SERVICE_URL",
    "http://127.0.0.1:8011",
).rstrip("/")
_BROWSER_SERVICE_API_KEY = os.environ.get("SCBE_BROWSER_API_KEY", "").strip()
try:
    _BROWSER_TIMEOUT_SEC = int(os.environ.get("SCBE_BROWSER_TIMEOUT_SEC", "45"))
except ValueError:
    _BROWSER_TIMEOUT_SEC = 45

# LLM provider router settings
_OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
_ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
_XAI_API_KEY = os.environ.get("XAI_API_KEY", "").strip()
_HF_ROUTER_TOKEN = (
    os.environ.get("HF_TOKEN", "").strip()
    or os.environ.get("HUGGINGFACEHUB_API_TOKEN", "").strip()
    or os.environ.get("HUGGINGFACE_HUB_TOKEN", "").strip()
)
_GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
_CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "").strip()
_GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", os.environ.get("GEMINI_API_KEY", "")).strip()
_GITHUB_MODELS_TOKEN = os.environ.get("GITHUB_TOKEN", os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")).strip()
_OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
_ZAPIER_WEBHOOK_URL = os.environ.get("SCBE_ZAPIER_HOOK_URL", "").strip()

_OPENAI_DEFAULT_MODEL = os.environ.get("SCBE_OPENAI_MODEL", "gpt-4o-mini").strip()
_ANTHROPIC_DEFAULT_MODEL = os.environ.get(
    "SCBE_ANTHROPIC_MODEL",
    "claude-3-5-sonnet-latest",
).strip()
_XAI_DEFAULT_MODEL = os.environ.get("SCBE_XAI_MODEL", "grok-beta").strip()
_HF_DEFAULT_MODEL = os.environ.get("SCBE_HF_MODEL", "Qwen/Qwen2.5-7B-Instruct").strip()
_HF_DATASET_REPO_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}/[A-Za-z0-9][A-Za-z0-9._-]{0,95}$"
)
_HF_ALLOWED_DATASET_REPOS = {
    repo.strip().lower()
    for repo in os.environ.get("SCBE_HF_ALLOWED_DATASET_REPOS", "").split(",")
    if repo.strip()
}
_HF_COMMIT_MESSAGE_MAX_LEN = 120
_AUTOMATION_RULES_PATH = Path(
    os.environ.get(
        "SCBE_AUTOMATION_RULES_PATH",
        os.path.join(_PROJECT, "artifacts", "automations", "rules.json"),
    )
).resolve()
_AUTOMATION_RUNS_PATH = Path(
    os.environ.get(
        "SCBE_AUTOMATION_RUNS_PATH",
        os.path.join(_PROJECT, "artifacts", "automations", "runs.jsonl"),
    )
).resolve()
_AUTOMATION_ALLOWED_HOSTS = parse_allowed_hosts(os.environ.get("SCBE_AUTOMATION_ALLOWED_HOSTS", ""))
_AUTOMATION_HUB = AutomationHub(
    store_path=_AUTOMATION_RULES_PATH,
    runs_path=_AUTOMATION_RUNS_PATH,
    allowed_hosts=_AUTOMATION_ALLOWED_HOSTS,
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


class TrainingIngestRequest(BaseModel):
    """Game event forwarded from n8n for training data collection."""
    event_type: str
    context: str = ""
    outcome: str = ""
    tongue: str = "KO"
    metadata: Dict[str, Any] = {}


class N8nBrowseAction(BaseModel):
    """Compact action payload expected by browser integration endpoint."""
    action: str
    target: str
    value: Optional[str] = None
    timeout_ms: Optional[int] = None
    include_full_data: bool = False


class N8nBrowseRequest(BaseModel):
    """Bridge request used by n8n workflows for Playwright browsing."""
    actions: List[N8nBrowseAction]
    session_id: Optional[str] = None
    dry_run: bool = False
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    source: str = "n8n"


class CouncilRequest(BaseModel):
    """AI Round Table — fan out a query to multiple LLMs with governance."""
    query: str
    system: Optional[str] = None
    providers: List[str] = ["anthropic", "openai", "xai"]
    rounds: int = 1
    strategy: str = "consensus"  # consensus | majority | debate | chain
    governance_scan: bool = True
    tongue: str = "DR"


class LLMDispatchRequest(BaseModel):
    """Unified provider dispatch for OpenAI, Anthropic, xAI, and HF router."""
    provider: str
    model: Optional[str] = None
    messages: List[Dict[str, Any]] = []
    prompt: Optional[str] = None
    system: Optional[str] = None
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 800
    tools: List[Dict[str, Any]] = []
    tool_choice: Optional[Any] = None
    metadata: Dict[str, Any] = {}
    passthrough: Dict[str, Any] = {}
    route_to_zapier: bool = False


class LatticeNoteInput(BaseModel):
    note_id: Optional[str] = None
    text: str
    tags: List[str] = Field(default_factory=list)
    source: str = "n8n"
    authority: str = "public"
    tongue: str = "KO"
    phase_rad: Optional[float] = None


class Lattice25DRequest(BaseModel):
    notes: List[LatticeNoteInput] = Field(default_factory=list)
    include_notion_notes: bool = False
    notion_query: str = ""
    notion_page_size: int = 20
    notion_max_notes: int = 20
    include_repo_notes: bool = False
    notes_glob: str = "docs/**/*.md"
    max_notes: int = 60
    cell_size: float = 0.4
    max_depth: int = 6
    phase_weight: float = 0.35
    index_mode: Literal["grid", "quadtree", "hybrid"] = "grid"
    quadtree_capacity: int = 8
    quadtree_z_variance: float = 0.01
    quadtree_query_extent: float = 0.35
    radius: float = 0.72
    query_intent: List[float] = Field(default_factory=lambda: [0.9, 0.1, 0.1])
    query_x: float = 0.1
    query_y: float = 0.1
    query_phase: float = 0.0
    query_top_k: int = 5
    hf_dataset_repo: Optional[str] = None
    hf_output_path: str = "artifacts/hf/lattice25d_notes.jsonl"
    hf_push: bool = False
    hf_create_pr: bool = False
    hf_commit_message: str = "feat(dataset): lattice25d notes export"
    include_note_payload: bool = True


class AutomationRuleRequest(BaseModel):
    name: str
    event: str
    target_url: str
    method: Literal["POST", "PUT", "PATCH"] = "POST"
    description: str = ""
    enabled: bool = True
    static_headers: Dict[str, str] = Field(default_factory=dict)
    static_payload: Dict[str, Any] = Field(default_factory=dict)


class AutomationEmitRequest(BaseModel):
    event: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class CodeExecRequest(BaseModel):
    code: str
    language: str = "python"
    timeout: int = 10


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "scbe-n8n-bridge",
        "version": "2.0.0",
        "buffer_queue": _buffer.summary(),
        "orchestrator": _orchestrator.summary(),
        "telemetry_count": len(_telemetry),
        "council_sessions": len(_council_sessions),
        "browser_service_url": _BROWSER_SERVICE_URL,
    }


def _normalize_provider(raw: str) -> str:
    p = (raw or "").strip().lower()
    aliases = {
        "gpt": "openai",
        "codex": "openai",
        "openai": "openai",
        "claude": "anthropic",
        "anthropic": "anthropic",
        "grok": "xai",
        "xai": "xai",
        "hf": "huggingface",
        "huggingface": "huggingface",
    }
    return aliases.get(p, p)


def _coerce_messages(req: LLMDispatchRequest) -> List[Dict[str, Any]]:
    if req.messages:
        return req.messages
    if req.prompt:
        msgs: List[Dict[str, Any]] = []
        if req.system:
            msgs.append({"role": "system", "content": req.system})
        msgs.append({"role": "user", "content": req.prompt})
        return msgs
    return [{"role": "user", "content": ""}]


def _http_post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    req = urllib_request.Request(
        url=url,
        method="POST",
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "upstream_http_error",
                "upstream_status": exc.code,
                "url": url,
                "body": detail[:1800],
            },
        )
    except urllib_error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Upstream provider unavailable: {exc.reason}",
        )


def _extract_openai_style_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    choices = resp.get("choices", [])
    if not choices:
        return {"text": "", "tool_calls": []}
    message = choices[0].get("message", {}) or {}
    content = message.get("content", "")
    if isinstance(content, list):
        content = "\n".join(
            str(block.get("text", "")) if isinstance(block, dict) else str(block)
            for block in content
        )
    return {
        "text": content or "",
        "tool_calls": message.get("tool_calls", []) or [],
    }


def _extract_anthropic_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    blocks = resp.get("content", []) or []
    text_parts: List[str] = []
    tool_calls: List[Dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text_parts.append(str(block.get("text", "")))
        elif block_type == "tool_use":
            tool_calls.append(block)
    return {
        "text": "\n".join(t for t in text_parts if t).strip(),
        "tool_calls": tool_calls,
    }


def _dispatch_openai_compatible(
    req: LLMDispatchRequest,
    base_url: str,
    bearer_token: str,
    default_model: str,
) -> Dict[str, Any]:
    if not bearer_token:
        raise HTTPException(status_code=400, detail="Provider API key not configured")
    payload: Dict[str, Any] = {
        "model": req.model or default_model,
        "messages": _coerce_messages(req),
    }
    if req.temperature is not None:
        payload["temperature"] = req.temperature
    if req.max_tokens is not None:
        payload["max_tokens"] = req.max_tokens
    if req.tools:
        payload["tools"] = req.tools
    if req.tool_choice is not None:
        payload["tool_choice"] = req.tool_choice
    if req.passthrough:
        payload.update(req.passthrough)

    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }
    return _http_post_json(
        url=base_url,
        payload=payload,
        headers=headers,
        timeout_sec=max(20, _BROWSER_TIMEOUT_SEC),
    )


def _dispatch_anthropic(req: LLMDispatchRequest) -> Dict[str, Any]:
    if not _ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured")

    src_messages = _coerce_messages(req)
    system_chunks: List[str] = []
    msgs: List[Dict[str, Any]] = []
    for m in src_messages:
        role = str(m.get("role", "user")).lower()
        content = m.get("content", "")
        if role == "system":
            system_chunks.append(str(content))
            continue
        if role not in ("user", "assistant"):
            role = "user"
        msgs.append({"role": role, "content": str(content)})

    payload: Dict[str, Any] = {
        "model": req.model or _ANTHROPIC_DEFAULT_MODEL,
        "messages": msgs,
        "max_tokens": int(req.max_tokens or 800),
    }
    system_prompt = req.system or "\n".join(t for t in system_chunks if t)
    if system_prompt:
        payload["system"] = system_prompt
    if req.temperature is not None:
        payload["temperature"] = req.temperature
    if req.tools:
        payload["tools"] = req.tools
    if req.tool_choice is not None:
        payload["tool_choice"] = req.tool_choice
    if req.passthrough:
        payload.update(req.passthrough)

    headers = {
        "x-api-key": _ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    return _http_post_json(
        url="https://api.anthropic.com/v1/messages",
        payload=payload,
        headers=headers,
        timeout_sec=max(20, _BROWSER_TIMEOUT_SEC),
    )


def _send_zapier_event(event_payload: Dict[str, Any]) -> Dict[str, Any]:
    hook_url = _ZAPIER_WEBHOOK_URL
    if not hook_url:
        return {"status": "skipped", "reason": "missing_hook_url"}
    # SSRF protection: only allow known webhook domains
    from urllib.parse import urlparse
    parsed = urlparse(hook_url)
    _ALLOWED_WEBHOOK_HOSTS = {
        "hooks.zapier.com",
        "api.zapier.com",
        "hook.us1.make.com",
        "hook.eu1.make.com",
    }
    if parsed.hostname not in _ALLOWED_WEBHOOK_HOSTS:
        return {"status": "blocked", "reason": f"host not in allowlist: {parsed.hostname}"}
    if parsed.scheme != "https":
        return {"status": "blocked", "reason": "only https allowed"}
    req = urllib_request.Request(
        url=hook_url,
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps(event_payload).encode("utf-8"),
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "status": "sent",
                "status_code": getattr(resp, "status", 200),
                "body": body[:800],
            }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "error": str(exc)}


@app.get("/v1/llm/providers")
async def llm_provider_status(x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    return {
        "providers": {
            "openai": {"configured": bool(_OPENAI_API_KEY), "default_model": _OPENAI_DEFAULT_MODEL},
            "anthropic": {"configured": bool(_ANTHROPIC_API_KEY), "default_model": _ANTHROPIC_DEFAULT_MODEL},
            "xai": {"configured": bool(_XAI_API_KEY), "default_model": _XAI_DEFAULT_MODEL},
            "huggingface": {"configured": bool(_HF_ROUTER_TOKEN), "default_model": _HF_DEFAULT_MODEL},
        },
        "zapier": {"configured": bool(_ZAPIER_WEBHOOK_URL)},
    }


@app.post("/v1/llm/dispatch")
async def llm_dispatch(req: LLMDispatchRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    provider = _normalize_provider(req.provider)

    raw_response: Dict[str, Any]
    if provider == "openai":
        raw_response = _dispatch_openai_compatible(
            req=req,
            base_url="https://api.openai.com/v1/chat/completions",
            bearer_token=_OPENAI_API_KEY,
            default_model=_OPENAI_DEFAULT_MODEL,
        )
        extracted = _extract_openai_style_response(raw_response)
    elif provider == "xai":
        raw_response = _dispatch_openai_compatible(
            req=req,
            base_url="https://api.x.ai/v1/chat/completions",
            bearer_token=_XAI_API_KEY,
            default_model=_XAI_DEFAULT_MODEL,
        )
        extracted = _extract_openai_style_response(raw_response)
    elif provider == "huggingface":
        raw_response = _dispatch_openai_compatible(
            req=req,
            base_url="https://router.huggingface.co/v1/chat/completions",
            bearer_token=_HF_ROUTER_TOKEN,
            default_model=_HF_DEFAULT_MODEL,
        )
        extracted = _extract_openai_style_response(raw_response)
    elif provider == "anthropic":
        raw_response = _dispatch_anthropic(req)
        extracted = _extract_anthropic_response(raw_response)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{req.provider}'. Use openai|anthropic|xai|huggingface.",
        )

    result: Dict[str, Any] = {
        "provider": provider,
        "model": req.model,
        "text": extracted.get("text", ""),
        "tool_calls": extracted.get("tool_calls", []),
        "raw": raw_response,
    }

    if req.route_to_zapier:
        result["zapier"] = _send_zapier_event(
            event_payload={
                "event": "llm_dispatch",
                "provider": provider,
                "metadata": req.metadata,
                "result": {
                    "text": result["text"],
                    "tool_calls": result["tool_calls"],
                },
            },
        )

    return result


# ── Arena Chat endpoint (used by AetherCode mobile app) ──────────────

# Map app seat IDs → provider + base_url + key + default model
_ARENA_PROVIDERS = {
    "groq":          {"base_url": "https://api.groq.com/openai/v1/chat/completions",          "key_fn": lambda: _GROQ_API_KEY,         "model": "llama-3.3-70b-versatile", "style": "openai"},
    "cerebras":      {"base_url": "https://api.cerebras.ai/v1/chat/completions",               "key_fn": lambda: _CEREBRAS_API_KEY,     "model": "llama3.1-8b",             "style": "openai"},
    "google_ai":     {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "key_fn": lambda: _GOOGLE_AI_KEY, "model": "gemini-2.5-flash", "style": "openai"},
    "claude":        {"base_url": None,                                                        "key_fn": lambda: _ANTHROPIC_API_KEY,    "model": _ANTHROPIC_DEFAULT_MODEL,  "style": "anthropic"},
    "xai":           {"base_url": "https://api.x.ai/v1/chat/completions",                      "key_fn": lambda: _XAI_API_KEY,          "model": "grok-3-mini-fast",        "style": "openai"},
    "openrouter":    {"base_url": "https://openrouter.ai/api/v1/chat/completions",             "key_fn": lambda: _OPENROUTER_API_KEY,   "model": "moonshotai/kimi-k2",      "style": "openai"},
    "github_models": {"base_url": "https://models.inference.ai.azure.com/chat/completions",    "key_fn": lambda: _GITHUB_MODELS_TOKEN,  "model": "gpt-4o-mini",             "style": "openai"},
    "huggingface":   {"base_url": "https://router.huggingface.co/v1/chat/completions",         "key_fn": lambda: _HF_ROUTER_TOKEN,      "model": _HF_DEFAULT_MODEL,         "style": "openai"},
    "ollama":        {"base_url": "http://127.0.0.1:11434/v1/chat/completions",                "key_fn": lambda: "ollama",              "model": "llama3.2",                "style": "openai"},
}


class ArenaChatRequest(BaseModel):
    message: str
    mode: str = "chat"
    tentacle: str = "groq"
    context: List[Dict[str, Any]] = []


def _arena_chat_openai_sdk(messages: List[Dict], base_url: str, api_key: str, model: str) -> str:
    """Use the openai SDK to avoid Cloudflare 1010 blocks on raw urllib."""
    try:
        from openai import OpenAI
    except ImportError:
        raise HTTPException(500, "openai SDK not installed. Run: pip install openai")
    # Strip /chat/completions from base_url — SDK adds it
    base = base_url.rsplit("/chat/completions", 1)[0]
    client = OpenAI(api_key=api_key, base_url=base)
    resp = client.chat.completions.create(model=model, messages=messages, max_tokens=800)
    return resp.choices[0].message.content or ""


def _arena_chat_anthropic_sdk(messages: List[Dict], api_key: str, model: str) -> str:
    """Use anthropic SDK for Claude."""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise HTTPException(500, "anthropic SDK not installed. Run: pip install anthropic")
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    user_msgs = [m for m in messages if m["role"] != "system"]
    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        system="\n\n".join(system_parts) if system_parts else "",
        messages=user_msgs,
        max_tokens=800,
    )
    return resp.content[0].text if resp.content else ""


@app.post("/v1/chat")
async def arena_chat(req: ArenaChatRequest):
    """AetherCode Arena chat — routes to the right AI provider via SDK (no Cloudflare blocks)."""
    t0 = time.time()
    seat = req.tentacle.lower().strip()
    cfg = _ARENA_PROVIDERS.get(seat)
    if not cfg:
        raise HTTPException(400, f"Unknown seat '{seat}'. Available: {list(_ARENA_PROVIDERS.keys())}")

    api_key = cfg["key_fn"]()
    if not api_key or (api_key == "ollama" and seat != "ollama"):
        raise HTTPException(503, f"No API key configured for '{seat}'.")

    # Build messages from context + user message
    messages = []
    for ctx in req.context:
        if isinstance(ctx, dict) and "role" in ctx and "content" in ctx:
            messages.append({"role": ctx["role"], "content": ctx["content"]})
    messages.append({"role": "user", "content": req.message})

    try:
        if cfg["style"] == "anthropic":
            text = _arena_chat_anthropic_sdk(messages, api_key, cfg["model"])
        else:
            text = _arena_chat_openai_sdk(messages, cfg["base_url"], api_key, cfg["model"])

        latency_ms = (time.time() - t0) * 1000
        return {
            "response": text,
            "tentacle": seat,
            "model": cfg["model"],
            "latency_ms": latency_ms,
            "governance_score": 1.0,
        }
    except HTTPException:
        raise
    except Exception as exc:
        latency_ms = (time.time() - t0) * 1000
        raise HTTPException(502, detail=f"{seat} error: {str(exc)[:300]}")


@app.get("/v1/providers")
async def arena_providers():
    """Return which providers are available for the Arena app."""
    result = {}
    for seat, cfg in _ARENA_PROVIDERS.items():
        api_key = cfg["key_fn"]()
        available = bool(api_key) and (api_key != "ollama" or seat == "ollama")
        result[seat] = {
            "available": available,
            "model": cfg["model"],
            "required_env": "API key",
        }
    return result


@app.post("/v1/execute")
async def execute_code(req: CodeExecRequest):
    """Run user-supplied code in a subprocess and return stdout/stderr/exit_code."""
    if req.language not in ("python", "javascript"):
        raise HTTPException(400, detail=f"Unsupported language: {req.language}")
    timeout = max(1, min(req.timeout, 30))
    if req.language == "python":
        cmd = [sys.executable, "-c", req.code]
    else:
        cmd = ["node", "-e", req.code]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration_ms = round((time.time() - t0) * 1000)
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "language": req.language,
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired:
        duration_ms = round((time.time() - t0) * 1000)
        return {
            "stdout": "",
            "stderr": f"Process timed out after {timeout}s",
            "exit_code": -1,
            "language": req.language,
            "duration_ms": duration_ms,
        }


def _browser_health_check() -> Dict[str, Any]:
    """Probe browser service /health endpoint."""
    url = f"{_BROWSER_SERVICE_URL}/health"
    req = urllib_request.Request(url=url, method="GET")
    try:
        with urllib_request.urlopen(req, timeout=max(3, _BROWSER_TIMEOUT_SEC // 2)) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body) if body else {}
            return {
                "reachable": True,
                "status_code": getattr(resp, "status", 200),
                "health": data,
                "url": url,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "reachable": False,
            "error": str(exc),
            "url": url,
        }


def _forward_to_browser_service(payload: Dict[str, Any], bridge_api_key: str) -> Dict[str, Any]:
    """Forward browse request from n8n bridge to browser service."""
    url = f"{_BROWSER_SERVICE_URL}/v1/integrations/n8n/browse"
    data = json.dumps(payload).encode("utf-8")
    browser_api_key = _BROWSER_SERVICE_API_KEY or bridge_api_key
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": browser_api_key,
    }
    req = urllib_request.Request(url=url, data=data, headers=headers, method="POST")

    try:
        with urllib_request.urlopen(req, timeout=_BROWSER_TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {"status": "ok"}
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "browser_service_http_error",
                "upstream_status": exc.code,
                "url": url,
                "body": body[:1500],
            },
        )
    except urllib_error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Browser service unavailable at {_BROWSER_SERVICE_URL}: {exc.reason}",
        )
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Browser service returned invalid JSON: {exc}",
        )


@app.get("/v1/integrations/status")
async def integrations_status(x_api_key: Optional[str] = Header(None)):
    """Return integration health for n8n->bridge->browser pipeline."""
    _check_key(x_api_key)
    return {
        "bridge": {
            "status": "ok",
            "service": "scbe-n8n-bridge",
        },
        "browser_service": _browser_health_check(),
    }


@app.get("/v1/automations/health")
async def automation_health(x_api_key: Optional[str] = Header(None)):
    """Return health and file locations for the self-hosted automation hub."""
    _check_key(x_api_key)
    return {
        "status": "ok",
        "rules_path": str(_AUTOMATION_RULES_PATH),
        "runs_path": str(_AUTOMATION_RUNS_PATH),
        "allowed_hosts": sorted(_AUTOMATION_ALLOWED_HOSTS) if _AUTOMATION_ALLOWED_HOSTS else ["*"],
        "rules_count": len(_AUTOMATION_HUB.list_rules()),
    }


@app.get("/v1/automations/rules")
async def automation_list_rules(x_api_key: Optional[str] = Header(None)):
    """List registered automation rules for the local hub."""
    _check_key(x_api_key)
    return {"rules": _AUTOMATION_HUB.list_rules()}


@app.post("/v1/automations/rules")
async def automation_register_rule(req: AutomationRuleRequest, x_api_key: Optional[str] = Header(None)):
    """Register a local automation rule that routes matching events to a webhook."""
    _check_key(x_api_key)
    try:
        rule = _AUTOMATION_HUB.register_rule(req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "registered", "rule": rule}


@app.delete("/v1/automations/rules/{rule_id}")
async def automation_delete_rule(rule_id: str, x_api_key: Optional[str] = Header(None)):
    """Delete a local automation rule."""
    _check_key(x_api_key)
    deleted = _AUTOMATION_HUB.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    return {"status": "deleted", "rule_id": rule_id}


@app.post("/v1/automations/emit")
async def automation_emit(req: AutomationEmitRequest, x_api_key: Optional[str] = Header(None)):
    """Emit an event through all matching local automation rules."""
    _check_key(x_api_key)
    try:
        result = await asyncio.to_thread(
            _AUTOMATION_HUB.emit_event,
            event=req.event,
            payload=req.payload,
            metadata=req.metadata,
            dry_run=bool(req.dry_run),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


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


@app.post("/v1/integrations/n8n/browse")
async def n8n_browse_proxy(req: N8nBrowseRequest, x_api_key: Optional[str] = Header(None)):
    """Proxy n8n browse payloads to Playwright browser service."""
    _check_key(x_api_key)
    serialized_actions = [
        action.model_dump() if hasattr(action, "model_dump") else action.dict()
        for action in req.actions
    ]
    payload = {
        "actions": serialized_actions,
        "session_id": req.session_id,
        "dry_run": req.dry_run,
        "workflow_id": req.workflow_id,
        "run_id": req.run_id,
        "source": req.source,
    }
    return _forward_to_browser_service(payload=payload, bridge_api_key=x_api_key or "")


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


# ---------------------------------------------------------------------------
#  AI Round Table — Multi-LLM Council Deliberation
# ---------------------------------------------------------------------------

_council_sessions: List[Dict[str, Any]] = []

_TONGUE_COUNCIL_ROLES: Dict[str, Dict[str, str]] = {
    "KO": {"role": "Intent Analyst", "instruction": "Analyze the intent, motivation, and alignment of this query."},
    "AV": {"role": "Creative Advocate", "instruction": "Explore creative solutions and narrative possibilities."},
    "RU": {"role": "Security Auditor", "instruction": "Identify risks, vulnerabilities, and edge cases."},
    "CA": {"role": "Compute Optimizer", "instruction": "Evaluate efficiency, cost, and implementation feasibility."},
    "UM": {"role": "Governance Arbiter", "instruction": "Assess policy compliance, ethics, and governance alignment."},
    "DR": {"role": "Lead Architect", "instruction": "Synthesize all perspectives into a coherent, actionable plan."},
}


def _dispatch_single_provider(provider: str, prompt: str, system_prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
    """Dispatch to a single LLM provider and return text + metadata."""
    p = _normalize_provider(provider)
    try:
        req = LLMDispatchRequest(
            provider=provider,
            prompt=prompt,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        if p == "openai":
            raw = _dispatch_openai_compatible(req, "https://api.openai.com/v1/chat/completions", _OPENAI_API_KEY, _OPENAI_DEFAULT_MODEL)
            return {"provider": p, "text": _extract_openai_style_response(raw).get("text", ""), "status": "ok"}
        elif p == "xai":
            raw = _dispatch_openai_compatible(req, "https://api.x.ai/v1/chat/completions", _XAI_API_KEY, _XAI_DEFAULT_MODEL)
            return {"provider": p, "text": _extract_openai_style_response(raw).get("text", ""), "status": "ok"}
        elif p == "huggingface":
            raw = _dispatch_openai_compatible(req, "https://router.huggingface.co/v1/chat/completions", _HF_ROUTER_TOKEN, _HF_DEFAULT_MODEL)
            return {"provider": p, "text": _extract_openai_style_response(raw).get("text", ""), "status": "ok"}
        elif p == "anthropic":
            raw = _dispatch_anthropic(req)
            return {"provider": p, "text": _extract_anthropic_response(raw).get("text", ""), "status": "ok"}
        else:
            return {"provider": p, "text": "", "status": "unsupported"}
    except Exception as exc:
        return {"provider": p, "text": "", "status": "error", "error": str(exc)[:500]}


@app.post("/v1/council/deliberate")
async def council_deliberate(req: CouncilRequest, x_api_key: Optional[str] = Header(None)):
    """AI Round Table: fan query to multiple LLMs, run governance, synthesize consensus.

    Inspired by the AI Workflow Architect's Multi-AI Roundtable pattern:
    - Each provider gets the query with a Sacred Tongue role assignment
    - Responses go through SCBE governance scan
    - A synthesis round merges all perspectives into a governed result
    """
    _check_key(x_api_key)

    session_id = str(uuid.uuid4())[:12]
    tongue_role = _TONGUE_COUNCIL_ROLES.get(req.tongue, _TONGUE_COUNCIL_ROLES["DR"])
    base_system = req.system or f"You are {tongue_role['role']} in the SCBE AI Council. {tongue_role['instruction']}"

    # Round 1: Fan out to all providers
    responses: List[Dict[str, Any]] = []
    for provider in req.providers:
        p_norm = _normalize_provider(provider)
        # Check if provider is configured
        configured = {
            "openai": bool(_OPENAI_API_KEY),
            "anthropic": bool(_ANTHROPIC_API_KEY),
            "xai": bool(_XAI_API_KEY),
            "huggingface": bool(_HF_ROUTER_TOKEN),
        }
        if not configured.get(p_norm, False):
            responses.append({"provider": p_norm, "text": "", "status": "not_configured"})
            continue
        result = _dispatch_single_provider(provider, req.query, base_system)
        responses.append(result)

    # Governance scan each response
    governance_results = []
    if req.governance_scan:
        for resp in responses:
            if resp.get("text"):
                scan = _antivirus.scan(resp["text"])
                gov = scan.to_dict()
                resp["governance"] = gov
                governance_results.append(gov)

    # Multi-round debate (if rounds > 1)
    debate_log = [{"round": 1, "responses": responses}]
    for round_num in range(2, req.rounds + 1):
        prior_texts = [r.get("text", "") for r in responses if r.get("text")]
        if not prior_texts:
            break
        debate_prompt = (
            f"Previous council responses (Round {round_num - 1}):\n\n"
            + "\n---\n".join(prior_texts)
            + f"\n\nOriginal query: {req.query}\n\n"
            f"Critique the above responses. Identify agreements, disagreements, and blind spots. "
            f"Then provide your improved answer."
        )
        round_responses = []
        for provider in req.providers:
            p_norm = _normalize_provider(provider)
            configured = {
                "openai": bool(_OPENAI_API_KEY),
                "anthropic": bool(_ANTHROPIC_API_KEY),
                "xai": bool(_XAI_API_KEY),
                "huggingface": bool(_HF_ROUTER_TOKEN),
            }
            if not configured.get(p_norm, False):
                continue
            result = _dispatch_single_provider(provider, debate_prompt, base_system, max_tokens=1200)
            round_responses.append(result)
        debate_log.append({"round": round_num, "responses": round_responses})
        responses = round_responses  # latest round becomes the current state

    # Synthesis: merge all responses
    all_texts = [r.get("text", "") for r in responses if r.get("text")]
    if req.strategy == "majority":
        # Simple: pick the longest response (most detailed)
        synthesis = max(all_texts, key=len) if all_texts else ""
    elif req.strategy == "chain":
        synthesis = all_texts[-1] if all_texts else ""
    elif req.strategy == "debate":
        synthesis = "\n\n---\n\n".join(
            f"[{r.get('provider', '?')}]: {r.get('text', '')}"
            for r in responses if r.get("text")
        )
    else:  # consensus
        synthesis = " | ".join(all_texts) if len(all_texts) <= 2 else all_texts[0] if all_texts else ""

    # Final governance stamp
    final_governance = None
    if req.governance_scan and synthesis:
        final_scan = _antivirus.scan(synthesis)
        final_governance = final_scan.to_dict()

    session = {
        "session_id": session_id,
        "query": req.query,
        "tongue": req.tongue,
        "role": tongue_role["role"],
        "strategy": req.strategy,
        "rounds": req.rounds,
        "providers_used": [r.get("provider") for r in responses],
        "provider_count": len([r for r in responses if r.get("status") == "ok"]),
        "synthesis": synthesis[:3000],
        "governance": final_governance,
        "debate_rounds": len(debate_log),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _council_sessions.append(session)

    return {
        "session_id": session_id,
        "synthesis": synthesis,
        "responses": responses,
        "debate_log": debate_log,
        "governance": final_governance,
        "tongue_role": tongue_role,
        "strategy": req.strategy,
        "providers_active": len([r for r in responses if r.get("status") == "ok"]),
    }


@app.get("/v1/council/status")
async def council_status(x_api_key: Optional[str] = Header(None)):
    """Return recent council deliberation sessions."""
    _check_key(x_api_key)
    return {
        "total_sessions": len(_council_sessions),
        "recent": _council_sessions[-20:],
    }


# ---------------------------------------------------------------------------
#  Training pipeline integration (game events -> RealTimeHFTrainer)
# ---------------------------------------------------------------------------

_trainer = None
_trainer_lock = threading.Lock()


def _get_trainer():
    """Lazy-initialise and return the shared RealTimeHFTrainer.

    The trainer is created and started on the first request so that
    importing this module alone does not spawn background threads.
    """
    global _trainer
    if _trainer is not None:
        return _trainer
    with _trainer_lock:
        # Double-check after acquiring the lock
        if _trainer is not None:
            return _trainer
        try:
            from hf_trainer import RealTimeHFTrainer, load_dotenv

            load_dotenv()
            _trainer = RealTimeHFTrainer()
            _trainer.start()
            logger.info("RealTimeHFTrainer started via n8n bridge")
        except Exception as exc:
            logger.error("Failed to start RealTimeHFTrainer: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Training pipeline unavailable: {exc}",
            )
    return _trainer


# Map n8n game event types to TrainingEvent event_type values
_EVENT_TYPE_MAP: Dict[str, str] = {
    "battle_won": "battle",
    "battle_lost": "battle",
    "choice_made": "choice",
    "scene_transition": "dialogue",
    "evolution": "evolution",
    "gacha_pull": "choice",
    "level_up": "evolution",
    "quest_complete": "choice",
    "npc_dialogue": "dialogue",
    "dungeon_floor_cleared": "tower_floor",
    "boss_defeated": "battle",
    "tongue_mastered": "evolution",
    "companion_evolved": "evolution",
    "quest_progress": "choice",
}


@app.post("/v1/training/ingest")
async def training_ingest(
    req: TrainingIngestRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Accept a game event from n8n and feed it to the RealTimeHFTrainer.

    The event is converted into a TrainingEvent (prompt/response SFT pair)
    and enqueued for governance validation, local JSONL export, and
    optional HuggingFace Hub upload.
    """
    _check_key(x_api_key)

    trainer = _get_trainer()

    from hf_trainer import TrainingEvent

    # Build the SFT prompt/response pair from the game event
    mapped_type = _EVENT_TYPE_MAP.get(req.event_type, req.event_type)
    tongue = req.tongue or "KO"

    prompt = f"[{tongue}] {req.event_type}: {req.context}" if req.context else f"[{tongue}] {req.event_type}"
    response = req.outcome or f"{req.event_type} recorded"

    meta: Dict[str, Any] = {
        "tongue": tongue,
        "source": "n8n",
        "original_event_type": req.event_type,
    }
    if req.metadata:
        meta.update(req.metadata)

    event = TrainingEvent(
        event_type=mapped_type,
        prompt=prompt,
        response=response,
        metadata=meta,
    )

    trainer.put_event(event)

    return {
        "status": "queued",
        "event_type": mapped_type,
        "trainer_stats": trainer.get_stats(),
    }


@app.get("/v1/training/status")
async def training_status(x_api_key: Optional[str] = Header(None)):
    """Return the current trainer pipeline status."""
    _check_key(x_api_key)
    trainer = _get_trainer()
    return trainer.get_status_dict()


# ---------------------------------------------------------------------------
#  Hyperbolic Lattice 2.5D Workflow Route
# ---------------------------------------------------------------------------

def _notion_token() -> str:
    token = (
        os.environ.get("NOTION_TOKEN", "").strip()
        or os.environ.get("NOTION_API_KEY", "").strip()
    )
    return token


def _notion_request(
    *,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout_sec: int = 30,
) -> Dict[str, Any]:
    token = _notion_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Notion integration unavailable: NOTION_TOKEN/NOTION_API_KEY is not configured.",
        )

    url = f"https://api.notion.com{path}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib_request.Request(url=url, method=method.upper(), data=data)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Notion-Version", os.environ.get("NOTION_VERSION", "2025-09-03"))
    req.add_header("Content-Type", "application/json")

    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "notion_http_error",
                "upstream_status": exc.code,
                "path": path,
                "body": detail[:1800],
            },
        )
    except urllib_error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Notion unavailable: {exc.reason}",
        )


def _notion_rich_text_to_plain(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    out: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        plain = item.get("plain_text")
        if isinstance(plain, str) and plain.strip():
            out.append(plain.strip())
            continue
        text_obj = item.get("text", {})
        if isinstance(text_obj, dict):
            content = text_obj.get("content")
            if isinstance(content, str) and content.strip():
                out.append(content.strip())
    return " ".join(out).strip()


def _notion_page_title(page: Dict[str, Any]) -> str:
    properties = page.get("properties", {})
    if isinstance(properties, dict):
        for _, prop in properties.items():
            if not isinstance(prop, dict):
                continue
            if prop.get("type") == "title":
                title = _notion_rich_text_to_plain(prop.get("title", []))
                if title:
                    return title
    fallback = page.get("id", "notion-page")
    return str(fallback)


def _notion_page_body(page_id: str, page_size: int = 100) -> str:
    page_size = max(1, min(100, int(page_size)))
    cursor: Optional[str] = None
    lines: List[str] = []
    while True:
        suffix = f"?page_size={page_size}"
        if cursor:
            suffix = f"{suffix}&start_cursor={cursor}"
        data = _notion_request(method="GET", path=f"/v1/blocks/{page_id}/children{suffix}")
        for block in data.get("results", []):
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if not isinstance(block_type, str):
                continue
            block_payload = block.get(block_type, {})
            if not isinstance(block_payload, dict):
                continue
            plain = _notion_rich_text_to_plain(block_payload.get("rich_text", []))
            if plain:
                lines.append(plain)
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return "\n".join(lines).strip()


def _fetch_notion_notes(
    *,
    query: str,
    page_size: int,
    max_notes: int,
) -> List[Dict[str, Any]]:
    page_size = max(1, min(100, int(page_size)))
    max_notes = max(1, min(200, int(max_notes)))

    body: Dict[str, Any] = {
        "filter": {"property": "object", "value": "page"},
        "page_size": page_size,
        "sort": {"direction": "descending", "timestamp": "last_edited_time"},
    }
    if query.strip():
        body["query"] = query.strip()

    data = _notion_request(method="POST", path="/v1/search", payload=body)
    pages = data.get("results", [])
    notes: List[Dict[str, Any]] = []

    for page in pages:
        if len(notes) >= max_notes:
            break
        if not isinstance(page, dict) or page.get("object") != "page":
            continue
        page_id = str(page.get("id", "")).strip()
        if not page_id:
            continue
        title = _notion_page_title(page)
        body_text = _notion_page_body(page_id=page_id, page_size=100)
        text = f"{title}\n\n{body_text}".strip()
        if not text:
            continue
        notes.append(
            {
                "note_id": f"notion:{page_id}",
                "text": text,
                "tags": ["notion", "workspace", "search"],
                "source": "notion",
                "authority": "internal",
                "tongue": "KO",
            }
        )
    return notes


def _resolve_repo_relative_output_path(output_path: str) -> Path:
    candidate = Path((output_path or "").strip())
    if candidate.is_absolute():
        raise HTTPException(status_code=400, detail="Output path must be repo-relative")
    if not candidate.parts:
        raise HTTPException(status_code=400, detail="Output path is required")
    if any(part in {"..", ""} for part in candidate.parts):
        raise HTTPException(status_code=400, detail="Invalid output path")
    safe_root = Path(_PROJECT).resolve()
    out = safe_root.joinpath(*candidate.parts).resolve(strict=False)
    try:
        out.relative_to(safe_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid output path") from exc
    if out.suffix.lower() != ".jsonl":
        raise HTTPException(status_code=400, detail="Output path must end with .jsonl")
    return out


def _write_lattice_jsonl(payload: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    out = _resolve_repo_relative_output_path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = payload.get("notes", []) if isinstance(payload.get("notes"), list) else []
    line_count = 0
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            if not isinstance(row, dict):
                continue
            record = {
                "note_id": row.get("note_id"),
                "bundle_id": row.get("bundle_id"),
                "tongue": row.get("tongue"),
                "authority": row.get("authority"),
                "intent_vector": row.get("intent_vector"),
                "metric_tags": row.get("metric_tags"),
                "metrics": row.get("metrics"),
                "position": row.get("position"),
                "phase_rad": row.get("phase_rad"),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            line_count += 1
    return {"path": str(out), "rows": line_count}


def _validate_hf_dataset_repo(repo_id: str) -> str:
    normalized = (repo_id or "").strip()
    if not normalized or not _HF_DATASET_REPO_RE.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail="hf_dataset_repo must match 'owner/name' using only letters, numbers, '.', '_' or '-'.",
        )
    return normalized


def _sanitize_hf_commit_message(message: str) -> str:
    normalized = " ".join(str(message or "").replace("\r", " ").replace("\n", " ").split())
    if not normalized:
        return "feat(dataset): lattice25d notes export"
    if len(normalized) > _HF_COMMIT_MESSAGE_MAX_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"hf_commit_message must be {_HF_COMMIT_MESSAGE_MAX_LEN} characters or fewer.",
        )
    return normalized


def _upload_lattice25d_export_to_hf(
    *,
    repo_id: str,
    local_path: str,
    commit_message: str,
    create_pr: bool,
) -> Dict[str, Any]:
    allowed = _HF_ALLOWED_DATASET_REPOS
    repo_id = _validate_hf_dataset_repo(repo_id)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="HF push is disabled until SCBE_HF_ALLOWED_DATASET_REPOS is configured.",
        )
    if repo_id.lower() not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"HF push blocked for non-allowlisted dataset repo: {repo_id}",
        )
    if not _HF_ROUTER_TOKEN:
        raise HTTPException(status_code=503, detail="HF token not configured for dataset upload.")

    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="huggingface_hub is required for dataset upload.",
        ) from exc

    remote_path = f"lattice25d/{Path(local_path).name}"
    api = HfApi(token=_HF_ROUTER_TOKEN)
    try:
        api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=remote_path,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=commit_message,
            create_pr=create_pr,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"HF dataset upload failed: {exc}") from exc

    return {
        "status": "uploaded",
        "dataset_repo": repo_id,
        "path_in_repo": remote_path,
        "create_pr": create_pr,
    }


@app.post("/v1/workflow/lattice25d")
async def workflow_lattice25d(
    req: Lattice25DRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Embed notes into HyperbolicLattice25D with metric tags and intent vectors."""
    _check_key(x_api_key)

    from hydra.lattice25d_ops import (
        NoteRecord,
        build_lattice25d_payload,
        load_notes_from_glob,
    )

    notes: List[NoteRecord] = []
    for idx, row in enumerate(req.notes):
        text_value = (row.text or "").strip()
        if not text_value:
            continue
        note_id = row.note_id or f"n8n-note-{idx}"
        notes.append(
            NoteRecord(
                note_id=note_id,
                text=text_value,
                tags=tuple(row.tags),
                source=row.source or "n8n",
                authority=row.authority or "public",
                tongue=row.tongue or "KO",
                phase_rad=row.phase_rad,
            )
        )

    remaining = max(0, int(req.max_notes) - len(notes))
    if req.include_notion_notes and remaining > 0:
        notion_rows = _fetch_notion_notes(
            query=req.notion_query,
            page_size=req.notion_page_size,
            max_notes=min(req.notion_max_notes, remaining),
        )
        for row in notion_rows:
            if len(notes) >= int(req.max_notes):
                break
            text_value = str(row.get("text", "")).strip()
            if not text_value:
                continue
            notes.append(
                NoteRecord(
                    note_id=str(row.get("note_id", f"notion-note-{len(notes)}")),
                    text=text_value,
                    tags=tuple(row.get("tags", [])),
                    source=str(row.get("source", "notion")),
                    authority=str(row.get("authority", "internal")),
                    tongue=str(row.get("tongue", "KO")),
                    phase_rad=row.get("phase_rad"),
                )
            )

    if req.include_repo_notes:
        remaining = max(0, int(req.max_notes) - len(notes))
        if remaining > 0:
            try:
                notes.extend(
                    load_notes_from_glob(
                        pattern=req.notes_glob,
                        max_notes=remaining,
                        source="repo",
                        authority="internal",
                    )
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not notes:
        raise HTTPException(
            status_code=400,
            detail="No notes supplied. Provide notes[] or set include_repo_notes=true with a valid notes_glob.",
        )

    payload = build_lattice25d_payload(
        notes,
        cell_size=req.cell_size,
        max_depth=req.max_depth,
        phase_weight=req.phase_weight,
        index_mode=req.index_mode,
        quadtree_capacity=req.quadtree_capacity,
        quadtree_z_variance=req.quadtree_z_variance,
        quadtree_query_extent=req.quadtree_query_extent,
        radius=req.radius,
        query_intent=list(req.query_intent),
        query_x=req.query_x,
        query_y=req.query_y,
        query_phase=req.query_phase,
        query_top_k=req.query_top_k,
    )

    if req.hf_output_path:
        export_result = _write_lattice_jsonl(payload, req.hf_output_path)
        export_result["status"] = "written"

        if req.hf_dataset_repo:
            dataset_repo = _validate_hf_dataset_repo(req.hf_dataset_repo)
            export_result["dataset_repo"] = dataset_repo
            if req.hf_push:
                export_result.update(
                    _upload_lattice25d_export_to_hf(
                        repo_id=dataset_repo,
                        local_path=export_result["path"],
                        commit_message=_sanitize_hf_commit_message(req.hf_commit_message),
                        create_pr=req.hf_create_pr,
                    )
                )
            else:
                export_result["status"] = "staged"
        payload["hf_export"] = export_result

    if not req.include_note_payload:
        payload.pop("notes", None)

    payload["source"] = "n8n-bridge"
    payload["notes_glob"] = req.notes_glob if req.include_repo_notes else None
    payload["notion_query"] = req.notion_query if req.include_notion_notes else None
    payload["input_notion_enabled"] = req.include_notion_notes
    payload["input_notes"] = len(req.notes)
    return payload


# ---------------------------------------------------------------------------
#  ChoiceScript Branching Workflow Engine
# ---------------------------------------------------------------------------

class BranchExploreRequest(BaseModel):
    """Execute a branching scene graph with multi-path exploration."""
    graph_name: str = "research_pipeline"
    topic: str = ""
    strategy: str = "all_paths"
    context: Dict[str, Any] = {}
    max_paths: int = 20
    max_depth: int = 50
    export_n8n: bool = False
    export_choicescript: bool = False


class BranchActionRequest(BaseModel):
    """Single scene action callback from n8n branching workflow."""
    scene: str
    action: str
    params: Dict[str, Any] = {}


@app.post("/v1/workflow/branch")
async def workflow_branch_explore(req: BranchExploreRequest, x_api_key: Optional[str] = Header(None)):
    """Execute a ChoiceScript branching workflow with multi-path exploration.

    Supports pre-built graphs (research_pipeline, content_publisher, training_funnel)
    or custom graphs via the graph_name parameter.
    """
    _check_key(x_api_key)

    try:
        from workflows.n8n.choicescript_branching_engine import (
            BranchingEngine,
            ExploreStrategy,
            build_research_pipeline_graph,
            build_content_publishing_graph,
            build_training_funnel_graph,
        )
    except ImportError:
        # Fallback: direct import from same directory
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "choicescript_branching_engine",
            os.path.join(os.path.dirname(__file__), "choicescript_branching_engine.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        BranchingEngine = mod.BranchingEngine
        ExploreStrategy = mod.ExploreStrategy
        build_research_pipeline_graph = mod.build_research_pipeline_graph
        build_content_publishing_graph = mod.build_content_publishing_graph
        build_training_funnel_graph = mod.build_training_funnel_graph

    # Select graph template
    graph_builders = {
        "research_pipeline": lambda: build_research_pipeline_graph(req.topic or "general research"),
        "content_publisher": build_content_publishing_graph,
        "training_funnel": build_training_funnel_graph,
    }

    builder = graph_builders.get(req.graph_name)
    if not builder:
        raise HTTPException(status_code=400, detail=f"Unknown graph: {req.graph_name}. Available: {list(graph_builders.keys())}")

    graph = builder()
    engine = BranchingEngine(
        bridge_url=f"http://127.0.0.1:{os.environ.get('PORT', '8001')}",
        max_depth=req.max_depth,
        max_paths=req.max_paths,
    )

    # Map strategy string
    strategy_map = {s.value: s for s in ExploreStrategy}
    strategy = strategy_map.get(req.strategy, ExploreStrategy.ALL_PATHS)

    ctx = dict(req.context)
    if req.topic:
        ctx["query"] = req.topic

    result = engine.explore_sync(graph, context=ctx, strategy=strategy)

    response: Dict[str, Any] = {
        "graph_name": result.graph_name,
        "strategy": result.strategy.value,
        "total_scenes": result.total_scenes,
        "coverage": round(result.coverage, 3),
        "paths_explored": len(result.paths),
        "best_path": {
            "scenes": result.best_path.scenes_visited,
            "score": result.best_path.score,
            "actions": len(result.best_path.actions_taken),
        } if result.best_path else None,
        "all_paths": [
            {
                "id": p.path_id,
                "scenes": p.scenes_visited,
                "score": p.score,
                "terminal": p.terminal,
                "error": p.error,
            }
            for p in result.paths
        ],
        "timestamp": result.timestamp,
    }

    if req.export_choicescript:
        response["choicescript"] = graph.to_choicescript()

    if req.export_n8n:
        response["n8n_workflow"] = graph.to_n8n_workflow()

    return response


@app.post("/v1/workflow/branch/action")
async def workflow_branch_action(req: BranchActionRequest, x_api_key: Optional[str] = Header(None)):
    """Execute a single scene action from a branching workflow (callback from n8n)."""
    _check_key(x_api_key)

    # Route to existing bridge endpoints based on action type
    action_routes = {
        "governance_scan": lambda p: _antivirus.scan(p.get("content", "")).to_dict(),
        "noop": lambda p: {"status": "ok"},
    }

    handler = action_routes.get(req.action)
    if handler:
        return {"scene": req.scene, "action": req.action, "result": handler(req.params)}

    # Default: return stub result
    return {
        "scene": req.scene,
        "action": req.action,
        "result": {"status": "stub", "params": req.params},
    }
