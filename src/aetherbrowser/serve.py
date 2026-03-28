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
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.aetherbrowser.ws_feed import WsFeed, MsgType, Agent, Zone
from src.aetherbrowser.agents import AgentSquad, TongueRole, AgentState
from src.aetherbrowser.command_planner import CommandPlan, build_command_plan
from src.aetherbrowser.page_analyzer import PageAnalyzer
from src.aetherbrowser.provider_executor import ProviderExecutor
from src.aetherbrowser.router import OctoArmorRouter

logger = logging.getLogger("aetherbrowser")

app = FastAPI(title="AetherBrowser", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "http://127.0.0.1:*", "http://localhost:*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared instances
feed = WsFeed()
squad = AgentSquad(feed)
analyzer = PageAnalyzer()
router = OctoArmorRouter()
executor = ProviderExecutor()
pending_zone_requests: dict[int, "PendingCommandApproval"] = {}


@dataclass
class PendingCommandApproval:
    plan: CommandPlan
    assignments: list[dict[str, Any]]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "agents": squad.status_snapshot(),
        "providers": router.provider_status_snapshot(),
        "executor": executor.runtime_status_snapshot(),
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
        pending_zone_requests.clear()
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


async def _handle_command(ws: WebSocket, msg: dict) -> None:
    payload = msg.get("payload", {})
    text = payload.get("text", "")
    if not text:
        await ws.send_json(feed.error("Empty command"))
        return

    routing = payload.get("routing", {}) if isinstance(payload.get("routing"), dict) else {}
    routing_preferences = routing.get("preferences") if isinstance(routing.get("preferences"), dict) else None
    auto_cascade = bool(routing.get("auto_cascade", routing.get("autoCascade", True)))

    plan = build_command_plan(
        text=text,
        squad=squad,
        router=router,
        routing_preferences=routing_preferences,
        auto_cascade=auto_cascade,
    )
    assignments = plan.assignments
    squad.set_state(TongueRole.KO, AgentState.WORKING, model=plan.provider)
    await ws.send_json(feed.agent_status(Agent.KO, "working", model=plan.provider))
    await ws.send_json(
        feed.chat(
            Agent.KO,
            _format_command_summary(plan),
            model=plan.provider,
            payload={"plan": plan.to_dict()},
        )
    )

    if plan.approval_required and plan.review_zone:
        squad.set_state(TongueRole.KO, AgentState.WAITING, model=plan.provider)
        await ws.send_json(feed.agent_status(Agent.KO, "waiting", model=plan.provider))
        zone_request = feed.zone_request(
            Agent.RU,
            Zone[plan.review_zone],
            url=plan.targets[0] if plan.targets else "pending://browser-action",
            action=plan.intent,
            description="; ".join(plan.required_approvals),
        )
        pending_zone_requests[zone_request["seq"]] = PendingCommandApproval(
            plan=plan,
            assignments=assignments,
        )
        await ws.send_json(zone_request)
        return

    await _complete_command_flow(ws, plan, assignments)


async def _handle_page_context(ws: WebSocket, msg: dict) -> None:
    payload = msg.get("payload", {})
    url = payload.get("url", "")
    title = payload.get("title", "")
    text = payload.get("text", "")

    await ws.send_json(feed.agent_status(Agent.CA, "analyzing"))

    result = analyzer.analyze_sync(
        url=url,
        title=title,
        text=text,
        headings=payload.get("headings") or [],
        links=payload.get("links") or [],
        forms=payload.get("forms") or [],
        buttons=payload.get("buttons") or [],
        tabs=payload.get("tabs") or [],
        selection=payload.get("selection", ""),
        page_type=payload.get("page_type", "generic"),
        screenshot=payload.get("screenshot", ""),
    )

    summary_text = (
        f"Page: {result['title']}\n"
        f"Words: {result['word_count']}\n"
        f"Topics: {', '.join(result['topics']) or 'General'}\n"
        f"Intent: {result['intent']}\n"
        f"Risk: {result['risk_tier']}\n"
        f"Type: {result['page_type']}\n"
        f"Headings: {result['heading_count']} | Links: {result['link_count']}"
        f" | Forms: {result['form_count']} | Tabs: {result['tab_count']}\n\n"
        f"{result['summary']}"
    )
    await ws.send_json(
        feed.chat(
            Agent.CA,
            summary_text,
            model="local",
            payload={"page_analysis": result},
        )
    )
    await ws.send_json(feed.agent_status(Agent.CA, "done"))

    if result["topics"]:
        next_action_labels = ", ".join(action["label"] for action in result["next_actions"]) or "none"
        await ws.send_json(
            feed.chat(
                Agent.DR,
                f"Structured topics: {json.dumps(result['topics'])}\nNext actions: {next_action_labels}",
                model="local",
                payload={"page_analysis": result},
            )
        )


async def _handle_zone_response(ws: WebSocket, msg: dict) -> None:
    payload = msg.get("payload", {})
    decision = payload.get("decision", "deny")
    request_seq = payload.get("request_seq")
    pending = pending_zone_requests.pop(request_seq, None)
    if pending is None:
        await ws.send_json(feed.error(f"Unknown zone request: {request_seq}", agent=Agent.RU))
        return

    if decision in {"allow", "allow_once", "add_yellow"}:
        await ws.send_json(
            feed.chat(
                Agent.RU,
                f"Zone decision received: {decision}. Releasing the held browser plan.",
                payload={"plan": pending.plan.to_dict()},
            )
        )
        await _complete_command_flow(ws, pending.plan, pending.assignments)
        return

    squad.set_state(TongueRole.KO, AgentState.ERROR, model=pending.plan.provider)
    await ws.send_json(
        feed.chat(
            Agent.RU,
            f"Zone decision received: {decision}. Browser plan denied.",
            payload={"plan": pending.plan.to_dict()},
        )
    )
    await ws.send_json(feed.agent_status(Agent.KO, "error", model=pending.plan.provider))


async def _complete_command_flow(
    ws: WebSocket,
    plan: CommandPlan,
    assignments: list[dict[str, Any]],
) -> None:
    for assignment in assignments:
        if assignment["role"] == TongueRole.KO:
            continue
        role_agent = Agent[assignment["role"].value]
        await ws.send_json(feed.agent_status(role_agent, "assigned"))

    try:
        execution = await executor.execute(plan)
    except Exception as exc:
        squad.set_state(TongueRole.KO, AgentState.ERROR, model=plan.provider)
        await ws.send_json(feed.error(f"Command execution failed: {exc}", agent=Agent.KO))
        await ws.send_json(feed.agent_status(Agent.KO, "error", model=plan.provider))
        return

    await ws.send_json(
        feed.chat(
            Agent.KO,
            execution.text,
            model=execution.model_id,
            payload={"execution": execution.to_dict()},
        )
    )
    await ws.send_json(
        feed.chat(
            Agent.DR,
            (
                f"Execution provider={execution.provider}, model={execution.model_id}, "
                f"fallback_used={execution.fallback_used}, attempted={', '.join(execution.attempted)}."
            ),
            model="local",
            payload={"execution": execution.to_dict()},
        )
    )

    squad.set_state(TongueRole.KO, AgentState.DONE, model=execution.model_id)
    await ws.send_json(feed.agent_status(Agent.KO, "done", model=execution.model_id))


def _format_command_summary(plan: CommandPlan) -> str:
    targets = ", ".join(plan.targets) if plan.targets else "generic browser lane"
    approvals = ", ".join(plan.required_approvals) if plan.required_approvals else "none"
    next_action = plan.next_actions[0].label if plan.next_actions else "review plan"
    return (
        f"Intent: {plan.intent}\n"
        f"Task: {plan.task_type} | Complexity: {plan.complexity.value} | Risk: {plan.risk_tier}\n"
        f"Engine: {plan.preferred_engine} | Target: {targets}\n"
        f"Approvals: {approvals}\n"
        f"Lead action: {next_action}\n"
        f"Model: {plan.provider} ({plan.selection_reason}) | Auto-cascade: {plan.auto_cascade}"
    )
