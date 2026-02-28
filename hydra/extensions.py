"""
HYDRA Extensions — Compute & Orchestration Limbs
=================================================

Extends HYDRA with external compute backends so headless browser swarms
can scale across the internet.  Each extension is a HydraLimb subclass
that the Spine registers and delegates work to via the Switchboard.

Backends:
    ColabLimb       — Google Colab notebooks (free T4 / A100 via Pro)
    VertexLimb      — Vertex AI Custom Training + Prediction
    ZapierLimb      — Zapier webhook triggers (5000+ app integrations)
    N8nLimb         — n8n workflow execution via SCBE n8n Bridge
    TelegramLimb    — Telegram Bot API for human-in-the-loop + alerts
    PlaywrightLimb  — Remote Playwright instances (Cloud Run / Colab)

Usage:
    from hydra.extensions import register_all_extensions
    from hydra.spine import HydraSpine

    spine = HydraSpine()
    extensions = await register_all_extensions(spine)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .limbs import HydraLimb


# ---------------------------------------------------------------------------
#  Colab Limb — Google Colab notebooks as compute workers
# ---------------------------------------------------------------------------

class ColabLimb(HydraLimb):
    """Execute tasks on Google Colab notebooks.

    Colab notebooks expose a REST API when running the SCBE remote worker.
    The worker polls the Switchboard for tasks and reports results back.

    For free-tier T4 GPUs this is ideal for:
    - QLoRA fine-tuning (vertex_hydra_trainer.py)
    - Batch embedding generation
    - Browser swarm workers (headless Chrome in Colab)
    """

    limb_type = "colab"

    def __init__(
        self,
        notebook_url: str = "",
        runtime_type: str = "T4",  # T4 | A100 | TPU_V2
        scbe_url: str = "http://127.0.0.1:8080",
    ):
        super().__init__(scbe_url)
        self.notebook_url = notebook_url
        self.runtime_type = runtime_type
        self.worker_status: Dict[str, Any] = {}
        self._colab_api_url = os.environ.get("COLAB_API_URL", "")

    async def activate(self) -> bool:
        await super().activate()
        # If a Colab API URL is set, ping it
        if self._colab_api_url:
            try:
                import urllib.request
                req = urllib.request.Request(
                    f"{self._colab_api_url}/health",
                    headers={"User-Agent": "HYDRA-ColabLimb/1.0"},
                )
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(
                    None, lambda: urllib.request.urlopen(req, timeout=10)
                )
                self.worker_status = json.loads(resp.read().decode())
                print(f"[COLAB] Connected: {self.runtime_type} — {self.worker_status.get('gpu', 'cpu')}")
            except Exception as e:
                print(f"[COLAB] Ping failed (offline?): {e}")
        return True

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.action_count += 1

        gov = await self._check_governance(action, target, 0.4)
        if gov.get("decision") == "DENY":
            return {"success": False, "decision": "DENY", "reason": gov.get("explanation")}

        if action == "train":
            return await self._submit_training(target, params)
        elif action == "embed":
            return await self._batch_embed(target, params)
        elif action == "browser_worker":
            return await self._launch_browser_worker(target, params)
        elif action == "status":
            return {"success": True, "status": self.worker_status, "runtime": self.runtime_type}
        else:
            return {"success": False, "error": f"Unknown colab action: {action}"}

    async def _submit_training(self, head: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit QLoRA training job to Colab worker."""
        payload = {
            "task": "train",
            "head": head,
            "epochs": params.get("epochs", 3),
            "batch_size": params.get("batch_size", 4),
            "lora_r": params.get("lora_r", 16),
            "data_categories": params.get("categories", []),
        }
        return await self._post_to_worker("/train", payload)

    async def _batch_embed(self, text: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings on Colab GPU."""
        payload = {"task": "embed", "texts": params.get("texts", [text]), "model": params.get("model", "phdm-21d")}
        return await self._post_to_worker("/embed", payload)

    async def _launch_browser_worker(self, role: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start a headless browser worker on Colab that polls the Switchboard."""
        payload = {
            "task": "browser_worker",
            "role": role,
            "switchboard_url": params.get("switchboard_url", ""),
            "max_tasks": params.get("max_tasks", 50),
        }
        return await self._post_to_worker("/browser-worker", payload)

    async def _post_to_worker(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._colab_api_url:
            return {"success": False, "error": "COLAB_API_URL not set", "mock": True, "payload": payload}
        try:
            import urllib.request
            url = f"{self._colab_api_url}{endpoint}"
            body = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=body, headers={
                "Content-Type": "application/json",
                "User-Agent": "HYDRA-ColabLimb/1.0",
            })
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=60))
            data = json.loads(resp.read().decode())
            return {"success": True, "data": data, "limb_id": self.limb_id}
        except Exception as e:
            return {"success": False, "error": str(e), "limb_id": self.limb_id}


# ---------------------------------------------------------------------------
#  Vertex AI Limb — Google Cloud Vertex AI
# ---------------------------------------------------------------------------

class VertexLimb(HydraLimb):
    """Submit training jobs, run predictions, and manage models on Vertex AI.

    Wraps the google-cloud-aiplatform SDK. For headless swarms this provides
    persistent GPU/TPU compute that doesn't time out like Colab.
    """

    limb_type = "vertex"

    def __init__(
        self,
        project_id: str = "",
        region: str = "us-central1",
        scbe_url: str = "http://127.0.0.1:8080",
    ):
        super().__init__(scbe_url)
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self.region = region
        self._aiplatform = None

    async def activate(self) -> bool:
        await super().activate()
        try:
            from google.cloud import aiplatform
            aiplatform.init(project=self.project_id, location=self.region)
            self._aiplatform = aiplatform
            print(f"[VERTEX] Initialized: {self.project_id} / {self.region}")
        except ImportError:
            print("[VERTEX] google-cloud-aiplatform not installed — mock mode")
        except Exception as e:
            print(f"[VERTEX] Init warning: {e}")
        return True

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.action_count += 1

        gov = await self._check_governance(action, target, 0.6)
        if gov.get("decision") == "DENY":
            return {"success": False, "decision": "DENY", "reason": gov.get("explanation")}

        if action == "train":
            return await self._submit_custom_job(target, params)
        elif action == "predict":
            return await self._predict(target, params)
        elif action == "list_models":
            return await self._list_models()
        elif action == "status":
            return await self._job_status(target)
        else:
            return {"success": False, "error": f"Unknown vertex action: {action}"}

    async def _submit_custom_job(self, display_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._aiplatform:
            return {"success": False, "error": "Vertex AI SDK not available", "mock": True}
        try:
            loop = asyncio.get_event_loop()
            job = await loop.run_in_executor(None, lambda: self._aiplatform.CustomJob(
                display_name=display_name,
                worker_pool_specs=[{
                    "machine_spec": {
                        "machine_type": params.get("machine_type", "n1-standard-4"),
                        "accelerator_type": params.get("accelerator", "NVIDIA_TESLA_T4"),
                        "accelerator_count": params.get("gpu_count", 1),
                    },
                    "replica_count": 1,
                    "container_spec": {
                        "image_uri": params.get("image_uri", ""),
                        "args": params.get("args", []),
                    },
                }],
            ))
            await loop.run_in_executor(None, lambda: job.submit())
            return {
                "success": True,
                "job_name": job.resource_name,
                "state": str(job.state),
                "limb_id": self.limb_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _predict(self, endpoint_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._aiplatform:
            return {"success": False, "error": "Vertex AI SDK not available", "mock": True}
        try:
            loop = asyncio.get_event_loop()
            endpoint = self._aiplatform.Endpoint(endpoint_id)
            instances = params.get("instances", [])
            result = await loop.run_in_executor(None, lambda: endpoint.predict(instances=instances))
            return {"success": True, "predictions": [str(p) for p in result.predictions[:10]], "limb_id": self.limb_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _list_models(self) -> Dict[str, Any]:
        if not self._aiplatform:
            return {"success": False, "error": "Vertex AI SDK not available", "mock": True}
        try:
            loop = asyncio.get_event_loop()
            models = await loop.run_in_executor(None, self._aiplatform.Model.list)
            return {
                "success": True,
                "models": [{"name": m.display_name, "id": m.resource_name} for m in models[:20]],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _job_status(self, job_name: str) -> Dict[str, Any]:
        if not self._aiplatform:
            return {"success": False, "error": "Vertex AI SDK not available", "mock": True}
        try:
            loop = asyncio.get_event_loop()
            job = await loop.run_in_executor(
                None, lambda: self._aiplatform.CustomJob.get(job_name)
            )
            return {"success": True, "state": str(job.state), "job_name": job_name}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
#  Zapier Limb — 5000+ app integrations via webhooks
# ---------------------------------------------------------------------------

class ZapierLimb(HydraLimb):
    """Trigger Zapier workflows via webhooks.

    Each Zap is identified by a webhook URL. HYDRA can fire webhooks to:
    - Post to social media (Twitter, LinkedIn, Bluesky)
    - Send Slack/Discord/Email notifications
    - Create Notion/Asana/Linear tasks
    - Trigger data pipelines
    - Sync with Shopify, Stripe, HubSpot
    """

    limb_type = "zapier"

    def __init__(
        self,
        webhooks: Optional[Dict[str, str]] = None,
        scbe_url: str = "http://127.0.0.1:8080",
    ):
        super().__init__(scbe_url)
        # Named webhooks: {"publish_tweet": "https://hooks.zapier.com/...", ...}
        self.webhooks: Dict[str, str] = webhooks or {}
        self._load_env_webhooks()

    def _load_env_webhooks(self) -> None:
        """Load webhook URLs from ZAPIER_WEBHOOK_* env vars."""
        for key, val in os.environ.items():
            if key.startswith("ZAPIER_WEBHOOK_"):
                name = key[len("ZAPIER_WEBHOOK_"):].lower()
                self.webhooks[name] = val

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.action_count += 1

        # Sensitivity based on action type
        sensitivity = 0.5
        if action in ("publish", "send", "create", "delete"):
            sensitivity = 0.7
        if "payment" in target.lower() or "transfer" in target.lower():
            sensitivity = 0.95

        gov = await self._check_governance(action, target, sensitivity)
        if gov.get("decision") == "DENY":
            return {"success": False, "decision": "DENY", "reason": gov.get("explanation")}

        if action == "trigger":
            return await self._trigger_webhook(target, params)
        elif action == "list":
            return {"success": True, "webhooks": list(self.webhooks.keys()), "count": len(self.webhooks)}
        elif action == "register":
            self.webhooks[target] = params.get("url", "")
            return {"success": True, "registered": target}
        else:
            # Treat action as webhook name
            return await self._trigger_webhook(action, {"target": target, **params})

    async def _trigger_webhook(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = self.webhooks.get(name) or name  # Allow direct URL or named webhook
        if not url.startswith("http"):
            return {"success": False, "error": f"Unknown webhook: {name}", "available": list(self.webhooks.keys())}
        try:
            import urllib.request
            body = json.dumps({"source": "hydra", "limb_id": self.limb_id, **payload}).encode()
            req = urllib.request.Request(url, data=body, headers={
                "Content-Type": "application/json",
                "User-Agent": "HYDRA-ZapierLimb/1.0",
            })
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=15))
            result_text = resp.read().decode()
            return {"success": True, "webhook": name, "response": result_text[:2000], "limb_id": self.limb_id}
        except Exception as e:
            return {"success": False, "error": str(e), "webhook": name}


# ---------------------------------------------------------------------------
#  n8n Limb — Self-hosted workflow automation
# ---------------------------------------------------------------------------

class N8nLimb(HydraLimb):
    """Execute n8n workflows via the SCBE n8n Bridge.

    The bridge (workflows/n8n/scbe_n8n_bridge.py) exposes endpoints for:
    - Semantic antivirus scanning
    - Sacred Tongue encoding
    - Content Buffer posting
    - Web agent task submission
    - Vertex AI training/prediction
    - HuggingFace model pull/push

    n8n workflows trigger these endpoints and chain them into pipelines.
    """

    limb_type = "n8n"

    def __init__(
        self,
        bridge_url: str = "http://127.0.0.1:8001",
        n8n_url: str = "",
        scbe_url: str = "http://127.0.0.1:8080",
    ):
        super().__init__(scbe_url)
        self.bridge_url = bridge_url or os.environ.get("N8N_BRIDGE_URL", "http://127.0.0.1:8001")
        self.n8n_url = n8n_url or os.environ.get("N8N_URL", "")

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.action_count += 1

        gov = await self._check_governance(action, target, 0.5)
        if gov.get("decision") == "DENY":
            return {"success": False, "decision": "DENY", "reason": gov.get("explanation")}

        # Route to appropriate bridge endpoint
        endpoint_map = {
            "scan": "/v1/governance/scan",
            "encode": "/v1/tongue/encode",
            "post": "/v1/buffer/post",
            "task": "/v1/agent/task",
            "task_status": f"/v1/agent/task/{target}/status",
            "train": "/v1/vertex/train",
            "predict": "/v1/vertex/predict",
            "pull_model": "/v1/hf/pull-model",
            "push_model": "/v1/vertex/push-to-hf",
            "models": "/v1/vertex/models",
            "training_status": "/v1/training/status",
            "ingest": "/v1/training/ingest",
        }

        endpoint = endpoint_map.get(action)
        if not endpoint:
            return {"success": False, "error": f"Unknown n8n action: {action}", "available": list(endpoint_map.keys())}

        method = "GET" if action in ("task_status", "models", "training_status") else "POST"
        return await self._bridge_call(method, endpoint, params)

    async def _bridge_call(self, method: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import urllib.request
            url = f"{self.bridge_url}{endpoint}"

            if method == "GET":
                req = urllib.request.Request(url, headers={"User-Agent": "HYDRA-N8nLimb/1.0"})
            else:
                body = json.dumps(payload).encode()
                req = urllib.request.Request(url, data=body, headers={
                    "Content-Type": "application/json",
                    "User-Agent": "HYDRA-N8nLimb/1.0",
                }, method="POST")

            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=30))
            data = json.loads(resp.read().decode())
            return {"success": True, "data": data, "limb_id": self.limb_id}
        except Exception as e:
            return {"success": False, "error": str(e), "limb_id": self.limb_id}


# ---------------------------------------------------------------------------
#  Telegram Limb — Human-in-the-loop + Alerts
# ---------------------------------------------------------------------------

class TelegramLimb(HydraLimb):
    """Send messages and receive commands via Telegram Bot API.

    For HYDRA this enables:
    - Human-in-the-loop escalation (QUARANTINE decisions need human approval)
    - Real-time alerts (swarm anomalies, spectral drift, budget overruns)
    - Remote command injection (operator sends /fleet from phone)
    - Status broadcasting to team channels
    """

    limb_type = "telegram"

    def __init__(
        self,
        bot_token: str = "",
        chat_ids: Optional[List[str]] = None,
        scbe_url: str = "http://127.0.0.1:8080",
    ):
        super().__init__(scbe_url)
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_ids: List[str] = chat_ids or []
        self._base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.action_count += 1

        gov = await self._check_governance(action, target, 0.3)
        if gov.get("decision") == "DENY":
            return {"success": False, "decision": "DENY", "reason": gov.get("explanation")}

        if action == "send":
            return await self._send_message(target, params.get("text", ""))
        elif action == "broadcast":
            return await self._broadcast(params.get("text", target))
        elif action == "alert":
            return await self._send_alert(target, params)
        elif action == "escalate":
            return await self._escalate(target, params)
        else:
            return {"success": False, "error": f"Unknown telegram action: {action}"}

    async def _send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        if not self.bot_token:
            return {"success": False, "error": "TELEGRAM_BOT_TOKEN not set"}
        try:
            import urllib.request
            url = f"{self._base_url}/sendMessage"
            body = json.dumps({"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML"}).encode()
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=10))
            data = json.loads(resp.read().decode())
            return {"success": data.get("ok", False), "message_id": data.get("result", {}).get("message_id")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _broadcast(self, text: str) -> Dict[str, Any]:
        results = []
        for chat_id in self.chat_ids:
            r = await self._send_message(chat_id, text)
            results.append({"chat_id": chat_id, **r})
        return {"success": all(r.get("success") for r in results), "results": results}

    async def _send_alert(self, severity: str, params: Dict[str, Any]) -> Dict[str, Any]:
        icons = {"critical": "🔴", "warning": "🟡", "info": "🔵", "success": "🟢"}
        icon = icons.get(severity, "⚪")
        text = (
            f"{icon} <b>HYDRA Alert — {severity.upper()}</b>\n\n"
            f"{params.get('text', params.get('message', 'No details'))}\n\n"
            f"Source: {params.get('source', 'system')}\n"
            f"Time: {time.strftime('%H:%M:%S UTC', time.gmtime())}"
        )
        return await self._broadcast(text)

    async def _escalate(self, decision_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send governance escalation requiring human approval."""
        text = (
            f"⚠️ <b>GOVERNANCE ESCALATION</b>\n\n"
            f"Decision: {decision_id}\n"
            f"Action: {params.get('action', '?')}\n"
            f"Agent: {params.get('agent_id', '?')}\n"
            f"Risk: {params.get('risk_score', 0):.3f}\n\n"
            f"Reply /approve {decision_id} or /deny {decision_id}"
        )
        return await self._broadcast(text)


# ---------------------------------------------------------------------------
#  Remote Playwright Limb — Cloud browser instances
# ---------------------------------------------------------------------------

class PlaywrightCloudLimb(HydraLimb):
    """Remote Playwright browser instances running on Cloud Run / Colab / VPS.

    Each instance runs headless Chromium and accepts tasks via HTTP.
    Multiple instances = browser swarm across the internet.

    The remote worker (hydra/remote_worker.py) polls the Switchboard,
    but this limb can also push tasks directly via HTTP.
    """

    limb_type = "playwright_cloud"

    def __init__(
        self,
        worker_urls: Optional[List[str]] = None,
        scbe_url: str = "http://127.0.0.1:8080",
    ):
        super().__init__(scbe_url)
        self.worker_urls: List[str] = worker_urls or []
        self._worker_health: Dict[str, Dict[str, Any]] = {}
        self._load_env_workers()

    def _load_env_workers(self) -> None:
        """Load worker URLs from PW_WORKER_* env vars."""
        for key, val in os.environ.items():
            if key.startswith("PW_WORKER_"):
                self.worker_urls.append(val)

    async def activate(self) -> bool:
        await super().activate()
        # Health-check all workers
        for url in self.worker_urls:
            health = await self._ping_worker(url)
            self._worker_health[url] = health
        alive = sum(1 for h in self._worker_health.values() if h.get("ok"))
        print(f"[PLAYWRIGHT-CLOUD] {alive}/{len(self.worker_urls)} workers alive")
        return True

    async def _ping_worker(self, url: str) -> Dict[str, Any]:
        try:
            import urllib.request
            req = urllib.request.Request(f"{url}/health", headers={"User-Agent": "HYDRA-PW/1.0"})
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=5))
            return {"ok": True, **json.loads(resp.read().decode())}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _pick_worker(self) -> Optional[str]:
        """Round-robin among healthy workers."""
        alive = [u for u, h in self._worker_health.items() if h.get("ok")]
        if not alive:
            return None
        # Simple round-robin by action count
        return alive[self.action_count % len(alive)]

    async def execute(self, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.action_count += 1

        sensitivity = {"navigate": 0.3, "click": 0.4, "type": 0.5, "extract": 0.3, "screenshot": 0.2}.get(action, 0.5)
        gov = await self._check_governance(action, target, sensitivity)
        if gov.get("decision") == "DENY":
            return {"success": False, "decision": "DENY", "reason": gov.get("explanation")}

        if action == "add_worker":
            self.worker_urls.append(target)
            health = await self._ping_worker(target)
            self._worker_health[target] = health
            return {"success": True, "worker": target, "health": health}

        if action == "workers":
            return {"success": True, "workers": self._worker_health, "total": len(self.worker_urls)}

        # Route to a worker
        worker = params.get("worker_url") or self._pick_worker()
        if not worker:
            return {"success": False, "error": "No healthy workers available"}

        return await self._dispatch(worker, action, target, params)

    async def _dispatch(self, worker_url: str, action: str, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import urllib.request
            url = f"{worker_url}/execute"
            body = json.dumps({"action": action, "target": target, "params": params}).encode()
            req = urllib.request.Request(url, data=body, headers={
                "Content-Type": "application/json",
                "User-Agent": "HYDRA-PW/1.0",
            })
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=30))
            data = json.loads(resp.read().decode())
            return {"success": True, "worker": worker_url, "data": data, "limb_id": self.limb_id}
        except Exception as e:
            # Mark worker as unhealthy
            self._worker_health[worker_url] = {"ok": False, "error": str(e)}
            return {"success": False, "error": str(e), "worker": worker_url}

    async def execute_swarm(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Distribute tasks across all healthy workers in parallel."""
        alive = [u for u, h in self._worker_health.items() if h.get("ok")]
        if not alive:
            return [{"success": False, "error": "No workers"} for _ in tasks]

        coros = []
        for i, task in enumerate(tasks):
            worker = alive[i % len(alive)]
            coros.append(self._dispatch(worker, task["action"], task["target"], task.get("params", {})))

        return list(await asyncio.gather(*coros, return_exceptions=True))


# ---------------------------------------------------------------------------
#  Registration helper
# ---------------------------------------------------------------------------

@dataclass
class ExtensionRegistry:
    """Tracks all registered extensions for the Spine."""
    colab: Optional[ColabLimb] = None
    vertex: Optional[VertexLimb] = None
    zapier: Optional[ZapierLimb] = None
    n8n: Optional[N8nLimb] = None
    telegram: Optional[TelegramLimb] = None
    playwright_cloud: Optional[PlaywrightCloudLimb] = None

    def active(self) -> Dict[str, HydraLimb]:
        return {k: v for k, v in {
            "colab": self.colab, "vertex": self.vertex, "zapier": self.zapier,
            "n8n": self.n8n, "telegram": self.telegram, "playwright_cloud": self.playwright_cloud,
        }.items() if v and v.active}

    def summary(self) -> Dict[str, Any]:
        return {
            name: {"active": limb.active, "actions": limb.action_count, "id": limb.limb_id}
            for name, limb in self.active().items()
        }


async def register_all_extensions(
    spine: Any,
    *,
    colab: bool = True,
    vertex: bool = True,
    zapier: bool = True,
    n8n: bool = True,
    telegram: bool = True,
    playwright_cloud: bool = True,
) -> ExtensionRegistry:
    """Register all available extensions as Limbs on the Spine.

    Only activates extensions whose required env vars / SDKs are present.

    Usage:
        from hydra.spine import HydraSpine
        from hydra.extensions import register_all_extensions

        spine = HydraSpine()
        ext = await register_all_extensions(spine)
        print(ext.summary())
    """
    reg = ExtensionRegistry()

    if colab:
        reg.colab = ColabLimb()
        await reg.colab.activate()
        if hasattr(spine, "register_limb"):
            spine.register_limb(reg.colab)

    if vertex:
        reg.vertex = VertexLimb()
        await reg.vertex.activate()
        if hasattr(spine, "register_limb"):
            spine.register_limb(reg.vertex)

    if zapier:
        reg.zapier = ZapierLimb()
        await reg.zapier.activate()
        if hasattr(spine, "register_limb"):
            spine.register_limb(reg.zapier)

    if n8n:
        reg.n8n = N8nLimb()
        await reg.n8n.activate()
        if hasattr(spine, "register_limb"):
            spine.register_limb(reg.n8n)

    if telegram and os.environ.get("TELEGRAM_BOT_TOKEN"):
        reg.telegram = TelegramLimb()
        await reg.telegram.activate()
        if hasattr(spine, "register_limb"):
            spine.register_limb(reg.telegram)

    if playwright_cloud:
        reg.playwright_cloud = PlaywrightCloudLimb()
        await reg.playwright_cloud.activate()
        if hasattr(spine, "register_limb"):
            spine.register_limb(reg.playwright_cloud)

    active = reg.active()
    print(f"[EXTENSIONS] {len(active)} limbs registered: {', '.join(active.keys())}")
    return reg
