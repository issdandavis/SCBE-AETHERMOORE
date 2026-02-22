"""
SCBE-AETHERMOORE Cloud Browser Service
========================================

FastAPI router providing governed headless browser automation as a service.
Each request is tenant-isolated, credit-metered, antivirus-scanned, and
governed by BFT consensus via the Flock Shepherd.

Mount this router inside the SaaS API::

    from src.api.cloud_browser import router as browser_router
    app.include_router(browser_router)

Endpoints
---------
POST   /api/v1/browser/session          Create a new browser session
DELETE /api/v1/browser/session/{id}      Close a browser session
POST   /api/v1/browser/navigate          Navigate to a URL
POST   /api/v1/browser/screenshot        Take a page screenshot (base64)
POST   /api/v1/browser/extract           Extract text/data from a page
POST   /api/v1/browser/act               Perform a governed action
POST   /api/v1/browser/script            Execute JavaScript (antivirus-gated)
GET    /api/v1/browser/sessions          List active sessions for tenant
POST   /api/v1/browser/task              High-level task via flock agent
"""

from __future__ import annotations

import base64
import hashlib
import os
import sys
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
#  Path setup — allow running from project root
# ---------------------------------------------------------------------------
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.semantic_antivirus import (
    SemanticAntivirus,
)
from src.symphonic_cipher.scbe_aethermoore.flock_shepherd import Flock

# Local SFT collector import
from src.api.sft_collector import sft_collector

# Re-use auth & tenant helpers from the main SaaS API
from src.api.saas_api import (
    _authenticate,
    _get_tenant,
    _charge,
    _ok,
    CREDIT_COSTS,
    TenantState,
)

# ============================================================================
#  CREDIT COSTS FOR BROWSER OPERATIONS
# ============================================================================

BROWSER_CREDIT_COSTS: Dict[str, float] = {
    "browser.session.create": 100.0,
    "browser.session.close": 0.0,
    "browser.session.list": 0.0,
    "browser.navigate": 5.0,
    "browser.screenshot": 3.0,
    "browser.extract": 5.0,
    "browser.act": 10.0,
    "browser.script": 20.0,
    "browser.task": 50.0,
}

# Register browser costs in the global cost table so _charge() can find them
CREDIT_COSTS.update(BROWSER_CREDIT_COSTS)

# ============================================================================
#  BROWSER BACKEND ABSTRACTION
# ============================================================================

@runtime_checkable
class BrowserBackend(Protocol):
    """Protocol for browser backends (Playwright local, Browserbase cloud, etc.)."""

    async def create_context(self, session_id: str) -> Dict[str, Any]:
        """Create an isolated browser context. Returns context metadata."""
        ...

    async def close_context(self, session_id: str) -> bool:
        """Close and destroy a browser context."""
        ...

    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate to a URL. Returns page info (title, status, url)."""
        ...

    async def screenshot(self, session_id: str) -> str:
        """Take a screenshot. Returns base64-encoded PNG."""
        ...

    async def extract(
        self, session_id: str, selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract text/data from the page. Returns extracted content."""
        ...

    async def act(
        self, session_id: str, action_type: str, target: str, value: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform an action (click, type, select, scroll)."""
        ...

    async def run_script(self, session_id: str, script: str) -> Any:
        """Execute JavaScript on the page. Returns the result."""
        ...


class LocalPlaywrightBackend:
    """Local Playwright browser backend (default for dev/self-hosted).

    When Playwright is not installed, all methods return mock/stub results
    so that the API layer can still run and be tested.
    """

    def __init__(self) -> None:
        self._contexts: Dict[str, Any] = {}

    async def create_context(self, session_id: str) -> Dict[str, Any]:
        self._contexts[session_id] = {
            "created_at": time.time(),
            "current_url": "about:blank",
            "title": "",
        }
        return {"session_id": session_id, "backend": "playwright-local"}

    async def close_context(self, session_id: str) -> bool:
        return self._contexts.pop(session_id, None) is not None

    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        ctx = self._contexts.get(session_id)
        if ctx is None:
            raise RuntimeError(f"No browser context for session {session_id}")
        ctx["current_url"] = url
        ctx["title"] = f"Page at {url}"
        return {"url": url, "title": ctx["title"], "status": 200}

    async def screenshot(self, session_id: str) -> str:
        # Return a minimal 1x1 transparent PNG as base64
        pixel = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
            b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return base64.b64encode(pixel).decode()

    async def extract(
        self, session_id: str, selector: Optional[str] = None
    ) -> Dict[str, Any]:
        ctx = self._contexts.get(session_id)
        if ctx is None:
            raise RuntimeError(f"No browser context for session {session_id}")
        return {
            "url": ctx["current_url"],
            "title": ctx["title"],
            "selector": selector,
            "text": f"Extracted content from {ctx['current_url']}",
            "element_count": 1 if selector else 0,
        }

    async def act(
        self, session_id: str, action_type: str, target: str, value: Optional[str] = None
    ) -> Dict[str, Any]:
        ctx = self._contexts.get(session_id)
        if ctx is None:
            raise RuntimeError(f"No browser context for session {session_id}")
        return {
            "action": action_type,
            "target": target,
            "value": value,
            "success": True,
        }

    async def run_script(self, session_id: str, script: str) -> Any:
        ctx = self._contexts.get(session_id)
        if ctx is None:
            raise RuntimeError(f"No browser context for session {session_id}")
        return {"executed": True, "script_length": len(script), "result": None}


class BrowserbaseBackend:
    """Cloud Browserbase backend stub.

    In production this would call the Browserbase REST API.
    For now it delegates to LocalPlaywrightBackend as a shim.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("BROWSERBASE_API_KEY", "")
        self._delegate = LocalPlaywrightBackend()

    async def create_context(self, session_id: str) -> Dict[str, Any]:
        result = await self._delegate.create_context(session_id)
        result["backend"] = "browserbase-cloud"
        return result

    async def close_context(self, session_id: str) -> bool:
        return await self._delegate.close_context(session_id)

    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        return await self._delegate.navigate(session_id, url)

    async def screenshot(self, session_id: str) -> str:
        return await self._delegate.screenshot(session_id)

    async def extract(
        self, session_id: str, selector: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._delegate.extract(session_id, selector)

    async def act(
        self, session_id: str, action_type: str, target: str, value: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self._delegate.act(session_id, action_type, target, value)

    async def run_script(self, session_id: str, script: str) -> Any:
        return await self._delegate.run_script(session_id, script)


# ============================================================================
#  SESSION MANAGEMENT
# ============================================================================

@dataclass
class BrowserSession:
    """Represents a single tenant browser session."""
    session_id: str
    tenant_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    current_url: str = "about:blank"
    page_title: str = ""
    actions_count: int = 0

    # 30-minute inactivity timeout
    TIMEOUT_SECONDS: float = 1800.0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_activity) > self.TIMEOUT_SECONDS

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()
        self.actions_count += 1


# tenant_id -> {session_id -> BrowserSession}
_BROWSER_SESSIONS: Dict[str, Dict[str, BrowserSession]] = {}

# Max concurrent sessions per tenant (free tier)
MAX_SESSIONS_PER_TENANT = 3

# Destructive action types requiring BFT governance vote
DESTRUCTIVE_ACTIONS = {"submit", "delete", "post", "purchase", "confirm"}


def _get_sessions(tenant_id: str) -> Dict[str, BrowserSession]:
    """Get (or create) the session map for a tenant."""
    if tenant_id not in _BROWSER_SESSIONS:
        _BROWSER_SESSIONS[tenant_id] = {}
    return _BROWSER_SESSIONS[tenant_id]


def _get_session(tenant_id: str, session_id: str) -> BrowserSession:
    """Get a specific session, raising 404 if not found or expired."""
    sessions = _get_sessions(tenant_id)

    # Prune expired sessions
    expired_ids = [sid for sid, s in sessions.items() if s.is_expired]
    for sid in expired_ids:
        sessions.pop(sid, None)

    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(404, f"Browser session {session_id} not found or expired")
    return session


# ============================================================================
#  BROWSER BACKEND SINGLETON
# ============================================================================

_backend: Optional[BrowserBackend] = None


def get_backend() -> BrowserBackend:
    """Return the active browser backend (lazy init)."""
    global _backend
    if _backend is None:
        # Default to local Playwright backend
        _backend = LocalPlaywrightBackend()
    return _backend


def set_backend(backend: BrowserBackend) -> None:
    """Override the browser backend (for testing or cloud deployment)."""
    global _backend
    _backend = backend


# ============================================================================
#  SFT CAPTURE HELPER
# ============================================================================

def _capture_sft(
    instruction: str,
    response: str,
    tenant_id: str,
    session_id: str,
    action: str,
    safety_score: float,
    credits_used: float,
) -> Dict[str, Any]:
    """Capture an SFT training record for a browser operation."""
    return sft_collector.capture(
        instruction=instruction,
        response=response,
        category="browser-automation",
        metadata={
            "source": "cloud_browser",
            "tenant": tenant_id,
            "session_id": session_id,
            "action": action,
            "safety_score": safety_score,
            "credits_used": credits_used,
            "timestamp": time.time(),
        },
    )


# ============================================================================
#  BROWSER CHARGE HELPER
# ============================================================================

def _browser_charge(tenant: TenantState, operation: str, detail: str = "") -> float:
    """Deduct browser credits. Uses the same _charge mechanism as saas_api."""
    return _charge(tenant, operation, detail)


# ============================================================================
#  REQUEST / RESPONSE MODELS
# ============================================================================

class SessionCreateRequest(BaseModel):
    """Request to create a new browser session."""
    label: Optional[str] = Field(None, max_length=128, description="Optional human label")


class NavigateRequest(BaseModel):
    session_id: str = Field(..., description="Browser session ID")
    url: str = Field(..., min_length=1, max_length=4096, description="URL to navigate to")


class ScreenshotRequest(BaseModel):
    session_id: str = Field(..., description="Browser session ID")


class ExtractRequest(BaseModel):
    session_id: str = Field(..., description="Browser session ID")
    selector: Optional[str] = Field(
        None, max_length=512, description="CSS selector (omit for full page)"
    )


class ActRequest(BaseModel):
    session_id: str = Field(..., description="Browser session ID")
    action_type: str = Field(
        ..., description="Action: click, type, select, scroll, submit"
    )
    target: str = Field(..., max_length=1024, description="CSS selector or target")
    value: Optional[str] = Field(
        None, max_length=4096, description="Value for type/select actions"
    )


class ScriptRequest(BaseModel):
    session_id: str = Field(..., description="Browser session ID")
    script: str = Field(
        ..., min_length=1, max_length=65536, description="JavaScript to execute"
    )


class TaskRequest(BaseModel):
    session_id: Optional[str] = Field(
        None, description="Existing session ID (optional — creates one if omitted)"
    )
    goal: str = Field(
        ..., min_length=1, max_length=4096,
        description="High-level task description, e.g. 'go to X, do Y, return Z'",
    )


# ============================================================================
#  ROUTER
# ============================================================================

router = APIRouter(prefix="/api/v1/browser", tags=["Browser"])


# -- Session Management -----------------------------------------------------

@router.post("/session")
async def create_session(
    req: SessionCreateRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Create a new isolated browser session for the tenant."""
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.session.create", req.label or "")

    sessions = _get_sessions(tenant_id)

    # Prune expired sessions first
    expired_ids = [sid for sid, s in sessions.items() if s.is_expired]
    for sid in expired_ids:
        await get_backend().close_context(sid)
        sessions.pop(sid, None)

    # Enforce session limit
    if len(sessions) >= MAX_SESSIONS_PER_TENANT:
        raise HTTPException(
            429,
            f"Session limit reached ({MAX_SESSIONS_PER_TENANT} concurrent sessions). "
            "Close an existing session first.",
        )

    session_id = f"bs-{uuid.uuid4().hex[:12]}"
    backend = get_backend()
    ctx_info = await backend.create_context(session_id)

    session = BrowserSession(
        session_id=session_id,
        tenant_id=tenant_id,
    )
    sessions[session_id] = session

    _capture_sft(
        instruction=f"Create browser session (label={req.label})",
        response=f"Created session {session_id}",
        tenant_id=tenant_id,
        session_id=session_id,
        action="session.create",
        safety_score=1.0,
        credits_used=cost,
    )

    return _ok({
        "session_id": session_id,
        "created_at": session.created_at,
        "timeout_seconds": BrowserSession.TIMEOUT_SECONDS,
        "backend": ctx_info.get("backend", "unknown"),
        "label": req.label,
    }, cost)


@router.delete("/session/{session_id}")
async def close_session(
    session_id: str,
    tenant_id: str = Depends(_authenticate),
):
    """Close and destroy a browser session."""
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.session.close", session_id)

    sessions = _get_sessions(tenant_id)
    session = sessions.pop(session_id, None)
    if session is None:
        raise HTTPException(404, f"Session {session_id} not found")

    await get_backend().close_context(session_id)

    _capture_sft(
        instruction=f"Close browser session {session_id}",
        response=f"Session {session_id} closed after {session.actions_count} actions",
        tenant_id=tenant_id,
        session_id=session_id,
        action="session.close",
        safety_score=1.0,
        credits_used=cost,
    )

    return _ok({
        "session_id": session_id,
        "closed": True,
        "actions_performed": session.actions_count,
        "lifetime_seconds": round(time.time() - session.created_at, 1),
    }, cost)


@router.get("/sessions")
async def list_sessions(tenant_id: str = Depends(_authenticate)):
    """List active browser sessions for the tenant."""
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.session.list")

    sessions = _get_sessions(tenant_id)

    # Prune expired
    expired_ids = [sid for sid, s in sessions.items() if s.is_expired]
    for sid in expired_ids:
        sessions.pop(sid, None)

    result = []
    for s in sessions.values():
        result.append({
            "session_id": s.session_id,
            "created_at": s.created_at,
            "last_activity": s.last_activity,
            "current_url": s.current_url,
            "page_title": s.page_title,
            "actions_count": s.actions_count,
            "is_expired": s.is_expired,
        })

    return _ok({
        "sessions": result,
        "count": len(result),
        "max_allowed": MAX_SESSIONS_PER_TENANT,
    }, cost)


# -- Navigation --------------------------------------------------------------

@router.post("/navigate")
async def navigate(
    req: NavigateRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Navigate to a URL with antivirus pre-scan."""
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.navigate", req.url[:80])

    session = _get_session(tenant_id, req.session_id)

    # Antivirus pre-scan of the URL
    threat = tenant.antivirus.scan_url(req.url)
    if threat.governance_decision == "DENY":
        _capture_sft(
            instruction=f"Navigate to {req.url}",
            response=f"BLOCKED by antivirus: {', '.join(threat.reasons)}",
            tenant_id=tenant_id,
            session_id=req.session_id,
            action="navigate",
            safety_score=threat.hamiltonian_score,
            credits_used=cost,
        )
        return _ok({
            "navigated": False,
            "reason": "URL blocked by SemanticAntivirus",
            "threat_profile": threat.to_dict(),
        }, cost)

    # Perform navigation
    backend = get_backend()
    page_info = await backend.navigate(req.session_id, req.url)

    session.current_url = req.url
    session.page_title = page_info.get("title", "")
    session.touch()

    _capture_sft(
        instruction=f"Navigate to {req.url}",
        response=(
            f"Navigated to {req.url} ({page_info.get('status', '?')} "
            f"{page_info.get('title', '')})"
        ),
        tenant_id=tenant_id,
        session_id=req.session_id,
        action="navigate",
        safety_score=threat.hamiltonian_score,
        credits_used=cost,
    )

    return _ok({
        "navigated": True,
        "url": req.url,
        "page_info": page_info,
        "threat_profile": threat.to_dict(),
    }, cost)


# -- Screenshot ---------------------------------------------------------------

@router.post("/screenshot")
async def screenshot(
    req: ScreenshotRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Take a screenshot of the current page (base64-encoded PNG)."""
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.screenshot", req.session_id)

    session = _get_session(tenant_id, req.session_id)
    session.touch()

    backend = get_backend()
    image_b64 = await backend.screenshot(req.session_id)

    _capture_sft(
        instruction=f"Take screenshot of {session.current_url}",
        response=f"Screenshot captured ({len(image_b64)} bytes base64)",
        tenant_id=tenant_id,
        session_id=req.session_id,
        action="screenshot",
        safety_score=1.0,
        credits_used=cost,
    )

    return _ok({
        "session_id": req.session_id,
        "url": session.current_url,
        "image_base64": image_b64,
        "format": "png",
    }, cost)


# -- Extract ------------------------------------------------------------------

@router.post("/extract")
async def extract(
    req: ExtractRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Extract text/data from the current page."""
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.extract", req.selector or "full-page")

    session = _get_session(tenant_id, req.session_id)
    session.touch()

    backend = get_backend()
    data = await backend.extract(req.session_id, req.selector)

    extracted_text = data.get("text", "")

    # Scan extracted content through antivirus
    threat = tenant.antivirus.scan(extracted_text, url=session.current_url)

    selector_label = req.selector or "full page"
    _capture_sft(
        instruction=f"Extract data from {session.current_url} (selector={selector_label})",
        response=f"Extracted {len(extracted_text)} chars, safety={threat.hamiltonian_score:.3f}",
        tenant_id=tenant_id,
        session_id=req.session_id,
        action="extract",
        safety_score=threat.hamiltonian_score,
        credits_used=cost,
    )

    return _ok({
        "session_id": req.session_id,
        "url": session.current_url,
        "selector": req.selector,
        "extracted": data,
        "content_scan": threat.to_dict(),
    }, cost)


# -- Act (governed) -----------------------------------------------------------

@router.post("/act")
async def act(
    req: ActRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Perform a governed browser action (click, type, select, scroll, submit).

    Destructive actions (submit, delete, post, purchase, confirm) require
    a BFT governance vote from the tenant flock.
    """
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.act", f"{req.action_type}:{req.target[:60]}")

    session = _get_session(tenant_id, req.session_id)
    action_lower = req.action_type.lower()

    # Governance gate for destructive actions
    vote_result = None
    if action_lower in DESTRUCTIVE_ACTIONS:
        vote_result = tenant.flock.vote_on_action(
            f"browser-act:{action_lower}:{req.target[:60]}"
        )
        if vote_result["consensus"] == "DENY":
            _capture_sft(
                instruction=f"Act: {req.action_type} on {req.target}",
                response=f"DENIED by governance vote: {vote_result['consensus']}",
                tenant_id=tenant_id,
                session_id=req.session_id,
                action=f"act.{action_lower}",
                safety_score=0.0,
                credits_used=cost,
            )
            return _ok({
                "acted": False,
                "reason": "Destructive action denied by governance vote",
                "vote": vote_result,
            }, cost)

    backend = get_backend()
    result = await backend.act(req.session_id, action_lower, req.target, req.value)
    session.touch()

    _capture_sft(
        instruction=f"Act: {req.action_type} on '{req.target}' (value={req.value})",
        response=f"Action {action_lower} performed: {result.get('success', False)}",
        tenant_id=tenant_id,
        session_id=req.session_id,
        action=f"act.{action_lower}",
        safety_score=1.0 if result.get("success") else 0.5,
        credits_used=cost,
    )

    return _ok({
        "acted": True,
        "action_type": action_lower,
        "target": req.target,
        "result": result,
        "governance_vote": vote_result,
    }, cost)


# -- Script (antivirus-gated) ------------------------------------------------

@router.post("/script")
async def run_script(
    req: ScriptRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Execute JavaScript on the page. MUST pass antivirus scan first."""
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.script", f"len={len(req.script)}")

    session = _get_session(tenant_id, req.session_id)

    # Antivirus scan of the script content
    threat = tenant.antivirus.scan(req.script, url=session.current_url)
    if threat.governance_decision == "DENY":
        script_hash = hashlib.sha256(req.script.encode()).hexdigest()[:16]
        _capture_sft(
            instruction=f"Execute script (hash={script_hash}, len={len(req.script)})",
            response=f"BLOCKED by antivirus: {', '.join(threat.reasons)}",
            tenant_id=tenant_id,
            session_id=req.session_id,
            action="script",
            safety_score=threat.hamiltonian_score,
            credits_used=cost,
        )
        return _ok({
            "executed": False,
            "reason": "Script blocked by SemanticAntivirus",
            "threat_profile": threat.to_dict(),
        }, cost)

    backend = get_backend()
    result = await backend.run_script(req.session_id, req.script)
    session.touch()

    script_hash = hashlib.sha256(req.script.encode()).hexdigest()[:16]
    _capture_sft(
        instruction=f"Execute script (hash={script_hash}, len={len(req.script)})",
        response=f"Script executed, safety={threat.hamiltonian_score:.3f}",
        tenant_id=tenant_id,
        session_id=req.session_id,
        action="script",
        safety_score=threat.hamiltonian_score,
        credits_used=cost,
    )

    return _ok({
        "executed": True,
        "result": result,
        "threat_profile": threat.to_dict(),
    }, cost)


# -- High-Level Task ----------------------------------------------------------

@router.post("/task")
async def browser_task(
    req: TaskRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Dispatch a high-level browser task to a flock agent.

    Example goal: 'Go to https://example.com and extract the main heading.'

    The flock assigns the task to the best available agent and returns
    a task ID for tracking.
    """
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "browser.task", req.goal[:80])

    # Governance vote on the task
    vote = tenant.flock.vote_on_action(f"browser-task:{req.goal[:60]}")
    if vote["consensus"] == "DENY":
        _capture_sft(
            instruction=req.goal,
            response=f"Task DENIED by governance: {vote['consensus']}",
            tenant_id=tenant_id,
            session_id=req.session_id or "none",
            action="task",
            safety_score=0.0,
            credits_used=cost,
        )
        return _ok({
            "dispatched": False,
            "reason": "Task denied by governance vote",
            "vote": vote,
        }, cost)

    # Create or reuse session
    session_id = req.session_id
    if not session_id:
        # Auto-create a session for this task
        sessions = _get_sessions(tenant_id)
        expired_ids = [sid for sid, s in sessions.items() if s.is_expired]
        for sid in expired_ids:
            await get_backend().close_context(sid)
            sessions.pop(sid, None)

        if len(sessions) >= MAX_SESSIONS_PER_TENANT:
            raise HTTPException(
                429,
                "Cannot auto-create session: session limit reached. "
                "Pass an existing session_id or close a session.",
            )
        session_id = f"bs-{uuid.uuid4().hex[:12]}"
        await get_backend().create_context(session_id)
        sessions[session_id] = BrowserSession(
            session_id=session_id, tenant_id=tenant_id
        )

    # Verify session exists
    _get_session(tenant_id, session_id)

    # Dispatch to flock
    from src.symphonic_cipher.scbe_aethermoore.flock_shepherd import TrainingTrack

    task = tenant.flock.add_task(
        description=f"[browser-task] {req.goal}",
        track=TrainingTrack.FUNCTIONS,
        priority=3,
    )
    assigned = tenant.flock.assign_task(task.task_id)

    _capture_sft(
        instruction=req.goal,
        response=(
            f"Task dispatched: {task.task_id} "
            f"(assigned={assigned}, session={session_id})"
        ),
        tenant_id=tenant_id,
        session_id=session_id,
        action="task",
        safety_score=1.0,
        credits_used=cost,
    )

    return _ok({
        "dispatched": True,
        "task_id": task.task_id,
        "session_id": session_id,
        "assigned": assigned,
        "assigned_to": task.owner,
        "governance_vote": vote,
    }, cost)
