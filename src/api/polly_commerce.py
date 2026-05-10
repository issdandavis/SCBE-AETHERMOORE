"""Polly commerce + auto-training surface.

Adds three behaviors on top of the deterministic chat router in
``polly_routes.py``:

1. **Order fulfillment** — when the user expresses buying intent, return the
   exact product + Stripe payment link, not generic pricing copy.

2. **Custom-product builder** — when the user describes a need that doesn't
   match a stock product, surface a "scope a custom build" CTA that points
   at the consulting page (``aethermoore.com/hire``) and an email pre-fill.

3. **Auto-training capture** — every consented conversation turn is appended
   to ``training-data/polly-chat-live/{YYYY-MM}.jsonl`` so the next training
   run can pull live customer interactions as supervised data.

4. **Membership / sign-up CTA** — when the user shows research / repeat-visit
   intent, surface the Ko-fi sponsorship + newsletter signup link.

Design constraints:
- No external secrets required for capture (writes to local disk).
- Every link in the catalog is verified live as of 2026-05-09.
- Intent classification is deterministic regex — no LLM needed for the
  routing layer; the LLM (Gemini / HF) handles the conversational reply
  separately.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

logger = logging.getLogger("scbe.api.polly.commerce")

# ---------------------------------------------------------------------------
# Product catalog — single source of truth for what Polly can sell.
# Keep this in sync with docs/offers/index.html and src/api/stripe_billing.py.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Product:
    """A Polly-sellable product surface."""

    sku: str
    name: str
    price_label: str
    short: str
    checkout_url: str
    delivery_url: str = ""
    keywords: Tuple[str, ...] = field(default_factory=tuple)


PRODUCT_CATALOG: Tuple[Product, ...] = (
    Product(
        sku="scbe-service-credits",
        name="SCBE Service Credits",
        price_label="$5+ pay-as-you-go",
        short=(
            "Small credit top-ups for hosted SCBE routing, governed runs, "
            "reports, and provider/model usage. We pass through compute/model "
            "cost and add only a 2-5% coordination fee where usage is billable."
        ),
        checkout_url="https://ko-fi.com/izdandavis",
        delivery_url="https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html",
        keywords=(
            "credits",
            "service credits",
            "pay as you go",
            "pay-as-you-go",
            "token routing",
            "tokens",
            "usage",
            "hosted run",
            "hosted routing",
            "ollama cloud",
            "cloud models",
        ),
    ),
    Product(
        sku="ai-governance-toolkit",
        name="SCBE AI Governance Toolkit",
        price_label="$29 one-time",
        short=(
            "Templates, decision records, setup guidance, buyer manual, and a "
            "support route for governed AI workflows. Shipped as a downloadable "
            "ZIP after Stripe checkout."
        ),
        checkout_url="https://buy.stripe.com/cNibJ25Ca2TJ9gQ3a6dby06",
        delivery_url="https://aethermoore.com/product-manual/ai-governance-toolkit.html",
        keywords=(
            "toolkit",
            "governance toolkit",
            "ai governance",
            "templates",
            "decision records",
        ),
    ),
    Product(
        sku="ai-security-training-vault",
        name="SCBE AI Security Training Vault",
        price_label="$29 one-time",
        short=(
            "Training data, projector weights, benchmark suite, and notebook "
            "materials for governed AI model work. Shipped as a downloadable "
            "ZIP after Stripe checkout."
        ),
        checkout_url="https://buy.stripe.com/28E8wQ5Cacuj64EaCydby0g",
        delivery_url="https://aethermoore.com/product-manual/training-vault.html",
        keywords=(
            "training vault",
            "training data",
            "vault",
            "ai security",
            "benchmark suite",
            "notebooks",
        ),
    ),
    Product(
        sku="five-dollar-tip-jar",
        name="$5 SCBE Tip Jar",
        price_label="$5 one-time",
        short=(
            "If the open-source work has helped you and there's no formal "
            "engagement, a tip keeps the next release shipping."
        ),
        checkout_url="https://ko-fi.com/izdandavis",
        keywords=(
            "tip",
            "tip jar",
            "donate",
            "donation",
            "support",
            "buy a coffee",
            "coffee",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Consulting / custom-build CTA — when no stock product matches.
# ---------------------------------------------------------------------------


CONSULTING_TIERS: Tuple[Dict[str, str], ...] = (
    {
        "name": "Short advisory call",
        "price": "$300 / 60 min",
        "fit": "one concrete AI safety / governance problem you're facing",
    },
    {
        "name": "Adversarial audit",
        "price": "$5,000 – $15,000 / 1–3 weeks",
        "fit": "audit your production LLM endpoint or agent against the SCBE governance harness",
    },
    {
        "name": "Custom governance overlay",
        "price": "$25,000 – $80,000 / 4–10 weeks",
        "fit": "build a deployable governance layer in front of your model API",
    },
    {
        "name": "Federal subcontract role",
        "price": "$150 – $250 / hour, contract",
        "fit": "AI safety / LLM evaluation work on a SAM-registered prime's contract",
    },
)

CONSULTING_LANDING_URL = "https://aethermoore.com/hire"
HIRE_EMAIL = "issdandavis7795@gmail.com"
MEMBERSHIP_KOFI_URL = "https://ko-fi.com/izdandavis"

SERVICE_CREDITS_POLICY: Dict[str, Any] = {
    "name": "SCBE Service Credits",
    "service_fee_percent_range": [2, 5],
    "minimum_top_up_usd": 5,
    "usage_model": (
        "mostly-free local tools; service credits only pay for hosted routing, "
        "reports, delivery, storage, and provider/model usage"
    ),
    "fee_formula": (
        "customer_charge = actual_provider_cost + " "max(actual_provider_cost * service_fee_percent, small_run_floor)"
    ),
    "preferred_routing": (
        "local/Ollama and deterministic harness first; paid providers only "
        "when the run needs hosted capacity or a customer explicitly requests it"
    ),
}


# ---------------------------------------------------------------------------
# Intent classification — deterministic regex on the user message.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Intent:
    """Result of classifying a user message."""

    name: str
    confidence: float
    matched_term: Optional[str] = None
    product: Optional[Product] = None


_BUY_PATTERN = re.compile(
    r"\b(buy|purchase|order|checkout|pay\s+for|get\s+the|want\s+the|" r"how\s+much|sign\s+me\s+up|add\s+to\s+cart)\b",
    re.IGNORECASE,
)

_CUSTOM_PATTERN = re.compile(
    r"\b(custom|bespoke|tailor|specifically\s+for|my\s+team|my\s+company|"
    r"my\s+org|my\s+(use\s*case|workflow)|something\s+else|not\s+listed|"
    r"build\s+me|hire\s+you|consulting|advisory|audit|engagement|contract)\b",
    re.IGNORECASE,
)

_RESEARCH_PATTERN = re.compile(
    r"\b(research|find|look\s+up|search|investigate|what\s+do\s+you\s+know|"
    r"recent|latest|news|paper|study|literature|sources?|cite|references?)\b",
    re.IGNORECASE,
)

_MEMBERSHIP_PATTERN = re.compile(
    r"\b(member|membership|subscribe|signup|sign\s*up|join|newsletter|"
    r"follow|stay\s+updated|notify|sponsor|tip|donate)\b",
    re.IGNORECASE,
)


def classify_intent(message: str) -> Intent:
    """Classify the dominant intent of a user message.

    Order of precedence (highest first): buy > custom > research > membership.
    Returns ``Intent(name="general", confidence=0.0)`` when nothing matches.
    """
    if not isinstance(message, str) or not message.strip():
        return Intent(name="general", confidence=0.0)

    # Buy intent — try to bind a specific product if a keyword matches.
    buy_match = _BUY_PATTERN.search(message)
    if buy_match:
        product = _resolve_product(message)
        return Intent(
            name="buy",
            confidence=0.95 if product else 0.7,
            matched_term=buy_match.group(0),
            product=product,
        )

    # Bare product keyword without explicit buy verb still surfaces the product.
    product = _resolve_product(message)
    if product is not None:
        return Intent(name="buy", confidence=0.6, matched_term=product.sku, product=product)

    # Custom-build intent.
    custom_match = _CUSTOM_PATTERN.search(message)
    if custom_match:
        return Intent(name="custom", confidence=0.85, matched_term=custom_match.group(0))

    # Research intent.
    research_match = _RESEARCH_PATTERN.search(message)
    if research_match:
        return Intent(name="research", confidence=0.8, matched_term=research_match.group(0))

    # Membership / sponsorship intent.
    membership_match = _MEMBERSHIP_PATTERN.search(message)
    if membership_match:
        return Intent(name="membership", confidence=0.75, matched_term=membership_match.group(0))

    return Intent(name="general", confidence=0.0)


def _resolve_product(message: str) -> Optional[Product]:
    """Return the first product whose keywords appear in the message."""
    lower = message.lower()
    for product in PRODUCT_CATALOG:
        for keyword in product.keywords:
            if keyword in lower:
                return product
    return None


# ---------------------------------------------------------------------------
# Reply rendering — builds the assistant text + structured action links.
# ---------------------------------------------------------------------------


def render_buy_reply(product: Optional[Product]) -> Tuple[str, List[Dict[str, str]]]:
    """Render a buy-intent reply. If product is None, list the catalog."""
    if product is None:
        lines = [
            "Three current products. Click to check out:",
            "",
        ]
        actions: List[Dict[str, str]] = []
        for item in PRODUCT_CATALOG:
            lines.append(f"- **{item.name}** — {item.price_label}. {item.short}")
            actions.append({"label": f"Buy {item.name}", "url": item.checkout_url})
        return "\n".join(lines), actions

    text = f"**{product.name}** — {product.price_label}.\n\n" f"{product.short}\n\n" f"Checkout: {product.checkout_url}"
    if product.delivery_url:
        text += f"\nWhat you get + delivery: {product.delivery_url}"
    actions = [{"label": f"Buy {product.name}", "url": product.checkout_url}]
    if product.delivery_url:
        actions.append({"label": "What's inside", "url": product.delivery_url})
    return text, actions


def render_custom_reply(message: str) -> Tuple[str, List[Dict[str, str]]]:
    """Render a custom-build reply with consulting tiers + email pre-fill."""
    subject = "Custom engagement inquiry — from Polly chat"
    body = (
        f"Hi Issac,\n\n"
        f'I described to Polly: "{message[:300]}"\n\n'
        f"I'd like to discuss:\n"
        f"[ ] Short advisory call ($300, 60 min)\n"
        f"[ ] Adversarial audit\n"
        f"[ ] Custom governance overlay\n"
        f"[ ] Federal subcontract conversation\n\n"
        f"Context:\n\n"
        f"Thanks,\n"
    )
    mailto = f"mailto:{HIRE_EMAIL}" f"?subject={quote(subject)}" f"&body={quote(body)}"

    tier_lines = [f"- **{t['name']}** ({t['price']}) — {t['fit']}" for t in CONSULTING_TIERS]
    text = (
        "What you're describing is custom — not in the stock catalog. "
        "Four ways we can scope it:\n\n"
        + "\n".join(tier_lines)
        + "\n\nFastest path: email with a one-paragraph description of the "
        "outcome you want. I reply same day where I can."
    )
    actions = [
        {"label": "Email Issac with this context", "url": mailto},
        {"label": "Full hire details", "url": CONSULTING_LANDING_URL},
    ]
    return text, actions


def render_membership_reply() -> Tuple[str, List[Dict[str, str]]]:
    """Render a membership / sponsorship CTA."""
    text = (
        "Three ways to stay close to the work:\n\n"
        "- **Use service credits** for pay-as-you-go hosted routing without a big subscription\n"
        "- **Sponsor / tip** the open-source work via Ko-fi\n"
        "- **Watch the GitHub repo** for releases (`Watch -> Custom -> Releases`)\n"
        "- **Email** me at the address below for a private update list\n\n"
        "The target model is mostly free local tools, with credits only used when "
        "a hosted run, report, or provider/model call is needed. Billable usage is "
        "passed through with a small 2-5% SCBE coordination fee."
    )
    actions = [
        {
            "label": "Service credits",
            "url": "https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html",
        },
        {"label": "Top up on Ko-fi", "url": MEMBERSHIP_KOFI_URL},
        {
            "label": "Watch the repo",
            "url": "https://github.com/issdandavis/SCBE-AETHERMOORE",
        },
        {"label": "Email Issac", "url": f"mailto:{HIRE_EMAIL}"},
    ]
    return text, actions


# ---------------------------------------------------------------------------
# Auto-training capture — append consented conversations to a JSONL corpus.
# ---------------------------------------------------------------------------


_TRAIN_CORPUS_DIR_ENV = "POLLY_TRAIN_CORPUS_DIR"
_DEFAULT_TRAIN_CORPUS_DIR = Path(__file__).resolve().parents[2] / "training-data" / "polly-chat-live"


def train_corpus_dir() -> Path:
    """Return the directory where live training corpus shards are written."""
    override = os.environ.get(_TRAIN_CORPUS_DIR_ENV, "").strip()
    if override:
        return Path(override)
    return _DEFAULT_TRAIN_CORPUS_DIR


def append_training_record(
    *,
    consent: bool,
    user_message: str,
    assistant_reply: str,
    intent: str,
    page_context: Optional[str] = None,
    feedback: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Optional[Path]:
    """Append one conversation turn to the live training corpus.

    Returns the path written to, or ``None`` if consent was not granted or the
    write failed. Never raises — training capture must not break the chat path.
    """
    if not consent:
        return None
    if not isinstance(user_message, str) or not user_message.strip():
        return None
    if not isinstance(assistant_reply, str) or not assistant_reply.strip():
        return None

    corpus_dir = train_corpus_dir()
    try:
        corpus_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("polly training corpus dir create failed: %s", exc)
        return None

    shard_name = f"{time.strftime('%Y-%m')}.jsonl"
    shard = corpus_dir / shard_name

    record: Dict[str, Any] = {
        "ts": int(time.time()),
        "session_id": session_id or "",
        "intent": intent,
        "user": user_message[:4096],
        "assistant": assistant_reply[:8192],
    }
    if page_context:
        record["page_context"] = page_context[:512]
    if feedback in ("up", "down"):
        record["feedback"] = feedback

    try:
        with shard.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("polly training corpus write failed: %s", exc)
        return None

    return shard


__all__ = [
    "Product",
    "PRODUCT_CATALOG",
    "CONSULTING_TIERS",
    "SERVICE_CREDITS_POLICY",
    "CONSULTING_LANDING_URL",
    "HIRE_EMAIL",
    "MEMBERSHIP_KOFI_URL",
    "Intent",
    "classify_intent",
    "render_buy_reply",
    "render_custom_reply",
    "render_membership_reply",
    "train_corpus_dir",
    "append_training_record",
]
