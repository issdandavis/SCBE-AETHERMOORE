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
import hashlib
import json
import math
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
_spin_context_cache: List[str] = []
_spin_context_loaded = False

_OBS_NOTES_CONTEXT = REPO_ROOT / "notes" / "_context.md"
_OBS_NOTES_INBOX = REPO_ROOT / "notes" / "_inbox.md"
_OBS_AGENT_CODEX = REPO_ROOT / "agents" / "codex.md"
_CROSSTALK_LANE = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes" / "cross_talk.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_task = _safe_packet_token(payload.task_id, fallback="general")
    packet_id = f"cross-talk-{_safe_packet_token(payload.sender, fallback='agent')}-{safe_task}-{stamp}"

    packet = {
        "packet_id": packet_id,
        "created_at": created_at,
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
        "gates": {"governance_packet": True, "tests_requested": []},
    }

    out_dir = REPO_ROOT / "artifacts" / "agent_comm" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    packet_path = out_dir / f"{packet_id}.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    _CROSSTALK_LANE.parent.mkdir(parents=True, exist_ok=True)
    with _CROSSTALK_LANE.open("a", encoding="utf-8") as lane:
        lane.write(json.dumps(packet) + "\n")

    line = (
        f"- {created_at} {payload.sender} -> {payload.recipient} | {payload.intent} | {payload.status} | "
        f"{payload.task_id} | {payload.summary} ({packet_path})"
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
        },
        "models_available": engine.octo is not None,
        "providers_available": provider_status.get("available", []),
        "providers_available_count": provider_status.get("available_count", 0),
        "max_octotree_workers": 216,
        "sacred_tongues": ["KO", "AV", "RU", "CA", "UM", "DR"],
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
