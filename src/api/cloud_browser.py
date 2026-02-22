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
    """Cloud Browserbase backend — real headless Chromium in the cloud.

    Uses the Browserbase Python SDK + Playwright CDP connection to provide
    full browser automation without running a local browser process.

    Requires: BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID in env.
    Falls back to LocalPlaywrightBackend if the SDK or Playwright are missing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.getenv("BROWSERBASE_API_KEY", "")
        self._project_id = project_id or os.getenv("BROWSERBASE_PROJECT_ID", "")
        self._bb: Any = None          # Browserbase client
        self._pw: Any = None          # playwright async instance
        self._browsers: Dict[str, Any] = {}   # session_id -> browser
        self._pages: Dict[str, Any] = {}      # session_id -> page
        self._bb_sessions: Dict[str, str] = {}  # session_id -> bb_session_id
        self._fallback = LocalPlaywrightBackend()
        self._use_fallback = False

        # Try to initialize real SDK
        try:
            from browserbase import Browserbase
            self._bb = Browserbase(api_key=self._api_key)
        except Exception:
            self._use_fallback = True

    async def _ensure_playwright(self) -> Any:
        """Lazy-init Playwright."""
        if self._pw is not None:
            return self._pw
        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            self._pw = pw
            return pw
        except ImportError:
            self._use_fallback = True
            return None

    async def create_context(self, session_id: str) -> Dict[str, Any]:
        if self._use_fallback or not self._bb:
            result = await self._fallback.create_context(session_id)
            result["backend"] = "browserbase-fallback"
            return result

        try:
            # Create a real Browserbase session
            bb_session = self._bb.sessions.create(
                project_id=self._project_id,
            )
            bb_session_id = bb_session.id
            self._bb_sessions[session_id] = bb_session_id

            # Connect via Playwright CDP
            pw = await self._ensure_playwright()
            if pw is None:
                # Playwright not available, use fallback
                result = await self._fallback.create_context(session_id)
                result["backend"] = "browserbase-fallback"
                result["bb_session_id"] = bb_session_id
                return result

            ws_url = self._bb.sessions.debug(bb_session_id).debug_url
            browser = await pw.chromium.connect_over_cdp(ws_url)
            self._browsers[session_id] = browser

            # Get or create a page
            contexts = browser.contexts
            if contexts:
                page = contexts[0].pages[0] if contexts[0].pages else await contexts[0].new_page()
            else:
                context = await browser.new_context()
                page = await context.new_page()

            self._pages[session_id] = page

            return {
                "session_id": session_id,
                "backend": "browserbase-cloud",
                "bb_session_id": bb_session_id,
                "connected": True,
            }
        except Exception as e:
            # Fallback on any error
            result = await self._fallback.create_context(session_id)
            result["backend"] = "browserbase-fallback"
            result["error"] = str(e)
            return result

    async def close_context(self, session_id: str) -> bool:
        page = self._pages.pop(session_id, None)
        browser = self._browsers.pop(session_id, None)
        bb_sid = self._bb_sessions.pop(session_id, None)

        try:
            if page:
                await page.close()
            if browser:
                await browser.close()
            if bb_sid and self._bb:
                self._bb.sessions.update(bb_sid, status="REQUEST_RELEASE")
        except Exception:
            pass

        if not page and not browser:
            return await self._fallback.close_context(session_id)
        return True

    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        page = self._pages.get(session_id)
        if page is None:
            return await self._fallback.navigate(session_id, url)

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            title = await page.title()
            return {
                "url": page.url,
                "title": title,
                "status": response.status if response else 0,
            }
        except Exception as e:
            return {"url": url, "title": "", "status": 0, "error": str(e)}

    async def screenshot(self, session_id: str) -> str:
        page = self._pages.get(session_id)
        if page is None:
            return await self._fallback.screenshot(session_id)

        try:
            img_bytes = await page.screenshot(full_page=False, type="png")
            return base64.b64encode(img_bytes).decode()
        except Exception:
            return await self._fallback.screenshot(session_id)

    async def extract(
        self, session_id: str, selector: Optional[str] = None,
    ) -> Dict[str, Any]:
        page = self._pages.get(session_id)
        if page is None:
            return await self._fallback.extract(session_id, selector)

        try:
            title = await page.title()
            if selector:
                elements = await page.query_selector_all(selector)
                texts = []
                for el in elements[:50]:  # cap at 50 elements
                    t = await el.text_content()
                    if t:
                        texts.append(t.strip())
                return {
                    "url": page.url,
                    "title": title,
                    "selector": selector,
                    "text": "\n".join(texts),
                    "element_count": len(elements),
                }
            else:
                body = await page.text_content("body")
                return {
                    "url": page.url,
                    "title": title,
                    "selector": None,
                    "text": (body or "")[:10000],
                    "element_count": 0,
                }
        except Exception as e:
            return {
                "url": page.url if page else "",
                "title": "",
                "selector": selector,
                "text": "",
                "element_count": 0,
                "error": str(e),
            }

    async def act(
        self, session_id: str, action_type: str, target: str, value: Optional[str] = None,
    ) -> Dict[str, Any]:
        page = self._pages.get(session_id)
        if page is None:
            return await self._fallback.act(session_id, action_type, target, value)

        try:
            if action_type == "click":
                await page.click(target, timeout=5000)
            elif action_type == "type":
                await page.fill(target, value or "", timeout=5000)
            elif action_type == "select":
                await page.select_option(target, value or "", timeout=5000)
            elif action_type == "scroll":
                await page.evaluate(f"document.querySelector('{target}')?.scrollIntoView()")
            elif action_type in ("submit", "press"):
                await page.press(target, value or "Enter", timeout=5000)
            else:
                return {"action": action_type, "success": False, "error": f"Unknown action: {action_type}"}

            return {"action": action_type, "target": target, "value": value, "success": True}
        except Exception as e:
            return {"action": action_type, "target": target, "success": False, "error": str(e)}

    async def run_script(self, session_id: str, script: str) -> Any:
        page = self._pages.get(session_id)
        if page is None:
            return await self._fallback.run_script(session_id, script)

        try:
            result = await page.evaluate(script)
            return {"executed": True, "script_length": len(script), "result": result}
        except Exception as e:
            return {"executed": False, "script_length": len(script), "error": str(e)}


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
    """Return the active browser backend (lazy init).

    Auto-detects Browserbase credentials — if BROWSERBASE_API_KEY is set,
    uses the real cloud backend. Otherwise falls back to local Playwright stubs.
    """
    global _backend
    if _backend is None:
        bb_key = os.getenv("BROWSERBASE_API_KEY", "")
        if bb_key:
            _backend = BrowserbaseBackend(api_key=bb_key)
        else:
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


# ============================================================================
#  CROSS-LLM & INTEGRATIONS ENDPOINTS
# ============================================================================

from src.api.integrations import integration_hub


class AICompleteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=16384)
    task_type: str = Field("general", description="code|safety|extract|general|browser")
    provider: Optional[str] = Field(None, description="Force a specific provider key")
    model: Optional[str] = Field(None, description="Force a specific model")
    max_tokens: int = Field(512, ge=1, le=4096)
    temperature: float = Field(0.7, ge=0.0, le=2.0)


class CrossLLMRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=16384)
    task_type: str = Field("general")
    providers: Optional[List[str]] = Field(None, description="Specific providers to query")


# Integration credit costs
INTEGRATION_CREDIT_COSTS: Dict[str, float] = {
    "ai.complete": 10.0,
    "ai.cross_llm": 25.0,
    "integrations.status": 0.0,
    "integrations.health": 0.0,
}
CREDIT_COSTS.update(INTEGRATION_CREDIT_COSTS)


@router.get("/integrations")
async def integrations_status(tenant_id: str = Depends(_authenticate)):
    """Show all connected integrations and available models."""
    return _ok(integration_hub.status_summary(), 0.0)


@router.get("/integrations/health")
async def integrations_health(tenant_id: str = Depends(_authenticate)):
    """Health-check all connected services."""
    report = await integration_hub.health_check()
    return _ok(report, 0.0)


@router.post("/ai/complete")
async def ai_complete(
    req: AICompleteRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Send a prompt to the best available AI model.

    Routes automatically based on task_type, or you can force a specific
    provider/model.  Every call is antivirus-scanned and SFT-captured.
    """
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "ai.complete", req.task_type)

    # Antivirus scan the prompt
    threat = tenant.antivirus.scan(req.prompt)
    if threat.governance_decision == "DENY":
        _capture_sft(
            instruction=req.prompt[:200],
            response=f"BLOCKED by antivirus: {', '.join(threat.reasons)}",
            tenant_id=tenant_id,
            session_id="ai-complete",
            action="ai.complete",
            safety_score=threat.hamiltonian_score,
            credits_used=cost,
        )
        return _ok({
            "completed": False,
            "reason": "Prompt blocked by SemanticAntivirus",
            "threat_profile": threat.to_dict(),
        }, cost)

    result = await integration_hub.complete(
        prompt=req.prompt,
        task_type=req.task_type,
        provider=req.provider,
        model=req.model,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )

    _capture_sft(
        instruction=req.prompt[:500],
        response=(result.get("response") or result.get("error", ""))[:500],
        tenant_id=tenant_id,
        session_id="ai-complete",
        action="ai.complete",
        safety_score=threat.hamiltonian_score,
        credits_used=cost,
    )

    return _ok({
        "completed": not bool(result.get("error")),
        "provider": result.get("provider"),
        "model": result.get("model"),
        "response": result.get("response"),
        "usage": result.get("usage"),
        "latency_ms": result.get("latency_ms"),
        "error": result.get("error"),
        "safety": threat.to_dict(),
    }, cost)


@router.post("/ai/cross-llm")
async def cross_llm(
    req: CrossLLMRequest,
    tenant_id: str = Depends(_authenticate),
):
    """Send a prompt to multiple AI models simultaneously.

    This is the cross-LLM talk feature — different models discuss,
    verify, and build on each other's responses.  Flock governance
    aggregates the results.
    """
    tenant = _get_tenant(tenant_id)
    cost = _browser_charge(tenant, "ai.cross_llm", req.task_type)

    # Antivirus scan
    threat = tenant.antivirus.scan(req.prompt)
    if threat.governance_decision == "DENY":
        return _ok({
            "completed": False,
            "reason": "Prompt blocked by SemanticAntivirus",
        }, cost)

    result = await integration_hub.cross_llm_exchange(
        prompt=req.prompt,
        providers=req.providers,
        task_type=req.task_type,
    )

    _capture_sft(
        instruction=f"[cross-llm] {req.prompt[:300]}",
        response=f"{result['response_count']} responses from {result['providers_queried']} providers",
        tenant_id=tenant_id,
        session_id="cross-llm",
        action="ai.cross_llm",
        safety_score=threat.hamiltonian_score,
        credits_used=cost,
    )

    return _ok({
        "completed": True,
        "results": result["results"],
        "response_count": result["response_count"],
        "providers_queried": result["providers_queried"],
        "consensus": result["consensus"],
        "safety": threat.to_dict(),
    }, cost)
