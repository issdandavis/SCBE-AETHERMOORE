"""
Polly v2 API routes for SCBE-AETHERMOORE.

Public-facing assistant endpoints — no SCBE API key required.
Services (Gemini, Tavily, Email, Slack) are enabled by environment variables.
"""

from __future__ import annotations

import json
import logging
import os
import re
import smtplib
import ssl
import time
from email.message import EmailMessage
from typing import Any, Dict, List, Optional
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("scbe.api.polly")

polly_router = APIRouter(prefix="/v1/polly", tags=["polly"])

# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

ENV_FILE = os.path.join(os.path.dirname(__file__), "../../config/connector_oauth/.env.connector.oauth")
_env_loaded = False


def _load_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip("\"'")
                    if k and v:
                        os.environ.setdefault(k, v)


def _gemini_key() -> Optional[str]:
    _load_env()
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _tavily_key() -> Optional[str]:
    _load_env()
    return os.environ.get("TAVILY_API_KEY")


def _slack_url() -> Optional[str]:
    _load_env()
    return os.environ.get("SLACK_WEBHOOK_URL")


def _smtp_user() -> str:
    _load_env()
    return os.environ.get("PROTONMAIL_SMTP_USER", "")


def _smtp_pass() -> str:
    _load_env()
    return os.environ.get("PROTONMAIL_SMTP_TOKEN", "")


def _smtp_host() -> str:
    _load_env()
    return os.environ.get("PROTONMAIL_SMTP_HOST", "smtp.protonmail.ch")


def _smtp_port() -> int:
    _load_env()
    return int(os.environ.get("PROTONMAIL_SMTP_PORT", "587"))


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., max_length=8192)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    thinking: bool = Field(default=False, description="Enable step-by-step reasoning mode (Gemini)")
    history: List[ChatMessage] = Field(default_factory=list, max_length=20)
    page_context: Optional[str] = Field(default=None, max_length=512)


class ChatResponse(BaseModel):
    response: str
    route: str
    thinking: bool
    model: str
    ts: int


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)


class SearchResult(BaseModel):
    title: str
    url: str
    excerpt: str


class SearchResponse(BaseModel):
    results: List[SearchResult]
    source: str
    query: str
    ts: int


class EmailRequest(BaseModel):
    to: str = Field(..., min_length=3, max_length=320)
    subject: str = Field(..., min_length=1, max_length=512)
    body: str = Field(..., min_length=1, max_length=8192)
    reply_to: Optional[str] = Field(default=None, max_length=320)

    @field_validator("to", "reply_to")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email address")
        return v


class EmailResponse(BaseModel):
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class SlackRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    channel: Optional[str] = Field(default=None, max_length=128)


class SlackResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class ContextResponse(BaseModel):
    gemini: bool
    tavily: bool
    email: bool
    slack: bool


# ---------------------------------------------------------------------------
# Deterministic chat routing
# ---------------------------------------------------------------------------

_ROUTE_PATTERNS: List[tuple[str, str, str]] = [
    # (pattern, route_name, response_template)
    (
        r"\b(price|pricing|cost|buy|purchase|plan|tier|subscription|paid|free)\b",
        "pricing",
        "SCBE-AETHERMOORE is available in several tiers — from a free community edition to enterprise plans "
        "with full 14-layer pipeline access, PQC cryptography, and multi-agent fleet support. "
        "Visit https://aethermoore.com/#pricing for current pricing or email us for a custom quote.",
    ),
    (
        r"\b(error|bug|broken|fail|crash|exception|traceback|not working|issue|problem|help)\b",
        "support",
        "I'm here to help. Please share the exact error message, the command or page where it occurred, "
        "your OS and Python/Node version, and what you expected to happen. "
        "You can also email support@aethermoore.com or open a GitHub issue at "
        "https://github.com/issdandavis/SCBE-AETHERMOORE/issues.",
    ),
    (
        r"\b(hyperbolic|poincar[eé]|geodesic|manifold|curvature|geometry|pipeline|layer|axiom|harmonic|scbe|governance)\b",
        "science",
        "SCBE uses a 14-layer harmonic pipeline built on Poincaré ball geometry. "
        "Adversarial intent scales exponentially in hyperbolic space, making attacks computationally "
        "infeasible. The five quantum axioms (Unitarity, Locality, Causality, Symmetry, Composition) "
        "govern each layer. See LAYER_INDEX.md and SPEC.md in the repo for the full technical reference.",
    ),
    (
        r"\b(lore|story|aethermoore|world|character|polly|sacre[d]?\s*tongue|tongue|raven|canon)\b",
        "lore",
        "AetherMoore is the fictional world layered over the SCBE governance stack. "
        "Polly is the AI companion who navigates both the technical system and the story canon. "
        "The Sacred Tongues (KO, AV, RU, CA, UM, DR) are the six linguistic dimensions of the "
        "tokenizer, each weighted by the golden ratio. Ask me about a specific character, event, "
        "or tongue to go deeper.",
    ),
    (
        r"\b(train|training|fine.?tun|sft|dataset|model|qlora|lora|hug.?ging\s*face|hf|corpus)\b",
        "training",
        "SCBE supports SFT (supervised fine-tuning) and DPO datasets. Training data lives in "
        "training-data/ and is managed by the Apollo pipeline. You can generate SFT pairs from "
        "the codebase with `python scripts/codebase_to_sft.py` or run the HuggingFace training loop "
        "via `python scripts/hf_training_loop.py`. QLoRA notebooks are in notebooks/.",
    ),
    (
        r"\b(install|setup|start|run|docker|deploy|quickstart|get\s+started)\b",
        "setup",
        "Quick start: clone the repo, run `npm install && npm run build` for TypeScript, "
        "and `pip install -r requirements.txt` for Python. Spin up the API with "
        "`uvicorn src.api.main:app --reload`. For Docker: `npm run docker:compose`. "
        "See docs/RUNBOOK.md for the full deployment guide.",
    ),
    (
        r"\b(contact|email|reach|support|team|human|person|owner)\b",
        "contact",
        "You can reach the SCBE team at issdandavis@gmail.com or open an issue at "
        "https://github.com/issdandavis/SCBE-AETHERMOORE/issues. "
        "For enterprise inquiries use the contact form at https://aethermoore.com/contact.html.",
    ),
]


def _deterministic_route(message: str) -> tuple[str, str]:
    """Return (route_name, response) for a message using keyword matching."""
    lower = message.lower()
    for pattern, route, response in _ROUTE_PATTERNS:
        if re.search(pattern, lower):
            return route, response
    return (
        "general",
        f"I'm Polly, the SCBE-AETHERMOORE assistant. I can answer questions about the "
        f"14-layer governance pipeline, Sacred Tongues tokenizer, training data, lore, "
        f"pricing, and setup. What would you like to know?\n\n"
        f"(Tip: add a GEMINI_API_KEY on the server to unlock deep reasoning mode.)",
    )


async def _gemini_chat(message: str, history: List[ChatMessage], page_context: Optional[str]) -> str:
    """Call Gemini for thinking-mode responses. Returns text or raises."""
    api_key = _gemini_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    try:
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        system = (
            "You are Polly, the AI assistant for SCBE-AETHERMOORE — an AI safety and governance "
            "framework using hyperbolic geometry. Think step-by-step and be concise but thorough. "
            "Focus on the user's specific question."
        )
        if page_context:
            system += f"\n\nPage context: {page_context}"

        parts = [system]
        for msg in history[-6:]:
            parts.append(f"{msg.role.upper()}: {msg.content}")
        parts.append(f"USER: {message}")
        parts.append("ASSISTANT (think step-by-step):")

        resp = model.generate_content(
            "\n\n".join(parts),
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        return getattr(resp, "text", None) or "[empty Gemini response]"
    except Exception as exc:
        logger.warning("Gemini chat error: %s", exc)
        raise RuntimeError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@polly_router.get("/context", response_model=ContextResponse, summary="Service availability")
async def polly_context() -> ContextResponse:
    """Return which backend services are configured and available."""
    return ContextResponse(
        gemini=bool(_gemini_key()),
        tavily=bool(_tavily_key()),
        email=bool(_smtp_user() and _smtp_pass()),
        slack=bool(_slack_url()),
    )


@polly_router.post("/chat", response_model=ChatResponse, summary="Chat with Polly")
async def polly_chat(req: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with routing and optional thinking mode.

    - When ``thinking=True`` and GEMINI_API_KEY is set, Polly uses Gemini for
      step-by-step reasoning.
    - Otherwise a deterministic router handles common query types (pricing,
      support, science, lore, training, setup, contact).
    """
    if req.thinking and _gemini_key():
        try:
            text = await _gemini_chat(req.message, req.history, req.page_context)
            return ChatResponse(
                response=text,
                route="gemini-thinking",
                thinking=True,
                model="gemini-1.5-flash",
                ts=int(time.time()),
            )
        except RuntimeError as exc:
            logger.warning("Gemini fallback to deterministic: %s", exc)

    route, response = _deterministic_route(req.message)
    return ChatResponse(
        response=response,
        route=route,
        thinking=False,
        model="polly-deterministic",
        ts=int(time.time()),
    )


@polly_router.post("/search", response_model=SearchResponse, summary="Web search")
async def polly_search(req: SearchRequest) -> SearchResponse:
    """
    Web search via Tavily (if TAVILY_API_KEY is set) or a no-op fallback.
    """
    query = req.query.strip()

    tavily_key = _tavily_key()
    if tavily_key:
        try:
            payload = json.dumps(
                {"api_key": tavily_key, "query": query, "search_depth": "basic", "max_results": 5}
            ).encode()
            http_req = urlrequest.Request(
                "https://api.tavily.com/search",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlrequest.urlopen(http_req, timeout=10) as resp:
                data: Dict[str, Any] = json.loads(resp.read().decode())

            raw_results = data.get("results", [])
            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    excerpt=r.get("content", "")[:300],
                )
                for r in raw_results[:5]
            ]
            return SearchResponse(results=results, source="tavily", query=query, ts=int(time.time()))
        except (HTTPError, URLError, Exception) as exc:
            logger.warning("Tavily search error: %s", exc)

    # Fallback: inform the client no search backend is available.
    return SearchResponse(
        results=[
            SearchResult(
                title=f"Search: {query}",
                url=f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                excerpt=(
                    "No Tavily API key is configured. Click the link to search DuckDuckGo directly, "
                    "or add TAVILY_API_KEY to the server environment."
                ),
            )
        ],
        source="fallback",
        query=query,
        ts=int(time.time()),
    )


@polly_router.post("/email", response_model=EmailResponse, summary="Send email")
async def polly_email(req: EmailRequest) -> EmailResponse:
    """
    Send an email via configured Proton SMTP.

    Requires ``PROTONMAIL_SMTP_USER`` and ``PROTONMAIL_SMTP_TOKEN`` environment
    variables (loaded from config/connector_oauth/.env.connector.oauth).
    """
    user = _smtp_user()
    password = _smtp_pass()
    if not user or not password:
        return EmailResponse(ok=False, error="SMTP credentials not configured on the server")

    msg = EmailMessage()
    msg["Subject"] = req.subject
    msg["From"] = user
    msg["To"] = req.to
    if req.reply_to:
        msg["Reply-To"] = req.reply_to
    msg.set_content(req.body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(_smtp_host(), _smtp_port(), timeout=30) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)
        return EmailResponse(ok=True, message_id=msg.get("Message-ID") or "sent")
    except Exception as exc:
        logger.exception("Polly email send failed")
        return EmailResponse(ok=False, error=str(exc))


@polly_router.post("/slack", response_model=SlackResponse, summary="Send Slack notification")
async def polly_slack(req: SlackRequest) -> SlackResponse:
    """
    Post a message to Slack via an incoming webhook.

    Requires ``SLACK_WEBHOOK_URL`` environment variable.
    """
    webhook = _slack_url()
    if not webhook:
        return SlackResponse(ok=False, error="SLACK_WEBHOOK_URL not configured on the server")

    payload: Dict[str, Any] = {"text": req.text}
    if req.channel:
        payload["channel"] = req.channel

    try:
        data = json.dumps(payload).encode()
        http_req = urlrequest.Request(
            webhook,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlrequest.urlopen(http_req, timeout=10) as resp:
            body = resp.read().decode()
        if body.strip().lower() != "ok":
            return SlackResponse(ok=False, error=f"Slack returned: {body[:200]}")
        return SlackResponse(ok=True)
    except HTTPError as exc:
        err = f"Slack HTTP {exc.code}: {exc.read().decode()[:200]}"
        logger.warning("Polly Slack error: %s", err)
        return SlackResponse(ok=False, error=err)
    except Exception as exc:
        logger.exception("Polly Slack send failed")
        return SlackResponse(ok=False, error=str(exc))
