"""
SCBE Telegram Webhook Server
================================
FastAPI server that receives Telegram webhook updates and routes
them through SCBE governance + OctoArmor.

Also exposes REST API for other SCBE services to send Telegram messages.

Port: 8500
Start: python telegram_bridge/webhook_server.py
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
logger = logging.getLogger("scbe-telegram-webhook")

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    from telethon import TelegramClient
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False

from telegram_bridge.bot_service import (
    load_config, generate_ai_response, govern_incoming, govern_outgoing,
    chat_memory, training_logger, HAS_OCTOARMOR,
)


# ---------------------------------------------------------------------------
#  FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="SCBE Telegram Bridge")

_client: Optional[TelegramClient] = None
_config: dict = {}


@app.on_event("startup")
async def startup():
    global _client, _config
    _config = load_config()
    if HAS_TELETHON and _config["api_id"] and _config["api_hash"]:
        _client = TelegramClient(
            str(ROOT / "telegram_bridge" / _config["session_name"] + "_webhook"),
            _config["api_id"],
            _config["api_hash"],
        )
        if _config.get("bot_token"):
            await _client.start(bot_token=_config["bot_token"])
        else:
            await _client.start()
        me = await _client.get_me()
        logger.info(f"Telegram client ready: {me.first_name} (ID: {me.id})")


@app.on_event("shutdown")
async def shutdown():
    if _client:
        await _client.disconnect()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "telegram_connected": _client is not None and _client.is_connected(),
        "octoarmor": HAS_OCTOARMOR,
        "active_chats": len(chat_memory._memory),
    }


@app.post("/v1/telegram/send")
async def send_message(request: Request):
    """Send a governed message to a Telegram chat.

    Body: {"chat_id": 123456, "text": "Hello!"}
    """
    if not _client:
        return JSONResponse(status_code=503, content={"error": "Telegram client not connected"})

    body = await request.json()
    chat_id = body.get("chat_id")
    text = body.get("text", "")

    if not chat_id or not text:
        return JSONResponse(status_code=400, content={"error": "chat_id and text required"})

    # Govern outgoing
    gov = govern_outgoing(text)
    if gov["decision"] == "DENY":
        return JSONResponse(status_code=403, content={
            "error": "Message blocked by governance",
            "governance": gov,
        })

    await _client.send_message(chat_id, text, parse_mode='md')
    return {"status": "sent", "chat_id": chat_id, "governance": gov}


@app.post("/v1/telegram/ask")
async def ask_ai(request: Request):
    """Send a question to the AI and get a response (no Telegram delivery).

    Body: {"question": "What is SCBE?", "chat_id": 0}
    """
    body = await request.json()
    question = body.get("question", "")
    chat_id = body.get("chat_id", 0)

    if not question:
        return JSONResponse(status_code=400, content={"error": "question required"})

    context = chat_memory.get(chat_id)
    chat_memory.add(chat_id, "user", question)
    response = await generate_ai_response(question, context)
    chat_memory.add(chat_id, "assistant", response)

    gov = govern_outgoing(response)
    training_logger.log_pair(question, response, chat_id, {"decision": "ALLOW"})

    return {
        "response": response,
        "governance": gov,
    }


@app.post("/v1/telegram/broadcast")
async def broadcast(request: Request):
    """Send a governed message to multiple chats.

    Body: {"chat_ids": [123, 456], "text": "Announcement!"}
    """
    if not _client:
        return JSONResponse(status_code=503, content={"error": "Telegram client not connected"})

    body = await request.json()
    chat_ids = body.get("chat_ids", [])
    text = body.get("text", "")

    gov = govern_outgoing(text)
    if gov["decision"] == "DENY":
        return JSONResponse(status_code=403, content={"error": "Blocked", "governance": gov})

    results = []
    for cid in chat_ids:
        try:
            await _client.send_message(cid, text, parse_mode='md')
            results.append({"chat_id": cid, "status": "sent"})
        except Exception as e:
            results.append({"chat_id": cid, "status": "error", "error": str(e)})
        await asyncio.sleep(0.5)  # Rate limit

    return {"results": results, "governance": gov}


@app.get("/v1/telegram/chats")
async def list_chats():
    """List active chat memory sessions."""
    return {
        "active_chats": [
            {"chat_id": cid, "messages": len(msgs)}
            for cid, msgs in chat_memory._memory.items()
        ]
    }


def main():
    if not HAS_FASTAPI:
        print("ERROR: FastAPI not installed. Run: pip install fastapi uvicorn")
        sys.exit(1)

    logger.info("Starting SCBE Telegram Webhook Server on port 8500")
    uvicorn.run(app, host="127.0.0.1", port=8500, log_level="info")


if __name__ == "__main__":
    main()
