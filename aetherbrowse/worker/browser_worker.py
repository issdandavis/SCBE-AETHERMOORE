"""
AetherBrowse — Playwright Browser Worker
==========================================
Drives a real Chromium instance via Playwright.
The Python agent runtime sends commands over an internal queue;
this worker executes them and returns results.

Start: python aetherbrowse/worker/browser_worker.py
"""

import asyncio
import json
import logging
import re
import sys
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from aetherbrowse.runtime.env_bootstrap import bootstrap_runtime_env

bootstrap_runtime_env()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("aetherbrowse-worker")

try:
    from playwright.async_api import async_playwright, Browser, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    from huggingface_hub import HfApi
    HAS_HF_HUB = True
except ImportError:
    HAS_HF_HUB = False

from src.fleet.connector_bridge import ConnectorBridge
from src.security.secret_store import get_secret

# Try importing SCBE governance for per-action checks
try:
    from symphonic_cipher.scbe_aethermoore.axiom_grouped.causality_axiom import (
        temporal_distance as scbe_temporal_distance,
    )
    HAS_SCBE = True
except ImportError:
    HAS_SCBE = False


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name, "").strip().lower()
    if not val:
        return default
    return val in {"1", "true", "yes", "on", "y"}


def _env_str(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip()


def _mobile_context():
    """Return a mobile-friendly Playwright context when configured."""
    if not _env_bool("AETHERSCREEN_MOBILE", False):
        return None

    return {
        "viewport": {"width": 390, "height": 844},
        "user_agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "CriOS/120.0.0.0 Mobile/15E148 Safari/604.1"
        ),
        "is_mobile": True,
        "has_touch": True,
        "device_scale_factor": 3,
    }


def _normalize_profile(profile: str) -> str:
    raw = (profile or "").strip().lower()
    if raw in {"open", "soft", "hard", "dark"}:
        return raw
    return "open"


def _normalize_profile_id(profile_id: str) -> str:
    raw = (profile_id or "").strip().lower()
    if not raw:
        return "default"
    clean = re.sub(r"[^a-z0-9_-]+", "-", raw).strip("-")
    return clean or "default"


def _proxy_for_profile(profile: str) -> Optional[dict]:
    """Resolve per-profile proxy settings.

    dark profile:
      - Uses AETHERBROWSE_TOR_PROXY or AETHERBROWSE_PROXY_SERVER.
      - Defaults to socks5://127.0.0.1:9050 (local Tor daemon).
    non-dark profiles:
      - Direct by default.
      - Can be forced to use custom proxy with AETHERBROWSE_FORCE_PROXY=1.
    """
    profile = _normalize_profile(profile)
    force_proxy = _env_bool("AETHERBROWSE_FORCE_PROXY", False)
    proxy_server = _env_str("AETHERBROWSE_PROXY_SERVER", "")
    tor_proxy = _env_str("AETHERBROWSE_TOR_PROXY", "") or proxy_server or "socks5://127.0.0.1:9050"

    server = ""
    if profile == "dark":
        server = tor_proxy
    elif force_proxy:
        server = proxy_server

    if not server:
        return None

    proxy: dict[str, str] = {"server": server}
    username = _env_str("AETHERBROWSE_PROXY_USERNAME", "")
    password = _env_str("AETHERBROWSE_PROXY_PASSWORD", "")
    bypass = _env_str("AETHERBROWSE_PROXY_BYPASS", "")
    if username:
        proxy["username"] = username
    if password:
        proxy["password"] = password
    if bypass:
        proxy["bypass"] = bypass
    return proxy


def _mask_proxy(proxy: Optional[dict]) -> str:
    if not proxy:
        return "direct"
    server = proxy.get("server", "")
    if not server:
        return "direct"
    try:
        parsed = urlparse(server)
        host = parsed.hostname or ""
        port = parsed.port or ""
        scheme = parsed.scheme or "proxy"
        if host:
            return f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
    except Exception:
        pass
    return "proxy-configured"


class BrowserWorker:
    """Drives a headed Chromium browser via Playwright."""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.network_profile = _normalize_profile(_env_str("AETHERBROWSE_NETWORK_PROFILE", "open"))
        self.profile_id = _normalize_profile_id(_env_str("AETHERBROWSE_PROFILE_ID", "default"))
        self._screenshots_dir = ROOT / "aetherbrowse" / "artifacts" / "screenshots"
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._profiles_root = ROOT / "aetherbrowse" / "profiles"
        self._profiles_root.mkdir(parents=True, exist_ok=True)
        self._credentials_root = ROOT / "external" / "credentials" / "browser_profiles"
        self._connector_bridge = ConnectorBridge()

    def _storage_state_path(self, profile_id: Optional[str] = None) -> Path:
        pid = _normalize_profile_id(profile_id or self.profile_id)
        profile_dir = self._profiles_root / pid
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir / "storage_state.json"

    async def _persist_storage_state(self) -> None:
        if self.context is None:
            return
        path = self._storage_state_path(self.profile_id)
        await self.context.storage_state(path=str(path))

    def _context_kwargs(self, profile: str, profile_id: Optional[str] = None) -> dict:
        mobile_ctx = _mobile_context()
        context_kwargs = dict(mobile_ctx or {})
        if not mobile_ctx:
            context_kwargs.update(
                {
                    "viewport": {"width": 1280, "height": 800},
                    "user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                }
            )

        proxy = _proxy_for_profile(profile)
        if proxy:
            context_kwargs["proxy"] = proxy

        state_path = self._storage_state_path(profile_id)
        if state_path.exists():
            context_kwargs["storage_state"] = str(state_path)
        return context_kwargs

    async def _recreate_context(self, profile: str, profile_id: Optional[str] = None) -> dict:
        pid = _normalize_profile_id(profile_id or self.profile_id)
        if self.browser is None:
            return {"ok": False, "error": "browser_not_initialized", "requested_profile": profile, "profile_id": pid}

        if self.page is not None:
            await self.page.close()
            self.page = None
        if self.context is not None:
            await self._persist_storage_state()
            await self.context.close()
            self.context = None

        kwargs = self._context_kwargs(profile, profile_id=pid)
        self.context = await self.browser.new_context(**kwargs)
        self.page = await self.context.new_page()
        self.network_profile = _normalize_profile(profile)
        self.profile_id = pid
        return {
            "ok": True,
            "network_profile": self.network_profile,
            "profile_id": self.profile_id,
            "storage_state_path": str(self._storage_state_path(self.profile_id)),
            "proxy": _mask_proxy(kwargs.get("proxy")),
        }

    async def set_network_profile(self, profile: str) -> dict:
        """Switch browsing profile (open/soft/hard/dark) at runtime."""
        requested = _normalize_profile(profile)
        if self.browser is None:
            return {"ok": False, "error": "browser_not_initialized", "requested_profile": requested}
        if requested == self.network_profile and self.page is not None:
            return {
                "ok": True,
                "network_profile": self.network_profile,
                "changed": False,
                "profile_id": self.profile_id,
                "proxy": _mask_proxy(_proxy_for_profile(self.network_profile)),
            }
        result = await self._recreate_context(requested, self.profile_id)
        if not result.get("ok"):
            return result

        logger.info(
            "Network profile switched | profile=%s | browser_profile=%s | proxy=%s",
            self.network_profile,
            self.profile_id,
            result.get("proxy", "direct"),
        )
        result["changed"] = True
        return result

    async def switch_profile(self, profile_id: str) -> dict:
        """Switch persistent browser storage profile."""
        requested = _normalize_profile_id(profile_id)
        if requested == self.profile_id and self.page is not None:
            return {
                "ok": True,
                "changed": False,
                "profile_id": self.profile_id,
                "network_profile": self.network_profile,
                "storage_state_path": str(self._storage_state_path(self.profile_id)),
            }
        result = await self._recreate_context(self.network_profile, requested)
        if result.get("ok"):
            result["changed"] = True
            logger.info("Browser profile switched | browser_profile=%s", self.profile_id)
        return result

    async def list_profiles(self) -> dict:
        """List known browser profiles with storage-state presence."""
        rows = []
        for child in sorted(self._profiles_root.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            state = child / "storage_state.json"
            rows.append(
                {
                    "profile_id": child.name,
                    "storage_state_exists": state.exists(),
                    "storage_state_path": str(state),
                }
            )
        if not any(r["profile_id"] == self.profile_id for r in rows):
            current_state = self._storage_state_path(self.profile_id)
            rows.append(
                {
                    "profile_id": self.profile_id,
                    "storage_state_exists": current_state.exists(),
                    "storage_state_path": str(current_state),
                }
            )
        return {"ok": True, "active_profile_id": self.profile_id, "profiles": rows}

    def _credentials_index_path(self, profile_id: Optional[str] = None) -> Path:
        pid = _normalize_profile_id(profile_id or self.profile_id)
        return self._credentials_root / pid / "credentials_index.json"

    async def autofill_login(self, domain: str = "", submit: bool = False, profile_id: str = "") -> dict:
        """Autofill username/password from secret-backed profile credential index."""
        pid = _normalize_profile_id(profile_id or self.profile_id)
        index_path = self._credentials_index_path(pid)
        if not index_path.exists():
            return {"ok": False, "error": f"credentials_index_missing: {index_path}", "profile_id": pid}

        payload = json.loads(index_path.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            return {"ok": False, "error": "invalid_credentials_index", "profile_id": pid}

        active_domain = domain.strip().lower()
        if not active_domain:
            try:
                parsed = urlparse(self.page.url)
                active_domain = (parsed.hostname or "").lower()
            except Exception:
                active_domain = ""

        match = None
        for entry in entries:
            row_domain = str(entry.get("domain", "")).strip().lower()
            if not row_domain:
                continue
            if active_domain == row_domain or active_domain.endswith("." + row_domain) or row_domain in active_domain:
                match = entry
                break
        if not match:
            return {"ok": False, "error": f"no_credentials_for_domain:{active_domain}", "profile_id": pid}

        user_secret = str(match.get("username_secret", "")).strip()
        pass_secret = str(match.get("password_secret", "")).strip()
        username = get_secret(user_secret, "")
        password = get_secret(pass_secret, "")
        if not (username and password):
            return {"ok": False, "error": "credential_secret_missing", "profile_id": pid}

        username_selectors = [
            "input[type='email']",
            "input[name='username']",
            "input[name='email']",
            "input[autocomplete='username']",
            "input[autocomplete='email']",
            "input[type='text']",
        ]
        password_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input[autocomplete='current-password']",
            "input[autocomplete='new-password']",
        ]

        async def _first_visible(selectors: list[str]):
            for sel in selectors:
                loc = self.page.locator(sel)
                if await loc.count() > 0:
                    try:
                        if await loc.first.is_visible():
                            return sel
                    except Exception:
                        continue
            return ""

        user_sel = await _first_visible(username_selectors)
        pass_sel = await _first_visible(password_selectors)
        if not (user_sel and pass_sel):
            return {"ok": False, "error": "login_fields_not_found", "profile_id": pid}

        await self.page.fill(user_sel, username)
        await self.page.fill(pass_sel, password)

        submitted = False
        if submit:
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Sign in')",
                "button:has-text('Log in')",
                "button:has-text('Continue')",
            ]
            sub_sel = await _first_visible(submit_selectors)
            if sub_sel:
                await self.page.click(sub_sel)
                submitted = True

        return {
            "ok": True,
            "action": "autofill_login",
            "profile_id": pid,
            "domain": active_domain,
            "filled": True,
            "submitted": submitted,
            "username_hint": str(match.get("username_hint", "")),
        }

    async def launch(self, headless: Optional[bool] = None):
        """Start Playwright and launch Chromium."""
        if headless is None:
            headless = _env_bool("AETHERSCREEN_HEADLESS", True)

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        result = await self._recreate_context(self.network_profile, self.profile_id)
        logger.info(
            "Playwright Chromium launched | headless=%s | mobile=%s | net_profile=%s | browser_profile=%s | proxy=%s",
            headless,
            bool(_mobile_context()),
            self.network_profile,
            self.profile_id,
            result.get("proxy", "direct"),
        )

    async def close(self):
        """Shutdown browser and Playwright."""
        if self.context:
            await self._persist_storage_state()
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright shut down")

    # ------------------------------------------------------------------
    #  Core actions — called by the agent runtime
    # ------------------------------------------------------------------

    async def navigate(self, url: str, network_profile: str = "") -> dict:
        """Navigate to URL. Returns page title + URL."""
        requested_profile = _normalize_profile(network_profile) if network_profile else self.network_profile
        if requested_profile != self.network_profile:
            await self.set_network_profile(requested_profile)
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await self.page.title()
        return {"url": self.page.url, "title": title, "network_profile": self.network_profile}

    async def snapshot(self) -> dict:
        """Get accessibility tree (text representation) of current page."""
        # Use Playwright's accessibility snapshot
        snapshot = await self.page.accessibility.snapshot()
        return {"url": self.page.url, "tree": snapshot}

    async def screenshot(self, name: str = "page") -> str:
        """Take a screenshot, return file path."""
        path = self._screenshots_dir / f"{name}.png"
        await self.page.screenshot(path=str(path), full_page=False)
        logger.info(f"Screenshot saved: {path}")
        return str(path)

    async def click(self, selector: str) -> dict:
        """Click an element by CSS selector."""
        await self.page.click(selector, timeout=10000)
        return {"action": "click", "selector": selector, "url": self.page.url}

    async def fill(self, selector: str, value: str) -> dict:
        """Fill a form field."""
        await self.page.fill(selector, value)
        return {"action": "fill", "selector": selector}

    async def upload_file(self, selector: str, file_path: str) -> dict:
        """Upload a file to a file input element."""
        await self.page.set_input_files(selector, file_path)
        return {"action": "upload", "selector": selector, "file": file_path}

    async def evaluate(self, script: str) -> dict:
        """Execute JavaScript in the page context."""
        result = await self.page.evaluate(script)
        return {"result": result}

    async def huggingface_upload(
        self,
        file_path: str,
        repo_id: str,
        repo_type: str = "model",
        path_in_repo: str = "",
        commit_message: str = "",
    ) -> dict:
        """Upload a file directly to Hugging Face Hub via API."""
        if not HAS_HF_HUB:
            return {"error": "huggingface_hub is not installed. Run: pip install huggingface_hub"}

        token = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            or os.environ.get("HUGGINGFACE_TOKEN")
            or os.environ.get("HUGGINGFACE_API_KEY")
            or os.environ.get("HF_API_KEY")
        )
        if not token:
            return {
                "error": "No HF token found. Set HF_TOKEN, HUGGING_FACE_HUB_TOKEN, HUGGINGFACE_TOKEN, HUGGINGFACE_API_KEY, or HF_API_KEY."
            }

        if not repo_id:
            repo_id = (
                os.environ.get("HF_DEFAULT_REPO")
                or os.environ.get("HF_REPO_ID")
                or os.environ.get("HF_DEFAULT_REPOSITORY")
            )
        if not repo_id:
            return {"error": "repo_id is required for huggingface upload."}

        if not file_path:
            return {"error": "file_path is required for huggingface upload."}

        local_path = Path(file_path)
        if not local_path.exists():
            return {"error": f"File not found: {file_path}"}

        if not path_in_repo:
            path_in_repo = local_path.name

        def _upload():
            api = HfApi(token=token)
            return api.upload_file(
                path_or_fileobj=str(local_path),
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=commit_message or "Upload via AetherBrowse",
            )

        result = await asyncio.to_thread(_upload)
        return {
            "action": "huggingface_upload",
            "repo_id": repo_id,
            "repo_type": repo_type,
            "path_in_repo": path_in_repo,
            "commit_message": commit_message,
            "upload_result": result,
        }

    async def telegram_send(self, message: str, chat_id: str = "", parse_mode: str = "Markdown") -> dict:
        """Send a Telegram message through Bot API."""
        token = (
            os.environ.get("TELEGRAM_BOT_TOKEN")
            or os.environ.get("SCBE_TELEGRAM_BOT_TOKEN")
            or os.environ.get("BOT_TOKEN")
            or os.environ.get("TELEGRAM_TOKEN")
        )
        if not token:
            return {"error": "Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN or SCBE_TELEGRAM_BOT_TOKEN."}

        if not chat_id:
            chat_id = (
                os.environ.get("TELEGRAM_CHAT_ID")
                or os.environ.get("SCBE_TELEGRAM_CHAT_ID")
                or os.environ.get("TELEGRAM_CHAT")
                or os.environ.get("CHAT_ID")
                or os.environ.get("TELEGRAM_TO_CHAT_ID")
            )
        if not chat_id:
            return {"error": "No Telegram chat_id provided. Set TELEGRAM_CHAT_ID in env or pass chat_id in action."}

        if not message:
            return {"error": "No message provided for telegram_send."}

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

        try:
            def _call():
                with urllib.request.urlopen(req, timeout=15) as response:
                    return response.read().decode("utf-8", errors="replace")

            data = await asyncio.to_thread(_call)
            return json.loads(data)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def telegram_get_updates(self, offset: int = 0, limit: int = 100) -> dict:
        """Fetch Telegram updates."""
        token = (
            os.environ.get("TELEGRAM_BOT_TOKEN")
            or os.environ.get("SCBE_TELEGRAM_BOT_TOKEN")
            or os.environ.get("BOT_TOKEN")
            or os.environ.get("TELEGRAM_TOKEN")
        )
        if not token:
            return {"error": "Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN or SCBE_TELEGRAM_BOT_TOKEN."}

        params = {}
        if offset:
            params["offset"] = str(offset)
        if limit:
            params["limit"] = str(limit)
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"https://api.telegram.org/bot{token}/getUpdates" + (f"?{qs}" if qs else "")
        req = urllib.request.Request(url)

        try:
            def _call():
                with urllib.request.urlopen(req, timeout=15) as response:
                    return response.read().decode("utf-8", errors="replace")

            data = await asyncio.to_thread(_call)
            return json.loads(data)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def github_action(self, action_name: str, payload: dict) -> dict:
        """Execute a GitHub connector action and return normalized connector output."""
        payload = payload or {}
        if not action_name:
            return {"ok": False, "error": "Missing github action_name"}

        result = await self._connector_bridge.execute("github", action_name, payload)
        if not result.success:
            return {"ok": False, "error": result.error or "GitHub action failed"}

        return {
            "ok": True,
            "platform": "github",
            "action": action_name,
            "result": result.data,
            "elapsed_ms": result.elapsed_ms,
            "credits_earned": result.credits_earned,
        }

    async def get_text(self) -> str:
        """Get all visible text content from the page."""
        return await self.page.inner_text("body")

    async def extract_article(self) -> dict:
        """Extract article-like structured content from the current page."""
        script = """
        () => {
          const root =
            document.querySelector('article') ||
            document.querySelector('main') ||
            document.body;

          const titleEl = document.querySelector('h1') || document.querySelector('title');
          const title = (titleEl?.innerText || titleEl?.textContent || document.title || '').trim();

          const paragraphs = Array.from(root.querySelectorAll('p'))
            .map((p) => (p.innerText || p.textContent || '').trim())
            .filter((t) => t.length >= 40);

          const headings = Array.from(root.querySelectorAll('h1,h2,h3'))
            .map((h) => (h.innerText || h.textContent || '').trim())
            .filter(Boolean)
            .slice(0, 20);

          const text = paragraphs.join('\\n\\n').slice(0, 50000);
          const words = text.split(/\\s+/).filter(Boolean).length;
          const readingMinutes = words > 0 ? Math.max(1, Math.round(words / 220)) : 0;

          return {
            title,
            url: window.location.href,
            paragraph_count: paragraphs.length,
            headings,
            excerpt: text.slice(0, 600),
            text,
            word_count: words,
            estimated_reading_minutes: readingMinutes,
          };
        }
        """
        data = await self.page.evaluate(script)
        return {"action": "extract_article", **(data or {})}

    async def extract_video(self) -> dict:
        """Extract on-page video and media embedding metadata."""
        script = """
        () => {
          const videos = Array.from(document.querySelectorAll('video')).map((v, idx) => ({
            index: idx,
            src: v.currentSrc || v.src || '',
            poster: v.poster || '',
            muted: !!v.muted,
            autoplay: !!v.autoplay,
            controls: !!v.controls,
            duration: Number.isFinite(v.duration) ? Number(v.duration) : null,
            width: v.videoWidth || null,
            height: v.videoHeight || null
          }));

          const iframes = Array.from(document.querySelectorAll('iframe'))
            .map((f) => f.src || '')
            .filter(Boolean)
            .filter((src) => /youtube|youtu\\.be|vimeo|dailymotion|twitch/i.test(src))
            .slice(0, 20);

          const links = Array.from(document.querySelectorAll('a[href]'))
            .map((a) => a.href || '')
            .filter((href) => /youtube|youtu\\.be|vimeo|dailymotion|twitch/i.test(href))
            .slice(0, 20);

          return {
            url: window.location.href,
            video_count: videos.length,
            videos,
            embedded_video_iframes: iframes,
            video_links: links
          };
        }
        """
        data = await self.page.evaluate(script)
        return {"action": "extract_video", **(data or {})}

    async def wait_for(self, selector: str, timeout: int = 10000) -> dict:
        """Wait for an element to appear."""
        await self.page.wait_for_selector(selector, timeout=timeout)
        return {"found": True, "selector": selector}

    # ------------------------------------------------------------------
    #  Compound actions (multi-step recipes)
    # ------------------------------------------------------------------

    async def form_fill_and_submit(self, fields: dict, submit_selector: str) -> dict:
        """Fill multiple form fields then click submit."""
        for selector, value in fields.items():
            await self.page.fill(selector, value)
        await self.page.click(submit_selector)
        await self.page.wait_for_load_state("domcontentloaded")
        return {"action": "form_submit", "fields": len(fields), "url": self.page.url}

    async def upload_product(self, file_path: str, title: str, description: str,
                             price: str, platform_config: dict) -> dict:
        """Generic product upload workflow. Platform-specific selectors come from config."""
        results = []

        # Navigate to upload page
        await self.navigate(platform_config["upload_url"])
        results.append("navigated")

        # Fill title
        if "title_selector" in platform_config:
            await self.fill(platform_config["title_selector"], title)
            results.append("title_filled")

        # Fill description
        if "desc_selector" in platform_config:
            await self.fill(platform_config["desc_selector"], description)
            results.append("desc_filled")

        # Fill price
        if "price_selector" in platform_config:
            await self.fill(platform_config["price_selector"], price)
            results.append("price_filled")

        # Upload file
        if "file_selector" in platform_config:
            await self.upload_file(platform_config["file_selector"], file_path)
            results.append("file_uploaded")

        # Submit
        if "submit_selector" in platform_config:
            await self.page.click(platform_config["submit_selector"])
            await self.page.wait_for_load_state("domcontentloaded")
            results.append("submitted")

        return {"action": "upload_product", "steps": results, "url": self.page.url}

    # ------------------------------------------------------------------
    #  Command dispatch (from agent runtime messages)
    # ------------------------------------------------------------------

    async def execute_command(self, cmd: dict) -> dict:
        """Dispatch a command dict from the agent runtime."""
        action = cmd.get("action", "")
        try:
            if action == "navigate":
                return await self.navigate(cmd["url"], cmd.get("network_profile", ""))
            elif action == "set_network_profile":
                return await self.set_network_profile(cmd.get("network_profile", "open"))
            elif action == "switch_profile":
                return await self.switch_profile(cmd.get("profile_id", "default"))
            elif action == "list_profiles":
                return await self.list_profiles()
            elif action == "snapshot":
                return await self.snapshot()
            elif action == "screenshot":
                return await self.screenshot(cmd.get("name", "page"))
            elif action == "click":
                return await self.click(cmd["selector"])
            elif action == "fill":
                return await self.fill(cmd["selector"], cmd["value"])
            elif action == "upload":
                return await self.upload_file(cmd["selector"], cmd["file_path"])
            elif action == "evaluate":
                return await self.evaluate(cmd["script"])
            elif action == "huggingface_upload":
                return await self.huggingface_upload(
                    cmd.get("file_path", ""),
                    cmd.get("repo_id", ""),
                    cmd.get("repo_type", "model"),
                    cmd.get("path_in_repo", ""),
                    cmd.get("commit_message", ""),
                )
            elif action == "telegram_send":
                return await self.telegram_send(
                    cmd.get("message", ""),
                    cmd.get("chat_id", ""),
                    parse_mode=cmd.get("parse_mode", "Markdown"),
                )
            elif action == "telegram_get_updates":
                return await self.telegram_get_updates(
                    offset=int(cmd.get("offset", 0) or 0),
                    limit=int(cmd.get("limit", 100) or 100),
                )
            elif action.startswith("github_") or action == "github_action":
                action_name = cmd.get("action_name") or cmd.get("github_action") or action
                payload = dict(cmd.get("metadata") or {})
                if cmd.get("repo"):
                    payload["repo"] = cmd["repo"]
                if cmd.get("value"):
                    payload.setdefault("title", cmd["value"])
                if cmd.get("body"):
                    payload["body"] = cmd["body"]
                if cmd.get("message"):
                    payload["body"] = cmd["message"]
                if cmd.get("title"):
                    payload["title"] = cmd["title"]
                return await self.github_action(action_name, payload)
            elif action == "get_text":
                text = await self.get_text()
                return {"text": text[:5000]}  # Truncate for transport
            elif action == "extract_article":
                return await self.extract_article()
            elif action == "extract_video":
                return await self.extract_video()
            elif action == "autofill_login":
                return await self.autofill_login(
                    domain=cmd.get("domain", ""),
                    submit=bool(cmd.get("submit", False)),
                    profile_id=cmd.get("profile_id", ""),
                )
            elif action == "wait_for":
                return await self.wait_for(cmd["selector"], cmd.get("timeout", 10000))
            elif action == "form_submit":
                return await self.form_fill_and_submit(cmd["fields"], cmd["submit"])
            elif action == "upload_product":
                return await self.upload_product(
                    cmd["file_path"], cmd["title"], cmd["description"],
                    cmd["price"], cmd["platform_config"],
                )
            else:
                return {"error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Command failed: {action} — {e}")
            return {"error": str(e), "action": action}


# ---------------------------------------------------------------------------
#  WebSocket client — connects to the agent runtime
# ---------------------------------------------------------------------------

async def worker_loop():
    """Connect to agent runtime and process browser commands."""
    try:
        import websockets
    except ImportError:
        print("ERROR: websockets not installed. pip install websockets")
        sys.exit(1)

    worker = BrowserWorker()
    await worker.launch()

    uri = "ws://127.0.0.1:8400/ws/worker"
    logger.info(f"Connecting to runtime at {uri}")

    while True:
        try:
            async with websockets.connect(uri) as ws:
                logger.info("Connected to agent runtime")
                await ws.send(json.dumps({"type": "worker-ready", "capabilities": [
                    "navigate", "snapshot", "screenshot", "click", "fill",
                    "upload", "evaluate", "huggingface_upload", "get_text", "wait_for",
                    "extract_article", "extract_video",
                    "set_network_profile",
                    "switch_profile", "list_profiles", "autofill_login",
                    "form_submit", "upload_product",
                    "telegram_send", "telegram_get_updates",
                    "github_issue_list", "github_issue_create", "github_issue_comment",
                    "github_issue_close", "github_pr_list", "github_pr_create", "github_pr_merge",
                    "github_codespace_list", "github_codespace_create", "github_codespace_stop",
                ]}))

                async for message in ws:
                    cmd = json.loads(message)
                    if cmd.get("type") == "browser-command":
                        result = await worker.execute_command(cmd)
                        await ws.send(json.dumps({
                            "type": "command-result",
                            "requestId": cmd.get("requestId"),
                            "result": result,
                        }))

        except Exception as e:
            logger.warning(f"Connection lost: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


def main():
    if not HAS_PLAYWRIGHT:
        print("ERROR: Playwright not installed.")
        print("Install: pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    logger.info("Starting AetherBrowse Playwright Worker")
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
