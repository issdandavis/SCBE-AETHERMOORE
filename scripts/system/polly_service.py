"""Polly Service — Route-first AI assistant backend for aethermoore.com.

Handles chat, search, delegation, and context for the Polly sidebar assistant.
Falls back to keyword-based deterministic responses when no LLM is available.
"""

from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _env_get(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
#  Lore & Knowledge Base
# ---------------------------------------------------------------------------

POLLY_LORE = """
You are Polly, the route-first operator for SCBE-AETHERMOORE (aethermoore.com).
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
#  Intent Classification (Deterministic)
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
#  LLM Enhancement (Gemini)
# ---------------------------------------------------------------------------

async def enhance_with_gemini(user_text: str, intent: str, route: str) -> Optional[str]:
    """Use Gemini to enhance the response if API key is available."""
    api_key = _env_get("GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        import httpx

        prompt = f"""You are Polly, a helpful and concise assistant for SCBE-AETHERMOORE (an AI governance company).

User message: {user_text}
Detected intent: {intent}
Suggested route: {route}

Respond in 1-2 sentences. Be direct, plain-spoken, and operational. Never use hype or marketing language. If you don't know something, say so."""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 200, "temperature": 0.3},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return text.strip() if text else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
#  Main Service Functions
# ---------------------------------------------------------------------------

async def chat(message: str, context: str = "site") -> dict:
    """Handle a chat message and return a response."""
    intent_key, intent_data = classify_intent(message)

    # Try Gemini enhancement
    enhanced = await enhance_with_gemini(message, intent_key, intent_data.get("route", ""))
    response_text = enhanced or intent_data["response"]

    return {
        "response": response_text,
        "intent": intent_key,
        "route": intent_data.get("route", "/assistant.html"),
        "context": context,
        "enhanced": enhanced is not None,
    }


async def respond(text: str, context: str = "site", intent: str = "") -> dict:
    """Alternative response endpoint (used by some Polly clients)."""
    result = await chat(text, context)
    return {
        "text": result["response"],
        "intent": result["intent"],
        "route": result["route"],
    }


async def get_context() -> dict:
    """Return backend capabilities and context."""
    return {
        "capabilities": ["chat", "search", "route", "delegate"],
        "version": "1.0.0",
        "model": "deterministic+gemini-fallback",
        "lore_hash": hash(POLLY_LORE) & 0xFFFFFFFF,
    }


async def search(query: str) -> dict:
    """Simple search proxy — returns intent-classified results."""
    intent_key, intent_data = classify_intent(query)
    return {
        "query": query,
        "intent": intent_key,
        "route": intent_data.get("route", ""),
        "results": [{"title": intent_data.get("response", "")[:80], "url": intent_data.get("route", "")}],
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
