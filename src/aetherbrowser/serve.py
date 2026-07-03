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
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.aetherbrowser.ws_feed import WsFeed, MsgType, Agent, Zone
from src.aetherbrowser.agents import AgentSquad, TongueRole, AgentState
from src.aetherbrowser.command_planner import CommandPlan, build_command_plan
from src.aetherbrowser.page_analyzer import PageAnalyzer
from src.aetherbrowser.provider_executor import ProviderExecutor
from src.aetherbrowser.router import OctoArmorRouter
from src.aetherbrowser.topology_engine import compute_page_topology

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
shared_headless_context: dict[str, Any] = {
    "page_context": None,
    "page_analysis": None,
    "topology": None,
    "updated_at": None,
}
pending_browser_actions: list[dict[str, Any]] = []
pending_controller_events: list[dict[str, Any]] = []
_headless_seq = count(1)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HEADLESS_RUN_ARTIFACT_DIR = _REPO_ROOT / "artifacts" / "aetherbrowser_headless_runs"

_SAFE_CONTROLLER_EVENTS = {
    "observe",
    "move_up",
    "move_down",
    "move_left",
    "move_right",
    "back",
    "forward",
    "reload",
    "escape",
}
_HELD_CONTROLLER_EVENTS = {
    "primary",
    "secondary",
    "type",
    "paste",
    "submit",
}


@dataclass
class PendingCommandApproval:
    plan: CommandPlan
    assignments: list[dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_slug(value: str, *, fallback: str = "page") -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-._")
    return (slug or fallback)[:80]


def _validate_headless_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    if url == "about:blank":
        return url
    if url.startswith("data:text/html,") and len(url) <= 20_000:
        return url
    raise HTTPException(status_code=400, detail="url must be http(s), about:blank, or a short data:text/html URL")


def _normalize_timeout_ms(value: Any, *, default: int = 20_000, minimum: int = 3_000, maximum: int = 60_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _normalize_limit(value: Any, *, default: int = 10, minimum: int = 1, maximum: int = 50) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _bounded_append(queue: list[dict[str, Any]], item: dict[str, Any], *, limit: int = 100) -> None:
    queue.append(item)
    if len(queue) > limit:
        del queue[: len(queue) - limit]


def _normalize_browser_items(items: Any, *, text_key: str = "text") -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            normalized.append(item)
        elif item is not None:
            normalized.append({text_key: str(item)})
    return normalized


def _analyze_page_payload(payload: dict[str, Any]) -> dict[str, Any]:
    url = str(payload.get("url", ""))
    title = str(payload.get("title", ""))
    text = str(payload.get("text", ""))
    headings = _normalize_browser_items(payload.get("headings"))
    links = _normalize_browser_items(payload.get("links"), text_key="href")
    forms = _normalize_browser_items(payload.get("forms"))
    buttons = _normalize_browser_items(payload.get("buttons"))
    tabs = _normalize_browser_items(payload.get("tabs"))

    result = analyzer.analyze_sync(
        url=url,
        title=title,
        text=text,
        headings=headings,
        links=links,
        forms=forms,
        buttons=buttons,
        tabs=tabs,
        selection=payload.get("selection", ""),
        page_type=payload.get("page_type", "generic"),
        screenshot=payload.get("screenshot", ""),
    )
    topology = compute_page_topology(
        url=url,
        title=result["title"],
        text=text,
        links=links,
        headings=headings,
        topics=result.get("topics") or [],
        risk_tier=result.get("risk_tier", "low"),
    )
    result["topology_lens"] = _derive_topology_lens(
        result=result,
        topology=topology,
        forms=forms,
        buttons=buttons,
    )

    page_context = {
        "url": url,
        "title": result["title"],
        "word_count": result["word_count"],
        "risk_tier": result["risk_tier"],
        "page_type": result["page_type"],
    }
    return {
        "page_context": page_context,
        "page_analysis": result,
        "topology": topology,
    }


def _build_headless_plan(
    *,
    text: str,
    routing: dict[str, Any] | None = None,
) -> CommandPlan:
    routing = routing or {}
    routing_preferences = routing.get("preferences") if isinstance(routing.get("preferences"), dict) else None
    auto_cascade = bool(routing.get("auto_cascade", routing.get("autoCascade", True)))
    plan = build_command_plan(
        text=text,
        squad=squad,
        router=router,
        routing_preferences=routing_preferences,
        auto_cascade=auto_cascade,
    )
    if plan.risk_tier == "high" and not plan.approval_required:
        import dataclasses

        return dataclasses.replace(plan, approval_required=True, review_zone="RED")
    return plan


async def _run_headless_readonly(payload: dict[str, Any]) -> dict[str, Any]:
    action = str(payload.get("action", "inspect")).strip().lower()
    if action not in {"inspect", "read", "screenshot"}:
        raise HTTPException(status_code=400, detail="headless run action must be inspect, read, or screenshot")

    url = _validate_headless_url(payload.get("url"))
    timeout_ms = _normalize_timeout_ms(payload.get("timeout_ms"))
    full_page = bool(payload.get("full_page", False))
    run_id = f"{_stamp()}_{_safe_slug(urlparse(url).netloc or urlparse(url).path or action)}_{next(_headless_seq)}"
    run_dir = _HEADLESS_RUN_ARTIFACT_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    from agents.playwright_runtime import PlaywrightRuntime

    runtime = PlaywrightRuntime()
    started_at = _utc_now()
    try:
        await runtime.launch(headless=True)
        final_url = await runtime.navigate(url, timeout=timeout_ms)
        title = await runtime.title()
        text = await runtime.evaluate("() => document.body ? document.body.innerText : ''")
        html = await runtime.content()
        page_bits = await runtime.evaluate(
            """() => ({
              headings: Array.from(document.querySelectorAll('h1,h2,h3')).slice(0, 24)
                .map((el) => ({ level: el.tagName, text: (el.innerText || el.textContent || '').trim() })),
              links: Array.from(document.querySelectorAll('a[href]')).slice(0, 80)
                .map((el) => ({ text: (el.innerText || el.textContent || '').trim(), href: el.href })),
              buttons: Array.from(document.querySelectorAll('button,[role="button"],input[type="button"],input[type="submit"]')).slice(0, 40)
                .map((el) => ({ text: (el.innerText || el.value || el.textContent || '').trim(), type: el.type || el.getAttribute('role') || 'button' })),
              forms: Array.from(document.querySelectorAll('form')).slice(0, 20)
                .map((form, index) => ({
                  index,
                  method: (form.getAttribute('method') || 'get').toLowerCase(),
                  fields: Array.from(form.querySelectorAll('input,textarea,select')).slice(0, 40)
                    .map((field) => ({ name: field.getAttribute('name') || '', type: field.getAttribute('type') || field.tagName.toLowerCase() }))
                }))
            })"""
        )
        screenshot_path = run_dir / "screenshot.png"
        text_path = run_dir / "visible_text.txt"
        html_path = run_dir / "page.html"
        receipt_path = run_dir / "receipt.json"

        screenshot_bytes = await runtime.screenshot(path=str(screenshot_path), full_page=full_page)
        text_path.write_text(str(text or ""), encoding="utf-8")
        html_path.write_text(str(html or ""), encoding="utf-8")

        analyzed = _analyze_page_payload(
            {
                "url": final_url,
                "title": title,
                "text": str(text or ""),
                "headings": (page_bits or {}).get("headings") or [],
                "links": (page_bits or {}).get("links") or [],
                "forms": (page_bits or {}).get("forms") or [],
                "buttons": (page_bits or {}).get("buttons") or [],
                "page_type": "headless-run",
            }
        )

        receipt = {
            "ok": True,
            "schema": "aetherbrowser_headless_run_v0",
            "run_id": run_id,
            "action": action,
            "started_at": started_at,
            "finished_at": _utc_now(),
            "url": final_url,
            "title": title,
            "word_count": analyzed["page_analysis"]["word_count"],
            "risk_tier": analyzed["page_analysis"]["risk_tier"],
            "page_type": analyzed["page_analysis"]["page_type"],
            "artifacts": {
                "dir": str(run_dir),
                "receipt": str(receipt_path),
                "screenshot": str(screenshot_path),
                "text": str(text_path),
                "html": str(html_path),
            },
            "screenshot_bytes": len(screenshot_bytes),
            "text_tail": str(text or "")[-4000:],
            "page_analysis": analyzed["page_analysis"],
            "topology": analyzed["topology"],
            "boundaries": {
                "mode": "fresh-headless-context",
                "logged_in_state": "not_used",
                "mutations": "none",
            },
        }
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=True), encoding="utf-8")
        shared_headless_context.update(
            {
                "page_context": analyzed["page_context"],
                "page_analysis": analyzed["page_analysis"],
                "topology": analyzed["topology"],
                "updated_at": receipt["finished_at"],
                "source": "headless-run",
                "receipt_path": str(receipt_path),
            }
        )
        return receipt
    finally:
        await runtime.close()


def _summarize_headless_run(receipt_path: Path) -> dict[str, Any] | None:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        stat = receipt_path.stat()
    except (OSError, json.JSONDecodeError):
        return None

    artifacts = receipt.get("artifacts") if isinstance(receipt.get("artifacts"), dict) else {}
    return {
        "run_id": receipt.get("run_id") or receipt_path.parent.name,
        "action": receipt.get("action"),
        "url": receipt.get("url"),
        "title": receipt.get("title"),
        "finished_at": receipt.get("finished_at"),
        "risk_tier": receipt.get("risk_tier"),
        "word_count": receipt.get("word_count"),
        "screenshot_bytes": receipt.get("screenshot_bytes"),
        "receipt": str(receipt_path),
        "screenshot": artifacts.get("screenshot"),
        "text": artifacts.get("text"),
        "html": artifacts.get("html"),
        "mtime": stat.st_mtime,
        "boundaries": receipt.get("boundaries") if isinstance(receipt.get("boundaries"), dict) else {},
    }


def _list_headless_runs(limit: Any = 10) -> list[dict[str, Any]]:
    limit_int = _normalize_limit(limit)
    if not _HEADLESS_RUN_ARTIFACT_DIR.exists():
        return []

    runs: list[dict[str, Any]] = []
    for receipt_path in _HEADLESS_RUN_ARTIFACT_DIR.glob("*/receipt.json"):
        summary = _summarize_headless_run(receipt_path)
        if summary is not None:
            runs.append(summary)
    runs.sort(key=lambda item: float(item.get("mtime") or 0), reverse=True)
    for item in runs:
        item.pop("mtime", None)
    return runs[:limit_int]


def _derive_topology_lens(
    *,
    result: dict[str, Any],
    topology: dict[str, Any],
    forms: list[dict[str, Any]],
    buttons: list[dict[str, Any]],
) -> dict[str, Any]:
    approvals = [str(item).lower() for item in result.get("required_approvals", [])]
    boundary_signals: list[str] = []

    has_password_field = any(
        any(str(field.get("type", "")).lower() == "password" for field in form.get("fields", [])) for form in forms
    )
    if has_password_field or any("authentication" in item or "credential" in item for item in approvals):
        boundary_signals.append("identity boundary present")

    if buttons or any("high-impact" in item or "payment" in item for item in approvals):
        boundary_signals.append("state-change controls exposed")

    nodes = topology.get("nodes", [])
    red_radii = [float(node.get("radius", 0.0)) for node in nodes if node.get("zone") == Zone.RED.value]
    yellow_radii = [float(node.get("radius", 0.0)) for node in nodes if node.get("zone") == Zone.YELLOW.value]

    if result.get("risk_tier") == "high" or red_radii:
        zone = Zone.RED.value
        trust_distance = max(red_radii or yellow_radii or [0.0])
    elif result.get("risk_tier") == "medium" or yellow_radii:
        zone = Zone.YELLOW.value
        trust_distance = max(yellow_radii or [0.0])
    else:
        zone = Zone.GREEN.value
        trust_distance = 0.0

    return {
        "zone": zone,
        "trust_distance": round(trust_distance, 6),
        "boundary_signals": boundary_signals,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "agents": squad.status_snapshot(),
        "providers": router.provider_status_snapshot(),
        "executor": executor.runtime_status_snapshot(),
    }


@app.get("/context")
def context():
    return {
        "status": "ok",
        "schema": "aetherbrowser_context_v0",
        "generated_at": _utc_now(),
        "context": shared_headless_context,
        "pending": {
            "browser_actions": len(pending_browser_actions),
            "controller_events": len(pending_controller_events),
            "zone_requests": len(pending_zone_requests),
        },
    }


@app.get("/headless/capabilities")
def headless_capabilities():
    return {
        "ok": True,
        "schema": "aetherbrowser_headless_capabilities_v0",
        "generated_at": _utc_now(),
        "backend": "src.aetherbrowser.serve",
        "surfaces": [
            "headless-http",
            "websocket",
            "headed-frontdoor-bridge",
            "visible-browser-queue",
        ],
        "routes": {
            "health": {"method": "GET", "path": "/health", "gate": "read-only"},
            "context": {"method": "GET", "path": "/context", "gate": "read-only"},
            "capabilities": {"method": "GET", "path": "/headless/capabilities", "gate": "read-only"},
            "command": {"method": "POST", "path": "/headless/command", "gate": "plan-first"},
            "run": {"method": "POST", "path": "/headless/run", "gate": "read-only-evidence"},
            "runs": {"method": "GET", "path": "/headless/runs", "gate": "read-only"},
            "page_context": {"method": "POST", "path": "/headless/page-context", "gate": "read-only"},
            "browser_action": {"method": "POST", "path": "/headless/browser-action", "gate": "queued"},
            "browser_actions": {"method": "GET", "path": "/headless/browser-actions", "gate": "read-only"},
            "controller_state": {"method": "GET", "path": "/headless/controller-state", "gate": "read-only"},
            "controller_event": {"method": "POST", "path": "/headless/controller-event", "gate": "event-policy"},
            "ws": {"method": "WS", "path": "/ws", "gate": "message-policy"},
        },
        "controller": {
            "model": "webpage_as_game_state",
            "safe_events": sorted(_SAFE_CONTROLLER_EVENTS),
            "held_events": sorted(_HELD_CONTROLLER_EVENTS),
            "haptics": ["selection", "impact", "success", "warning", "error"],
        },
        "boundaries": {
            "execution": "HTTP routes plan and queue; visible/headless consumers execute queued actions.",
            "headless_run": "fresh headless browser context for read-only inspect/read/screenshot receipts",
            "mutation_gate": "state-changing commands and held controller events require approval",
            "host_scope": "localhost",
            "secrets": "not_returned",
        },
    }


@app.get("/headless/runs")
def headless_runs(limit: int = 10):
    runs = _list_headless_runs(limit)
    return {
        "ok": True,
        "schema": "aetherbrowser_headless_runs_v0",
        "generated_at": _utc_now(),
        "artifact_dir": str(_HEADLESS_RUN_ARTIFACT_DIR),
        "count": len(runs),
        "runs": runs,
    }


@app.post("/headless/page-context")
def headless_page_context(payload: dict[str, Any]):
    analyzed = _analyze_page_payload(payload)
    shared_headless_context.update(
        {
            **analyzed,
            "updated_at": _utc_now(),
        }
    )
    return {
        "status": "analyzed",
        "schema": "aetherbrowser_headless_page_context_v0",
        "context": shared_headless_context,
    }


@app.post("/headless/command")
async def headless_command(payload: dict[str, Any]):
    text = str(payload.get("text", "")).strip()
    if not text:
        return {
            "status": "error",
            "error": "Empty command",
        }

    routing = payload.get("routing") if isinstance(payload.get("routing"), dict) else None
    plan = _build_headless_plan(text=text, routing=routing)
    plan_dict = plan.to_dict()

    if plan.approval_required:
        return {
            "status": "approval_required",
            "schema": "aetherbrowser_headless_command_v0",
            "source": payload.get("source", "headless-http"),
            "plan": plan_dict,
            "approval": {
                "zone": plan.review_zone,
                "required_approvals": plan.required_approvals,
            },
        }

    if not bool(payload.get("execute", False)):
        return {
            "status": "planned",
            "schema": "aetherbrowser_headless_command_v0",
            "source": payload.get("source", "headless-http"),
            "plan": plan_dict,
        }

    execution = await executor.execute(plan)
    return {
        "status": "executed",
        "schema": "aetherbrowser_headless_command_v0",
        "source": payload.get("source", "headless-http"),
        "plan": plan_dict,
        "execution": execution.to_dict(),
    }


@app.post("/headless/run")
async def headless_run(payload: dict[str, Any]):
    try:
        result = await _run_headless_readonly(payload)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        return {
            "ok": False,
            "schema": "aetherbrowser_headless_run_v0",
            "status": "error",
            "error": str(exc),
        }


@app.post("/headless/browser-action")
def headless_browser_action(payload: dict[str, Any]):
    action = str(payload.get("action", "")).strip()
    if not action:
        return {
            "status": "error",
            "error": "Missing action",
        }

    record = {
        "id": next(_headless_seq),
        "schema": "aetherbrowser_queued_browser_action_v0",
        "queued_at": _utc_now(),
        "source": payload.get("source", "headless-http"),
        "action": action,
        "url": payload.get("url"),
        "selector": payload.get("selector"),
        "text": payload.get("text"),
        "payload": payload,
        "status": "pending",
    }
    _bounded_append(pending_browser_actions, record)
    return {
        "status": "queued",
        "queued": record,
        "pending_count": len(pending_browser_actions),
    }


@app.get("/headless/browser-actions")
def headless_browser_actions():
    return {
        "status": "ok",
        "schema": "aetherbrowser_browser_actions_v0",
        "pending": pending_browser_actions,
    }


@app.get("/headless/controller-state")
def headless_controller_state():
    page_context = shared_headless_context.get("page_context") or {}
    return {
        "status": "ok",
        "schema": "aetherbrowser_controller_state_v0",
        "model": "webpage_as_game_state",
        "generated_at": _utc_now(),
        "page": page_context,
        "available_events": sorted(_SAFE_CONTROLLER_EVENTS | _HELD_CONTROLLER_EVENTS),
        "safe_events": sorted(_SAFE_CONTROLLER_EVENTS),
        "held_events": sorted(_HELD_CONTROLLER_EVENTS),
        "pending_events": pending_controller_events,
    }


@app.post("/headless/controller-event")
def headless_controller_event(payload: dict[str, Any]):
    event = str(payload.get("event", "")).strip().lower()
    if not event:
        return {
            "status": "error",
            "error": "Missing event",
        }

    if event in _HELD_CONTROLLER_EVENTS:
        return {
            "status": "approval_required",
            "schema": "aetherbrowser_controller_event_v0",
            "event": event,
            "approval": {
                "zone": "YELLOW",
                "required_approvals": ["Controller event can change page state"],
            },
        }

    if event not in _SAFE_CONTROLLER_EVENTS:
        return {
            "status": "rejected",
            "schema": "aetherbrowser_controller_event_v0",
            "event": event,
            "error": "Unknown controller event",
            "allowed": sorted(_SAFE_CONTROLLER_EVENTS | _HELD_CONTROLLER_EVENTS),
        }

    record = {
        "id": next(_headless_seq),
        "schema": "aetherbrowser_queued_controller_event_v0",
        "queued_at": _utc_now(),
        "source": payload.get("source", "headless-http"),
        "event": event,
        "intensity": payload.get("intensity"),
        "payload": payload,
        "status": "pending",
    }
    _bounded_append(pending_controller_events, record)
    return {
        "status": "queued",
        "queued": record,
        "pending_count": len(pending_controller_events),
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
            try:
                if msg_type == MsgType.COMMAND.value:
                    await _handle_command(ws, msg)
                elif msg_type == MsgType.PAGE_CONTEXT.value:
                    await _handle_page_context(ws, msg)
                elif msg_type == MsgType.ZONE_RESPONSE.value:
                    await _handle_zone_response(ws, msg)
                else:
                    await ws.send_json(feed.error(f"Unhandled message type: {msg_type}"))
            except Exception as handler_exc:
                # A4: never drop the client on handler failure — return JSON so tests/clients
                # do not block forever on receive_json waiting for a reply.
                logger.error("WebSocket handler error: %s", handler_exc, exc_info=True)
                await ws.send_json(feed.error(f"Request failed: {handler_exc}"))

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
    # A4: force RED gate on high-risk actions even if keyword heuristics missed
    if plan.risk_tier == "high" and not plan.approval_required:
        import dataclasses

        plan = dataclasses.replace(plan, approval_required=True, review_zone="RED")

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
    topology = compute_page_topology(
        url=url,
        title=result["title"],
        text=text,
        links=payload.get("links") or [],
        headings=payload.get("headings") or [],
        topics=result.get("topics") or [],
        risk_tier=result.get("risk_tier", "low"),
    )
    result["topology_lens"] = _derive_topology_lens(
        result=result,
        topology=topology,
        forms=payload.get("forms") or [],
        buttons=payload.get("buttons") or [],
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
    await ws.send_json(
        feed.topology(
            Agent.CA,
            topology,
            model="local",
            zone=result["topology_lens"]["zone"],
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
