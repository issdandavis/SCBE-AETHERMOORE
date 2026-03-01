"""
ConnectorBridge --- Unified Interface to All External Service Connectors for the HYDRA Agent Fleet
==================================================================================================

Wraps API calls to every supported platform behind a single ``execute()`` call so
that any agent in the fleet can interact with Shopify, Notion, GitHub, Canva,
Adobe, Gamma, Slack, Discord, Zapier, n8n, Airtable, Linear, or generic webhooks
in the same way.

Extends the 10 ConnectorKinds already defined in ``src.api.main`` (n8n, zapier,
shopify, slack, notion, airtable, github_actions, linear, discord, generic_webhook)
with four new platforms: **github** (direct ``gh`` CLI), **canva**, **adobe**, **gamma**.

Credits earned by each call feed directly into MMCCL::

    0.1  --- read operations
    0.5  --- write / update operations
    1.0  --- create operations

Quick start::

    from src.fleet.connector_bridge import ConnectorBridge

    bridge = ConnectorBridge()
    result = await bridge.execute("notion", "search", {"query": "GeoSeed"})
    print(result.success, result.data)

@module fleet/connector_bridge
@layer Layer 13
@patent USPTO #63/961,403
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

try:
    import httpx
except ImportError:  # pragma: no cover -- httpx is a project dependency
    httpx = None  # type: ignore[assignment]


# ═══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ConnectorResult:
    """Outcome of a single connector call.

    Attributes:
        success: Whether the call completed without error.
        data: Parsed response payload (empty dict on failure).
        error: Human-readable error string, empty on success.
        platform: Which platform handled the call.
        elapsed_ms: Wall-clock time for the operation in milliseconds.
        credits_earned: MMCCL credit value (0.1 read / 0.5 write / 1.0 create).
    """

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    platform: str = ""
    elapsed_ms: float = 0.0
    credits_earned: float = 0.0


class ConnectorCapability(str, Enum):
    """Capabilities a platform handler may support."""

    READ = "READ"
    WRITE = "WRITE"
    WEBHOOK = "WEBHOOK"
    SEARCH = "SEARCH"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class ConnectorInfo:
    """Metadata about a single registered connector.

    Attributes:
        platform: Lowercase platform key (e.g. ``"notion"``).
        capabilities: Set of supported :class:`ConnectorCapability` values.
        configured: True when the required env-var token is present.
        description: Short human-readable summary.
    """

    platform: str
    capabilities: Set[ConnectorCapability] = field(default_factory=set)
    configured: bool = False
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Credit Calculation
# ═══════════════════════════════════════════════════════════════════════════════

# Actions whose names imply a *create* get 1.0 credits.
_CREATE_ACTIONS = frozenset(
    {
        "create_issue",
        "create_pr",
        "create_product",
        "create_page",
        "create_record",
        "create_design",
        "create_site",
        "send_message",
        "trigger",
        "post",
        "publish",
        "upload_asset",
    }
)

# Actions whose names imply a *write / update* get 0.5 credits.
_WRITE_ACTIONS = frozenset(
    {
        "close_issue",
        "merge_pr",
        "comment",
        "update_inventory",
        "update_page",
        "update_record",
        "update_site",
        "export_design",
        "status",
    }
)


def _credits_for_action(action: str) -> float:
    """Return MMCCL credit value for *action*.

    Args:
        action: The action string passed to ``execute()``.

    Returns:
        1.0 for creates, 0.5 for writes/updates, 0.1 for reads.
    """
    if action in _CREATE_ACTIONS:
        return 1.0
    if action in _WRITE_ACTIONS:
        return 0.5
    return 0.1


# ═══════════════════════════════════════════════════════════════════════════════
# Env-Var Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _env(name: str) -> Optional[str]:
    """Read a non-empty environment variable or return ``None``."""
    val = os.environ.get(name, "").strip()
    return val if val else None


# ═══════════════════════════════════════════════════════════════════════════════
# ConnectorBridge
# ═══════════════════════════════════════════════════════════════════════════════


class ConnectorBridge:
    """Unified dispatch layer for all external service connectors.

    Args:
        session_pool: Optional shared ``httpx.AsyncClient`` instance.
            When *None* a new client is created per call.

    Usage::

        bridge = ConnectorBridge()
        result = await bridge.execute("github", "list_issues", {"repo": "org/repo"})
    """

    # ── Platform registry (populated in __init__) ──────────────────────────
    _handlers: Dict[str, Callable[..., Coroutine[Any, Any, ConnectorResult]]]
    _infos: Dict[str, ConnectorInfo]

    def __init__(self, session_pool: Any = None) -> None:
        self._session_pool = session_pool
        self._handlers = {}
        self._infos = {}
        self._register_all()

    # ── Public API ─────────────────────────────────────────────────────────

    async def execute(self, platform: str, action: str, payload: Optional[Dict[str, Any]] = None) -> ConnectorResult:
        """Run *action* on *platform* with *payload* and return a :class:`ConnectorResult`.

        Args:
            platform: Lowercase platform key (e.g. ``"notion"``).
            action: Platform-specific action verb (e.g. ``"search"``).
            payload: Arbitrary parameters forwarded to the handler.

        Returns:
            A :class:`ConnectorResult` with ``success``, ``data``, ``error``,
            ``platform``, ``elapsed_ms``, and ``credits_earned`` populated.
        """
        payload = payload or {}
        platform = platform.lower()

        handler = self._handlers.get(platform)
        if handler is None:
            return ConnectorResult(
                success=False,
                error=f"Unknown platform: {platform}",
                platform=platform,
            )

        t0 = time.perf_counter()
        try:
            result = await handler(action, payload)
        except Exception as exc:  # noqa: BLE001
            result = ConnectorResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                platform=platform,
            )

        elapsed = (time.perf_counter() - t0) * 1000.0
        result.platform = platform
        result.elapsed_ms = round(elapsed, 2)
        result.credits_earned = _credits_for_action(action) if result.success else 0.0
        return result

    async def health_check(self, platform: str) -> bool:
        """Return ``True`` if *platform* is configured and reachable.

        Args:
            platform: Lowercase platform key.

        Returns:
            Boolean reachability flag.
        """
        platform = platform.lower()
        if not self.is_configured(platform):
            return False

        # Each handler must gracefully handle a lightweight probe action.
        try:
            result = await self.execute(platform, "_health", {})
            return result.success
        except Exception:  # noqa: BLE001
            return False

    def list_connectors(self) -> List[ConnectorInfo]:
        """Return metadata for every registered connector.

        Returns:
            A list of :class:`ConnectorInfo` objects.
        """
        return list(self._infos.values())

    def is_configured(self, platform: str) -> bool:
        """Return ``True`` when the required env-var token for *platform* is set.

        Args:
            platform: Lowercase platform key.

        Returns:
            Boolean configuration flag.
        """
        info = self._infos.get(platform.lower())
        return info.configured if info else False

    # ── Registration ───────────────────────────────────────────────────────

    def _register_all(self) -> None:
        """Wire every platform handler and build the info registry."""
        self._add(
            "github",
            self._github,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.WRITE, ConnectorCapability.SEARCH, ConnectorCapability.DELETE},
            configured=bool(_env("GITHUB_TOKEN")),
            description="GitHub via gh CLI (issues, PRs, comments)",
        )
        self._add(
            "shopify",
            self._shopify,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.UPDATE, ConnectorCapability.SEARCH},
            configured=bool(_env("SHOPIFY_ADMIN_TOKEN") and _env("SHOPIFY_SHOP_DOMAIN")),
            description="Shopify Admin GraphQL API (products, orders, inventory)",
        )
        self._add(
            "notion",
            self._notion,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.UPDATE, ConnectorCapability.SEARCH},
            configured=bool(_env("NOTION_TOKEN")),
            description="Notion API v1 (pages, databases, search)",
        )
        self._add(
            "airtable",
            self._airtable,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.UPDATE},
            configured=bool(_env("AIRTABLE_TOKEN") and _env("AIRTABLE_BASE_ID")),
            description="Airtable REST API (records CRUD)",
        )
        self._add(
            "canva",
            self._canva,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.WRITE},
            configured=bool(_env("CANVA_API_KEY")),
            description="Canva Connect API (designs, exports)",
        )
        self._add(
            "adobe",
            self._adobe,
            {ConnectorCapability.READ, ConnectorCapability.CREATE},
            configured=bool(_env("ADOBE_CLIENT_ID") and _env("ADOBE_CLIENT_SECRET")),
            description="Adobe Creative Cloud API (assets)",
        )
        self._add(
            "gamma",
            self._gamma,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.UPDATE, ConnectorCapability.WRITE},
            configured=bool(_env("GAMMA_API_KEY")),
            description="Gamma API (popup sites, publish)",
        )
        self._add(
            "slack",
            self._slack,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.WEBHOOK},
            configured=bool(_env("SLACK_BOT_TOKEN")),
            description="Slack Web API (messages, channels)",
        )
        self._add(
            "discord",
            self._discord,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.WEBHOOK},
            configured=bool(_env("DISCORD_BOT_TOKEN")),
            description="Discord Bot API (messages, channels)",
        )
        self._add(
            "zapier",
            self._zapier,
            {ConnectorCapability.WEBHOOK},
            configured=bool(_env("ZAPIER_WEBHOOK_URL")),
            description="Zapier webhook trigger",
        )
        self._add(
            "n8n",
            self._n8n,
            {ConnectorCapability.WEBHOOK, ConnectorCapability.READ},
            configured=bool(_env("N8N_WEBHOOK_URL")),
            description="n8n webhook trigger and status",
        )
        self._add(
            "linear",
            self._linear,
            {ConnectorCapability.READ, ConnectorCapability.CREATE, ConnectorCapability.SEARCH},
            configured=bool(_env("LINEAR_API_KEY")),
            description="Linear GraphQL API (issues)",
        )
        self._add(
            "webhook",
            self._webhook,
            {ConnectorCapability.WEBHOOK},
            configured=True,  # generic -- always available
            description="Generic webhook POST",
        )

    def _add(
        self,
        platform: str,
        handler: Callable[..., Coroutine[Any, Any, ConnectorResult]],
        capabilities: Set[ConnectorCapability],
        configured: bool,
        description: str,
    ) -> None:
        """Register a handler and its metadata."""
        self._handlers[platform] = handler
        self._infos[platform] = ConnectorInfo(
            platform=platform,
            capabilities=capabilities,
            configured=configured,
            description=description,
        )

    # ── HTTP helper ────────────────────────────────────────────────────────

    async def _http(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Any] = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        """Fire an HTTP request using the shared pool or a fresh client.

        Args:
            method: HTTP verb (``"GET"``, ``"POST"``, etc.).
            url: Fully-qualified URL.
            headers: Optional request headers.
            json_body: Optional JSON-serializable body.
            timeout: Timeout in seconds.

        Returns:
            An ``httpx.Response`` object.

        Raises:
            RuntimeError: If httpx is not installed.
        """
        if httpx is None:
            raise RuntimeError("httpx is required but not installed -- pip install httpx")

        if self._session_pool is not None:
            return await self._session_pool.request(method, url, headers=headers, json=json_body, timeout=timeout)

        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.request(method, url, headers=headers, json=json_body)

    # ── Subprocess helper (gh CLI) ─────────────────────────────────────────

    @staticmethod
    async def _run_gh(*args: str, env_extra: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute a ``gh`` CLI command asynchronously.

        Args:
            *args: Positional arguments appended to ``gh``.
            env_extra: Extra environment variables merged into the subprocess env.

        Returns:
            Parsed JSON from stdout when the command exits 0.

        Raises:
            RuntimeError: When the process exits non-zero.
        """
        env = {**os.environ, **(env_extra or {})}
        cmd = ["gh", *args]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"gh exited {proc.returncode}: {stderr.decode().strip()}")

        text = stdout.decode().strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    # ═══════════════════════════════════════════════════════════════════════
    # Platform Handlers
    # ═══════════════════════════════════════════════════════════════════════

    # ── GitHub (gh CLI) ────────────────────────────────────────────────────

    async def _github(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """GitHub operations via the ``gh`` CLI.

        Supported actions:
            list_issues, create_issue, close_issue, list_prs,
            create_pr, merge_pr, comment, _health.

        Args:
            action: Action verb.
            payload: Must include ``repo`` (``"owner/name"``); action-specific
                keys include ``title``, ``body``, ``number``, ``base``, ``head``.

        Returns:
            :class:`ConnectorResult`
        """
        token = _env("GITHUB_TOKEN")
        env_extra = {"GH_TOKEN": token} if token else {}
        repo = payload.get("repo", "")

        try:
            if action == "_health":
                data = await self._run_gh("auth", "status", "--hostname", "github.com", env_extra=env_extra)
                return ConnectorResult(success=True, data=data)

            if action == "list_issues":
                data = await self._run_gh("issue", "list", "--repo", repo, "--json", "number,title,state,url", env_extra=env_extra)
                return ConnectorResult(success=True, data={"issues": data} if isinstance(data, list) else data)

            if action == "create_issue":
                title = payload.get("title", "Untitled")
                body = payload.get("body", "")
                data = await self._run_gh("issue", "create", "--repo", repo, "--title", title, "--body", body, env_extra=env_extra)
                return ConnectorResult(success=True, data=data)

            if action == "close_issue":
                number = str(payload.get("number", ""))
                data = await self._run_gh("issue", "close", "--repo", repo, number, env_extra=env_extra)
                return ConnectorResult(success=True, data=data)

            if action == "list_prs":
                data = await self._run_gh("pr", "list", "--repo", repo, "--json", "number,title,state,url", env_extra=env_extra)
                return ConnectorResult(success=True, data={"prs": data} if isinstance(data, list) else data)

            if action == "create_pr":
                title = payload.get("title", "")
                body = payload.get("body", "")
                base = payload.get("base", "main")
                head = payload.get("head", "")
                data = await self._run_gh(
                    "pr", "create", "--repo", repo, "--title", title, "--body", body,
                    "--base", base, "--head", head,
                    env_extra=env_extra,
                )
                return ConnectorResult(success=True, data=data)

            if action == "merge_pr":
                number = str(payload.get("number", ""))
                data = await self._run_gh("pr", "merge", "--repo", repo, number, "--merge", env_extra=env_extra)
                return ConnectorResult(success=True, data=data)

            if action == "comment":
                number = str(payload.get("number", ""))
                body = payload.get("body", "")
                data = await self._run_gh("issue", "comment", "--repo", repo, number, "--body", body, env_extra=env_extra)
                return ConnectorResult(success=True, data=data)

            return ConnectorResult(success=False, error=f"Unknown github action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Shopify (Admin GraphQL) ────────────────────────────────────────────

    async def _shopify(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Shopify Admin GraphQL API.

        Supported actions:
            list_products, create_product, update_inventory,
            list_orders, get_order, _health.

        Args:
            action: Action verb.
            payload: Action-specific keys (``title``, ``order_id``,
                ``inventory_item_id``, ``quantity``, etc.).

        Returns:
            :class:`ConnectorResult`
        """
        token = _env("SHOPIFY_ADMIN_TOKEN")
        shop = _env("SHOPIFY_SHOP_DOMAIN")
        if not token or not shop:
            return ConnectorResult(success=False, error="SHOPIFY_ADMIN_TOKEN or SHOPIFY_SHOP_DOMAIN not set")

        url = f"https://{shop}/admin/api/2024-01/graphql.json"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}

        try:
            if action == "_health":
                query = '{ shop { name } }'
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "list_products":
                limit = payload.get("limit", 10)
                query = f'{{ products(first: {limit}) {{ edges {{ node {{ id title status }} }} }} }}'
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "create_product":
                title = payload.get("title", "Untitled Product")
                query = f'''
                    mutation {{
                        productCreate(input: {{ title: "{title}" }}) {{
                            product {{ id title }}
                            userErrors {{ field message }}
                        }}
                    }}
                '''
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "update_inventory":
                item_id = payload.get("inventory_item_id", "")
                qty = payload.get("quantity", 0)
                location_id = payload.get("location_id", "")
                query = f'''
                    mutation {{
                        inventoryAdjustQuantities(input: {{
                            reason: "correction",
                            name: "available",
                            changes: [{{ delta: {qty}, inventoryItemId: "{item_id}", locationId: "{location_id}" }}]
                        }}) {{
                            userErrors {{ field message }}
                        }}
                    }}
                '''
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "list_orders":
                limit = payload.get("limit", 10)
                query = f'{{ orders(first: {limit}) {{ edges {{ node {{ id name totalPriceSet {{ shopMoney {{ amount }} }} }} }} }} }}'
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "get_order":
                order_id = payload.get("order_id", "")
                query = f'{{ order(id: "{order_id}") {{ id name email totalPriceSet {{ shopMoney {{ amount }} }} }} }}'
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            return ConnectorResult(success=False, error=f"Unknown shopify action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Notion (API v1) ────────────────────────────────────────────────────

    async def _notion(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Notion API v1.

        Supported actions:
            search, get_page, create_page, update_page,
            query_database, _health.

        Args:
            action: Action verb.
            payload: Keys vary by action (``query``, ``page_id``,
                ``database_id``, ``parent_id``, ``properties``, ``filter``).

        Returns:
            :class:`ConnectorResult`
        """
        token = _env("NOTION_TOKEN")
        if not token:
            return ConnectorResult(success=False, error="NOTION_TOKEN not set")

        base = "https://api.notion.com/v1"
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        try:
            if action == "_health":
                resp = await self._http("GET", f"{base}/users/me", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "search":
                body = {"query": payload.get("query", "")}
                resp = await self._http("POST", f"{base}/search", headers=headers, json_body=body)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "get_page":
                page_id = payload.get("page_id", "")
                resp = await self._http("GET", f"{base}/pages/{page_id}", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "create_page":
                parent_id = payload.get("parent_id", "")
                properties = payload.get("properties", {})
                body: Dict[str, Any] = {
                    "parent": {"page_id": parent_id},
                    "properties": properties,
                }
                if "children" in payload:
                    body["children"] = payload["children"]
                resp = await self._http("POST", f"{base}/pages", headers=headers, json_body=body)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "update_page":
                page_id = payload.get("page_id", "")
                properties = payload.get("properties", {})
                resp = await self._http("PATCH", f"{base}/pages/{page_id}", headers=headers, json_body={"properties": properties})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "query_database":
                db_id = payload.get("database_id", "")
                body_q: Dict[str, Any] = {}
                if "filter" in payload:
                    body_q["filter"] = payload["filter"]
                if "sorts" in payload:
                    body_q["sorts"] = payload["sorts"]
                resp = await self._http("POST", f"{base}/databases/{db_id}/query", headers=headers, json_body=body_q)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            return ConnectorResult(success=False, error=f"Unknown notion action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Airtable ───────────────────────────────────────────────────────────

    async def _airtable(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Airtable REST API.

        Supported actions:
            list_records, create_record, update_record, _health.

        Args:
            action: Action verb.
            payload: Must include ``table`` name; action-specific keys are
                ``fields`` (dict), ``record_id``.

        Returns:
            :class:`ConnectorResult`
        """
        token = _env("AIRTABLE_TOKEN")
        base_id = _env("AIRTABLE_BASE_ID")
        if not token or not base_id:
            return ConnectorResult(success=False, error="AIRTABLE_TOKEN or AIRTABLE_BASE_ID not set")

        base_url = f"https://api.airtable.com/v0/{base_id}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            if action == "_health":
                resp = await self._http("GET", f"{base_url}", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            table = payload.get("table", "")

            if action == "list_records":
                resp = await self._http("GET", f"{base_url}/{table}", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "create_record":
                fields = payload.get("fields", {})
                resp = await self._http("POST", f"{base_url}/{table}", headers=headers, json_body={"fields": fields})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "update_record":
                record_id = payload.get("record_id", "")
                fields = payload.get("fields", {})
                resp = await self._http("PATCH", f"{base_url}/{table}/{record_id}", headers=headers, json_body={"fields": fields})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            return ConnectorResult(success=False, error=f"Unknown airtable action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Canva (Connect API) ────────────────────────────────────────────────

    async def _canva(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Canva Connect API.

        Supported actions:
            list_designs, create_design, export_design, _health.

        Args:
            action: Action verb.
            payload: Action-specific keys (``title``, ``design_id``,
                ``template_id``, ``format``).

        Returns:
            :class:`ConnectorResult`
        """
        api_key = _env("CANVA_API_KEY")
        if not api_key:
            return ConnectorResult(success=False, error="CANVA_API_KEY not set")

        base = "https://api.canva.com/rest/v1"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        try:
            if action == "_health":
                resp = await self._http("GET", f"{base}/users/me", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "list_designs":
                resp = await self._http("GET", f"{base}/designs", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "create_design":
                body: Dict[str, Any] = {}
                if "title" in payload:
                    body["title"] = payload["title"]
                if "template_id" in payload:
                    body["template_id"] = payload["template_id"]
                resp = await self._http("POST", f"{base}/designs", headers=headers, json_body=body)
                return ConnectorResult(success=resp.status_code in (200, 201), data=resp.json())

            if action == "export_design":
                design_id = payload.get("design_id", "")
                fmt = payload.get("format", "pdf")
                body_e = {"format": fmt}
                resp = await self._http("POST", f"{base}/designs/{design_id}/exports", headers=headers, json_body=body_e)
                return ConnectorResult(success=resp.status_code in (200, 201, 202), data=resp.json())

            return ConnectorResult(success=False, error=f"Unknown canva action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Adobe (Creative Cloud) ─────────────────────────────────────────────

    async def _adobe(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Adobe Creative Cloud API.

        Supported actions:
            list_assets, upload_asset, _health.

        Args:
            action: Action verb.
            payload: Action-specific keys (``name``, ``content_type``,
                ``asset_url``).

        Returns:
            :class:`ConnectorResult`
        """
        client_id = _env("ADOBE_CLIENT_ID")
        client_secret = _env("ADOBE_CLIENT_SECRET")
        if not client_id or not client_secret:
            return ConnectorResult(success=False, error="ADOBE_CLIENT_ID or ADOBE_CLIENT_SECRET not set")

        # Adobe CC APIs use IMS for auth -- simplified token exchange
        base = "https://cc-api.adobe.io/v1"
        headers = {"x-api-key": client_id, "Content-Type": "application/json"}

        try:
            if action == "_health":
                resp = await self._http("GET", f"{base}/health", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            if action == "list_assets":
                resp = await self._http("GET", f"{base}/assets", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "upload_asset":
                name = payload.get("name", "untitled")
                content_type = payload.get("content_type", "image/png")
                upload_headers = {**headers, "Content-Type": content_type, "x-asset-name": name}
                resp = await self._http("POST", f"{base}/assets", headers=upload_headers, json_body=payload.get("data", {}))
                return ConnectorResult(success=resp.status_code in (200, 201), data=resp.json() if resp.content else {})

            return ConnectorResult(success=False, error=f"Unknown adobe action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Gamma (Popup Sites) ────────────────────────────────────────────────

    async def _gamma(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Gamma API for popup sites.

        Supported actions:
            create_site, update_site, list_sites, publish, _health.

        Args:
            action: Action verb.
            payload: Action-specific keys (``title``, ``content``,
                ``site_id``, ``template``).

        Returns:
            :class:`ConnectorResult`
        """
        api_key = _env("GAMMA_API_KEY")
        if not api_key:
            return ConnectorResult(success=False, error="GAMMA_API_KEY not set")

        base = "https://api.gamma.app/v1"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        try:
            if action == "_health":
                resp = await self._http("GET", f"{base}/sites", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            if action == "list_sites":
                resp = await self._http("GET", f"{base}/sites", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "create_site":
                body: Dict[str, Any] = {
                    "title": payload.get("title", "Untitled"),
                }
                if "content" in payload:
                    body["content"] = payload["content"]
                if "template" in payload:
                    body["template"] = payload["template"]
                resp = await self._http("POST", f"{base}/sites", headers=headers, json_body=body)
                return ConnectorResult(success=resp.status_code in (200, 201), data=resp.json())

            if action == "update_site":
                site_id = payload.get("site_id", "")
                body_u: Dict[str, Any] = {}
                if "title" in payload:
                    body_u["title"] = payload["title"]
                if "content" in payload:
                    body_u["content"] = payload["content"]
                resp = await self._http("PATCH", f"{base}/sites/{site_id}", headers=headers, json_body=body_u)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "publish":
                site_id = payload.get("site_id", "")
                resp = await self._http("POST", f"{base}/sites/{site_id}/publish", headers=headers, json_body={})
                return ConnectorResult(success=resp.status_code in (200, 201, 202), data=resp.json() if resp.content else {})

            return ConnectorResult(success=False, error=f"Unknown gamma action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Slack (Web API) ────────────────────────────────────────────────────

    async def _slack(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Slack Web API.

        Supported actions:
            send_message, list_channels, _health.

        Args:
            action: Action verb.
            payload: Keys include ``channel`` (ID), ``text``.

        Returns:
            :class:`ConnectorResult`
        """
        token = _env("SLACK_BOT_TOKEN")
        if not token:
            return ConnectorResult(success=False, error="SLACK_BOT_TOKEN not set")

        base = "https://slack.com/api"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            if action == "_health":
                resp = await self._http("POST", f"{base}/auth.test", headers=headers)
                data = resp.json()
                return ConnectorResult(success=data.get("ok", False), data=data)

            if action == "list_channels":
                resp = await self._http("GET", f"{base}/conversations.list", headers=headers)
                data = resp.json()
                return ConnectorResult(success=data.get("ok", False), data=data)

            if action == "send_message":
                channel = payload.get("channel", "")
                text = payload.get("text", "")
                body = {"channel": channel, "text": text}
                resp = await self._http("POST", f"{base}/chat.postMessage", headers=headers, json_body=body)
                data = resp.json()
                return ConnectorResult(success=data.get("ok", False), data=data)

            return ConnectorResult(success=False, error=f"Unknown slack action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Discord (Bot API) ──────────────────────────────────────────────────

    async def _discord(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Discord Bot API.

        Supported actions:
            send_message, list_channels, _health.

        Args:
            action: Action verb.
            payload: Keys include ``channel_id``, ``content``, ``guild_id``.

        Returns:
            :class:`ConnectorResult`
        """
        token = _env("DISCORD_BOT_TOKEN")
        if not token:
            return ConnectorResult(success=False, error="DISCORD_BOT_TOKEN not set")

        base = "https://discord.com/api/v10"
        headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

        try:
            if action == "_health":
                resp = await self._http("GET", f"{base}/users/@me", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "list_channels":
                guild_id = payload.get("guild_id", "")
                resp = await self._http("GET", f"{base}/guilds/{guild_id}/channels", headers=headers)
                return ConnectorResult(success=resp.status_code == 200, data={"channels": resp.json()})

            if action == "send_message":
                channel_id = payload.get("channel_id", "")
                content = payload.get("content", "")
                resp = await self._http("POST", f"{base}/channels/{channel_id}/messages", headers=headers, json_body={"content": content})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            return ConnectorResult(success=False, error=f"Unknown discord action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Zapier (Webhook) ───────────────────────────────────────────────────

    async def _zapier(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Zapier webhook trigger.

        Supported actions:
            trigger, _health.

        Args:
            action: Action verb.
            payload: Arbitrary JSON forwarded as the webhook body.

        Returns:
            :class:`ConnectorResult`
        """
        webhook_url = _env("ZAPIER_WEBHOOK_URL")
        if not webhook_url:
            return ConnectorResult(success=False, error="ZAPIER_WEBHOOK_URL not set")

        try:
            if action == "_health":
                resp = await self._http("POST", webhook_url, json_body={"_health": True})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            if action == "trigger":
                resp = await self._http("POST", webhook_url, json_body=payload)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            return ConnectorResult(success=False, error=f"Unknown zapier action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── n8n (Webhook) ──────────────────────────────────────────────────────

    async def _n8n(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """n8n webhook trigger and status check.

        Supported actions:
            trigger, status, _health.

        Args:
            action: Action verb.
            payload: Arbitrary JSON forwarded as the webhook body.
                For ``status``, ``workflow_id`` is optional.

        Returns:
            :class:`ConnectorResult`
        """
        webhook_url = _env("N8N_WEBHOOK_URL")
        if not webhook_url:
            return ConnectorResult(success=False, error="N8N_WEBHOOK_URL not set")

        try:
            if action == "_health":
                # Probe the webhook endpoint with a minimal payload
                resp = await self._http("POST", webhook_url, json_body={"_health": True})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            if action == "trigger":
                resp = await self._http("POST", webhook_url, json_body=payload)
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            if action == "status":
                # If the n8n instance exposes a /healthz or similar, use it.
                # Fall back to the webhook URL with a status query.
                resp = await self._http("POST", webhook_url, json_body={"action": "status", **payload})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            return ConnectorResult(success=False, error=f"Unknown n8n action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Linear (GraphQL) ───────────────────────────────────────────────────

    async def _linear(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Linear GraphQL API.

        Supported actions:
            list_issues, create_issue, _health.

        Args:
            action: Action verb.
            payload: Keys include ``title``, ``description``, ``team_id``,
                ``filter`` (for list queries).

        Returns:
            :class:`ConnectorResult`
        """
        api_key = _env("LINEAR_API_KEY")
        if not api_key:
            return ConnectorResult(success=False, error="LINEAR_API_KEY not set")

        url = "https://api.linear.app/graphql"
        headers = {"Authorization": api_key, "Content-Type": "application/json"}

        try:
            if action == "_health":
                query = "{ viewer { id name } }"
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "list_issues":
                limit = payload.get("limit", 25)
                query = f"""
                    {{
                        issues(first: {limit}) {{
                            nodes {{ id title state {{ name }} url }}
                        }}
                    }}
                """
                resp = await self._http("POST", url, headers=headers, json_body={"query": query})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            if action == "create_issue":
                title = payload.get("title", "Untitled")
                description = payload.get("description", "")
                team_id = payload.get("team_id", "")
                mutation = f'''
                    mutation {{
                        issueCreate(input: {{
                            title: "{title}",
                            description: "{description}",
                            teamId: "{team_id}"
                        }}) {{
                            success
                            issue {{ id title url }}
                        }}
                    }}
                '''
                resp = await self._http("POST", url, headers=headers, json_body={"query": mutation})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json())

            return ConnectorResult(success=False, error=f"Unknown linear action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))

    # ── Generic Webhook ────────────────────────────────────────────────────

    async def _webhook(self, action: str, payload: Dict[str, Any]) -> ConnectorResult:
        """Generic webhook POST.

        Supported actions:
            post, _health.

        Args:
            action: Action verb.
            payload: Must include ``url``; optional ``headers`` (dict)
                and ``body`` (dict) keys.

        Returns:
            :class:`ConnectorResult`
        """
        try:
            target_url = payload.get("url", "")
            if not target_url:
                return ConnectorResult(success=False, error="payload must include 'url'")

            extra_headers = payload.get("headers", {})
            body = payload.get("body", {})

            if action == "_health":
                resp = await self._http("POST", target_url, headers=extra_headers, json_body={"_health": True})
                return ConnectorResult(success=resp.status_code == 200, data=resp.json() if resp.content else {})

            if action == "post":
                resp = await self._http("POST", target_url, headers=extra_headers, json_body=body)
                try:
                    data = resp.json()
                except Exception:
                    data = {"status_code": resp.status_code, "text": resp.text[:500]}
                return ConnectorResult(success=200 <= resp.status_code < 300, data=data)

            return ConnectorResult(success=False, error=f"Unknown webhook action: {action}")

        except Exception as exc:  # noqa: BLE001
            return ConnectorResult(success=False, error=str(exc))
