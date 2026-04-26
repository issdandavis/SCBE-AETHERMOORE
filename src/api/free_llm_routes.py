"""Free/open LLM routing for HYDRA mission-dock workers.

This router is intentionally provider-thin: it exposes a stable registry and
dispatch contract while keeping provider-specific details behind adapters.
"""

from __future__ import annotations

import json
import os
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from src.api.auth_config import VALID_API_KEYS

free_llm_router = APIRouter(prefix="/hydra/free-llm", tags=["HYDRA Free LLM"])
REPO_ROOT = Path(__file__).resolve().parents[2]

ProviderKind = Literal["offline", "ollama", "huggingface", "custom"]


class FreeLLMDispatchRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000)
    provider: Optional[str] = Field(
        default=None, max_length=64, description="Provider id; auto selects if omitted"
    )
    model: Optional[str] = Field(default=None, max_length=256)
    system: Optional[str] = Field(default=None, max_length=8000)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    require_free: bool = Field(
        default=True, description="Only route to local/open/free-style providers"
    )
    dry_run: bool = Field(
        default=False,
        description="Return route decision without sending prompt to a provider",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OllamaLaunchPlanRequest(BaseModel):
    integration: str = Field(..., min_length=1, max_length=64)
    model: Optional[str] = Field(default=None, max_length=256)
    extra_args: list[str] = Field(default_factory=list, max_length=32)
    configure_only: bool = Field(
        default=False,
        description="Generate a configuration command instead of a launch command",
    )
    assume_yes: bool = Field(
        default=True,
        description="Include --yes for non-interactive launch confirmation",
    )


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return VALID_API_KEYS[x_api_key]


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _http_json(
    url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float
) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        suffix = f":{body}" if body else ""
        raise RuntimeError(f"provider_http_{exc.code}{suffix}") from exc
    except URLError as exc:
        raise RuntimeError("provider_unreachable") from exc
    except TimeoutError as exc:
        raise RuntimeError("provider_timeout") from exc


def _load_custom_providers() -> Dict[str, Dict[str, Any]]:
    raw = os.getenv("SCBE_FREE_LLM_PROVIDERS", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    providers: Dict[str, Dict[str, Any]] = {}
    for provider_id, config in data.items():
        if isinstance(provider_id, str) and isinstance(config, dict):
            providers[provider_id] = config
    return providers


def _bus_path() -> Path:
    return REPO_ROOT / ".scbe" / "packets" / "free_llm_dispatch.jsonl"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_bus_event(
    *,
    request: FreeLLMDispatchRequest,
    user: str,
    route: Dict[str, Any],
    result: Dict[str, Any] | None = None,
    error: str | None = None,
    origin: Literal["inside", "outside"] = "outside",
) -> Dict[str, Any]:
    event_seed = json.dumps(
        {
            "provider": route.get("provider"),
            "model": route.get("model"),
            "prompt_sha256": _sha256_text(request.prompt),
            "ts_ns": time.time_ns(),
        },
        sort_keys=True,
    )
    return {
        "version": "hydra-free-llm-bus-event-v1",
        "event_id": _sha256_text(event_seed)[:24],
        "origin": origin,
        "user": user,
        "timestamp": int(time.time()),
        "route": route,
        "prompt": {
            "sha256": _sha256_text(request.prompt),
            "chars": len(request.prompt),
            "system_sha256": (
                _sha256_text(request.system or "") if request.system else None
            ),
        },
        "result": {
            "provider": result.get("provider") if result else None,
            "model": result.get("model") if result else route.get("model"),
            "finish_reason": result.get("finish_reason") if result else None,
            "text_sha256": (
                _sha256_text(result.get("text", ""))
                if result and result.get("text")
                else None
            ),
            "text_chars": len(result.get("text", "")) if result else 0,
        },
        "error": error,
    }


def _append_bus_event(event: Dict[str, Any]) -> None:
    if _env_flag("SCBE_FREE_LLM_DISABLE_BUS_LOG", False):
        return
    path = _bus_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


OLLAMA_LAUNCH_INTEGRATIONS: Dict[str, Dict[str, Any]] = {
    "claude": {"name": "Claude Code", "aliases": []},
    "cline": {"name": "Cline", "aliases": []},
    "codex": {"name": "Codex", "aliases": []},
    "copilot": {"name": "Copilot CLI", "aliases": ["copilot-cli"]},
    "droid": {"name": "Droid", "aliases": []},
    "hermes": {"name": "Hermes Agent", "aliases": []},
    "kimi": {"name": "Kimi Code CLI", "aliases": []},
    "opencode": {"name": "OpenCode", "aliases": []},
    "openclaw": {"name": "OpenClaw", "aliases": ["clawdbot", "moltbot"]},
    "pi": {"name": "Pi", "aliases": []},
    "vscode": {"name": "VS Code", "aliases": ["code"]},
}


def _ollama_launch_registry() -> Dict[str, Any]:
    alias_map = {
        alias: integration
        for integration, meta in OLLAMA_LAUNCH_INTEGRATIONS.items()
        for alias in meta.get("aliases", [])
    }
    return {
        "version": "hydra-ollama-launch-registry-v1",
        "command": "ollama launch",
        "privacy": "local_agent_process",
        "execution_policy": "plan_only",
        "integrations": OLLAMA_LAUNCH_INTEGRATIONS,
        "aliases": alias_map,
    }


def build_ollama_launch_plan(
    request: OllamaLaunchPlanRequest, *, user: str = "internal"
) -> Dict[str, Any]:
    registry = _ollama_launch_registry()
    requested = request.integration.strip().lower()
    integration = registry["aliases"].get(requested, requested)
    if integration not in registry["integrations"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported Ollama launch integration: {requested}",
        )
    command = ["ollama", "launch", integration]
    if request.assume_yes:
        command.append("--yes")
    if request.configure_only:
        command.append("--config")
    if request.model:
        command.extend(["--model", request.model])
    if request.extra_args:
        command.append("--")
        command.extend(request.extra_args)
    return {
        "version": "hydra-ollama-launch-plan-v1",
        "user": user,
        "integration": integration,
        "display_name": registry["integrations"][integration]["name"],
        "command": command,
        "command_text": " ".join(command),
        "command_sha256": _sha256_text("\0".join(command)),
        "execution_policy": "plan_only",
    }


def free_llm_registry() -> Dict[str, Any]:
    hf_token_present = bool(
        os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACE_TOKEN")
        or os.getenv("HUGGING_FACE_HUB_TOKEN")
    )
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    registry: Dict[str, Any] = {
        "version": "hydra-free-llm-registry-v1",
        "default_order": ["ollama", "huggingface", "offline"],
        "agent_launchers": _ollama_launch_registry(),
        "providers": {
            "offline": {
                "provider": "offline",
                "kind": "offline",
                "cost": "free",
                "privacy": "local",
                "available": True,
                "default_model": "scbe-offline-control-plane",
                "dispatch": "deterministic_local",
            },
            "ollama": {
                "provider": "ollama",
                "kind": "ollama",
                "cost": "free_local_runtime",
                "privacy": "local",
                "available": True,
                "base_url": ollama_base,
                "default_model": os.getenv("OLLAMA_MODEL", "qwen2.5-coder:0.5b"),
                "dispatch": "ollama_api_chat",
            },
            "huggingface": {
                "provider": "huggingface",
                "kind": "huggingface",
                "cost": "account_or_free_tier",
                "privacy": "remote",
                "available": hf_token_present,
                "token_present": hf_token_present,
                "default_model": os.getenv(
                    "HF_ROUTER_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct"
                ),
                "dispatch": "hf_router_chat_completions",
            },
        },
    }
    for provider_id, config in _load_custom_providers().items():
        registry["providers"][provider_id] = {
            "provider": provider_id,
            "kind": "custom",
            "cost": config.get("cost", "user_configured"),
            "privacy": config.get(
                "privacy",
                "local" if "localhost" in str(config.get("endpoint", "")) else "remote",
            ),
            "available": bool(config.get("enabled", True)),
            "endpoint": config.get("endpoint"),
            "default_model": config.get("model", "custom-open-worker"),
            "dispatch": "openai_compatible_chat",
        }
    return registry


def _select_provider(
    request: FreeLLMDispatchRequest, registry: Dict[str, Any]
) -> Dict[str, Any]:
    providers = registry["providers"]
    if request.provider:
        provider = providers.get(request.provider)
        if not provider:
            raise HTTPException(
                status_code=404, detail=f"Unknown provider '{request.provider}'"
            )
        return provider
    for provider_id in registry["default_order"]:
        provider = providers.get(provider_id)
        if provider and provider.get("available"):
            return provider
    return providers["offline"]


def _offline_dispatch(
    request: FreeLLMDispatchRequest, provider: Dict[str, Any]
) -> Dict[str, Any]:
    prompt = request.prompt.strip()
    text = (
        "SCBE offline worker accepted the task. "
        "No remote model was called. "
        f"Prompt chars={len(prompt)}. "
        "Use Ollama, Hugging Face, or a custom provider id for live generation."
    )
    return {
        "text": text,
        "provider": provider["provider"],
        "model": request.model or provider["default_model"],
        "finish_reason": "offline_deterministic",
        "usage": {"input_chars": len(prompt), "output_chars": len(text)},
    }


def _ollama_dispatch(
    request: FreeLLMDispatchRequest, provider: Dict[str, Any]
) -> Dict[str, Any]:
    model = request.model or provider["default_model"]
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": request.system
                or "You are a concise coding worker in the HYDRA mission dock.",
            },
            {"role": "user", "content": request.prompt},
        ],
        "stream": False,
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
        },
    }
    data = _http_json(f"{provider['base_url']}/api/chat", payload, {}, timeout=45)
    message = data.get("message") or {}
    text = message.get("content") or data.get("response") or ""
    return {
        "text": text,
        "provider": provider["provider"],
        "model": model,
        "finish_reason": data.get("done_reason") or "stop",
        "usage": {
            "raw": {
                k: data.get(k)
                for k in ("prompt_eval_count", "eval_count", "total_duration")
                if k in data
            }
        },
    }


def _hf_dispatch(
    request: FreeLLMDispatchRequest, provider: Dict[str, Any]
) -> Dict[str, Any]:
    token = (
        os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACE_TOKEN")
        or os.getenv("HUGGING_FACE_HUB_TOKEN")
    )
    if not token:
        raise HTTPException(status_code=400, detail="Hugging Face token not configured")
    model = request.model or provider["default_model"]
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": request.system
                or "You are a concise coding worker in the HYDRA mission dock.",
            },
            {"role": "user", "content": request.prompt},
        ],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    data = _http_json(
        os.getenv(
            "HF_ROUTER_CHAT_URL", "https://router.huggingface.co/v1/chat/completions"
        ),
        payload,
        {"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return {
        "text": message.get("content") or "",
        "provider": provider["provider"],
        "model": model,
        "finish_reason": choice.get("finish_reason") or "stop",
        "usage": data.get("usage") or {},
    }


def _custom_dispatch(
    request: FreeLLMDispatchRequest, provider: Dict[str, Any]
) -> Dict[str, Any]:
    endpoint = provider.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Custom provider missing endpoint")
    if provider.get("privacy") == "remote" and not _env_flag(
        "SCBE_ALLOW_REMOTE_FREE_LLM_CUSTOM", False
    ):
        raise HTTPException(
            status_code=400,
            detail="Remote custom providers require SCBE_ALLOW_REMOTE_FREE_LLM_CUSTOM=1",
        )
    model = request.model or provider["default_model"]
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": request.system
                or "You are a concise coding worker in the HYDRA mission dock.",
            },
            {"role": "user", "content": request.prompt},
        ],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    headers = {}
    token_env = provider.get("token_env")
    if token_env and os.getenv(str(token_env)):
        headers["Authorization"] = f"Bearer {os.getenv(str(token_env))}"
    data = _http_json(
        str(endpoint), payload, headers, timeout=float(provider.get("timeout", 45))
    )
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return {
        "text": message.get("content") or data.get("text") or "",
        "provider": provider["provider"],
        "model": model,
        "finish_reason": choice.get("finish_reason")
        or data.get("finish_reason")
        or "stop",
        "usage": data.get("usage") or {},
    }


@free_llm_router.get("/providers")
async def list_free_llm_providers(x_api_key: str = Header(...)):
    _ = await verify_api_key(x_api_key)
    return {"status": "ok", "data": free_llm_registry()}


@free_llm_router.get("/ollama-launchers")
async def list_ollama_launchers(x_api_key: str = Header(...)):
    _ = await verify_api_key(x_api_key)
    return {"status": "ok", "data": _ollama_launch_registry()}


@free_llm_router.post("/ollama-launch-plan")
async def plan_ollama_launcher(
    request: OllamaLaunchPlanRequest, x_api_key: str = Header(...)
):
    user = await verify_api_key(x_api_key)
    return {"status": "ok", "data": build_ollama_launch_plan(request, user=user)}


def dispatch_free_llm_request(
    request: FreeLLMDispatchRequest,
    *,
    user: str = "internal",
    origin: Literal["inside", "outside"] = "inside",
) -> Dict[str, Any]:
    """Dispatch a free/open LLM request and write a redacted bus event."""

    registry = free_llm_registry()
    provider = _select_provider(request, registry)
    if request.require_free and provider.get("cost") not in {
        "free",
        "free_local_runtime",
        "account_or_free_tier",
        "user_configured",
    }:
        raise HTTPException(
            status_code=400, detail="Selected provider is not marked free/open"
        )
    route = {
        "provider": provider["provider"],
        "kind": provider["kind"],
        "privacy": provider["privacy"],
        "model": request.model or provider["default_model"],
        "dry_run": request.dry_run,
    }
    if request.dry_run:
        bus_event = _build_bus_event(
            request=request,
            user=user,
            route=route,
            result=None,
            origin=origin,
        )
        _append_bus_event(bus_event)
        return {
            "status": "ok",
            "data": {
                "version": "hydra-free-llm-dispatch-v1",
                "user": user,
                "route": route,
                "bus_event": bus_event,
            },
        }
    try:
        if provider["kind"] == "offline":
            result = _offline_dispatch(request, provider)
        elif provider["kind"] == "ollama":
            result = _ollama_dispatch(request, provider)
        elif provider["kind"] == "huggingface":
            result = _hf_dispatch(request, provider)
        elif provider["kind"] == "custom":
            result = _custom_dispatch(request, provider)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported provider kind {provider['kind']}"
            )
    except HTTPException:
        raise
    except Exception as exc:
        if provider["kind"] != "offline" and not request.provider:
            fallback = _offline_dispatch(request, registry["providers"]["offline"])
            fallback["fallback_from"] = provider["provider"]
            fallback["fallback_error_class"] = str(exc)
            fallback_route = {
                "provider": "offline",
                "kind": "offline",
                "privacy": "local",
                "model": fallback["model"],
            }
            bus_event = _build_bus_event(
                request=request,
                user=user,
                route=fallback_route,
                result=fallback,
                error=str(exc),
                origin=origin,
            )
            _append_bus_event(bus_event)
            return {
                "status": "ok",
                "data": {
                    "version": "hydra-free-llm-dispatch-v1",
                    "user": user,
                    "route": fallback_route,
                    "result": fallback,
                    "bus_event": bus_event,
                },
            }
        bus_event = _build_bus_event(
            request=request,
            user=user,
            route=route,
            result=None,
            error=str(exc),
            origin=origin,
        )
        _append_bus_event(bus_event)
        raise HTTPException(status_code=502, detail="provider_dispatch_failed") from exc
    bus_event = _build_bus_event(
        request=request,
        user=user,
        route=route,
        result=result,
        origin=origin,
    )
    _append_bus_event(bus_event)
    return {
        "status": "ok",
        "data": {
            "version": "hydra-free-llm-dispatch-v1",
            "user": user,
            "route": route,
            "result": result,
            "bus_event": bus_event,
        },
    }


@free_llm_router.post("/dispatch")
async def dispatch_free_llm(
    request: FreeLLMDispatchRequest, x_api_key: str = Header(...)
):
    user = await verify_api_key(x_api_key)
    return dispatch_free_llm_request(request, user=user, origin="outside")
