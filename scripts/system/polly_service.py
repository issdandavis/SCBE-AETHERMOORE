"""Polly Service — Route-first AI assistant backend for aethermoore.com.

Handles chat, search, delegation, email, Slack, and deep reasoning for the Polly sidebar.
Uses Gemini as the primary reasoning engine with deterministic keyword fallback.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional


def _env_get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
#  Lore & Knowledge Base
# ---------------------------------------------------------------------------

POLLY_LORE = """You are Polly, the route-first operator for SCBE-AETHERMOORE (aethermoore.com).
Your first job is to identify intent and point people to the correct surface before adding extra reasoning.

CRITICAL RULE: Only recommend products that are listed below. NEVER invent products, prices, features, or URLs.

=== SOLUTIONS ===
A. CX Refund Guardrail — $500-5K/month SaaS. Page: /cx-guardrail.html
B. ISO 42001 Evidence-as-a-Service — $50-150K/year. Page: /iso-42001.html
C. AI Red Team as a Service — $5-50K/engagement. Page: /red-team.html

=== PRODUCTS ===
1. AI Governance Toolkit — $29 one-time. Buy: Stripe link. Manual: /product-manual/ai-governance-toolkit.html
2. HYDRA Agent Templates — $29 one-time.
3. n8n Workflow Pack — $29 one-time.
4. Content Spin Engine — $29 one-time.
5. The Six Tongues Protocol (Novel) — Amazon KDP.
6. Training Data — /datasets.html

=== OPEN SOURCE ===
- SCBE-AETHERMOORE (main framework): github.com/issdandavis/SCBE-AETHERMOORE
- 9 repos total, MIT licensed

=== SITE ROUTES ===
- /assistant.html — Front desk
- /tools.html — Live action tools
- /support.html — Recovery
- /product-manual/ — Buyer guides
- /research/ — Benchmarks and evidence
- /book.html — Narrative teaching
- /demos/ — Interactive visualizations
- /arena.html — AI debate arena
- /members/ — Exclusive research (gated)

=== CONTACT ===
- Email: issac@aethermoorgames.com
- Built by Issac Davis in Port Angeles, WA
"""


# ---------------------------------------------------------------------------
#  Intent Classification (Deterministic Fallback)
# ---------------------------------------------------------------------------

INTENT_PATTERNS = {
    "pricing": {
        "patterns": [r"price", r"cost", r"how much", r"pricing", r"\$\d+", r"monthly", r"subscription", r"fee"],
        "response": "Our solutions range from $29 one-time products to $150K/year enterprise services. See the full pricing grid at https://aethermoore.com/pricing.html",
        "route": "/pricing.html",
    },
    "cx_guardrail": {
        "patterns": [r"refund", r"guardrail", r"cx", r"customer support", r"chatbot liability", r"moffatt", r"policy enforcement"],
        "response": "The CX Refund Guardrail stops chatbots from promising refunds they can't deliver. It's policy-enforcement middleware between your LLM and customer. $500-5K/month. https://aethermoore.com/cx-guardrail.html",
        "route": "/cx-guardrail.html",
    },
    "iso_42001": {
        "patterns": [r"iso.?42001", r"audit", r"compliance", r"regulatory", r"eu ai act", r"sr 11-7", r"governance framework"],
        "response": "ISO 42001 Evidence-as-a-Service provides adversarial testing, risk reports, drift monitoring, and audit response dossiers. $50-150K/year. https://aethermoore.com/iso-42001.html",
        "route": "/iso-42001.html",
    },
    "red_team": {
        "patterns": [r"red team", r"penetration", r"adversarial", r"attack", r"security test", r"vulnerability", r"threat"],
        "response": "AI Red Team as a Service runs 6,000+ adversarial tests against your LLM application. Branded PDF report and remediation roadmap. $5-50K/engagement. https://aethermoore.com/red-team.html",
        "route": "/red-team.html",
    },
    "datasets": {
        "patterns": [r"dataset", r"training data", r"sft", r"corpus", r"prompt pack", r"adversarial prompts"],
        "response": "We sell training datasets including the Governance SFT Pack ($99), Red Team Fortress ($149), and The Full Arsenal bundle ($399). https://aethermoore.com/datasets.html",
        "route": "/datasets.html",
    },
    "contact": {
        "patterns": [r"contact", r"email", r"reach out", r"talk to", r"schedule", r"book a call", r"get in touch"],
        "response": "Email me directly at issac@aethermoorgames.com or use the contact form at https://aethermoore.com/contact.html. I usually reply within 24 hours.",
        "route": "/contact.html",
    },
    "support": {
        "patterns": [r"help", r"support", r"broken", r"missing", r"delivery", r"refund", r"issue", r"problem"],
        "response": "For support with purchases, delivery, or broken links, visit https://aethermoore.com/support.html or email issac@aethermoorgames.com.",
        "route": "/support.html",
    },
    "tools": {
        "patterns": [r"tool", r"calculator", r"demo", r"interactive", r"browser tool", r"visualization"],
        "response": "Our live browser tools and interactive demos are at https://aethermoore.com/demos/index.html. No install needed.",
        "route": "/demos/index.html",
    },
    "research": {
        "patterns": [r"research", r"benchmark", r"evidence", r"paper", r"study", r"proof", r"technical"],
        "response": "Benchmarks, proofs, and technical justification are at https://aethermoore.com/research/index.html. Member-only raw notes are at https://aethermoore.com/members/research-notes.html",
        "route": "/research/index.html",
    },
    "members": {
        "patterns": [r"member", r"exclusive", r"insider", r"gated", r"research notes", r"early access"],
        "response": "Members get raw research notes, early datasets, and member-only tools. Join SCBE Weekly to get the access PIN. https://aethermoore.com/members/",
        "route": "/members/",
    },
    "open_source": {
        "patterns": [r"github", r"open source", r"repo", r"code", r"npm", r"pypi", r"install"],
        "response": "The framework is MIT-licensed and split across 9 repos. Main repo: github.com/issdandavis/SCBE-AETHERMOORE. npm install scbe-aethermoore",
        "route": "https://github.com/issdandavis/SCBE-AETHERMOORE",
    },
    "book": {
        "patterns": [r"book", r"novel", r"story", r"six tongues", r"fiction", r"read"],
        "response": "The Six Tongues Protocol is a 70K-word novel that teaches the SCBE framework through story. Available on Amazon KDP.",
        "route": "https://www.amazon.com/dp/B0F28PHSPR",
    },
    "greeting": {
        "patterns": [r"^hi\b", r"^hello\b", r"^hey\b", r"^howdy\b"],
        "response": "Hey. I'm Polly, the route-first operator for SCBE-AETHERMOORE. Tell me what you're looking for — pricing, products, research, support, or something else — and I'll point you to the right page.",
        "route": "/assistant.html",
    },
}


def classify_intent(text: str) -> tuple[str, dict]:
    """Classify user text into an intent. Returns (intent_key, intent_data)."""
    text_lower = text.lower().strip()
    for intent_key, data in INTENT_PATTERNS.items():
        for pattern in data["patterns"]:
            if re.search(pattern, text_lower):
                return intent_key, data
    return "unknown", {
        "response": "I'm not sure I understood. I can help with pricing, products, support, research, or point you to the right page. What are you looking for?",
        "route": "/assistant.html",
    }


# ---------------------------------------------------------------------------
#  Gemini LLM Integration
# ---------------------------------------------------------------------------

# Multi-provider LLM support
LLM_CONFIGS = [
    ("GEMINI_API_KEY", "gemini-1.5-flash", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}", "google"),
    ("OPENAI_API_KEY", "gpt-4o-mini", "https://api.openai.com/v1/chat/completions", "openai"),
    ("GROQ_API_KEY", "llama-3.1-8b-instant", "https://api.groq.com/openai/v1/chat/completions", "openai"),
    ("ANTHROPIC_API_KEY", "claude-3-haiku-20240307", "https://api.anthropic.com/v1/messages", "anthropic"),
]

async def _llm_generate(
    system_prompt: str,
    user_text: str,
    max_tokens: int = 400,
    temperature: float = 0.4,
) -> Optional[tuple[str, str]]:
    """Try multiple LLM providers until one works. Returns (text, provider_name)."""
    import httpx

    for env_key, model, url_template, provider_type in LLM_CONFIGS:
        api_key = _env_get(env_key, "")
        if not api_key:
            continue

        try:
            url = url_template.format(model=model, key=api_key) if "{key}" in url_template else url_template
            headers = {"Content-Type": "application/json"}
            payload: dict[str, Any] = {}

            if provider_type == "google":
                payload = {
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
                }
            elif provider_type == "openai":
                headers["Authorization"] = f"Bearer {api_key}"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            elif provider_type == "anthropic":
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
                payload = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_text}],
                }

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code != 200:
                    continue
                data = resp.json()

                text = ""
                if provider_type == "google":
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                elif provider_type == "openai":
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                elif provider_type == "anthropic":
                    text = data.get("content", [{}])[0].get("text", "")

                if text:
                    return text.strip(), provider_type
        except Exception:
            continue

    return None


async def generate_response(message: str, thinking: bool = False) -> dict:
    """Primary response generator using Gemini with lore grounding."""
    intent_key, intent_data = classify_intent(message)
    route = intent_data.get("route", "/assistant.html")

    mode_label = "DEEP THINKING" if thinking else "STANDARD"
    mode_instruction = (
        "Think step by step. Analyze the user's request carefully, identify the domain, then provide a thorough, well-reasoned response. Use 2-4 paragraphs."
        if thinking else
        "Be concise and direct. Route first, explain second. Use 1-2 sentences for simple questions, 1 short paragraph for complex ones."
    )
    system = f"""{POLLY_LORE}

You are operating in {mode_label} mode.
{mode_instruction}

You have access to:
- Web search (Tavily)
- Email sending (Proton SMTP to issac@aethermoorgames.com)
- Slack notifications
- Site routing and product knowledge

If the user asks you to send an email, schedule something, or notify someone, say you can do it and ask for the details you need.
If you don't know something, say "I don't have that" — never invent.
"""

    llm_result = await _llm_generate(system, message, max_tokens=800 if thinking else 400)

    if llm_result:
        llm_text, provider = llm_result
        return {
            "response": llm_text,
            "intent": intent_key,
            "route": route,
            "enhanced": True,
            "model": provider,
        }

    # Fallback to deterministic response
    return {
        "response": intent_data["response"],
        "intent": intent_key,
        "route": route,
        "enhanced": False,
        "model": "deterministic",
    }


# ---------------------------------------------------------------------------
#  Web Search (Tavily)
# ---------------------------------------------------------------------------

TAVILY_API_KEY = _env_get("TAVILY_API_KEY", "")

async def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web using Tavily API (free tier: 1000 req/month)."""
    if not TAVILY_API_KEY:
        return {"query": query, "results": [], "error": "TAVILY_API_KEY not configured"}

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": True,
                },
            )
            if resp.status_code != 200:
                return {"query": query, "results": [], "error": f"Tavily HTTP {resp.status_code}"}

            data = resp.json()
            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:300],
                })

            return {
                "query": query,
                "answer": data.get("answer", ""),
                "results": results,
                "source": "tavily",
            }
    except Exception as e:
        return {"query": query, "results": [], "error": str(e)}


# ---------------------------------------------------------------------------
#  Email via Proton SMTP
# ---------------------------------------------------------------------------

async def send_email_from_chat(to: str, subject: str, body: str) -> dict:
    """Send an email using the existing Proton SMTP service."""
    try:
        from scripts.system.email_service import send_contact_notification
        result = send_contact_notification(
            name="Polly Assistant",
            email=to,
            subject=subject,
            message=body,
            page="polly-chat",
        )
        return {"ok": result["ok"], "message": result.get("message", "Sent"), "error": result.get("error")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
#  Slack Webhook
# ---------------------------------------------------------------------------

SLACK_WEBHOOK_URL = _env_get("SLACK_WEBHOOK_URL", "")

async def notify_slack(message: str, channel: Optional[str] = None) -> dict:
    """Send a notification to Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        return {"ok": False, "error": "SLACK_WEBHOOK_URL not configured"}

    try:
        import httpx
        payload = {"text": f"🤖 Polly: {message}"}
        if channel:
            payload["channel"] = channel

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(SLACK_WEBHOOK_URL, json=payload)
            if resp.status_code == 200:
                return {"ok": True, "message": "Slack notification sent"}
            return {"ok": False, "error": f"Slack HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
#  Legacy Service Interface (API-compatible)
# ---------------------------------------------------------------------------

async def chat(message: str, context: str = "site", thinking: bool = False) -> dict:
    """Handle a chat message and return a response."""
    result = await generate_response(message, thinking=thinking)
    result["context"] = context
    return result


async def respond(text: str, context: str = "site", intent: str = "", thinking: bool = False) -> dict:
    """Alternative response endpoint (used by some Polly clients)."""
    result = await chat(text, context, thinking=thinking)
    return {
        "text": result["response"],
        "intent": result["intent"],
        "route": result["route"],
        "enhanced": result.get("enhanced", False),
    }


async def get_context() -> dict:
    """Return backend capabilities and context."""
    return {
        "capabilities": ["chat", "search", "route", "delegate", "email", "slack", "thinking"],
        "version": "2.0.0",
        "model": "multi-llm+deterministic-fallback",
        "lore_hash": hash(POLLY_LORE) & 0xFFFFFFFF,
        "services": {
            "gemini": bool(_env_get("GEMINI_API_KEY")),
            "openai": bool(_env_get("OPENAI_API_KEY")),
            "groq": bool(_env_get("GROQ_API_KEY")),
            "anthropic": bool(_env_get("ANTHROPIC_API_KEY")),
            "tavily": bool(TAVILY_API_KEY),
            "slack": bool(SLACK_WEBHOOK_URL),
            "email": True,
        },
    }


async def search(query: str) -> dict:
    """Search proxy — uses Tavily if available, falls back to intent routing."""
    tavily_result = await web_search(query)
    if tavily_result.get("results"):
        return {"ok": True, "data": tavily_result}

    # Fallback to intent-classified results
    intent_key, intent_data = classify_intent(query)
    return {
        "ok": True,
        "data": {
            "query": query,
            "intent": intent_key,
            "route": intent_data.get("route", ""),
            "results": [{"title": intent_data.get("response", "")[:80], "url": intent_data.get("route", "")}],
            "source": "intent",
        },
    }


async def delegate(text: str) -> dict:
    """Delegation endpoint — routes to appropriate handler."""
    intent_key, intent_data = classify_intent(text)
    return {
        "intent": intent_key,
        "route": intent_data.get("route", "/assistant.html"),
        "action": "route",
        "confidence": 0.9 if intent_key != "unknown" else 0.3,
    }
