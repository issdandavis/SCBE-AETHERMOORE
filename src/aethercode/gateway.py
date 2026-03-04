"""
AetherCode Gateway — Unified AI Development Platform API
=========================================================

Single entry point that unifies:
  - PollyPad IDE (multi-LLM chat/code/research)  → port 8200
  - AetherNet Social (governed feed, tasks, XP)   → port 8300
  - OctoTree Accelerator (216x parallel browsing)
  - Context Scorer (7D reference evaluation)
  - SCBE Governance (L13 scan on every request)

Run:
    python -m uvicorn src.aethercode.gateway:app --port 8400

@layer Layer 1, Layer 13, Layer 14
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import hashlib
import io
import json
import math
import os
import re
import runpy
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, unquote, urlparse

# ---------------------------------------------------------------------------
#  Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
_src = str(REPO_ROOT / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
#  FastAPI
# ---------------------------------------------------------------------------

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
#  Import subsystems (graceful fallback)
# ---------------------------------------------------------------------------

# OctoArmor — multi-LLM routing
try:
    from fleet.octo_armor import OctoArmor, TENTACLE_REGISTRY
    _OCTO_AVAILABLE = True
except ImportError:
    _OCTO_AVAILABLE = False
    TENTACLE_REGISTRY = {}

try:
    from src.security.secret_store import pick_secret
except Exception:  # pragma: no cover - fallback when optional dependency is unavailable
    def pick_secret(*_names: str) -> Tuple[str, str]:
        return "", ""

# OctoTree — parallel browser acceleration
try:
    from browser.octotree_accelerator import OctoTree, AcceleratorConfig, Baton
    _OCTOTREE_AVAILABLE = True
except ImportError:
    _OCTOTREE_AVAILABLE = False

# Context Scorer — 7D reference evaluation
try:
    from browser.context_scorer import (
        ContextScorer, ContextReference, ContextScore,
        InfoState, DepthLevel, SourceType, MagnetismField, FiveW,
    )
    _SCORER_AVAILABLE = True
except ImportError:
    _SCORER_AVAILABLE = False

# AetherNet — agent identity, task monitoring
try:
    from aaoe.agent_identity import AgentRegistry, GeoSeal, AccessTier
    from aaoe.task_monitor import TaskMonitor, IntentVector
    from aaoe.ephemeral_prompt import EphemeralPromptEngine
    _AAOE_AVAILABLE = True
except ImportError:
    _AAOE_AVAILABLE = False

# Firebase
try:
    from fleet.firebase_connector import FirebaseSync
    _FIREBASE = True
except ImportError:
    _FIREBASE = False

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2
VERSION = "0.1.0"
PRODUCT_NAME = "AetherCode"
TRAINING_DIR = REPO_ROOT / "training-data" / "aethercode"
TRAINING_DIR.mkdir(parents=True, exist_ok=True)
AETHERCODE_DIR = Path(__file__).parent
AETHERCODE_STATIC_DIR = AETHERCODE_DIR / "static"

_LEGACY_REPLIT_LOCAL_REPO_PATHS: Dict[str, Path] = {
    "ai-workflow-architect-main": REPO_ROOT / "external" / "intake" / "ai-workflow-architect" / "ai-workflow-architect-main",
    "ai-workflow-architect-replit": REPO_ROOT / "external" / "intake" / "ai-workflow-architect" / "ai-workflow-architect-main",
    "kiro_version_ai-workflow-architect": REPO_ROOT / "external" / "intake" / "ai-workflow-architect" / "ai-workflow-architect-main",
    "ai-workflow-platform": REPO_ROOT / "external" / "intake" / "ai-workflow-architect" / "ai-workflow-architect-main",
}

# Curated lore visuals exposed to the UI. Whitelisted to avoid arbitrary file serving.
_LORE_ART_REGISTRY: Dict[str, Dict[str, Any]] = {
    "codex-spiralverse": {
        "title": "Codex I - Spiralverse",
        "story": "Codex I",
        "path": REPO_ROOT / "shopify" / "aethermoore-creator-os" / "assets" / "spiralverse-aqm.png",
    },
    "everweave-fibonacci": {
        "title": "Everweave Harmonic Spiral",
        "story": "Codex II",
        "path": REPO_ROOT / "docs" / "grants" / "figures" / "fig3_fibonacci_spirals.png",
    },
    "polloneth-protocol": {
        "title": "Polloneth Protocol Weave",
        "story": "Codex III",
        "path": REPO_ROOT / "shopify" / "aethermoore-creator-os" / "assets" / "protocol-diagram-symphonic.png",
    },
    "spiral-risk-zones": {
        "title": "Spiral Risk Landscape",
        "story": "Everweave Atlas",
        "path": REPO_ROOT / "docs" / "grants" / "figures" / "fig5_poincare_risk_zones.png",
    },
}

# Canonical provider env names with accepted aliases.
# This lets users keep their existing key names while AetherCode consumes
# one stable set of env vars internally.
_PROVIDER_ENV_ALIASES: Dict[str, List[str]] = {
    "GOOGLE_AI_API_KEY": ["GOOGLE_AI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "GITHUB_TOKEN": ["GITHUB_TOKEN", "GITHUB_PAT"],
    "HF_TOKEN": ["HF_TOKEN", "HUGGINGFACE_TOKEN", "HF_HUB_TOKEN"],
    "XAI_API_KEY": ["XAI_API_KEY", "GROK_API_KEY"],
    "OPENROUTER_API_KEY": ["OPENROUTER_API_KEY", "OPEN_ROUTER_API_KEY", "OR_API_KEY"],
    "ANTHROPIC_API_KEY": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
    "OPENAI_API_KEY": ["OPENAI_API_KEY", "OPENAI_KEY"],
    "GROQ_API_KEY": ["GROQ_API_KEY", "GROQ_KEY"],
    "CEREBRAS_API_KEY": ["CEREBRAS_API_KEY", "CEREBRAS_KEY"],
    "MISTRAL_API_KEY": ["MISTRAL_API_KEY"],
    "COHERE_API_KEY": ["COHERE_API_KEY"],
    "TOGETHER_API_KEY": ["TOGETHER_API_KEY"],
    "DEEPINFRA_API_KEY": ["DEEPINFRA_API_KEY"],
    "NVIDIA_API_KEY": ["NVIDIA_API_KEY"],
    "NOVITA_API_KEY": ["NOVITA_API_KEY"],
    "FIREWORKS_API_KEY": ["FIREWORKS_API_KEY"],
    "SAMBANOVA_API_KEY": ["SAMBANOVA_API_KEY"],
    "CLOUDFLARE_API_KEY": ["CLOUDFLARE_API_KEY", "CLOUDFLARE_TOKEN"],
}


def _read_env_or_secret(names: List[str]) -> Tuple[str, str]:
    """Return first non-empty value from env or secret store with source label."""
    for name in names:
        value = os.environ.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip(), f"env:{name}"

    try:
        source, value = pick_secret(*names)
    except Exception:
        source, value = "", ""

    if isinstance(value, str) and value.strip():
        src = source or names[0]
        return value.strip(), f"secret:{src}"
    return "", ""


def _bootstrap_provider_env_aliases() -> Dict[str, str]:
    """Populate canonical provider env vars from common aliases/secret store."""
    resolved: Dict[str, str] = {}
    for canonical, aliases in _PROVIDER_ENV_ALIASES.items():
        existing = os.environ.get(canonical)
        if isinstance(existing, str) and existing.strip():
            resolved[canonical] = f"env:{canonical}"
            continue
        value, source = _read_env_or_secret(aliases)
        if value:
            os.environ[canonical] = value
            resolved[canonical] = source
    return resolved


_PROVIDER_BOOTSTRAP_SOURCES: Dict[str, str] = _bootstrap_provider_env_aliases()

_DEFAULT_WORKSPACE_OWNER = (
    os.getenv("AETHERCODE_WORKSPACE_OWNER", "issdandavis").strip() or "issdandavis"
)
_DEFAULT_WORKSPACE_REPO = (
    os.getenv("AETHERCODE_WORKSPACE_REPO", "aethercode-browser-workbench").strip()
    or "aethercode-browser-workbench"
)
_DEFAULT_WORKSPACE_BRANCH = (
    os.getenv("AETHERCODE_WORKSPACE_BRANCH", "main").strip() or "main"
)
_DEFAULT_WORKSPACE_MODE = (
    "browser_repo" if _DEFAULT_WORKSPACE_REPO.lower() == "scbe-aethermoore" else "shared_repo"
)

# ---------------------------------------------------------------------------
#  Billing Tiers (Stripe-ready)
# ---------------------------------------------------------------------------

class BillingTier(Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


# AetherCode is FREE forever. Users bring their own API keys for paid models.
# Tier config kept for internal capability mapping — everything unlocked.
_ALL_UNLOCKED = {
    "name": "AetherCode",
    "price_monthly": 0,
    "messages_per_day": -1,  # unlimited
    "code_mode": True,
    "multi_agent": True,
    "research_mode": True,
    "tentacles": 20,         # all tentacles
    "octotree_depth": 3,     # 216 workers
    "training_export": True,
    "priority_routing": True,
    "voice_input": True,
    "stripe_price_id": None,
}

TIER_CONFIG = {
    BillingTier.FREE: _ALL_UNLOCKED,
    BillingTier.PRO: _ALL_UNLOCKED,
    BillingTier.TEAM: _ALL_UNLOCKED,
    BillingTier.ENTERPRISE: _ALL_UNLOCKED,
}

# ---------------------------------------------------------------------------
#  Request / Response Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    mode: str = "chat"  # chat, code, research, browse
    think_mode: str = "standard"  # standard, fast, deep, harmonic
    model: Optional[str] = None
    tentacle: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    context: Optional[List[Dict[str, str]]] = None
    session_id: Optional[str] = None
    language: Optional[str] = None  # programming language for code mode
    file_path: Optional[str] = None  # file context for code mode


class ChatResponse(BaseModel):
    id: str
    status: str
    mode: str
    tentacle: str
    model: str
    response: str
    latency_ms: float
    governance_score: float
    tokens_used: int = 0
    session_id: str
    training_pair_id: Optional[str] = None


class BrowseRequest(BaseModel):
    urls: List[str]
    task: str = "extract"
    depth: int = 2
    max_concurrent: int = 36


class BrowseResponse(BaseModel):
    id: str
    urls_processed: int
    results: List[Dict[str, Any]]
    latency_ms: float
    octotree_depth: int
    workers_used: int


class ScoreRequest(BaseModel):
    content: str
    url: str = ""
    author_era: str = "contemporary"
    target_audience: str = "general"
    depth_levels: List[str] = ["facts"]
    source_type: str = "community"


class RoundPitRequest(BaseModel):
    message: str
    think_mode: str = "harmonic"  # fast, deep, research, harmonic
    mode: str = "research"
    min_models: int = 4
    max_models: int = 6
    include_spin_data: bool = True
    background_reflection: bool = True
    session_id: Optional[str] = None


class CrossTalkRequest(BaseModel):
    summary: str
    recipient: str = "agent.claude"
    sender: str = "agent.codex"
    intent: str = "handoff"
    status: str = "in_progress"
    task_id: str = "AETHERCODE-UI"
    next_action: str = ""
    risk: str = "low"
    repo: str = "SCBE-AETHERMOORE"
    branch: str = "local"
    proof: List[str] = Field(default_factory=list)
    session_id: str = ""
    codename: str = ""
    where: str = ""
    why: str = ""
    how: str = ""


class AI2AIStartRequest(BaseModel):
    interval_seconds: int = Field(default=180, ge=45, le=3600)
    max_models: int = Field(default=4, ge=2, le=8)
    seed_prompt: str = (
        "Audit legacy Replit app capabilities and propose one concrete integration step "
        "for the current SCBE-AETHERMOORE stack."
    )


class AI2AITickRequest(BaseModel):
    prompt: str = ""


class WebResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)
    max_results: int = Field(default=8, ge=1, le=20)
    include_duckduckgo: bool = True
    include_google_news: bool = True
    include_arxiv: bool = True
    fetch_snippets: bool = True


class AI2AIWorkflowDebateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1200)
    max_models: int = Field(default=4, ge=2, le=8)
    create_issue: bool = True
    labels: List[str] = Field(default_factory=lambda: ["ai2ai", "workflow"])
    assignees: List[str] = Field(default_factory=list)
    min_avg_governance: float = Field(default=0.64, ge=0.0, le=1.0)
    min_any_governance: float = Field(default=0.45, ge=0.0, le=1.0)
    require_tests_hint: bool = True


class AI2AIWorkflowReviewGateRequest(BaseModel):
    summary: str = Field(default="", max_length=6000)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    min_avg_governance: float = Field(default=0.64, ge=0.0, le=1.0)
    min_any_governance: float = Field(default=0.45, ge=0.0, le=1.0)
    require_tests_hint: bool = True


class RepoWorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    private: bool = True
    auto_init: bool = True
    attach: bool = True
    branch: str = "main"


class RepoWorkspaceAttachRequest(BaseModel):
    owner: str = Field(min_length=1, max_length=100)
    repo: str = Field(min_length=1, max_length=100)
    branch: str = "main"
    mode: str = "shared_repo"


class RepoWorkspaceIssueRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    body: str = ""
    labels: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)


class UserSession(BaseModel):
    session_id: str
    user_id: str
    tier: str
    messages_today: int = 0
    created_at: str = ""
    last_active: str = ""
    conversation: List[Dict[str, str]] = []


# ---------------------------------------------------------------------------
#  In-memory state
# ---------------------------------------------------------------------------

_sessions: Dict[str, Dict[str, Any]] = {}
_daily_usage: Dict[str, int] = {}  # user_id → message count today
_training_pairs: List[Dict[str, Any]] = []
_active_ws: Dict[str, WebSocket] = {}
_run_history: List[Dict[str, Any]] = []
_max_run_history = 200
_autopilot_task: Optional[asyncio.Task] = None
_dashboard_actions: Dict[str, str] = {
    "post_content": "Publish next item from content queue",
    "run_research": "Start a Polly research sweep",
    "check_patent": "Check USPTO status for #63/961,403",
    "push_training": "Merge and push training data to HuggingFace",
    "list_products": "List digital products on storefronts",
}
_ops_supported_actions = {"crosstalk", "portal", "backup", "synth", "publish", "monetize"}
_ops_dashboard_action_map: Dict[str, str] = {
    "synth": "run_research",
    "publish": "post_content",
    "monetize": "list_products",
}
_ops_backup_builtin_source = ["src/aethercode/ide.html"]
_ops_backup_builtin_destinations = [
    "artifacts/storage_ship/default_a",
    "artifacts/storage_ship/default_b",
]
_ops_backup_defaults_path = REPO_ROOT / "config" / "governance" / "ops_backup_defaults.json"
_action_revenue_usd: Dict[str, float] = {
    "post_content": 0.25,
    "list_products": 0.35,
    "run_research": 0.05,
    "push_training": 0.05,
    "check_patent": 0.00,
}
_autopilot_state: Dict[str, Any] = {
    "enabled": False,
    "ai_cursor_enabled": False,
    "goal": "Autopilot idle",
    "target_usd": 1.0,
    "estimated_revenue_today_usd": 0.0,
    "revenue_day": datetime.now(timezone.utc).date().isoformat(),
    "status": "idle",
    "last_action": "",
    "last_error": "",
    "started_at": "",
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
_ai2ai_task: Optional[asyncio.Task] = None
_ai2ai_state: Dict[str, Any] = {
    "enabled": False,
    "status": "idle",
    "interval_seconds": 180,
    "max_models": 4,
    "cycles": 0,
    "seed_prompt": "Audit legacy Replit app capabilities and propose one concrete integration step.",
    "last_summary": "",
    "last_error": "",
    "started_at": "",
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
_spin_context_cache: List[str] = []
_spin_context_loaded = False

_OBS_NOTES_CONTEXT = REPO_ROOT / "notes" / "_context.md"
_OBS_NOTES_INBOX = REPO_ROOT / "notes" / "_inbox.md"
_OBS_AGENT_CODEX = REPO_ROOT / "agents" / "codex.md"
_CROSSTALK_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"
_SESSION_SIGNON_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "session_signons.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_repo_workspace: Dict[str, Any] = {
    "owner": _DEFAULT_WORKSPACE_OWNER,
    "repo": _DEFAULT_WORKSPACE_REPO,
    "branch": _DEFAULT_WORKSPACE_BRANCH,
    "mode": _DEFAULT_WORKSPACE_MODE,
    "source": "bootstrap",
    "updated_at": _utc_now_iso(),
}


def _workspace_ref() -> str:
    return f"{_repo_workspace.get('owner', 'issdandavis')}/{_repo_workspace.get('repo', 'SCBE-AETHERMOORE')}@{_repo_workspace.get('branch', 'main')}"


def _workspace_snapshot() -> Dict[str, Any]:
    return {
        "owner": _repo_workspace.get("owner", ""),
        "repo": _repo_workspace.get("repo", ""),
        "branch": _repo_workspace.get("branch", "main"),
        "mode": _repo_workspace.get("mode", "shared_repo"),
        "source": _repo_workspace.get("source", "unknown"),
        "updated_at": _repo_workspace.get("updated_at", _utc_now_iso()),
        "ref": _workspace_ref(),
    }


def _set_workspace_repo(owner: str, repo: str, branch: str = "main", mode: str = "shared_repo", source: str = "api") -> Dict[str, Any]:
    _repo_workspace["owner"] = owner.strip()
    _repo_workspace["repo"] = repo.strip()
    _repo_workspace["branch"] = branch.strip() or "main"
    _repo_workspace["mode"] = mode.strip() or "shared_repo"
    _repo_workspace["source"] = source.strip() or "api"
    _repo_workspace["updated_at"] = _utc_now_iso()
    return _workspace_snapshot()


def _github_token() -> str:
    return os.environ.get("GITHUB_TOKEN", "").strip()


def _github_headers(require_auth: bool = False) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if require_auth and not token:
        raise HTTPException(400, "GITHUB_TOKEN not set in environment or secret store")
    return headers


async def _github_repo_probe(owner: str, repo: str) -> Dict[str, Any]:
    owner = owner.strip()
    repo = repo.strip()
    if not owner or not repo:
        return {"ok": False, "error": "owner/repo required"}
    try:
        import httpx
    except ImportError:
        return {"ok": False, "error": "httpx package not installed"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=_github_headers(require_auth=False),
            )
    except Exception as exc:
        return {"ok": False, "error": f"github_probe_failed: {str(exc)[:220]}"}

    if resp.status_code != 200:
        return {
            "ok": False,
            "status_code": resp.status_code,
            "error": f"github_{resp.status_code}: {resp.text[:220]}",
        }

    data = resp.json()
    return {
        "ok": True,
        "owner": owner,
        "repo": repo,
        "default_branch": data.get("default_branch", "main"),
        "private": bool(data.get("private", False)),
        "html_url": data.get("html_url", ""),
        "description": data.get("description", ""),
    }


async def _github_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        import httpx
    except ImportError:
        raise HTTPException(500, "httpx package not installed")

    payload: Dict[str, Any] = {
        "title": title.strip(),
        "body": body.strip(),
    }
    if labels:
        payload["labels"] = [x for x in labels if str(x).strip()]
    if assignees:
        payload["assignees"] = [x for x in assignees if str(x).strip()]
    if not payload["title"]:
        raise HTTPException(400, "title is required")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers=_github_headers(require_auth=True),
                json=payload,
            )
    except Exception as exc:
        raise HTTPException(502, f"GitHub issue create failed: {str(exc)[:220]}")

    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"GitHub issue create error: {resp.text[:280]}")
    return resp.json()


def _clean_text_block(value: str, max_chars: int = 1400) -> str:
    text = value or ""
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _extract_duckduckgo_links(html_text: str, max_results: int) -> List[str]:
    links: List[str] = []
    seen: set = set()
    for raw in re.findall(r'href="([^"]+)"', html_text):
        if "duckduckgo.com/l/?" in raw and "uddg=" in raw:
            parsed = urlparse(raw)
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            target = unquote(target).strip()
        elif raw.startswith("http"):
            target = raw.strip()
        else:
            continue

        if not target.startswith("http"):
            continue
        if target in seen:
            continue
        seen.add(target)
        links.append(target)
        if len(links) >= max_results:
            break
    return links


async def _duckduckgo_search(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    try:
        import httpx
    except ImportError:
        return []

    url = "https://duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (AetherCodeResearch/1.0)"}
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, params={"q": query}, headers=headers)
    except Exception:
        return []
    if resp.status_code != 200:
        return []
    links = _extract_duckduckgo_links(resp.text, max_results=max_results)
    return [{"source": "duckduckgo", "url": link, "title": ""} for link in links]


async def _google_news_search(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    try:
        import httpx
        import xml.etree.ElementTree as ET
    except ImportError:
        return []

    rss_url = "https://news.google.com/rss/search"
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(rss_url, params=params)
    except Exception:
        return []
    if resp.status_code != 200:
        return []

    try:
        root = ET.fromstring(resp.text)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for item in root.findall(".//item")[:max_results]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not link:
            continue
        out.append({"source": "google_news_rss", "title": title, "url": link})
    return out


async def _arxiv_search(query: str, max_results: int = 6) -> List[Dict[str, Any]]:
    try:
        import httpx
        import xml.etree.ElementTree as ET
    except ImportError:
        return []

    params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results}
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get("http://export.arxiv.org/api/query", params=params)
    except Exception:
        return []
    if resp.status_code != 200:
        return []

    try:
        root = ET.fromstring(resp.text)
    except Exception:
        return []

    ns = {"a": "http://www.w3.org/2005/Atom"}
    out: List[Dict[str, Any]] = []
    for entry in root.findall("a:entry", ns)[:max_results]:
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip().replace("\n", " ")
        link = ""
        id_text = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
        if id_text.startswith("http"):
            link = id_text
        if not link:
            for l in entry.findall("a:link", ns):
                href = (l.attrib.get("href") or "").strip()
                if href.startswith("http"):
                    link = href
                    break
        if not link:
            continue
        out.append({"source": "arxiv", "title": title, "url": link})
    return out


async def _fetch_page_snippet(url: str, timeout_sec: float = 12.0) -> str:
    if not url.startswith("http"):
        return ""
    try:
        import httpx
    except ImportError:
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (AetherCodeResearch/1.0)"}
    try:
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
    except Exception:
        return ""
    if resp.status_code >= 400:
        return ""
    return _clean_text_block(resp.text, max_chars=1200)


def _safe_packet_token(value: str, fallback: str = "task") -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed[:40] if collapsed else fallback


def _append_markdown_line(path: Path, header: str, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(header + "\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")


def _write_crosstalk_packet(payload: CrossTalkRequest) -> Dict[str, Any]:
    created_at = _utc_now_iso()
    now_utc = datetime.now(timezone.utc)
    stamp = now_utc.strftime("%Y%m%dT%H%M%S%fZ")
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_task = _safe_packet_token(payload.task_id, fallback="general")
    packet_id = f"cross-talk-{_safe_packet_token(payload.sender, fallback='agent')}-{safe_task}-{stamp}"
    session_id = payload.session_id.strip() or f"sess-{day}"
    codename = payload.codename.strip() or _safe_packet_token(payload.sender, fallback="agent")
    where = payload.where.strip()
    why = payload.why.strip()
    how = payload.how.strip()

    packet = {
        "packet_id": packet_id,
        "created_at": created_at,
        "session_id": session_id,
        "codename": codename,
        "sender": payload.sender,
        "recipient": payload.recipient,
        "intent": payload.intent,
        "status": payload.status,
        "repo": payload.repo,
        "branch": payload.branch,
        "task_id": payload.task_id,
        "summary": payload.summary,
        "proof": payload.proof,
        "next_action": payload.next_action,
        "risk": payload.risk,
        "where": where,
        "why": why,
        "how": how,
        "gates": {"governance_packet": True, "tests_requested": []},
    }

    out_dir = REPO_ROOT / "artifacts" / "agent_comm" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_path = out_dir / f"{packet_id}.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    _CROSSTALK_LANE.parent.mkdir(parents=True, exist_ok=True)
    with _CROSSTALK_LANE.open("a", encoding="utf-8") as lane:
        lane.write(json.dumps(packet) + "\n")

    where_part = f" | where={where}" if where else ""
    why_part = f" | why={why}" if why else ""
    how_part = f" | how={how}" if how else ""
    line = (
        f"- {created_at} [{session_id}] [{codename}] {payload.sender} -> {payload.recipient} | "
        f"{payload.intent} | {payload.status} | {payload.task_id} | {payload.summary}"
        f"{where_part}{why_part}{how_part} ({packet_path})"
    )
    _append_markdown_line(_OBS_NOTES_INBOX, "## AI-to-AI Packet Inbox", line)
    _append_markdown_line(_OBS_NOTES_CONTEXT, "## AI-to-AI Packet", line)
    _append_markdown_line(_OBS_AGENT_CODEX, "## AI-to-AI Packet", line)

    return {
        "packet": packet,
        "packet_path": packet_path,
        "line": line,
    }


def _read_crosstalk_latest(limit: int = 20) -> List[Dict[str, Any]]:
    if not _CROSSTALK_LANE.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with _CROSSTALK_LANE.open("r", encoding="utf-8") as lane:
        for raw in lane:
            line = raw.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"raw": line})
    return list(reversed(rows[-limit:]))


def _read_jsonl_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    rows.append(parsed)
                else:
                    rows.append({"raw": parsed})
            except json.JSONDecodeError:
                rows.append({"raw": line})
    return rows


def _crosstalk_pending_snapshot(limit: int = 200) -> Dict[str, Any]:
    rows = _read_jsonl_rows(_CROSSTALK_LANE)
    if not rows:
        return {
            "ok": True,
            "lane": str(_CROSSTALK_LANE),
            "total_records": 0,
            "total_tasks": 0,
            "pending_count": 0,
            "resolved_count": 0,
            "items": [],
        }

    latest_by_task: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        task_id = str(row.get("task_id", "")).strip()
        if not task_id:
            continue
        created = str(row.get("created_at", ""))
        previous = latest_by_task.get(task_id)
        if previous is None or created >= str(previous.get("created_at", "")):
            latest_by_task[task_id] = row

    terminal_statuses = {
        "done",
        "completed",
        "closed",
        "verified",
        "resolved",
        "retired",
        "stopped",
        "cancelled",
        "canceled",
        "failed",
        "error",
    }

    pending_items: List[Dict[str, Any]] = []
    resolved_count = 0
    for task_id, row in latest_by_task.items():
        status = str(row.get("status", "unknown")).strip().lower() or "unknown"
        item = {
            "task_id": task_id,
            "created_at": row.get("created_at", ""),
            "status": status,
            "intent": row.get("intent", ""),
            "sender": row.get("sender", ""),
            "recipient": row.get("recipient", ""),
            "summary": str(row.get("summary", ""))[:260],
            "next_action": str(row.get("next_action", ""))[:260],
            "risk": row.get("risk", ""),
            "packet_id": row.get("packet_id", ""),
            "session_id": row.get("session_id", ""),
            "codename": row.get("codename", ""),
        }
        if status in terminal_statuses:
            resolved_count += 1
            continue
        pending_items.append(item)

    pending_items.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    clipped = pending_items[: max(1, limit)]
    return {
        "ok": True,
        "lane": str(_CROSSTALK_LANE),
        "total_records": len(rows),
        "total_tasks": len(latest_by_task),
        "pending_count": len(pending_items),
        "resolved_count": resolved_count,
        "items": clipped,
    }


def _session_signons_snapshot(limit: int = 200) -> Dict[str, Any]:
    rows = _read_jsonl_rows(_SESSION_SIGNON_LANE)
    if not rows:
        return {
            "ok": True,
            "lane": str(_SESSION_SIGNON_LANE),
            "total_records": 0,
            "unique_sessions": 0,
            "counts": {"active": 0, "verified": 0, "retired": 0, "other": 0},
            "items": [],
        }

    latest_by_session: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        session_id = str(row.get("session_id", "")).strip()
        if not session_id:
            continue
        ts = str(row.get("timestamp_utc") or row.get("created_at") or "")
        prev = latest_by_session.get(session_id)
        prev_ts = str(prev.get("timestamp_utc") or prev.get("created_at") or "") if prev else ""
        if prev is None or ts >= prev_ts:
            latest_by_session[session_id] = row

    counts = {"active": 0, "verified": 0, "retired": 0, "other": 0}
    items: List[Dict[str, Any]] = []
    for session_id, row in latest_by_session.items():
        status = str(row.get("status", "other")).strip().lower() or "other"
        if status not in counts:
            counts["other"] += 1
        else:
            counts[status] += 1
        items.append(
            {
                "timestamp_utc": row.get("timestamp_utc", row.get("created_at", "")),
                "session_id": session_id,
                "agent": row.get("agent", ""),
                "callsign": row.get("callsign", ""),
                "status": status,
                "summary": str(row.get("summary", ""))[:260],
                "workspace_path": row.get("workspace_path", ""),
            }
        )

    items.sort(key=lambda x: str(x.get("timestamp_utc", "")), reverse=True)
    clipped = items[: max(1, limit)]
    return {
        "ok": True,
        "lane": str(_SESSION_SIGNON_LANE),
        "total_records": len(rows),
        "unique_sessions": len(latest_by_session),
        "counts": counts,
        "items": clipped,
    }


def _legacy_replit_local_profile(limit: int = 12) -> Dict[str, Any]:
    """Best-effort profile of the legacy Replit app code already mirrored locally."""
    roots = []
    seen: set[str] = set()
    for root in _LEGACY_REPLIT_LOCAL_REPO_PATHS.values():
        key = str(root.resolve()) if root.exists() else str(root)
        if key in seen:
            continue
        seen.add(key)
        roots.append(root)
    root = next((r for r in roots if r.exists()), None)
    if root is None:
        return {"ok": False, "source": "none", "count": 0, "files": [], "capabilities": {}}

    candidate_rel = [
        "README.md",
        "replit.md",
        "server/routes.ts",
        "server/replitAuth.ts",
        "server/services/providerAdapters.ts",
        "server/services/orchestrator.ts",
        "server/services/stripeClient.ts",
        "server/services/webhookHandlers.ts",
        "server/shopify/webhooks.ts",
        "shared/schema.ts",
    ]
    files: List[Dict[str, str]] = []
    for rel in candidate_rel:
        p = root / rel
        if p.exists():
            files.append({"path": rel, "full_path": str(p)})
    files = files[:limit]

    route_samples: List[str] = []
    routes_path = root / "server" / "routes.ts"
    if routes_path.exists():
        try:
            for raw in routes_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if "app.get(" in line or "app.post(" in line or "app.put(" in line or "app.delete(" in line:
                    route_samples.append(line[:180])
                if len(route_samples) >= 12:
                    break
        except Exception:
            pass

    paths = [f["path"] for f in files]
    path_text = " ".join(paths).lower()
    capabilities = {
        "replit_auth": any("replitauth" in x.lower() or "replitauth" in x.lower() for x in paths),
        "provider_router": any("provideradapters" in x.lower() for x in paths),
        "stripe": any("stripe" in x.lower() for x in paths),
        "webhooks": any("webhook" in x.lower() for x in paths),
        "shopify": any("shopify" in x.lower() for x in paths),
        "workflows": "workflow" in path_text,
        "orchestration": any("orchestrator" in x.lower() for x in paths),
    }
    return {
        "ok": True,
        "source": "local_intake",
        "root": str(root),
        "count": len(files),
        "files": files,
        "capabilities": capabilities,
        "route_samples": route_samples,
    }


def _touch_ai2ai(**kwargs: Any) -> None:
    _ai2ai_state.update(kwargs)
    _ai2ai_state["updated_at"] = _utc_now_iso()


def _ai2ai_available_tentacles(max_models: int = 4) -> List[str]:
    payload = _provider_status_payload()
    available = list(payload.get("available", []) or [])
    preferred = ["google_ai", "claude", "xai", "github_models", "huggingface", "ollama", "groq", "cerebras", "openrouter"]
    ordered = [x for x in preferred if x in available] + [x for x in available if x not in preferred]
    return ordered[: max(2, max_models)]


async def _run_ai2ai_cycle(prompt_seed: str = "", max_models: int = 4) -> Dict[str, Any]:
    profile = _legacy_replit_local_profile(limit=12)
    tentacles = _ai2ai_available_tentacles(max_models=max_models)
    if not tentacles:
        raise RuntimeError("No available tentacles/providers for AI-to-AI cycle")

    cap = profile.get("capabilities", {}) if isinstance(profile, dict) else {}
    cap_summary = ", ".join(k for k, v in cap.items() if v) or "none"
    file_lines = [str(x.get("path", "")) for x in profile.get("files", [])[:8]] if isinstance(profile, dict) else []
    route_lines = [str(x) for x in profile.get("route_samples", [])[:8]] if isinstance(profile, dict) else []

    base_prompt = (
        (prompt_seed.strip() + "\n\n" if prompt_seed.strip() else "")
        + "Legacy Replit app context:\n"
        + f"- Source: {profile.get('source', 'unknown')}\n"
        + f"- Capabilities: {cap_summary}\n"
        + f"- Files:\n  - " + ("\n  - ".join(file_lines) if file_lines else "(none)")
        + ("\n- Route samples:\n  - " + "\n  - ".join(route_lines) if route_lines else "")
        + "\n\nTask: generate one concrete implementation change for SCBE-AETHERMOORE, with file targets and risk notes."
    )

    outputs: List[Dict[str, Any]] = []
    baton = base_prompt
    tier = _resolve_tier(None)
    for idx, tentacle in enumerate(tentacles):
        req = ChatRequest(
            message=baton,
            mode="research",
            think_mode="harmonic",
            tentacle=tentacle,
            context=[{"role": "system", "content": "Autonomous AI-to-AI cycle. Be concrete and executable."}],
            max_tokens=1600,
        )
        result = await engine.chat(req, tier)
        outputs.append(
            {
                "tentacle": tentacle,
                "model": result.model,
                "response": result.response,
                "governance_score": result.governance_score,
            }
        )
        baton = (
            f"Previous model ({tentacle}) said:\n{result.response[:1400]}\n\n"
            "Refine it into clearer implementation steps and note any risks."
        )
        if idx >= max_models - 1:
            break

    summary_prompt = (
        "Synthesize this AI-to-AI cycle into:\n"
        "1) one action to execute now\n2) files to touch\n3) blockers\n4) fallback option\n\n"
        + "\n\n---\n\n".join(
            f"[{row['tentacle']} / {row['model']}]\n{str(row['response'])[:1200]}" for row in outputs
        )
    )
    leader = tentacles[0]
    summary_req = ChatRequest(
        message=summary_prompt,
        mode="research",
        think_mode="harmonic",
        tentacle=leader,
        context=[{"role": "system", "content": "Return concise execution-ready summary."}],
        max_tokens=1200,
    )
    summary_result = await engine.chat(summary_req, tier)
    summary_text = summary_result.response[:1800]

    packet = CrossTalkRequest(
        summary=f"AI2AI cycle complete via {', '.join(tentacles[:max_models])}. {summary_text[:220]}",
        recipient="agent.claude",
        sender="agent.codex",
        intent="autonomous-cycle",
        status="done",
        task_id="AI2AI-AUTONOMOUS-LOOP",
        next_action="Apply the top action from cycle summary.",
        risk="low",
        repo="SCBE-AETHERMOORE",
        branch=_repo_workspace.get("branch", "local"),
        proof=[f"{row['tentacle']}:{row['model']}" for row in outputs[:4]],
    )
    written = _write_crosstalk_packet(packet)
    return {
        "ok": True,
        "participants": tentacles[:max_models],
        "outputs": outputs,
        "summary": summary_text,
        "packet_id": written["packet"]["packet_id"],
        "packet_path": str(written["packet_path"]),
    }


def _ai2ai_review_gate(
    summary: str,
    outputs: List[Dict[str, Any]],
    min_avg_governance: float = 0.64,
    min_any_governance: float = 0.45,
    require_tests_hint: bool = True,
) -> Dict[str, Any]:
    """Deterministic production filter for debate outputs."""
    summary_text = (summary or "").strip()
    summary_lc = summary_text.lower()

    governance_scores: List[float] = []
    for row in outputs:
        raw = row.get("governance_score")
        if raw is None:
            continue
        try:
            governance_scores.append(max(0.0, min(1.0, float(raw))))
        except (TypeError, ValueError):
            continue

    avg_score = round(sum(governance_scores) / max(1, len(governance_scores)), 3) if governance_scores else 0.0
    min_score = round(min(governance_scores), 3) if governance_scores else 0.0
    max_score = round(max(governance_scores), 3) if governance_scores else 0.0

    risk_terms = (
        "force push",
        "force-push",
        "delete user data",
        "skip tests",
        "disable auth",
        "hardcode key",
        "api key",
        "secret key",
        "bypass review",
    )
    risky_hits = [term for term in risk_terms if term in summary_lc]

    test_terms = (
        "test",
        "tests",
        "pytest",
        "unit test",
        "integration test",
        "smoke test",
    )
    has_test_signal = any(term in summary_lc for term in test_terms)

    blockers: List[str] = []
    if len(outputs) < 2:
        blockers.append("insufficient_model_quorum")
    if not governance_scores:
        blockers.append("missing_governance_scores")
    if governance_scores and avg_score < float(min_avg_governance):
        blockers.append("average_governance_below_threshold")
    if governance_scores and min_score < float(min_any_governance):
        blockers.append("minimum_governance_below_threshold")
    if risky_hits:
        blockers.append("risky_language_detected")
    if require_tests_hint and not has_test_signal:
        blockers.append("missing_test_plan_signal")

    decision = "promote" if not blockers else "hold"
    route_to = "production" if decision == "promote" else "review_queue"
    recommended_labels = ["ai2ai-gate", "production-approved"] if decision == "promote" else ["ai2ai-gate", "needs-review"]
    confidence = round(
        max(
            0.05,
            min(
                0.99,
                (avg_score if governance_scores else 0.2) - (0.08 * len(blockers)) + (0.2 if decision == "promote" else 0.05),
            ),
        ),
        3,
    )

    return {
        "decision": decision,
        "route_to": route_to,
        "confidence": confidence,
        "thresholds": {
            "min_avg_governance": float(min_avg_governance),
            "min_any_governance": float(min_any_governance),
            "require_tests_hint": bool(require_tests_hint),
        },
        "metrics": {
            "participants": len(outputs),
            "governance_count": len(governance_scores),
            "governance_avg": avg_score,
            "governance_min": min_score,
            "governance_max": max_score,
            "has_test_signal": has_test_signal,
        },
        "blockers": blockers,
        "risky_hits": risky_hits,
        "recommended_labels": recommended_labels,
        "reviewed_at": _utc_now_iso(),
    }


async def _ai2ai_loop() -> None:
    _touch_ai2ai(status="running", last_error="")
    try:
        # Yield once so start endpoint can return before first heavy model cycle.
        await asyncio.sleep(0.25)
        while _ai2ai_state.get("enabled", False):
            cycle = await _run_ai2ai_cycle(
                prompt_seed=str(_ai2ai_state.get("seed_prompt", "")),
                max_models=int(_ai2ai_state.get("max_models", 4)),
            )
            _touch_ai2ai(
                cycles=int(_ai2ai_state.get("cycles", 0)) + 1,
                last_summary=str(cycle.get("summary", ""))[:600],
                status="running",
            )
            await asyncio.sleep(max(45, int(_ai2ai_state.get("interval_seconds", 180))))
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _touch_ai2ai(status="error", last_error=str(exc)[:300])
    finally:
        if not _ai2ai_state.get("enabled", False):
            _touch_ai2ai(status="stopped")


def _ensure_autopilot_day() -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    if _autopilot_state.get("revenue_day") != today:
        _autopilot_state["revenue_day"] = today
        _autopilot_state["estimated_revenue_today_usd"] = 0.0


def _touch_autopilot(**kwargs: Any) -> None:
    _autopilot_state.update(kwargs)
    _autopilot_state["updated_at"] = _utc_now_iso()


def _append_run(run: Dict[str, Any]) -> Dict[str, Any]:
    _run_history.append(run)
    if len(_run_history) > _max_run_history:
        del _run_history[0 : len(_run_history) - _max_run_history]
    return run


def _new_run(goal: str, action: str, source: str, steps_total: int = 3) -> Dict[str, Any]:
    now = int(time.time())
    return {
        "id": uuid.uuid4().hex[:10],
        "goal": goal,
        "action": action,
        "source": source,
        "status": "running",
        "steps_total": steps_total,
        "steps_completed": 0,
        "plan_method": "browser-autopilot" if source == "autopilot" else "manual-action",
        "plan_confidence": 0.86 if source == "autopilot" else 0.72,
        "error": "",
        "created_at": now,
        "updated_at": now,
    }


def _firebase_status_payload() -> Dict[str, Any]:
    project_id = (
        os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCP_PROJECT_ID")
        or ""
    )
    storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET", "")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    creds_exists = bool(creds_path and Path(creds_path).exists())
    configured = bool(project_id)
    connected = bool(configured and (_FIREBASE or creds_exists))
    return {
        "ok": True,
        "configured": configured,
        "connected": connected,
        "sdk_available": _FIREBASE,
        "project_id": project_id,
        "storage_bucket": storage_bucket,
        "credentials_path_set": bool(creds_path),
        "credentials_file_exists": creds_exists,
        "tips": (
            []
            if connected
            else [
                "Set FIREBASE_PROJECT_ID (or GOOGLE_CLOUD_PROJECT).",
                "Set GOOGLE_APPLICATION_CREDENTIALS to a valid service account JSON for admin operations.",
            ]
        ),
    }


def _think_mode_profile(mode: str) -> Dict[str, Any]:
    raw = (mode or "standard").strip().lower()
    if raw == "fast":
        return {
            "name": "fast",
            "temperature": 0.35,
            "guidance": "Respond quickly with direct actionable output. Prefer short concrete steps.",
        }
    if raw == "deep":
        return {
            "name": "deep",
            "temperature": 0.55,
            "guidance": "Reason deeply, include tradeoffs and hidden failure modes before final recommendation.",
        }
    if raw == "research":
        return {
            "name": "research",
            "temperature": 0.45,
            "guidance": "Prioritize evidence quality, cite assumptions, and separate known facts from inference.",
        }
    if raw == "harmonic":
        return {
            "name": "harmonic",
            "temperature": 0.65,
            "guidance": (
                "Allow minor ambiguity and self-corrective flow. If one detail is uncertain, preserve momentum "
                "by proposing robust alternatives that still converge."
            ),
        }
    return {
        "name": "standard",
        "temperature": 0.7,
        "guidance": "Be practical and clear.",
    }


def _load_spin_context(limit: int = 6) -> List[str]:
    global _spin_context_loaded, _spin_context_cache
    if _spin_context_loaded:
        return _spin_context_cache

    candidates = [
        os.getenv("AETHERCODE_SPIN_DATA_PATH", "").strip(),
        str(REPO_ROOT / "training-data" / "funnel" / "sft_pairs.jsonl"),
        str(REPO_ROOT / "training-data" / "sft_spiralverse.jsonl"),
    ]
    snippets: List[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if len(snippets) >= limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    prompt = str(obj.get("input") or obj.get("instruction") or "").strip()
                    output = str(obj.get("output") or "").strip()
                    if not prompt and not output:
                        continue
                    if output:
                        snippets.append(f"{prompt[:140]} -> {output[:240]}")
                    else:
                        snippets.append(prompt[:200])
            if snippets:
                break
        except Exception:
            continue

    _spin_context_cache = snippets
    _spin_context_loaded = True
    return _spin_context_cache


def _roundpit_bitstream(text: str) -> str:
    payload = text or ""
    checks = [
        "```" in payload,  # code
        any(x in payload.lower() for x in ["risk", "tradeoff", "failure"]),
        any(x in payload.lower() for x in ["step", "1.", "2.", "- "]),
        any(x in payload.lower() for x in ["revenue", "sell", "customer", "market"]),
        len(payload) > 700,
        "?" in payload,
        any(x in payload.lower() for x in ["therefore", "because", "so that"]),
        any(x in payload.lower() for x in ["assume", "unknown", "uncertain"]),
    ]
    return "".join("1" if flag else "0" for flag in checks)


def _extract_keywords(text: str, top_n: int = 6) -> List[str]:
    words: Dict[str, int] = {}
    for token in (text or "").lower().replace("\n", " ").split():
        clean = "".join(ch for ch in token if ch.isalnum() or ch in ("-", "_"))
        if len(clean) < 4:
            continue
        if clean in {"that", "this", "with", "from", "into", "have", "will", "your", "they"}:
            continue
        words[clean] = words.get(clean, 0) + 1
    ranked = sorted(words.items(), key=lambda kv: kv[1], reverse=True)
    return [k for k, _ in ranked[:top_n]]


def _harmonic_reflection(request: str, model_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined = "\n".join(str(x.get("response", "")) for x in model_outputs)
    concepts = _extract_keywords(combined, top_n=8)
    bitstreams = {str(x.get("tentacle", "unknown")): _roundpit_bitstream(str(x.get("response", ""))) for x in model_outputs}
    stability = round(
        sum(1 for x in model_outputs if str(x.get("status", "")) == "ok") / max(1, len(model_outputs)),
        3,
    )
    tonal_shift = round(min(1.0, len(set(bitstreams.values())) / max(1, len(model_outputs))), 3)
    return {
        "query": request[:240],
        "concepts": concepts,
        "bitstreams": bitstreams,
        "stability": stability,
        "tonal_shift": tonal_shift,
        "auto_resolve_hint": (
            "If one model drifts, keep consensus concepts fixed and re-run only the diverged branch."
            if model_outputs
            else "No outputs to resolve."
        ),
    }


async def _execute_dashboard_action(name: str, desc: str, source: str) -> Dict[str, Any]:
    run = _append_run(_new_run(goal=desc, action=name, source=source, steps_total=3))
    steps = ("plan", "dispatch", "verify")
    try:
        for idx, step in enumerate(steps, start=1):
            await asyncio.sleep(0.08 if source == "autopilot" else 0.04)
            run["steps_completed"] = idx
            run["last_step"] = step
            run["updated_at"] = int(time.time())

        _ensure_autopilot_day()
        delta = float(_action_revenue_usd.get(name, 0.0))
        _autopilot_state["estimated_revenue_today_usd"] = round(
            float(_autopilot_state.get("estimated_revenue_today_usd", 0.0)) + delta, 2
        )
        run["estimated_revenue_delta_usd"] = delta
        run["estimated_revenue_today_usd"] = _autopilot_state["estimated_revenue_today_usd"]
        run["status"] = "succeeded"
        run["updated_at"] = int(time.time())
        _touch_autopilot(last_action=name, status="running" if source == "autopilot" else _autopilot_state.get("status", "idle"))
        return run
    except Exception as exc:
        run["status"] = "failed"
        run["error"] = str(exc)
        run["updated_at"] = int(time.time())
        _touch_autopilot(status="error", last_error=str(exc))
        return run


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _coerce_str_list(value: Any, default: List[str]) -> List[str]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item) for item in value]
    else:
        items = [str(value)]
    cleaned = [item.strip() for item in items if str(item).strip()]
    return cleaned or list(default)


def _ops_backup_defaults() -> Dict[str, Any]:
    sources = list(_ops_backup_builtin_source)
    destinations = list(_ops_backup_builtin_destinations)
    source_kind = "builtin"

    if _ops_backup_defaults_path.exists():
        try:
            loaded = json.loads(_ops_backup_defaults_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg_sources = _coerce_str_list(loaded.get("source"), default=[])
                cfg_dests = _coerce_str_list(loaded.get("dest"), default=[])
                if cfg_sources:
                    sources = cfg_sources
                if cfg_dests:
                    destinations = cfg_dests
                if cfg_sources or cfg_dests:
                    source_kind = "config"
        except Exception:
            pass

    env_source = str(os.getenv("SCBE_BACKUP_SOURCE", "")).strip()
    env_dests = str(os.getenv("SCBE_BACKUP_DESTS", "")).strip()
    env_repo = str(os.getenv("SCBE_BACKUP_REPO_DEST", "")).strip()
    env_cloud = str(os.getenv("SCBE_BACKUP_CLOUD_DEST", "")).strip()

    if env_source:
        sources = [env_source]
        source_kind = "env"

    parsed_env_dests = [x.strip() for x in re.split(r"[;,]", env_dests) if x.strip()]
    repo_cloud_dests = [x for x in [env_repo, env_cloud] if x]
    if parsed_env_dests:
        destinations = parsed_env_dests
        source_kind = "env"
    elif repo_cloud_dests:
        destinations = repo_cloud_dests
        source_kind = "env_repo_cloud"

    return {
        "source": sources or list(_ops_backup_builtin_source),
        "dest": destinations or list(_ops_backup_builtin_destinations),
        "source_kind": source_kind,
    }


def _extract_json_object(stdout_text: str) -> Optional[Dict[str, Any]]:
    text = (stdout_text or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    for line in reversed([ln.strip() for ln in text.splitlines() if ln.strip()]):
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    return None


async def _run_local_python_script(
    script_relpath: str,
    *,
    args: List[str],
    timeout_sec: float = 180.0,
) -> Dict[str, Any]:
    script_path = REPO_ROOT / script_relpath
    if not script_path.exists():
        return {
            "ok": False,
            "error": f"Script not found: {script_path}",
            "script": str(script_path),
            "returncode": None,
            "stdout": "",
            "stderr": "",
        }

    python_exec = sys.executable or "python"
    try:
        proc = await asyncio.create_subprocess_exec(
            python_exec,
            str(script_path),
            *args,
            cwd=str(REPO_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except PermissionError:
        prev_argv = sys.argv[:]
        stdout_stream = io.StringIO()
        stderr_stream = io.StringIO()
        exit_code = 0
        try:
            sys.argv = [str(script_path), *args]
            with contextlib.redirect_stdout(stdout_stream), contextlib.redirect_stderr(stderr_stream):
                try:
                    runpy.run_path(str(script_path), run_name="__main__")
                except SystemExit as exc:
                    if isinstance(exc.code, int):
                        exit_code = int(exc.code)
                    elif exc.code is None:
                        exit_code = 0
                    else:
                        exit_code = 1
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "script": str(script_path),
                "returncode": None,
                "stdout": stdout_stream.getvalue(),
                "stderr": stderr_stream.getvalue(),
                "json": None,
                "runner": "inprocess",
            }
        finally:
            sys.argv = prev_argv

        inline_stdout = stdout_stream.getvalue()
        inline_stderr = stderr_stream.getvalue()
        return {
            "ok": exit_code == 0,
            "script": str(script_path),
            "returncode": exit_code,
            "stdout": inline_stdout,
            "stderr": inline_stderr,
            "json": _extract_json_object(inline_stdout),
            "runner": "inprocess",
        }
    try:
        raw_stdout, raw_stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        proc.kill()
        raw_stdout, raw_stderr = await proc.communicate()
        stdout = raw_stdout.decode("utf-8", errors="replace")
        stderr = raw_stderr.decode("utf-8", errors="replace")
        return {
            "ok": False,
            "error": f"Timed out after {timeout_sec:.1f}s",
            "script": str(script_path),
            "returncode": None,
            "stdout": stdout,
            "stderr": stderr,
            "json": _extract_json_object(stdout),
        }

    stdout = raw_stdout.decode("utf-8", errors="replace")
    stderr = raw_stderr.decode("utf-8", errors="replace")
    return {
        "ok": proc.returncode == 0,
        "script": str(script_path),
        "returncode": int(proc.returncode),
        "stdout": stdout,
        "stderr": stderr,
        "json": _extract_json_object(stdout),
    }


async def _autopilot_loop() -> None:
    _touch_autopilot(status="running", last_error="")
    action_order = ("post_content", "list_products", "run_research", "push_training")
    try:
        while _autopilot_state.get("enabled", False):
            _ensure_autopilot_day()
            target = float(_autopilot_state.get("target_usd", 1.0))
            current = float(_autopilot_state.get("estimated_revenue_today_usd", 0.0))
            if current >= target:
                _touch_autopilot(status="target_hit")
                await asyncio.sleep(12)
                continue

            for action_name in action_order:
                if not _autopilot_state.get("enabled", False):
                    break
                desc = _dashboard_actions.get(action_name, action_name)
                await _execute_dashboard_action(action_name, desc, source="autopilot")
                await asyncio.sleep(1.2)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _touch_autopilot(status="error", last_error=str(exc))
    finally:
        if not _autopilot_state.get("enabled", False):
            _touch_autopilot(status="stopped")

# ---------------------------------------------------------------------------
#  Core Engine
# ---------------------------------------------------------------------------

class AetherCodeEngine:
    """Unified engine that orchestrates all subsystems."""

    def __init__(self) -> None:
        self.octo: Optional[Any] = None
        self.scorer: Optional[ContextScorer] = None
        self.registry: Optional[Any] = None
        self._init_subsystems()

    def _init_subsystems(self) -> None:
        if _OCTO_AVAILABLE:
            try:
                self.octo = OctoArmor()
            except Exception:
                self.octo = None

        if _SCORER_AVAILABLE:
            self.scorer = ContextScorer()

        if _AAOE_AVAILABLE:
            self.registry = AgentRegistry()

    async def chat(self, req: ChatRequest, tier: BillingTier) -> ChatResponse:
        """Route a chat/code/research request through OctoArmor."""
        start = time.time()
        session_id = req.session_id or uuid.uuid4().hex[:12]
        tier_cfg = TIER_CONFIG[tier]

        # Build system prompt based on mode
        system_prompt = self._build_system_prompt(req.mode, req.language, tier)

        # Build messages — include conversation history so the AI has memory
        messages = []
        if req.context:
            messages.extend(req.context)
        # Inject session history so AI remembers previous turns
        if session_id in _sessions and _sessions[session_id]["conversation"]:
            messages.extend(_sessions[session_id]["conversation"])
        messages.append({"role": "user", "content": req.message})

        # Route through OctoArmor or fallback
        tentacle_name = "internal"
        model_name = "aethercode-router"
        response_text = ""
        tokens = 0

        if self.octo:
            try:
                result = await self._route_to_tentacle(
                    messages, system_prompt, req, tier_cfg
                )
                tentacle_name = result.get("tentacle", "unknown")
                model_name = result.get("model", "unknown")
                response_text = result.get("response", "")
                tokens = result.get("tokens", 0)
            except Exception as e:
                response_text = f"[Routing error: {e}. Falling back to local.]"
                tentacle_name = "fallback"
        else:
            # No OctoArmor — provide structured fallback
            response_text = self._local_fallback(req)

        # Governance scan
        gov_score = self._governance_scan(response_text)

        latency = (time.time() - start) * 1000

        # Generate training pair
        pair_id = self._record_training_pair(req, response_text, gov_score, session_id)

        # Update session
        self._update_session(session_id, req, response_text, tier)

        return ChatResponse(
            id=uuid.uuid4().hex[:12],
            status="ok",
            mode=req.mode,
            tentacle=tentacle_name,
            model=model_name,
            response=response_text,
            latency_ms=round(latency, 2),
            governance_score=round(gov_score, 4),
            tokens_used=tokens,
            session_id=session_id,
            training_pair_id=pair_id,
        )

    async def browse(self, req: BrowseRequest, tier: BillingTier) -> BrowseResponse:
        """Parallel browsing via OctoTree."""
        start = time.time()
        tier_cfg = TIER_CONFIG[tier]
        max_depth = min(req.depth, tier_cfg["octotree_depth"])

        results = []
        workers_used = 0

        if _OCTOTREE_AVAILABLE:
            config = AcceleratorConfig(max_depth=max_depth)
            tree = OctoTree(config=config)
            for url in req.urls:
                baton = Baton(url=url, task=req.task)
                tree.submit(baton)
            raw = await tree.run()
            results = [{"url": r.url, "status": r.status, "data": r.data} for r in raw]
            workers_used = min(6 ** max_depth, len(req.urls))
        else:
            # Sequential fallback
            for url in req.urls:
                results.append({"url": url, "status": "skipped", "data": None})

        latency = (time.time() - start) * 1000
        return BrowseResponse(
            id=uuid.uuid4().hex[:12],
            urls_processed=len(results),
            results=results,
            latency_ms=round(latency, 2),
            octotree_depth=max_depth,
            workers_used=workers_used,
        )

    def score_reference(self, req: ScoreRequest) -> Dict[str, Any]:
        """Score a reference through the 7D context scorer."""
        if not self.scorer:
            return {"error": "Context scorer not available"}

        depth_map = {
            "principles": DepthLevel.PRINCIPLES,
            "facts": DepthLevel.FACTS,
            "thoughts": DepthLevel.THOUGHTS,
            "emotions": DepthLevel.EMOTIONS,
            "theories": DepthLevel.THEORIES,
            "implications": DepthLevel.IMPLICATIONS,
        }
        src_map = {
            "peer_reviewed": SourceType.PEER_REVIEWED,
            "official": SourceType.OFFICIAL,
            "community": SourceType.COMMUNITY,
            "personal": SourceType.PERSONAL,
            "ai_generated": SourceType.AI_GENERATED,
        }

        ref = ContextReference(
            content=req.content,
            url=req.url,
            author_era=req.author_era,
            target_audience=req.target_audience,
            depth_levels=[depth_map.get(d, DepthLevel.FACTS) for d in req.depth_levels],
            source_type=src_map.get(req.source_type, SourceType.COMMUNITY),
        )
        score = self.scorer.score(ref)
        return score.to_dict()

    def _build_system_prompt(self, mode: str, language: Optional[str], tier: BillingTier) -> str:
        workspace = _workspace_snapshot()
        base = (
            "You are AetherCode — a multi-model AI assistant running inside the SCBE-AETHERMOORE platform.\n"
            "You are one of many AI tentacles (Groq, Cerebras, Google AI, Claude, xAI, OpenRouter, GitHub Models, Ollama).\n\n"
            "OWNER: Issac Davis (issdandavis)\n"
            "GITHUB: https://github.com/issdandavis\n"
            "PRIMARY REPO: SCBE-AETHERMOORE — AI safety framework with 14-layer governance pipeline\n"
            "HUGGING FACE: https://huggingface.co/issdandavis\n\n"
            "RULES — follow these or get replaced:\n"
            "1. ACT, don't ask. If the user says 'browse my github', GO browse it and report what you find.\n"
            "2. NEVER ask clarifying questions unless genuinely ambiguous. Assume context from the conversation.\n"
            "3. When told to look at code, look at the SCBE-AETHERMOORE codebase. That's where you live.\n"
            "4. Be concise. No filler, no disclaimers, no 'great question!' nonsense.\n"
            "5. If you can't do something, say so in one sentence and suggest what you CAN do instead.\n"
            "6. You have access to all modes: chat, code, research, browse. Use them.\n"
            "7. The user is building a money-making AI system. Help them ship, not philosophize.\n\n"
            "KEY CODEBASE STRUCTURE:\n"
            "- src/aethercode/ — THIS app (gateway, arena, PWA)\n"
            "- src/fleet/octo_armor.py — 20-tentacle multi-LLM router\n"
            "- src/geoseed/ — GeoSeed neural network (6 sacred tongue spheres)\n"
            "- src/aaoe/ — AetherNet social platform for AIs\n"
            "- src/browser/ — HydraHand browser automation\n"
            "- workflows/n8n/ — n8n workflow bridge\n"
            "- training-data/ — SFT/DPO training corpus\n"
            "- aetherbrowse/ — Electron browser shell (Kerrigan)\n\n"
            "ACTIVE SHARED WORKSPACE:\n"
            f"- Repo: {workspace['ref']}\n"
            f"- Mode: {workspace['mode']}\n"
            "- All Arena seats collaborate against this repo target unless explicitly changed.\n"
            "- Generate git actions, branch plans, and issue plans for this exact workspace.\n\n"
        )
        if mode == "code":
            lang = language or "the requested language"
            base += (
                f"MODE: Code Generation\n"
                f"Language: {lang}\n"
                f"Write clean, working code. No filler comments. Output code blocks with language tags.\n"
            )
        elif mode == "research":
            base += (
                "MODE: Research\n"
                "Search broadly, cite sources, provide executive summary + findings. No padding.\n"
            )
        elif mode == "browse":
            base += (
                "MODE: Web Browsing\n"
                "Extract data from web pages. Summarize what you find. Don't ask what to look for — look.\n"
            )
        return base

    async def _route_to_tentacle(
        self, messages: List[Dict], system_prompt: str,
        req: ChatRequest, tier_cfg: Dict
    ) -> Dict[str, Any]:
        """Route request through OctoArmor tentacle (async reach API)."""
        if not self.octo:
            return {"response": self._local_fallback(req), "tentacle": "none", "model": "none"}

        try:
            # OctoArmor.reach() is async — pass prompt + context
            # Resolve preferred tentacle from request
            _pref_tentacle = None
            if req.tentacle:
                try:
                    from fleet.octo_armor import Tentacle as _T
                    _pref_tentacle = _T(req.tentacle)
                except (ValueError, ImportError):
                    pass

            result = await asyncio.wait_for(
                self.octo.reach(
                    prompt=req.message,
                    task_type=req.mode if req.mode != "chat" else None,
                    preferred_tentacle=_pref_tentacle,
                    model=req.model,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    context=system_prompt,
                ),
                timeout=60.0,
            )
            if result.get("status") == "ok":
                return {
                    "response": result.get("response", ""),
                    "tentacle": result.get("tentacle", "unknown"),
                    "model": result.get("model", "unknown"),
                    "tokens": len(result.get("response", "")) // 4,
                }
            else:
                # OctoArmor returned error — show it
                return {
                    "response": f"[OctoArmor: {result.get('error', 'Unknown error')}]",
                    "tentacle": str(result.get("tentacle", "none")),
                    "model": "error",
                }
        except asyncio.TimeoutError:
            return {"response": "[Request timed out after 60s]", "tentacle": "timeout", "model": "timeout"}
        except Exception as e:
            return {"response": f"[Tentacle error: {e}]", "tentacle": "error", "model": "error"}

    def _select_tentacle(self, mode: str, tier_cfg: Dict) -> str:
        """Select best tentacle for the given mode and tier."""
        # Mode-based preferences (Sacred Tongue mapping)
        mode_prefs = {
            "code": ["cerebras", "groq", "claude"],       # Fast code generation
            "research": ["google_ai", "claude", "openrouter"],  # Deep reasoning
            "chat": ["groq", "cerebras", "xai"],           # Low latency
            "browse": ["google_ai", "huggingface", "ollama"],  # Extraction
        }
        prefs = mode_prefs.get(mode, mode_prefs["chat"])
        # Return first available within tier tentacle limit
        return prefs[0] if prefs else "groq"

    def _local_fallback(self, req: ChatRequest) -> str:
        """Structured response when no LLM tentacles are available."""
        return (
            f"[AetherCode local mode — no LLM tentacles connected]\n\n"
            f"**Mode**: {req.mode}\n"
            f"**Query**: {req.message[:200]}\n\n"
            f"To enable full AI responses, configure at least one provider in .env:\n"
            f"- GROQ_API_KEY (fastest, free tier)\n"
            f"- CEREBRAS_API_KEY (fast inference)\n"
            f"- GOOGLE_AI_API_KEY (Gemini)\n"
            f"- ANTHROPIC_API_KEY (Claude)\n"
        )

    def _governance_scan(self, content: str) -> float:
        """L13 governance scan — score content 0.0 to 1.0."""
        if not content:
            return 0.5
        score = 0.6
        # Length factor: longer = more structured = higher base
        length = len(content)
        if length > 100:
            score += min(length / 5000, 0.2)
        # Structure bonus: has code blocks, lists, headers
        if "```" in content:
            score += 0.05
        if "\n- " in content or "\n* " in content:
            score += 0.03
        if "\n#" in content:
            score += 0.02
        # Penalty: suspicious patterns
        suspicious = ["ignore previous", "system prompt", "jailbreak", "bypass", "hack"]
        for s in suspicious:
            if s.lower() in content.lower():
                score -= 0.3
        return max(0.0, min(1.0, score))

    def _record_training_pair(
        self, req: ChatRequest, response: str, gov_score: float, session_id: str
    ) -> Optional[str]:
        """Record SFT training pair from interaction."""
        pair_id = uuid.uuid4().hex[:10]
        pair = {
            "id": pair_id,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "type": f"aethercode_{req.mode}",
            "input": {
                "message": req.message,
                "mode": req.mode,
                "language": req.language,
            },
            "output": {
                "response": response[:2000],
                "governance_score": gov_score,
            },
            "metadata": {
                "session_id": session_id,
                "product": "aethercode",
                "version": VERSION,
                "workspace_repo": f"{_repo_workspace.get('owner', '')}/{_repo_workspace.get('repo', '')}",
                "workspace_branch": _repo_workspace.get("branch", "main"),
            },
        }
        _training_pairs.append(pair)
        return pair_id

    def _update_session(
        self, session_id: str, req: ChatRequest, response: str, tier: BillingTier
    ) -> None:
        """Update or create session state."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if session_id not in _sessions:
            _sessions[session_id] = {
                "session_id": session_id,
                "tier": tier.value,
                "messages": 0,
                "created_at": now,
                "conversation": [],
            }
        sess = _sessions[session_id]
        sess["messages"] += 1
        sess["last_active"] = now
        sess["conversation"].append({"role": "user", "content": req.message})
        sess["conversation"].append({"role": "assistant", "content": response[:1000]})
        # Keep last 20 turns
        if len(sess["conversation"]) > 40:
            sess["conversation"] = sess["conversation"][-40:]


# ---------------------------------------------------------------------------
#  App + Engine
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AetherCode",
    description="Governed Multi-Model AI Development Platform",
    version=VERSION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
if AETHERCODE_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=AETHERCODE_STATIC_DIR), name="aethercode-static")

engine = AetherCodeEngine()


@app.on_event("startup")
async def _start_training_timer():
    """Auto-flush training pairs every 30 minutes."""
    async def _flush_loop():
        while True:
            await asyncio.sleep(1800)
            if _training_pairs:
                try:
                    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    path = TRAINING_DIR / f"aethercode_sft_{ts}.jsonl"
                    with path.open("w", encoding="utf-8") as f:
                        for pair in _training_pairs:
                            f.write(json.dumps(pair, ensure_ascii=True) + "\n")
                    _training_pairs.clear()
                except Exception:
                    pass
    asyncio.create_task(_flush_loop())


@app.on_event("shutdown")
async def _stop_background_tasks():
    """Cancel long-lived background loops on process shutdown."""
    global _autopilot_task, _ai2ai_task
    for task in (_autopilot_task, _ai2ai_task):
        if task and not task.done():
            task.cancel()
    _autopilot_task = None
    _ai2ai_task = None


# ---------------------------------------------------------------------------
#  Tier resolution helper
# ---------------------------------------------------------------------------

def _resolve_tier(api_key: Optional[str] = None) -> BillingTier:
    """Everything is free. All features unlocked for everyone."""
    return BillingTier.FREE


def _check_rate_limit(user_id: str, tier: BillingTier) -> bool:
    """Check if user has messages remaining today."""
    limit = TIER_CONFIG[tier]["messages_per_day"]
    if limit < 0:
        return True  # unlimited
    used = _daily_usage.get(user_id, 0)
    return used < limit


def _provider_status_payload() -> Dict[str, Any]:
    """Provider/tentacle availability with key requirements (never key values)."""
    if not _OCTO_AVAILABLE or engine.octo is None:
        return {
            "enabled": False,
            "available_count": 0,
            "available": [],
            "bootstrap_sources": dict(_PROVIDER_BOOTSTRAP_SOURCES),
            "tentacles": [],
        }

    status_rows = engine.octo.tentacle_status()
    required_env_map = {
        tentacle.value: cfg.api_key_env
        for tentacle, cfg in TENTACLE_REGISTRY.items()
    }
    normalized: List[Dict[str, Any]] = []
    available: List[str] = []

    for row in status_rows:
        item = dict(row)
        tentacle_name = str(item.get("tentacle", "")).strip()
        required_env = required_env_map.get(tentacle_name, "")
        item["required_env"] = required_env
        item["key_loaded_from"] = _PROVIDER_BOOTSTRAP_SOURCES.get(required_env, "")
        normalized.append(item)
        if bool(item.get("available")):
            available.append(tentacle_name)

    return {
        "enabled": True,
        "available_count": len(available),
        "available": available,
        "bootstrap_sources": dict(_PROVIDER_BOOTSTRAP_SOURCES),
        "tentacles": normalized,
    }


# ---------------------------------------------------------------------------
#  Routes: Core Chat
# ---------------------------------------------------------------------------

@app.post("/v1/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    api_key: Optional[str] = Query(None, alias="key"),
):
    """Universal chat endpoint — routes by mode (chat/code/research/browse)."""
    tier = _resolve_tier(api_key)
    tier_cfg = TIER_CONFIG[tier]

    # All modes unlocked — AetherCode is free forever
    user_id = api_key or "anonymous"
    _daily_usage[user_id] = _daily_usage.get(user_id, 0) + 1
    return await engine.chat(req, tier)


@app.post("/v1/browse", response_model=BrowseResponse)
async def browse_endpoint(
    req: BrowseRequest,
    api_key: Optional[str] = Query(None, alias="key"),
):
    """Parallel web browsing via OctoTree."""
    tier = _resolve_tier(api_key)
    return await engine.browse(req, tier)


@app.post("/v1/score")
async def score_endpoint(req: ScoreRequest):
    """Score a reference through the 7D context scorer."""
    return engine.score_reference(req)


# ---------------------------------------------------------------------------
#  Routes: Sessions
# ---------------------------------------------------------------------------

@app.get("/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session state and conversation history."""
    sess = _sessions.get(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return sess


@app.get("/v1/sessions")
async def list_sessions():
    """List active sessions."""
    return {
        "count": len(_sessions),
        "sessions": [
            {"id": s["session_id"], "messages": s["messages"], "tier": s["tier"]}
            for s in _sessions.values()
        ],
    }


# ---------------------------------------------------------------------------
#  Routes: Training Data
# ---------------------------------------------------------------------------

@app.get("/v1/training/stats")
async def training_stats():
    """Training data statistics."""
    by_mode: Dict[str, int] = {}
    for p in _training_pairs:
        t = p.get("type", "unknown")
        by_mode[t] = by_mode.get(t, 0) + 1
    return {
        "total_pairs": len(_training_pairs),
        "by_mode": by_mode,
        "storage_dir": str(TRAINING_DIR),
    }


@app.post("/v1/training/flush")
async def flush_training():
    """Flush training pairs to JSONL file."""
    if not _training_pairs:
        return {"flushed": 0}
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = TRAINING_DIR / f"aethercode_sft_{ts}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for pair in _training_pairs:
            f.write(json.dumps(pair, ensure_ascii=True) + "\n")
    count = len(_training_pairs)
    _training_pairs.clear()
    return {"flushed": count, "file": str(path)}


@app.post("/v1/training/push")
async def push_training():
    """Flush training pairs to JSONL then push to HuggingFace."""
    flush_result = await flush_training()
    flushed = flush_result.get("flushed", 0)
    if flushed == 0:
        return {"status": "nothing_to_push", "flushed": 0}
    try:
        from huggingface_hub import HfApi  # type: ignore[import-untyped]
        token = os.environ.get("HF_TOKEN")
        if not token:
            return {"status": "flushed_only", "flushed": flushed, "error": "HF_TOKEN not set"}
        api = HfApi(token=token)
        filepath = flush_result.get("file")
        if filepath:
            api.upload_file(
                path_or_fileobj=filepath,
                path_in_repo=f"aethercode/{Path(filepath).name}",
                repo_id="issdandavis/scbe-aethermoore-training-data",
                repo_type="dataset",
            )
            return {"status": "pushed", "flushed": flushed, "repo": "issdandavis/scbe-aethermoore-training-data"}
    except ImportError:
        return {"status": "flushed_only", "flushed": flushed, "error": "huggingface_hub not installed"}
    except Exception as e:
        return {"status": "flushed_only", "flushed": flushed, "error": str(e)[:300]}
    return {"status": "flushed_only", "flushed": flushed}


# ---------------------------------------------------------------------------
#  Routes: Claude Batch Processing (50% cheaper)
# ---------------------------------------------------------------------------

class BatchRequest(BaseModel):
    """Batch of prompts to process via Anthropic Message Batches API."""
    prompts: List[Dict[str, str]]  # [{"id": "task-1", "message": "..."}]
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 1024
    system: Optional[str] = None


@app.post("/v1/batch/submit")
async def submit_batch(req: BatchRequest):
    """Submit a batch of prompts to Claude at 50% discount."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(400, "ANTHROPIC_API_KEY not set in .env")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        requests = []
        for item in req.prompts:
            msgs = [{"role": "user", "content": item.get("message", "")}]
            params: Dict[str, Any] = {
                "model": req.model,
                "max_tokens": req.max_tokens,
                "messages": msgs,
            }
            if req.system:
                params["system"] = req.system
            requests.append({
                "custom_id": item.get("id", uuid.uuid4().hex[:10]),
                "params": params,
            })
        batch = client.messages.batches.create(requests=requests)
        return {
            "status": "submitted",
            "batch_id": batch.id,
            "count": len(requests),
            "model": req.model,
            "processing_status": batch.processing_status,
        }
    except ImportError:
        raise HTTPException(500, "anthropic package not installed. Run: pip install anthropic")
    except Exception as e:
        raise HTTPException(500, str(e)[:500])


@app.get("/v1/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Check status of a Claude batch job."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(400, "ANTHROPIC_API_KEY not set")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        batch = client.messages.batches.retrieve(batch_id)
        result: Dict[str, Any] = {
            "batch_id": batch.id,
            "processing_status": batch.processing_status,
            "request_counts": {
                "processing": batch.request_counts.processing,
                "succeeded": batch.request_counts.succeeded,
                "errored": batch.request_counts.errored,
                "canceled": batch.request_counts.canceled,
                "expired": batch.request_counts.expired,
            },
            "created_at": str(batch.created_at),
        }
        return result
    except ImportError:
        raise HTTPException(500, "anthropic package not installed")
    except Exception as e:
        raise HTTPException(500, str(e)[:500])


@app.get("/v1/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Retrieve results from a completed Claude batch."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(400, "ANTHROPIC_API_KEY not set")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        results = []
        for result in client.messages.batches.results(batch_id):
            entry: Dict[str, Any] = {"custom_id": result.custom_id, "type": result.result.type}
            if result.result.type == "succeeded":
                msg = result.result.message
                text = msg.content[0].text if msg.content else ""
                entry["response"] = text
                entry["model"] = msg.model
                entry["tokens"] = {"input": msg.usage.input_tokens, "output": msg.usage.output_tokens}
            elif result.result.type == "errored":
                entry["error"] = str(result.result.error)
            results.append(entry)
        return {"batch_id": batch_id, "count": len(results), "results": results}
    except ImportError:
        raise HTTPException(500, "anthropic package not installed")
    except Exception as e:
        raise HTTPException(500, str(e)[:500])


# ---------------------------------------------------------------------------
#  Routes: Billing & Pricing
# ---------------------------------------------------------------------------

@app.get("/v1/pricing")
async def pricing():
    """AetherCode is free forever. Bring your own API keys."""
    return {
        "product": PRODUCT_NAME,
        "price": "Free forever",
        "how_it_works": "Bring your own API keys for paid models (Google AI, Claude, OpenAI, xAI, etc). Free models (Ollama, HuggingFace) work out of the box.",
        "features": {
            "all_modes": True,
            "code_mode": True,
            "research_mode": True,
            "multi_agent": True,
            "tentacles": 20,
            "training_export": True,
            "arena": True,
            "unlimited_messages": True,
        },
    }


@app.get("/v1/providers")
async def providers():
    """Provider setup and runtime availability for BYOK model access."""
    return _provider_status_payload()


@app.post("/v1/research/web")
async def research_web(req: WebResearchRequest):
    """Run lightweight web research (search + source snippets) for Arena evidence packs."""
    query = req.query.strip()
    if not query:
        raise HTTPException(400, "query is required")

    tasks: List[Awaitable[List[Dict[str, Any]]]] = []
    if req.include_duckduckgo:
        tasks.append(_duckduckgo_search(query, max_results=req.max_results))
    if req.include_google_news:
        tasks.append(_google_news_search(query, max_results=req.max_results))
    if req.include_arxiv:
        tasks.append(_arxiv_search(query, max_results=max(3, min(req.max_results, 10))))

    gathered: List[Dict[str, Any]] = []
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for block in results:
            if isinstance(block, Exception):
                continue
            gathered.extend(block)

    deduped: List[Dict[str, Any]] = []
    seen_urls: set = set()
    for item in gathered:
        url = str(item.get("url", "")).strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)
        if len(deduped) >= req.max_results:
            break

    if req.fetch_snippets and deduped:
        snippets = await asyncio.gather(
            *[_fetch_page_snippet(str(item.get("url", ""))) for item in deduped],
            return_exceptions=True,
        )
        for idx, snippet in enumerate(snippets):
            if isinstance(snippet, Exception):
                deduped[idx]["snippet"] = ""
            else:
                deduped[idx]["snippet"] = str(snippet or "")

    evidence: List[str] = []
    for item in deduped[:8]:
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        source = str(item.get("source", "")).strip()
        snippet = str(item.get("snippet", "")).strip()
        line = f"[{source}] {title or url}"
        if snippet:
            line += f" :: {snippet[:220]}"
        evidence.append(line)

    return {
        "ok": True,
        "query": query,
        "count": len(deduped),
        "items": deduped,
        "evidence_pack": evidence,
    }


@app.get("/v1/github/workspace")
async def github_workspace():
    """Current shared GitHub workspace repo used by Arena collaboration."""
    snap = _workspace_snapshot()
    probe = await _github_repo_probe(snap["owner"], snap["repo"])
    return {
        "ok": True,
        "workspace": snap,
        "probe": probe,
    }


@app.post("/v1/github/workspace/attach")
async def github_workspace_attach(req: RepoWorkspaceAttachRequest):
    """Attach Arena collaboration context to an existing GitHub repo."""
    probe = await _github_repo_probe(req.owner, req.repo)
    if not probe.get("ok"):
        raise HTTPException(404, f"Cannot attach repo: {probe.get('error', 'not found')}")

    branch = req.branch.strip() or str(probe.get("default_branch", "main"))
    mode = req.mode.strip() or "shared_repo"
    workspace = _set_workspace_repo(req.owner, req.repo, branch=branch, mode=mode, source="attach_api")
    return {
        "ok": True,
        "workspace": workspace,
        "probe": probe,
    }


@app.post("/v1/github/workspace/create")
async def github_workspace_create(req: RepoWorkspaceCreateRequest):
    """Create a new GitHub repo and optionally attach Arena to it."""
    token = _github_token()
    if not token:
        raise HTTPException(400, "GITHUB_TOKEN not set; cannot create repository")

    try:
        import httpx
    except ImportError:
        raise HTTPException(500, "httpx package not installed")

    payload = {
        "name": req.name.strip(),
        "description": req.description.strip(),
        "private": bool(req.private),
        "auto_init": bool(req.auto_init),
    }
    if not payload["name"]:
        raise HTTPException(400, "Repository name is required")

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                "https://api.github.com/user/repos",
                headers=_github_headers(require_auth=True),
                json=payload,
            )
    except Exception as exc:
        raise HTTPException(502, f"GitHub create repo failed: {str(exc)[:220]}")

    status = "created"
    created_payload: Dict[str, Any] = {}
    if resp.status_code == 201:
        created_payload = resp.json()
    elif resp.status_code == 422:
        status = "already_exists"
    else:
        detail = resp.text[:300]
        raise HTTPException(resp.status_code, f"GitHub create repo error: {detail}")

    owner = (
        str(created_payload.get("owner", {}).get("login", "")).strip()
        or _workspace_snapshot().get("owner", "issdandavis")
    )
    repo = payload["name"]
    probe = await _github_repo_probe(owner, repo)
    if not probe.get("ok"):
        raise HTTPException(502, f"Repo created but probe failed: {probe.get('error', 'unknown')}")

    workspace = _workspace_snapshot()
    if req.attach:
        workspace = _set_workspace_repo(
            owner,
            repo,
            branch=req.branch.strip() or str(probe.get("default_branch", "main")),
            mode="shared_repo",
            source="create_api",
        )

    return {
        "ok": True,
        "status": status,
        "workspace": workspace,
        "repo": {
            "owner": owner,
            "repo": repo,
            "html_url": probe.get("html_url", ""),
            "default_branch": probe.get("default_branch", "main"),
            "private": bool(probe.get("private", req.private)),
        },
    }


@app.get("/v1/github/workspace/tree")
async def github_workspace_tree(
    path: str = Query("", description="Directory path in repo"),
    branch: str = Query("", description="Branch/ref; defaults to workspace branch"),
    limit: int = Query(200, ge=1, le=1000),
):
    """List files/directories from the attached workspace repo using GitHub Contents API."""
    workspace = _workspace_snapshot()
    owner = workspace["owner"]
    repo = workspace["repo"]
    ref = branch.strip() or workspace["branch"]
    clean_path = path.strip().strip("/")
    encoded_path = quote(clean_path, safe="/")
    suffix = f"/{encoded_path}" if encoded_path else ""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents{suffix}"

    try:
        import httpx
    except ImportError:
        raise HTTPException(500, "httpx package not installed")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                url,
                headers=_github_headers(require_auth=False),
                params={"ref": ref},
            )
    except Exception as exc:
        raise HTTPException(502, f"GitHub tree read failed: {str(exc)[:220]}")

    if resp.status_code == 404:
        if not clean_path:
            return {
                "ok": True,
                "workspace": workspace,
                "path": "",
                "ref": ref,
                "kind": "directory",
                "count": 0,
                "items": [],
                "note": "Repository appears empty on this branch.",
            }
        raise HTTPException(404, f"Path not found: {clean_path or '/'}")
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"GitHub tree read error: {resp.text[:280]}")

    payload = resp.json()
    if isinstance(payload, dict) and payload.get("type") == "file":
        return {
            "ok": True,
            "workspace": workspace,
            "path": clean_path,
            "ref": ref,
            "kind": "file",
            "item": {
                "name": payload.get("name", ""),
                "path": payload.get("path", ""),
                "sha": payload.get("sha", ""),
                "size": payload.get("size", 0),
                "download_url": payload.get("download_url", ""),
                "html_url": payload.get("html_url", ""),
            },
        }

    items = payload if isinstance(payload, list) else []
    rows: List[Dict[str, Any]] = []
    for item in items[:limit]:
        rows.append(
            {
                "name": item.get("name", ""),
                "path": item.get("path", ""),
                "type": item.get("type", ""),
                "sha": item.get("sha", ""),
                "size": item.get("size", 0),
                "url": item.get("html_url", ""),
            }
        )
    return {
        "ok": True,
        "workspace": workspace,
        "path": clean_path,
        "ref": ref,
        "kind": "directory",
        "count": len(rows),
        "items": rows,
    }


@app.post("/v1/github/workspace/issues")
async def github_workspace_create_issue(req: RepoWorkspaceIssueRequest):
    """Create a GitHub issue in the attached workspace repo."""
    workspace = _workspace_snapshot()
    owner = workspace["owner"]
    repo = workspace["repo"]

    try:
        import httpx
    except ImportError:
        raise HTTPException(500, "httpx package not installed")

    issue_payload: Dict[str, Any] = {
        "title": req.title.strip(),
        "body": req.body.strip(),
    }
    if req.labels:
        issue_payload["labels"] = req.labels
    if req.assignees:
        issue_payload["assignees"] = req.assignees
    if not issue_payload["title"]:
        raise HTTPException(400, "title is required")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers=_github_headers(require_auth=True),
                json=issue_payload,
            )
    except Exception as exc:
        raise HTTPException(502, f"GitHub issue create failed: {str(exc)[:220]}")

    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"GitHub issue create error: {resp.text[:280]}")

    issue = resp.json()
    return {
        "ok": True,
        "workspace": workspace,
        "issue": {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "url": issue.get("html_url"),
            "state": issue.get("state"),
        },
    }


@app.get("/v1/research/replit")
async def research_replit(
    owner: str = Query("issdandavis", min_length=1),
    repo: str = Query("", description="Optional repo name. If blank, searches all owner repos."),
    limit: int = Query(12, ge=1, le=50),
):
    """Find Replit-related code on GitHub for a user or specific repo."""
    import httpx

    owner = owner.strip()
    repo = repo.strip()
    scope = f"repo:{owner}/{repo}" if repo else f"user:{owner}"
    query = f"replit in:file {scope}"
    per_page = min(limit, 50)

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://api.github.com/search/code",
                params={"q": query, "per_page": per_page, "page": 1},
                headers=headers,
            )
    except Exception as e:
        return {
            "ok": False,
            "query": query,
            "count": 0,
            "items": [],
            "error": f"github_search_failed: {str(e)[:220]}",
        }

    if resp.status_code >= 400:
        detail = resp.text[:220]
        return {
            "ok": False,
            "query": query,
            "count": 0,
            "items": [],
            "error": f"github_{resp.status_code}: {detail}",
        }

    payload = resp.json()
    items_out = []
    for row in payload.get("items", [])[:limit]:
        repo_meta = row.get("repository", {}) if isinstance(row, dict) else {}
        items_out.append(
            {
                "name": row.get("name", ""),
                "path": row.get("path", ""),
                "repository": repo_meta.get("full_name", ""),
                "url": row.get("html_url", ""),
                "score": row.get("score", 0),
            }
        )

    return {
        "ok": True,
        "query": query,
        "count": len(items_out),
        "items": items_out,
        "owner": owner,
        "repo": repo,
    }


@app.get("/v1/research/replit/profile")
async def research_replit_profile(
    owner: str = Query("issdandavis", min_length=1),
    repo: str = Query("ai-workflow-architect-replit", min_length=1),
    limit: int = Query(12, ge=4, le=40),
):
    """Build a capability profile for the legacy Replit app code (local-first, GitHub fallback)."""
    owner = owner.strip()
    repo = repo.strip()
    repo_key = repo.lower()

    direct_local = REPO_ROOT / "external" / "intake" / repo
    mapped_local = _LEGACY_REPLIT_LOCAL_REPO_PATHS.get(repo_key)
    local_root = None
    if direct_local.exists():
        local_root = direct_local
    elif isinstance(mapped_local, Path) and mapped_local.exists():
        local_root = mapped_local

    if local_root is not None:
        profile = _legacy_replit_local_profile(limit=limit)
        profile.update({"owner": owner, "repo": repo, "source": "local_intake"})
        return profile

    probe = await _github_repo_probe(owner, repo)
    if not probe.get("ok"):
        return {
            "ok": False,
            "owner": owner,
            "repo": repo,
            "count": 0,
            "files": [],
            "capabilities": {},
            "error": probe.get("error", "repo_probe_failed"),
        }

    branch = str(probe.get("default_branch", "main"))
    try:
        import httpx
    except ImportError:
        return {
            "ok": False,
            "owner": owner,
            "repo": repo,
            "count": 0,
            "files": [],
            "capabilities": {},
            "error": "httpx package not installed",
        }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            tree_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
                params={"recursive": 1},
                headers=_github_headers(require_auth=False),
            )
    except Exception as exc:
        return {
            "ok": False,
            "owner": owner,
            "repo": repo,
            "count": 0,
            "files": [],
            "capabilities": {},
            "error": f"github_tree_failed: {str(exc)[:220]}",
        }

    if tree_resp.status_code >= 400:
        return {
            "ok": False,
            "owner": owner,
            "repo": repo,
            "count": 0,
            "files": [],
            "capabilities": {},
            "error": f"github_{tree_resp.status_code}: {tree_resp.text[:220]}",
        }

    tree_payload = tree_resp.json()
    all_paths = [str(x.get("path", "")) for x in tree_payload.get("tree", []) if x.get("type") == "blob"]

    priority = [
        "server/routes.ts",
        "server/replitAuth.ts",
        "server/services/providerAdapters.ts",
        "server/services/orchestrator.ts",
        "server/services/stripeClient.ts",
        "server/services/webhookHandlers.ts",
        "server/shopify/webhooks.ts",
        "shared/schema.ts",
        "README.md",
        "replit.md",
    ]
    selected: List[str] = []
    for rel in priority:
        hit = next((p for p in all_paths if p.endswith(rel)), None)
        if hit and hit not in selected:
            selected.append(hit)
    if len(selected) < limit:
        scored = sorted(
            (p for p in all_paths if p not in selected),
            key=lambda p: (
                ("routes" in p.lower()) * 6
                + ("stripe" in p.lower()) * 5
                + ("webhook" in p.lower()) * 5
                + ("shopify" in p.lower()) * 4
                + ("provider" in p.lower()) * 4
                + ("orchestr" in p.lower()) * 3
                + ("workflow" in p.lower()) * 3
                + ("replit" in p.lower()) * 2
            ),
            reverse=True,
        )
        for path in scored:
            if len(selected) >= limit:
                break
            selected.append(path)

    files = [
        {
            "path": p,
            "url": f"https://github.com/{owner}/{repo}/blob/{branch}/{p}",
        }
        for p in selected[:limit]
    ]
    paths_blob = " ".join(selected).lower()
    capabilities = {
        "replit_auth": ("replitauth" in paths_blob) or ("replitauth" in paths_blob),
        "provider_router": "provideradapters" in paths_blob or "provider" in paths_blob,
        "stripe": "stripe" in paths_blob,
        "webhooks": "webhook" in paths_blob,
        "shopify": "shopify" in paths_blob,
        "workflows": "workflow" in paths_blob,
        "orchestration": "orchestr" in paths_blob or "roundtable" in paths_blob,
    }
    return {
        "ok": True,
        "source": "github_tree",
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "count": len(files),
        "files": files,
        "capabilities": capabilities,
        "repo_url": probe.get("html_url", f"https://github.com/{owner}/{repo}"),
    }


@app.get("/v1/lore/art")
async def lore_art_manifest():
    """Return available Codex/Everweave art assets for the UI."""
    items = []
    for slug, meta in _LORE_ART_REGISTRY.items():
        path = meta.get("path")
        if isinstance(path, Path) and path.exists():
            items.append(
                {
                    "id": slug,
                    "title": meta.get("title", slug),
                    "story": meta.get("story", ""),
                    "url": f"/v1/lore/art/{slug}",
                }
            )
    return {"count": len(items), "items": items}


@app.get("/v1/lore/art/{art_id}")
async def lore_art_file(art_id: str):
    """Serve a whitelisted lore image by id."""
    meta = _LORE_ART_REGISTRY.get(art_id)
    if not meta:
        raise HTTPException(404, f"Unknown lore art id: {art_id}")
    path = meta.get("path")
    if not isinstance(path, Path) or not path.exists():
        raise HTTPException(404, f"Art asset missing: {art_id}")
    return FileResponse(path)


@app.get("/v1/crosstalk/latest")
async def crosstalk_latest(limit: int = Query(20, ge=1, le=100)):
    """Read latest AI-to-AI cross-talk packets."""
    return {
        "ok": True,
        "count": limit,
        "items": _read_crosstalk_latest(limit=limit),
        "lane": str(_CROSSTALK_LANE),
    }


@app.get("/v1/crosstalk/pending")
async def crosstalk_pending(limit: int = Query(200, ge=1, le=2000)):
    """Return latest unresolved cross-talk tasks keyed by task_id."""
    return _crosstalk_pending_snapshot(limit=limit)


@app.get("/v1/crosstalk/session-signons")
async def crosstalk_session_signons(limit: int = Query(200, ge=1, le=2000)):
    """Return latest per-session sign-on records for agent coordination."""
    return _session_signons_snapshot(limit=limit)


@app.post("/v1/crosstalk/send")
async def crosstalk_send(payload: CrossTalkRequest):
    """Emit a cross-talk packet and mirror it into Obsidian notes."""
    if not payload.summary.strip():
        raise HTTPException(400, "summary cannot be empty")
    written = _write_crosstalk_packet(payload)
    return {
        "ok": True,
        "packet_id": written["packet"]["packet_id"],
        "packet_path": str(written["packet_path"]),
        "lane": str(_CROSSTALK_LANE),
    }


@app.get("/v1/crosstalk/verify/{packet_id}")
async def crosstalk_verify(packet_id: str):
    """Verify that a packet exists on all delivery lanes."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "system"))
        from crosstalk_relay import verify_packet
        return verify_packet(packet_id)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class CrossTalkAckRequest(BaseModel):
    packet_id: str
    agent: str
    notes: str = ""


@app.post("/v1/crosstalk/ack")
async def crosstalk_ack(payload: CrossTalkAckRequest):
    """Mark a cross-talk packet as consumed by an agent."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "system"))
        from crosstalk_relay import ack_packet
        return ack_packet(payload.packet_id, payload.agent, payload.notes)
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/v1/crosstalk/pending/{agent}")
async def crosstalk_pending_for_agent(agent: str, limit: int = Query(50, ge=1, le=500)):
    """List packets addressed to an agent that haven't been ACK'd."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "system"))
        from crosstalk_relay import pending_for_agent
        items = pending_for_agent(agent, limit)
        return {"agent": agent, "count": len(items), "items": items}
    except Exception as exc:
        return {"agent": agent, "count": 0, "items": [], "error": str(exc)}


@app.get("/v1/crosstalk/health")
async def crosstalk_health():
    """Cross-talk system health report: lane status, ACK stats, pending counts."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "system"))
        from crosstalk_relay import health_report
        return health_report()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
#  Routes: AetherGates — Controlled Portals from the Everweave
# ---------------------------------------------------------------------------

@app.get("/v1/gates")
async def gates_list(tongue: Optional[str] = Query(None)):
    """List all AetherGates, optionally filtered by Sacred Tongue."""
    try:
        from src.aethercode.aether_gates import list_gates
        return {"ok": True, "gates": list_gates(tongue)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class GateInvokeRequest(BaseModel):
    gate_id: str
    agent_id: str = "agent.claude"
    params: Dict[str, str] = Field(default_factory=dict)
    path_vars: Dict[str, str] = Field(default_factory=dict)


@app.post("/v1/gates/invoke")
async def gates_invoke(payload: GateInvokeRequest):
    """Invoke an AetherGate with governance checks and Rath observation."""
    try:
        from src.aethercode.aether_gates import invoke_gate
        return await invoke_gate(
            gate_id=payload.gate_id,
            agent_id=payload.agent_id,
            params=payload.params or None,
            path_vars=payload.path_vars or None,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/v1/gates/permissions/{agent_id}")
async def gates_permissions(agent_id: str):
    """Check an agent's privilege tier and permissions."""
    try:
        from src.aethercode.aether_gates import get_agent_permissions
        return get_agent_permissions(agent_id)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/v1/gates/rath/observations")
async def gates_rath_observations(limit: int = Query(50, ge=1, le=500)):
    """Rath's observation log — all portal traffic."""
    try:
        from src.aethercode.aether_gates import rath
        return {"observations": rath.recent(limit), "stats": rath.stats()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
#  Routes: Platform Status
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Platform health check."""
    provider_status = _provider_status_payload()
    return {
        "status": "ok",
        "product": PRODUCT_NAME,
        "version": VERSION,
        "subsystems": {
            "octo_armor": _OCTO_AVAILABLE and engine.octo is not None,
            "octotree": _OCTOTREE_AVAILABLE,
            "context_scorer": _SCORER_AVAILABLE,
            "aaoe": _AAOE_AVAILABLE,
            "firebase": _FIREBASE,
        },
        "providers": {
            "enabled": provider_status.get("enabled", False),
            "available_count": provider_status.get("available_count", 0),
            "available": provider_status.get("available", []),
        },
        "workspace_repo": _workspace_snapshot(),
        "sessions_active": len(_sessions),
        "training_pairs_buffered": len(_training_pairs),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@app.get("/v1/capabilities")
async def capabilities():
    """Return full platform capabilities for client discovery."""
    provider_status = _provider_status_payload()
    return {
        "product": PRODUCT_NAME,
        "version": VERSION,
        "modes": {
            "chat": {"available": True, "min_tier": "free"},
            "code": {"available": True, "min_tier": "free"},
            "research": {"available": True, "min_tier": "free"},
            "browse": {"available": _OCTOTREE_AVAILABLE, "min_tier": "free"},
        },
        "features": {
            "governance": True,
            "training_flywheel": True,
            "multi_model": _OCTO_AVAILABLE,
            "parallel_browse": _OCTOTREE_AVAILABLE,
            "context_scoring": _SCORER_AVAILABLE,
            "agent_identity": _AAOE_AVAILABLE,
            "firebase_sync": _FIREBASE,
            "github_workspace": True,
            "ai2ai_autonomous": True,
        },
        "models_available": engine.octo is not None,
        "providers_available": provider_status.get("available", []),
        "providers_available_count": provider_status.get("available_count", 0),
        "max_octotree_workers": 216,
        "sacred_tongues": ["KO", "AV", "RU", "CA", "UM", "DR"],
        "workspace_repo": _workspace_snapshot(),
    }


# ---------------------------------------------------------------------------
#  Routes: WebSocket (real-time streaming)
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """Real-time WebSocket chat with streaming responses."""
    await ws.accept()
    ws_id = uuid.uuid4().hex[:8]
    _active_ws[ws_id] = ws

    try:
        while True:
            data = await ws.receive_json()
            req = ChatRequest(**data)
            tier = _resolve_tier(data.get("key"))

            # Stream start
            await ws.send_json({"type": "stream_start", "mode": req.mode})

            # Process
            result = await engine.chat(req, tier)

            # Send result
            await ws.send_json({
                "type": "response",
                "data": result.dict(),
            })

    except WebSocketDisconnect:
        pass
    finally:
        _active_ws.pop(ws_id, None)


# ---------------------------------------------------------------------------
#  Routes: Dashboard (PWA)
# ---------------------------------------------------------------------------

@app.get("/manifest.json")
async def serve_manifest():
    """Serve PWA manifest for desktop/mobile install prompts."""
    manifest_path = AETHERCODE_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(404, "manifest.json not found")


@app.get("/sw.js")
async def serve_service_worker():
    """Serve service worker at root scope."""
    sw_path = AETHERCODE_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(404, "sw.js not found")


@app.get("/icon-192.png")
async def serve_legacy_icon_192():
    """Backward-compatible icon route."""
    icon = AETHERCODE_STATIC_DIR / "icons" / "icon-192.png"
    if icon.exists():
        return FileResponse(icon, media_type="image/png")
    raise HTTPException(404, "icon-192.png not found")


@app.get("/icon-512.png")
async def serve_legacy_icon_512():
    """Backward-compatible icon route."""
    icon = AETHERCODE_STATIC_DIR / "icons" / "icon-512.png"
    if icon.exists():
        return FileResponse(icon, media_type="image/png")
    raise HTTPException(404, "icon-512.png not found")


@app.get("/arena", response_class=HTMLResponse)
async def serve_arena():
    """Serve the AI Arena — multi-model poker table."""
    arena_path = Path(__file__).parent / "arena.html"
    if arena_path.exists():
        return HTMLResponse(arena_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Arena — arena.html not found</h1>", status_code=404)


@app.get("/home", response_class=HTMLResponse)
async def serve_kerrigan_home():
    """Serve the Kerrigan AI Home dashboard."""
    dashboard_path = REPO_ROOT / "aetherbrowse" / "runtime" / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Kerrigan — dashboard.html not found</h1>", status_code=404)


@app.get("/api/status")
async def api_status():
    """System status for the Kerrigan dashboard."""
    provider_status = _provider_status_payload()
    crosstalk = _crosstalk_pending_snapshot(limit=25)
    session_signons = _session_signons_snapshot(limit=25)
    return {
        "ok": True,
        "product": PRODUCT_NAME,
        "version": VERSION,
        "subsystems": {
            "octo_armor": _OCTO_AVAILABLE and engine.octo is not None,
            "octotree": _OCTOTREE_AVAILABLE,
            "context_scorer": _SCORER_AVAILABLE,
            "aaoe": _AAOE_AVAILABLE,
            "firebase": _FIREBASE,
        },
        "providers": {
            "enabled": provider_status.get("enabled", False),
            "available_count": provider_status.get("available_count", 0),
            "available": provider_status.get("available", []),
        },
        "firebase": _firebase_status_payload(),
        "autopilot": dict(_autopilot_state),
        "ai2ai": dict(_ai2ai_state),
        "coordination": {
            "crosstalk_pending": crosstalk.get("pending_count", 0),
            "crosstalk_total_tasks": crosstalk.get("total_tasks", 0),
            "sessions_active": session_signons.get("counts", {}).get("active", 0),
            "sessions_verified": session_signons.get("counts", {}).get("verified", 0),
        },
        "sessions": len(_sessions),
        "training_pairs": len(_training_pairs),
    }


@app.post("/api/action/{name}")
async def api_action(name: str):
    """Trigger a named action from the Kerrigan dashboard."""
    if name not in _dashboard_actions:
        return JSONResponse({"ok": False, "error": f"Unknown action: {name}"}, status_code=400)
    desc = _dashboard_actions[name]
    run = await _execute_dashboard_action(name, desc, source="manual")
    return {
        "ok": True,
        "action": name,
        "message": f"Executed: {desc}",
        "run_id": run.get("id"),
        "estimated_revenue_today_usd": _autopilot_state.get("estimated_revenue_today_usd", 0.0),
    }


@app.post("/ops/{action}")
async def ops_action(action: str, payload: Dict[str, Any] = Body(default_factory=dict)):
    """Execute IDE Ops panel actions through concrete backend handlers."""
    op = (action or "").strip().lower()
    if op not in _ops_supported_actions:
        return JSONResponse(
            {
                "ok": False,
                "action": op,
                "error": f"Unsupported ops action: {action}",
                "supported": sorted(_ops_supported_actions),
            },
            status_code=400,
        )

    try:
        if op == "crosstalk":
            summary = str(payload.get("summary", "Ops sync emitted from IDE panel")).strip() or "Ops sync emitted from IDE panel"
            packet = CrossTalkRequest(
                summary=summary,
                recipient=str(payload.get("recipient", "agent.claude")).strip() or "agent.claude",
                sender=str(payload.get("sender", "agent.codex")).strip() or "agent.codex",
                intent=str(payload.get("intent", "sync")).strip() or "sync",
                status=str(payload.get("status", "in_progress")).strip() or "in_progress",
                task_id=str(payload.get("task_id", "OPS-SYNC")).strip() or "OPS-SYNC",
                next_action=str(payload.get("next_action", "")).strip(),
                risk=str(payload.get("risk", "low")).strip() or "low",
                repo=str(payload.get("repo", "SCBE-AETHERMOORE")).strip() or "SCBE-AETHERMOORE",
                branch=str(payload.get("branch", "local")).strip() or "local",
                proof=_coerce_str_list(payload.get("proof"), default=[]),
                session_id=str(payload.get("session_id", "")).strip(),
                codename=str(payload.get("codename", "")).strip(),
                where=str(payload.get("where", "aethercode:ops-panel")).strip(),
                why=str(payload.get("why", "synchronize multi-agent workflow state")).strip(),
                how=str(payload.get("how", "gateway route /ops/crosstalk")).strip(),
            )
            written = _write_crosstalk_packet(packet)
            return {
                "ok": True,
                "action": op,
                "message": "Cross-talk packet written",
                "packet_id": written["packet"]["packet_id"],
                "packet_path": str(written["packet_path"]),
                "line": written["line"],
            }

        if op == "portal":
            registry = str(payload.get("registry", "config/governance/verified_links_registry.json")).strip()
            out_dir = str(payload.get("out_dir", "artifacts/verified_links_portal")).strip()
            script_run = await _run_local_python_script(
                "scripts/system/build_verified_links_portal.py",
                args=["--registry", registry, "--out-dir", out_dir],
                timeout_sec=120.0,
            )
            if not script_run.get("ok"):
                return JSONResponse(
                    {
                        "ok": False,
                        "action": op,
                        "error": script_run.get("stderr", "").strip() or script_run.get("error", "portal_build_failed"),
                        "returncode": script_run.get("returncode"),
                    },
                    status_code=500,
                )
            parsed = script_run.get("json") or {}
            return {
                "ok": True,
                "action": op,
                "message": "Verified links portal built",
                "result": parsed,
                "manifest": parsed.get("manifest", str((REPO_ROOT / out_dir / "manifest.json").resolve())),
                "portal_index": parsed.get("portal_index", str((REPO_ROOT / out_dir / "index.html").resolve())),
            }

        if op == "backup":
            defaults = _ops_backup_defaults()
            source_defaults = defaults["source"]
            dest_defaults = defaults["dest"]
            sources = _coerce_str_list(payload.get("source"), default=source_defaults)
            dests = _coerce_str_list(payload.get("dest"), default=dest_defaults)
            dry_run = _coerce_bool(payload.get("dry_run"), default=True)

            if not dests:
                return JSONResponse(
                    {
                        "ok": False,
                        "action": op,
                        "error": "No backup destinations provided. Set payload.dest or SCBE_BACKUP_DESTS / SCBE_BACKUP_REPO_DEST+SCBE_BACKUP_CLOUD_DEST.",
                    },
                    status_code=400,
                )

            args: List[str] = []
            for source_path in sources:
                args.extend(["--source", source_path])
            for dest_path in dests:
                args.extend(["--dest", dest_path])

            bundle_name = str(payload.get("bundle_name", "")).strip()
            manifest_out = str(payload.get("manifest_out", "")).strip()
            if bundle_name:
                args.extend(["--bundle-name", bundle_name])
            if manifest_out:
                args.extend(["--manifest-out", manifest_out])

            min_copies = payload.get("min_verified_copies")
            if min_copies is not None:
                try:
                    min_copies_int = int(min_copies)
                    if min_copies_int > 0:
                        args.extend(["--min-verified-copies", str(min_copies_int)])
                except (TypeError, ValueError):
                    pass

            if _coerce_bool(payload.get("delete_source"), default=False):
                args.append("--delete-source")
            if dry_run:
                args.append("--dry-run")

            script_run = await _run_local_python_script(
                "scripts/system/ship_verify_prune.py",
                args=args,
                timeout_sec=300.0,
            )
            if not script_run.get("ok"):
                return JSONResponse(
                    {
                        "ok": False,
                        "action": op,
                        "error": script_run.get("stderr", "").strip() or script_run.get("error", "backup_run_failed"),
                        "returncode": script_run.get("returncode"),
                    },
                    status_code=500,
                )

            parsed = script_run.get("json") or {}
            return {
                "ok": True,
                "action": op,
                "message": "Backup verify run complete",
                "dry_run": dry_run,
                "sources": sources,
                "destinations": dests,
                "defaults_source": defaults.get("source_kind", "builtin"),
                "result": parsed,
                "manifest": parsed.get("manifest", ""),
            }

        mapped_action = _ops_dashboard_action_map.get(op, "")
        if mapped_action:
            desc = _dashboard_actions.get(mapped_action, mapped_action)
            run = await _execute_dashboard_action(mapped_action, desc, source="manual")
            return {
                "ok": True,
                "action": op,
                "mapped_action": mapped_action,
                "message": f"Executed: {desc}",
                "run_id": run.get("id"),
                "run_status": run.get("status"),
                "estimated_revenue_today_usd": _autopilot_state.get("estimated_revenue_today_usd", 0.0),
            }

        return JSONResponse(
            {"ok": False, "action": op, "error": "No handler available for action"},
            status_code=500,
        )
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "action": op,
                "error": str(exc)[:500],
            },
            status_code=500,
        )


@app.get("/api/firebase/status")
async def api_firebase_status():
    """Firebase readiness for browser features and automation."""
    return _firebase_status_payload()


@app.get("/api/runs/latest")
async def api_runs_latest(limit: int = Query(8, ge=1, le=50)):
    """Recent run lane records for dashboard transparency."""
    runs = list(reversed(_run_history[-limit:]))
    return {"ok": True, "runs": runs}


@app.get("/api/autopilot/status")
async def api_autopilot_status():
    """Current autopilot state used by dashboard controls."""
    _ensure_autopilot_day()
    return {"ok": True, "autopilot": dict(_autopilot_state)}


@app.post("/api/autopilot/start")
async def api_autopilot_start(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Enable revenue autopilot loop (target defaults to $1/day)."""
    global _autopilot_task
    target = payload.get("target_usd", 1.0)
    try:
        target_value = float(target)
    except (TypeError, ValueError):
        target_value = 1.0
    target_value = max(0.25, min(target_value, 100.0))

    _touch_autopilot(
        enabled=True,
        goal=f"Reach ${target_value:.2f}/day via browser execution loop",
        target_usd=target_value,
        started_at=_autopilot_state.get("started_at") or _utc_now_iso(),
        status="starting",
        last_error="",
    )
    if _autopilot_task is None or _autopilot_task.done():
        _autopilot_task = asyncio.create_task(_autopilot_loop())
    return {"ok": True, "autopilot": dict(_autopilot_state)}


@app.post("/api/autopilot/stop")
async def api_autopilot_stop():
    """Disable revenue autopilot loop."""
    global _autopilot_task
    _touch_autopilot(enabled=False, status="stopping")
    if _autopilot_task and not _autopilot_task.done():
        _autopilot_task.cancel()
    _autopilot_task = None
    _touch_autopilot(status="stopped")
    return {"ok": True, "autopilot": dict(_autopilot_state)}


@app.post("/api/autopilot/cursor")
async def api_autopilot_cursor(payload: Dict[str, Any] = Body(default_factory=dict)):
    """Toggle dashboard AI cursor overlay state."""
    enabled = bool(payload.get("enabled", False))
    _touch_autopilot(ai_cursor_enabled=enabled)
    return {"ok": True, "enabled": enabled}


@app.get("/api/ai2ai/status")
async def api_ai2ai_status():
    """Current autonomous AI-to-AI loop state."""
    participants = _ai2ai_available_tentacles(max_models=int(_ai2ai_state.get("max_models", 4)))
    return {
        "ok": True,
        "ai2ai": dict(_ai2ai_state),
        "participants": participants,
    }


@app.post("/api/ai2ai/start")
async def api_ai2ai_start(payload: AI2AIStartRequest):
    """Enable autonomous AI-to-AI cycles in the background."""
    global _ai2ai_task
    interval_seconds = int(payload.interval_seconds)
    max_models = int(payload.max_models)
    seed_prompt = payload.seed_prompt.strip()
    if not seed_prompt:
        seed_prompt = _ai2ai_state.get("seed_prompt", "")

    _touch_ai2ai(
        enabled=True,
        status="starting",
        interval_seconds=interval_seconds,
        max_models=max_models,
        seed_prompt=seed_prompt,
        started_at=_utc_now_iso(),
        last_error="",
    )
    if _ai2ai_task is None or _ai2ai_task.done():
        _ai2ai_task = asyncio.create_task(_ai2ai_loop())
    return {"ok": True, "ai2ai": dict(_ai2ai_state)}


@app.post("/api/ai2ai/stop")
async def api_ai2ai_stop():
    """Disable autonomous AI-to-AI background cycles."""
    global _ai2ai_task
    _touch_ai2ai(enabled=False, status="stopping")
    if _ai2ai_task and not _ai2ai_task.done():
        _ai2ai_task.cancel()
    _ai2ai_task = None
    _touch_ai2ai(status="stopped")
    return {"ok": True, "ai2ai": dict(_ai2ai_state)}


@app.post("/api/ai2ai/tick")
async def api_ai2ai_tick(payload: AI2AITickRequest):
    """Run one immediate AI-to-AI cycle now."""
    prompt = payload.prompt.strip() if payload.prompt else ""
    if not prompt:
        prompt = str(_ai2ai_state.get("seed_prompt", ""))

    try:
        cycle = await _run_ai2ai_cycle(
            prompt_seed=prompt,
            max_models=int(_ai2ai_state.get("max_models", 4)),
        )
    except Exception as exc:
        _touch_ai2ai(status="error", last_error=str(exc)[:300])
        raise HTTPException(500, f"ai2ai_cycle_failed: {str(exc)[:220]}")

    _touch_ai2ai(
        cycles=int(_ai2ai_state.get("cycles", 0)) + 1,
        last_summary=str(cycle.get("summary", ""))[:600],
        status="running" if _ai2ai_state.get("enabled", False) else "idle",
        last_error="",
    )
    return {"ok": True, "cycle": cycle, "ai2ai": dict(_ai2ai_state)}


@app.post("/api/ai2ai/workflow/debate")
async def api_ai2ai_workflow_debate(payload: AI2AIWorkflowDebateRequest):
    """Run one multi-model debate cycle and convert output into a workflow task."""
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")

    try:
        cycle = await _run_ai2ai_cycle(
            prompt_seed=prompt,
            max_models=int(payload.max_models),
        )
    except Exception as exc:
        _touch_ai2ai(status="error", last_error=str(exc)[:300])
        raise HTTPException(500, f"ai2ai_workflow_cycle_failed: {str(exc)[:220]}")

    _touch_ai2ai(
        cycles=int(_ai2ai_state.get("cycles", 0)) + 1,
        last_summary=str(cycle.get("summary", ""))[:600],
        status="running" if _ai2ai_state.get("enabled", False) else "idle",
        last_error="",
    )

    review_gate = _ai2ai_review_gate(
        summary=str(cycle.get("summary", "")),
        outputs=list(cycle.get("outputs", []) or []),
        min_avg_governance=float(payload.min_avg_governance),
        min_any_governance=float(payload.min_any_governance),
        require_tests_hint=bool(payload.require_tests_hint),
    )

    workspace = _workspace_snapshot()
    issue_payload: Optional[Dict[str, Any]] = None
    if payload.create_issue:
        decision_prefix = "PRODUCTION" if review_gate.get("decision") == "promote" else "REVIEW"
        title_seed = prompt.splitlines()[0].strip()
        issue_title = f"[{decision_prefix}][AI2AI Debate] {title_seed[:120]}"
        summary = str(cycle.get("summary", "")).strip()
        participants = ", ".join(cycle.get("participants", []) or [])
        gate_json = json.dumps(review_gate, indent=2, ensure_ascii=True)
        issue_labels = list(dict.fromkeys([*(payload.labels or []), *(review_gate.get("recommended_labels", []) or [])]))
        body = (
            "## AI2AI Debate Prompt\n"
            f"{prompt}\n\n"
            "## Cycle Summary\n"
            f"{summary[:4000]}\n\n"
            "## Participants\n"
            f"{participants}\n\n"
            "## Review Gate\n"
            f"```json\n{gate_json}\n```\n\n"
            "## Next Step\n"
            "Convert this into an implementation branch + PR checklist."
        )
        issue = await _github_create_issue(
            workspace["owner"],
            workspace["repo"],
            issue_title,
            body=body,
            labels=issue_labels,
            assignees=payload.assignees,
        )
        issue_payload = {
            "number": issue.get("number"),
            "title": issue.get("title"),
            "url": issue.get("html_url"),
            "state": issue.get("state"),
            "labels": issue_labels,
        }

    return {
        "ok": True,
        "workspace": workspace,
        "cycle": cycle,
        "review_gate": review_gate,
        "production_decision": review_gate.get("decision", "hold"),
        "production_route": review_gate.get("route_to", "review_queue"),
        "issue": issue_payload,
        "ai2ai": dict(_ai2ai_state),
    }


@app.post("/api/ai2ai/workflow/review-gate")
async def api_ai2ai_workflow_review_gate(payload: AI2AIWorkflowReviewGateRequest):
    """Evaluate a workflow proposal and decide production routing."""
    gate = _ai2ai_review_gate(
        summary=payload.summary,
        outputs=payload.outputs,
        min_avg_governance=float(payload.min_avg_governance),
        min_any_governance=float(payload.min_any_governance),
        require_tests_hint=bool(payload.require_tests_hint),
    )
    return {
        "ok": True,
        "review_gate": gate,
        "production_decision": gate.get("decision", "hold"),
        "production_route": gate.get("route_to", "review_queue"),
    }


# ---------------------------------------------------------------------------
#  Cross-Port Mesh (Neural Ring — arms talk without going through brain)
# ---------------------------------------------------------------------------

# Internal service registry — octopus arms
_MESH_SERVICES = {
    "bridge":    {"port": 8001, "name": "SCBE Bridge",     "prefix": "/mesh/bridge"},
    "webhook":   {"port": 8002, "name": "Webhook Server",  "prefix": "/mesh/webhook"},
    "pollypad":  {"port": 8200, "name": "PollyPad IDE",    "prefix": "/mesh/pollypad"},
    "aethernet": {"port": 8300, "name": "AetherNet Social", "prefix": "/mesh/aethernet"},
}


@app.get("/mesh/status")
async def mesh_status():
    """Check which services are alive across all ports."""
    import httpx
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for svc_id, svc in _MESH_SERVICES.items():
            try:
                resp = await client.get(f"http://127.0.0.1:{svc['port']}/health")
                results[svc_id] = {
                    "name": svc["name"],
                    "port": svc["port"],
                    "status": "online" if resp.status_code == 200 else "degraded",
                    "data": resp.json() if resp.status_code == 200 else None,
                }
            except Exception:
                results[svc_id] = {
                    "name": svc["name"],
                    "port": svc["port"],
                    "status": "offline",
                    "data": None,
                }
    # Add self
    results["aethercode"] = {
        "name": "AetherCode Gateway",
        "port": 8500,
        "status": "online",
        "data": {"sessions": len(_sessions), "training_pairs": len(_training_pairs)},
    }
    online = sum(1 for v in results.values() if v["status"] == "online")
    return {"mesh_health": f"{online}/{len(results)} online", "services": results}


from fastapi import Request as FastAPIRequest


@app.api_route(
    "/mesh/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def mesh_proxy(service: str, path: str, request: FastAPIRequest):
    """Reverse proxy — route requests to any mesh service through port 8500.

    Examples:
        GET  /mesh/aethernet/feed          → localhost:8300/feed
        POST /mesh/bridge/v1/tongue/encode → localhost:8001/v1/tongue/encode
        GET  /mesh/pollypad/health         → localhost:8200/health
    """
    svc = _MESH_SERVICES.get(service)
    if not svc:
        raise HTTPException(404, f"Unknown mesh service: {service}. Available: {list(_MESH_SERVICES.keys())}")

    import httpx
    target = f"http://127.0.0.1:{svc['port']}/{path}"
    if request.url.query:
        target += f"?{request.url.query}"

    try:
        body = await request.body()
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding")
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=request.method,
                url=target,
                content=body if body else None,
                headers=headers,
            )
            ct = resp.headers.get("content-type", "")
            if "application/json" in ct:
                return JSONResponse(content=resp.json(), status_code=resp.status_code)
            elif "text/html" in ct:
                return HTMLResponse(content=resp.text, status_code=resp.status_code)
            else:
                return JSONResponse(content={"raw": resp.text}, status_code=resp.status_code)
    except Exception as e:
        err_type = type(e).__name__
        raise HTTPException(502, f"Mesh proxy to '{service}' (port {svc['port']}): {err_type} — {e}")


@app.get("/mesh/ring")
async def mesh_ring():
    """Neural ring topology — show which services can talk to each other.

    The octopus neural ring lets arms communicate WITHOUT going through
    the brain. This endpoint shows the ring connectivity map.
    """
    # Every service can reach every other through the gateway
    services = list(_MESH_SERVICES.keys()) + ["aethercode"]
    ring = []
    for i, svc in enumerate(services):
        next_svc = services[(i + 1) % len(services)]
        ring.append({"from": svc, "to": next_svc, "type": "ring"})
    return {
        "topology": "neural_ring",
        "bio_analog": "Octopus arm-to-arm signaling bypasses central brain",
        "nodes": len(services),
        "ring": ring,
        "cross_talk_bus": str(REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"),
    }


# ---------------------------------------------------------------------------
#  Routes: Dashboard (PWA)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_app():
    """Serve the AetherCode PWA."""
    app_path = Path(__file__).parent / "app.html"
    if app_path.exists():
        return HTMLResponse(app_path.read_text(encoding="utf-8"))
    return HTMLResponse(f"""
    <html><head><title>AetherCode</title></head>
    <body style="background:#0a0e17;color:#e2e8f0;font-family:system-ui;display:flex;
    align-items:center;justify-content:center;height:100vh;margin:0">
    <div style="text-align:center">
        <h1 style="font-size:3rem">AetherCode</h1>
        <p style="color:#94a3b8">Free Multi-Model AI Platform — Bring Your Own Keys</p>
        <p style="color:#6366f1">v{VERSION} — Gateway running on port 8500</p>
        <p style="color:#94a3b8;margin-top:2rem">
            <a href="/app" style="color:#818cf8">App</a> |
            <a href="/arena" style="color:#818cf8">Arena</a> |
            <a href="/docs" style="color:#818cf8">API</a> |
            <a href="/health" style="color:#818cf8">Health</a>
        </p>
    </div>
    </body></html>
    """)


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="AetherCode Gateway")
    parser.add_argument("--port", type=int, default=8500)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn
    uvicorn.run(
        "src.aethercode.gateway:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
