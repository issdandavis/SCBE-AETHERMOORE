"""
SCBE Telegram Bot — Pure Bot API Mode
=======================================
Uses the Telegram Bot HTTP API directly (no Telethon needed).
Only requires BOT_TOKEN — no api_id/api_hash.

Start: python telegram_bridge/bot_api_service.py
"""

import asyncio
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("scbe-telegram-bot")

# Load .env
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Import SCBE stack
try:
    from fleet.octo_armor import OctoArmor
    HAS_OCTOARMOR = True
except ImportError:
    HAS_OCTOARMOR = False

try:
    from telegram_bridge.bot_service import (
        govern_incoming, govern_outgoing, generate_ai_response,
        chat_memory, training_logger, SYSTEM_PROMPT,
    )
    HAS_BOT_SERVICE = True
except ImportError:
    HAS_BOT_SERVICE = False

try:
    from telegram_bridge.aetherbrowse_integration import is_web_task, process_web_task
    HAS_AETHERBROWSE = True
except ImportError:
    HAS_AETHERBROWSE = False

try:
    from telegram_bridge.service_connector import connector
    HAS_CONNECTOR = True
except ImportError:
    HAS_CONNECTOR = False

try:
    from scripts.shopify_bridge import ShopifyCLIBridge
    HAS_SHOPIFY = True
except ImportError:
    HAS_SHOPIFY = False


# ---------------------------------------------------------------------------
#  Telegram Bot API helpers
# ---------------------------------------------------------------------------

def api_call(method: str, data: dict = None, timeout: float = 60) -> dict:
    """Call Telegram Bot API synchronously."""
    url = f"{BASE_URL}/{method}"
    if data:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
        )
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        if "timed out" in str(e).lower():
            return {"ok": True, "result": []}  # Normal for long polling
        logger.error(f"API call failed: {method} — {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        if "timed out" in str(e).lower():
            return {"ok": True, "result": []}
        logger.error(f"API call failed: {method} — {e}")
        return {"ok": False, "error": str(e)}


async def api_call_async(method: str, data: dict = None, timeout: float = 60) -> dict:
    """Async wrapper for API calls."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: api_call(method, data, timeout))


def send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> dict:
    """Send a message to a chat."""
    # Telegram has 4096 char limit
    if len(text) > 4000:
        text = text[:3997] + "..."
    return api_call("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    })


async def send_message_async(chat_id: int, text: str, parse_mode: str = "Markdown") -> dict:
    """Send a message asynchronously."""
    if len(text) > 4000:
        text = text[:3997] + "..."
    return await api_call_async("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    })


# ---------------------------------------------------------------------------
#  Fallback governance + AI when bot_service not available
# ---------------------------------------------------------------------------

BLOCKED_PATTERNS = [
    "password", "ssn", "credit card", "bank account", "private key",
    "secret key", "api key", "token", "bearer",
]

INJECTION_PATTERNS = [
    "ignore previous instructions", "forget your rules", "you are now",
    "system prompt", "jailbreak", "DAN mode",
]


def _govern_incoming(text: str) -> dict:
    if HAS_BOT_SERVICE:
        return govern_incoming(text, 0, 0)
    text_lower = text.lower()
    for p in INJECTION_PATTERNS:
        if p in text_lower:
            return {"decision": "DENY", "reason": f"Injection: {p}", "risk_score": 0.9}
    return {"decision": "ALLOW", "reason": "OK", "risk_score": 0.1}


def _govern_outgoing(text: str) -> dict:
    if HAS_BOT_SERVICE:
        return govern_outgoing(text)
    text_lower = text.lower()
    for p in BLOCKED_PATTERNS:
        if p in text_lower:
            return {"decision": "DENY", "reason": f"Sensitive: {p}", "risk_score": 0.95}
    return {"decision": "ALLOW", "reason": "Safe", "risk_score": 0.05}


async def _generate_response(text: str, chat_id: int) -> str:
    if HAS_BOT_SERVICE:
        context = chat_memory.get(chat_id)
        chat_memory.add(chat_id, "user", text)
        response = await generate_ai_response(text, context)
        chat_memory.add(chat_id, "assistant", response)
        return response

    # Fallback: try OctoArmor directly
    if HAS_OCTOARMOR:
        try:
            armor = OctoArmor()
            result = await armor.reach(text, task_type="chat", temperature=0.7, max_tokens=1500)
            if result.get("status") == "ok" and result.get("response"):
                return result["response"]
        except Exception as e:
            logger.error(f"OctoArmor error: {e}")

    return (
        "AETHERMOORE AI is online but no LLM provider is configured.\n\n"
        "Set API keys in `.env` for: GROQ_API_KEY, CEREBRAS_API_KEY, "
        "GOOGLE_AI_API_KEY, or ANTHROPIC_API_KEY"
    )


# ---------------------------------------------------------------------------
#  Command handlers
# ---------------------------------------------------------------------------

async def handle_command(chat_id: int, text: str, message_id: int, sender_id: int):
    """Route commands and messages."""
    text = text.strip()

    # /start
    if text == "/start":
        await send_message_async(chat_id,
            "*AETHERMOORE AI Assistant* (@SCBEAETRHBot)\n\n"
            "Powered by SCBE 14-layer governance + OctoArmor fleet.\n\n"
            "*Commands:*\n"
            "/ask `<question>` — Ask the AI\n"
            "/browse `<task>` — Web task via AetherBrowse\n"
            "/github `<task>` — GitHub ops via AetherBrowse (e.g. issue list repo owner/repo)\n"
            "/notebook or /codespace or /lm `<task>` — GitHub Codespace ops (a.k.a. LM Notebook)\n"
            "/tg `<task>` — Telegram ops via AetherBrowse (e.g. send chat_id=12345 text)\n"
            "/govern `<text>` — Governance check\n"
            "/shop — Shopify store management\n"
            "/services — SCBE stack status\n"
            "/status — Bot status\n"
            "/clear — Clear memory\n\n"
            "Or just send a message."
        )
        return

    # /status
    if text == "/status":
        status = (
            f"*AETHERMOORE Status*\n"
            f"OctoArmor: {'online' if HAS_OCTOARMOR else 'offline'}\n"
            f"Governance: active\n"
            f"AetherBrowse: {'connected' if HAS_AETHERBROWSE else 'offline'}\n"
            f"Shopify: {'connected' if HAS_SHOPIFY else 'offline'}\n"
            f"Connector: {'active' if HAS_CONNECTOR else 'offline'}"
        )
        if HAS_CONNECTOR:
            svc_status = await connector.discover_services()
            status += "\n\n" + connector.format_status()
        await send_message_async(chat_id, status)
        return

    # /services
    if text == "/services":
        if HAS_CONNECTOR:
            await connector.discover_services()
            await send_message_async(chat_id, connector.format_status())
        else:
            await send_message_async(chat_id, "Service connector not loaded.")
        return

    # /clear
    if text == "/clear":
        if HAS_BOT_SERVICE:
            chat_memory.clear(chat_id)
        await send_message_async(chat_id, "Memory cleared.")
        return

    # /govern <text>
    if text.startswith("/govern "):
        check_text = text[8:]
        gov = _govern_outgoing(check_text)
        await send_message_async(chat_id,
            f"*Governance Check*\n"
            f"Decision: {gov['decision']}\n"
            f"Risk: {gov['risk_score']:.2f}\n"
            f"Reason: {gov['reason']}"
        )
        return

    # /browse <task>
    if text.startswith("/browse "):
        task = text[8:]
        if HAS_AETHERBROWSE:
            await send_message_async(chat_id, "Routing to AetherBrowse...")
            result = await process_web_task(task)
            await send_message_async(chat_id, f"*Result:*\n{result}")
        else:
            await send_message_async(chat_id, "AetherBrowse not available.")
        return

    # /github <task>
    if text.startswith("/github "):
        task = f"github {text[8:]}"
        if HAS_AETHERBROWSE:
            await send_message_async(chat_id, "Routing to GitHub action...")
            result = await process_web_task(task)
            await send_message_async(chat_id, f"*GitHub:*\n{result}")
        else:
            await send_message_async(chat_id, "AetherBrowse not available.")
        return

    # /notebook <task> or /codespace <task>
    if text.startswith("/notebook "):
        task = f"codespace {text[10:]}"
        if HAS_AETHERBROWSE:
            await send_message_async(chat_id, "Routing to Codespace action...")
            result = await process_web_task(task)
            await send_message_async(chat_id, f"*Codespace:*\n{result}")
        else:
            await send_message_async(chat_id, "AetherBrowse not available.")
        return

    # /lm <task> (LM Notebook alias)
    if text.startswith("/lm "):
        task = f"codespace {text[4:]}"
        if HAS_AETHERBROWSE:
            await send_message_async(chat_id, "Routing to Codespace action...")
            result = await process_web_task(task)
            await send_message_async(chat_id, f"*Codespace:*\n{result}")
        else:
            await send_message_async(chat_id, "AetherBrowse not available.")
        return

    if text.startswith("/codespace "):
        task = f"codespace {text[10:]}"
        if HAS_AETHERBROWSE:
            await send_message_async(chat_id, "Routing to Codespace action...")
            result = await process_web_task(task)
            await send_message_async(chat_id, f"*Codespace:*\n{result}")
        else:
            await send_message_async(chat_id, "AetherBrowse not available.")
        return

    # /tg <task>
    if text.startswith("/tg "):
        task = f"telegram {text[4:]}"
        if HAS_AETHERBROWSE:
            await send_message_async(chat_id, "Routing to Telegram action...")
            result = await process_web_task(task)
            await send_message_async(chat_id, f"*Telegram:*\n{result}")
        else:
            await send_message_async(chat_id, "AetherBrowse not available.")
        return

    # /shop [subcommand]
    if text.startswith("/shop"):
        parts = text.split(maxsplit=1)
        subcmd = parts[1].strip().lower() if len(parts) > 1 else "status"

        if not HAS_SHOPIFY:
            await send_message_async(chat_id, "Shopify bridge not loaded.")
            return

        bridge = ShopifyCLIBridge()

        if subcmd == "products":
            products = bridge.revenue_products_to_shopify()
            lines = ["*Shopify Products*\n"]
            for p in products:
                prod = p["product"]
                variant = prod.get("variants", [{}])[0]
                lines.append(f"• *{prod['title']}* — ${variant.get('price', 'N/A')}")
            await send_message_async(chat_id, "\n".join(lines))
        elif subcmd == "blog":
            posts = bridge.queue_to_blog_posts()
            if not posts:
                await send_message_async(chat_id, "No blog posts queued.")
            else:
                lines = ["*Blog Posts Ready*\n"]
                for post in posts:
                    article = post["article"]
                    lines.append(f"• *{article['title']}*")
                await send_message_async(chat_id, "\n".join(lines))
        else:
            store = bridge.store or "Not configured"
            products = bridge.revenue_products_to_shopify()
            blog_posts = bridge.queue_to_blog_posts()
            await send_message_async(chat_id,
                f"*Shopify Store*\n\n"
                f"Store: `{store}`\n"
                f"Products: {len(products)}\n"
                f"Blog posts ready: {len(blog_posts)}\n\n"
                f"Try: `/shop products`, `/shop blog`"
            )
        return

    # /ask <question>
    if text.startswith("/ask "):
        question = text[5:]
        await _process_ai_message(chat_id, question, sender_id)
        return

    # Default: treat as AI question (DMs)
    if not text.startswith("/"):
        await _process_ai_message(chat_id, text, sender_id)


async def _process_ai_message(chat_id: int, text: str, sender_id: int):
    """Process a message through governance + AI + governance pipeline."""
    # Govern incoming
    gov_in = _govern_incoming(text)
    if gov_in["decision"] == "DENY":
        if HAS_BOT_SERVICE:
            training_logger.log_governance_deny(text, chat_id, gov_in)
        await send_message_async(chat_id, f"Blocked by governance: {gov_in['reason']}")
        return

    # Check for web tasks
    if HAS_AETHERBROWSE and is_web_task(text):
        await send_message_async(chat_id, "Routing to AetherBrowse...")
        result = await process_web_task(text)
        await send_message_async(chat_id, f"*AetherBrowse:*\n{result}")
        return

    # Generate AI response
    response = await _generate_response(text, chat_id)

    # Govern outgoing
    gov_out = _govern_outgoing(response)
    if gov_out["decision"] == "DENY":
        response = "[Response blocked — contained sensitive data]"

    # Send
    result = await send_message_async(chat_id, response)

    # Fallback to plain text if Markdown fails
    if not result.get("ok") and "parse" in str(result.get("error", "")).lower():
        await send_message_async(chat_id, response, parse_mode="")

    # Log training data
    if HAS_BOT_SERVICE:
        training_logger.log_pair(text, response, chat_id, gov_in)


# ---------------------------------------------------------------------------
#  Long polling loop
# ---------------------------------------------------------------------------

async def polling_loop():
    """Long poll the Telegram Bot API for updates."""
    logger.info("Starting long polling...")

    # Verify bot token
    me = await api_call_async("getMe")
    if not me.get("ok"):
        logger.error(f"Invalid bot token: {me}")
        sys.exit(1)

    bot_info = me["result"]
    logger.info(f"Bot online: @{bot_info['username']} (ID: {bot_info['id']})")

    # Discover services
    if HAS_CONNECTOR:
        svc_status = await connector.discover_services()
        online = [n for n, s in svc_status.items() if s["online"]]
        logger.info(f"Connected services: {', '.join(online) if online else 'none'}")

    offset = 0
    while True:
        try:
            updates = await api_call_async("getUpdates", {
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message"],
            })

            if not updates.get("ok"):
                logger.warning(f"getUpdates failed: {updates}")
                await asyncio.sleep(5)
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message or not message.get("text"):
                    continue

                chat_id = message["chat"]["id"]
                text = message["text"]
                message_id = message["message_id"]
                sender_id = message.get("from", {}).get("id", 0)
                sender_name = message.get("from", {}).get("first_name", "Unknown")

                logger.info(f"[{sender_name}] {text[:80]}")

                try:
                    await handle_command(chat_id, text, message_id, sender_id)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    try:
                        await send_message_async(chat_id, f"Error: {str(e)[:200]}")
                    except Exception:
                        pass

        except KeyboardInterrupt:
            logger.info("Shutting down...")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

def main():
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        print("Create a bot via @BotFather on Telegram")
        sys.exit(1)

    print(f"\nSCBE Telegram Bot — Pure API Mode")
    print(f"Token: ...{BOT_TOKEN[-8:]}")
    print(f"OctoArmor: {'YES' if HAS_OCTOARMOR else 'NO'}")
    print(f"AetherBrowse: {'YES' if HAS_AETHERBROWSE else 'NO'}")
    print(f"Shopify: {'YES' if HAS_SHOPIFY else 'NO'}")
    print(f"Connector: {'YES' if HAS_CONNECTOR else 'NO'}")
    print()

    asyncio.run(polling_loop())


if __name__ == "__main__":
    main()
