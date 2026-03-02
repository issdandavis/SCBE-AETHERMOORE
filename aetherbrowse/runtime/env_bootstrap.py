"""
AetherBrowse Runtime Environment Bootstrap
========================================

Loads environment variables for runtime components and normalizes common
connector/API aliases into canonical names expected by runtime code.

This keeps one place where token key variants are resolved, so shell env,
`.env` files, and older naming conventions all work without manual key mapping.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("aetherbrowse-env-bootstrap")

_BOOTSTRAPPED = False


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    # Keep explicit env vars as source of truth; never override existing values.
    load_dotenv(path, override=False)
    logger.debug("Loaded env file: %s", path)


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _copy_alias(canonical: str, aliases: tuple[str, ...]) -> None:
    if os.getenv(canonical):
        return
    value = _first_env(*aliases)
    if value:
        os.environ[canonical] = value
        logger.debug("Set %s from alias key (value redacted)", canonical)


def bootstrap_runtime_env() -> None:
    """
    Prepare the process environment for AetherBrowse runtime.
    Safe to call multiple times.
    """
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    root = Path(__file__).resolve().parent.parent.parent
    # Load project env files (if dotenv is available)
    _load_dotenv_file(root / ".env")
    _load_dotenv_file(root / ".env.local")

    # Canonical -> aliases
    aliases: dict[str, tuple[str, ...]] = {
        # Core auth
        "HF_TOKEN": (
            "HF_TOKEN",
            "HUGGINGFACE_TOKEN",
            "HUGGING_FACE_HUB_TOKEN",
            "HF_HUB_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
            "HUGGINGFACE_API_KEY",
            "HF_API_KEY",
        ),
        "NOTION_TOKEN": (
            "NOTION_TOKEN",
            "NOTION_API_KEY",
            "NOTION_AUTH_TOKEN",
        ),
        "AIRTABLE_TOKEN": (
            "AIRTABLE_TOKEN",
            "AIRTABLE_API_KEY",
            "AIRTABLE_SECRET",
            "AIRTABLE_ACCESS_TOKEN",
        ),
        "GITHUB_TOKEN": (
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "GITHUB_PAT",
        ),
        "SHOPIFY_ACCESS_TOKEN": (
            "SHOPIFY_ACCESS_TOKEN",
            "SHOPIFY_API_TOKEN",
            "SHOPIFY_TOKEN",
            "SHOPIFY_PRIVATE_APP_TOKEN",
        ),
        "STRIPE_API_KEY": (
            "STRIPE_API_KEY",
            "STRIPE_SECRET_KEY",
            "STRIPE_SK",
        ),
        "STRIPE_CONNECTOR_WEBHOOK_URL": (
            "STRIPE_CONNECTOR_WEBHOOK_URL",
            "STRIPE_WEBHOOK_URL",
            "STRIPE_WEBHOOK",
        ),
        "LINEAR_API_KEY": ("LINEAR_API_KEY", "LINEAR_TOKEN"),
        "ASANA_PAT": ("ASANA_PAT", "ASANA_ACCESS_TOKEN"),
        "SLACK_CONNECTOR_WEBHOOK_URL": (
            "SLACK_CONNECTOR_WEBHOOK_URL",
            "SLACK_WEBHOOK_URL",
            "SLACK_WEBHOOK",
        ),
        "DISCORD_CONNECTOR_WEBHOOK_URL": (
            "DISCORD_CONNECTOR_WEBHOOK_URL",
            "DISCORD_WEBHOOK_URL",
            "DISCORD_WEBHOOK",
        ),
        "N8N_CONNECTOR_WEBHOOK_URL": (
            "N8N_CONNECTOR_WEBHOOK_URL",
            "N8N_WEBHOOK_URL",
            "N8N_WEBHOOK",
        ),
        "NOTION_CONNECTOR_WEBHOOK_URL": (
            "NOTION_CONNECTOR_WEBHOOK_URL",
            "NOTION_WEBHOOK_URL",
            "NOTION_WEBHOOK",
        ),
        "AIRTABLE_CONNECTOR_WEBHOOK_URL": (
            "AIRTABLE_CONNECTOR_WEBHOOK_URL",
            "AIRTABLE_WEBHOOK_URL",
            "AIRTABLE_WEBHOOK",
        ),
        "HF_CONNECTOR_WEBHOOK_URL": (
            "HF_CONNECTOR_WEBHOOK_URL",
            "HUGGINGFACE_CONNECTOR_WEBHOOK_URL",
        ),
        "TELEGRAM_CONNECTOR_WEBHOOK_URL": (
            "TELEGRAM_CONNECTOR_WEBHOOK_URL",
            "SCBE_TELEGRAM_WEBHOOK_URL",
            "TELEGRAM_WEBHOOK_URL",
        ),
        "TELEGRAM_BOT_TOKEN": (
            "TELEGRAM_BOT_TOKEN",
            "SCBE_TELEGRAM_BOT_TOKEN",
            "BOT_TOKEN",
            "TELEGRAM_TOKEN",
            "SCBE_BOT_TOKEN",
        ),
        "TELEGRAM_CHAT_ID": (
            "TELEGRAM_CHAT_ID",
            "SCBE_TELEGRAM_CHAT_ID",
            "TELEGRAM_CHAT",
            "CHAT_ID",
            "TELEGRAM_TO_CHAT_ID",
        ),
        "SCBE_TELEGRAM_WEBHOOK_URL": (
            "SCBE_TELEGRAM_WEBHOOK_URL",
            "TELEGRAM_CONNECTOR_WEBHOOK_URL",
            "TELEGRAM_WEBHOOK_URL",
        ),
        "GITHUB_ACTIONS_CONNECTOR_URL": (
            "GITHUB_ACTIONS_CONNECTOR_URL",
            "GITHUB_ACTIONS_WEBHOOK_URL",
            "GITHUB_ACTIONS_HOOK",
        ),
        "GUMROAD_API_TOKEN": (
            "GUMROAD_API_TOKEN",
            "GUMROAD_ACCESS_TOKEN",
            "GUMROAD_TOKEN",
        ),
        "HF_DEFAULT_REPO": (
            "HF_DEFAULT_REPO",
            "HF_REPO_ID",
            "HF_DEFAULT_REPOSITORY",
            "HF_REPOSITORY",
        ),
        "SHOPIFY_SHOP_DOMAIN": (
            "SHOPIFY_SHOP_DOMAIN",
            "SHOP_DOMAIN",
            "SHOPIFY_SHOP",
        ),
        "SCBE_API_KEY": (
            "SCBE_API_KEY",
            "SCBE_MOBILE_API_KEY",
            "SCBE_CLIENT_API_KEY",
        ),
    }

    for canonical, candidates in aliases.items():
        _copy_alias(canonical, candidates)

    # Additional derived aliases for compatibility
    if not os.getenv("HF_DEFAULT_REPOSITORY") and os.getenv("HF_DEFAULT_REPO"):
        os.environ["HF_DEFAULT_REPOSITORY"] = os.getenv("HF_DEFAULT_REPO", "")
    if not os.getenv("HF_REPO_ID") and os.getenv("HF_DEFAULT_REPO"):
        value = os.getenv("HF_DEFAULT_REPO", "")
        os.environ["HF_REPO_ID"] = value
    if not os.getenv("SHOPIFY_API_VERSION"):
        os.environ["SHOPIFY_API_VERSION"] = _first_env("SHOPIFY_API_VERSION", "SHOPIFY_API_VER") or "2025-10"

    # Canonical endpoint names expected by some registration code
    if not os.getenv("SCBE_MOBILE_API_KEY") and os.getenv("SCBE_API_KEY"):
        os.environ["SCBE_MOBILE_API_KEY"] = os.getenv("SCBE_API_KEY", "")

    _BOOTSTRAPPED = True
    logger.info("AetherBrowse runtime environment bootstrap completed.")
