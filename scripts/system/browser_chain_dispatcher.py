#!/usr/bin/env python3
"""Browser Chain Dispatcher — Multi-Agent Browser Tentacle Router.

Coordinates Playwright browser agents working as "tentacles" on different
sites.  Bridges the dual-tentacle model (webhook_side + cli_side) from
``github_dual_tentacle_router.py`` with actual browser automation surfaces.

This is a **dispatcher/router** — it decides WHICH agent handles WHICH site
and logs the assignment.  Actual browser execution flows through the existing
HydraHand / PollyVision stack in ``src/browser/``.

Sacred Tongue mapping (6 tentacles):

    KO  korath_forge   — webhook_side — fire/action   — Shopify, Gumroad, GH Pages
    AV  avewing_scout  — webhook_side — water/scout   — Twitter, Bluesky, Reddit, LinkedIn
    RU  runecub_dig    — cli_side     — earth/builder  — git, HuggingFace, PyPI
    CA  caelum_bridge  — cli_side     — air/connector  — Notion, Airtable, Firebase, GCP
    UM  umbra_shadow   — webhook_side — shadow/research — arXiv, Medium, Dev.to, forums
    DR  draconis_guard — cli_side     — dragon/guardian — n8n, SCBE Bridge, AetherNet, local

Usage:
    python scripts/system/browser_chain_dispatcher.py --domain github.com --task navigate
    python scripts/system/browser_chain_dispatcher.py --domain arxiv.org --task scrape
    python scripts/system/browser_chain_dispatcher.py --status
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from src.security.secret_store import pick_secret
except Exception:  # pragma: no cover - optional dependency
    def pick_secret(*_names: str):  # type: ignore[override]
        return "", ""


# ── Paths ────────────────────────────────────────────────────────────

LANE_ROOT = REPO_ROOT / "artifacts" / "agent_comm" / "github_lanes"
CROSSTALK_LOG = LANE_ROOT / "cross_talk.jsonl"
PLAYWRITER_LANE_LOG = LANE_ROOT / "playwriter_lane.jsonl"
ACCESS_MAP_DEFAULT = REPO_ROOT / "config" / "web_access_map.json"
COST_PROFILE_DEFAULT = REPO_ROOT / "config" / "governance" / "browser_cost_controls.json"

DEFAULT_COST_PROFILE: Dict[str, Any] = {
    "default_max_cost_cents": 8,
    "paywall_domains": [
        "medium.com",
        "linkedin.com",
        "x.com",
        "shopify.com",
        "gumroad.com",
    ],
    "premium_hint_keywords": [
        "subscription",
        "requires company-level approval",
        "browser-only",
        "rate limits",
        "paywall",
        "metered",
    ],
    "domain_overrides": {
        "medium.com": {
            "estimated_cost_cents": 10,
            "paywall_risk": "high",
            "alternatives": ["arxiv.org", "dev.to", "news.ycombinator.com"],
        },
        "linkedin.com": {
            "estimated_cost_cents": 12,
            "paywall_risk": "high",
            "alternatives": ["reddit.com", "github.com"],
        },
        "x.com": {
            "estimated_cost_cents": 11,
            "paywall_risk": "high",
            "alternatives": ["bsky.app", "reddit.com"],
        },
        "reddit.com": {
            "estimated_cost_cents": 6,
            "paywall_risk": "medium",
            "alternatives": ["news.ycombinator.com", "dev.to"],
        },
        "dev.to": {
            "estimated_cost_cents": 3,
            "paywall_risk": "low",
            "alternatives": [],
        },
        "arxiv.org": {
            "estimated_cost_cents": 2,
            "paywall_risk": "low",
            "alternatives": [],
        },
    },
}

PROVIDER_ENV_MAP: Dict[str, List[str]] = {
    "github": ["GITHUB_TOKEN"],
    "claude_code": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "cerebras": ["CEREBRAS_API_KEY"],
    "google_ai": ["GOOGLE_AI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "grok_xai": ["XAI_API_KEY"],
    "huggingface": ["HF_TOKEN", "HUGGINGFACEHUB_API_TOKEN"],
    "openrouter_free": ["OPENROUTER_API_KEY"],
    "ollama_local": ["OLLAMA_HOST"],  # command availability is also checked
}


# ── Helpers ──────────────────────────────────────────────────────────

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    """Append a single JSON object as one line to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def load_access_map(path: Path) -> Dict[str, Any]:
    """Load the web_access_map.json if it exists, else return empty dict."""
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_cost_profile(path: Path) -> Dict[str, Any]:
    """Load browser cost controls with a sane built-in fallback."""
    if not path.is_file():
        return DEFAULT_COST_PROFILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_COST_PROFILE
    merged = dict(DEFAULT_COST_PROFILE)
    merged.update(data if isinstance(data, dict) else {})
    return merged


# ── Data Model ───────────────────────────────────────────────────────

@dataclass
class BrowserTentacle:
    """A single browser agent tentacle in the fleet."""

    tentacle_id: str
    agent_name: str
    side: str                                   # "webhook_side" or "cli_side"
    assigned_domains: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    status: str = "idle"                        # "idle" | "busy" | "error"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tentacle_id": self.tentacle_id,
            "agent_name": self.agent_name,
            "side": self.side,
            "assigned_domains": self.assigned_domains,
            "capabilities": self.capabilities,
            "status": self.status,
        }

    def covers_domain(self, domain: str) -> bool:
        """Return True if *domain* matches any of our assigned domain patterns."""
        d = domain.lower()
        for pattern in self.assigned_domains:
            p = pattern.lower()
            if p == d or d.endswith("." + p) or p in d:
                return True
        return False


# ── Dispatcher ───────────────────────────────────────────────────────

class BrowserChainDispatcher:
    """Route browser tasks to the best-fit tentacle and log assignments."""

    def __init__(
        self,
        access_map_path: Optional[str] = None,
        cost_profile_path: Optional[str] = None,
    ):
        path = Path(access_map_path) if access_map_path else ACCESS_MAP_DEFAULT
        profile_path = Path(cost_profile_path) if cost_profile_path else COST_PROFILE_DEFAULT
        self.access_map: Dict[str, Any] = load_access_map(path)
        self.cost_profile: Dict[str, Any] = load_cost_profile(profile_path)
        self._services: List[Dict[str, Any]] = (
            self.access_map.get("services", [])
            if isinstance(self.access_map.get("services", []), list)
            else []
        )
        self._tentacles: Dict[str, BrowserTentacle] = {}

    def _match_service(self, domain: str) -> Dict[str, Any]:
        """Find service metadata entry for a domain (exact/suffix/contains)."""
        d = domain.lower().strip()
        best: Dict[str, Any] = {}
        best_len = -1
        for service in self._services:
            candidate = str(service.get("domain", "")).lower().strip()
            if not candidate:
                continue
            if candidate == d or d.endswith("." + candidate) or candidate in d:
                if len(candidate) > best_len:
                    best = service
                    best_len = len(candidate)
        return best

    @staticmethod
    def _secret_ready(var_name: str) -> bool:
        key = str(var_name or "").strip()
        if not key:
            return False
        _, secret_value = pick_secret(key)
        return bool(str(secret_value or "").strip())

    @staticmethod
    def _env_ready(var_name: str) -> bool:
        key = str(var_name or "").strip()
        if not key:
            return False
        if os.getenv(key):
            return True
        return BrowserChainDispatcher._secret_ready(key)

    @staticmethod
    def _github_cli_ready() -> bool:
        """Return True when ``gh`` is authenticated via keyring/session.

        We intentionally remove ``GITHUB_TOKEN`` from the subprocess env so an
        invalid process-level token does not mask a valid keyring login.
        """
        if not shutil.which("gh"):
            return False
        env = os.environ.copy()
        env.pop("GITHUB_TOKEN", None)
        try:
            probe = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        except OSError:
            return False
        return probe.returncode == 0 and bool((probe.stdout or "").strip())

    def get_domain_connection_plan(self, domain: str, task_type: str = "navigate") -> Dict[str, Any]:
        """Build connector readiness and suggested channel for a domain/task."""
        service = self._match_service(domain)
        if not service:
            return {
                "service": "unknown",
                "domain": domain,
                "ready": False,
                "recommended_channel": "browser",
                "available_channels": [],
                "missing_env_vars": [],
                "setup_steps": [
                    f"Add domain {domain} to config/web_access_map.json with auth metadata.",
                    "Provide connector auth in environment variables or secret store.",
                ],
            }

        access_methods = service.get("access_methods", {}) if isinstance(service.get("access_methods", {}), dict) else {}
        api = access_methods.get("api", {}) if isinstance(access_methods.get("api", {}), dict) else {}
        browser = access_methods.get("browser", {}) if isinstance(access_methods.get("browser", {}), dict) else {}
        cli = access_methods.get("cli", {}) if isinstance(access_methods.get("cli", {}), dict) else {}

        channels: List[str] = []
        missing_env: List[str] = []

        api_available = bool(api.get("available", False))
        browser_available = bool(browser.get("available", False))
        cli_available = bool(cli.get("available", False))

        if api_available:
            channels.append("api")
            env_var = str(api.get("env_var", "")).strip()
            if env_var and not self._env_ready(env_var):
                missing_env.append(env_var)
        if cli_available:
            channels.append("cli")
        if browser_available:
            channels.append("browser")

        # Function-first priority:
        # 1) API when configured
        # 2) CLI when available
        # 3) Browser fallback
        if api_available and not missing_env:
            recommended = "api"
            ready = True
        elif cli_available:
            recommended = "cli"
            ready = True
        elif browser_available:
            recommended = "browser"
            ready = True
        elif api_available:
            recommended = "api"
            ready = False
        else:
            recommended = "browser"
            ready = False

        setup_steps: List[str] = []
        if missing_env:
            for key in missing_env:
                setup_steps.append(f"Set {key} in env or secret store for {service.get('service', domain)}.")
        if not ready:
            setup_steps.append("Connector is not ready; configure auth or switch to a supported channel.")

        return {
            "service": service.get("service", "unknown"),
            "domain": domain,
            "tier": service.get("tier", "unknown"),
            "ready": ready,
            "recommended_channel": recommended,
            "available_channels": channels,
            "missing_env_vars": missing_env,
            "setup_steps": setup_steps,
            "notes": service.get("notes", ""),
        }

    def get_provider_mesh_status(self) -> Dict[str, Any]:
        """Return which AI providers are wired and ready in this runtime."""
        status: Dict[str, Any] = {}
        for provider, env_vars in PROVIDER_ENV_MAP.items():
            active_env = [name for name in env_vars if bool(os.getenv(name))]
            active_secret = [name for name in env_vars if (name not in active_env and self._secret_ready(name))]
            ready = bool(active_env or active_secret)
            status[provider] = {
                "ready": ready,
                "active_env_vars": active_env,
                "active_secret_vars": active_secret,
                "required_env_vars": env_vars,
            }

        # GitHub can be authenticated through gh keyring even when GITHUB_TOKEN
        # is absent from environment variables.
        gh_ready = self._github_cli_ready()
        if "github" in status:
            status["github"]["gh_cli_authenticated"] = gh_ready
            status["github"]["ready"] = bool(status["github"].get("ready") or gh_ready)

        # Ollama can be usable without env vars when local binary exists.
        if shutil.which("ollama"):
            ollama = status.get("ollama_local", {})
            ollama["ready"] = True
            ollama["binary_found"] = True
            status["ollama_local"] = ollama

        status["summary"] = {
            "ready_count": sum(1 for key, item in status.items() if key != "summary" and item.get("ready")),
            "total": len(PROVIDER_ENV_MAP),
        }
        return status

    # ── Registration ─────────────────────────────────────────────────

    def register_tentacle(self, tentacle: BrowserTentacle) -> None:
        """Add (or replace) a tentacle in the pool."""
        self._tentacles[tentacle.tentacle_id] = tentacle

    # ── Matching ─────────────────────────────────────────────────────

    def _match_tentacle(
        self,
        domain: str,
        side_preference: Optional[str] = None,
    ) -> Optional[BrowserTentacle]:
        """Find the best tentacle for *domain*, preferring *side_preference*.

        Scoring:
        1. Domain coverage match  (+10)
        2. Side preference match  (+5)
        3. Idle status            (+3)
        4. Capability count       (+1 per capability)
        """
        best: Optional[BrowserTentacle] = None
        best_score = -1

        for t in self._tentacles.values():
            score = 0
            if t.covers_domain(domain):
                score += 10
            if side_preference and t.side == side_preference:
                score += 5
            if t.status == "idle":
                score += 3
            score += len(t.capabilities)

            if score > best_score:
                best_score = score
                best = t

        return best

    # ── Task Assignment ──────────────────────────────────────────────

    def assign_task(
        self,
        domain: str,
        task_type: str,
        payload: Optional[Dict[str, Any]] = None,
        strict_connectivity: bool = False,
    ) -> Dict[str, Any]:
        """Pick the best tentacle for *domain* + *task_type* and return the
        assignment record.  Also appends a cross-talk packet to the shared
        JSONL log so both webhook_side and cli_side can observe.
        """
        payload = payload or {}
        connection_plan = self.get_domain_connection_plan(domain, task_type=task_type)
        if strict_connectivity and not connection_plan.get("ready", False):
            return {
                "ok": False,
                "error": "connector_not_ready",
                "domain": domain,
                "task_type": task_type,
                "connection_plan": connection_plan,
            }

        # Determine side preference from task type heuristics.
        side_pref = self._infer_side(task_type)
        engine = self._infer_engine(task_type=task_type, payload=payload)
        requested_channel = str(payload.get("channel", "")).strip().lower()
        connection_channel = requested_channel or str(connection_plan.get("recommended_channel", "browser"))
        if connection_channel not in {"api", "cli", "browser"}:
            connection_channel = str(connection_plan.get("recommended_channel", "browser"))

        tentacle = self._match_tentacle(domain, side_preference=side_pref)
        if tentacle is None:
            return {
                "ok": False,
                "error": "no_tentacle_available",
                "domain": domain,
                "task_type": task_type,
            }

        assignment_id = (
            f"bc-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            f"-{uuid.uuid4().hex[:6]}"
        )

        record: Dict[str, Any] = {
            "ok": True,
            "assignment_id": assignment_id,
            "tentacle_id": tentacle.tentacle_id,
            "agent_name": tentacle.agent_name,
            "side": tentacle.side,
            "domain": domain,
            "task_type": task_type,
            "payload": payload,
            "execution_engine": engine,
            "connection_channel": connection_channel,
            "connection_plan": connection_plan,
            "provider_mesh": self.get_provider_mesh_status(),
            "assigned_at": utc_now(),
            "tentacle_status_before": tentacle.status,
        }

        # Mark tentacle busy.
        tentacle.status = "busy"

        # Write cross-talk so both sides see the assignment.
        self._write_crosstalk(record)
        if engine == "playwriter":
            append_jsonl(
                PLAYWRITER_LANE_LOG,
                {
                    "created_at": record["assigned_at"],
                    "assignment_id": assignment_id,
                    "tentacle_id": tentacle.tentacle_id,
                    "agent_name": tentacle.agent_name,
                    "domain": domain,
                    "task_type": task_type,
                    "payload": payload,
                    "connection_channel": connection_channel,
                },
            )

        return record

    # ── Cross-Talk ───────────────────────────────────────────────────

    def cross_talk(
        self,
        from_tentacle: str,
        to_tentacle: str,
        message: str,
    ) -> Dict[str, Any]:
        """Write a cross-talk packet between two tentacles."""
        packet: Dict[str, Any] = {
            "created_at": utc_now(),
            "packet_id": f"xt-{uuid.uuid4().hex[:8]}",
            "type": "browser_chain_crosstalk",
            "from": from_tentacle,
            "to": to_tentacle,
            "message": message,
        }
        append_jsonl(CROSSTALK_LOG, packet)
        return packet

    # ── Fleet Status ─────────────────────────────────────────────────

    def get_fleet_status(self) -> Dict[str, Any]:
        """Return a snapshot of every tentacle's current state."""
        tentacles = {
            tid: t.to_dict() for tid, t in self._tentacles.items()
        }
        summary = {
            "total": len(tentacles),
            "idle": sum(1 for t in self._tentacles.values() if t.status == "idle"),
            "busy": sum(1 for t in self._tentacles.values() if t.status == "busy"),
            "error": sum(1 for t in self._tentacles.values() if t.status == "error"),
        }
        return {"tentacles": tentacles, "summary": summary}

    # ── Internals ────────────────────────────────────────────────────

    @staticmethod
    def _infer_side(task_type: str) -> Optional[str]:
        """Heuristic: which side suits this task type best?"""
        t = task_type.lower()
        webhook_hints = ["navigate", "click", "fill", "screenshot", "scrape", "browse", "research"]
        cli_hints = ["git", "push", "deploy", "sync", "build", "api", "upload", "query"]
        if any(h in t for h in webhook_hints):
            return "webhook_side"
        if any(h in t for h in cli_hints):
            return "cli_side"
        return None

    @staticmethod
    def _infer_engine(task_type: str, payload: Dict[str, Any]) -> str:
        requested = str(payload.get("engine", "")).strip().lower()
        if requested in {"playwriter", "playwright"}:
            return requested

        t = task_type.lower()
        # Prefer playwriter for interactive/browser-state tasks so we reuse
        # the existing signed-in browser context.
        interactive_hints = ["navigate", "click", "fill", "screenshot", "manual", "interactive"]
        if any(h in t for h in interactive_hints):
            return "playwriter"
        return "playwright"

    def _write_crosstalk(self, record: Dict[str, Any]) -> None:
        """Persist an assignment record to the shared cross_talk.jsonl."""
        packet: Dict[str, Any] = {
            "created_at": record["assigned_at"],
            "packet_id": record["assignment_id"],
            "type": "browser_chain_assignment",
            "from": "browser_chain_dispatcher",
            "to": record["tentacle_id"],
            "agent_name": record["agent_name"],
            "side": record["side"],
            "domain": record["domain"],
            "task_type": record["task_type"],
            "connection_channel": record.get("connection_channel", "browser"),
            "execution_engine": record.get("execution_engine", "playwright"),
        }
        append_jsonl(CROSSTALK_LOG, packet)


# ── Pre-configured Fleet ─────────────────────────────────────────────

def build_default_fleet() -> List[BrowserTentacle]:
    """Return the canonical 6-tentacle fleet aligned to Sacred Tongues."""
    return [
        # KO — fire/action tentacle
        BrowserTentacle(
            tentacle_id="KO",
            agent_name="korath_forge",
            side="webhook_side",
            assigned_domains=[
                "github.io", "pages.github.com",
                "shopify.com", "admin.shopify.com",
                "gumroad.com",
            ],
            capabilities=["navigate", "click", "fill", "screenshot"],
        ),
        # AV — water/scout tentacle
        BrowserTentacle(
            tentacle_id="AV",
            agent_name="avewing_scout",
            side="webhook_side",
            assigned_domains=[
                "twitter.com", "x.com",
                "bsky.app", "bsky.social",
                "reddit.com",
                "linkedin.com",
            ],
            capabilities=["navigate", "click", "fill", "screenshot", "scrape"],
        ),
        # RU — earth/builder tentacle
        BrowserTentacle(
            tentacle_id="RU",
            agent_name="runecub_dig",
            side="cli_side",
            assigned_domains=[
                "github.com",
                "huggingface.co",
                "pypi.org",
            ],
            capabilities=["navigate", "click", "fill", "scrape"],
        ),
        # CA — air/connector tentacle
        BrowserTentacle(
            tentacle_id="CA",
            agent_name="caelum_bridge",
            side="cli_side",
            assigned_domains=[
                "notion.so", "notion.site",
                "airtable.com",
                "firebase.google.com", "console.firebase.google.com",
                "console.cloud.google.com",
            ],
            capabilities=["navigate", "click", "fill", "screenshot", "scrape"],
        ),
        # UM — shadow/research tentacle
        BrowserTentacle(
            tentacle_id="UM",
            agent_name="umbra_shadow",
            side="webhook_side",
            assigned_domains=[
                "arxiv.org",
                "medium.com",
                "dev.to",
                "stackoverflow.com",
                "news.ycombinator.com",
                "scholar.google.com",
            ],
            capabilities=["navigate", "screenshot", "scrape"],
        ),
        # DR — dragon/guardian tentacle
        BrowserTentacle(
            tentacle_id="DR",
            agent_name="draconis_guard",
            side="cli_side",
            assigned_domains=[
                "localhost",
                "127.0.0.1",
                "n8n.local", "n8n.io",
                "aethernet.local",
            ],
            capabilities=["navigate", "click", "fill", "screenshot", "scrape"],
        ),
    ]


# ── CLI Entry Point ──────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Browser Chain Dispatcher — route browser tasks to Sacred Tongue tentacles.",
    )
    parser.add_argument(
        "--access-map",
        default=None,
        help="Path to web_access_map.json (default: config/web_access_map.json).",
    )
    parser.add_argument(
        "--cost-profile",
        default=None,
        help="Path to browser_cost_controls.json (default: config/governance/browser_cost_controls.json).",
    )
    parser.add_argument(
        "--domain",
        default=None,
        help="Target domain for the task (e.g., 'arxiv.org').",
    )
    parser.add_argument(
        "--task",
        default="navigate",
        help="Task type: navigate, click, fill, screenshot, scrape, git, push, etc.",
    )
    parser.add_argument(
        "--payload",
        default=None,
        help="Optional JSON string with extra task payload.",
    )
    parser.add_argument(
        "--engine",
        default=None,
        choices=["playwriter", "playwright"],
        help="Force execution engine for this assignment.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print fleet status and exit.",
    )
    parser.add_argument(
        "--provider-status",
        action="store_true",
        help="Print provider mesh readiness (Claude, Grok, HF, Ollama, etc.) and exit.",
    )
    parser.add_argument(
        "--domain-plan",
        action="store_true",
        help="Print connector readiness plan for --domain and exit.",
    )
    parser.add_argument(
        "--strict-connectivity",
        action="store_true",
        help="Fail assignment when connector auth/setup is incomplete.",
    )
    parser.add_argument(
        "--crosstalk-from",
        default=None,
        help="Send a cross-talk message: source tentacle ID.",
    )
    parser.add_argument(
        "--crosstalk-to",
        default=None,
        help="Send a cross-talk message: destination tentacle ID.",
    )
    parser.add_argument(
        "--crosstalk-msg",
        default=None,
        help="Send a cross-talk message: message body.",
    )
    args = parser.parse_args()

    # Build dispatcher and register the default fleet.
    dispatcher = BrowserChainDispatcher(
        access_map_path=args.access_map,
        cost_profile_path=args.cost_profile,
    )
    for tentacle in build_default_fleet():
        dispatcher.register_tentacle(tentacle)

    # ── Fleet status mode ────────────────────────────────────────────
    if args.status:
        print(json.dumps(dispatcher.get_fleet_status(), indent=2))
        return 0

    if args.provider_status:
        print(json.dumps(dispatcher.get_provider_mesh_status(), indent=2))
        return 0

    # ── Cross-talk mode ──────────────────────────────────────────────
    if args.crosstalk_from and args.crosstalk_to and args.crosstalk_msg:
        result = dispatcher.cross_talk(
            args.crosstalk_from,
            args.crosstalk_to,
            args.crosstalk_msg,
        )
        print(json.dumps(result, indent=2))
        return 0

    # ── Assignment mode (default) ────────────────────────────────────
    if not args.domain:
        parser.error("--domain is required for task assignment (or use --status).")
        return 1

    if args.domain_plan:
        print(json.dumps(dispatcher.get_domain_connection_plan(args.domain, task_type=args.task), indent=2))
        return 0

    payload: Dict[str, Any] = {}
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "error": f"bad payload JSON: {exc}"}))
            return 1
    if args.engine:
        payload["engine"] = args.engine

    result = dispatcher.assign_task(
        domain=args.domain,
        task_type=args.task,
        payload=payload,
        strict_connectivity=args.strict_connectivity,
    )

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
