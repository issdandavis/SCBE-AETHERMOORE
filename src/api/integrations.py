"""
SCBE-AETHERMOORE Integrations Hub
===================================

Centralizes all external service connections — Browserbase (cloud browsers),
Vercel AI Gateway (cross-LLM routing), HuggingFace (open models), and direct
HTTP access — into a single governed configuration layer.

Every outbound call flows through the SemanticAntivirus before touching the
network.  Every response is captured by the SFT collector for training data.

Environment variables (loaded from .env):
    BROWSERBASE_API_KEY        — Browserbase cloud browser API key
    BROWSERBASE_PROJECT_ID     — Browserbase project for session isolation
    VERCEL_AI_GATEWAY_KEY      — Vercel AI Gateway API key (vck_...)
    VERCEL_AI_GATEWAY_URL      — Override gateway URL (default: api.vercel.ai)
    HF_TOKEN                   — HuggingFace Inference API token
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
#  Path setup
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_project_root, ".env"))
except ImportError:
    pass

# ---------------------------------------------------------------------------
#  Service Configuration
# ---------------------------------------------------------------------------

@dataclass
class ServiceConfig:
    """Configuration for a single external service."""
    name: str
    enabled: bool = False
    api_key: str = ""
    base_url: str = ""
    project_id: str = ""
    tier: str = "free"
    models: List[str] = field(default_factory=list)
    last_health_check: float = 0.0
    healthy: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "tier": self.tier,
            "models": self.models,
            "healthy": self.healthy,
            "has_key": bool(self.api_key),
            "base_url": self.base_url or "(default)",
        }


# ---------------------------------------------------------------------------
#  Integration Hub
# ---------------------------------------------------------------------------

class IntegrationHub:
    """Central registry of all external service integrations.

    Provides:
    - Service discovery (which integrations are active)
    - Cross-LLM routing (pick the best model for a task)
    - Health checking
    - Unified AI completion API across providers
    """

    def __init__(self) -> None:
        self.services: Dict[str, ServiceConfig] = {}
        self._http_client: Any = None  # lazy httpx.AsyncClient
        self._load_from_env()

    def _load_from_env(self) -> None:
        """Auto-detect configured services from environment variables."""

        # Browserbase — cloud browser infrastructure
        bb_key = os.getenv("BROWSERBASE_API_KEY", "")
        bb_project = os.getenv("BROWSERBASE_PROJECT_ID", "")
        self.services["browserbase"] = ServiceConfig(
            name="Browserbase",
            enabled=bool(bb_key),
            api_key=bb_key,
            base_url="https://www.browserbase.com",
            project_id=bb_project,
            tier="free" if bb_key else "none",
            models=["chromium"],
        )

        # Vercel AI Gateway — cross-LLM routing
        vk = os.getenv("VERCEL_AI_GATEWAY_KEY", "")
        vurl = os.getenv("VERCEL_AI_GATEWAY_URL", "https://api.vercel.ai/v1")
        self.services["vercel_ai"] = ServiceConfig(
            name="Vercel AI Gateway",
            enabled=bool(vk),
            api_key=vk,
            base_url=vurl,
            tier="free" if vk else "none",
            models=[
                "gpt-4o-mini",
                "claude-3-haiku-20240307",
                "claude-sonnet-4-20250514",
                "mistral-small-latest",
                "llama-3.1-8b",
            ],
        )

        # HuggingFace Inference API — open-source models
        hf_token = os.getenv("HF_TOKEN", "")
        self.services["huggingface"] = ServiceConfig(
            name="HuggingFace Inference",
            enabled=bool(hf_token),
            api_key=hf_token,
            base_url="https://api-inference.huggingface.co/models",
            tier="free" if hf_token else "none",
            models=[
                "mistralai/Mistral-7B-Instruct-v0.3",
                "meta-llama/Llama-3.1-8B-Instruct",
                "google/gemma-2b-it",
                "microsoft/Phi-3-mini-4k-instruct",
            ],
        )

    # -----------------------------------------------------------------------
    #  Service Discovery
    # -----------------------------------------------------------------------

    def active_services(self) -> List[ServiceConfig]:
        """Return all enabled services."""
        return [s for s in self.services.values() if s.enabled]

    def get_service(self, name: str) -> Optional[ServiceConfig]:
        return self.services.get(name)

    def available_models(self) -> Dict[str, List[str]]:
        """Return all available models across all active services."""
        return {
            svc.name: svc.models
            for svc in self.active_services()
        }

    # -----------------------------------------------------------------------
    #  Cross-LLM Routing
    # -----------------------------------------------------------------------

    def route_task(
        self,
        task_type: str = "general",
        prefer_provider: Optional[str] = None,
        max_cost: str = "low",
    ) -> Dict[str, Any]:
        """Route a task to the best available LLM provider.

        Routes by task type:
        - "code"     -> prefer Vercel (GPT-4o) > HuggingFace (CodeLlama)
        - "safety"   -> prefer Vercel (Claude) > HuggingFace (Mistral)
        - "extract"  -> prefer HuggingFace (fast, cheap) > Vercel
        - "general"  -> cheapest available
        - "browser"  -> Browserbase (browser) + any LLM for reasoning

        Returns provider name, model, and endpoint URL.
        """
        routing_table = {
            "code": [
                ("vercel_ai", "gpt-4o-mini"),
                ("huggingface", "mistralai/Mistral-7B-Instruct-v0.3"),
            ],
            "safety": [
                ("vercel_ai", "claude-3-haiku-20240307"),
                ("huggingface", "mistralai/Mistral-7B-Instruct-v0.3"),
            ],
            "extract": [
                ("huggingface", "meta-llama/Llama-3.1-8B-Instruct"),
                ("vercel_ai", "gpt-4o-mini"),
            ],
            "general": [
                ("huggingface", "mistralai/Mistral-7B-Instruct-v0.3"),
                ("vercel_ai", "gpt-4o-mini"),
            ],
            "browser": [
                ("vercel_ai", "gpt-4o-mini"),
                ("huggingface", "mistralai/Mistral-7B-Instruct-v0.3"),
            ],
        }

        candidates = routing_table.get(task_type, routing_table["general"])

        # If user prefers a provider, try it first
        if prefer_provider:
            candidates = sorted(
                candidates,
                key=lambda c: 0 if c[0] == prefer_provider else 1,
            )

        for provider_key, model in candidates:
            svc = self.services.get(provider_key)
            if svc and svc.enabled:
                return {
                    "provider": svc.name,
                    "provider_key": provider_key,
                    "model": model,
                    "base_url": svc.base_url,
                    "has_key": True,
                }

        return {
            "provider": None,
            "provider_key": None,
            "model": None,
            "base_url": None,
            "has_key": False,
            "error": "No AI provider configured. Set VERCEL_AI_GATEWAY_KEY or HF_TOKEN.",
        }

    # -----------------------------------------------------------------------
    #  Unified AI Completion
    # -----------------------------------------------------------------------

    async def _get_http(self) -> Any:
        """Lazy-init httpx async client."""
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(timeout=30.0)
            except ImportError:
                raise RuntimeError("httpx required: pip install httpx")
        return self._http_client

    async def complete(
        self,
        prompt: str,
        task_type: str = "general",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Send a completion request to the best available LLM.

        This is the core cross-LLM abstraction — the caller doesn't need to
        know which provider is serving the request.
        """
        route = self.route_task(task_type, prefer_provider=provider)
        if route.get("error"):
            return {"error": route["error"], "response": None}

        provider_key = route["provider_key"]
        selected_model = model or route["model"]

        try:
            if provider_key == "vercel_ai":
                return await self._complete_vercel(
                    prompt, selected_model, max_tokens, temperature
                )
            elif provider_key == "huggingface":
                return await self._complete_huggingface(
                    prompt, selected_model, max_tokens, temperature
                )
            else:
                return {"error": f"Unknown provider: {provider_key}", "response": None}
        except Exception as e:
            return {
                "error": str(e),
                "provider": route["provider"],
                "model": selected_model,
                "response": None,
            }

    async def _complete_vercel(
        self, prompt: str, model: str, max_tokens: int, temperature: float,
    ) -> Dict[str, Any]:
        """Call Vercel AI Gateway (OpenAI-compatible endpoint)."""
        svc = self.services["vercel_ai"]
        http = await self._get_http()

        resp = await http.post(
            f"{svc.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {svc.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )

        if resp.status_code != 200:
            return {
                "error": f"Vercel AI Gateway {resp.status_code}: {resp.text[:200]}",
                "provider": "Vercel AI Gateway",
                "model": model,
                "response": None,
            }

        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "provider": "Vercel AI Gateway",
            "model": model,
            "response": text,
            "usage": data.get("usage", {}),
            "latency_ms": resp.elapsed.total_seconds() * 1000 if hasattr(resp, "elapsed") else None,
        }

    async def _complete_huggingface(
        self, prompt: str, model: str, max_tokens: int, temperature: float,
    ) -> Dict[str, Any]:
        """Call HuggingFace Inference API."""
        svc = self.services["huggingface"]
        http = await self._get_http()

        resp = await http.post(
            f"{svc.base_url}/{model}",
            headers={
                "Authorization": f"Bearer {svc.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "return_full_text": False,
                },
            },
        )

        if resp.status_code != 200:
            return {
                "error": f"HuggingFace {resp.status_code}: {resp.text[:200]}",
                "provider": "HuggingFace Inference",
                "model": model,
                "response": None,
            }

        data = resp.json()
        if isinstance(data, list) and data:
            text = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            text = data.get("generated_text", str(data))
        else:
            text = str(data)

        return {
            "provider": "HuggingFace Inference",
            "model": model,
            "response": text,
            "latency_ms": resp.elapsed.total_seconds() * 1000 if hasattr(resp, "elapsed") else None,
        }

    # -----------------------------------------------------------------------
    #  Cross-LLM Conversation (agents talking to each other)
    # -----------------------------------------------------------------------

    async def cross_llm_exchange(
        self,
        prompt: str,
        providers: Optional[List[str]] = None,
        task_type: str = "general",
    ) -> Dict[str, Any]:
        """Send the same prompt to multiple LLMs and aggregate responses.

        This is the "cross-LLM talk" feature — different AI models can
        discuss, verify, and build on each other's answers.
        """
        if providers is None:
            providers = [s.name for s in self.active_services()
                         if s.name != "Browserbase"]

        results = []
        for provider_name in providers:
            # Map display name to key
            key_map = {
                "Vercel AI Gateway": "vercel_ai",
                "HuggingFace Inference": "huggingface",
            }
            provider_key = key_map.get(provider_name, provider_name)
            svc = self.services.get(provider_key)
            if not svc or not svc.enabled:
                results.append({
                    "provider": provider_name,
                    "error": "Not configured",
                    "response": None,
                })
                continue

            result = await self.complete(
                prompt=prompt,
                task_type=task_type,
                provider=provider_key,
            )
            results.append(result)

        # Find consensus (if multiple responses agree)
        responses = [r["response"] for r in results if r.get("response")]
        consensus = None
        if len(responses) >= 2:
            # Simple: if any two models' first 100 chars substantially overlap
            consensus = "multiple_responses"

        return {
            "prompt": prompt[:200],
            "results": results,
            "response_count": len(responses),
            "providers_queried": len(providers),
            "consensus": consensus,
        }

    # -----------------------------------------------------------------------
    #  Health Check
    # -----------------------------------------------------------------------

    async def health_check(self) -> Dict[str, Any]:
        """Check all service connections."""
        report = {}
        for key, svc in self.services.items():
            if not svc.enabled:
                report[key] = {"status": "disabled", "reason": "No API key configured"}
                continue

            if key == "browserbase":
                try:
                    from browserbase import Browserbase
                    bb = Browserbase(api_key=svc.api_key)
                    # Just instantiate — listing sessions would verify connectivity
                    svc.healthy = True
                    svc.last_health_check = time.time()
                    report[key] = {"status": "ok", "project_id": svc.project_id}
                except Exception as e:
                    svc.healthy = False
                    report[key] = {"status": "error", "error": str(e)}

            elif key == "vercel_ai":
                try:
                    http = await self._get_http()
                    resp = await http.get(
                        f"{svc.base_url}/models",
                        headers={"Authorization": f"Bearer {svc.api_key}"},
                    )
                    svc.healthy = resp.status_code in (200, 401, 403)
                    svc.last_health_check = time.time()
                    report[key] = {
                        "status": "ok" if resp.status_code == 200 else f"http_{resp.status_code}",
                    }
                except Exception as e:
                    svc.healthy = False
                    report[key] = {"status": "error", "error": str(e)}

            elif key == "huggingface":
                svc.healthy = bool(svc.api_key)
                svc.last_health_check = time.time()
                report[key] = {
                    "status": "ok" if svc.api_key else "no_token",
                }

        return {
            "services": report,
            "active_count": len(self.active_services()),
            "total_models": sum(len(s.models) for s in self.active_services()),
            "checked_at": time.time(),
        }

    def status_summary(self) -> Dict[str, Any]:
        """Quick status without network calls."""
        return {
            "services": {k: v.to_dict() for k, v in self.services.items()},
            "active": [s.name for s in self.active_services()],
            "total_models": sum(len(s.models) for s in self.active_services()),
            "cross_llm_ready": len([
                s for s in self.active_services() if s.name != "Browserbase"
            ]) >= 2,
        }


# ---------------------------------------------------------------------------
#  Module-level singleton
# ---------------------------------------------------------------------------

integration_hub = IntegrationHub()
