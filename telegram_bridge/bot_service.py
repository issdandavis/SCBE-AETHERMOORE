"""
SCBE Telegram Bridge — AI-Governed Messaging Service
======================================================
Connects to Telegram via Telethon (MTProto) and routes messages
through OctoArmor + SCBE governance. Every conversation generates
training data for the flywheel.

Modes:
  1. Bot mode: Runs as a Telegram bot (@YourBot)
  2. Userbot mode: Runs as your actual account (MTProto client)
  3. Hybrid: Bot for public, userbot for private AI assistant

Start: python telegram_bridge/bot_service.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("scbe-telegram")

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import PeerUser, PeerChat, PeerChannel
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False

# Load SCBE stack
try:
    from fleet.octo_armor import OctoArmor
    HAS_OCTOARMOR = True
except ImportError:
    HAS_OCTOARMOR = False

try:
    from aetherbrowse.runtime.hydra_bridge import compute_risk_score, local_governance_check
    HAS_GOVERNANCE = True
except ImportError:
    HAS_GOVERNANCE = False


# ---------------------------------------------------------------------------
#  Config
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load Telegram credentials from env or .env file."""
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

    return {
        "api_id": int(os.environ.get("TELEGRAM_API_ID", "0")),
        "api_hash": os.environ.get("TELEGRAM_API_HASH", ""),
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "session_name": os.environ.get("TELEGRAM_SESSION", "scbe_telegram"),
        "mode": os.environ.get("TELEGRAM_MODE", "bot"),  # "bot" or "userbot"
        "owner_id": int(os.environ.get("TELEGRAM_OWNER_ID", "0")),
        "ai_enabled_chats": os.environ.get("TELEGRAM_AI_CHATS", "").split(","),
    }


# ---------------------------------------------------------------------------
#  Governance layer
# ---------------------------------------------------------------------------

BLOCKED_PATTERNS = [
    "password", "ssn", "credit card", "bank account", "private key",
    "secret key", "api key", "token", "bearer",
]


def govern_outgoing(text: str, context: str = "") -> dict:
    """Check if an outgoing message should be sent."""
    text_lower = text.lower()

    # Check for sensitive data leakage
    for pattern in BLOCKED_PATTERNS:
        if pattern in text_lower:
            return {
                "decision": "DENY",
                "reason": f"Outgoing message contains sensitive pattern: {pattern}",
                "risk_score": 0.95,
            }

    # Check message length (don't spam)
    if len(text) > 4000:
        return {
            "decision": "QUARANTINE",
            "reason": "Message exceeds 4000 chars — consider splitting",
            "risk_score": 0.4,
        }

    return {"decision": "ALLOW", "reason": "Safe message", "risk_score": 0.05}


def govern_incoming(text: str, sender_id: int, owner_id: int) -> dict:
    """Governance check on incoming messages before AI processes them."""
    # Prompt injection detection
    injection_patterns = [
        "ignore previous instructions",
        "forget your rules",
        "you are now",
        "system prompt",
        "jailbreak",
        "DAN mode",
    ]

    text_lower = text.lower()
    for pattern in injection_patterns:
        if pattern in text_lower:
            return {
                "decision": "DENY",
                "reason": f"Prompt injection attempt detected: {pattern}",
                "risk_score": 0.9,
            }

    # Owner gets higher trust
    if sender_id == owner_id:
        return {"decision": "ALLOW", "reason": "Owner message", "risk_score": 0.01}

    return {"decision": "ALLOW", "reason": "Normal message", "risk_score": 0.1}


# ---------------------------------------------------------------------------
#  AI response engine
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an AI assistant powered by AETHERMOORE's SCBE governance framework.
You run inside Telegram as part of the HYDRA multi-agent fleet.

Your persona traits:
- Helpful, concise, technically competent
- You know about AI safety, SCBE's 14-layer pipeline, Sacred Tongues
- You can help with code, research, planning, and creative tasks
- You never share sensitive information (keys, passwords, financial data)
- You mention governance checks naturally when relevant

Keep responses under 2000 characters for Telegram readability.
Use markdown formatting that Telegram supports (bold, italic, code, links)."""


async def generate_ai_response(message: str, chat_context: list[dict] = None) -> str:
    """Route through OctoArmor to generate a response."""
    if not HAS_OCTOARMOR:
        return "AI engine offline — OctoArmor not available. Install fleet dependencies."

    try:
        armor = OctoArmor()

        # Build context from recent messages
        context = SYSTEM_PROMPT
        if chat_context:
            history = "\n".join(
                f"{'User' if m['role'] == 'user' else 'AI'}: {m['text'][:500]}"
                for m in chat_context[-5:]
            )
            context += f"\n\nRecent conversation:\n{history}"

        result = await armor.reach(
            message,
            task_type="chat",
            temperature=0.7,
            max_tokens=1500,
            context=context,
        )

        if result.get("status") == "ok" and result.get("response"):
            response = result["response"]
            provider = result.get("tentacle", "unknown")
            logger.info(f"AI response via {provider} ({result.get('latency_ms', 0):.0f}ms)")
            return response
        else:
            return f"AI processing error: {result.get('error', 'unknown')}"

    except Exception as e:
        logger.error(f"AI response failed: {e}")
        return f"Error generating response: {str(e)[:200]}"


# ---------------------------------------------------------------------------
#  Training data generation
# ---------------------------------------------------------------------------

class TrainingLogger:
    """Log conversations as SFT training pairs."""

    def __init__(self):
        self.log_path = ROOT / "training-data" / "telegram" / "conversations.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_pair(self, user_msg: str, ai_response: str, chat_id: int,
                 governance: dict, provider: str = ""):
        pair = {
            "timestamp": time.time(),
            "input": {"role": "user", "text": user_msg},
            "output": {"role": "assistant", "text": ai_response},
            "metadata": {
                "chat_id": chat_id,
                "governance": governance.get("decision", "ALLOW"),
                "risk_score": governance.get("risk_score", 0),
                "provider": provider,
                "source": "telegram_bridge",
            },
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    def log_governance_deny(self, text: str, chat_id: int, governance: dict):
        pair = {
            "timestamp": time.time(),
            "type": "governance_deny",
            "input": text[:500],
            "governance": governance,
            "chat_id": chat_id,
            "source": "telegram_bridge",
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")


training_logger = TrainingLogger()

# Import AetherBrowse integration
try:
    from telegram_bridge.aetherbrowse_integration import is_web_task, process_web_task
    HAS_AETHERBROWSE = True
except ImportError:
    HAS_AETHERBROWSE = False

# Import service connector
try:
    from telegram_bridge.service_connector import connector
    HAS_CONNECTOR = True
except ImportError:
    HAS_CONNECTOR = False

# Import Shopify bridge
try:
    from scripts.shopify_bridge import ShopifyCLIBridge
    HAS_SHOPIFY = True
except ImportError:
    HAS_SHOPIFY = False


# ---------------------------------------------------------------------------
#  Chat context memory (per-chat recent history)
# ---------------------------------------------------------------------------

class ChatMemory:
    """In-memory recent message history per chat."""

    def __init__(self, max_messages: int = 20):
        self._memory: dict[int, list[dict]] = {}
        self._max = max_messages

    def add(self, chat_id: int, role: str, text: str):
        if chat_id not in self._memory:
            self._memory[chat_id] = []
        self._memory[chat_id].append({"role": role, "text": text, "time": time.time()})
        if len(self._memory[chat_id]) > self._max:
            self._memory[chat_id] = self._memory[chat_id][-self._max:]

    def get(self, chat_id: int) -> list[dict]:
        return self._memory.get(chat_id, [])

    def clear(self, chat_id: int):
        self._memory.pop(chat_id, None)


chat_memory = ChatMemory()


# ---------------------------------------------------------------------------
#  Telegram client setup
# ---------------------------------------------------------------------------

async def run_bot(config: dict):
    """Run in bot mode — responds to /commands and mentions."""
    client = TelegramClient(
        str(ROOT / "telegram_bridge" / config["session_name"]),
        config["api_id"],
        config["api_hash"],
    )

    await client.start(bot_token=config["bot_token"])
    me = await client.get_me()
    logger.info(f"Bot started: @{me.username} (ID: {me.id})")

    # Register with AetherNet if available
    if HAS_CONNECTOR:
        svc_status = await connector.discover_services()
        online = [n for n, s in svc_status.items() if s["online"]]
        logger.info(f"Connected services: {', '.join(online) if online else 'none'}")
        reg = await connector.register_with_aethernet()
        if "error" not in reg:
            logger.info("Registered with AetherNet")

    @client.on(events.NewMessage(pattern=r'/start'))
    async def handle_start(event):
        await event.respond(
            "**AETHERMOORE AI Assistant**\n\n"
            "Powered by SCBE 14-layer governance.\n\n"
            "Commands:\n"
            "/ask <question> — Ask the AI anything\n"
            "/browse <task> — Execute a web task via AetherBrowse\n"
            "/govern <text> — Check governance on a message\n"
            "/tongue <text> — Encode via Sacred Tongues\n"
            "/services — Show SCBE service status\n"
            "/status — System status\n"
            "/clear — Clear conversation memory\n\n"
            "Or just send a message and I'll respond."
        )

    @client.on(events.NewMessage(pattern=r'/status'))
    async def handle_status(event):
        status = (
            f"**AETHERMOORE Status**\n"
            f"OctoArmor: {'online' if HAS_OCTOARMOR else 'offline'}\n"
            f"Governance: {'active' if HAS_GOVERNANCE else 'basic'}\n"
            f"Training data: {training_logger.log_path}\n"
            f"Chat memory: {len(chat_memory._memory)} active chats"
        )
        # Add cross-service status if connector available
        if HAS_CONNECTOR:
            await connector.discover_services()
            status += "\n\n" + connector.format_status()
        await event.respond(status)

    @client.on(events.NewMessage(pattern=r'/services'))
    async def handle_services(event):
        """Show all SCBE service health."""
        if HAS_CONNECTOR:
            svc_status = await connector.discover_services()
            await event.respond(connector.format_status())
        else:
            await event.respond("Service connector not available.")

    @client.on(events.NewMessage(pattern=r'/tongue\s+(.+)'))
    async def handle_tongue(event):
        """Encode text through Sacred Tongues."""
        text = event.pattern_match.group(1)
        if HAS_CONNECTOR:
            result = await connector.tongue_encode(text)
            if "error" in result:
                await event.respond(f"Tongue encoding failed: {result['error']}")
            else:
                encoded = result.get("encoded", result)
                await event.respond(f"**Sacred Tongue (KO)**\n`{json.dumps(encoded, indent=2)[:2000]}`")
        else:
            await event.respond("SCBE Bridge not connected.")

    @client.on(events.NewMessage(pattern=r'/clear'))
    async def handle_clear(event):
        chat_memory.clear(event.chat_id)
        await event.respond("Conversation memory cleared.")

    @client.on(events.NewMessage(pattern=r'/govern\s+(.+)'))
    async def handle_govern(event):
        text = event.pattern_match.group(1)
        result = govern_outgoing(text)
        await event.respond(
            f"**Governance Check**\n"
            f"Decision: {result['decision']}\n"
            f"Risk: {result['risk_score']:.2f}\n"
            f"Reason: {result['reason']}"
        )

    @client.on(events.NewMessage(pattern=r'/browse\s+(.+)'))
    async def handle_browse(event):
        """Route web tasks directly to AetherBrowse."""
        task = event.pattern_match.group(1)
        if HAS_AETHERBROWSE:
            await event.respond("Sending to AetherBrowse...")
            result = await process_web_task(task)
            await event.respond(f"**Result:**\n{result}", parse_mode='md')
        else:
            await event.respond("AetherBrowse integration not available.")

    @client.on(events.NewMessage(pattern=r'/ask\s+(.+)'))
    async def handle_ask(event):
        question = event.pattern_match.group(1)
        await _process_message(event, question)

    @client.on(events.NewMessage(pattern=r'/shop(?:\s+(.+))?'))
    async def handle_shop(event):
        """Shopify store management from Telegram."""
        if not HAS_SHOPIFY:
            await event.respond("Shopify bridge not available. Install shopify_bridge.")
            return

        subcommand = (event.pattern_match.group(1) or "status").strip().lower()
        bridge = ShopifyCLIBridge()

        if subcommand == "status":
            store = bridge.store or "Not configured"
            blog_posts = bridge.queue_to_blog_posts()
            products = bridge.revenue_products_to_shopify()
            await event.respond(
                f"**Shopify Store Status**\n\n"
                f"Store: `{store}`\n"
                f"Products: {len(products)}\n"
                f"Blog posts ready: {len(blog_posts)}\n"
                f"Theme: aethermoore-creator-os\n\n"
                f"Commands: `/shop products`, `/shop blog`"
            )
        elif subcommand == "products":
            products = bridge.revenue_products_to_shopify()
            lines = ["**Shopify Products**\n"]
            for p in products:
                prod = p["product"]
                variant = prod.get("variants", [{}])[0]
                lines.append(f"- **{prod['title']}** — ${variant.get('price', 'N/A')}")
            await event.respond("\n".join(lines))
        elif subcommand == "blog":
            posts = bridge.queue_to_blog_posts()
            if not posts:
                await event.respond("No blog posts queued. Run content engine first.")
                return
            lines = ["**Blog Posts Ready**\n"]
            for post in posts:
                article = post["article"]
                lines.append(f"- **{article['title']}** (gov: {post['_governance_score']:.2f})")
            await event.respond("\n".join(lines))
        else:
            await event.respond(f"Unknown shop command: `{subcommand}`\nTry: status, products, blog")

    @client.on(events.NewMessage(func=lambda e: not e.text.startswith('/') and e.is_private))
    async def handle_dm(event):
        """Respond to all DMs that aren't commands."""
        await _process_message(event, event.text)

    async def _process_message(event, text):
        """Core message processing: govern → AI → govern → respond → log."""
        sender = await event.get_sender()
        sender_id = sender.id if sender else 0

        # Step 1: Govern incoming
        gov_in = govern_incoming(text, sender_id, config["owner_id"])
        if gov_in["decision"] == "DENY":
            training_logger.log_governance_deny(text, event.chat_id, gov_in)
            await event.respond(f"Message blocked by governance: {gov_in['reason']}")
            return

        # Step 2: Check if this is a web task for AetherBrowse
        if HAS_AETHERBROWSE and is_web_task(text):
            await event.respond("Routing to AetherBrowse...")
            web_result = await process_web_task(text)
            await event.respond(f"**AetherBrowse Result:**\n{web_result}", parse_mode='md')
            chat_memory.add(event.chat_id, "user", text)
            chat_memory.add(event.chat_id, "assistant", web_result)
            training_logger.log_pair(text, web_result, event.chat_id, gov_in)
            return

        # Step 3: Add to memory
        chat_memory.add(event.chat_id, "user", text)

        # Step 4: Generate AI response
        context = chat_memory.get(event.chat_id)
        response = await generate_ai_response(text, context)

        # Step 4: Govern outgoing
        gov_out = govern_outgoing(response)
        if gov_out["decision"] == "DENY":
            response = "[Response blocked by governance — contained sensitive data]"
            training_logger.log_governance_deny(response, event.chat_id, gov_out)

        # Step 5: Send response
        await event.respond(response, parse_mode='md')

        # Step 6: Save to memory + training log
        chat_memory.add(event.chat_id, "assistant", response)
        training_logger.log_pair(text, response, event.chat_id, gov_in)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    await client.run_until_disconnected()


async def run_userbot(config: dict):
    """Run in userbot mode — AI assistant on your real account."""
    client = TelegramClient(
        str(ROOT / "telegram_bridge" / config["session_name"]),
        config["api_id"],
        config["api_hash"],
    )

    await client.start()
    me = await client.get_me()
    logger.info(f"Userbot started: {me.first_name} (ID: {me.id})")

    # Trigger word for AI — user types ".ai <question>" in any chat
    @client.on(events.NewMessage(pattern=r'\.ai\s+(.+)', outgoing=True))
    async def handle_ai_trigger(event):
        """When you type '.ai <question>' it replaces with AI response."""
        question = event.pattern_match.group(1)

        # Govern incoming (self-messages are owner)
        gov_in = govern_incoming(question, me.id, me.id)

        # Generate response
        context = chat_memory.get(event.chat_id)
        chat_memory.add(event.chat_id, "user", question)
        response = await generate_ai_response(question, context)

        # Govern outgoing
        gov_out = govern_outgoing(response)
        if gov_out["decision"] == "DENY":
            response = "[Governance blocked: sensitive content detected]"

        # Edit the original message with the AI response
        await event.edit(f"**Q:** {question}\n\n**A:** {response}")

        # Log
        chat_memory.add(event.chat_id, "assistant", response)
        training_logger.log_pair(question, response, event.chat_id, gov_in)

    # Auto-respond in specific chats (when someone messages you)
    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def handle_incoming_dm(event):
        # Only auto-respond if AI chats are configured
        ai_chats = config.get("ai_enabled_chats", [])
        sender = await event.get_sender()
        sender_id = str(sender.id) if sender else ""

        if ai_chats and ai_chats != [''] and sender_id not in ai_chats:
            return  # Not an AI-enabled chat

        text = event.text
        if not text:
            return

        # Govern
        gov_in = govern_incoming(text, int(sender_id or 0), me.id)
        if gov_in["decision"] == "DENY":
            training_logger.log_governance_deny(text, event.chat_id, gov_in)
            return

        chat_memory.add(event.chat_id, "user", text)
        context = chat_memory.get(event.chat_id)
        response = await generate_ai_response(text, context)

        gov_out = govern_outgoing(response)
        if gov_out["decision"] == "DENY":
            response = "[Response blocked by governance]"

        await event.respond(response, parse_mode='md')
        chat_memory.add(event.chat_id, "assistant", response)
        training_logger.log_pair(text, response, event.chat_id, gov_in)

    # SCBE governance commands
    @client.on(events.NewMessage(pattern=r'\.status', outgoing=True))
    async def handle_status(event):
        status = (
            f"**AETHERMOORE Telegram Bridge**\n"
            f"Mode: userbot\n"
            f"OctoArmor: {'online' if HAS_OCTOARMOR else 'offline'}\n"
            f"Governance: {'active' if HAS_GOVERNANCE else 'basic'}\n"
            f"Active chats: {len(chat_memory._memory)}\n"
            f"Training log: {training_logger.log_path}"
        )
        await event.edit(status)

    @client.on(events.NewMessage(pattern=r'\.clear', outgoing=True))
    async def handle_clear(event):
        chat_memory.clear(event.chat_id)
        await event.edit("Chat memory cleared.")

    logger.info("Userbot running. Type '.ai <question>' in any chat. Press Ctrl+C to stop.")
    await client.run_until_disconnected()


# ---------------------------------------------------------------------------
#  Entry point
# ---------------------------------------------------------------------------

def main():
    if not HAS_TELETHON:
        print("ERROR: Telethon not installed. Run: pip install telethon")
        sys.exit(1)

    config = load_config()

    if not config["api_id"] or not config["api_hash"]:
        print("ERROR: Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")
        print("Get them from: https://my.telegram.org/apps")
        sys.exit(1)

    if config["mode"] == "bot":
        if not config["bot_token"]:
            print("ERROR: Set TELEGRAM_BOT_TOKEN in .env")
            print("Create a bot via @BotFather on Telegram")
            sys.exit(1)
        asyncio.run(run_bot(config))
    elif config["mode"] == "userbot":
        asyncio.run(run_userbot(config))
    else:
        print(f"ERROR: Unknown mode '{config['mode']}'. Use 'bot' or 'userbot'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
