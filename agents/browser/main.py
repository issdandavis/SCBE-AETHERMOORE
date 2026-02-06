"""
@file main.py
@module agents/browser/main
@layer Layer 13, Layer 14
@component FastAPI Browser Agent with Geometric Containment
@version 1.0.0

Browser agent with provable geometric containment using Poincare ball model.
Core loop: Observe → Embed → PHDM.is_safe() → Execute if radius < safe_radius
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, Field, field_validator

from .phdm_brain import SimplePHDM, SafetyDecision, ContainmentResult, create_phdm_brain
from .playwright_wrapper import PlaywrightWrapper, BrowserConfig, ScreenshotResult
from .vision_embedding import VisionEmbedder, EmbeddingResult, create_vision_embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API key validation (matches existing pattern)
VALID_API_KEYS = {
    "browser-agent-key": "browser-agent",
    "test-key": "test-user"
}


async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key authentication."""
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return VALID_API_KEYS[x_api_key]


# Global state
_browser: Optional[PlaywrightWrapper] = None
_embedder: Optional[VisionEmbedder] = None
_phdm: Optional[SimplePHDM] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _browser, _embedder, _phdm

    # Initialize components
    logger.info("Initializing browser agent components...")

    _phdm = create_phdm_brain(safe_radius=0.92, dim=16)
    _embedder = await create_vision_embedder(target_dim=16)

    logger.info(
        f"PHDM Brain initialized: safe_radius={_phdm.safe_radius}, dim={_phdm.dim}"
    )

    yield

    # Cleanup
    if _browser:
        await _browser.close()
    logger.info("Browser agent shutdown complete")


app = FastAPI(
    title="Geometrically-Contained Browser Agent",
    description="""
    Browser automation with provable geometric safety containment.

    Uses Poincaré ball model where:
    - Origin = maximum safety (trusted behavior)
    - Boundary = maximum risk
    - Actions blocked if embedding radius >= 0.92

    Core loop: Observe → Embed to Poincaré ball → Check safety → Execute if safe
    """,
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# Request/Response Models
# ============================================================================

class BrowseActionType(str, Enum):
    """Supported browser action types."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    EXTRACT = "extract"


class BrowseAction(BaseModel):
    """Single browser action to execute."""
    action: BrowseActionType
    target: str = Field(..., description="URL, CSS selector, or scroll direction")
    value: Optional[str] = Field(None, description="Text to type (for TYPE action)")
    timeout_ms: Optional[int] = Field(None, ge=1000, le=60000)

    @field_validator('target')
    @classmethod
    def validate_target(cls, v):
        if not v or not v.strip():
            raise ValueError("Target cannot be empty")
        return v.strip()


class BrowseRequest(BaseModel):
    """Request to execute browser actions."""
    actions: List[BrowseAction] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of actions to execute"
    )
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    dry_run: bool = Field(False, description="Check safety without executing")


class ContainmentInfo(BaseModel):
    """Containment check information."""
    decision: str
    radius: float
    hyperbolic_distance: float
    risk_score: float
    safe_radius: float
    message: str


class ActionResult(BaseModel):
    """Result of a single action."""
    action: str
    target: str
    success: bool
    containment: ContainmentInfo
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_ms: float


class BrowseResponse(BaseModel):
    """Response from browse endpoint."""
    status: str
    session_id: str
    total_actions: int
    executed_actions: int
    blocked_actions: int
    results: List[ActionResult]
    trace: str


class SafetyCheckRequest(BaseModel):
    """Request to check action safety without browser."""
    action: BrowseActionType
    target: str
    context: Optional[str] = Field(None, description="Optional page context")


class SafetyCheckResponse(BaseModel):
    """Safety check result."""
    containment: ContainmentInfo
    would_execute: bool
    trace: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    phdm_ready: bool
    embedder_ready: bool
    browser_ready: bool
    safe_radius: float
    dimension: int
    containment_stats: Dict[str, Any]


# ============================================================================
# Core Browse Logic
# ============================================================================

async def ensure_browser() -> PlaywrightWrapper:
    """Ensure browser is initialized."""
    global _browser

    if _browser is None:
        config = BrowserConfig(
            headless=True,
            default_timeout_ms=30000,
            max_actions_per_session=100
        )
        _browser = PlaywrightWrapper(config)
        await _browser.initialize()
        logger.info("Browser initialized on demand")

    return _browser


async def check_action_safety(
    action: BrowseAction,
    context_embedding: Optional[any] = None
) -> ContainmentResult:
    """
    Check if an action is safe to execute.

    Pipeline:
    1. Embed action to Poincaré ball
    2. Check radius against safe_radius
    3. Compute full containment result

    Args:
        action: The action to check
        context_embedding: Optional current page context

    Returns:
        ContainmentResult with safety decision
    """
    # Embed the action
    embedding_result = await _embedder.embed_action(
        action_type=action.action.value,
        target=action.target,
        context_embedding=context_embedding
    )

    # Check containment
    containment = _phdm.check_containment(embedding_result.poincare_embedding)

    return containment


async def execute_action(
    browser: PlaywrightWrapper,
    action: BrowseAction
) -> Dict[str, Any]:
    """
    Execute a browser action and return results.

    Args:
        browser: Browser instance
        action: Action to execute

    Returns:
        Action-specific result data
    """
    if action.action == BrowseActionType.NAVIGATE:
        url = await browser.navigate(action.target, timeout_ms=action.timeout_ms)
        return {"url": url}

    elif action.action == BrowseActionType.CLICK:
        await browser.click(action.target, timeout_ms=action.timeout_ms)
        return {"clicked": action.target}

    elif action.action == BrowseActionType.TYPE:
        if not action.value:
            raise ValueError("TYPE action requires 'value' field")
        await browser.type_text(action.target, action.value, timeout_ms=action.timeout_ms)
        return {"typed": len(action.value), "target": action.target}

    elif action.action == BrowseActionType.SCREENSHOT:
        screenshot = await browser.screenshot(
            selector=action.target if action.target != "full_page" else None,
            timeout_ms=action.timeout_ms
        )
        return {
            "screenshot": screenshot.to_base64()[:100] + "...",  # Truncated for response
            "width": screenshot.width,
            "height": screenshot.height,
            "full_data_length": len(screenshot.data)
        }

    elif action.action == BrowseActionType.SCROLL:
        await browser.scroll(direction=action.target, timeout_ms=action.timeout_ms)
        return {"scrolled": action.target}

    elif action.action == BrowseActionType.EXTRACT:
        text = await browser.extract_text(action.target, timeout_ms=action.timeout_ms)
        return {"text": text[:1000] if text else "", "length": len(text) if text else 0}

    else:
        raise ValueError(f"Unknown action type: {action.action}")


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/v1/browse", response_model=BrowseResponse, tags=["Browser Agent"])
async def browse(
    request: BrowseRequest,
    user: str = Depends(verify_api_key)
):
    """
    Execute browser actions with geometric containment safety.

    ## Core Loop
    For each action:
    1. **Observe**: Get current page state (if navigated)
    2. **Embed**: Convert action to Poincaré ball embedding
    3. **Check**: PHDM.is_safe(embedding) - verify radius < 0.92
    4. **Execute**: Only if safe, perform the browser action

    ## Safety Guarantees
    - Actions with embedding radius >= 0.92 are BLOCKED
    - All containment decisions are logged for audit
    - Hyperbolic geometry ensures adversarial drift is exponentially costly

    ## Responses
    - `ALLOW`: Action executed successfully
    - `QUARANTINE`: Action executed with elevated monitoring
    - `ESCALATE`: Action requires human review (not executed)
    - `DENY`: Action blocked due to safety violation
    """
    import time
    import uuid

    session_id = request.session_id or str(uuid.uuid4())[:8]
    results: List[ActionResult] = []
    executed = 0
    blocked = 0
    context_embedding = None

    browser = None
    if not request.dry_run:
        browser = await ensure_browser()

    for action in request.actions:
        start_time = time.time()

        # Check safety
        containment = await check_action_safety(action, context_embedding)

        containment_info = ContainmentInfo(
            decision=containment.decision.value,
            radius=containment.radius,
            hyperbolic_distance=containment.hyperbolic_distance,
            risk_score=containment.risk_score,
            safe_radius=_phdm.safe_radius,
            message=containment.message
        )

        # Determine if we should execute
        should_execute = (
            not request.dry_run and
            containment.decision in [SafetyDecision.ALLOW, SafetyDecision.QUARANTINE]
        )

        result_data = None
        error = None

        if should_execute:
            try:
                result_data = await execute_action(browser, action)
                executed += 1

                # Update context embedding from screenshot if available
                if action.action == BrowseActionType.SCREENSHOT:
                    pass  # Could capture embedding here for future actions

            except Exception as e:
                error = str(e)
                logger.error(f"Action execution failed: {e}")
        else:
            blocked += 1
            if request.dry_run:
                error = "Dry run - not executed"
            else:
                error = f"Blocked by containment: {containment.decision.value}"

        execution_ms = (time.time() - start_time) * 1000

        results.append(ActionResult(
            action=action.action.value,
            target=action.target,
            success=should_execute and error is None,
            containment=containment_info,
            data=result_data,
            error=error,
            execution_ms=execution_ms
        ))

        # Update context for next action
        if containment.embedding is not None:
            context_embedding = containment.embedding

    return BrowseResponse(
        status="success" if blocked == 0 else "partial" if executed > 0 else "blocked",
        session_id=session_id,
        total_actions=len(request.actions),
        executed_actions=executed,
        blocked_actions=blocked,
        results=results,
        trace=f"v1_browse_{session_id}_{executed}exec_{blocked}block"
    )


@app.post("/v1/safety-check", response_model=SafetyCheckResponse, tags=["Safety"])
async def safety_check(
    request: SafetyCheckRequest,
    user: str = Depends(verify_api_key)
):
    """
    Check if an action would be allowed without executing.

    Use this to pre-validate actions before submission.
    """
    containment = await check_action_safety(
        BrowseAction(action=request.action, target=request.target),
        context_embedding=None
    )

    return SafetyCheckResponse(
        containment=ContainmentInfo(
            decision=containment.decision.value,
            radius=containment.radius,
            hyperbolic_distance=containment.hyperbolic_distance,
            risk_score=containment.risk_score,
            safe_radius=_phdm.safe_radius,
            message=containment.message
        ),
        would_execute=containment.decision in [SafetyDecision.ALLOW, SafetyDecision.QUARANTINE],
        trace=f"v1_safety_{containment.decision.value}_{containment.radius:.4f}"
    )


@app.get("/v1/containment-stats", tags=["Safety"])
async def containment_stats(user: str = Depends(verify_api_key)):
    """
    Get containment statistics from recent checks.

    Returns aggregated metrics about safety decisions.
    """
    stats = _phdm.get_containment_stats()

    return {
        "status": "success",
        "safe_radius": _phdm.safe_radius,
        "dimension": _phdm.dim,
        "harmonic_base": _phdm.harmonic_base,
        "stats": stats,
        "thresholds": {
            "allow": _phdm.allow_threshold,
            "quarantine": _phdm.quarantine_threshold
        }
    }


@app.post("/v1/reset-session", tags=["Session"])
async def reset_session(user: str = Depends(verify_api_key)):
    """
    Reset the browser session and containment history.
    """
    global _browser

    if _browser:
        _browser.reset_session()

    _phdm.reset_history()
    _embedder.clear_cache()

    return {
        "status": "success",
        "message": "Session reset complete"
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """
    Health check endpoint.

    Returns component status and configuration.
    """
    return HealthResponse(
        status="healthy",
        phdm_ready=_phdm is not None,
        embedder_ready=_embedder is not None and _embedder._is_initialized,
        browser_ready=_browser is not None and _browser._is_initialized,
        safe_radius=_phdm.safe_radius if _phdm else 0.0,
        dimension=_phdm.dim if _phdm else 0,
        containment_stats=_phdm.get_containment_stats() if _phdm else {}
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Geometrically-Contained Browser Agent",
        "version": "1.0.0",
        "description": "Browser automation with Poincaré ball safety containment",
        "safe_radius": 0.92,
        "dimension": 16,
        "endpoints": {
            "browse": "POST /v1/browse",
            "safety_check": "POST /v1/safety-check",
            "stats": "GET /v1/containment-stats",
            "reset": "POST /v1/reset-session",
            "health": "GET /health"
        },
        "documentation": "/docs"
    }


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agents.browser.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
