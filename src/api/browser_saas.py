"""
Browser-as-a-Service (BaaS) API Gateway
=========================================
Governed, multi-tenant, API-accessible headless browser service.

Turn the browser into an API that people call, with SCBE 14-layer
governance securing every action and every interaction generating
training data for the baby AI.

Start: uvicorn src.api.browser_saas:app --host 127.0.0.1 --port 8600

Endpoints:
    POST   /v1/sessions                  — Create governed browser session
    GET    /v1/sessions/{id}              — Get session status
    DELETE /v1/sessions/{id}              — Destroy session
    POST   /v1/sessions/{id}/navigate     — Navigate to URL
    POST   /v1/sessions/{id}/click        — Click element
    POST   /v1/sessions/{id}/type         — Type into element
    POST   /v1/sessions/{id}/screenshot   — Take screenshot (base64)
    POST   /v1/sessions/{id}/snapshot     — Get accessibility tree
    POST   /v1/sessions/{id}/execute      — Run NL task (baby AI plans)
    GET    /v1/sessions/{id}/perception   — Get PollyVision perception
    POST   /v1/search                     — Governed web search
    POST   /v1/research                   — Deep research pipeline
    POST   /v1/compute/train              — Trigger remote compute job
    GET    /v1/compute/job/{job_id}       — Query compute job status
    POST   /v1/compute/job/{job_id}/cancel— Cancel compute job
    GET    /v1/usage                      — API key usage stats
    GET    /health                        — Health check
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root for imports
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.api.session_manager import (
    SessionManager,
    BrowserSession,
    Tier,
    SessionLimitError,
    SessionNotFoundError,
    SessionExpiredError,
    SessionPermissionError,
)
from src.api.training_tap import TrainingTap
from src.api.governance_saas import evaluate_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("baas-gateway")


# ---------------------------------------------------------------------------
#  Optional imports (graceful degradation)
# ---------------------------------------------------------------------------

try:
    from aetherbrowse.worker.browser_worker import BrowserWorker
    HAS_WORKER = True
except ImportError:
    HAS_WORKER = False
    logger.warning("BrowserWorker not available — sessions will be mock-only")

try:
    from aetherbrowse.runtime.perceiver import perceive, PagePerception
    HAS_PERCEIVER = True
except ImportError:
    HAS_PERCEIVER = False

try:
    from aetherbrowse.runtime.planner import create_plan
    HAS_PLANNER = True
except ImportError:
    HAS_PLANNER = False

try:
    from src.browser.headless import HeadlessBrowser
    HAS_HEADLESS = True
except ImportError:
    HAS_HEADLESS = False


# ---------------------------------------------------------------------------
#  App + Globals
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SCBE Browser-as-a-Service",
    version="1.0.0",
    description="Governed headless browser API — every action trained, every call secured.",
    docs_url="/docs",
    redoc_url="/redoc",
)

_CORS_ORIGINS = os.environ.get(
    "BAAS_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://localhost:8080,http://localhost:8600",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _CORS_ORIGINS if o.strip()],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

COLAB_API_URL = os.environ.get("COLAB_API_URL", "").strip()
DEFAULT_COLAB_NOTEBOOK = os.environ.get(
    "COLAB_NOTEBOOK_URL",
    "https://colab.research.google.com/drive/1lAVkczDpiSlXVoCXgJ6UBpTvlgjM1o9M?usp=sharing",
).strip()

sessions = SessionManager()
training = TrainingTap()

# API key → tier mapping (loaded from env or defaults)
_API_KEY_TIERS: Dict[str, Tier] = {}


def _load_api_keys():
    """Load API keys and their tiers from environment."""
    # Format: BAAS_API_KEYS=key1:pro,key2:enterprise,key3:free
    # Or simple: SCBE_API_KEYS=key1,key2 (all default to free)
    raw = os.environ.get("BAAS_API_KEYS", "")
    if raw:
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" in entry:
                key, tier_str = entry.split(":", 1)
                try:
                    _API_KEY_TIERS[key.strip()] = Tier(tier_str.strip().lower())
                except ValueError:
                    _API_KEY_TIERS[key.strip()] = Tier.FREE
            else:
                _API_KEY_TIERS[entry] = Tier.FREE

    # Also accept SCBE_API_KEYS for dev
    scbe_keys = os.environ.get("SCBE_API_KEYS", "")
    if scbe_keys:
        for key in scbe_keys.split(","):
            key = key.strip()
            if key and key not in _API_KEY_TIERS:
                _API_KEY_TIERS[key] = Tier.FREE

    # Dev fallbacks
    for dev_key in ["scbe-dev-key", "test-key"]:
        if dev_key not in _API_KEY_TIERS:
            _API_KEY_TIERS[dev_key] = Tier.PRO


_load_api_keys()


# ---------------------------------------------------------------------------
#  Auth + Rate Limiting
# ---------------------------------------------------------------------------

_rate_buckets: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 120


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Validate API key and apply rate limiting."""
    if x_api_key not in _API_KEY_TIERS:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Rate limiting
    now = time.time()
    bucket = _rate_buckets.setdefault(x_api_key, [])
    bucket[:] = [t for t in bucket if t > now - RATE_LIMIT_WINDOW]
    if len(bucket) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)

    # Ensure tier is set on session manager
    sessions.set_tier(x_api_key, _API_KEY_TIERS[x_api_key])
    return x_api_key


# ---------------------------------------------------------------------------
#  Request Models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    headless: bool = True
    mobile: bool = False


class ColabComputeRequest(BaseModel):
    """Optional session-scoped compute request."""

    session_id: Optional[str] = None
    provider: str = "colab"
    purpose: Optional[str] = "train_browser_actions"
    payload: Dict[str, Any] = Field(default_factory=dict)
    action: str = "train"
    dataset: Optional[str] = None
    colab_notebook_url: Optional[str] = None

class NavigateRequest(BaseModel):
    url: str

class ClickRequest(BaseModel):
    selector: str

class TypeRequest(BaseModel):
    selector: str
    value: str

class ExecuteRequest(BaseModel):
    goal: str

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10

class ResearchRequest(BaseModel):
    topic: str
    depth: int = 2


# ---------------------------------------------------------------------------
#  Helper: Governance gate
# ---------------------------------------------------------------------------

def _govern(text: str, profile: str = "research_agent") -> Dict[str, Any]:
    """Run text through SCBE governance. Returns evaluation dict."""
    return evaluate_text(text, profile=profile)


def _check_governance(gov: Dict[str, Any], action: str) -> None:
    """Raise HTTPException if governance denies the action."""
    decision = gov.get("decision", "ALLOW")
    if str(decision).upper() == "DENY":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Action denied by SCBE governance",
                "action": action,
                "decision": decision,
                "risk_score": gov.get("risk_score", 0),
                "threats": gov.get("threats_detected", []),
                "patent": "USPTO #63/961,403 (Pending)",
            },
        )
    if str(decision).upper() == "BLOCK":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Action blocked by SCBE governance",
                "action": action,
                "decision": decision,
                "risk_score": gov.get("risk_score", 0),
                "threats": gov.get("threats_detected", []),
                "patent": "USPTO #63/961,403 (Pending)",
            },
        )


def _resolve_session(sessions_: SessionManager, session_id: str, api_key: str) -> BrowserSession:
    """Resolve session with ownership checks."""
    try:
        return sessions_.get_session_for_api_key(session_id, api_key)
    except SessionPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------------------------------------------------------------------------
#  Helper: Launch worker for session
# ---------------------------------------------------------------------------

async def _ensure_worker(session: BrowserSession, headless: bool = True, mobile: bool = False):
    """Lazy-launch a Playwright worker for the session."""
    if session._launched:
        return

    if not HAS_WORKER:
        # Mock mode — no real browser
        logger.info("Mock mode: no BrowserWorker for session %s", session.session_id)
        session._launched = True
        return

    worker = BrowserWorker()
    await worker.launch(headless=headless, mobile=mobile)
    session._worker = worker
    session._launched = True
    logger.info("Playwright worker launched for session %s", session.session_id)


def _call_colab_api(
    action: str,
    payload: Dict[str, Any],
    notebook_url: str = "",
) -> Dict[str, Any]:
    """Call external Colab webhook/API if configured."""
    resolved_notebook_url = (notebook_url or payload.get("notebook_url") or DEFAULT_COLAB_NOTEBOOK).strip()
    if not COLAB_API_URL:
        return {
            "success": False,
            "mode": "manual",
            "manual_url": resolved_notebook_url,
            "notebook_url": resolved_notebook_url,
            "message": "COLAB_API_URL is not configured. Open the notebook and run the generated payload.",
        }

    body = {"action": action, **payload}
    request = urllib.request.Request(
        COLAB_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            try:
                result = json.loads(raw)
            except Exception:
                result = {"message": raw}
            result["status"] = getattr(resp, "status", 200)
            result["success"] = True
            return result
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(e)
        return {
            "success": False,
            "status": e.code,
            "message": detail[:500],
        }
    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": str(e),
        }


# ---------------------------------------------------------------------------
#  Session Endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/sessions", tags=["Sessions"])
async def create_session(
    body: CreateSessionRequest = CreateSessionRequest(),
    api_key: str = Depends(verify_api_key),
):
    """Create a new governed browser session."""
    try:
        session = await sessions.create_session(
            api_key,
            config={"headless": body.headless, "mobile": body.mobile},
        )
    except SessionLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))

    # Launch worker in background
    asyncio.ensure_future(_ensure_worker(session, headless=body.headless, mobile=body.mobile))

    return {
        "session_id": session.session_id,
        "tier": session.tier.value,
        "ttl_seconds": session.ttl_seconds,
        "execute_enabled": session.execute_enabled,
        "actions_remaining": session.actions_remaining,
    }


@app.get("/v1/sessions/{session_id}", tags=["Sessions"])
async def get_session(session_id: str, api_key: str = Depends(verify_api_key)):
    """Get session status and current URL."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return session.to_dict()


@app.delete("/v1/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str, api_key: str = Depends(verify_api_key)):
    """Destroy a session and flush its training data."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Flush training buffer before destroying
    flushed = training.flush_session(session.training_buffer)

    await sessions.destroy_session(session_id)
    return {"destroyed": session_id, "training_pairs_flushed": flushed}


@app.get("/v1/sessions", tags=["Sessions"])
async def list_sessions(api_key: str = Depends(verify_api_key)):
    """List all active sessions for this API key."""
    return {"sessions": sessions.list_sessions(api_key)}


# ---------------------------------------------------------------------------
#  Browser Action Endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/sessions/{session_id}/navigate", tags=["Actions"])
async def navigate(session_id: str, body: NavigateRequest, api_key: str = Depends(verify_api_key)):
    """Navigate the browser to a URL."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    if session.actions_remaining <= 0:
        raise HTTPException(status_code=429, detail="Daily action limit reached")

    # Governance gate
    gov = _govern(f"navigate to {body.url}")
    _check_governance(gov, "navigate")

    # Execute
    await _ensure_worker(session, **session.worker_config)
    result = {}
    if session._worker:
        result = await session._worker.navigate(body.url)
    else:
        result = {"url": body.url, "title": "(mock)", "mock": True}

    session.current_url = result.get("url", body.url)
    session.record_action(gov.get("risk_score", 0))

    # Training pair
    pair = training.record_navigate(session.session_id, body.url, result, gov)
    session.training_buffer.append(pair)

    return {
        "url": result.get("url", body.url),
        "title": result.get("title", ""),
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.post("/v1/sessions/{session_id}/click", tags=["Actions"])
async def click(session_id: str, body: ClickRequest, api_key: str = Depends(verify_api_key)):
    """Click an element by CSS selector."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    if session.actions_remaining <= 0:
        raise HTTPException(status_code=429, detail="Daily action limit reached")

    gov = _govern(f"click element {body.selector}")
    _check_governance(gov, "click")

    await _ensure_worker(session, **session.worker_config)
    result = {}
    if session._worker:
        result = await session._worker.click(body.selector)
    else:
        result = {"action": "click", "selector": body.selector, "url": session.current_url, "mock": True}

    session.record_action(gov.get("risk_score", 0))

    pair = training.record_click(
        session.session_id, body.selector, result, gov,
        perception_before=session.last_perception,
    )
    session.training_buffer.append(pair)

    return {
        "action": "click",
        "selector": body.selector,
        "url": result.get("url", session.current_url),
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.post("/v1/sessions/{session_id}/type", tags=["Actions"])
async def type_text(session_id: str, body: TypeRequest, api_key: str = Depends(verify_api_key)):
    """Type text into an element."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    if session.actions_remaining <= 0:
        raise HTTPException(status_code=429, detail="Daily action limit reached")

    gov = _govern(f"type into {body.selector}")
    _check_governance(gov, "type")

    await _ensure_worker(session, **session.worker_config)
    result = {}
    if session._worker:
        result = await session._worker.fill(body.selector, body.value)
    else:
        result = {"action": "fill", "selector": body.selector, "mock": True}

    session.record_action(gov.get("risk_score", 0))

    pair = training.record_type(session.session_id, body.selector, body.value, result, gov)
    session.training_buffer.append(pair)

    return {
        "action": "type",
        "selector": body.selector,
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.post("/v1/sessions/{session_id}/screenshot", tags=["Actions"])
async def screenshot(session_id: str, api_key: str = Depends(verify_api_key)):
    """Take a screenshot of the current page (returns base64 PNG)."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    session.touch()

    await _ensure_worker(session, **session.worker_config)
    if session._worker and session._worker.page:
        png_bytes = await session._worker.page.screenshot(full_page=False)
        b64 = base64.b64encode(png_bytes).decode("ascii")
        return {"screenshot": b64, "format": "png", "encoding": "base64"}
    else:
        return {"screenshot": None, "mock": True}


@app.post("/v1/sessions/{session_id}/snapshot", tags=["Actions"])
async def snapshot(session_id: str, api_key: str = Depends(verify_api_key)):
    """Get the accessibility tree of the current page."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    session.touch()

    await _ensure_worker(session, **session.worker_config)
    if session._worker:
        result = await session._worker.snapshot()

        # Run perceiver if available
        if HAS_PERCEIVER and "tree" in result:
            perception = perceive(
                tree=result["tree"],
                url=result.get("url", session.current_url),
                title=result.get("title", ""),
            )
            session.last_perception = perception.to_dict() if hasattr(perception, "to_dict") else {}
            return {
                "tree": result["tree"],
                "perception": session.last_perception,
            }

        return {"tree": result.get("tree"), "url": result.get("url")}
    else:
        return {"tree": None, "mock": True}


@app.post("/v1/sessions/{session_id}/execute", tags=["Actions"])
async def execute_task(session_id: str, body: ExecuteRequest, api_key: str = Depends(verify_api_key)):
    """Execute a natural-language task using the baby AI planner."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not session.execute_enabled:
        raise HTTPException(status_code=403, detail="Execute not available on Free tier. Upgrade to Pro.")

    if session.actions_remaining <= 0:
        raise HTTPException(status_code=429, detail="Daily action limit reached")

    # Governance gate on the goal itself
    gov = _govern(body.goal)
    _check_governance(gov, "execute")

    await _ensure_worker(session, **session.worker_config)
    plan_dict = {}
    success = False

    if HAS_PLANNER:
        # Use AetherBrowse planner to create an action plan
        perception = None
        if HAS_PERCEIVER and session.last_perception:
            # Reconstruct PagePerception from cached dict
            perception = session.last_perception

        plan = await create_plan(
            goal=body.goal,
            perception=perception,
            use_llm=True,
        )
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else {"goal": body.goal}
        success = plan.confidence >= 0.5 if hasattr(plan, "confidence") else True

        # Execute the plan steps if we have a worker
        if success and session._worker and hasattr(plan, "steps"):
            for step in plan.steps:
                step_gov = _govern(f"{step.action} {getattr(step, 'value', '')}")
                if str(step_gov.get("decision", "DENY")).upper() in {"DENY", "BLOCK"}:
                    continue

                try:
                    if step.action == "navigate" and hasattr(step, "value"):
                        await session._worker.navigate(step.value)
                    elif step.action == "click" and hasattr(step, "selector"):
                        await session._worker.click(step.selector)
                    elif step.action == "type" and hasattr(step, "selector"):
                        await session._worker.fill(step.selector, getattr(step, "value", ""))
                except Exception as e:
                    logger.warning("Step failed: %s — %s", step.action, e)

                session.record_action(step_gov.get("risk_score", 0))

                if hasattr(step, "wait_after_ms") and step.wait_after_ms > 0:
                    await asyncio.sleep(step.wait_after_ms / 1000)
    else:
        plan_dict = {"goal": body.goal, "planner": "unavailable"}
        success = False

    session.record_action(gov.get("risk_score", 0))

    # Training pair (most valuable data)
    pair = training.record_execute(
        session.session_id, body.goal, plan_dict, success, gov,
        perception=session.last_perception,
    )
    session.training_buffer.append(pair)

    return {
        "goal": body.goal,
        "plan": plan_dict,
        "success": success,
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.get("/v1/sessions/{session_id}/perception", tags=["Actions"])
async def get_perception(session_id: str, api_key: str = Depends(verify_api_key)):
    """Get the cached PollyVision perception of the current page."""
    try:
        session = _resolve_session(sessions, session_id, api_key)
    except (SessionNotFoundError, SessionExpiredError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    if session.last_perception:
        return {"perception": session.last_perception}

    # Try to generate fresh perception
    await _ensure_worker(session, **session.worker_config)
    if session._worker and HAS_PERCEIVER:
        result = await session._worker.snapshot()
        if "tree" in result:
            perception = perceive(
                tree=result["tree"],
                url=result.get("url", session.current_url),
                title=result.get("title", ""),
            )
            session.last_perception = perception.to_dict() if hasattr(perception, "to_dict") else {}
            return {"perception": session.last_perception}

    return {"perception": None, "message": "No perception available. Call /snapshot first."}


# ---------------------------------------------------------------------------
#  Stateless Endpoints (no session needed)
# ---------------------------------------------------------------------------

@app.post("/v1/search", tags=["Stateless"])
async def search(body: SearchRequest, api_key: str = Depends(verify_api_key)):
    """Governed web search (DuckDuckGo). No session needed."""
    gov = _govern(f"search: {body.query}")
    _check_governance(gov, "search")

    results = []
    if HAS_HEADLESS:
        async with HeadlessBrowser() as browser:
            results = await browser.search(body.query, max_results=body.max_results)
    else:
        results = [{"title": "(mock)", "url": "https://example.com", "snippet": "Mock result"}]

    # Training pair
    training.record_search(body.query, results, gov)

    return {
        "query": body.query,
        "results": results,
        "result_count": len(results),
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.post("/v1/research", tags=["Stateless"])
async def research(body: ResearchRequest, api_key: str = Depends(verify_api_key)):
    """Deep governed research pipeline. Returns structured report."""
    gov = _govern(f"research: {body.topic}")
    _check_governance(gov, "research")

    report = {}
    if HAS_HEADLESS:
        async with HeadlessBrowser() as browser:
            report = await browser.research(body.topic, depth=body.depth)
    else:
        report = {"topic": body.topic, "results": [], "mock": True}

    return {
        "topic": body.topic,
        "report": report,
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.post("/v1/compute/train", tags=["Compute"])
async def compute_train(body: ColabComputeRequest, api_key: str = Depends(verify_api_key)):
    """Trigger a remote compute/finetuning job (Colab or another provider)."""
    gov = _govern(f"compute: {body.purpose or body.action}")
    _check_governance(gov, "compute")

    session = None
    if body.session_id:
        session = _resolve_session(sessions, body.session_id, api_key)

    dataset = body.dataset or body.payload.get(
        "dataset",
        os.environ.get("SCBE_TRAINING_DATASET", "issdandavis/scbe-aethermoore-training-data"),
    )
    notebook_url = (
        body.colab_notebook_url
        or body.payload.get("notebook_url")
        or os.environ.get("COLAB_NOTEBOOK_URL", DEFAULT_COLAB_NOTEBOOK)
    ).strip()
    result = _call_colab_api(
        "train",
        {
            "provider": body.provider,
            "action": body.action,
            "dataset": dataset,
            "purpose": body.purpose,
            "payload": {
                **body.payload,
                "dataset": dataset,
                "notebook_url": notebook_url,
                "api_key_prefix": api_key[:8] + "...",
                "session_id": body.session_id,
            },
        },
        notebook_url=notebook_url,
    )

    if session is not None:
        pair = training.record_compute(
            session.session_id,
            {
                "provider": body.provider,
                "purpose": body.purpose,
                "action": body.action,
                "payload": {
                    **body.payload,
                    "dataset": dataset,
                    "notebook_url": notebook_url,
                },
            },
            result,
            gov,
        )
        session.training_buffer.append(pair)
        session.record_action(gov.get("risk_score", 0))

    return {
        "provider": body.provider,
        "result": result,
        "notebook_url": notebook_url,
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.get("/v1/compute/job/{job_id}", tags=["Compute"])
async def compute_job_status(job_id: str, api_key: str = Depends(verify_api_key)):
    """Get remote compute job status, if an external compute API is available."""
    gov = _govern(f"compute status: {job_id}")
    _check_governance(gov, "compute-status")

    return {
        "job_id": job_id,
        "status": _call_colab_api(
            "status",
            {"job_id": job_id},
            notebook_url=DEFAULT_COLAB_NOTEBOOK,
        ),
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


@app.post("/v1/compute/job/{job_id}/cancel", tags=["Compute"])
async def compute_job_cancel(job_id: str, api_key: str = Depends(verify_api_key)):
    """Cancel a remote compute job."""
    gov = _govern(f"compute cancel: {job_id}")
    _check_governance(gov, "compute-cancel")

    return {
        "job_id": job_id,
        "status": _call_colab_api(
            "cancel",
            {"job_id": job_id},
            notebook_url=DEFAULT_COLAB_NOTEBOOK,
        ),
        "governance": {"decision": gov["decision"], "risk_score": gov["risk_score"]},
    }


# ---------------------------------------------------------------------------
#  Usage / Health
# ---------------------------------------------------------------------------

@app.get("/v1/usage", tags=["System"])
async def usage(api_key: str = Depends(verify_api_key)):
    """Get API key usage statistics and training data stats."""
    return {
        "api_key": api_key[:8] + "...",
        "tier": _API_KEY_TIERS.get(api_key, Tier.FREE).value,
        "sessions": sessions.list_sessions(api_key),
        "session_stats": sessions.stats(),
        "training_stats": training.get_stats(),
    }


@app.get("/health", tags=["System"])
async def health():
    """Health check."""
    return {
        "status": "ok",
        "service": "SCBE Browser-as-a-Service",
        "version": "1.0.0",
        "capabilities": {
            "playwright": HAS_WORKER,
            "perceiver": HAS_PERCEIVER,
            "planner": HAS_PLANNER,
            "headless": HAS_HEADLESS,
        },
        "session_stats": sessions.stats(),
        "patent": "USPTO #63/961,403 (Pending)",
    }


@app.get("/", response_class=HTMLResponse, tags=["System"])
async def landing():
    """Landing page."""
    return """<!DOCTYPE html>
<html>
<head><title>SCBE Browser-as-a-Service</title>
<style>
body{font-family:system-ui;max-width:720px;margin:40px auto;padding:0 20px;color:#e0e0e0;background:#0a0a0a}
h1{color:#00ff88}h2{color:#00ccff}a{color:#00ff88}
code{background:#1a1a1a;padding:2px 6px;border-radius:3px;font-size:0.9em}
pre{background:#1a1a1a;padding:16px;border-radius:6px;overflow-x:auto}
.badge{display:inline-block;background:#00ff88;color:#000;padding:2px 8px;border-radius:3px;font-size:0.8em;font-weight:bold}
</style></head>
<body>
<h1>SCBE Browser-as-a-Service</h1>
<p><span class="badge">v1.0.0</span> &mdash; Governed headless browser API</p>
<p>Every action secured by the <strong>14-layer SCBE governance pipeline</strong>.<br>
Every interaction generates training data for the baby AI.</p>

<h2>Quick Start</h2>
<pre>
# Create a session
curl -X POST http://localhost:8600/v1/sessions \\
  -H "X-API-Key: scbe-dev-key"

# Navigate
curl -X POST http://localhost:8600/v1/sessions/{id}/navigate \\
  -H "X-API-Key: scbe-dev-key" \\
  -H "Content-Type: application/json" \\
  -d '{"url":"https://example.com"}'

# Execute natural-language task
curl -X POST http://localhost:8600/v1/sessions/{id}/execute \\
  -H "X-API-Key: scbe-dev-key" \\
  -H "Content-Type: application/json" \\
  -d '{"goal":"click the More information link"}'

# Trigger Colab-backed finetune job (manual fallback by default if no COLAB_API_URL)
# Optional env:
#   COLAB_API_URL (automation webhook)
#   COLAB_NOTEBOOK_URL (manual notebook fallback)
curl -X POST http://localhost:8600/v1/compute/train \\
  -H "X-API-Key: scbe-dev-key" \\
  -H "Content-Type: application/json" \\
  -d '{"purpose":"train_browser_actions","provider":"colab","payload":{"dataset":"issdandavis/scbe-aethermoore-training-data"}}'
</pre>

<h2>Docs</h2>
<p><a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></p>

<p style="margin-top:40px;color:#666;font-size:0.8em">
Patent: USPTO #63/961,403 (Pending) &bull; SCBE-AETHERMOORE
</p>
</body></html>"""


# ---------------------------------------------------------------------------
#  Startup / Shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    sessions.start_cleanup_loop(interval=60)
    logger.info("BaaS gateway started — %d API keys loaded", len(_API_KEY_TIERS))


@app.on_event("shutdown")
async def shutdown():
    # Flush all training data
    for sid in list(sessions._sessions.keys()):
        try:
            session = sessions._sessions[sid]
            training.flush_session(session.training_buffer)
        except Exception:
            pass
    logger.info("BaaS gateway shutdown — training data flushed")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main():
    import uvicorn
    port = int(os.environ.get("BAAS_PORT", "8600"))
    logger.info("Starting BaaS on port %d", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
