"""
AetherBrowse Agent Runtime — WebSocket Server
===============================================
Runs as a local sidecar to Electron. Hosts the agent loop:
PERCEIVE → PLAN → GOVERN → EXECUTE

Start: python aetherbrowse/runtime/server.py
Connects: ws://127.0.0.1:8400/ws
"""

import asyncio
import json
import logging
import sys
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Optional

# Add project root to path for SCBE imports
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from aetherbrowse.runtime.env_bootstrap import bootstrap_runtime_env

bootstrap_runtime_env()

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("aetherbrowse-runtime")

# Import perceiver, planner, and hydra bridge
from aetherbrowse.runtime.perceiver import perceive, PagePerception
from aetherbrowse.runtime.planner import create_plan, log_plan_result, ActionPlan
from aetherbrowse.runtime.hydra_bridge import register_hydra_routes

RUNTIME_ARTIFACTS_DIR = ROOT / "artifacts" / "agent_comm" / "aetherbrowse"
RUN_LOG_PATH = RUNTIME_ARTIFACTS_DIR / "runs.jsonl"

# ---------------------------------------------------------------------------
#  Agent State
# ---------------------------------------------------------------------------

class AgentRuntime:
    """Central runtime managing perception, planning, governance, execution."""

    def __init__(self):
        self.ws: Optional[WebSocket] = None
        self.worker_ws: Optional[WebSocket] = None
        self.agents = {
            "kael": {"role": "executor", "tongue": "CA", "status": "idle"},
            "aria": {"role": "validator", "tongue": "AV", "status": "idle"},
            "zara": {"role": "leader", "tongue": "KO", "status": "idle"},
            "polly": {"role": "observer", "tongue": "UM", "status": "idle"},
        }
        self.current_url = ""
        self.action_log = []
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._request_counter = 0
        self._runs_by_id: dict[str, dict[str, Any]] = {}
        self._recent_runs: deque[dict[str, Any]] = deque(maxlen=50)
        self.last_perception: Optional[PagePerception] = None
        RUNTIME_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    async def send(self, msg: dict):
        """Send message to Electron frontend."""
        if self.ws:
            await self.ws.send_json(msg)

    async def send_to_worker(
        self,
        action: str,
        *,
        wait_for_result: bool = False,
        timeout_s: float = 45.0,
        **kwargs,
    ) -> Optional[dict]:
        """Send a browser command to the Playwright worker."""
        if not self.worker_ws:
            logger.warning("No Playwright worker connected")
            return None
        self._request_counter += 1
        req_id = str(self._request_counter)
        msg = {"type": "browser-command", "action": action, "requestId": req_id, **kwargs}
        result_future: Optional[asyncio.Future] = None
        if wait_for_result:
            result_future = asyncio.get_running_loop().create_future()
            self._pending_requests[req_id] = result_future
        await self.worker_ws.send_json(msg)
        logger.info(f"Sent to worker: {action} (req {req_id})")
        if not wait_for_result:
            return {"requestId": req_id, "sent": True}

        try:
            assert result_future is not None
            result = await asyncio.wait_for(result_future, timeout=timeout_s)
            return {"requestId": req_id, "sent": True, "result": result}
        except asyncio.TimeoutError:
            logger.warning("Worker timeout on req %s action=%s", req_id, action)
            return {"requestId": req_id, "sent": True, "error": f"timeout after {timeout_s:.0f}s", "action": action}
        finally:
            self._pending_requests.pop(req_id, None)

    def resolve_worker_result(self, request_id: Any, result: dict[str, Any]) -> None:
        """Resolve a pending worker result by request id."""
        if request_id is None:
            return
        req_id = str(request_id)
        fut = self._pending_requests.pop(req_id, None)
        if fut and not fut.done():
            fut.set_result(result)

    @staticmethod
    def _result_has_error(result: Any) -> bool:
        if result is None:
            return True
        if not isinstance(result, dict):
            return False
        if result.get("error"):
            return True
        if result.get("ok") is False:
            return True
        return False

    @staticmethod
    def _result_error_text(result: Any) -> str:
        if result is None:
            return "no_result"
        if isinstance(result, dict):
            if result.get("error"):
                return str(result.get("error"))
            if result.get("ok") is False:
                return str(result.get("message") or "action returned ok=false")
        return ""

    @staticmethod
    def _retry_budget_for_action(step_action: str, metadata: dict[str, Any]) -> int:
        if isinstance(metadata, dict):
            raw = metadata.get("max_retries")
            if raw is not None:
                try:
                    value = int(raw)
                    return max(0, min(value, 5))
                except (TypeError, ValueError):
                    pass
        defaults = {
            "navigate": 2,
            "click": 2,
            "fill": 2,
            "wait_for": 2,
            "snapshot": 1,
            "set_network_profile": 1,
            "evaluate": 0,
            "upload": 0,
            "huggingface_upload": 0,
        }
        return defaults.get(step_action, 1)

    def _new_run(self, goal: str, plan: ActionPlan) -> dict[str, Any]:
        run_id = f"run-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        run = {
            "run_id": run_id,
            "goal": goal,
            "status": "running",
            "created_at": time.time(),
            "updated_at": time.time(),
            "plan_method": plan.method,
            "plan_confidence": float(plan.confidence),
            "steps_total": len(plan.steps),
            "steps_completed": 0,
            "steps": [],
            "error": "",
        }
        self._runs_by_id[run_id] = run
        self._recent_runs.appendleft(run)
        self._write_run_event({"type": "run_started", **self._run_public(run)})
        return run

    def _run_public(self, run: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": run.get("run_id"),
            "goal": run.get("goal"),
            "status": run.get("status"),
            "plan_method": run.get("plan_method"),
            "plan_confidence": run.get("plan_confidence"),
            "steps_total": run.get("steps_total"),
            "steps_completed": run.get("steps_completed"),
            "updated_at": run.get("updated_at"),
            "error": run.get("error", ""),
            "steps": run.get("steps", []),
        }

    def _write_run_event(self, payload: dict[str, Any]) -> None:
        event = {"timestamp": time.time(), **payload}
        with RUN_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")

    def _update_run(self, run: dict[str, Any], **updates: Any) -> None:
        run.update(updates)
        run["updated_at"] = time.time()

    async def _emit_step_event(
        self,
        *,
        run_id: str,
        step_index: int,
        step_total: int,
        status: str,
        message: str,
        payload: Optional[dict[str, Any]] = None,
        coherence: float = 0.92,
        decision: str = "ALLOW",
    ) -> None:
        body = {
            "type": "governance-event",
            "from": "kael",
            "message": message,
            "governance": {"decision": decision, "coherence": coherence},
            "payload": {
                "run_id": run_id,
                "step_index": step_index,
                "step_total": step_total,
                "status": status,
            },
        }
        if payload:
            body["payload"].update(payload)
        await self.send(body)

    async def handle_user_command(self, text: str):
        """Handle natural language command from user."""
        logger.info(f"User command: {text}")
        command = text.strip().lower()

        # Log the governance check
        await self.send({
            "type": "governance-event",
            "from": "zara",
            "message": f"Evaluating command: {text}",
            "governance": {"decision": "ALLOW", "coherence": 0.95},
        })

        # For v0.1: simple URL navigation detection
        if command.startswith("go to ") or command.startswith("navigate to "):
            url = text.replace("go to ", "").replace("navigate to ", "").strip()
            if not url.startswith("http"):
                url = "https://" + url
            await self.send({
                "type": "browser-command",
                "action": "navigate",
                "url": url,
            })
            await self.send({
                "type": "governance-event",
                "from": "kael",
                "message": f"Navigating to {url}",
                "governance": {"decision": "ALLOW", "coherence": 0.92},
            })
        elif command.startswith("snapshot") or command.startswith("perceive"):
            # Request a perception snapshot via Playwright worker
            if self.worker_ws:
                await self.send_to_worker("snapshot")
                await self.send({
                    "type": "governance-event",
                    "from": "polly",
                    "message": "Perceiving current page...",
                    "governance": {"decision": "ALLOW", "coherence": 0.95},
                })
            else:
                await self.send({
                    "type": "governance-event",
                    "from": "polly",
                    "message": "No Playwright worker connected. Cannot perceive.",
                    "governance": {"decision": "QUARANTINE", "coherence": 0.5},
                })
        elif command.startswith("switch profile ") or command.startswith("use profile "):
            profile_id = command.split("profile ", 1)[1].strip() if "profile " in command else ""
            if self.worker_ws and profile_id:
                result = await self.send_to_worker("switch_profile", wait_for_result=True, profile_id=profile_id)
                await self.send(
                    {
                        "type": "governance-event",
                        "from": "kael",
                        "message": f"Profile switch result: {str(result.get('result') if isinstance(result, dict) else result)[:180]}",
                        "governance": {"decision": "ALLOW", "coherence": 0.92},
                    }
                )
            else:
                await self.send(
                    {
                        "type": "governance-event",
                        "from": "kael",
                        "message": "No worker/profile id available for profile switch.",
                        "governance": {"decision": "QUARANTINE", "coherence": 0.55},
                    }
                )
        elif command in {"list profiles", "show profiles"}:
            if self.worker_ws:
                result = await self.send_to_worker("list_profiles", wait_for_result=True)
                payload = result.get("result", {}) if isinstance(result, dict) else {}
                await self.send(
                    {
                        "type": "governance-event",
                        "from": "kael",
                        "message": f"Profiles: {payload}",
                        "governance": {"decision": "ALLOW", "coherence": 0.93},
                    }
                )
            else:
                await self.send(
                    {
                        "type": "governance-event",
                        "from": "kael",
                        "message": "No worker connected. Cannot list profiles.",
                        "governance": {"decision": "QUARANTINE", "coherence": 0.55},
                    }
                )
        elif "dark web" in command or " tor" in f" {command} " or "onion" in command:
            if self.worker_ws:
                await self.send_to_worker("set_network_profile", network_profile="dark")
                await self.send({
                    "type": "governance-event",
                    "from": "zara",
                    "message": "Dark profile selected. Routing via configured proxy lane (if available).",
                    "governance": {"decision": "ALLOW", "coherence": 0.86},
                })
            else:
                await self.send({
                    "type": "governance-event",
                    "from": "zara",
                    "message": "No Playwright worker connected. Cannot switch to dark profile.",
                    "governance": {"decision": "QUARANTINE", "coherence": 0.52},
                })
        elif "extract article" in command or "reader mode" in command:
            if self.worker_ws:
                await self.send_to_worker("extract_article")
                await self.send({
                    "type": "governance-event",
                    "from": "polly",
                    "message": "Extracting article from current page.",
                    "governance": {"decision": "ALLOW", "coherence": 0.96},
                })
            else:
                await self.send({
                    "type": "governance-event",
                    "from": "polly",
                    "message": "No Playwright worker connected. Cannot extract article.",
                    "governance": {"decision": "QUARANTINE", "coherence": 0.5},
                })
        elif "extract video" in command or "video mode" in command or "watch video" in command:
            if self.worker_ws:
                await self.send_to_worker("extract_video")
                await self.send({
                    "type": "governance-event",
                    "from": "polly",
                    "message": "Inspecting page video/media content.",
                    "governance": {"decision": "ALLOW", "coherence": 0.96},
                })
            else:
                await self.send({
                    "type": "governance-event",
                    "from": "polly",
                    "message": "No Playwright worker connected. Cannot inspect media.",
                    "governance": {"decision": "QUARANTINE", "coherence": 0.5},
                })
        elif command in {"reload", "refresh"}:
            await self.send({
                "type": "browser-command",
                "action": "reload",
            })
            await self.send({
                "type": "governance-event",
                "from": "kael",
                "message": "Refresh requested.",
                "governance": {"decision": "ALLOW", "coherence": 0.9},
            })
        else:
            # PLAN phase: Generate an action plan
            await self.send({
                "type": "governance-event",
                "from": "zara",
                "message": f"Planning: {text}",
                "governance": {"decision": "ALLOW", "coherence": 0.90},
            })

            plan = await create_plan(
                goal=text,
                perception=self.last_perception,
                use_llm=True,
            )

            # Report the plan to Electron
            await self.send({
                "type": "governance-event",
                "from": "zara",
                "message": plan.summary(),
                "governance": {"decision": "ALLOW", "coherence": plan.confidence},
                "payload": {"plan": plan.to_dict()},
            })

            # EXECUTE phase: Send each step to the worker (or Electron)
            if plan.steps and plan.confidence >= 0.5:
                await self._execute_plan(plan)
            elif plan.confidence < 0.5:
                await self.send({
                    "type": "governance-event",
                    "from": "zara",
                    "message": f"Low confidence ({plan.confidence:.0%}). Waiting for user guidance.",
                    "governance": {"decision": "QUARANTINE", "coherence": plan.confidence},
                })

    async def _execute_step_with_retries(
        self,
        *,
        run_id: str,
        step_index: int,
        step_total: int,
        step,
    ) -> tuple[bool, dict[str, Any], int]:
        cmd = step.to_worker_command()
        action = cmd.get("action", step.action)
        attempts_allowed = 1 + self._retry_budget_for_action(step.action, step.metadata or {})
        last_result: dict[str, Any] = {"error": "step_not_executed"}

        for attempt in range(1, attempts_allowed + 1):
            await self._emit_step_event(
                run_id=run_id,
                step_index=step_index,
                step_total=step_total,
                status="running",
                message=f"Step {step_index}/{step_total} attempt {attempt}/{attempts_allowed}: [{step.action}] {step.description}",
                payload={"attempt": attempt, "action": step.action},
                coherence=0.9,
            )

            if self.worker_ws:
                worker_response = await self.send_to_worker(
                    action,
                    wait_for_result=True,
                    timeout_s=45.0,
                    **{k: v for k, v in cmd.items() if k not in {"type", "action", "requestId"}},
                )
                if isinstance(worker_response, dict):
                    if worker_response.get("error"):
                        last_result = {"error": worker_response.get("error"), "action": action}
                    else:
                        last_result = worker_response.get("result", {}) if isinstance(worker_response.get("result"), dict) else {"result": worker_response.get("result")}
                else:
                    last_result = {"error": "invalid_worker_response", "action": action}
            elif step.action == "navigate":
                await self.send({"type": "browser-command", "action": "navigate", "url": step.value})
                last_result = {"ok": True, "action": "navigate", "url": step.value}
            else:
                last_result = {"error": "no_playwright_worker", "action": step.action}

            if not self._result_has_error(last_result):
                return True, last_result, attempt

            if attempt < attempts_allowed:
                await self._emit_step_event(
                    run_id=run_id,
                    step_index=step_index,
                    step_total=step_total,
                    status="retrying",
                    message=f"Retrying step {step_index}/{step_total}: {self._result_error_text(last_result)}",
                    payload={"attempt": attempt, "max_attempts": attempts_allowed},
                    coherence=0.72,
                    decision="QUARANTINE",
                )
                # Quick stabilizer: refresh perception before retrying most actions.
                if self.worker_ws and step.action not in {"snapshot", "evaluate"}:
                    await self.send_to_worker("snapshot", wait_for_result=False)
                await asyncio.sleep(min(1.5, 0.25 * attempt))

        return False, last_result, attempts_allowed

    async def _execute_plan(self, plan: ActionPlan):
        """Execute an ActionPlan with deterministic step waits and retries."""
        run = self._new_run(plan.goal, plan)
        run_id = str(run["run_id"])
        self.agents["kael"]["status"] = "executing"

        await self.send({
            "type": "governance-event",
            "from": "kael",
            "message": f"Executing {len(plan.steps)}-step plan: {plan.goal}",
            "governance": {"decision": "ALLOW", "coherence": plan.confidence},
            "payload": {"run_id": run_id, "plan": plan.to_dict()},
        })

        step_total = len(plan.steps)
        for i, step in enumerate(plan.steps, start=1):
            started = time.time()
            step_record: dict[str, Any] = {
                "index": i,
                "action": step.action,
                "description": step.description,
                "status": "running",
                "attempts": 0,
                "duration_ms": 0.0,
            }
            run["steps"].append(step_record)

            if step.governance_required:
                await self.send({
                    "type": "governance-event",
                    "from": "aria",
                    "message": f"Step {i}/{step_total} requires governance review: [{step.action}] {step.description}",
                    "governance": {"decision": "QUARANTINE", "coherence": 0.72},
                    "payload": {"run_id": run_id, "step_index": i},
                })

            ok, result, attempts = await self._execute_step_with_retries(
                run_id=run_id,
                step_index=i,
                step_total=step_total,
                step=step,
            )

            duration_ms = round((time.time() - started) * 1000.0, 2)
            step_record["attempts"] = attempts
            step_record["duration_ms"] = duration_ms
            step_record["result_preview"] = str(result)[:240]

            if ok:
                step_record["status"] = "ok"
                run["steps_completed"] = int(run.get("steps_completed", 0)) + 1
                self._update_run(run)
                await self._emit_step_event(
                    run_id=run_id,
                    step_index=i,
                    step_total=step_total,
                    status="ok",
                    message=f"Step {i}/{step_total} complete in {duration_ms:.0f}ms",
                    payload={"attempts": attempts, "result": result},
                    coherence=0.95,
                )
            else:
                err = self._result_error_text(result) or "step_failed"
                step_record["status"] = "failed"
                step_record["error"] = err
                self._update_run(run, status="failed", error=f"Step {i} [{step.action}] failed: {err}")
                self._write_run_event({"type": "run_failed", **self._run_public(run)})
                log_plan_result(plan, success=False, error=str(run["error"]))
                await self._emit_step_event(
                    run_id=run_id,
                    step_index=i,
                    step_total=step_total,
                    status="failed",
                    message=f"Plan failed at step {i}/{step_total}: {err}",
                    payload={"attempts": attempts, "result": result},
                    coherence=0.45,
                    decision="DENY",
                )
                self.agents["kael"]["status"] = "idle"
                return

            if step.wait_after_ms > 0 and i < step_total:
                await asyncio.sleep(step.wait_after_ms / 1000.0)

        self._update_run(run, status="succeeded", error="")
        self._write_run_event({"type": "run_succeeded", **self._run_public(run)})
        self.agents["kael"]["status"] = "idle"
        log_plan_result(plan, success=True)
        await self.send({
            "type": "governance-event",
            "from": "kael",
            "message": f"Plan complete: {plan.goal}",
            "governance": {"decision": "ALLOW", "coherence": 0.97},
            "payload": {"run_id": run_id, "run": self._run_public(run)},
        })

    async def handle_navigation(self, url: str):
        """Track navigation events for governance."""
        self.current_url = url
        self.action_log.append({
            "timestamp": time.time(),
            "type": "navigation",
            "url": url,
            "governance": "ALLOW",
        })
        logger.info(f"Navigation: {url}")


runtime = AgentRuntime()

# ---------------------------------------------------------------------------
#  FastAPI WebSocket Server
# ---------------------------------------------------------------------------

if HAS_FASTAPI:
    from fastapi.responses import HTMLResponse, JSONResponse
    from pathlib import Path as _Path

    app = FastAPI(title="Kerrigan — AI Home")

    _DASHBOARD_HTML = _Path(__file__).parent / "dashboard.html"

    @app.get("/", response_class=HTMLResponse)
    @app.get("/home", response_class=HTMLResponse)
    async def dashboard():
        """Serve the Kerrigan home dashboard."""
        if _DASHBOARD_HTML.exists():
            return HTMLResponse(_DASHBOARD_HTML.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>Kerrigan — dashboard.html not found</h1>", status_code=404)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "electron": runtime.ws is not None,
            "worker": runtime.worker_ws is not None,
            "agents": {k: v["status"] for k, v in runtime.agents.items()},
        }

    @app.get("/api/status")
    async def api_status():
        """Full system status for the dashboard."""
        return {
            "ok": True,
            "runtime": {
                "electron": runtime.ws is not None,
                "worker": runtime.worker_ws is not None,
                "url": runtime.current_url,
                "actions": len(runtime.action_log),
            },
            "agents": runtime.agents,
        }

    @app.get("/api/runs/latest")
    async def api_runs_latest(limit: int = 10):
        safe_limit = max(1, min(int(limit), 50))
        runs = [runtime._run_public(run) for run in list(runtime._recent_runs)[:safe_limit]]
        return {"ok": True, "count": len(runs), "runs": runs}

    @app.get("/api/runs/{run_id}")
    async def api_run_detail(run_id: str):
        run = runtime._runs_by_id.get(run_id)
        if not run:
            return JSONResponse({"ok": False, "error": "run_not_found", "run_id": run_id}, status_code=404)
        return {"ok": True, "run": runtime._run_public(run)}

    @app.post("/api/action/{name}")
    async def api_action(name: str):
        """Trigger a named action from the dashboard."""
        known_actions = {
            "post_content": "Publish next item from content queue",
            "run_research": "Start a Polly research sweep",
            "check_patent": "Check USPTO status for #63/961,403",
            "push_training": "Merge and push training data to HuggingFace",
            "list_products": "List digital products on storefronts",
        }

        if name not in known_actions:
            return JSONResponse({"ok": False, "error": f"Unknown action: {name}"}, status_code=400)

        desc = known_actions[name]
        logger.info(f"Dashboard action triggered: {name} — {desc}")

        # Queue the action as a user command to the agent runtime
        asyncio.create_task(runtime.handle_user_command(desc))

        return {"ok": True, "action": name, "message": f"Queued: {desc}"}

    @app.post("/command")
    async def command(payload: dict[str, Any]):
        """Submit a natural-language command to the runtime and execute it in background."""
        text = str(payload.get("text", "")).strip() if isinstance(payload, dict) else ""
        if not text:
            return {
                "status": "error",
                "message": "Missing 'text' in request body",
            }

        source = str(payload.get("source", "api")).strip() or "api"
        logger.info(f"HTTP command from {source}: {text}")
        asyncio.create_task(runtime.handle_user_command(text))
        return {
            "status": "submitted",
            "text": text,
            "source": source,
        }

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws.accept()
        runtime.ws = ws
        logger.info("Electron connected")

        # Send initial agent status
        await ws.send_json({
            "type": "governance-event",
            "from": "system",
            "message": "Agent runtime connected. 4 agents ready.",
            "governance": {"decision": "ALLOW", "coherence": 1.0},
        })

        try:
            while True:
                data = await ws.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "user-command":
                    await runtime.handle_user_command(data.get("text", ""))
                elif msg_type == "navigation":
                    await runtime.handle_navigation(data.get("url", ""))
                elif msg_type == "eval-result":
                    logger.info(f"Eval result: {data.get('result', '')[:200]}")
                elif msg_type == "dom-snapshot":
                    tree = data.get("tree", {})
                    runtime.last_perception = perceive(
                        tree=tree,
                        url=runtime.current_url,
                        title=data.get("title", ""),
                    )
                    p = runtime.last_perception
                    logger.info(f"Perceived: {p.page_type} — {p.title} — {len(p.interactive_elements)} elements, {len(p.forms)} forms")
                else:
                    logger.info(f"Unknown message type: {msg_type}")

        except WebSocketDisconnect:
            logger.info("Electron disconnected")
            runtime.ws = None

    @app.websocket("/ws/worker")
    async def worker_endpoint(ws: WebSocket):
        """WebSocket for the Playwright browser worker."""
        await ws.accept()
        runtime.worker_ws = ws
        logger.info("Playwright worker connected")

        # Notify Electron that worker is ready
        await runtime.send({
            "type": "governance-event",
            "from": "system",
            "message": "Playwright browser worker connected.",
            "governance": {"decision": "ALLOW", "coherence": 1.0},
        })

        try:
            while True:
                data = await ws.receive_json()
                msg_type = data.get("type", "")

                if msg_type == "worker-ready":
                    caps = data.get("capabilities", [])
                    logger.info(f"Worker ready with capabilities: {caps}")
                elif msg_type == "command-result":
                    req_id = data.get("requestId")
                    result = data.get("result", {})
                    logger.info(f"Worker result for req {req_id}: {str(result)[:200]}")
                    runtime.resolve_worker_result(req_id, result if isinstance(result, dict) else {"result": result})
                    runtime.action_log.append({
                        "timestamp": time.time(),
                        "type": "worker_result",
                        "request_id": req_id,
                        "ok": not runtime._result_has_error(result),
                        "result_preview": str(result)[:240],
                    })

                    # If result contains an accessibility tree, run perceiver
                    if "tree" in result:
                        runtime.last_perception = perceive(
                            tree=result["tree"],
                            url=result.get("url", runtime.current_url),
                            title=result.get("title", ""),
                        )
                        p = runtime.last_perception
                        await runtime.send({
                            "type": "governance-event",
                            "from": "polly",
                            "message": f"Perceived: {p.page_type} page — {len(p.interactive_elements)} elements, {len(p.forms)} forms",
                            "governance": {"decision": "ALLOW", "coherence": 0.95},
                            "payload": {"perception": p.to_dict()},
                        })

                    # Forward result to Electron as governance event
                    await runtime.send({
                        "type": "governance-event",
                        "from": "kael",
                        "message": f"Action complete: {result.get('action', result.get('url', 'done'))}",
                        "governance": {"decision": "ALLOW", "coherence": 0.95},
                        "payload": {"requestId": req_id, "result": result},
                    })
                else:
                    logger.info(f"Worker message: {msg_type}")

        except WebSocketDisconnect:
            logger.info("Playwright worker disconnected")
            runtime.worker_ws = None

    # Register Hydra Armor API routes
    register_hydra_routes(app)

    def main():
        logger.info("Starting AetherBrowse Agent Runtime on ws://127.0.0.1:8400")
        uvicorn.run(app, host="127.0.0.1", port=8400, log_level="info")

else:
    def main():
        print("ERROR: FastAPI/uvicorn not installed.")
        print("Install: pip install fastapi uvicorn websockets")
        sys.exit(1)


if __name__ == "__main__":
    main()
