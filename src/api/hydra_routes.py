"""
HYDRA API Routes
================

FastAPI router exposing HYDRA spine operations via REST endpoints.
Provides head management, workflow execution, switchboard access,
and LLM think/reason capabilities.

All endpoints use the same x-api-key header auth as the core SCBE API.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================


class HydraExecuteRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=256, description="Action to execute")
    target: str = Field(default="", max_length=2048, description="Action target")
    params: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    head_id: Optional[str] = Field(default=None, max_length=128, description="Route to specific head")


class HydraRegisterHeadRequest(BaseModel):
    ai_type: str = Field(..., min_length=1, max_length=64, description="AI provider type (claude, gpt, gemini, local)")
    model: str = Field(..., min_length=1, max_length=128, description="Model identifier")
    callsign: Optional[str] = Field(default=None, max_length=64, description="Custom callsign")


class HydraWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256, description="Workflow name")
    phases: List[Dict[str, Any]] = Field(..., min_length=1, description="Ordered list of phase definitions")


class HydraSwitchboardEnqueueRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=128, description="Target role channel")
    payload: Dict[str, Any] = Field(..., description="Task payload")
    priority: int = Field(default=100, ge=0, le=10000, description="Priority (lower = higher priority)")
    dedupe_key: Optional[str] = Field(default=None, max_length=256, description="Deduplication key")


class HydraThinkRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000, description="Prompt for the AI head")
    head_id: Optional[str] = Field(default=None, max_length=128, description="Specific head to use")
    system: Optional[str] = Field(default=None, max_length=8000, description="System prompt override")


class HydraResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Research query in natural language")
    max_subtasks: int = Field(default=5, ge=1, le=10, description="Max parallel sub-tasks")
    discovery_per_subtask: int = Field(default=3, ge=1, le=10, description="Max pages per sub-task")
    provider_order: List[str] = Field(
        default_factory=lambda: ["claude", "gpt", "gemini"],
        description="LLM providers to use (tried in order)",
    )
    mode: str = Field(default="httpx", pattern="^(local|cloud|httpx)$", description="Browsing mode: httpx (lightweight), local (Playwright), or cloud (workers)")
    local_max_tabs: int = Field(default=4, ge=1, le=12, description="Max local browser tabs")
    extract_max_chars: int = Field(default=8000, ge=500, le=50000, description="Per-page extracted char cap")
    synthesis_provider: Optional[str] = Field(default=None, max_length=64, description="Preferred synthesis provider")
    use_hf_summarizer: bool = Field(default=False, description="Use HuggingFace BART for page compression")


# ============================================================================
# SHARED STATE
# ============================================================================

# Singleton spine instance; initialized via init_hydra_spine().
_spine = None
# Map of head_id -> LLMProvider for heads that have LLM backing.
_providers: Dict[str, Any] = {}


def get_spine():
    """Return the shared HydraSpine singleton, or raise if not initialized."""
    if _spine is None:
        raise HTTPException(500, "HYDRA spine not initialized")
    return _spine


# ============================================================================
# AUTH (mirrors main.py verify_api_key)
# ============================================================================

# Import at module level is safe; the dict is defined in main.py and we
# re-use the same validation logic here without coupling tightly.
VALID_API_KEYS = {
    "demo_key_12345": "demo_user",
    "pilot_key_67890": "pilot_customer",
}


async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key and return user identifier."""
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(401, "Invalid API key")
    return VALID_API_KEYS[x_api_key]


# ============================================================================
# ROUTER
# ============================================================================

hydra_router = APIRouter(prefix="/hydra", tags=["HYDRA"])


# ---------------------------------------------------------------------------
# POST /hydra/execute
# ---------------------------------------------------------------------------

@hydra_router.post("/execute")
async def hydra_execute(
    request: HydraExecuteRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Execute Action

    Execute an action through the HYDRA spine with full SCBE governance.
    """
    spine = get_spine()

    command: Dict[str, Any] = {
        "action": request.action,
        "target": request.target,
        "params": request.params,
    }
    if request.head_id:
        if request.head_id not in spine.heads:
            raise HTTPException(404, f"Head '{request.head_id}' not found")
        command["head_id"] = request.head_id

    try:
        result = await spine.execute(command)
        return {"status": "ok", "data": result}
    except Exception as exc:
        raise HTTPException(500, f"Execute failed: {exc}")


# ---------------------------------------------------------------------------
# GET /hydra/status
# ---------------------------------------------------------------------------

@hydra_router.get("/status")
async def hydra_status(user: str = Depends(verify_api_key)):
    """
    ## HYDRA Status

    Return connected heads, limbs, active workflows, and switchboard stats.
    """
    spine = get_spine()

    heads_info = {}
    for hid, head in spine.heads.items():
        heads_info[hid] = {
            "ai_type": head.ai_type,
            "model": head.model,
            "callsign": head.callsign,
            "status": head.status.value if hasattr(head.status, "value") else str(head.status),
            "action_count": head.action_count,
            "has_llm_provider": hid in _providers,
        }

    limbs_info = {}
    for lid, limb in spine.limbs.items():
        limbs_info[lid] = {
            "limb_type": limb.limb_type,
            "active": limb.active,
            "action_count": limb.action_count,
        }

    workflows_info = {}
    for wid, wf in spine.workflows.items():
        workflows_info[wid] = {
            "name": wf.name,
            "status": wf.status.value if hasattr(wf.status, "value") else str(wf.status),
            "current_phase": wf.current_phase,
            "total_phases": len(wf.phases),
            "created_at": wf.created_at,
        }

    switchboard_stats = None
    if spine.switchboard:
        try:
            switchboard_stats = spine.switchboard.stats()
        except Exception:
            switchboard_stats = {"error": "Failed to read switchboard stats"}

    return {
        "status": "ok",
        "data": {
            "heads": heads_info,
            "limbs": limbs_info,
            "workflows": workflows_info,
            "switchboard": switchboard_stats,
            "role_channels": {k: list(v) for k, v in spine.role_channels.items()},
        },
    }


# ---------------------------------------------------------------------------
# POST /hydra/heads
# ---------------------------------------------------------------------------

@hydra_router.post("/heads")
async def hydra_register_head(
    request: HydraRegisterHeadRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Register AI Head

    Create and connect a new AI head to the HYDRA spine.
    If the corresponding API key environment variable is set, an LLM
    provider is attached so the head can be used with /hydra/think.
    """
    spine = get_spine()

    try:
        from hydra.head import HydraHead

        head = HydraHead(
            ai_type=request.ai_type,
            model=request.model,
            callsign=request.callsign,
        )
        await head.connect(spine)
    except Exception as exc:
        raise HTTPException(500, f"Failed to create head: {exc}")

    # Attempt to attach an LLM provider for /hydra/think support.
    try:
        from hydra.llm_providers import create_provider

        provider = create_provider(request.ai_type, model=request.model)
        _providers[head.head_id] = provider
    except Exception:
        # Provider creation is best-effort; the head still works for
        # execute/workflow operations without an LLM provider.
        pass

    return {
        "status": "created",
        "data": {
            "head_id": head.head_id,
            "callsign": head.callsign,
            "ai_type": head.ai_type,
            "model": head.model,
            "has_llm_provider": head.head_id in _providers,
        },
    }


# ---------------------------------------------------------------------------
# DELETE /hydra/heads/{head_id}
# ---------------------------------------------------------------------------

@hydra_router.delete("/heads/{head_id}")
async def hydra_disconnect_head(
    head_id: str,
    user: str = Depends(verify_api_key),
):
    """
    ## Disconnect AI Head

    Remove an AI head from the HYDRA spine.
    """
    spine = get_spine()

    if head_id not in spine.heads:
        raise HTTPException(404, f"Head '{head_id}' not found")

    try:
        spine.disconnect_head(head_id)
        _providers.pop(head_id, None)
    except Exception as exc:
        raise HTTPException(500, f"Failed to disconnect head: {exc}")

    return {"status": "disconnected", "data": {"head_id": head_id}}


# ---------------------------------------------------------------------------
# POST /hydra/workflow
# ---------------------------------------------------------------------------

@hydra_router.post("/workflow")
async def hydra_workflow(
    request: HydraWorkflowRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Define and Run Workflow

    Define a multi-phase workflow and execute it immediately through the spine.
    """
    spine = get_spine()

    if not request.phases:
        raise HTTPException(400, "At least one phase is required")

    try:
        result = await spine.execute({
            "action": "workflow",
            "definition": {
                "name": request.name,
                "phases": request.phases,
            },
        })
        return {"status": "ok", "data": result}
    except Exception as exc:
        raise HTTPException(500, f"Workflow execution failed: {exc}")


# ---------------------------------------------------------------------------
# GET /hydra/switchboard/stats
# ---------------------------------------------------------------------------

@hydra_router.get("/switchboard/stats")
async def hydra_switchboard_stats(user: str = Depends(verify_api_key)):
    """
    ## Switchboard Statistics

    Return task queue and role channel statistics from the HYDRA switchboard.
    """
    spine = get_spine()

    if not spine.switchboard:
        raise HTTPException(400, "Switchboard is not enabled on this spine instance")

    try:
        stats = spine.switchboard.stats()
        return {"status": "ok", "data": stats}
    except Exception as exc:
        raise HTTPException(500, f"Failed to read switchboard stats: {exc}")


# ---------------------------------------------------------------------------
# POST /hydra/switchboard/enqueue
# ---------------------------------------------------------------------------

@hydra_router.post("/switchboard/enqueue")
async def hydra_switchboard_enqueue(
    request: HydraSwitchboardEnqueueRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Enqueue Switchboard Task

    Add a task to the switchboard queue for a specific role channel.
    """
    spine = get_spine()

    if not spine.switchboard:
        raise HTTPException(400, "Switchboard is not enabled on this spine instance")

    try:
        result = spine.switchboard.enqueue_task(
            role=request.role,
            payload=request.payload,
            dedupe_key=request.dedupe_key,
            priority=request.priority,
        )
        return {"status": "ok", "data": result}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(500, f"Enqueue failed: {exc}")


# ---------------------------------------------------------------------------
# POST /hydra/think
# ---------------------------------------------------------------------------

@hydra_router.post("/think")
async def hydra_think(
    request: HydraThinkRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Think / Reason

    Ask an AI head to think about a prompt and return the LLM response.
    Uses the LLM provider attached to the specified (or any available) head.
    """
    spine = get_spine()

    # Resolve which provider to use.
    provider = None

    if request.head_id:
        if request.head_id not in spine.heads:
            raise HTTPException(404, f"Head '{request.head_id}' not found")
        provider = _providers.get(request.head_id)
        if provider is None:
            raise HTTPException(
                400,
                f"Head '{request.head_id}' has no LLM provider attached. "
                "Register it with a valid API key to enable /think.",
            )
    else:
        # Pick first available provider.
        for hid, prov in _providers.items():
            if hid in spine.heads:
                provider = prov
                break

    if provider is None:
        raise HTTPException(
            400,
            "No AI head with an LLM provider is available. "
            "Register a head with POST /hydra/heads first.",
        )

    try:
        response = await provider.complete(
            prompt=request.prompt,
            system=request.system,
        )
        return {
            "status": "ok",
            "data": {
                "text": response.text,
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "finish_reason": response.finish_reason,
            },
        }
    except Exception as exc:
        raise HTTPException(500, f"Think failed: {exc}")


# ---------------------------------------------------------------------------
# POST /hydra/research
# ---------------------------------------------------------------------------

@hydra_router.post("/research")
async def hydra_research(
    request: HydraResearchRequest,
    user: str = Depends(verify_api_key),
):
    """
    ## Multi-Agent Research

    Decompose a research query into parallel sub-tasks, browse the web
    simultaneously with multiple agents, extract content, and synthesize
    a structured research report.
    """
    spine = get_spine()

    try:
        from hydra.research import ResearchOrchestrator, ResearchConfig

        config = ResearchConfig(
            mode=request.mode,
            provider_order=request.provider_order,
            synthesis_provider=request.synthesis_provider,
            max_subtasks=request.max_subtasks,
            discovery_per_subtask=request.discovery_per_subtask,
            local_max_tabs=request.local_max_tabs,
            extract_max_chars=request.extract_max_chars,
            use_hf_summarizer=request.use_hf_summarizer,
        )

        # Collect existing LLM providers from registered heads
        providers_dict = {}
        for hid, prov in _providers.items():
            if hid in spine.heads:
                head = spine.heads[hid]
                ai_type = getattr(head, "ai_type", "unknown")
                if ai_type not in providers_dict:
                    providers_dict[ai_type] = prov

        orchestrator = ResearchOrchestrator(
            config=config,
            switchboard=spine.switchboard if request.mode == "cloud" else None,
            providers=providers_dict if providers_dict else None,
        )

        try:
            report = await orchestrator.research(request.query)
            return {"status": "ok", "data": report.to_dict()}
        finally:
            await orchestrator.close()

    except Exception as exc:
        raise HTTPException(500, f"Research failed: {exc}")


# ============================================================================
# SPINE INITIALIZATION
# ============================================================================


async def init_hydra_spine() -> None:
    """
    Initialize the shared HydraSpine singleton and optionally attach a
    default AI head based on available API keys.

    Called from the FastAPI startup event in main.py.
    """
    global _spine

    from hydra.spine import HydraSpine
    from hydra.head import HydraHead

    _spine = HydraSpine(
        use_dual_lattice=False,  # Avoid hard dependency on dual_lattice at API level
        use_switchboard=True,
    )

    print("[HYDRA-API] Spine initialized")

    # Register researcher role channel for research workers
    if hasattr(_spine, "role_channels"):
        _spine.role_channels.setdefault("researcher", set())
        print("[HYDRA-API] Researcher role channel registered")

    # Auto-register a default head if an LLM API key is available.
    default_head = None

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from hydra.llm_providers import create_provider

            default_head = HydraHead(ai_type="claude", model="claude-sonnet-4-20250514", callsign="CT-DEFAULT")
            await default_head.connect(_spine)
            _providers[default_head.head_id] = create_provider("claude")
            print(f"[HYDRA-API] Default Claude head registered: {default_head.head_id}")
        except Exception as exc:
            print(f"[HYDRA-API] Failed to create default Claude head: {exc}")
            default_head = None

    if default_head is None and os.environ.get("OPENAI_API_KEY"):
        try:
            from hydra.llm_providers import create_provider

            default_head = HydraHead(ai_type="gpt", model="gpt-4o", callsign="GP-DEFAULT")
            await default_head.connect(_spine)
            _providers[default_head.head_id] = create_provider("gpt")
            print(f"[HYDRA-API] Default GPT head registered: {default_head.head_id}")
        except Exception as exc:
            print(f"[HYDRA-API] Failed to create default GPT head: {exc}")

    if default_head is None:
        print("[HYDRA-API] No LLM API key found; /hydra/think requires manual head registration")
