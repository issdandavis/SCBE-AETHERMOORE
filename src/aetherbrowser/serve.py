"""
AetherBrowser Backend Server
==============================

FastAPI + WebSocket entry point. The Chrome extension connects here.

Start:
    python -m uvicorn src.aetherbrowser.serve:app --host 127.0.0.1 --port 8002
"""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.aetherbrowser.ws_feed import WsFeed, MsgType, Agent
from src.aetherbrowser.agents import AgentSquad, TongueRole, AgentState
from src.aetherbrowser.page_analyzer import PageAnalyzer
from src.aetherbrowser.router import OctoArmorRouter

logger = logging.getLogger("aetherbrowser")

app = FastAPI(title="AetherBrowser", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
feed = WsFeed()
squad = AgentSquad(feed)
analyzer = PageAnalyzer()
router = OctoArmorRouter()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "agents": squad.status_snapshot(),
    }


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = WsFeed.parse(raw)
            except (ValueError, json.JSONDecodeError) as e:
                await ws.send_json(feed.error(str(e)))
                continue

            msg_type = msg.get("type")

            if msg_type == MsgType.COMMAND.value:
                await _handle_command(ws, msg)
            elif msg_type == MsgType.PAGE_CONTEXT.value:
                await _handle_page_context(ws, msg)
            elif msg_type == MsgType.ZONE_RESPONSE.value:
                await _handle_zone_response(ws, msg)
            else:
                await ws.send_json(feed.error(f"Unhandled message type: {msg_type}"))

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def _handle_command(ws: WebSocket, msg: dict) -> None:
    text = msg.get("payload", {}).get("text", "")
    if not text:
        await ws.send_json(feed.error("Empty command"))
        return

    # Decompose task
    assignments = squad.decompose(text)

    # Score complexity and pick model for KO
    complexity = router.score_complexity(text)
    model = router.select_model(complexity, role="KO")

    # Send KO's initial response
    squad.set_state(TongueRole.KO, AgentState.WORKING, model=model.provider.value)
    await ws.send_json(feed.agent_status(Agent.KO, "working", model=model.provider.value))
    await ws.send_json(feed.chat(
        Agent.KO,
        f"Received: '{text}'. Complexity: {complexity.value}. "
        f"Assigning {len(assignments)} agents. Model: {model.provider.value}.",
        model=model.provider.value,
    ))

    # Assign other agents
    for a in assignments:
        if a["role"] != TongueRole.KO:
            role_agent = Agent[a["role"].value]
            await ws.send_json(feed.agent_status(role_agent, "assigned"))

    squad.set_state(TongueRole.KO, AgentState.DONE)
    await ws.send_json(feed.agent_status(Agent.KO, "done"))


async def _handle_page_context(ws: WebSocket, msg: dict) -> None:
    payload = msg.get("payload", {})
    url = payload.get("url", "")
    title = payload.get("title", "")
    text = payload.get("text", "")

    await ws.send_json(feed.agent_status(Agent.CA, "analyzing"))

    result = analyzer.analyze_sync(url=url, title=title, text=text)

    summary_text = (
        f"Page: {result['title']}\n"
        f"Words: {result['word_count']}\n"
        f"Topics: {', '.join(result['topics']) or 'General'}\n\n"
        f"{result['summary']}"
    )
    await ws.send_json(feed.chat(Agent.CA, summary_text, model="local"))
    await ws.send_json(feed.agent_status(Agent.CA, "done"))

    if result["topics"]:
        await ws.send_json(feed.chat(
            Agent.DR,
            f"Structured topics: {json.dumps(result['topics'])}",
            model="local",
        ))


async def _handle_zone_response(ws: WebSocket, msg: dict) -> None:
    payload = msg.get("payload", {})
    decision = payload.get("decision", "deny")
    await ws.send_json(feed.chat(
        Agent.RU,
        f"Zone decision received: {decision}",
    ))
