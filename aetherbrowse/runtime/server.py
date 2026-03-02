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
        self._pending_requests = {}
        self._request_counter = 0
        self.last_perception: Optional[PagePerception] = None

    async def send(self, msg: dict):
        """Send message to Electron frontend."""
        if self.ws:
            await self.ws.send_json(msg)

    async def send_to_worker(self, action: str, **kwargs) -> Optional[dict]:
        """Send a browser command to the Playwright worker."""
        if not self.worker_ws:
            logger.warning("No Playwright worker connected")
            return None
        self._request_counter += 1
        req_id = str(self._request_counter)
        msg = {"type": "browser-command", "action": action, "requestId": req_id, **kwargs}
        await self.worker_ws.send_json(msg)
        logger.info(f"Sent to worker: {action} (req {req_id})")
        return {"requestId": req_id, "sent": True}

    async def handle_user_command(self, text: str):
        """Handle natural language command from user."""
        logger.info(f"User command: {text}")

        # Log the governance check
        await self.send({
            "type": "governance-event",
            "from": "zara",
            "message": f"Evaluating command: {text}",
            "governance": {"decision": "ALLOW", "coherence": 0.95},
        })

        # For v0.1: simple URL navigation detection
        if text.startswith("go to ") or text.startswith("navigate to "):
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
        elif text.startswith("snapshot") or text.startswith("perceive"):
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

    async def _execute_plan(self, plan: ActionPlan):
        """Execute an ActionPlan step by step, sending each action to the appropriate target."""
        self.agents["kael"]["status"] = "executing"
        await self.send({
            "type": "governance-event",
            "from": "kael",
            "message": f"Executing {len(plan.steps)}-step plan: {plan.goal}",
            "governance": {"decision": "ALLOW", "coherence": plan.confidence},
        })

        for i, step in enumerate(plan.steps):
            step_label = f"Step {i+1}/{len(plan.steps)}"

            # GOVERN phase: check governance for flagged actions
            if step.governance_required:
                await self.send({
                    "type": "governance-event",
                    "from": "aria",
                    "message": f"{step_label} requires governance review: [{step.action}] {step.description}",
                    "governance": {"decision": "QUARANTINE", "coherence": 0.7},
                })
                # For v0.1 we log but allow — future: wait for user confirm
                logger.info(f"Governance flag on step {i+1}: {step.description}")

            # Report step to Electron
            await self.send({
                "type": "governance-event",
                "from": "kael",
                "message": f"{step_label}: [{step.action}] {step.description}",
                "governance": {"decision": "ALLOW", "coherence": 0.92},
            })

            # Route the action
            if self.worker_ws:
                # Send to Playwright worker
                cmd = step.to_worker_command()
                self._request_counter += 1
                cmd["requestId"] = str(self._request_counter)
                await self.worker_ws.send_json(cmd)
                logger.info(f"Sent step {i+1} to worker: {step.action}")
            elif step.action == "navigate":
                # Fallback: send navigate to Electron's BrowserView
                await self.send({
                    "type": "browser-command",
                    "action": "navigate",
                    "url": step.value,
                })
            else:
                logger.warning(f"No worker available for step {i+1}: {step.action}")
                await self.send({
                    "type": "governance-event",
                    "from": "kael",
                    "message": f"{step_label}: Skipped — no Playwright worker connected",
                    "governance": {"decision": "QUARANTINE", "coherence": 0.5},
                })

            # Wait between steps
            if step.wait_after_ms > 0 and i < len(plan.steps) - 1:
                await asyncio.sleep(step.wait_after_ms / 1000)

        self.agents["kael"]["status"] = "idle"

        # Log plan for training data
        log_plan_result(plan, success=True)

        await self.send({
            "type": "governance-event",
            "from": "kael",
            "message": f"Plan complete: {plan.goal}",
            "governance": {"decision": "ALLOW", "coherence": 0.95},
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
    app = FastAPI(title="AetherBrowse Agent Runtime")

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "electron": runtime.ws is not None,
            "worker": runtime.worker_ws is not None,
            "agents": {k: v["status"] for k, v in runtime.agents.items()},
        }

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
